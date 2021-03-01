import logging
import secrets
import string

from django.core.mail import send_mail
from rest_framework import serializers

from utils.exception import CreationError, UpdateError
from .models import Account

alphabet = string.ascii_letters + string.digits
logger = logging.getLogger(__name__)


def get_role_name(role):
    if role == 10:
        return 'DEFAULT'
    if role == 20:
        return 'STORAGE-WORKER'
    if role == 30:
        return 'OFFICE-WORKER'
    if role == 40:
        return 'ADMIN'
    else:
        return 'UNEXPECTED'


def create_password():
    return ''.join(secrets.choice(alphabet) for _ in range(20))


def create_username(role):
    return f"{get_role_name(role)}-{''.join(secrets.choice(alphabet) for _ in range(6))}"


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(max_length=100, read_only=True)
    username = serializers.CharField(max_length=100, read_only=True)
    email = serializers.EmailField(max_length=200)

    class Meta:
        model = Account
        fields = ['role', 'password', 'username', 'email']

    def create(self, validated_data):
        password = create_password()
        username = create_username(validated_data['role'])
        email = validated_data['email']
        try:
            account = Account.objects.create_user(
                username=username,
                password=password,
                role=validated_data['role'],
                email=email
            )
        except Exception as ex:
            logger.error(f"Error while creating user. username={username}, role={validated_data['role']}, email={email}", exc_info=True)
            raise CreationError()
        account.username = username
        account.password = password
        try:
            print(send_mail('Subject', f'логин и пароль для smola20.ru\nusername: {username}\npassword: {password}',
                            'smola20service@gmail.com',
                            [email], fail_silently=False))
            logger.info(f"sent email to {email}")
        except Exception as ex:
            logger.error(f"Error while sending email email={email}, username={username}", exc_info=True)
        logger.info(f"Successfully created user: {username}, {email}")
        return account


class UserEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['username', 'last_name', 'first_name', 'email']

    def update(self, instance, validated_data):
        instance.verified = True
        try:
            return super().update(instance, validated_data)
        except Exception as ex:
            logger.error(f"error while updating user info. vd: {validated_data}")
            raise UpdateError()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['username', 'role', 'first_name', 'last_name', 'email']


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['username', 'first_name', 'last_name', 'is_banned', 'email', 'role']

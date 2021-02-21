import secrets
import string

from rest_framework import serializers
from .models import Account

alphabet = string.ascii_letters + string.digits


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

    class Meta:
        model = Account
        fields = ['role', 'password', 'username', 'username']

    def create(self, validated_data):
        password = create_password()
        username = create_username(validated_data['role'])
        account = Account.objects.create_user(
            username=username,
            password=password,
            role=validated_data['role'],
            email=validated_data['email']
        )

        account.username = username
        account.password = password
        return account


class UserEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['username', 'last_name', 'first_name', 'email']

    def update(self, instance, validated_data):
        instance.verified = True
        return super(instance, validated_data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['username', 'role', 'first_name', 'last_name', 'email']
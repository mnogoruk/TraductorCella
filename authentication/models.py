from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin, User
from django.db import models

from authentication.manager import AccountManager, OperatorManager


class Account(AbstractBaseUser, PermissionsMixin):
    class RoleChoice(models.IntegerChoices):
        ADMIN = 40, 'Admin'
        OFFICE_WORKER = 30, 'Office worker'
        STORAGE_WORKER = 20, 'Storage_worker'
        DEFAULT = 10, 'Default'

    username = models.CharField(max_length=100, unique=True)

    first_name = models.CharField(max_length=100, null=True)
    last_name = models.CharField(max_length=100, null=True)
    is_banned = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    email = models.EmailField(max_length=200, null=True)
    role = models.IntegerField(choices=RoleChoice.choices, default=RoleChoice.DEFAULT)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    objects = AccountManager()

    def set_username(self, username):
        self.username = username

    def set_first_name(self, name):
        self.first_name = name

    def set_last_name(self, name):
        self.last_name = name

    def set_email(self, email):
        self.email = email

    def make_staff(self):
        self.is_staff = True

    def make_not_staff(self):
        self.is_staff = False

    def make_superuser(self):
        self.make_staff()

    def make_admin(self):
        self.make_not_staff()
        self.role = self.RoleChoice.ADMIN

    def make_office_worker(self):
        self.make_not_staff()
        self.role = self.RoleChoice.OFFICE_WORKER

    def make_storage_worker(self):
        self.make_not_staff()
        self.role = self.RoleChoice.STORAGE_WORKER

    def make_default_user(self):
        self.make_not_staff()
        self.role = self.RoleChoice.DEFAULT

    def is_admin(self):
        return self.role == self.RoleChoice.ADMIN

    def is_storage_worker(self):
        return self.role == self.RoleChoice.STORAGE_WORKER

    def is_office_worker(self):
        return self.role == self.RoleChoice.OFFICE_WORKER

    def is_default_user(self):
        return self.role == self.RoleChoice.DEFAULT

    def ban(self):
        self.is_banned = True

    def unban(self):
        self.is_banned = False

    @property
    def is_active(self):
        return not self.is_banned

    def __str__(self):
        return self.username


class Operator(models.Model):
    class OperatorTypeChoice(models.TextChoices):
        USER = 'USR', 'User'
        ANONYMOUS = 'ANS', 'Anonymous'
        SYSTEM = 'STM', 'System'
        DEFAULT = 'DFT', 'Default'

    user = models.OneToOneField(Account,
                                on_delete=models.SET_NULL,
                                related_name='operator',
                                null=True,
                                blank=True)
    name = models.CharField(max_length=150, null=True, blank=True)
    type = models.CharField(max_length=3, default=OperatorTypeChoice.DEFAULT)

    objects = OperatorManager()

    def set_user(self, user):
        self.user = user

    def set_name(self, name):
        self.name = name

    def is_anonymous(self):
        return self.type == Operator.OperatorTypeChoice.ANONYMOUS

    def is_system(self):
        return self.type == Operator.OperatorTypeChoice.SYSTEM

    def is_default(self):
        return self.type == Operator.OperatorTypeChoice.DEFAULT

    def is_user(self):
        return self.type == Operator.OperatorTypeChoice.USER

    def __str__(self):
        return self.name

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin, User
from django.db import models

from authentication.manager import AccountManager


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

    def _make_staff(self):
        self.is_staff = True

    def _unmake_staff(self):
        self.is_staff = False

    def make_admin(self):
        self._make_staff()
        self.role = self.RoleChoice.ADMIN

    def make_office_worker(self):
        self._unmake_staff()
        self.role = self.RoleChoice.OFFICE_WORKER

    def make_storage_worker(self):
        self._unmake_staff()
        self.role = self.RoleChoice.STORAGE_WORKER

    def make_default_user(self):
        self._unmake_staff()
        self.role = self.RoleChoice.DEFAULT

    def ban(self):
        self.is_banned = True

    def unban(self):
        self.is_banned = False

    @property
    def is_active(self):
        return not self.is_banned

    def __str__(self):
        return self.username


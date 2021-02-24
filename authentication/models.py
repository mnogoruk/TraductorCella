import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin, User
from django.contrib import auth
from django.db import models
from django.apps import apps


class RoleChoice(models.IntegerChoices):
    ADMIN = 40, 'Admin'
    OFFICE_WORKER = 30, 'Office worker'
    STORAGE_WORKER = 20, 'Storage_worker'
    DEFAULT = 10, 'Default'


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, username, password, **extra_fields):
        """
        Create and save a user with the given username, email, and password.
        """
        if not username:
            raise ValueError('The given username must be set')
        username = self.model.normalize_username(username)
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        Operator = apps.get_model('cella', 'Operator')
        Operator.objects.create(user=user, name=user.username)
        return user

    def create_user(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        user = self._create_user(username, password, **extra_fields)

        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', RoleChoice.ADMIN)
        extra_fields.setdefault('verified', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(username, password, **extra_fields)

    def with_perm(self, perm, is_active=True, include_superusers=True, backend=None, obj=None):
        if backend is None:
            backends = auth._get_backends(return_tuples=True)
            if len(backends) == 1:
                backend, _ = backends[0]
            else:
                raise ValueError(
                    'You have multiple authentication backends configured and '
                    'therefore must provide the `backend` argument.'
                )
        elif not isinstance(backend, str):
            raise TypeError(
                'backend must be a dotted import path string (got %r).'
                % backend
            )
        else:
            backend = auth.load_backend(backend)
        if hasattr(backend, 'with_perm'):
            return backend.with_perm(
                perm,
                is_active=is_active,
                include_superusers=include_superusers,
                obj=obj,
            )
        return self.none()


class Account(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=100, unique=True)

    first_name = models.CharField(max_length=100, null=True)
    last_name = models.CharField(max_length=100, null=True)
    is_banned = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    email = models.EmailField(max_length=200, null=True)
    verified = models.BooleanField(default=False)
    verifying_slug = models.SlugField(default=uuid.uuid4, editable=False, unique=True)
    role = models.IntegerField(choices=RoleChoice.choices, default=RoleChoice.DEFAULT)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    # Требуется для админки
    @property
    def is_active(self):
        return not self.is_banned

    def __str__(self):
        return self.username

    objects = UserManager()

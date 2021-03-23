from django.contrib import auth
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AnonymousUser
from django.db.models import Manager
from django.apps import apps


class AccountManager(BaseUserManager):
    use_in_migrations = True

    def crete_storage_worker(self, username, password, **extra_fields):
        extra_fields.setdefault('role', self.model.RoleChoice.STORAGE_WORKER)
        user = self.create_user(username, password, **extra_fields)

        return user

    def create_office_worker(self, username, password, **extra_fields):
        extra_fields.setdefault('role', self.model.RoleChoice.OFFICE_WORKER)
        user = self.create_user(username, password, **extra_fields)

        return user

    def create_admin(self, username, password, **extra_fields):
        extra_fields.setdefault('role', self.model.RoleChoice.ADMIN)
        user = self.create_user(username, password, **extra_fields)

        return user

    def create_user(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        user = self._create_user(username, password, **extra_fields)

        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', self.model.RoleChoice.ADMIN)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(username, password, **extra_fields)

    def _create_user(self, username, password, **extra_fields):
        if not username:
            raise ValueError('The given username must be set')
        username = self.model.normalize_username(username)
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

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


class OperatorManager(Manager):

    def get_or_create_operator(self, applicant):

        if isinstance(applicant, self.model):
            return applicant
        elif isinstance(applicant, int):
            return self.get(id=applicant)
        elif isinstance(applicant, apps.get_model('authentication.Account')):
            if self.user_operator_exists(applicant):
                return self.get_user_operator(applicant)
            else:
                operator = self._create_user_operator(applicant)
                return operator
        elif isinstance(applicant, AnonymousUser):
            if self.anonymous_operator_exists():
                return self.get_anonymous_operator()
            else:
                operator = self._create_anonymous_operator()
                return operator
        elif applicant == 'system':
            if self.system_operator_exists():
                return self.get_system_operator()
            else:
                operator = self.create_system_operator()
                return operator
        else:
            raise RuntimeError(f'Unexpected applicant. Got {applicant}')

    def create_system_operator(self):
        if not self.system_operator_exists():
            operator = self._create_system_operator()
            return operator
        else:
            raise RuntimeError("System operator already exists.")

    def create_anonymous_operator(self):
        if not self.anonymous_operator_exists():
            operator = self._create_anonymous_operator()
            return operator
        else:
            raise RuntimeError("Anonymous operator already exists.")

    def create_default_operator(self):
        if not self.default_operator_exists():
            operator = self._create_default_operator()
            return operator
        else:
            raise RuntimeError("Default operator already exists.")

    def create_user_operator(self, user):
        if not self.user_operator_exists(user):
            operator = self._create_user_operator(user)
            return operator
        else:
            raise RuntimeError(f"Operator for {user} exists.")

    def system_operator_exists(self):
        return self.filter(type=self.model.OperatorTypeChoice.SYSTEM).exists()

    def anonymous_operator_exists(self):
        return self.filter(type=self.model.OperatorTypeChoice.ANONYMOUS).exists()

    def default_operator_exists(self):
        return self.filter(type=self.model.OperatorTypeChoice.DEFAULT).exists()

    def user_operator_exists(self, user):
        return self.filter(user=user).exists()

    def get_system_operator(self):
        return self.get(type=self.model.OperatorTypeChoice.SYSTEM)

    def get_anonymous_operator(self):
        return self.get(type=self.model.OperatorTypeChoice.ANONYMOUS)

    def get_default_operator(self):
        return self.get(type=self.model.OperatorTypeChoice.DEFAULT)

    def get_user_operator(self, user):
        return self.get(user=user).object()

    def _create_system_operator(self):
        operator = self.create(type=self.model.OperatorTypeChoice.SYSTEM, name='system')
        return operator

    def _create_anonymous_operator(self):
        operator = self.create(type=self.model.OperatorTypeChoice.ANONYMOUS, name='anonymous')
        return operator

    def _create_default_operator(self):
        operator = self.create(type=self.model.OperatorTypeChoice.DEFAULT, name='default')
        return operator

    def _create_user_operator(self, user):
        name = user.username
        operator = self.create(type=self.model.OperatorTypeChoice.USER, name=name)
        return operator

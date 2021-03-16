from django.conf import settings
from rest_framework import permissions
from .models import Account

RoleChoice = Account.RoleChoice


class OfficeWorkerPermission(permissions.IsAuthenticated):

    def has_permission(self, request, view):
        if settings.DEBUG:
            return True
        if not super().has_permission(request, view):
            return False
        user = request.user
        return user.role >= RoleChoice.OFFICE_WORKER


class StorageWorkerPermission(permissions.IsAuthenticated):

    def has_permission(self, request, view):
        if settings.DEBUG:
            return True
        if not super().has_permission(request, view):
            return False
        user = request.user
        return user.role >= RoleChoice.STORAGE_WORKER


class AdminPermission(permissions.IsAuthenticated):

    def has_permission(self, request, view):
        if settings.DEBUG:
            return True
        if not super().has_permission(request, view):
            return False
        user = request.user
        return user.role >= RoleChoice.ADMIN


class DefaultPermission(permissions.IsAuthenticated):

    def has_permission(self, request, view):
        if settings.DEBUG:
            return True
        if not super().has_permission(request, view):
            return False
        user = request.user
        return user.role >= RoleChoice.DEFAULT

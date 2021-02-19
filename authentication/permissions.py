from rest_framework import permissions
from .models import Account


class OfficeWorkerPermission(permissions.IsAuthenticated):

    def has_permission(self, request, view):
        user = request.user
        return user.role >= Account.RoleChoice.OFFICE_WORKER and super(OfficeWorkerPermission, self).has_permission(request, view)


class StorageWorkerPermission(permissions.IsAuthenticated):

    def has_permission(self, request, view):
        user = request.user
        return user.role >= Account.RoleChoice.STORAGE_WORKER and super(StorageWorkerPermission, self).has_permission(request, view)


class AdminPermission(permissions.IsAuthenticated):

    def has_permission(self, request, view):
        user = request.user
        return user.role >= Account.RoleChoice.ADMIN and super(AdminPermission, self).has_permission(request, view)


class DefaultPermission(permissions.IsAuthenticated):

    def has_permission(self, request, view):
        user = request.user
        return user.role >= Account.RoleChoice.OTHER and super(DefaultPermission, self).has_permission(request, view)

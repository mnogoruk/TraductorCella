import logging

from rest_framework import status
from rest_framework.generics import CreateAPIView, UpdateAPIView, ListAPIView, DestroyAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from utils.exception import NoParameterSpecified, UpdateError
from .serializer import UserCreateSerializer, UserEditSerializer, UserSerializer, AccountSerializer
from .models import Account

from authentication.permissions import DefaultPermission, AdminPermission

logger = logging.getLogger(__name__)


class UserCreateView(CreateAPIView):
    serializer_class = UserCreateSerializer
    permission_classes = (IsAuthenticated, AdminPermission)


class UserEditView(UpdateAPIView):
    serializer_class = UserEditSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user


class UserListView(ListAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated, AdminPermission)

    def get_queryset(self):
        accounts = Account.objects.exclude(id=self.request.user.id)
        return accounts


class UserChangePasswordView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        user = request.user
        print(request.data)
        password = request.data['password']
        user.set_password(password)
        user.save()
        return Response(data={'correct': True}, status=status.HTTP_200_OK)


class UserDeleteView(DestroyAPIView):
    permission_classes = (IsAuthenticated, AdminPermission)

    def get_object(self):
        data = self.request.data
        try:
            a_id = data['id']
            return Account.objects.filter(id=a_id)
        except KeyError as ex:
            logger.warning(f"'id' not specified | {self.__class__.__name__}")
            raise NoParameterSpecified('ids')
        except Account.DoesNotExist:
            logger.warning("Update error | ResourceBulkDeleteView")
            raise UpdateError()


class CheckVerifyingView(APIView):
    permission_classes = ()

    def post(self, request, *args, **kwargs):
        verifying_slug = kwargs['verifying_slug']
        return Response(
            data={'verified': Account.objects.filter(verifying_slug=verifying_slug, verified=True).exists()})


class CheckView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        return Response(data={'correct': True}, status=status.HTTP_200_OK)


class AccountDetailView(RetrieveAPIView):
    permission_classes = (IsAuthenticated, DefaultPermission)
    serializer_class = AccountSerializer

    def get_object(self):
        return self.request.user

import logging

from rest_framework import status
from rest_framework.generics import CreateAPIView, UpdateAPIView, ListAPIView, DestroyAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from utils.exception import NoParameterSpecified, UpdateError
from .serializer import UserCreateSerializer, UserEditSerializer, UserSerializer, AccountSerializer, \
    TokenObtainPairWithRoleSerializer
from .models import Account
from cella.models import Operator
from authentication.permissions import DefaultPermission, AdminPermission

logger = logging.getLogger(__name__)


class UserCreateView(CreateAPIView):
    serializer_class = UserCreateSerializer
    permission_classes = (IsAuthenticated, AdminPermission)


class UserEditView(UpdateAPIView):
    serializer_class = UserEditSerializer
    permission_classes = (IsAuthenticated,)

    def perform_update(self, serializer):
        user = serializer.save()
        if user.first_name or user.last_name:
            Operator.objects.filter(user=user).update(name=f"{user.last_name} {user.first_name}")
        return user

    def get_object(self):
        return self.request.user


class UserListView(ListAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated, AdminPermission)

    def get_queryset(self):
        accounts = Account.objects.exclude(id=self.request.user.id, username='bitrix')
        return accounts


class UserChangePasswordView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        user = request.user
        old_password = request.data['old_password']
        if not request.user.check_password(old_password):
            logger.warning(f"Incorrect password for applicant: {user.username}")
            return Response(data={"old_password": "Incorrect password"}, status=status.HTTP_400_BAD_REQUEST)
        new_password = request.data['password']
        user.set_password(new_password)
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


class TokenObtainPairWithRoleView(TokenObtainPairView):
    """
    Takes a set of applicant credentials and returns an access and refresh JSON web
    token pair to prove the authentication of those credentials.
    """
    serializer_class = TokenObtainPairWithRoleSerializer
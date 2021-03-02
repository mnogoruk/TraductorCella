from asgiref.sync import async_to_sync
from django.http import Http404
from rest_framework import status
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.generics import RetrieveAPIView, CreateAPIView, UpdateAPIView, ListAPIView

from logging import getLogger

from rest_framework.response import Response
from rest_framework.views import APIView

from cella.serializer import FileSerializer
from cella.service import Operators
from resources.models import Resource
from resources.serializer import ResourceSerializer, ResourceWithUnverifiedCostSerializer, ResourceActionSerializer, \
    ResourceShortSerializer, ResourceProviderSerializer
from resources.service import Resources
from utils.exception import ParameterExceptions, NoParameterSpecified, FileException, CreationError, UpdateError, \
    QueryError, WrongParameterType
from utils.pagination import StandardResultsSetPagination
from authentication.permissions import OfficeWorkerPermission, AdminPermission, StorageWorkerPermission, \
    DefaultPermission
from rest_framework.permissions import IsAuthenticated

logger = getLogger(__name__)


class ResourceDetailView(RetrieveAPIView):
    serializer_class = ResourceSerializer
    permission_classes = [IsAuthenticated, DefaultPermission]

    def get_object(self):
        r_id = self.kwargs['r_id']
        try:
            resource = Resources.detail(r_id)
        except Resource.DoesNotExist:
            logger.warning(f"Can`t get object 'Resource' with id: {r_id} | {self.__class__.__name__}")
            raise Http404()

        return resource


class ResourceCreateView(CreateAPIView):
    serializer_class = ResourceSerializer
    permission_classes = [IsAuthenticated, OfficeWorkerPermission]

    def perform_create(self, serializer):
        try:
            serializer.save(request=self.request)
        except Resources.CreateError:
            logger.warning(
                f"Error while creating Resource. Request data: {self.request.data} | {self.__class__.__name__}",
                exc_info=True)
            raise CreationError()


class ResourceUpdateView(UpdateAPIView):
    serializer_class = ResourceSerializer
    permission_classes = [IsAuthenticated, OfficeWorkerPermission]

    def perform_update(self, serializer):
        try:
            serializer.save(request=self.request)
        except Resources.UpdateError as ex:
            logger.warning(
                f"Error while updating Resource. Resource data: {self.request.data}| {self.__class__.__name__}",
                exc_info=True)
            raise UpdateError()

    def get_object(self):
        r_id = self.kwargs['r_id']
        try:
            resource = Resources.get(r_id)
        except Resource.DoesNotExist:
            logger.warning(f"Can`t get object 'Resource'. | {self.__class__.__name__}", exc_info=True)
            raise Http404()

        return resource


class ResourceWithUnverifiedCostsView(ListAPIView):
    serializer_class = ResourceWithUnverifiedCostSerializer
    permission_classes = [IsAuthenticated, OfficeWorkerPermission]

    def get_queryset(self):
        try:
            return Resources.with_unverified_cost()
        except Resources.QueryError:
            logger.warning(f"Query error | {self.__class__.__name__}", exc_info=True)
            raise QueryError()


class ExpiredResourceCount(APIView):
    permission_classes = [IsAuthenticated, DefaultPermission]

    def get(self, request, *args, **kwargs):
        return Response(data={'count': Resources.expired_count()}, status=status.HTTP_200_OK)


class ResourceListView(ListAPIView):
    serializer_class = ResourceSerializer
    permission_classes = [StorageWorkerPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'id', 'provider__name', 'external_id']
    ordering = '-created_at'
    ordering_fields = [
        'last_change_amount',
        'last_change_cost',
        'name',
        'external_id',
        'provider__name',
        'cost',
        'amount',
        'amount_limit',
        'created_at'
    ]

    def get_queryset(self):
        try:
            return Resources.list()
        except Resources.QueryError:
            logger.warning(f"Query error | ResourceListView")
            raise QueryError()


class ResourceActionsView(ListAPIView):
    serializer_class = ResourceActionSerializer
    permission_classes = [IsAuthenticated, AdminPermission]

    def get_queryset(self):
        try:
            return Resources.actions(self.kwargs['r_id'])
        except Resources.QueryError:
            logger.warning(f"Query error | {self.__class__.__name__}", exc_info=True)
            raise QueryError()


class ResourceShortListView(ListAPIView):
    serializer_class = ResourceShortSerializer
    permission_classes = [IsAuthenticated, DefaultPermission]

    def get_queryset(self):
        try:
            return Resources.shortlist()
        except Resources.QueryError:
            logger.warning(f"Query error | {self.__class__.__name__}", exc_info=True)
            raise QueryError()


class ResourceSetCostView(APIView):
    permission_classes = [IsAuthenticated, OfficeWorkerPermission]

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            r_id = data['id']
        except KeyError as ex:
            logger.warning(f"'id' not specified | {self.__class__.__name__}")
            raise NoParameterSpecified('id')
        try:
            value = float(data['cost'])
        except KeyError as ex:
            logger.warning(f"'cost' not specified | {self.__class__.__name__}")
            raise NoParameterSpecified('cost')
        except TypeError as ex:
            logger.warning(f"'cost' wrong type")
            raise WrongParameterType('cost', 'float')
        if value is not None:
            try:
                cost, _ = Resources.set_cost(r_id, value, request.user)
            except Resources.UpdateError:
                logger.warning(f"Update error | {self.__class__.__name__}")
                raise UpdateError()
            return Response(data={'id': r_id, 'cost': cost.value}, status=status.HTTP_202_ACCEPTED)
        else:
            logger.warning(f"Set cost | {self.__class__.__name__}")
            raise NoParameterSpecified()


class ResourceSetAmount(APIView):
    permission_classes = [IsAuthenticated, StorageWorkerPermission]

    def post(self, request, *args, **keargs):
        data = request.data
        try:
            r_id = data['id']
        except KeyError as ex:
            logger.warning(f"'id' not specified | {self.__class__.__name__}")
            raise NoParameterSpecified('id')
        try:
            amount = float(data['amount'])
        except KeyError as ex:
            logger.warning(f"'amount' not specified | {self.__class__.__name__}")
            raise NoParameterSpecified('amount')
        except TypeError as ex:
            logger.warning(f"'amount' wrong type | {self.__class__.__name__}")
            WrongParameterType('cost', 'float')
        try:
            amount, _ = Resources.set_amount(r_id, amount, user=request.user)
        except Resources.UpdateError:
            logger.warning(f"Update error | {self.__class__.__name__}", exc_info=True)
            raise UpdateError()
        return Response(data={'id': r_id, 'amount': amount}, status=status.HTTP_202_ACCEPTED)

class ResourceAddAmountView(APIView):
    permission_classes = [IsAuthenticated, StorageWorkerPermission]

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            r_id = data['id']
        except KeyError as ex:
            logger.warning(f"'id' not specified | {self.__class__.__name__}")
            raise NoParameterSpecified('id')
        try:
            delta_amount = float(data['amount'])
        except KeyError as ex:
            logger.warning(f"'amount' not specified | {self.__class__.__name__}")
            raise NoParameterSpecified('amount')
        except TypeError as ex:
            logger.warning(f"'amount' wrong type | {self.__class__.__name__}")
            WrongParameterType('cost', 'float')
        try:
            amount, _ = Resources.change_amount(r_id, delta_amount, user=request.user)
        except Resources.UpdateError:
            logger.warning(f"Update error | {self.__class__.__name__}", exc_info=True)
            raise UpdateError()
        return Response(data={'id': r_id, 'amount': amount}, status=status.HTTP_202_ACCEPTED)


class ResourceVerifyCostView(APIView):
    permission_classes = [IsAuthenticated, OfficeWorkerPermission]

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            ids = data['ids']
        except KeyError as ex:
            logger.warning(f"'id' not specified | {self.__class__.__name__}")
            raise NoParameterSpecified('ids')
        if not isinstance(ids, list):
            logger.warning(f"'ids' has wrong type. Type: {type(ids)} | {self.__class__.__name__}")
            raise ParameterExceptions(detail="'ids' must be list object.")
        if ids is not None:
            try:
                Resources.verify_cost(ids, request.user)
            except Resources.UpdateError:
                logger.warning(f"Update error | {self.__class__.__name__}", exc_info=True)
                raise UpdateError()
            return Response(data={'correct': True}, status=status.HTTP_202_ACCEPTED)


class ProviderListView(ListAPIView):
    serializer_class = ResourceProviderSerializer
    permission_classes = [IsAuthenticated, DefaultPermission]

    def get_queryset(self):
        try:
            return Resources.providers()
        except Resources.QueryError:
            logger.warning(f"Query error | ProviderListView")
            raise QueryError()


# TODO: ...
class ResourceExelUploadView(CreateAPIView):
    serializer_class = FileSerializer
    permission_classes = [IsAuthenticated, OfficeWorkerPermission]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.instance = None

    def post(self, request, *args, **kwargs):

        response = super(ResourceExelUploadView, self).post(request, *args, **kwargs)
        instance = self.get_instance()
        try:
            operator = Operators.get_operator(request.user)
            creation = async_to_sync(Resources.create_from_excel)
            creation(file_instance_id=instance.id, operator_id=operator.id)
        except Exception as e:
            logger.warning(f"File error. File: {response}| {self.__class__.__name__}", exc_info=True)
            raise FileException()
        return response

    def perform_create(self, serializer):
        self.instance = serializer.save()

    def get_instance(self):
        return self.instance


class ResourceBulkDeleteView(APIView):
    permission_classes = [IsAuthenticated, OfficeWorkerPermission]

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            ids = data['ids']
        except KeyError as ex:
            logger.warning(f"'id' not specified | {self.__class__.__name__}")
            raise NoParameterSpecified('ids')
        if not isinstance(ids, list):
            logger.warning(f"'ids' has wrong type. Type: {type(ids)} | {self.__class__.__name__}")
            raise ParameterExceptions(detail="'ids' must be list object.")
        try:
            Resources.bulk_delete(ids, request.user)
        except Resources.UpdateError:
            logger.warning("Update error | {self.__class__.__name__}")
            raise UpdateError()
        return Response(data={'correct': True}, status=status.HTTP_202_ACCEPTED)

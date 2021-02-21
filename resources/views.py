from asgiref.sync import async_to_sync, sync_to_async
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
    QueryError
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
            logger.warning(f"Can`t get object 'Resource' with id: {r_id} | ResourceDetailView")
            raise Http404()
        self.check_object_permissions(request=self.request, obj=resource)

        return resource


class ResourceCreateView(CreateAPIView):
    serializer_class = ResourceSerializer
    permission_classes = [IsAuthenticated, OfficeWorkerPermission]

    def perform_create(self, serializer):
        try:
            serializer.save(request=self.request)
        except Resources.CreateError:
            logger.warning("Error while creating Resource | ResourceCreateView")
            raise CreationError()


class ResourceUpdateView(UpdateAPIView):
    serializer_class = ResourceSerializer
    permission_classes = [IsAuthenticated, OfficeWorkerPermission]

    def perform_update(self, serializer):
        try:
            serializer.save(request=self.request)
        except Resources.UpdateError as ex:
            logger.warning("Error while updating Resource | ResourceUpdateView")
            raise UpdateError()

    def get_object(self):
        r_id = self.kwargs['r_id']
        try:
            resource = Resources.get(r_id)
        except Resource.DoesNotExist:
            logger.warning("Can`t get object 'Resource'. | ResourceUpdateView")
            raise Http404()
        self.check_object_permissions(request=self.request, obj=resource)

        return resource


class ResourceWithUnverifiedCostsView(ListAPIView):
    serializer_class = ResourceWithUnverifiedCostSerializer
    permission_classes = [IsAuthenticated, OfficeWorkerPermission]

    def get_queryset(self):
        try:
            return Resources.with_unverified_cost()
        except Resources.QueryError:
            logger.warning(f"Query error | ResourceWithUnverifiedCostsView")
            raise QueryError()


class ResourceListView(ListAPIView):
    IsAuthenticated = [DefaultPermission]
    serializer_class = ResourceSerializer
    permission_classes = [OfficeWorkerPermission, ]
    pagination_class = StandardResultsSetPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'id', 'provider__name']
    ordering_fields = [
        'last_change_amount',
        'last_change_cost',
        'name',
        'external_id',
        'provider__name',
        'cost',
        'amount'
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
            logger.warning(f"Query error | ResourceActionsView")
            raise QueryError()


class ResourceShortListView(ListAPIView):
    serializer_class = ResourceShortSerializer
    permission_classes = [IsAuthenticated, DefaultPermission]

    def get_queryset(self):
        try:
            return Resources.shortlist()
        except Resources.QueryError:
            logger.warning(f"Query error | ResourceShortListView")
            raise QueryError()


class ResourceSetCostView(APIView):
    permission_classes = [IsAuthenticated, OfficeWorkerPermission]

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            r_id = data['id']
        except KeyError as ex:
            logger.warning(f"'id' not specified | ResourceSetCostView")
            raise NoParameterSpecified('id')
        try:
            value = data['cost']
        except KeyError as ex:
            logger.warning(f"'cost' not specified | ResourceSetCostView")
            raise NoParameterSpecified('cost')
        if value is not None:
            try:
                cost, _ = Resources.set_cost(r_id, value, request.user)
            except Resources.UpdateError:
                logger.warning(f"Update error | ResourceSetCostView")
                raise UpdateError()
            return Response(data={'id': r_id, 'cost': cost.value}, status=status.HTTP_202_ACCEPTED)
        else:
            raise NoParameterSpecified()


class ResourceAddAmountView(APIView):
    permission_classes = [IsAuthenticated, StorageWorkerPermission]

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            r_id = data['id']
        except KeyError as ex:
            logger.warning(f"'id' not specified | ResourceAddAmountView")
            raise NoParameterSpecified('id')
        try:
            delta_amount = data['amount']
        except KeyError as ex:
            logger.warning(f"'amount' not specified | ResourceAddAmountView")
            raise NoParameterSpecified('amount')
        try:
            amount, _ = Resources.change_amount(r_id, delta_amount, user=request.user)
        except Resources.UpdateError:
            logger.warning(f"Update error | ResourceAddAmountView")
            raise UpdateError()
        return Response(data={'id': r_id, 'amount': amount}, status=status.HTTP_202_ACCEPTED)


class ResourceVerifyCostView(APIView):
    permission_classes = [IsAuthenticated, OfficeWorkerPermission]

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            ids = data['ids']
        except KeyError as ex:
            logger.warning(f"'id' not specified | ResourceVerifyCostView")
            raise NoParameterSpecified('ids')
        if not isinstance(ids, list):
            logger.warning(f"'ids' has wrong type. Type: {type(ids)} | ResourceVerifyCostView")
            raise ParameterExceptions(detail="'ids' must be list object.")
        if ids is not None:
            try:
                Resources.verify_cost(ids, request.user)
            except Resources.UpdateError:
                logger.warning(f"Update error | ResourceVerifyCostView")
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
            logger.warning("File error | ResourceExelUploadView", exc_info=True)
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
            logger.warning(f"'id' not specified | ResourceBulkDeleteView")
            raise NoParameterSpecified('ids')
        if not isinstance(ids, list):
            logger.warning(f"'ids' has wrong type. Type: {type(ids)} | ResourceBulkDeleteView")
            raise ParameterExceptions(detail="'ids' must be list object.")
        try:
            Resources.bulk_delete(ids, request.user)
        except Resources.UpdateError:
            logger.warning("Update error | ResourceBulkDeleteView")
            raise UpdateError()
        return Response(data={'correct': True}, status=status.HTTP_202_ACCEPTED)

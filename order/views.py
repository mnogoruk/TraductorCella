import logging

from django.http import Http404
from rest_framework import status
from rest_framework.authentication import BasicAuthentication
from rest_framework.generics import RetrieveAPIView, ListAPIView, CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from order.serializer import OrderSerializer, OrderGetSerializer
from order.service import Orders
from utils.exception import NoParameterSpecified, WrongParameterValue, WrongParameterType
from utils.pagination import StandardResultsSetPagination
from authentication.permissions import OfficeWorkerPermission, StorageWorkerPermission, DefaultPermission

logger = logging.getLogger(__name__)


class OrderDetailView(RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, DefaultPermission]

    def get_object(self):
        o_id = self.kwargs.get('o_id')
        try:
            order = Orders.detail(o_id)
        except Orders.DoesNotExist:
            logger.warning(f"Can`t get object 'Order' with id: {o_id} | {self.__class__.__name__}", exc_info=True)
            raise Http404
        self.check_object_permissions(request=self.request, obj=order)

        return order


class OrderListView(ListAPIView):
    serializer_class = OrderSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated, DefaultPermission]

    def get_queryset(self):
        try:
            return Orders.list()
        except Orders.QueryError:
            logger.warning(f"List error | {self.__class__.__name__}", exc_info=True)


class OrderAssembleSpecificationView(APIView):
    permission_classes = [IsAuthenticated, StorageWorkerPermission]

    def post(self, request, *args, **kwargs):
        data = request.data

        try:
            order_id = data['order_id']
        except KeyError as ex:
            logger.warning(f"'order_id' not specified | {self.__class__.__name__}", exc_info=True)
            raise NoParameterSpecified('order_id')
        try:
            specification_id = data.get('specification_id', None)
        except KeyError as ex:
            logger.warning(f"'specification_id' not specified | {self.__class__.__name__}", exc_info=True)
            raise NoParameterSpecified('specification_id')

        if order_id is not None and specification_id is not None:
            try:
                Orders.assemble_specification(order_id, specification_id)
            except Orders.AssembleError:
                logger.warning(f"assemble info. | {self.__class__.__name__}", exc_info=True)
            return Response(data={"correct": True}, status=status.HTTP_202_ACCEPTED)
        else:
            raise NoParameterSpecified()


class OrderDisAssembleSpecificationView(APIView):
    permission_classes = [IsAuthenticated, StorageWorkerPermission]

    def post(self, request, *args, **kwargs):
        data = request.data

        try:
            order_id = data['order_id']
        except KeyError as ex:
            raise NoParameterSpecified('order_id')

        try:
            specification_id = data.get('specification_id', None)
        except KeyError as ex:
            raise NoParameterSpecified('specification_id')

        if order_id is not None and specification_id is not None:
            Orders.disassemble_specification(order_id, specification_id)
            return Response(data={"correct": True}, status=status.HTTP_202_ACCEPTED)
        else:
            raise NoParameterSpecified()


class OrderManageActionView(APIView):
    permission_classes = [IsAuthenticated, StorageWorkerPermission]

    def post(self, request, *args, **kwargs):
        data = request.data

        try:
            order_id = data['id']
        except KeyError as ex:
            raise NoParameterSpecified('id')

        try:
            action = data.get('action', None)
        except KeyError as ex:
            raise NoParameterSpecified('action')

        if order_id is not None and action is not None:
            if action == 'activate':
                Orders.activate(order_id, request.user)
            elif action == 'deactivate':
                Orders.deactivate(order_id, request.user)
            elif action == 'confirm':
                Orders.confirm(order_id, request.user)
            else:
                raise WrongParameterValue('action')
            return Response(data={'correct': True}, status=status.HTTP_202_ACCEPTED)
        else:
            raise NoParameterSpecified()


class OrderAssemblingInfoView(APIView):
    permission_classes = [IsAuthenticated, DefaultPermission]

    def get(self, request, *args, **kwargs):
        o_id = self.kwargs.get('o_id')
        miss_specification, miss_resources = Orders.assembling_info(o_id)
        return Response(data={'missing_specification': miss_specification,
                              'missing_resources': miss_resources},
                        status=status.HTTP_200_OK)


class OrderStatusCount(APIView):
    permission_classes = [IsAuthenticated, DefaultPermission]

    def get(self, request, *args, **kwargs):
        return Response(data=Orders.status_count(), status=status.HTTP_202_ACCEPTED)


class OrderBulkDeleteView(APIView):
    permission_classes = [IsAuthenticated, OfficeWorkerPermission]

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            ids = data['ids']
        except KeyError as ex:
            raise NoParameterSpecified('ids')
        if not isinstance(ids, list):
            raise WrongParameterType('ids', 'list')
        Orders.bulk_delete(ids, request.user)
        return Response(data={'correct': True}, status=status.HTTP_202_ACCEPTED)


class OrderCreateView(CreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, OfficeWorkerPermission]

    def perform_create(self, serializer):
        return serializer.save(request=self.request)


class ReceiveOrderView(CreateAPIView):
    serializer_class = OrderGetSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (BasicAuthentication,)

    def perform_create(self, serializer):
        return serializer.save(request=self.request)

    def post(self, request, *args, **kwargs):
        try:
            self.create(request, *args, **kwargs)
            return Response(data={'received': True}, status=status.HTTP_202_ACCEPTED)
        except Exception as ex:
            return Response(data={'received': False}, status=status.HTTP_400_BAD_REQUEST)

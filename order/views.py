import logging

from django.http import Http404
from rest_framework import status
from rest_framework.authentication import BasicAuthentication
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.generics import RetrieveAPIView, ListAPIView, CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from order.serializer import OrderSerializer, OrderGetSerializer, OrderDetailSerializer
from order.service import Orders
from utils.exception import NoParameterSpecified, WrongParameterValue, WrongParameterType, QueryError, StatusError
from utils.pagination import StandardResultsSetPagination
from authentication.permissions import OfficeWorkerPermission, StorageWorkerPermission, DefaultPermission

logger = logging.getLogger(__name__)


class OrderDetailView(RetrieveAPIView):
    serializer_class = OrderDetailSerializer
    permission_classes = [IsAuthenticated, DefaultPermission]

    def get_object(self):
        o_id = self.kwargs.get('o_id')
        try:
            order = Orders.detail(o_id)
        except Orders.DoesNotExist:
            logger.warning(f"Can`t get object 'Order' with id: {o_id} | {self.__class__.__name__}", exc_info=True)
            raise Http404

        return order


class OrderListView(ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, DefaultPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['external_id', 'id', 'source__name']
    ordering = 'status'
    ordering_fields = [
        'external_id',
        'source__name',
        'status'
    ]

    def get_queryset(self):
        try:
            return Orders.list()
        except Orders.QueryError:
            logger.warning(f"Queryset error | {self.__class__.__name__}", exc_info=True)
            raise QueryError()


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
            specification_id = data['specification_id']
        except KeyError as ex:
            logger.warning(f"'specification_id' not specified | {self.__class__.__name__}", exc_info=True)
            raise NoParameterSpecified('specification_id')

        if order_id is not None and specification_id is not None:
            try:
                Orders.assemble_specification(order_id, specification_id)
                return Response(data={"correct": True}, status=status.HTTP_202_ACCEPTED)
            except Orders.AssembleError:
                logger.warning(
                    f"Assemble info. Specification id: {specification_id}, order id: {order_id} | "
                    f"{self.__class__.__name__}", exc_info=True)
        else:
            if order_id is None:
                logger.warning(f"order id is not specified | {self.__class__.__name__}")
            if specification_id is None:
                logger.warning(f"specification id is not specified | {self.__class__.__name__}")
            raise NoParameterSpecified()


class OrderDisAssembleSpecificationView(APIView):
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
                Orders.disassemble_specification(order_id, specification_id)
                return Response(data={"correct": True}, status=status.HTTP_202_ACCEPTED)
            except Orders.AssembleError:
                logger.warning(
                    f"Disassemble info. Specification id: {specification_id}, order id: {order_id} | "
                    f"{self.__class__.__name__}", exc_info=True)
        else:
            if order_id is None:
                logger.warning(f"order id is None | {self.__class__.__name__}")
            if specification_id is None:
                logger.warning(f"specification id None | {self.__class__.__name__}")
            raise NoParameterSpecified()


class OrderManageActionView(APIView):
    permission_classes = [IsAuthenticated, StorageWorkerPermission]

    def post(self, request, *args, **kwargs):
        data = request.data

        try:
            order_id = data['id']
        except KeyError as ex:
            logger.warning(f"'id' not specified | {self.__class__.__name__}", exc_info=True)
            raise NoParameterSpecified('id')

        try:
            action = data['action']
        except KeyError as ex:
            logger.warning(f"'action' not specified | {self.__class__.__name__}", exc_info=True)
            raise NoParameterSpecified('action')

        if order_id is not None and action is not None:
            try:
                if action == 'activate':
                    Orders.activate(order_id, request.user)
                elif action == 'deactivate':
                    Orders.deactivate(order_id, request.user)
                elif action == 'confirm':
                    Orders.confirm(order_id, request.user)
                elif action == 'cancel':
                    Orders.cancel(order_id, request.user)
                else:
                    raise WrongParameterValue('action')
            except Orders.ActionError:
                logger.warning(f"Manage action error for order with id: {order_id} | {self.__class__.__name__}")
                raise StatusError()
            return Response(data={'correct': True}, status=status.HTTP_202_ACCEPTED)
        else:
            if order_id is None:
                logger.warning(f"id id is None| {self.__class__.__name__}")
            if action is None:
                logger.warning(f"action is none | {self.__class__.__name__}")
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
            logger.warning(f"'ids' not specified | {self.__class__.__name__}")
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
        logger.info(f"Received order {request.data} | {self.__class__.__name__}")
        try:
            self.create(request, *args, **kwargs)
            return Response(data={'received': True}, status=status.HTTP_202_ACCEPTED)
        except Exception as ex:
            return Response(data={'received': False}, status=status.HTTP_400_BAD_REQUEST)

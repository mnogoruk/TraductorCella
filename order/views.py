import logging

from django.http import Http404
from rest_framework import status
from rest_framework.authentication import BasicAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.generics import RetrieveAPIView, ListAPIView, CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from order.serializer import OrderSerializer, OrderDetailSerializer
from order.service import Orders
from utils.exception import NoParameterSpecified, WrongParameterValue, WrongParameterType, QueryError, StatusError
from utils.pagination import StandardResultsSetPagination
from authentication.permissions import OfficeWorkerPermission, StorageWorkerPermission, DefaultPermission

logger = logging.getLogger(__name__)


class OrderDetailView(RetrieveAPIView):
    serializer_class = OrderDetailSerializer
    permission_classes = [DefaultPermission]

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
    permission_classes = [DefaultPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [SearchFilter, OrderingFilter, DjangoFilterBackend]
    filterset_fields = ['status']
    search_fields = ['external_id', 'id', 'source__name']
    ordering = 'status'
    ordering_fields = [
        'external_id',
        'source__name',
        'status',
        'created_at'
    ]

    def get_queryset(self):
        try:
            return Orders.list()
        except Orders.QueryError:
            logger.warning(f"Queryset error | {self.__class__.__name__}", exc_info=True)
            raise QueryError()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            page = Orders.add_assembling_info(page)
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class OrderManageActionView(APIView):
    permission_classes = [StorageWorkerPermission]

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
                if action == 'confirm':
                    order = Orders.get(order_id)
                    Orders.confirm(order, request.user)
                    Orders.notify_new_status(order)
                elif action == 'cancel':
                    order = Orders.get(order_id)
                    Orders.cancel(order, request.user)
                    Orders.notify_new_status(order)
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
    permission_classes = [DefaultPermission]

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
    permission_classes = [OfficeWorkerPermission]

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
    permission_classes = [OfficeWorkerPermission]

    def perform_create(self, serializer):
        return serializer.save(request=self.request)


class ReceiveOrderView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (BasicAuthentication,)

    def post(self, request, *args, **kwargs):

        logger.info(f"Received order {request.data} | {self.__class__.__name__}")
        data = request.data
        external_id = data['ID']

        try:
            if 'create' in data:
                specifications = data['products']
                products = []

                for specification in specifications:
                    product = dict(product_id=specification['id'], amount=specification['amount'])
                    products.append(product)

                Orders.create(external_id=external_id, source='bitrix', products=products)
            elif 'ship' in data:
                Orders.confirm(external_id)
            elif 'cancel' in data:
                Orders.cancel(external_id)
            elif 'change' in data:

                specifications = data['products']
                products = []

                for specification in specifications:
                    product = dict(product_id=specification['id'], amount=specification['amount'])
                    products.append(product)

                Orders.change(external_id=external_id, products=products)

            return Response(data={'received': True}, status=status.HTTP_202_ACCEPTED)
        except Exception as ex:
            return Response(data={'received': False}, status=status.HTTP_400_BAD_REQUEST)

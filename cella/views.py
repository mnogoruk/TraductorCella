from django.db import transaction, DatabaseError
from django.http import Http404
from rest_framework import filters, status
from rest_framework.generics import CreateAPIView, RetrieveAPIView, ListAPIView, RetrieveUpdateAPIView, UpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
import pandas as pd

from .service import Resources, Specifications, Orders
from .serializer import ResourceSerializer, ResourceActionSerializer, ResourceWithUnverifiedCostSerializer, \
    SpecificationDetailSerializer, SpecificationListSerializer, ResourceShortSerializer, ProviderSerializer, \
    SpecificationCategorySerializer, SpecificationEditSerializer, FileSerializer, OrderSerializer, OderListSerializer
from .models import Resource, Specification
from .utils.pagination import StandardResultsSetPagination
from .utils.exceptions import NoParameterSpecified, ParameterExceptions, WrongParameterType, WrongParameterValue, \
    CreateException
import logging
from .models import Test1, Test2

logger = logging.getLogger(__name__)


# Resources
class ResourceDetailView(RetrieveAPIView):
    serializer_class = ResourceSerializer

    def get_object(self):
        r_id = self.kwargs['r_id']
        try:
            resource = Resources.detail(r_id)
        except Resource.DoesNotExist:
            logger.warning(f"Can`t get object 'Resource' with id: {r_id}.")
            raise Http404()
        self.check_object_permissions(request=self.request, obj=resource)

        return resource


class ResourceCreateView(CreateAPIView):
    serializer_class = ResourceSerializer

    def perform_create(self, serializer):
        serializer.save(request=self.request)


class ResourceUpdateView(UpdateAPIView):
    serializer_class = ResourceSerializer

    def perform_update(self, serializer):
        serializer.save(request=self.request)

    def get_object(self):
        r_id = self.kwargs['r_id']
        try:
            resource = Resources.get(r_id)
        except Resource.DoesNotExist:
            logger.warning("Can`t get object 'Resource'.")
            raise Http404()
        self.check_object_permissions(request=self.request, obj=resource)

        return resource


class ResourceWithUnverifiedCostsView(ListAPIView):
    serializer_class = ResourceWithUnverifiedCostSerializer

    def get_queryset(self):
        return Resources.with_unverified_cost()


class ResourceListView(ListAPIView):
    serializer_class = ResourceSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
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
        return Resources.list()


class ResourceActionsView(ListAPIView):
    serializer_class = ResourceActionSerializer

    def get_queryset(self):
        return Resources.actions(self.kwargs['r_id'])


class ResourceShortListView(ListAPIView):
    serializer_class = ResourceShortSerializer

    def get_queryset(self):
        return Resources.shortlist()


class ResourceSetCostView(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            r_id = data['id']
        except KeyError as ex:
            logger.warning(f"'{'id'}' not specified")
            raise NoParameterSpecified('id')
        try:
            value = data['cost']
        except KeyError as ex:
            logger.warning(f"'{'cost'}' not specified")
            raise NoParameterSpecified('cost')
        if value is not None:

            cost, _ = Resources.set_cost(r_id, value, request.user)
            return Response(data={'id': r_id, 'cost': cost.value}, status=status.HTTP_202_ACCEPTED)
        else:
            raise NoParameterSpecified()


class ResourceAddAmountView(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            r_id = data['id']
        except KeyError as ex:
            logger.warning(f"'{'id'}' not specified")
            raise NoParameterSpecified('id')
        try:
            logger.warning(f"'{'amount'}' not specified")
            delta_amount = data['amount']
        except KeyError as ex:
            raise NoParameterSpecified('amount')
        amount, _ = Resources.change_amount(r_id, delta_amount, user=request.user)
        return Response(data={'id': r_id, 'amount': amount}, status=status.HTTP_202_ACCEPTED)


class ResourceVerifyCostView(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            ids = data['ids']
        except KeyError as ex:
            raise NoParameterSpecified('ids')
        if not isinstance(ids, list):
            raise ParameterExceptions(detail="'ids' must be list object.")
        if ids is not None:
            Resources.verify_cost(ids, request.user)
            return Response(data={'correct': True}, status=status.HTTP_202_ACCEPTED)
        else:
            raise NoParameterSpecified()


class ProviderListView(ListAPIView):
    serializer_class = ProviderSerializer

    def get_queryset(self):
        return Resources.providers()


# TODO: ...
class ResourceExelUploadView(CreateAPIView):
    serializer_class = FileSerializer

    def post(self, request, *args, **kwargs):
        file = request.FILES['file']
        Resources.create_from_excel(file, request.user)

        return super().post(request, *args, **kwargs)


class ResourceBulkDeleteView(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            ids = data['ids']
        except KeyError as ex:
            raise NoParameterSpecified('ids')
        if not isinstance(ids, list):
            raise ParameterExceptions(detail="'ids' must be list object.")
        Resources.bulk_delete(ids, request.user)
        return Response(data={'correct': True}, status=status.HTTP_202_ACCEPTED)


# Specifications
class SpecificationCategoryListView(ListAPIView):
    serializer_class = SpecificationCategorySerializer

    def get_queryset(self):
        return Specifications.categories()


class SpecificationDetailView(RetrieveAPIView):
    serializer_class = SpecificationDetailSerializer

    def get_object(self):
        s_id = self.kwargs['s_id']
        try:
            specification = Specifications.detail(s_id)
        except Specification.DoesNotExist:
            raise Http404()
        self.check_object_permissions(request=self.request, obj=specification)

        return specification


class SpecificationListView(ListAPIView):
    serializer_class = SpecificationListSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return Specifications.list()


class SpecificationCreateView(CreateAPIView):
    serializer_class = SpecificationDetailSerializer

    def perform_create(self, serializer):
        return serializer.save(request=self.request)

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class SpecificationEditView(RetrieveUpdateAPIView):
    serializer_class = SpecificationEditSerializer

    def perform_update(self, serializer):
        return serializer.save(user=self.request.user)

    def get_object(self):
        return Specification.objects.get(id=self.kwargs['s_id'])


class SpecificationSetPriceView(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            s_id = data['id']
        except KeyError as ex:
            raise NoParameterSpecified('id')
        try:
            value = data['price']
        except KeyError as ex:
            raise NoParameterSpecified('price')

        if value is not None and s_id is not None:
            Specifications.set_price(specification=s_id, price=value, user=request.user)
            return Response(data={'id': s_id, 'price': value}, status=status.HTTP_202_ACCEPTED)
        else:
            raise NoParameterSpecified()


class SpecificationSetCoefficientView(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            s_id = data['id']
        except KeyError as ex:
            raise NoParameterSpecified('id')
        try:
            value = data['coefficient']
        except KeyError as ex:
            raise NoParameterSpecified('coefficient')
        if value is not None and s_id is not None:
            Specifications.set_coefficient(specification=s_id, coefficient=value, user=request.user)
            return Response(data={'id': s_id, 'coefficient': value}, status=status.HTTP_202_ACCEPTED)
        else:
            raise NoParameterSpecified()


class SpecificationSetCategoryView(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            ids = data['ids']
        except KeyError as ex:
            raise NoParameterSpecified('ids')
        if not isinstance(ids, list):
            raise ParameterExceptions(detail="'ids' must be list object.")
        try:
            category = data['category']
        except KeyError as ex:
            raise NoParameterSpecified('category')
        Specifications.set_category_many(ids, category, request.user)
        return Response(data={'correct': True}, status=status.HTTP_202_ACCEPTED)


class SpecificationAssembleInfoView(APIView):

    def get(self, request, *args, **kwargs):
        s_id = self.kwargs['s_id']
        assembling_amount = Specifications.assemble_info(s_id)

        return Response(data={'assembling_amount': assembling_amount}, status=status.HTTP_200_OK)


class SpecificationBuildSetView(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            s_id = data['id']
        except KeyError as ex:
            raise NoParameterSpecified(detail='id not specified.')
        try:
            amount = data['amount']
        except KeyError as ex:
            raise NoParameterSpecified(detail='amount not specified.')

        from_resources = data.get('from_resources', False)

        Specifications.build_set(s_id, amount, from_resources, user=request.user)
        return Response(data={'correct': True}, status=status.HTTP_202_ACCEPTED)


class SpecificationBulkDeleteView(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            ids = data['ids']
        except KeyError as ex:
            raise NoParameterSpecified('ids')
        if not isinstance(ids, list):
            raise ParameterExceptions(detail="'ids' must be list object.")
        Specifications.bulk_delete(ids, request.user)
        return Response(data={'correct': True}, status=status.HTTP_202_ACCEPTED)


class SpecificationCreateCategoryView(CreateAPIView):
    serializer_class = SpecificationCategorySerializer


# Orders
class OrderDetailView(RetrieveAPIView):
    serializer_class = OrderSerializer

    def get_object(self):
        return Orders.detail(self.kwargs.get('o_id'))


class OrderListView(ListAPIView):
    serializer_class = OderListSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return Orders.list()


class OrderAssembleSpecificationView(APIView):

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
            Orders.assemble_specification(order_id, specification_id)
            return Response(data={"correct": True}, status=status.HTTP_202_ACCEPTED)
        else:
            raise NoParameterSpecified()


class OrderDisAssembleSpecificationView(APIView):

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

    def get(self, request, *args, **kwargs):
        o_id = self.kwargs.get('o_id')
        miss_specification, miss_resources = Orders.assembling_info(o_id)
        return Response(data={'missing_specification': miss_specification,
                              'missing_resources': miss_resources},
                        status=status.HTTP_200_OK)


class OrderBulkDeleteView(APIView):

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

    def perform_create(self, serializer):
        return serializer.save(request=self.request)


class TestView(APIView):

    def get(self, request, *args, **kwargs):
        with transaction.atomic():
            t1 = Test1.objects.create(test='ew', var=23)
            t2 = Test2(tt='1', bb=2.3, v=t1)
            t3 = Test2(tt='2', bb=4.2, v=t1)
            a = [t2, t3]
            Test2.objects.bulk_create(a)

        return Response(data={"da": "yes"}, status=status.HTTP_200_OK)

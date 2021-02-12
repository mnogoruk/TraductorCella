from django.db import transaction
from django.http import Http404
from rest_framework import filters, status
from rest_framework.generics import CreateAPIView, RetrieveAPIView, ListAPIView, RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
import pandas as pd

from .service import Resources, Specifications, Orders
from .serializer import ResourceSerializer, ResourceActionSerializer, ResourceWithUnverifiedCostSerializer, \
    SpecificationDetailSerializer, SpecificationListSerializer, ResourceShortSerializer, ProviderSerializer, \
    SpecificationCategorySerializer, SpecificationEditSerializer, FileSerializer, OrderSerializer
from .models import Resource, Specification
from .utils.pagination import StandardResultsSetPagination
from .utils.exceptions import NoParameter


# Resources
class ResourceDetailView(RetrieveAPIView):
    serializer_class = ResourceSerializer

    def get_object(self):
        r_id = self.kwargs['r_id']
        try:
            resource = Resources.detail(r_id)
        except Resource.DoesNotExist:
            raise Http404()
        self.check_object_permissions(request=self.request, obj=resource)

        return resource


class ResourceCreateView(CreateAPIView):
    serializer_class = ResourceSerializer

    def perform_create(self, serializer):
        serializer.save(request=self.request)


class ResourceUpdateView(RetrieveUpdateAPIView):
    serializer_class = ResourceSerializer

    def perform_update(self, serializer):
        serializer.save(request=self.request)

    def get_object(self):
        r_id = self.kwargs['r_id']
        try:
            resource = Resources.detail(r_id)
        except Resource.DoesNotExist:
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
        r_id = data.get('id', None)
        value = data.get('cost', None)
        if value is not None:

            cost = Resources.set_cost(r_id, value, request.user)
            return Response(data={'id': r_id, 'cost': cost.value}, status=status.HTTP_202_ACCEPTED)
        else:
            raise NoParameter()


class ResourceAddAmountView(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        r_id = data.get('id')
        delta_amount = data.get('amount')
        amount = Resources.change_amount(r_id, delta_amount, user=request.user)
        return Response(data={'id': r_id, 'amount': amount.value}, status=status.HTTP_202_ACCEPTED)


class ResourceVerifyCostView(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        r_id = data.get('id', None)
        value = data.get('verify', None)
        if value is not None:

            Resources.verify_cost(r_id, request.user)
            return Response(data={'id': r_id, 'verified': True}, status=status.HTTP_202_ACCEPTED)
        else:
            raise NoParameter()


class ProviderListView(ListAPIView):
    serializer_class = ProviderSerializer

    def get_queryset(self):
        return Resources.providers()


class ResourceExelUploadView(CreateAPIView):
    serializer_class = FileSerializer

    def post(self, request, *args, **kwargs):
        file = request.FILES['file']
        excel = pd.read_excel(file)
        print(excel)
        try:
            data = []
            for row in range(excel.shape[0]):
                r = excel.iloc[row]
                data.append({
                    'resource_name': r['Название'].strip(),
                    'external_id': r['ID'].strip(),
                    'cost_value': float(r['Цена']),
                    'amount_value': float(r['Количество']),
                    'provider_name': r['Поставщик'].strip()
                })
            Resources.bulk_create(data=data, user=request.user)
        except Exception as ex:
            return Response(data={'detail': 'Ошибка обработки файла'},
                            status=status.HTTP_400_BAD_REQUEST)

        return super().post(request, *args, **kwargs)


class ResourceBulkDeleteView(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        ids = data['ids']
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
        s_id = data.get('id', None)
        value = data.get('price', None)
        if value is not None and s_id is not None:
            Specifications.set_price(specification=s_id, price=value, user=request.user)
            return Response(data={'id': s_id, 'price': value}, status=status.HTTP_202_ACCEPTED)
        else:
            raise NoParameter()


class SpecificationSetCoefficientView(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        s_id = data.get('id', None)
        value = data.get('coefficient', None)
        if value is not None and s_id is not None:
            Specifications.set_coefficient(specification=s_id, coefficient=value, user=request.user)
            return Response(data={'id': s_id, 'coefficient': value}, status=status.HTTP_202_ACCEPTED)
        else:
            raise NoParameter()


class SpecificationSetCategoryView(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        s_ids = data['ids']
        category = data['category']
        Specifications.set_category(s_ids, category)
        return Response(data={'correct': True}, status=status.HTTP_202_ACCEPTED)


class SpecificationAssembleInfoView(APIView):

    def get(self, request, *args, **kwargs):
        s_id = self.kwargs['s_id']
        assembling_amount = Specifications.assemble_info(s_id)

        return Response(data={'assembling_amount': assembling_amount}, status=status.HTTP_200_OK)


class SpecificationBuildSetView(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data

        s_id = data.get('id')
        amount = data.get('amount')
        from_resources = data.get('from_resources', False)

        Specifications.build_set(s_id, amount, from_resources, user=request.user)
        return Response(data={'correct': True}, status=status.HTTP_202_ACCEPTED)


class SpecificationBulkDeleteView(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        ids = data['ids']
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
    serializer_class = OrderSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return Orders.list()


class OrderAssembleSpecificationView(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        order_id = data.get('order_id', None)
        specification_id = data.get('specification_id', None)
        if order_id is not None and specification_id is not None:
            Orders.assemble_specification(order_id, specification_id)
            return Response(data={"correct": True}, status=status.HTTP_202_ACCEPTED)
        else:
            raise NoParameter()


class OrderDisAssembleSpecificationView(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        order_id = data.get('order_id', None)
        specification_id = data.get('specification_id', None)
        if order_id is not None and specification_id is not None:
            Orders.disassemble_specification(order_id, specification_id)
            return Response(data={"correct": True}, status=status.HTTP_202_ACCEPTED)
        else:
            raise NoParameter()


class OrderManageActionView(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        order_id = data.get('id', None)
        action = data.get('action', None)
        if order_id is not None and action is not None:
            if action == 'activate':
                Orders.activate(order_id, request.user)
            elif action == 'deactivate':
                Orders.deactivate(order_id, request.user)
            elif action == 'confirm':
                Orders.confirm(order_id, request.user)
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            return Response(data={'correct': True}, status=status.HTTP_202_ACCEPTED)
        else:
            raise NoParameter()


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
        ids = data['ids']
        Orders.bulk_delete(ids, request.user)
        return Response(data={'correct': True}, status=status.HTTP_202_ACCEPTED)


class OrderCreateView(CreateAPIView):
    serializer_class = OrderSerializer

    def perform_create(self, serializer):
        return serializer.save(request=self.request)

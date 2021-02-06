from django.http import Http404
from rest_framework import filters, status
from rest_framework.generics import CreateAPIView, RetrieveAPIView, ListAPIView, RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
import pandas as pd

from .service import Resources, Specifications
from .serializer import ResourceSerializer, ResourceActionSerializer, ResourceWithUnverifiedCostSerializer, \
    SpecificationDetailSerializer, SpecificationListSerializer, ResourceShortSerializer, ProviderSerializer, \
    SpecificationCategorySerializer, SpecificationEditSerializer, FileSerializer
from .models import Resource, Specification
from .utils.pagination import StandardResultsSetPagination
from .utils.exceptions import NoParameter


class ResourceDetailView(RetrieveAPIView):
    serializer_class = ResourceSerializer

    def get_object(self):
        r_id = self.kwargs['r_id']
        service = Resources(self.request)
        try:
            resource = service.detail(r_id)
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
        service = Resources(self.request)
        try:
            resource = service.detail(r_id)
        except Resource.DoesNotExist:
            raise Http404()
        self.check_object_permissions(request=self.request, obj=resource)

        return resource


class ResourceWithUnverifiedCostsView(ListAPIView):
    serializer_class = ResourceWithUnverifiedCostSerializer

    def get_queryset(self):
        service = Resources(self.request)
        return service.with_unverified_cost()


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
        service = Resources(self.request)
        return service.list()


class ResourceActionsView(ListAPIView):
    serializer_class = ResourceActionSerializer

    def get_queryset(self):
        service = Resources(self.request)

        return service.actions(self.kwargs['r_id'])


class ResourceShortListView(ListAPIView):
    serializer_class = ResourceShortSerializer

    def get_queryset(self):
        service = Resources(self.request)
        return service.shortlist()


class SpecificationDetailView(RetrieveAPIView):
    serializer_class = SpecificationDetailSerializer

    def get_object(self):
        s_id = self.kwargs['s_id']
        service = Specifications(self.request)
        try:
            specification = service.detail(s_id)
        except Specification.DoesNotExist:
            raise Http404()
        self.check_object_permissions(request=self.request, obj=specification)

        return specification


class SpecificationListView(ListAPIView):
    serializer_class = SpecificationListSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        service = Specifications(self.request)

        return service.list()


class ResourceSetCost(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        r_id = data.get('id', None)
        value = data.get('cost', None)
        if value is not None:
            service = Resources(request)
            cost, _ = service.set_cost(r_id, value)
            return Response(data={'cost': cost.value}, status=status.HTTP_202_ACCEPTED)
        else:
            raise NoParameter()


class ResourceAddAmount(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        r_id = data.get('id')
        delta_amount = data.get('amount')
        service = Resources(request)
        amount, _ = service.change_amount(r_id, delta_amount)
        return Response(data={'amount': amount.value}, status=status.HTTP_202_ACCEPTED)


class ResourceVerifyCost(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        r_id = data.get('id', None)
        value = data.get('verify', None)
        if value is not None:
            service = Resources(request)
            service.verify_cost(r_id)
            return Response(data={'verified': True}, status=status.HTTP_202_ACCEPTED)
        else:
            raise NoParameter()


class ProviderListView(ListAPIView):
    serializer_class = ProviderSerializer

    def get_queryset(self):
        service = Resources(self.request)

        return service.providers()


class SpecificationCategoryListView(ListAPIView):
    serializer_class = SpecificationCategorySerializer

    def get_queryset(self):
        service = Specifications(self.request)
        return service.categories()


class SpecificationCreateView(CreateAPIView):
    serializer_class = SpecificationDetailSerializer

    def perform_create(self, serializer):
        return serializer.save(request=self.request)


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
            Specifications.set_price(s_id=s_id, price=value)
            return Response(data={'price': value}, status=status.HTTP_202_ACCEPTED)
        else:
            raise NoParameter()


class SpecificationSetCoefficientView(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        s_id = data.get('id', None)
        value = data.get('coefficient', None)
        if value is not None and s_id is not None:
            Specifications.set_coefficient(s_id=s_id, coefficient=value)
            return Response(data={'coefficient': value}, status=status.HTTP_202_ACCEPTED)
        else:
            raise NoParameter()


class ResourceExelUpload(CreateAPIView):
    serializer_class = FileSerializer

    def post(self, request, *args, **kwargs):
        file = request.FILES['file']
        excel = pd.read_excel(file)
        try:
            data = []
            for row in range(excel.shape[0]):
                r = excel.iloc[row]
                data.append({
                    'resource_name': r['Наименование'].strip(),
                    'external_id': r['ID'].strip(),
                    'cost_value': float(r['Цена']),
                    'amount_value': float(r['Количество']),
                    'provider_name': r['Поставщик'].strip()
                })
            service = Resources(request)
            service.bulk_create(data=data)
        except Exception as ex:
            return Response(data={'detail': 'Ошибка обработки файла'},
                            status=status.HTTP_400_BAD_REQUEST)
        return super().post(request, *args, **kwargs)

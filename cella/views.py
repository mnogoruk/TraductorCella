from django.http import Http404
from rest_framework import filters, status
from rest_framework.generics import CreateAPIView, RetrieveAPIView, ListAPIView, RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .generic.views import ForRawQueryViewMixin
from .service import Resources, Specifications
from .serializer import ResourceSerializer, ResourceActionSerializer, ResourceWithUnverifiedCostSerializer, \
    SpecificationDetailSerializer, SpecificationListSerializer, ResourceShortListSerializer, ProviderSerializer, \
    SpecificationCategorySerializer
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


class ResourceListView(ListAPIView, ForRawQueryViewMixin):
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
    serializer_class = ResourceShortListSerializer

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

    def get_queryset(self):
        service = Specifications(self.request)

        return service.list()


class ResourceSetCost(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        r_id = kwargs.get('r_id')
        value = data.get('cost', None)
        if value is not None:
            service = Resources(request)
            cost, _ = service.set_cost(r_id, value)
            return Response(data={'cost': cost.value}, status=status.HTTP_202_ACCEPTED)
        else:
            raise NoParameter()


class ResourceVerifyCost(APIView):

    def post(self, request, *args, **kwargs):
        data = request.data
        r_id = kwargs.get('r_id')
        value = data.get('verify', None)
        if value is not None:
            service = Resources(request)
            print(service.verify_cost(r_id))
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

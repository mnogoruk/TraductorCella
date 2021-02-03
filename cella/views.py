from django.http import Http404
from rest_framework import filters
from rest_framework.generics import CreateAPIView, RetrieveAPIView, UpdateAPIView, ListAPIView, RetrieveUpdateAPIView

from .generic.views import ForRawQueryViewMixin
from .service import Resources
from .serializer import ResourceSerializer, ResourceActionSerializer, ResourceWithUnverifiedCostSerializer
from .models import Resource
from .utils.pagination import StandardResultsSetPagination


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

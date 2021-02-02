from django.http import Http404
from rest_framework.generics import CreateAPIView, RetrieveAPIView, UpdateAPIView, ListAPIView

from .service import Resources
from .serializer import ResourceSerializer, ResourceActionSerializer
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


class ResourceUpdateView(UpdateAPIView):
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


class ResourceListView(ListAPIView):
    serializer_class = ResourceSerializer
    pagination_class = StandardResultsSetPagination
    ordering_fields = {
        'name',
        'last_change_amount',
        'last_change_cost',
        'cost',
        'amount',
        'provider_name',
        'external_id',
        'id'
    }
    searching_fields = {
        'name',
        'external_id',
        'provider_name',
        'id'
    }

    def searching_expression(self, searching):
        searching_exp = f" LIKE '%{searching}%' OR ".join(self.searching_fields) + f" LIKE '%{searching}%'"
        return searching_exp

    def ordering_expression(self, ordering):
        ordering = ordering.strip(',').split(',')
        order_exp = []
        for ordering_field in ordering:

            if ordering_field.startswith('-'):
                ordering_field = ordering_field.replace('-', '')

                if ordering_field in self.ordering_fields:
                    order_exp.append(f"{ordering_field} DESC")

            if ordering_field in self.ordering_fields:
                order_exp.append(f"{ordering_field}")
        return order_exp

    def get_queryset(self):
        service = Resources(self.request)
        ordering = self.request.query_params.get('ordering', None)
        searching = self.request.query_params.get('searching', None)
        filtering = self.request.query_params.get('filtering', None)

        if ordering is not None:
            ordering = self.ordering_expression(ordering)

        if searching is not None:
            searching = self.searching_expression(searching)

        return service.list(ordering=ordering, searching=searching)


class ResourceActionsView(ListAPIView):
    serializer_class = ResourceActionSerializer

    def get_queryset(self):
        service = Resources(self.request)

        return service.actions(self.kwargs['r_id'])

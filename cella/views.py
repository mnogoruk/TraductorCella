from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render

# Create your views here.
from django.urls import reverse
from rest_framework.decorators import api_view
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView, RetrieveAPIView, UpdateAPIView, ListAPIView

from .service import Resources
from .serializer import ResourceSerializer, ResourceActionSerializer
from .models import Resource


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

    def get_queryset(self):
        service = Resources(self.request)

        return service.list()


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 10


class ResourceActionsView(ListAPIView):
    serializer_class = ResourceActionSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        service = Resources(self.request)

        return service.actions(self.kwargs['r_id'])

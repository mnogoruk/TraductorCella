from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render

# Create your views here.
from django.urls import reverse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView, RetrieveAPIView, UpdateAPIView

from .service import Resources
from .serializer import ResourceDetailSerializer, ResourceEditSerializer
from .models import Resource


class ResourceDetailView(RetrieveAPIView):
    serializer_class = ResourceDetailSerializer

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
    serializer_class = ResourceDetailSerializer

    def perform_create(self, serializer):
        serializer.save(request=self.request)


class ResourceUpdateView(UpdateAPIView):
    serializer_class = ResourceEditSerializer

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

# def resources(request):
#     if request.method == 'POST':
#         resources_to_change_amount = []
#         resources_to_change_price = []
#         for form in ResourceStoragePriceFormSet(request.POST):
#             if form.is_valid():
#                 cd = form.cleaned_data
#                 if len(cd) != 0:
#                     print(cd['new_cost'])
#                     if cd['new_cost'] is not None:
#                         resources_to_change_price.append((cd['external_id'], cd['new_cost']))
#                     if cd['delta_amount'] is not None:
#                         resources_to_change_amount.append((cd['external_id'], cd['delta_amount']))
#         print(resources_to_change_price)
#         Resources.set_new_costs(list(map(lambda x: x[0], resources_to_change_price)),
#                                 list(map(lambda x: float(x[1]), resources_to_change_price)),
#                                 user=None)
#         Resources.change_amount(list(map(lambda x: x[0], resources_to_change_amount)),
#                                 list(map(lambda x: x[1], resources_to_change_amount)),
#                                 user=None)
#
#     return render(request, 'resources.html',
#                   context={'resources': Resources.resource_list(), 'form': ResourceStoragePriceFormSet()})
#
#
# def specification(request, spec_id):
#     spec, res = Specifications.specification(spec_id)
#     return render(request, 'specification_detail.html',
#                   context={'specification': spec, 'resources': res})
#
#
# def specifications(request):
#     return render(request, 'specifications.html', context={'specifiactions': Specifications.specification_list()})
#
#
# def resource_detail(request, r_id):
#     history, resource = Resources.resource(r_id)
#     return render(request, 'resource_detail.html', context={'resource': resource, 'history': history})
#
#
# def resource_create(request):
#     if request.method == 'POST':
#         form = ResourceCreateForm(request.POST)
#         if form.is_valid():
#             data = form.cleaned_data
#             Resources.resource_create(resource_name=data.get('resource_name'),
#                                       external_id=data.get('external_id'),
#                                       cost=float(data.get('cost')),
#                                       amount=float(data.get('amount')),
#                                       provider_name=data.get('provider_name').provider_name,
#                                       user=request.user)
#         return HttpResponseRedirect(reverse('resource_list'))
#     else:
#         return render(request, 'resource_create.html', context={'form': ResourceCreateForm()})
#
#
# def resource_edit(request, r_id):
#     if request.method == 'POST':
#         _, resource = Resources.resource(r_id)
#         form = ResourceEditForm(data=request.POST)
#         if form.is_valid():
#             data = form.cleaned_data
#             Resources.resource_edit(r_id,
#                                     resource_name=data.get('resource_name'),
#                                     external_id=data.get('external_id'),
#                                     cost=float(data.get('cost')),
#                                     amount=float(data.get('amount')),
#                                     provider_name=data.get('provider_name').provider_name,
#                                     user=request.user)
#         return HttpResponseRedirect(reverse('resource_list'))
#     else:
#         _, resource = Resources.resource(r_id)
#         form = ResourceEditForm(initial={
#             'resource_name': resource.resource_name,
#             'external_id': resource.external_id,
#             'cost': resource.cost,
#             'amount': resource.amount,
#             'provider_name': resource.resource_provider.provider_name
#         })
#         return render(request, 'resource_create.html', context={'form': form})
#
#
# def resource_unverified(request):
#     return render(request, 'resource_unverified.html', context={'resources': Verify.unverified_resources()})
#
#
# def specification_create(request):
#     if request.method == 'POST':
#         specification_form = SpecificationCreateForm(request.POST)
#         resources_specification_formset = SpecificationResourceFormSet(request.POST)
#         if specification_form.is_valid() and resources_specification_formset.is_valid():
#             spec_data = specification_form.cleaned_data
#             spec_data['resources'] = []
#             for resource in resources_specification_formset.cleaned_data:
#                 if len(resource) == 0:
#                     break
#                 spec_data['resources'].append({'amount': float(resource['amount']), 'id': resource['resource'].id})
#             print(spec_data)
#             Specifications.specification_create(
#                 specification_name=spec_data['specification_name'],
#                 product_id=spec_data['product_id'],
#                 category_name=spec_data['category_name'].category_name,
#                 coefficient=spec_data['coefficient'],
#                 use_category_coefficient=spec_data['use_category_coefficient'],
#                 is_active=spec_data['is_active'],
#                 resources=spec_data['resources'])
#         return HttpResponseRedirect(reverse('specification_list'))
#     else:
#         return render(request, 'specification_create.html',
#                       context={'form': SpecificationCreateForm, 'forms': SpecificationResourceFormSet()})
#
#
# def specification_unverified(request):
#     return render(request, 'specification_unverified.html', context={'specs': Verify.unverified_specifications(), 'res': Verify.unverified_resources()})

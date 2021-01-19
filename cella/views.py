from django.shortcuts import render

# Create your views here.
from .service import Resources, Specifications
from .forms import ResourceStoragePriceFormSet


def resources(request):
    if request.method == 'POST':
        resources_to_change_amount = []
        resources_to_change_price = []
        for form in ResourceStoragePriceFormSet(request.POST):
            if form.is_valid():
                cd = form.cleaned_data
                if len(cd) != 0:
                    if cd['new_price'] is not None:
                        resources_to_change_price.append((cd['external_id'], cd['new_price']))
                    if cd['delta_amount'] is not None:
                        resources_to_change_amount.append((cd['external_id'], cd['delta_amount']))
        Resources.set_new_costs(list(map(lambda x: x[0], resources_to_change_price)),
                                list(map(lambda x: float(x[1]), resources_to_change_price)),
                                user=None)
        Resources.change_amount(list(map(lambda x: x[0], resources_to_change_amount)),
                                list(map(lambda x: x[1], resources_to_change_amount)),
                                user=None)

    return render(request, 'resources.html',
                  context={'resources': Resources.resource_list(), 'form': ResourceStoragePriceFormSet()})


def specification(request, spec_id):
    spec, res = Specifications.specification(spec_id)
    return render(request, 'specification_detail.html',
                  context={'specification': spec, 'resources': res})


def specifications(request):
    return render(request, 'specifications.html', context={'specifiactions': Specifications.specification_list()})


def resource_detail(request, r_id):
    history, resource = Resources.resource(r_id)
    return render(request, 'resource_detail.html', context={'resource': resource, 'history': history})
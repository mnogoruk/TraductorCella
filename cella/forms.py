from django import forms
from .models import ResourceProvider, SpecificationCategory, Resource


class ResourceStoragePriceForm(forms.Form):
    external_id = forms.CharField(required=False)
    delta_amount = forms.DecimalField(max_digits=8, decimal_places=3, required=False)
    new_cost = forms.DecimalField(max_digits=8, decimal_places=2, required=False)


ResourceStoragePriceFormSet = forms.formset_factory(ResourceStoragePriceForm, extra=999)


class ResourceCreateForm(forms.Form):
    external_id = forms.CharField(required=True)
    resource_name = forms.CharField(required=True)
    cost = forms.DecimalField(required=True)
    provider_name = forms.ModelChoiceField(
        queryset=ResourceProvider.objects.all()
    )
    amount = forms.DecimalField(max_digits=8, decimal_places=2)


class ResourceEditForm(forms.Form):
    external_id = forms.CharField(required=False)
    resource_name = forms.CharField(required=False)
    cost = forms.DecimalField(required=False)
    provider_name = forms.ModelChoiceField(
        queryset=ResourceProvider.objects.all()
    )
    amount = forms.DecimalField(max_digits=8, decimal_places=2)


class SpecificationCreateForm(forms.Form):
    specification_name = forms.CharField(required=True)
    product_id = forms.CharField(required=True)
    category_name = forms.ModelChoiceField(
        queryset=SpecificationCategory.objects.all(),
        required=False
    )
    coefficient = forms.FloatField(required=False)
    use_category_coefficient = forms.BooleanField(required=False)
    is_active = forms.BooleanField(required=False)


class SpecificationResourceForm(forms.Form):
    resource = forms.ModelChoiceField(
        queryset=Resource.objects.all()
    )
    amount = forms.DecimalField(max_digits=8, decimal_places=2)


SpecificationResourceFormSet = forms.formset_factory(SpecificationResourceForm, extra=999)

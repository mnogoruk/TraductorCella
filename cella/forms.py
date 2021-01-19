from django import forms
from .models import ResourceProvider


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

from django import forms


class ResourceStoragePriceForm(forms.Form):
    external_id = forms.CharField(required=False)
    delta_amount = forms.DecimalField(max_digits=8, decimal_places=3, required=False)
    new_price = forms.DecimalField(max_digits=8, decimal_places=2, required=False)


ResourceStoragePriceFormSet = forms.formset_factory(ResourceStoragePriceForm, extra=999)



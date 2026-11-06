from django import forms
from catalog.models import Product

class BulkStockForm(forms.Form):
    note = forms.CharField(required=False, max_length=250, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Optional batch note"}))

class ConsumptionForm(forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.filter(is_active=True), widget=forms.Select(attrs={"class": "form-select"}))
    quantity = forms.DecimalField(min_value=0.001, max_digits=12, decimal_places=3, widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.001"}))
    note = forms.CharField(required=False, max_length=250, widget=forms.TextInput(attrs={"class": "form-control"}))

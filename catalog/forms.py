from django import forms
from django.db import transaction
from .services import generate_sku
from .models import Category, Product
from inventory.models import StockMovement

class CategoryForm(forms.ModelForm):
    sku_prefix = forms.CharField(max_length=8, required=True, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. GR", "maxlength": "8"}))
    def clean_sku_prefix(self):
        import re
        prefix = self.cleaned_data["sku_prefix"].strip().upper()
        if not re.fullmatch(r"[A-Z0-9]{1,8}", prefix):
            raise forms.ValidationError("Use 1–8 letters or numbers only, without spaces or symbols.")
        return prefix

    class Meta:
        model = Category
        fields = ["name", "sku_prefix", "description", "is_active"]
        widgets = {"name": forms.TextInput(attrs={"class": "form-control"}), "description": forms.Textarea(attrs={"class": "form-control", "rows": 3})}

class ProductForm(forms.ModelForm):
    opening_quantity = forms.DecimalField(min_value=0, max_digits=12, decimal_places=3, initial=0, widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.001"}))
    class Meta:
        model = Product
        fields = ["name", "category", "unit", "minimum_quantity", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "sku": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "unit": forms.Select(attrs={"class": "form-select"}),
            "minimum_quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.001"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
    @transaction.atomic
    def save(self, commit=True, user=None):
        product = super().save(commit=False)
        product.created_by = user
        if not product.sku:
            product.sku = generate_sku(product.category)
        product.quantity = self.cleaned_data["opening_quantity"]
        if commit:
            product.save()
            if product.quantity > 0:
                StockMovement.objects.create(
                    product=product, movement_type=StockMovement.Type.OPENING,
                    old_quantity=0, new_quantity=product.quantity,
                    difference=product.quantity, note="Opening stock",
                    created_by=user,
                )
        return product

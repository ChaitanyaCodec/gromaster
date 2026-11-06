from django.contrib import admin
from .models import Category, Product
admin.site.register(Category)
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "category", "quantity", "unit", "minimum_quantity", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name", "sku")

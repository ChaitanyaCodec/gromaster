from django.conf import settings
from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    sku_prefix = models.CharField(max_length=8, unique=True, null=True, blank=True, help_text="Short prefix used for automatic product SKUs, e.g. GR for Grains.")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"
    def __str__(self):
        return self.name

class Product(models.Model):
    class Unit(models.TextChoices):
        KG = "kg", "Kilogram"
        G = "g", "Gram"
        L = "l", "Liter"
        ML = "ml", "Milliliter"
        PCS = "pcs", "Pieces"
        PACK = "pack", "Pack"
        BAG = "bag", "Bag"
        BOX = "box", "Box"

    name = models.CharField(max_length=160)
    sku = models.CharField(max_length=60, unique=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    unit = models.CharField(max_length=12, choices=Unit.choices, default=Unit.KG)
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    minimum_quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_products")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["sku"]), models.Index(fields=["category", "is_active"])]

    def __str__(self):
        return f"{self.name} ({self.sku})"

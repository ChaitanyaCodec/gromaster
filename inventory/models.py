import uuid
from django.conf import settings
from django.db import models
from catalog.models import Product

class StockUpdateBatch(models.Model):
    batch_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    note = models.CharField(max_length=250, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return str(self.batch_id)

class StockMovement(models.Model):
    class Type(models.TextChoices):
        OPENING = "OPENING", "Opening"
        ADJUSTMENT = "ADJUSTMENT", "Stock count adjustment"
        CONSUMPTION = "CONSUMPTION", "Consumption"
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="movements")
    batch = models.ForeignKey(StockUpdateBatch, on_delete=models.SET_NULL, null=True, blank=True, related_name="movements")
    movement_type = models.CharField(max_length=20, choices=Type.choices)
    old_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    new_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    difference = models.DecimalField(max_digits=12, decimal_places=3)
    note = models.CharField(max_length=250, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["product", "-created_at"]), models.Index(fields=["movement_type", "-created_at"])]
    def __str__(self):
        return f"{self.product} {self.difference:+}"

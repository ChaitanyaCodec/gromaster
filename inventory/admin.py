from django.contrib import admin
from .models import StockMovement, StockUpdateBatch
admin.site.register(StockUpdateBatch)
@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("product", "movement_type", "old_quantity", "new_quantity", "difference", "created_by", "created_at")
    list_filter = ("movement_type", "created_at")
    search_fields = ("product__name", "product__sku", "note")
    readonly_fields = ("product", "batch", "movement_type", "old_quantity", "new_quantity", "difference", "note", "created_by", "created_at")

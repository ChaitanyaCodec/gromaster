from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from catalog.models import Product
from .models import StockMovement, StockUpdateBatch

@transaction.atomic
def apply_stock_counts(counts, user, note=""):
    # counts is a mapping: product_id -> counted quantity.
    normalized = {}
    for product_id, quantity in counts.items():
        value = Decimal(str(quantity))
        if value < 0:
            raise ValueError("Stock quantity cannot be negative.")
        normalized[int(product_id)] = value

    products = list(Product.objects.select_for_update().filter(pk__in=normalized, is_active=True).order_by("pk"))
    if len(products) != len(normalized):
        raise ValueError("One or more selected products do not exist or are inactive.")

    batch = StockUpdateBatch.objects.create(created_by=user, note=note)
    now = timezone.now()
    movements = []
    changed = []
    for product in products:
        old = product.quantity
        new = normalized[product.pk]
        if old == new:
            continue
        product.quantity = new
        product.updated_at = now
        changed.append(product)
        movements.append(StockMovement(
            product=product, batch=batch, movement_type=StockMovement.Type.ADJUSTMENT,
            old_quantity=old, new_quantity=new, difference=new-old,
            note=note, created_by=user,
        ))
    if changed:
        Product.objects.bulk_update(changed, ["quantity", "updated_at"])
        StockMovement.objects.bulk_create(movements)
    return batch, len(movements)

@transaction.atomic
def record_consumption(product_id, quantity, user, note=""):
    amount = Decimal(str(quantity))
    if amount <= 0:
        raise ValueError("Consumption quantity must be greater than zero.")
    product = Product.objects.select_for_update().get(pk=product_id, is_active=True)
    if amount > product.quantity:
        raise ValueError(f"Only {product.quantity} {product.unit} is available.")
    old = product.quantity
    product.quantity = old - amount
    product.last_used_at = timezone.now()
    product.save(update_fields=["quantity", "last_used_at", "updated_at"])
    return StockMovement.objects.create(
        product=product, movement_type=StockMovement.Type.CONSUMPTION,
        old_quantity=old, new_quantity=product.quantity, difference=-amount,
        note=note, created_by=user,
    )

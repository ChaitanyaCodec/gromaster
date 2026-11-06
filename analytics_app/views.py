from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import render
from django.utils import timezone
from catalog.models import Product, Category
from inventory.models import StockMovement
from inventory.views import product_status

@login_required
def dashboard(request):
    products = list(Product.objects.filter(is_active=True).select_related("category"))
    statuses = [product_status(p) for p in products]
    movements_30 = StockMovement.objects.filter(created_at__gte=timezone.now()-timedelta(days=30))
    context = {
        "product_count": len(products),
        "category_count": Category.objects.filter(is_active=True).count(),
        "low_count": statuses.count("Low Stock"),
        "out_count": statuses.count("Out of Stock"),
        "unused_count": statuses.count("Unused Stock"),
        "recent_movements": StockMovement.objects.select_related("product", "created_by")[:8],
        "usage_count": movements_30.filter(movement_type=StockMovement.Type.CONSUMPTION).count(),
    }
    return render(request, "analytics/dashboard.html", context)

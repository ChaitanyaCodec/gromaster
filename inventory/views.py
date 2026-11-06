from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import timedelta
from accounts.decorators import manager_required
from catalog.models import Product
from .forms import ConsumptionForm
from .models import StockMovement
from .services import apply_stock_counts, record_consumption

def product_status(product):
    if product.quantity <= 0:
        return "Out of Stock"
    if product.quantity <= product.minimum_quantity:
        return "Low Stock"
    if not product.last_used_at or product.last_used_at < timezone.now() - timedelta(days=30):
        return "Unused Stock"
    return "In Stock"

@manager_required
def inventory_list(request):
    qs = Product.objects.select_related("category").filter(is_active=True)
    search = request.GET.get("q", "").strip()
    if search:
        qs = qs.filter(name__icontains=search) | qs.filter(sku__icontains=search)
    status_filter = request.GET.get("status", "")
    products = list(qs.distinct().order_by("name"))
    rows = [{"product": p, "status": product_status(p)} for p in products]
    if status_filter:
        rows = [r for r in rows if r["status"] == status_filter]
    return render(request, "inventory/list.html", {"rows": rows, "search": search, "status_filter": status_filter})

@manager_required
def bulk_update(request):
    products = Product.objects.filter(is_active=True).order_by("name")
    if request.method == "POST":
        counts = {}
        errors = []
        for product in products:
            key = f"quantity_{product.pk}"
            raw = request.POST.get(key)
            if raw is None or raw == "":
                continue
            try:
                value = Decimal(raw)
                if value < 0:
                    errors.append(f"{product.name}: quantity cannot be negative.")
                else:
                    counts[product.pk] = value
            except (InvalidOperation, ValueError):
                errors.append(f"{product.name}: enter a valid number.")
        if errors:
            for error in errors:
                messages.error(request, error)
        elif not counts:
            messages.warning(request, "Enter at least one counted quantity.")
        else:
            try:
                batch, changed = apply_stock_counts(counts, request.user, request.POST.get("note", "")[:250])
                messages.success(request, f"Batch saved. {changed} product(s) changed. Batch ID: {batch.batch_id}")
                return redirect("inventory:history")
            except ValueError as exc:
                messages.error(request, str(exc))
    return render(request, "inventory/bulk_update.html", {"products": products})

@manager_required
def consume(request):
    form = ConsumptionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            record_consumption(form.cleaned_data["product"].pk, form.cleaned_data["quantity"], request.user, form.cleaned_data["note"])
            messages.success(request, "Consumption recorded and stock updated.")
            return redirect("inventory:list")
        except ValueError as exc:
            form.add_error("quantity", str(exc))
    return render(request, "inventory/consume.html", {"form": form})

@manager_required
def history(request):
    movements = StockMovement.objects.select_related("product", "created_by", "batch")
    paginator = Paginator(movements, 50)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "inventory/history.html", {"page": page})

@manager_required
def alerts(request):
    products = Product.objects.filter(is_active=True)
    low = [p for p in products if 0 < p.quantity <= p.minimum_quantity]
    out = [p for p in products if p.quantity <= 0]
    return render(request, "inventory/alerts.html", {"low": low, "out": out})

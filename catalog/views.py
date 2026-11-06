from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.db import transaction
from decimal import Decimal, InvalidOperation
from io import BytesIO
from openpyxl import Workbook, load_workbook
from accounts.decorators import manager_required
from .forms import CategoryForm, ProductForm
from .models import Category, Product
from .services import generate_sku, get_or_create_import_category
from inventory.models import StockMovement

@manager_required
def category_list(request):
    return render(request, "catalog/category_list.html", {"categories": Category.objects.all()})

@manager_required
def category_create(request):
    form = CategoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        messages.success(request, "Category created.")
        return redirect("catalog:categories")
    return render(request, "catalog/category_form.html", {"form": form, "heading": "Add category"})

@manager_required
def product_list(request):
    products = Product.objects.select_related("category").filter(is_active=True)
    query = request.GET.get("q", "").strip()
    if query:
        products = products.filter(name__icontains=query) | products.filter(sku__icontains=query)
    category_id = request.GET.get("category")
    if category_id:
        products = products.filter(category_id=category_id)
    return render(request, "catalog/product_list.html", {"products": products.distinct(), "categories": Category.objects.filter(is_active=True), "query": query})

@manager_required
def product_create(request):
    form = ProductForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save(user=request.user)
        messages.success(request, "Product created with opening stock.")
        return redirect("catalog:products")
    return render(request, "catalog/product_form.html", {"form": form, "heading": "Add product"})


@manager_required
def product_import_template(request):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Products"
    sheet.append(["Category", "Item Name", "Unit", "Opening Quantity", "Minimum Quantity", "Description"])
    sheet.append(["Grains", "Bajra", "kg", 0, 2, "Pearl millet"])
    sheet.append(["Oils", "Sunflower Oil", "l", 0, 1, ""])
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = "A1:F2"
    for column, width in enumerate([22, 28, 14, 20, 20, 34], start=1):
        sheet.column_dimensions[chr(64 + column)].width = width
    instructions = workbook.create_sheet("Instructions")
    instructions.append(["Gromaster bulk product import"])
    instructions.append(["One product per row. Categories missing from Gromaster are created automatically."])
    instructions.append(["Category matching ignores uppercase/lowercase, extra spaces and punctuation."])
    instructions.append(["Unit values: kg, g, l, ml, pcs, pack, bag, box."])
    instructions.append(["Leave opening/minimum quantity as 0 if not applicable."])
    instructions.append(["SKU is generated automatically from the category prefix."])
    buffer = BytesIO()
    workbook.save(buffer)
    response = HttpResponse(buffer.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="gromaster_product_import_template.xlsx"'
    return response


@manager_required
def product_import(request):
    if request.method == "POST":
        uploaded = request.FILES.get("excel_file")
        if not uploaded:
            messages.error(request, "Choose an Excel file to upload.")
            return redirect("catalog:product_import")
        if not uploaded.name.lower().endswith(".xlsx"):
            messages.error(request, "Please upload an .xlsx Excel file.")
            return redirect("catalog:product_import")
        try:
            workbook = load_workbook(uploaded, read_only=True, data_only=True)
            sheet = workbook["Products"] if "Products" in workbook.sheetnames else workbook.active
            rows = list(sheet.iter_rows(values_only=True))
        except Exception:
            messages.error(request, "The Excel file could not be read. Use the Gromaster template.")
            return redirect("catalog:product_import")

        expected = ["Category", "Item Name", "Unit", "Opening Quantity", "Minimum Quantity", "Description"]
        if not rows or [str(v).strip() if v is not None else "" for v in rows[0][:6]] != expected:
            messages.error(request, "Excel headers do not match the template. Download and use the Gromaster template.")
            return redirect("catalog:product_import")

        parsed, errors = [], []
        valid_units = {value for value, _ in Product.Unit.choices}
        for row_number, row in enumerate(rows[1:], start=2):
            if not row or not any(value not in (None, "") for value in row):
                continue
            values = list(row) + [None] * max(0, 6 - len(row))
            category_name, item_name, unit, opening, minimum, description = values[:6]
            category_name = str(category_name or "").strip()
            item_name = str(item_name or "").strip()
            unit = str(unit or "pcs").strip().lower()
            if not category_name:
                errors.append(f"Row {row_number}: category name is required.")
                continue
            if not item_name:
                errors.append(f"Row {row_number}: item name is required.")
                continue
            if unit not in valid_units:
                errors.append(f"Row {row_number}: invalid unit '{unit}'. Use kg, g, l, ml, pcs, pack, bag or box.")
                continue
            try:
                opening_qty = Decimal(str(opening if opening not in (None, "") else 0))
                minimum_qty = Decimal(str(minimum if minimum not in (None, "") else 0))
                if not opening_qty.is_finite() or not minimum_qty.is_finite() or opening_qty < 0 or minimum_qty < 0:
                    raise InvalidOperation
                if opening_qty.as_tuple().exponent < -3 or minimum_qty.as_tuple().exponent < -3:
                    raise InvalidOperation
            except (InvalidOperation, ValueError):
                errors.append(f"Row {row_number}: quantities must be non-negative numbers with up to 3 decimal places.")
                continue
            parsed.append({
                "row": row_number, "category_name": category_name,
                "name": item_name, "unit": unit, "opening": opening_qty,
                "minimum": minimum_qty, "description": str(description or "").strip(),
            })

        if errors:
            for error in errors[:20]:
                messages.error(request, error)
            if len(errors) > 20:
                messages.error(request, f"{len(errors) - 20} additional row errors were not displayed.")
            return redirect("catalog:product_import")
        if not parsed:
            messages.warning(request, "The workbook contains no product rows.")
            return redirect("catalog:product_import")

        created_categories = set()
        reused_categories = set()
        try:
            with transaction.atomic():
                category_cache = {}
                # Resolve/create all categories in the same transaction as products.
                # Repeated category spellings in this workbook map to one category.
                for entry in parsed:
                    category, was_created = get_or_create_import_category(
                        entry["category_name"], user=request.user, cache=category_cache
                    )
                    entry["category"] = category
                    if was_created:
                        created_categories.add(category.name)
                    else:
                        reused_categories.add(category.name)

                # Lock all involved categories in a stable order while generating SKUs.
                category_ids = sorted({entry["category"].pk for entry in parsed})
                locked_categories = {
                    c.pk: c for c in Category.objects.select_for_update().filter(pk__in=category_ids).order_by("pk")
                }
                for entry in parsed:
                    category = locked_categories[entry["category"].pk]
                    sku = generate_sku(category)
                    product = Product.objects.create(
                        name=entry["name"], sku=sku, category=category, unit=entry["unit"],
                        quantity=entry["opening"], minimum_quantity=entry["minimum"],
                        description=entry["description"], created_by=request.user,
                    )
                    if product.quantity > 0:
                        StockMovement.objects.create(
                            product=product, movement_type=StockMovement.Type.OPENING,
                            old_quantity=0, new_quantity=product.quantity,
                            difference=product.quantity, note="Opening stock imported from Excel",
                            created_by=request.user,
                        )
        except Exception as exc:
            messages.error(request, f"Import was not completed; no rows were saved. Check the workbook and category data. Details: {exc}")
            return redirect("catalog:product_import")

        messages.success(request, f"Successfully imported {len(parsed)} products.")
        if created_categories:
            messages.success(request, "Automatically created categories: " + ", ".join(sorted(created_categories)) + ".")
        if reused_categories:
            messages.info(request, "Reused existing categories (case/spacing/punctuation ignored): " + ", ".join(sorted(reused_categories)) + ".")
        return redirect("catalog:products")

    return render(request, "catalog/product_import.html", {"categories": Category.objects.filter(is_active=True).order_by("name")})

import re
from django.db import transaction
from .models import Category, Product


def _ensure_category_prefix(category):
    prefix = (category.sku_prefix or "").strip().upper()
    if prefix:
        if prefix != category.sku_prefix:
            category.sku_prefix = prefix
            category.save(update_fields=["sku_prefix"])
        return prefix

    # Backfill a sensible prefix for categories created before SKU prefixes existed.
    letters = re.sub(r"[^A-Z0-9]", "", category.name.upper())
    base = (letters[:2] or "CA")
    prefix = base
    suffix = 2
    while Category.objects.exclude(pk=category.pk).filter(sku_prefix=prefix).exists():
        prefix = f"{base[:6]}{suffix}"
        suffix += 1
    category.sku_prefix = prefix
    category.save(update_fields=["sku_prefix"])
    return prefix


@transaction.atomic
def generate_sku(category):
    """Generate the next category-scoped SKU, e.g. GR-003."""
    locked_category = Category.objects.select_for_update().get(pk=category.pk)
    prefix = _ensure_category_prefix(locked_category)
    pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
    highest = 0
    for existing in Product.objects.filter(sku__startswith=f"{prefix}-").values_list("sku", flat=True):
        match = pattern.match(existing)
        if match:
            highest = max(highest, int(match.group(1)))
    return f"{prefix}-{highest + 1:03d}"



def normalize_category_name(name):
    """Normalize case, spaces and punctuation for category matching."""
    return re.sub(r"[^a-z0-9]", "", str(name or "").casefold())


def build_category_prefix(name):
    """Build a readable default prefix: Grains -> GR, Dry Fruits -> DF."""
    words = re.findall(r"[A-Za-z0-9]+", str(name or "").upper())
    if not words:
        base = "CA"
    elif len(words) > 1:
        base = "".join(word[0] for word in words)[:8]
    else:
        base = words[0][:2]
    return base[:8] or "CA"


@transaction.atomic
def get_or_create_import_category(name, user=None, cache=None):
    """
    Reuse an existing category regardless of case/spacing/punctuation.
    Create a category only when no normalized match exists.
    """
    cache = cache if cache is not None else {}
    normalized = normalize_category_name(name)
    if not normalized:
        raise ValueError("Category name cannot be empty.")
    if normalized in cache:
        category = cache[normalized]
        if not category.is_active:
            raise ValueError(f"Category '{category.name}' exists but is inactive. Activate it before importing.")
        return category, False

    # Include inactive categories in matching so an inactive category is never
    # silently duplicated under a different capitalization.
    existing = list(Category.objects.select_for_update().order_by("pk"))
    matches = [c for c in existing if normalize_category_name(c.name) == normalized]
    if matches:
        category = next((c for c in matches if c.is_active), matches[0])
        if not category.is_active:
            raise ValueError(f"Category '{category.name}' exists but is inactive. Activate it before importing.")
        cache[normalized] = category
        return category, False

    display_name = str(name).strip()
    base = build_category_prefix(display_name)
    prefix = base
    suffix = 2
    while Category.objects.filter(sku_prefix__iexact=prefix).exists():
        suffix_text = str(suffix)
        prefix = f"{base[:8-len(suffix_text)]}{suffix_text}"
        suffix += 1

    category = Category.objects.create(
        name=display_name,
        sku_prefix=prefix,
        is_active=True,
        created_by=user,
    )
    cache[normalized] = category
    return category, True

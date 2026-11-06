from django import template
register = template.Library()
@register.filter
def status_class(value):
    return {
        "In Stock": "success",
        "Low Stock": "warning",
        "Unused Stock": "secondary",
        "Out of Stock": "danger",
    }.get(value, "secondary")

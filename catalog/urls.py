from django.urls import path
from . import views
app_name = "catalog"
urlpatterns = [
    path("categories/", views.category_list, name="categories"),
    path("categories/add/", views.category_create, name="category_create"),
    path("products/", views.product_list, name="products"),
    path("products/add/", views.product_create, name="product_create"),
    path("products/import/", views.product_import, name="product_import"),
    path("products/import/template/", views.product_import_template, name="product_import_template"),
]

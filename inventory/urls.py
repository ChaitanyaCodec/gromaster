from django.urls import path
from . import views
app_name = "inventory"
urlpatterns = [
    path("", views.inventory_list, name="list"),
    path("bulk-update/", views.bulk_update, name="bulk_update"),
    path("consume/", views.consume, name="consume"),
    path("history/", views.history, name="history"),
    path("alerts/", views.alerts, name="alerts"),
]

from django.contrib import admin
from django.urls import include, path
from django.shortcuts import redirect

urlpatterns = [
    path("", lambda request: redirect("analytics:dashboard")),
    path("django-admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("catalog/", include("catalog.urls")),
    path("inventory/", include("inventory.urls")),
    path("analytics/", include("analytics_app.urls")),
]

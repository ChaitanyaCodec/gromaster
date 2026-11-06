from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from .decorators import admin_required
from .forms import EmailLoginForm, AdminCreateUserForm
from .models import UserProfile

User = get_user_model()

def login_view(request):
    if request.user.is_authenticated:
        return redirect("analytics:dashboard")
    form = EmailLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = authenticate(request, email=form.cleaned_data["email"], password=form.cleaned_data["password"])
        if user:
            login(request, user)
            return redirect(request.GET.get("next") or "analytics:dashboard")
        messages.error(request, "Email or password is incorrect, or the account is inactive.")
    return render(request, "accounts/login.html", {"form": form})

@require_POST
@login_required
def logout_view(request):
    logout(request)
    return redirect("accounts:login")

@admin_required
def user_list_view(request):
    users = User.objects.select_related("profile").order_by("email")
    return render(request, "accounts/user_list.html", {"users": users})

@admin_required
def user_create_view(request):
    form = AdminCreateUserForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        with transaction.atomic():
            user = User.objects.create_user(
                username=data["email"], email=data["email"], password=data["password1"],
                first_name=data["first_name"], last_name=data["last_name"],
                is_active=True, is_staff=(data["role"] == UserProfile.Role.ADMIN),
            )
            UserProfile.objects.create(user=user, role=data["role"], phone=data["phone"])
        messages.success(request, f"Created {user.email}. Share the temporary Gromaster password securely.")
        return redirect("accounts:user_list")
    return render(request, "accounts/user_form.html", {"form": form})

@admin_required
def user_role_view(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    if target.is_superuser:
        messages.error(request, "Superuser role cannot be changed here.")
        return redirect("accounts:user_list")
    profile, _ = UserProfile.objects.get_or_create(user=target)
    if request.method == "POST":
        role = request.POST.get("role")
        if role in UserProfile.Role.values:
            profile.role = role
            profile.save()
            target.is_staff = role == UserProfile.Role.ADMIN
            target.save(update_fields=["is_staff"])
            messages.success(request, f"Updated {target.email}'s role.")
        else:
            messages.error(request, "Select a valid role.")
        return redirect("accounts:user_list")
    return render(request, "accounts/user_role.html", {"target": target, "profile": profile})

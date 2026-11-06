from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from .models import UserProfile

def role_required(*roles):
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.user.is_superuser:
                return view(request, *args, **kwargs)
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            if profile.role not in roles:
                raise PermissionDenied("You do not have permission to access this page.")
            return view(request, *args, **kwargs)
        return wrapped
    return decorator

admin_required = role_required(UserProfile.Role.ADMIN)
manager_required = role_required(UserProfile.Role.ADMIN, UserProfile.Role.MANAGER)

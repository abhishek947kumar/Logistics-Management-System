from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def provider_required(view_func):
    """
    Decorator for views that checks that the logged-in user is a Logistics Service Provider.
    If a consumer accesses it, redirect to the consumer dashboard.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('provider_login')
        
        # Check if user is provider or superuser
        profile = getattr(request.user, 'profile', None)
        if request.user.is_superuser or (profile and profile.role == 'PROVIDER'):
            return view_func(request, *args, **kwargs)
            
        messages.warning(request, "This area is reserved for Logistics Service Providers. Redirected to your Consumer portal.")
        return redirect('consumer_dashboard')

    return _wrapped_view


def consumer_required(view_func):
    """
    Decorator for views that checks that the logged-in user is a Consumer.
    If a provider accesses it, redirect to the provider operations dashboard.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('consumer_login')
            
        profile = getattr(request.user, 'profile', None)
        if profile and profile.role == 'CONSUMER':
            return view_func(request, *args, **kwargs)
            
        if request.user.is_superuser or (profile and profile.role == 'PROVIDER'):
            # Allow superuser to view consumer view or redirect
            return view_func(request, *args, **kwargs)

        return redirect('consumer_login')

    return _wrapped_view

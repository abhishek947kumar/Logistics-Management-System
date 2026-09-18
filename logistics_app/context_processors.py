from .models import Notification, CustomerEnquiry, ShipmentRequest

def logistics_global_context(request):
    if not request.user.is_authenticated:
        return {}
    
    unread_notifications_count = Notification.objects.filter(is_read=False).count()
    recent_notifications = Notification.objects.filter(is_read=False)[:5]
    pending_enquiries_count = CustomerEnquiry.objects.filter(status='Pending').count()
    pending_requests_count = ShipmentRequest.objects.filter(status='Pending').count()
    profile = getattr(request.user, 'profile', None)
    
    is_provider = request.user.is_superuser or (profile and profile.role == 'PROVIDER')
    is_consumer = profile and profile.role == 'CONSUMER'

    return {
        'unread_notifications_count': unread_notifications_count,
        'recent_notifications': recent_notifications,
        'pending_enquiries_count': pending_enquiries_count,
        'pending_requests_count': pending_requests_count,
        'user_profile': profile,
        'is_provider': is_provider,
        'is_consumer': is_consumer,
    }

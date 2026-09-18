from django.urls import path
from . import views

urlpatterns = [
    # Gateway & Authentication
    path('login/', views.portal_select_view, name='portal_select'),
    path('portal/', views.portal_select_view, name='login'),
    path('provider/login/', views.provider_login_view, name='provider_login'),
    path('provider/register/', views.provider_register_view, name='provider_register'),
    path('provider/profile/', views.provider_profile_view, name='provider_profile'),
    path('consumer/login/', views.consumer_login_view, name='consumer_login'),
    path('consumer/register/', views.consumer_register_view, name='consumer_register'),
    path('consumer/profile/', views.consumer_profile_view, name='consumer_profile'),
    path('logout/', views.logout_view, name='logout'),
    
    # Provider Operations Dashboard
    path('', views.dashboard_view, name='dashboard'),
    
    # Provider Consumer Booking Requests
    path('provider/requests/', views.provider_requests_list_view, name='provider_requests'),
    path('provider/requests/<int:pk>/approve/', views.provider_request_approve_view, name='provider_request_approve'),

    # Consumer Portal Workflows
    path('consumer/', views.consumer_dashboard_view, name='consumer_dashboard'),
    path('consumer/shipments/<str:tracking_number>/', views.consumer_shipment_detail_view, name='consumer_shipment_detail'),
    path('consumer/request/', views.consumer_request_shipment_view, name='consumer_request_shipment'),

    # Public Tracking & Customer Self-Service
    path('track/', views.public_track_view, name='public_tracking_search'),
    path('track/<str:tracking_number>/', views.public_track_view, name='public_tracking_detail'),
    path('track/<str:tracking_number>/enquiry/', views.submit_enquiry_view, name='submit_enquiry'),
    
    # Customer Support & Enquiries Desk (Admin)
    path('enquiries/', views.enquiry_list_view, name='enquiry_list'),
    path('enquiries/<int:pk>/', views.enquiry_detail_view, name='enquiry_detail'),
    
    # Manage Goods & Warehouse Inventory
    path('goods/', views.goods_list_view, name='goods_list'),
    path('goods/add/', views.goods_add_view, name='goods_add'),
    path('goods/<int:pk>/edit/', views.goods_edit_view, name='goods_edit'),
    path('goods/<int:pk>/delete/', views.goods_delete_view, name='goods_delete'),
    
    # Shipments & Goods Movement
    path('shipments/', views.shipment_list_view, name='shipment_list'),
    path('shipments/dispatch/', views.shipment_dispatch_view, name='shipment_dispatch'),
    path('shipments/<int:pk>/arrival/', views.goods_arrival_view, name='goods_arrival'),
    path('shipments/<int:pk>/invoice/', views.shipment_invoice_view, name='shipment_invoice'),
    
    # Admin Tracking Detail
    path('tracking/', views.tracking_view, name='tracking_search'),
    path('tracking/<str:tracking_number>/', views.tracking_view, name='tracking_detail'),
    
    # Facilities & Fleet
    path('warehouses/', views.warehouse_list_view, name='warehouse_list'),
    path('vehicles/', views.vehicle_list_view, name='vehicle_list'),
    
    # Reports & CSV Data Auditing
    path('reports/', views.reports_view, name='reports'),
    path('reports/export/goods/', views.export_goods_csv, name='export_goods_csv'),
    path('reports/export/transit/', views.export_transit_csv, name='export_transit_csv'),
    
    # Notification Center
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/mark-read/', views.mark_notifications_read, name='mark_notifications_read'),
]

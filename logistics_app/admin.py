from django.contrib import admin
from .models import Warehouse, Vehicle, GoodsItem, Shipment, ShipmentItem, TransitCheckpoint, WarehouseLog, CustomerEnquiry, Notification, UserProfile, ShipmentRequest


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'city', 'capacity', 'supervisor_name', 'contact_number', 'is_active')
    search_fields = ('name', 'code', 'city', 'supervisor_name')
    list_filter = ('is_active', 'city')


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('vehicle_number', 'vehicle_type', 'driver_name', 'driver_phone', 'capacity_kg', 'status')
    search_fields = ('vehicle_number', 'driver_name', 'driver_phone')
    list_filter = ('status', 'vehicle_type')


@admin.register(GoodsItem)
class GoodsItemAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'category', 'quantity', 'unit', 'weight_kg', 'warehouse', 'status', 'updated_at')
    search_fields = ('sku', 'name', 'category')
    list_filter = ('status', 'category', 'warehouse')
    readonly_fields = ('created_at', 'updated_at')


class ShipmentItemInline(admin.TabularInline):
    model = ShipmentItem
    extra = 1


class TransitCheckpointInline(admin.TabularInline):
    model = TransitCheckpoint
    extra = 1


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ('tracking_number', 'origin_warehouse', 'destination_city', 'recipient_name', 'status', 'dispatch_time', 'actual_arrival', 'transit_duration_display')
    search_fields = ('tracking_number', 'destination_city', 'recipient_name', 'recipient_phone')
    list_filter = ('status', 'origin_warehouse', 'delivery_condition')
    inlines = [ShipmentItemInline, TransitCheckpointInline]
    readonly_fields = ('created_at', 'updated_at')


@admin.register(WarehouseLog)
class WarehouseLogAdmin(admin.ModelAdmin):
    list_display = ('action_type', 'goods_item', 'warehouse', 'quantity', 'timestamp')
    search_fields = ('goods_item__name', 'goods_item__sku', 'warehouse__name')
    list_filter = ('action_type', 'timestamp')


@admin.register(CustomerEnquiry)
class CustomerEnquiryAdmin(admin.ModelAdmin):
    list_display = ('shipment', 'customer_name', 'customer_phone', 'subject', 'status', 'created_at')
    search_fields = ('customer_name', 'customer_email', 'subject', 'shipment__tracking_number')
    list_filter = ('status', 'created_at')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_read', 'created_at')
    list_filter = ('category', 'is_read', 'created_at')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'company_name', 'business_type', 'gstin_or_tax_id', 'phone', 'city', 'created_at')
    list_filter = ('role', 'business_type', 'city')
    search_fields = ('user__username', 'company_name', 'gstin_or_tax_id', 'phone')


@admin.register(ShipmentRequest)
class ShipmentRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'consumer', 'preferred_provider', 'goods_name', 'origin_city', 'destination_city', 'status', 'created_at')
    list_filter = ('status', 'category')
    search_fields = ('goods_name', 'consumer__username', 'preferred_provider__username', 'destination_city')



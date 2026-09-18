import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Standard coordinates for major logistics hubs & destination cities in India
DEFAULT_CITY_COORDINATES = {
    'Mumbai': (19.0760, 72.8777),
    'Delhi NCR': (28.7041, 77.1025),
    'Delhi': (28.7041, 77.1025),
    'Bengaluru': (12.9716, 77.5946),
    'Bangalore': (12.9716, 77.5946),
    'Kolkata': (22.5726, 88.3639),
    'Pune': (18.5204, 73.8567),
    'Jaipur': (26.9124, 75.7873),
    'Hyderabad': (17.3850, 78.4867),
    'Chennai': (13.0827, 80.2707),
    'Ahmedabad': (23.0225, 72.5714),
    'Nashik': (19.9975, 73.7898),
    'Nagpur': (21.1458, 79.0882),
    'Indore': (22.7196, 75.8577),
    'Surat': (21.1702, 72.8311),
}


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('PROVIDER', 'Logistics Service Provider'),
        ('CONSUMER', 'Consumer / Consignee'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='CONSUMER')
    company_name = models.CharField(max_length=150, blank=True, null=True, help_text="Company or Business Name")
    business_type = models.CharField(max_length=80, blank=True, null=True, help_text="e.g. 3PL Logistics Dealer, Freight Forwarder, Fleet Owner, Retailer, Manufacturer")
    gstin_or_tax_id = models.CharField(max_length=30, blank=True, null=True, help_text="Commercial Tax ID / GSTIN / Business Reg No.")
    phone = models.CharField(max_length=25, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True, help_text="Registered commercial office address")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_provider(self):
        return self.role == 'PROVIDER' or self.user.is_superuser

    @property
    def is_consumer(self):
        return self.role == 'CONSUMER'


class Warehouse(models.Model):
    provider = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='warehouses', help_text="Operating dealer/provider")
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=30, unique=True)
    location = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    latitude = models.FloatField(default=19.0760, help_text="GPS Latitude")
    longitude = models.FloatField(default=72.8777, help_text="GPS Longitude")
    capacity = models.PositiveIntegerField(help_text="Storage capacity (e.g., pallets/sq.ft)")
    supervisor_name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=25)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code}) - {self.city}"

    def save(self, *args, **kwargs):
        if self.city in DEFAULT_CITY_COORDINATES and (self.latitude == 19.0760 and self.longitude == 72.8777):
            lat, lng = DEFAULT_CITY_COORDINATES[self.city]
            self.latitude, self.longitude = lat, lng
        super().save(*args, **kwargs)

    @property
    def total_goods_count(self):
        return self.goods.filter(status='Available').count()

    @property
    def total_quantity(self):
        return self.goods.filter(status='Available').aggregate(models.Sum('quantity'))['quantity__sum'] or 0


class Vehicle(models.Model):
    provider = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='vehicles', help_text="Operating dealer/provider")
    TYPE_CHOICES = [
        ('Container Truck', 'Container Truck (32 Ft)'),
        ('Medium Duty Truck', 'Medium Duty Truck (14-19 Ft)'),
        ('Mini Truck / Pickup', 'Mini Truck / Pickup (Tata Ace / Bolero)'),
        ('Refrigerated Reefer', 'Refrigerated Reefer Van'),
        ('Flatbed Carrier', 'Flatbed Heavy Carrier'),
    ]
    STATUS_CHOICES = [
        ('Available', 'Available in Yard'),
        ('In Transit', 'On Route / In Transit'),
        ('Maintenance', 'Under Maintenance'),
    ]

    vehicle_number = models.CharField(max_length=30, unique=True)
    vehicle_type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='Container Truck')
    driver_name = models.CharField(max_length=100)
    driver_phone = models.CharField(max_length=25)
    capacity_kg = models.DecimalField(max_digits=10, decimal_places=2, default=5000.00)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Available')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['vehicle_number']

    def __str__(self):
        return f"{self.vehicle_number} - {self.driver_name} ({self.status})"


class GoodsItem(models.Model):
    CATEGORY_CHOICES = [
        ('Electronics', 'Electronics & Appliances'),
        ('Pharmaceuticals', 'Pharmaceuticals & Healthcare'),
        ('Automotive Parts', 'Automotive & Spares'),
        ('Industrial Equipment', 'Industrial & Heavy Equipment'),
        ('FMCG', 'FMCG & Consumer Goods'),
        ('Textiles', 'Textiles & Apparel'),
        ('Chemicals & Materials', 'Chemicals & Raw Materials'),
        ('General Cargo', 'General Cargo / Parcels'),
    ]

    STATUS_CHOICES = [
        ('Available', 'Available in Warehouse'),
        ('Issued', 'Issued for Dispatch'),
        ('In Transit', 'In Transit / On Route'),
        ('Delivered', 'Delivered to Destination'),
        ('Damaged', 'Damaged / Discrepancy'),
    ]

    UNIT_CHOICES = [
        ('Units', 'Units'),
        ('Boxes', 'Boxes'),
        ('Pallets', 'Pallets'),
        ('Cartons', 'Cartons'),
        ('Kg', 'Kilograms (Kg)'),
        ('Tons', 'Metric Tons'),
    ]

    sku = models.CharField(max_length=50, unique=True, help_text="Unique Stock Keeping Unit or Barcode ID")
    provider = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='goods_items', help_text="Dealer/owner of this inventory")
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='General Cargo')
    quantity = models.PositiveIntegerField(default=1)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='Units')
    weight_kg = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)
    unit_value = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="Declared goods value in INR")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True, related_name='goods')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Available')
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.sku}] {self.name} ({self.quantity} {self.unit})"

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = f"GDS-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class Shipment(models.Model):
    STATUS_CHOICES = [
        ('Dispatched', 'Dispatched / In Transit'),
        ('Delivered', 'Delivered / Arrived'),
        ('Delayed', 'Delayed in Transit'),
        ('Cancelled', 'Cancelled'),
    ]

    DELIVERY_CONDITION_CHOICES = [
        ('Intact', 'Intact / Perfect Condition'),
        ('Minor Damage', 'Minor Packaging Wear'),
        ('Damaged', 'Damaged / Discrepancy Noted'),
    ]

    tracking_number = models.CharField(max_length=50, unique=True)
    provider = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='serviced_shipments', help_text="Logistics dealer/provider operating this shipment")
    consumer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='consignments', help_text="Linked consumer/consignee user account")
    origin_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='dispatched_shipments')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='shipments')
    
    destination_hub_or_consignee = models.CharField(max_length=150, help_text="Receiving Center or Consignee Name")
    destination_address = models.TextField()
    destination_city = models.CharField(max_length=100)
    dest_latitude = models.FloatField(default=18.5204, help_text="Destination GPS Latitude")
    dest_longitude = models.FloatField(default=73.8567, help_text="Destination GPS Longitude")

    recipient_name = models.CharField(max_length=100)
    recipient_phone = models.CharField(max_length=25)
    
    dispatch_time = models.DateTimeField(default=timezone.now, help_text="Time shipment left the origin warehouse")
    estimated_arrival = models.DateTimeField(null=True, blank=True)
    actual_arrival = models.DateTimeField(null=True, blank=True, help_text="Exact timestamp goods arrived at destination")
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Dispatched')
    delivery_condition = models.CharField(max_length=50, choices=DELIVERY_CONDITION_CHOICES, default='Intact', blank=True)
    received_by_signature_name = models.CharField(max_length=100, blank=True, null=True, help_text="Name of recipient confirming arrival")
    arrival_notes = models.TextField(blank=True, null=True)
    
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-dispatch_time']

    def __str__(self):
        return f"{self.tracking_number} ({self.origin_warehouse.city} -> {self.destination_city}) - {self.status}"

    def save(self, *args, **kwargs):
        if not self.tracking_number:
            self.tracking_number = f"LMS-{timezone.now().strftime('%y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        if self.destination_city in DEFAULT_CITY_COORDINATES and (self.dest_latitude == 18.5204 and self.dest_longitude == 73.8567):
            lat, lng = DEFAULT_CITY_COORDINATES[self.destination_city]
            self.dest_latitude, self.dest_longitude = lat, lng
        super().save(*args, **kwargs)

    @property
    def is_delivered(self):
        return self.status == 'Delivered' and self.actual_arrival is not None

    def get_transit_duration(self):
        end_time = self.actual_arrival if (self.is_delivered and self.actual_arrival) else timezone.now()
        
        if not self.dispatch_time:
            return {
                'days': 0, 'hours': 0, 'minutes': 0, 'seconds': 0,
                'total_seconds': 0, 'formatted': "N/A"
            }
            
        delta = end_time - self.dispatch_time
        total_seconds = max(0, int(delta.total_seconds()))
        
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0 or days > 0:
            parts.append(f"{hours}h")
        parts.append(f"{minutes}m")
        
        formatted = " ".join(parts) if parts else f"{seconds}s"
        
        return {
            'days': days,
            'hours': hours,
            'minutes': minutes,
            'seconds': seconds,
            'total_seconds': total_seconds,
            'formatted': formatted,
        }

    @property
    def transit_duration_display(self):
        return self.get_transit_duration()['formatted']

    @property
    def progress_percentage(self):
        if self.is_delivered:
            return 100
        if not self.estimated_arrival or not self.dispatch_time:
            cps = self.checkpoints.count()
            return min(85, max(15, cps * 25))
        total_time = (self.estimated_arrival - self.dispatch_time).total_seconds()
        if total_time <= 0:
            return 50
        elapsed = (timezone.now() - self.dispatch_time).total_seconds()
        return min(95, max(10, int((elapsed / total_time) * 100)))


class ShipmentItem(models.Model):
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='items')
    goods_item = models.ForeignKey(GoodsItem, on_delete=models.CASCADE, related_name='shipment_records')
    quantity_shipped = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity_shipped}x {self.goods_item.name} for {self.shipment.tracking_number}"


class TransitCheckpoint(models.Model):
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='checkpoints')
    location_name = models.CharField(max_length=150)
    status_note = models.CharField(max_length=255)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    is_completed = models.BooleanField(default=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.location_name} - {self.status_note} ({self.timestamp.strftime('%d-%b %H:%M')})"


class WarehouseLog(models.Model):
    ACTION_CHOICES = [
        ('ADDED', 'Goods Added to Inventory'),
        ('UPDATED', 'Goods Details Updated'),
        ('ISSUED', 'Goods Issued for Shipment'),
        ('RECEIVED', 'Goods Arrived / Stock Received'),
        ('REMOVED', 'Goods Removed / Scrapped'),
    ]

    goods_item = models.ForeignKey(GoodsItem, on_delete=models.CASCADE, related_name='logs')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='activity_logs')
    action_type = models.CharField(max_length=30, choices=ACTION_CHOICES)
    quantity = models.IntegerField(default=0)
    notes = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action_type} - {self.goods_item.name} ({self.quantity}) at {self.timestamp.strftime('%d-%b %H:%M')}"


class ShipmentRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending Review'),
        ('Approved', 'Approved & Dispatched'),
        ('Rejected', 'Rejected'),
    ]

    consumer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shipment_requests')
    preferred_provider = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='directed_shipment_requests', help_text="Specific provider requested by consumer (or null for any network dealer)")
    goods_name = models.CharField(max_length=150)
    category = models.CharField(max_length=50, choices=GoodsItem.CATEGORY_CHOICES, default='General Cargo')
    quantity = models.PositiveIntegerField(default=1)
    unit = models.CharField(max_length=20, choices=GoodsItem.UNIT_CHOICES, default='Units')
    origin_city = models.CharField(max_length=100)
    destination_city = models.CharField(max_length=100)
    destination_address = models.TextField()
    special_instructions = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Pending')
    shipment = models.OneToOneField(Shipment, on_delete=models.SET_NULL, null=True, blank=True, related_name='booking_request')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Request #{self.id} by {self.consumer.username} - {self.goods_name} ({self.status})"


class CustomerEnquiry(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending Review'),
        ('In Progress', 'Under Investigation'),
        ('Resolved', 'Resolved & Answered'),
    ]

    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='enquiries')
    consumer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='enquiries')
    customer_name = models.CharField(max_length=120)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=25)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Pending')
    admin_response = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Enquiry from {self.customer_name} on {self.shipment.tracking_number} ({self.status})"


class Notification(models.Model):
    CATEGORY_CHOICES = [
        ('DISPATCH', 'Shipment Dispatched'),
        ('CHECKPOINT', 'Waypoint Passed'),
        ('ARRIVAL', 'Goods Arrived'),
        ('ENQUIRY', 'Customer Enquiry'),
        ('REQUEST', 'Shipment Booking Request'),
        ('STOCK', 'Warehouse Inventory'),
    ]

    title = models.CharField(max_length=150)
    message = models.TextField()
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='DISPATCH')
    link = models.CharField(max_length=255, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.category}] {self.title}"

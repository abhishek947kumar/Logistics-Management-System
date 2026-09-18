from django import forms
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone
from .models import GoodsItem, Warehouse, Vehicle, Shipment, TransitCheckpoint, ShipmentRequest, UserProfile


class GoodsItemForm(forms.ModelForm):
    class Meta:
        model = GoodsItem
        fields = ['sku', 'name', 'category', 'quantity', 'unit', 'weight_kg', 'unit_value', 'warehouse', 'status', 'description']
        widgets = {
            'sku': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Leave blank to auto-generate SKU'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Industrial Servo Motor 5kW'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'unit': forms.Select(attrs={'class': 'form-select'}),
            'weight_kg': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'unit_value': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'warehouse': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Goods description, handling instructions, fragile status, etc.'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sku'].required = False


class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['name', 'code', 'location', 'city', 'capacity', 'supervisor_name', 'contact_number', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Western Regional Logistics Hub'}),
            'code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. WH-BOM-01'}),
            'location': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Full street address or logistics park'}),
            'city': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Mumbai'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-input', 'min': '1'}),
            'supervisor_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Warehouse Manager / Supervisor'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+91 98765 43210'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ['vehicle_number', 'vehicle_type', 'driver_name', 'driver_phone', 'capacity_kg', 'status']
        widgets = {
            'vehicle_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. MH-04-AZ-8921'}),
            'vehicle_type': forms.Select(attrs={'class': 'form-select'}),
            'driver_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Assigned Driver Name'}),
            'driver_phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+91 98234 56789'}),
            'capacity_kg': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class ShipmentDispatchForm(forms.ModelForm):
    goods_item = forms.ModelChoiceField(
        queryset=GoodsItem.objects.filter(status='Available', quantity__gt=0),
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Select available goods from warehouse"
    )
    quantity_to_ship = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-input'}),
        help_text="Quantity to dispatch"
    )

    class Meta:
        model = Shipment
        fields = [
            'origin_warehouse', 'vehicle', 'destination_hub_or_consignee',
            'destination_address', 'destination_city', 'recipient_name',
            'recipient_phone', 'dispatch_time', 'estimated_arrival', 'remarks'
        ]
        widgets = {
            'origin_warehouse': forms.Select(attrs={'class': 'form-select'}),
            'vehicle': forms.Select(attrs={'class': 'form-select'}),
            'destination_hub_or_consignee': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Pune Distribution Center or Reliance Retail Hub'}),
            'destination_address': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'Full destination delivery address'}),
            'destination_city': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Pune'}),
            'recipient_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Receiving Contact Person'}),
            'recipient_phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+91 98111 22233'}),
            'dispatch_time': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'estimated_arrival': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'remarks': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'Special transit instructions / fragile handling'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get('dispatch_time'):
            self.initial['dispatch_time'] = timezone.now().strftime('%Y-%m-%dT%H:%M')


class GoodsArrivalForm(forms.ModelForm):
    class Meta:
        model = Shipment
        fields = ['actual_arrival', 'delivery_condition', 'received_by_signature_name', 'arrival_notes']
        widgets = {
            'actual_arrival': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'delivery_condition': forms.Select(attrs={'class': 'form-select'}),
            'received_by_signature_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Official Receiver Name (e.g. Rajesh Patil)'}),
            'arrival_notes': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Inspection notes, condition details, delivery confirmation'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get('actual_arrival'):
            self.initial['actual_arrival'] = timezone.now().strftime('%Y-%m-%dT%H:%M')
        self.fields['actual_arrival'].required = True
        self.fields['received_by_signature_name'].required = True


class CheckpointForm(forms.ModelForm):
    class Meta:
        model = TransitCheckpoint
        fields = ['location_name', 'status_note', 'timestamp']
        widgets = {
            'location_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Khalapur Toll Plaza / Transit Waypoint'}),
            'status_note': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Cleared security check, proceeding smoothly'}),
            'timestamp': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get('timestamp'):
            self.initial['timestamp'] = timezone.now().strftime('%Y-%m-%dT%H:%M')


class CustomerEnquiryForm(forms.ModelForm):
    class Meta:
        from .models import CustomerEnquiry
        model = CustomerEnquiry
        fields = ['customer_name', 'customer_email', 'customer_phone', 'subject', 'message']
        widgets = {
            'customer_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Your Full Name'}),
            'customer_email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'name@example.com'}),
            'customer_phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+91 98765 43210'}),
            'subject': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Enquiry Subject (e.g., Delivery Time Confirmation)'}),
            'message': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4, 'placeholder': 'Please specify your enquiry details regarding this consignment...'}),
        }


class EnquiryResponseForm(forms.ModelForm):
    class Meta:
        from .models import CustomerEnquiry
        model = CustomerEnquiry
        fields = ['status', 'admin_response']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'admin_response': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4, 'placeholder': 'Type official resolution or response to customer...'}),
        }


class ProviderRegistrationForm(forms.Form):
    BUSINESS_TYPE_CHOICES = [
        ('3PL Logistics Provider', '3PL Integrated Logistics Provider'),
        ('Logistics Carrier / 3PL', 'Logistics Carrier / 3PL'),
        ('Fleet & Trucking Operator', 'Fleet & Trucking Carrier Operator'),
        ('Express Freight Courier', 'Express Freight & Cargo Carrier'),
        ('Warehouse & Distribution Hub', 'Warehouse & Distribution Storage Hub'),
        ('Freight Forwarder', 'Domestic & Export Freight Forwarder'),
    ]

    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. bluedart_mumbai'}))
    company_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. BlueDart Express Freight Ltd'}))
    business_type = forms.ChoiceField(choices=BUSINESS_TYPE_CHOICES, initial='3PL Logistics Provider', widget=forms.Select(attrs={'class': 'form-select'}))
    gstin_or_tax_id = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. 27AABCU9603R1ZM'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'operations@dealer.com'}))
    phone = forms.CharField(max_length=25, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+91 98201 11223'}))
    city = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Mumbai'}))
    address = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'Registered business / hub facility address'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Create secure provider password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Re-enter password'}))

    def clean_username(self):
        from django.contrib.auth.models import User
        username = self.cleaned_data['username']
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This provider account username is already registered. Please choose another.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data


class ConsumerRegistrationForm(forms.Form):
    CONSUMER_TYPE_CHOICES = [
        ('Retail Consignee', 'Retail Consignee & Shop Distribution'),
        ('Manufacturing Client', 'Industrial Manufacturer / Factory'),
        ('E-Commerce Seller', 'E-Commerce Marketplace Seller'),
        ('Corporate Enterprise', 'Corporate / Commercial Enterprise'),
        ('Individual Consignee', 'Individual / Private Consignee'),
    ]

    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. reliance_pune'}))
    full_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Reliance Retail Distribution'}))
    business_type = forms.ChoiceField(choices=CONSUMER_TYPE_CHOICES, required=False, initial='Corporate Enterprise', widget=forms.Select(attrs={'class': 'form-select'}))
    gstin_or_tax_id = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'GSTIN / Business ID (optional)'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'contact@client.com'}))
    phone = forms.CharField(max_length=25, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+91 98220 55667'}))
    city = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Pune'}))
    address = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'Delivery receiving address / facility'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Create secure password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Re-enter password'}))

    def clean_username(self):
        from django.contrib.auth.models import User
        username = self.cleaned_data['username']
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken. Please select another.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('business_type'):
            cleaned_data['business_type'] = 'Corporate Enterprise'
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data


class ShipmentBookingRequestForm(forms.ModelForm):
    preferred_provider = forms.ModelChoiceField(
        queryset=User.objects.filter(Q(profile__role='PROVIDER') | Q(is_superuser=True)).distinct(),
        required=False,
        empty_label="🌐 Open Logistics Network (Any Certified Provider / Dealer)",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        from .models import ShipmentRequest
        model = ShipmentRequest
        fields = ['preferred_provider', 'goods_name', 'category', 'quantity', 'unit', 'origin_city', 'destination_city', 'destination_address', 'special_instructions']
        widgets = {
            'goods_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Commercial Air Compressor 500L'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-input', 'min': '1'}),
            'unit': forms.Select(attrs={'class': 'form-select'}),
            'origin_city': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Mumbai'}),
            'destination_city': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Pune'}),
            'destination_address': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Delivery warehouse/facility address with pincode'}),
            'special_instructions': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'Handling notes, fragile, priority delivery, forklift needed, etc.'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Display dealer company name alongside username if available
        self.fields['preferred_provider'].label_from_instance = lambda u: f"{u.profile.company_name or u.username} ({u.profile.city or 'National'})" if hasattr(u, 'profile') and u.profile.company_name else u.username


class ProviderBookingApprovalForm(forms.Form):
    warehouse = forms.ModelChoiceField(queryset=Warehouse.objects.filter(is_active=True), widget=forms.Select(attrs={'class': 'form-select'}))
    vehicle = forms.ModelChoiceField(queryset=Vehicle.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    estimated_arrival = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}))


class CompanyProfileUpdateForm(forms.ModelForm):
    class Meta:
        from .models import UserProfile
        model = UserProfile
        fields = ['company_name', 'business_type', 'gstin_or_tax_id', 'phone', 'city', 'address']
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-input'}),
            'business_type': forms.TextInput(attrs={'class': 'form-input'}),
            'gstin_or_tax_id': forms.TextInput(attrs={'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-input'}),
            'city': forms.TextInput(attrs={'class': 'form-input'}),
            'address': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
        }



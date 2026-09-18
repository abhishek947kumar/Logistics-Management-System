import csv
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.http import HttpResponse

from .models import (
    Warehouse, Vehicle, GoodsItem, Shipment, ShipmentItem,
    TransitCheckpoint, WarehouseLog, CustomerEnquiry, Notification,
    UserProfile, ShipmentRequest, DEFAULT_CITY_COORDINATES
)
from .forms import (
    GoodsItemForm, WarehouseForm, VehicleForm, ShipmentDispatchForm,
    GoodsArrivalForm, CheckpointForm, CustomerEnquiryForm, EnquiryResponseForm,
    ConsumerRegistrationForm, ProviderRegistrationForm, ShipmentBookingRequestForm,
    ProviderBookingApprovalForm, CompanyProfileUpdateForm
)
from .decorators import provider_required, consumer_required


def create_notification(title, message, category='DISPATCH', link=None):
    """Helper to record automated system notifications"""
    Notification.objects.create(
        title=title,
        message=message,
        category=category,
        link=link
    )


# ==========================================
# PORTAL GATEWAY & DUAL AUTHENTICATION
# ==========================================

def portal_select_view(request):
    """Gateway screen allowing selection between Provider and Consumer portals"""
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        if profile and profile.role == 'CONSUMER':
            return redirect('consumer_dashboard')
        return redirect('dashboard')
    return render(request, 'logistics/portal_select.html')


def provider_login_view(request):
    """Dedicated login portal for Logistics Service Providers & Fleet Admins"""
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        if profile and profile.role == 'CONSUMER':
            messages.info(request, "Logged in as consumer. Redirected to Consumer Portal.")
            return redirect('consumer_dashboard')
        return redirect('dashboard')

    if request.method == 'POST':
        u = request.POST.get('username', '').strip()
        p = request.POST.get('password', '')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            profile = getattr(user, 'profile', None)
            if profile and profile.role == 'CONSUMER':
                login(request, user)
                messages.info(request, f"Welcome back, {user.username}! Accessing Consumer Dashboard.")
                return redirect('consumer_dashboard')
            login(request, user)
            messages.success(request, f"Welcome to Provider Command Center, {user.username}!")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid provider username or password.")

    return render(request, 'logistics/provider_login.html')


def provider_register_view(request):
    """Self-service commercial onboarding for Logistics Service Providers / Dealers"""
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        if profile and profile.role == 'CONSUMER':
            return redirect('consumer_dashboard')
        return redirect('dashboard')

    if request.method == 'POST':
        form = ProviderRegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            company_name = form.cleaned_data['company_name']
            business_type = form.cleaned_data['business_type']
            gstin = form.cleaned_data['gstin_or_tax_id']
            email = form.cleaned_data['email']
            phone = form.cleaned_data['phone']
            city = form.cleaned_data['city']
            address = form.cleaned_data['address']
            password = form.cleaned_data['password']

            user = User.objects.create_user(username=username, email=email, password=password)
            user.first_name = company_name[:30]
            user.save()

            UserProfile.objects.create(
                user=user,
                role='PROVIDER',
                company_name=company_name,
                business_type=business_type,
                gstin_or_tax_id=gstin,
                phone=phone,
                city=city,
                address=address
            )

            # Automatically provision an initial primary logistics hub for this dealer
            wh_code = f"WH-{city[:3].upper()}-{uuid.uuid4().hex[:4].upper()}"
            Warehouse.objects.create(
                provider=user,
                name=f"{company_name} - {city} Terminal",
                code=wh_code,
                location=address or f"{city} Logistics Corridor",
                city=city,
                capacity=12000,
                supervisor_name=f"{company_name} Dispatcher",
                contact_number=phone,
                is_active=True
            )

            create_notification(
                title=f"New Logistics Dealer Registered: {company_name}",
                message=f"Dealer '{company_name}' ({business_type}, GSTIN: {gstin}) from {city} onboarded.",
                category='STOCK'
            )

            login(request, user)
            messages.success(request, f"Welcome to LogiTrack Commercial Network, {company_name}! Your primary logistics facility is provisioned.")
            return redirect('dashboard')
    else:
        form = ProviderRegistrationForm()

    return render(request, 'logistics/provider_register.html', {'form': form})


def consumer_login_view(request):
    """Dedicated login portal for Consumers, Clients & Consignees"""
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        if profile and profile.role == 'CONSUMER':
            return redirect('consumer_dashboard')
        return redirect('dashboard')

    if request.method == 'POST':
        u = request.POST.get('username', '').strip()
        p = request.POST.get('password', '')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            profile = getattr(user, 'profile', None)
            if profile and profile.role == 'CONSUMER':
                messages.success(request, f"Welcome to your Consumer Tracking Portal, {user.username}!")
                return redirect('consumer_dashboard')
            else:
                messages.info(request, f"Provider account detected. Redirected to Command Center.")
                return redirect('dashboard')
        else:
            messages.error(request, "Invalid client username or password.")

    return render(request, 'logistics/consumer_login.html')


def consumer_register_view(request):
    """Self-service registration for new Consumers / Consignees"""
    if request.user.is_authenticated:
        return redirect('consumer_dashboard')

    if request.method == 'POST':
        form = ConsumerRegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            full_name = form.cleaned_data['full_name']
            business_type = form.cleaned_data['business_type']
            gstin = form.cleaned_data.get('gstin_or_tax_id', '')
            phone = form.cleaned_data['phone']
            city = form.cleaned_data['city']
            address = form.cleaned_data.get('address', '')

            user = User.objects.create_user(username=username, email=email, password=password)
            user.first_name = full_name[:30]
            user.save()

            UserProfile.objects.create(
                user=user,
                role='CONSUMER',
                company_name=full_name,
                business_type=business_type,
                gstin_or_tax_id=gstin,
                phone=phone,
                city=city,
                address=address
            )

            create_notification(
                title=f"New Consumer Registered: {username}",
                message=f"Client '{full_name}' from {city} ({phone}) registered on Consumer Portal.",
                category='ENQUIRY'
            )

            login(request, user)
            messages.success(request, f"Account created successfully! Welcome to LogiTrack Pro, {full_name}.")
            return redirect('consumer_dashboard')
    else:
        form = ConsumerRegistrationForm()

    return render(request, 'logistics/consumer_register.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been safely signed out.")
    return redirect('portal_select')


# ==========================================
# CONSUMER PORTAL WORKFLOWS
# ==========================================

@consumer_required
def consumer_dashboard_view(request):
    """Personalized dashboard for authenticated consumers/clients"""
    user = request.user
    profile = getattr(user, 'profile', None)

    # Inbound / booked shipments matching this consumer account or phone
    consumer_shipments = Shipment.objects.filter(
        Q(consumer=user) | Q(recipient_phone=profile.phone if profile else '') | Q(recipient_name__icontains=user.username)
    ).select_related('origin_warehouse', 'vehicle').order_by('-dispatch_time')

    active_shipments = consumer_shipments.filter(status='Dispatched')
    delivered_shipments = consumer_shipments.filter(status='Delivered')
    
    # Booking requests placed by consumer
    my_requests = ShipmentRequest.objects.filter(consumer=user).order_by('-created_at')
    
    # Enquiries submitted by consumer
    my_enquiries = CustomerEnquiry.objects.filter(
        Q(consumer=user) | Q(customer_email=user.email)
    ).order_by('-created_at')[:5]

    context = {
        'profile': profile,
        'active_shipments': active_shipments,
        'delivered_shipments': delivered_shipments,
        'total_inbound_count': active_shipments.count(),
        'total_delivered_count': delivered_shipments.count(),
        'my_requests': my_requests,
        'my_enquiries': my_enquiries,
    }
    return render(request, 'logistics/consumer_dashboard.html', context)


@consumer_required
def consumer_shipment_detail_view(request, tracking_number):
    """Consumer shipment tracking detail with interactive Leaflet route map & live timer"""
    shipment = get_object_or_404(
        Shipment.objects.select_related('origin_warehouse', 'vehicle')
        .prefetch_related('items__goods_item', 'checkpoints'),
        tracking_number=tracking_number
    )
    transit_info = shipment.get_transit_duration()
    enquiry_form = CustomerEnquiryForm(initial={
        'customer_name': request.user.profile.company_name if hasattr(request.user, 'profile') else request.user.username,
        'customer_email': request.user.email,
        'customer_phone': request.user.profile.phone if hasattr(request.user, 'profile') else '',
    })

    context = {
        'shipment': shipment,
        'checkpoints': shipment.checkpoints.all(),
        'items': shipment.items.all(),
        'transit_info': transit_info,
        'enquiry_form': enquiry_form,
    }
    return render(request, 'logistics/consumer_shipment_detail.html', context)


@consumer_required
def consumer_request_shipment_view(request):
    """Allows consumers to book a shipment/pickup directly from their portal"""
    if request.method == 'POST':
        form = ShipmentBookingRequestForm(request.POST)
        if form.is_valid():
            req = form.save(commit=False)
            req.consumer = request.user
            req.status = 'Pending'
            req.save()

            # Trigger automated Provider Notification
            create_notification(
                title=f"New Consignment Booking Request #{req.id}",
                message=f"From {request.user.username}: {req.quantity} {req.unit} of {req.goods_name} ({req.origin_city} -> {req.destination_city})",
                category='REQUEST',
                link=f"/provider/requests/"
            )

            messages.success(request, f"Shipment booking request #{req.id} submitted! The logistics provider has been notified.")
            return redirect('consumer_dashboard')
    else:
        form = ShipmentBookingRequestForm()

    return render(request, 'logistics/consumer_request_form.html', {'form': form})


# ==========================================
# PROVIDER CONSUMER REQUESTS MANAGEMENT
# ==========================================

@provider_required
def provider_requests_list_view(request):
    """Provider inbox for reviewing consumer shipment booking requests"""
    status_filter = request.GET.get('status', '')
    if request.user.is_superuser:
        requests = ShipmentRequest.objects.select_related('consumer', 'consumer__profile', 'preferred_provider').all()
    else:
        # Show requests directed specifically to this provider or open to the entire network
        requests = ShipmentRequest.objects.select_related('consumer', 'consumer__profile', 'preferred_provider').filter(
            Q(preferred_provider=request.user) | Q(preferred_provider__isnull=True)
        )

    if status_filter:
        requests = requests.filter(status=status_filter)

    return render(request, 'logistics/provider_requests.html', {
        'requests': requests,
        'selected_status': status_filter
    })


@provider_required
def provider_request_approve_view(request, pk):
    """Provider one-click approval: converts consumer request into an active shipment!"""
    booking_req = get_object_or_404(ShipmentRequest.objects.select_related('consumer'), pk=pk)

    if request.method == 'POST':
        form = ProviderBookingApprovalForm(request.POST)
        if form.is_valid():
            warehouse = form.cleaned_data['warehouse']
            vehicle = form.cleaned_data['vehicle']
            est_arrival = form.cleaned_data['estimated_arrival']

            # 1. Create or stock GoodsItem
            sku = f"GDS-{uuid.uuid4().hex[:8].upper()}"
            goods_item = GoodsItem.objects.create(
                provider=request.user,
                sku=sku,
                name=booking_req.goods_name,
                category=booking_req.category,
                quantity=booking_req.quantity,
                unit=booking_req.unit,
                warehouse=warehouse,
                status='In Transit',
                description=f"Booked by consumer {booking_req.consumer.username}. {booking_req.special_instructions or ''}"
            )

            # 2. Create Active Shipment linked to Consumer and Provider
            recipient_phone = (booking_req.consumer.profile.phone if (hasattr(booking_req.consumer, 'profile') and booking_req.consumer.profile.phone) else '+91 9876543210')
            shipment = Shipment.objects.create(
                provider=request.user,
                consumer=booking_req.consumer,
                origin_warehouse=warehouse,
                vehicle=vehicle,
                destination_hub_or_consignee=booking_req.consumer.profile.company_name if hasattr(booking_req.consumer, 'profile') else booking_req.consumer.username,
                destination_city=booking_req.destination_city,
                destination_address=booking_req.destination_address,
                recipient_name=booking_req.consumer.username,
                recipient_phone=recipient_phone,
                dispatch_time=timezone.now(),
                estimated_arrival=est_arrival,
                status='Dispatched',
                remarks=f"Consumer Booking Request #{booking_req.id}. Instructions: {booking_req.special_instructions or 'None'}"
            )

            # 3. Create ShipmentItem
            ShipmentItem.objects.create(
                shipment=shipment,
                goods_item=goods_item,
                quantity_shipped=booking_req.quantity
            )

            # 4. Create Initial Dispatch Checkpoint
            TransitCheckpoint.objects.create(
                shipment=shipment,
                location_name=f"{warehouse.name}, {warehouse.city}",
                status_note=f"Pickup approved and dispatched via {vehicle.vehicle_number if vehicle else 'Designated Fleet'}.",
                latitude=warehouse.latitude,
                longitude=warehouse.longitude,
                timestamp=shipment.dispatch_time
            )

            # 5. Mark vehicle in transit
            if vehicle:
                vehicle.status = 'In Transit'
                vehicle.save()

            # 6. Update Booking Request Status
            booking_req.status = 'Approved'
            booking_req.shipment = shipment
            booking_req.save()

            create_notification(
                title=f"Booking Approved: #{booking_req.id}",
                message=f"Consignment {shipment.tracking_number} dispatched for {booking_req.consumer.username}.",
                category='DISPATCH',
                link=f"/tracking/{shipment.tracking_number}/"
            )

            messages.success(request, f"Request #{booking_req.id} approved! Shipment {shipment.tracking_number} created and synced with Consumer portal.")
            return redirect('tracking_detail', tracking_number=shipment.tracking_number)
    else:
        form = ProviderBookingApprovalForm(initial={
            'estimated_arrival': (timezone.now() + timezone.timedelta(hours=12)).strftime('%Y-%m-%dT%H:%M')
        })

    return render(request, 'logistics/provider_request_approve.html', {
        'booking_req': booking_req,
        'form': form
    })


# ==========================================
# PUBLIC CUSTOMER TRACKING & ENQUIRY PORTAL
# ==========================================

def public_track_view(request, tracking_number=None):
    if not tracking_number:
        query = request.GET.get('tracking_number', '').strip()
        if query:
            return redirect('public_tracking_detail', tracking_number=query)
        recent_shipments = Shipment.objects.select_related('origin_warehouse', 'vehicle').order_by('-dispatch_time')[:8]
        return render(request, 'logistics/public_track.html', {'recent_shipments': recent_shipments})

    shipment = get_object_or_404(
        Shipment.objects.select_related('origin_warehouse', 'vehicle')
        .prefetch_related('items__goods_item', 'checkpoints'),
        tracking_number=tracking_number
    )

    enquiry_form = CustomerEnquiryForm()
    transit_info = shipment.get_transit_duration()

    context = {
        'shipment': shipment,
        'checkpoints': shipment.checkpoints.all(),
        'items': shipment.items.all(),
        'transit_info': transit_info,
        'enquiry_form': enquiry_form,
    }
    return render(request, 'logistics/public_track.html', context)


def submit_enquiry_view(request, tracking_number):
    shipment = get_object_or_404(Shipment, tracking_number=tracking_number)

    if request.method == 'POST':
        form = CustomerEnquiryForm(request.POST)
        if form.is_valid():
            enquiry = form.save(commit=False)
            enquiry.shipment = shipment
            if request.user.is_authenticated:
                enquiry.consumer = request.user
            enquiry.save()

            create_notification(
                title=f"New Customer Enquiry: {shipment.tracking_number}",
                message=f"From {enquiry.customer_name} ({enquiry.customer_phone}): '{enquiry.subject}'",
                category='ENQUIRY',
                link=f"/enquiries/{enquiry.id}/"
            )

            messages.success(
                request,
                f"Thank you, {enquiry.customer_name}. Your enquiry for consignment {shipment.tracking_number} has been logged. Our logistics desk will review it shortly."
            )
            if request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role == 'CONSUMER':
                return redirect('consumer_dashboard')
            return redirect('public_tracking_detail', tracking_number=shipment.tracking_number)

    return redirect('public_tracking_detail', tracking_number=tracking_number)


# ==========================================
# ADMIN SUPPORT & ENQUIRY DESK
# ==========================================

@provider_required
def enquiry_list_view(request):
    status_filter = request.GET.get('status', '')
    enquiries = CustomerEnquiry.objects.select_related('shipment', 'consumer').all()

    if status_filter:
        enquiries = enquiries.filter(status=status_filter)

    return render(request, 'logistics/enquiry_list.html', {
        'enquiries': enquiries,
        'selected_status': status_filter,
    })


@provider_required
def enquiry_detail_view(request, pk):
    enquiry = get_object_or_404(CustomerEnquiry.objects.select_related('shipment'), pk=pk)

    if request.method == 'POST':
        form = EnquiryResponseForm(request.POST, instance=enquiry)
        if form.is_valid():
            resolved_enquiry = form.save(commit=False)
            if resolved_enquiry.status == 'Resolved' and not resolved_enquiry.resolved_at:
                resolved_enquiry.resolved_at = timezone.now()
            resolved_enquiry.save()
            messages.success(request, f"Response saved for enquiry #{enquiry.id}.")
            return redirect('enquiry_list')
    else:
        form = EnquiryResponseForm(instance=enquiry)

    return render(request, 'logistics/enquiry_detail.html', {
        'enquiry': enquiry,
        'form': form,
    })


# ==========================================
# PROVIDER DASHBOARD & INVENTORY MODULES
# ==========================================

@provider_required
def dashboard_view(request):
    total_goods_qty = GoodsItem.objects.filter(status='Available').aggregate(Sum('quantity'))['quantity__sum'] or 0
    total_goods_items = GoodsItem.objects.count()
    active_shipments = Shipment.objects.filter(status='Dispatched')
    delivered_shipments = Shipment.objects.filter(status='Delivered')
    active_vehicles = Vehicle.objects.filter(status='In Transit').count()
    total_warehouses = Warehouse.objects.filter(is_active=True).count()

    recent_shipments = Shipment.objects.select_related('origin_warehouse', 'vehicle').order_by('-dispatch_time')[:7]
    recent_logs = WarehouseLog.objects.select_related('goods_item', 'warehouse').order_by('-timestamp')[:8]
    category_counts = GoodsItem.objects.values('category').annotate(total_qty=Sum('quantity'), count=Count('id')).order_by('-total_qty')[:5]
    pending_consumer_requests = ShipmentRequest.objects.filter(status='Pending').count()

    context = {
        'total_goods_qty': total_goods_qty,
        'total_goods_items': total_goods_items,
        'active_shipments_count': active_shipments.count(),
        'delivered_shipments_count': delivered_shipments.count(),
        'active_vehicles': active_vehicles,
        'total_warehouses': total_warehouses,
        'recent_shipments': recent_shipments,
        'recent_logs': recent_logs,
        'category_counts': category_counts,
        'pending_consumer_requests': pending_consumer_requests,
        'now': timezone.now(),
    }
    return render(request, 'logistics/dashboard.html', context)


@provider_required
def goods_list_view(request):
    query = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category', '')
    status_filter = request.GET.get('status', '')
    warehouse_filter = request.GET.get('warehouse', '')

    goods = GoodsItem.objects.select_related('warehouse').all()

    if query:
        goods = goods.filter(
            Q(name__icontains=query) |
            Q(sku__icontains=query) |
            Q(description__icontains=query)
        )

    if category_filter:
        goods = goods.filter(category=category_filter)

    if status_filter:
        goods = goods.filter(status=status_filter)

    if warehouse_filter:
        goods = goods.filter(warehouse_id=warehouse_filter)

    warehouses = Warehouse.objects.filter(is_active=True)
    categories = GoodsItem.CATEGORY_CHOICES
    statuses = GoodsItem.STATUS_CHOICES

    context = {
        'goods': goods,
        'warehouses': warehouses,
        'categories': categories,
        'statuses': statuses,
        'selected_category': category_filter,
        'selected_status': status_filter,
        'selected_warehouse': warehouse_filter,
        'search_query': query,
    }
    return render(request, 'logistics/goods_list.html', context)


@provider_required
def goods_add_view(request):
    if request.method == 'POST':
        form = GoodsItemForm(request.POST)
        if form.is_valid():
            goods_item = form.save()
            if goods_item.warehouse:
                WarehouseLog.objects.create(
                    goods_item=goods_item,
                    warehouse=goods_item.warehouse,
                    action_type='ADDED',
                    quantity=goods_item.quantity,
                    notes=f"Initial stock added: {goods_item.name} ({goods_item.sku})"
                )
            create_notification(
                title=f"Stock In: {goods_item.name}",
                message=f"Added {goods_item.quantity} {goods_item.unit} to {goods_item.warehouse.name if goods_item.warehouse else 'Inventory'}",
                category='STOCK'
            )
            messages.success(request, f"Goods item '{goods_item.name}' ({goods_item.sku}) added successfully!")
            return redirect('goods_list')
    else:
        form = GoodsItemForm()

    return render(request, 'logistics/goods_form.html', {'form': form, 'title': 'Add New Goods to Warehouse'})


@provider_required
def goods_edit_view(request, pk):
    goods_item = get_object_or_404(GoodsItem, pk=pk)
    old_qty = goods_item.quantity

    if request.method == 'POST':
        form = GoodsItemForm(request.POST, instance=goods_item)
        if form.is_valid():
            updated_item = form.save()
            if updated_item.warehouse:
                WarehouseLog.objects.create(
                    goods_item=updated_item,
                    warehouse=updated_item.warehouse,
                    action_type='UPDATED',
                    quantity=updated_item.quantity,
                    notes=f"Details updated. Qty change: {old_qty} -> {updated_item.quantity}"
                )
            messages.success(request, f"Goods item '{updated_item.name}' updated successfully!")
            return redirect('goods_list')
    else:
        form = GoodsItemForm(instance=goods_item)

    return render(request, 'logistics/goods_form.html', {
        'form': form,
        'goods_item': goods_item,
        'title': f"Update Goods: {goods_item.name} ({goods_item.sku})"
    })


@provider_required
def goods_delete_view(request, pk):
    goods_item = get_object_or_404(GoodsItem, pk=pk)
    if request.method == 'POST':
        name = goods_item.name
        sku = goods_item.sku
        if goods_item.warehouse:
            WarehouseLog.objects.create(
                goods_item=goods_item,
                warehouse=goods_item.warehouse,
                action_type='REMOVED',
                quantity=goods_item.quantity,
                notes=f"Item {sku} removed from warehouse inventory"
            )
        goods_item.delete()
        messages.warning(request, f"Goods item '{name}' ({sku}) has been removed.")
        return redirect('goods_list')
    return render(request, 'logistics/goods_confirm_delete.html', {'goods_item': goods_item})


# ==========================================
# SHIPMENTS, TRANSIT & GOODS ARRIVAL
# ==========================================

@provider_required
def shipment_list_view(request):
    status_filter = request.GET.get('status', '')
    query = request.GET.get('q', '').strip()

    shipments = Shipment.objects.select_related('origin_warehouse', 'vehicle', 'consumer').prefetch_related('items__goods_item').all()

    if status_filter:
        shipments = shipments.filter(status=status_filter)

    if query:
        shipments = shipments.filter(
            Q(tracking_number__icontains=query) |
            Q(destination_city__icontains=query) |
            Q(recipient_name__icontains=query) |
            Q(destination_hub_or_consignee__icontains=query)
        )

    context = {
        'shipments': shipments,
        'selected_status': status_filter,
        'search_query': query,
    }
    return render(request, 'logistics/shipment_list.html', context)


@provider_required
def shipment_dispatch_view(request):
    if request.method == 'POST':
        form = ShipmentDispatchForm(request.POST)
        if form.is_valid():
            shipment = form.save(commit=False)
            goods_item = form.cleaned_data['goods_item']
            qty_to_ship = form.cleaned_data['quantity_to_ship']

            if qty_to_ship > goods_item.quantity:
                form.add_error('quantity_to_ship', f"Cannot dispatch {qty_to_ship} units. Only {goods_item.quantity} available in warehouse.")
                return render(request, 'logistics/shipment_form.html', {'form': form, 'title': 'Dispatch Goods / New Shipment'})

            shipment.status = 'Dispatched'
            shipment.save()

            ShipmentItem.objects.create(
                shipment=shipment,
                goods_item=goods_item,
                quantity_shipped=qty_to_ship
            )

            if goods_item.quantity == qty_to_ship:
                goods_item.status = 'In Transit'
            else:
                goods_item.quantity -= qty_to_ship
                GoodsItem.objects.create(
                    name=goods_item.name,
                    category=goods_item.category,
                    quantity=qty_to_ship,
                    unit=goods_item.unit,
                    weight_kg=goods_item.weight_kg,
                    unit_value=goods_item.unit_value,
                    warehouse=goods_item.warehouse,
                    status='In Transit',
                    description=f"In transit under shipment {shipment.tracking_number}"
                )
            goods_item.save()

            if shipment.vehicle:
                shipment.vehicle.status = 'In Transit'
                shipment.vehicle.save()

            TransitCheckpoint.objects.create(
                shipment=shipment,
                location_name=f"{shipment.origin_warehouse.name}, {shipment.origin_warehouse.city}",
                status_note=f"Consignment dispatched via {shipment.vehicle.vehicle_number if shipment.vehicle else 'Freight'}. Transit duration tracking initiated.",
                latitude=shipment.origin_warehouse.latitude,
                longitude=shipment.origin_warehouse.longitude,
                timestamp=shipment.dispatch_time
            )

            WarehouseLog.objects.create(
                goods_item=goods_item,
                warehouse=shipment.origin_warehouse,
                action_type='ISSUED',
                quantity=qty_to_ship,
                notes=f"Issued for shipment {shipment.tracking_number} to {shipment.destination_city}"
            )

            create_notification(
                title=f"Consignment Dispatched: {shipment.tracking_number}",
                message=f"Dispatched {qty_to_ship}x {goods_item.name} from {shipment.origin_warehouse.city} to {shipment.destination_city}",
                category='DISPATCH',
                link=f"/tracking/{shipment.tracking_number}/"
            )

            messages.success(request, f"Shipment {shipment.tracking_number} dispatched successfully! Transit tracking is now active.")
            return redirect('tracking_detail', tracking_number=shipment.tracking_number)
    else:
        form = ShipmentDispatchForm()

    return render(request, 'logistics/shipment_form.html', {'form': form, 'title': 'Dispatch Goods / New Shipment'})


@login_required
def tracking_view(request, tracking_number=None):
    if not tracking_number:
        query = request.GET.get('tracking_number', '').strip()
        if query:
            return redirect('tracking_detail', tracking_number=query)
        recent_shipments = Shipment.objects.select_related('origin_warehouse', 'vehicle').order_by('-dispatch_time')[:10]
        return render(request, 'logistics/tracking_search.html', {'recent_shipments': recent_shipments})

    shipment = get_object_or_404(
        Shipment.objects.select_related('origin_warehouse', 'vehicle')
        .prefetch_related('items__goods_item', 'checkpoints'),
        tracking_number=tracking_number
    )
    checkpoint_form = CheckpointForm()

    if request.method == 'POST' and 'add_checkpoint' in request.POST:
        checkpoint_form = CheckpointForm(request.POST)
        if checkpoint_form.is_valid():
            checkpoint = checkpoint_form.save(commit=False)
            checkpoint.shipment = shipment
            checkpoint.save()

            create_notification(
                title=f"Waypoint Logged: {shipment.tracking_number}",
                message=f"Milestone reached: {checkpoint.location_name} - {checkpoint.status_note}",
                category='CHECKPOINT',
                link=f"/tracking/{shipment.tracking_number}/"
            )

            messages.success(request, f"Transit checkpoint added at {checkpoint.location_name}.")
            return redirect('tracking_detail', tracking_number=shipment.tracking_number)

    transit_info = shipment.get_transit_duration()

    context = {
        'shipment': shipment,
        'checkpoints': shipment.checkpoints.all(),
        'items': shipment.items.all(),
        'checkpoint_form': checkpoint_form,
        'transit_info': transit_info,
    }
    return render(request, 'logistics/tracking_detail.html', context)


@provider_required
def goods_arrival_view(request, pk):
    shipment = get_object_or_404(
        Shipment.objects.select_related('origin_warehouse', 'vehicle').prefetch_related('items__goods_item'),
        pk=pk
    )

    if request.method == 'POST':
        form = GoodsArrivalForm(request.POST, instance=shipment)
        if form.is_valid():
            shipment = form.save(commit=False)
            shipment.status = 'Delivered'
            if not shipment.actual_arrival:
                shipment.actual_arrival = timezone.now()
            shipment.save()

            if shipment.vehicle:
                shipment.vehicle.status = 'Available'
                shipment.vehicle.save()

            for item in shipment.items.all():
                item.goods_item.status = 'Delivered'
                item.goods_item.save()

            TransitCheckpoint.objects.create(
                shipment=shipment,
                location_name=f"{shipment.destination_city} Destination Terminal",
                status_note=f"Goods arrived safely. Acknowledged by {shipment.received_by_signature_name} in {shipment.delivery_condition} condition.",
                latitude=shipment.dest_latitude,
                longitude=shipment.dest_longitude,
                timestamp=shipment.actual_arrival
            )

            final_duration = shipment.get_transit_duration()['formatted']

            create_notification(
                title=f"Goods Delivered: {shipment.tracking_number}",
                message=f"Arrived at {shipment.destination_city}. Total transit duration: {final_duration}. Received by {shipment.received_by_signature_name}",
                category='ARRIVAL',
                link=f"/tracking/{shipment.tracking_number}/"
            )

            messages.success(
                request,
                f"Goods Arrival recorded for {shipment.tracking_number}! Total transit duration: {final_duration}. Status marked as Delivered."
            )
            return redirect('tracking_detail', tracking_number=shipment.tracking_number)
    else:
        form = GoodsArrivalForm(instance=shipment, initial={'actual_arrival': timezone.now().strftime('%Y-%m-%dT%H:%M')})

    transit_info = shipment.get_transit_duration()

    return render(request, 'logistics/arrival_update.html', {
        'form': form,
        'shipment': shipment,
        'transit_info': transit_info,
    })


@login_required
def shipment_invoice_view(request, pk):
    shipment = get_object_or_404(
        Shipment.objects.select_related('origin_warehouse', 'vehicle').prefetch_related('items__goods_item'),
        pk=pk
    )
    transit_info = shipment.get_transit_duration()
    return render(request, 'logistics/challan_invoice.html', {
        'shipment': shipment,
        'transit_info': transit_info,
        'print_date': timezone.now(),
    })


# ==========================================
# WAREHOUSE, FLEET & REPORTS
# ==========================================

@provider_required
def warehouse_list_view(request):
    warehouses = Warehouse.objects.annotate(
        goods_types_count=Count('goods', distinct=True)
    ).all()

    if request.method == 'POST':
        form = WarehouseForm(request.POST)
        if form.is_valid():
            wh = form.save()
            messages.success(request, f"Warehouse '{wh.name}' ({wh.code}) created successfully!")
            return redirect('warehouse_list')
    else:
        form = WarehouseForm()

    return render(request, 'logistics/warehouse_list.html', {
        'warehouses': warehouses,
        'form': form
    })


@provider_required
def vehicle_list_view(request):
    vehicles = Vehicle.objects.all()

    if request.method == 'POST':
        form = VehicleForm(request.POST)
        if form.is_valid():
            veh = form.save()
            messages.success(request, f"Vehicle '{veh.vehicle_number}' added to fleet!")
            return redirect('vehicle_list')
    else:
        form = VehicleForm()

    return render(request, 'logistics/vehicle_list.html', {
        'vehicles': vehicles,
        'form': form
    })


@provider_required
def reports_view(request):
    total_goods = GoodsItem.objects.count()
    total_quantity = GoodsItem.objects.aggregate(Sum('quantity'))['quantity__sum'] or 0
    total_value = GoodsItem.objects.aggregate(total=Sum('unit_value'))['total'] or 0
    
    status_summary = GoodsItem.objects.values('status').annotate(total=Count('id'), qty=Sum('quantity'))
    category_summary = GoodsItem.objects.values('category').annotate(total=Count('id'), qty=Sum('quantity'))
    
    delivered_shipments = Shipment.objects.filter(status='Delivered')
    active_shipments = Shipment.objects.filter(status='Dispatched')

    context = {
        'total_goods': total_goods,
        'total_quantity': total_quantity,
        'total_value': total_value,
        'status_summary': status_summary,
        'category_summary': category_summary,
        'delivered_count': delivered_shipments.count(),
        'active_count': active_shipments.count(),
        'delivered_shipments': delivered_shipments[:10],
    }
    return render(request, 'logistics/reports.html', context)


# ==========================================
# CSV / EXCEL DATA AUDITING & EXPORT
# ==========================================

@provider_required
def export_goods_csv(request):
    response = HttpResponse(content_type='text/csv')
    timestamp = timezone.now().strftime('%Y%m%d_%H%M')
    response['Content-Disposition'] = f'attachment; filename="inventory_audit_{timestamp}.csv"'

    writer = csv.writer(response)
    writer.writerow(['SKU', 'Item Name', 'Category', 'Quantity', 'Unit', 'Weight (Kg)', 'Unit Value (INR)', 'Warehouse', 'City', 'Status', 'Last Updated'])

    goods = GoodsItem.objects.select_related('warehouse').all()
    for item in goods:
        writer.writerow([
            item.sku,
            item.name,
            item.get_category_display(),
            item.quantity,
            item.unit,
            item.weight_kg,
            item.unit_value,
            item.warehouse.name if item.warehouse else 'Unallocated',
            item.warehouse.city if item.warehouse else '-',
            item.status,
            item.updated_at.strftime('%Y-%m-%d %H:%M')
        ])

    return response


@provider_required
def export_transit_csv(request):
    response = HttpResponse(content_type='text/csv')
    timestamp = timezone.now().strftime('%Y%m%d_%H%M')
    response['Content-Disposition'] = f'attachment; filename="transit_durations_report_{timestamp}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Tracking Number', 'Origin Hub', 'Origin City', 'Destination City',
        'Consignee Name', 'Vehicle Number', 'Driver Name',
        'Departure Time', 'Actual Arrival Time', 'Calculated Transit Duration',
        'Delivery Condition', 'Recipient Sign-off', 'Status'
    ])

    shipments = Shipment.objects.select_related('origin_warehouse', 'vehicle').order_by('-dispatch_time')
    for s in shipments:
        writer.writerow([
            s.tracking_number,
            s.origin_warehouse.name,
            s.origin_warehouse.city,
            s.destination_city,
            s.recipient_name,
            s.vehicle.vehicle_number if s.vehicle else 'Freight',
            s.vehicle.driver_name if s.vehicle else 'Commercial',
            s.dispatch_time.strftime('%Y-%m-%d %H:%M') if s.dispatch_time else '-',
            s.actual_arrival.strftime('%Y-%m-%d %H:%M') if s.actual_arrival else 'In Transit',
            s.transit_duration_display,
            s.delivery_condition,
            s.received_by_signature_name or 'Pending',
            s.status
        ])

    return response


# ==========================================
# NOTIFICATIONS CENTER
# ==========================================

@login_required
def notifications_view(request):
    notifications = Notification.objects.all()[:30]
    return render(request, 'logistics/notifications.html', {'notifications': notifications})


@login_required
def mark_notifications_read(request):
    Notification.objects.filter(is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect('notifications')


# ==========================================
# COMMERCIAL PROFILE MANAGEMENT
# ==========================================

@provider_required
def provider_profile_view(request):
    """Company profile and commercial credentials for logistics dealer"""
    profile = getattr(request.user, 'profile', None)
    if not profile:
        profile = UserProfile.objects.create(user=request.user, role='PROVIDER')

    if request.method == 'POST':
        form = CompanyProfileUpdateForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Commercial company credentials updated successfully!")
            return redirect('provider_profile')
    else:
        form = CompanyProfileUpdateForm(instance=profile)

    dealer_shipments = Shipment.objects.filter(provider=request.user)
    total_dispatched = dealer_shipments.count()
    delivered_count = dealer_shipments.filter(status='Delivered').count()
    active_warehouses = Warehouse.objects.filter(provider=request.user).count()
    active_fleet = Vehicle.objects.filter(provider=request.user).count()

    context = {
        'profile': profile,
        'form': form,
        'total_dispatched': total_dispatched,
        'delivered_count': delivered_count,
        'active_warehouses': active_warehouses,
        'active_fleet': active_fleet,
    }
    return render(request, 'logistics/provider_profile.html', context)


@consumer_required
def consumer_profile_view(request):
    """Client company profile and delivery address management"""
    profile = getattr(request.user, 'profile', None)
    if not profile:
        profile = UserProfile.objects.create(user=request.user, role='CONSUMER')

    if request.method == 'POST':
        form = CompanyProfileUpdateForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Client profile and contact details updated successfully!")
            return redirect('consumer_profile')
    else:
        form = CompanyProfileUpdateForm(instance=profile)

    context = {
        'profile': profile,
        'form': form,
    }
    return render(request, 'logistics/consumer_profile.html', context)


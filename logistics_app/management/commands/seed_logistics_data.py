import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from logistics_app.models import Warehouse, Vehicle, GoodsItem, Shipment, ShipmentItem, TransitCheckpoint, WarehouseLog


class Command(BaseCommand):
    help = "Seed database with realistic initial logistics data (Warehouses, Fleet, Goods, Shipments, Checkpoints)"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting logistics data seeding..."))

        # 1. Accounts & User Profiles (Provider & Consumer)
        from logistics_app.models import UserProfile, ShipmentRequest

        # 1a. Superuser / Operations Admin
        admin_user, created = User.objects.get_or_create(username='admin', defaults={'email': 'admin@logistics.local'})
        if created or not admin_user.check_password('admin123'):
            admin_user.set_password('admin123')
            admin_user.is_superuser = True
            admin_user.is_staff = True
            admin_user.save()
        admin_profile, _ = UserProfile.objects.get_or_create(
            user=admin_user,
            defaults={
                'role': 'PROVIDER',
                'company_name': 'LogiTrack Operations Central',
                'business_type': 'Logistics Operations Authority',
                'gstin_or_tax_id': '27AAACL0000A1Z5',
                'phone': '+91 98200 11223',
                'city': 'Mumbai',
                'address': 'Corporate Central Headquarters, BKC, Mumbai'
            }
        )
        self.stdout.write(self.style.SUCCESS("Seeded admin user: 'admin' (password: 'admin123')"))

        # 1b. Logistics Service Provider Account
        provider_user, created = User.objects.get_or_create(username='provider', defaults={'email': 'provider@logistics.local', 'first_name': 'Dispatcher'})
        if created or not provider_user.check_password('provider123'):
            provider_user.set_password('provider123')
            provider_user.is_staff = True
            provider_user.save()
        prov_profile, _ = UserProfile.objects.get_or_create(
            user=provider_user,
            defaults={
                'role': 'PROVIDER',
                'company_name': 'Express Freight Operations',
                'business_type': '3PL Logistics Provider',
                'gstin_or_tax_id': '27AABCU9603R1ZM',
                'phone': '+91 98201 99887',
                'city': 'Mumbai',
                'address': 'Plot 42, Bhiwandi Logistics Industrial Corridor, Mumbai - 421302'
            }
        )
        prov_profile.gstin_or_tax_id = '27AABCU9603R1ZM'
        prov_profile.business_type = '3PL Logistics Provider'
        prov_profile.address = 'Plot 42, Bhiwandi Logistics Industrial Corridor, Mumbai - 421302'
        prov_profile.save()
        self.stdout.write(self.style.SUCCESS("Seeded provider user: 'provider' (password: 'provider123')"))

        # 1c. Consumer / Client Consignee Account
        consumer_user, created = User.objects.get_or_create(username='consumer', defaults={'email': 'contact@relianceretail.com', 'first_name': 'Reliance Logistics'})
        if created or not consumer_user.check_password('consumer123'):
            consumer_user.set_password('consumer123')
            consumer_user.save()
        cons_profile, _ = UserProfile.objects.get_or_create(
            user=consumer_user,
            defaults={
                'role': 'CONSUMER',
                'company_name': 'Reliance Retail Hub, Pune',
                'business_type': 'Corporate Enterprise',
                'gstin_or_tax_id': '27AABCR8899K1Z4',
                'phone': '+91 98220 55667',
                'city': 'Pune',
                'address': 'Plot 15, Chakan MIDC Phase 3, Pune - 410501'
            }
        )
        cons_profile.gstin_or_tax_id = '27AABCR8899K1Z4'
        cons_profile.business_type = 'Corporate Enterprise'
        cons_profile.address = 'Plot 15, Chakan MIDC Phase 3, Pune - 410501'
        cons_profile.save()
        self.stdout.write(self.style.SUCCESS("Seeded consumer user: 'consumer' (password: 'consumer123')"))

        # 2. Warehouses
        wh_data = [
            {
                'name': 'Western Central Logistics Hub',
                'code': 'WH-BOM-01',
                'location': 'Plot 42, Bhiwandi Logistics Industrial Corridor',
                'city': 'Mumbai',
                'capacity': 15000,
                'supervisor_name': 'Rajesh Deshmukh',
                'contact_number': '+91 98201 44556',
            },
            {
                'name': 'Northern Distribution Terminal',
                'code': 'WH-DEL-02',
                'location': 'Sector 37 Industrial Area, Kundli Gateway',
                'city': 'Delhi NCR',
                'capacity': 22000,
                'supervisor_name': 'Virender Sharma',
                'contact_number': '+91 98110 33441',
            },
            {
                'name': 'Southern Tech Cargo Facility',
                'code': 'WH-BLR-03',
                'location': 'Peenya Industrial Estate, Phase II',
                'city': 'Bengaluru',
                'capacity': 18000,
                'supervisor_name': 'Karthik Raman',
                'contact_number': '+91 99800 77889',
            },
            {
                'name': 'Eastern Port Logistics Depot',
                'code': 'WH-CCU-04',
                'location': 'Taratala Industrial Freight Hub',
                'city': 'Kolkata',
                'capacity': 12000,
                'supervisor_name': 'Anirban Mukherjee',
                'contact_number': '+91 98300 22119',
            }
        ]

        warehouses = []
        for w in wh_data:
            wh, _ = Warehouse.objects.get_or_create(code=w['code'], defaults={**w, 'provider': provider_user})
            if not wh.provider:
                wh.provider = provider_user
                wh.save()
            warehouses.append(wh)
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(warehouses)} warehouses."))

        # 3. Fleet & Vehicles
        veh_data = [
            {'vehicle_number': 'MH-04-AZ-8921', 'vehicle_type': 'Container Truck', 'driver_name': 'Ramesh Yadav', 'driver_phone': '+91 98765 12340', 'capacity_kg': 12000.00, 'status': 'In Transit'},
            {'vehicle_number': 'DL-1L-BX-3402', 'vehicle_type': 'Medium Duty Truck', 'driver_name': 'Harpreet Singh', 'driver_phone': '+91 98123 45671', 'capacity_kg': 6500.00, 'status': 'In Transit'},
            {'vehicle_number': 'KA-01-MJ-6712', 'vehicle_type': 'Refrigerated Reefer', 'driver_name': 'M. Shivakumar', 'driver_phone': '+91 94480 89123', 'capacity_kg': 5000.00, 'status': 'Available'},
            {'vehicle_number': 'WB-02-CP-9011', 'vehicle_type': 'Mini Truck / Pickup', 'driver_name': 'Subrata Roy', 'driver_phone': '+91 98311 65432', 'capacity_kg': 2500.00, 'status': 'Available'},
            {'vehicle_number': 'MH-12-QQ-4520', 'vehicle_type': 'Flatbed Carrier', 'driver_name': 'Santosh Patil', 'driver_phone': '+91 99750 11223', 'capacity_kg': 18000.00, 'status': 'In Transit'},
        ]

        vehicles = []
        for v in veh_data:
            veh, _ = Vehicle.objects.get_or_create(vehicle_number=v['vehicle_number'], defaults={**v, 'provider': provider_user})
            if not veh.provider:
                veh.provider = provider_user
                veh.save()
            vehicles.append(veh)
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(vehicles)} fleet vehicles."))

        # 4. Goods Items
        goods_catalog = [
            {'name': 'Precision CNC Servo Motors 5kW', 'category': 'Industrial Equipment', 'quantity': 45, 'unit': 'Units', 'weight_kg': 28.5, 'unit_value': 48000.00, 'warehouse': warehouses[0], 'status': 'Available', 'description': 'Heavy duty CNC machine replacement motors, high torque precision.'},
            {'name': 'Lyophilized Oncology Vials (Cold Chain)', 'category': 'Pharmaceuticals', 'quantity': 500, 'unit': 'Boxes', 'weight_kg': 0.8, 'unit_value': 3200.00, 'warehouse': warehouses[2], 'status': 'Available', 'description': 'Keep between 2-8°C. Do not freeze. Temperature logger included.'},
            {'name': 'Automotive Transmission Gear Sets', 'category': 'Automotive Parts', 'quantity': 120, 'unit': 'Units', 'weight_kg': 42.0, 'unit_value': 18500.00, 'warehouse': warehouses[0], 'status': 'Available', 'description': 'OEM standard hardened steel 6-speed transmission assembly.'},
            {'name': 'Lithium Iron Phosphate Battery Packs 48V', 'category': 'Electronics', 'quantity': 80, 'unit': 'Units', 'weight_kg': 35.0, 'unit_value': 35000.00, 'warehouse': warehouses[1], 'status': 'Available', 'description': 'Telecom & solar energy storage ESS units. Class 9 Hazmat.'},
            {'name': 'Export Grade Cotton Yarn Spools', 'category': 'Textiles', 'quantity': 350, 'unit': 'Cartons', 'weight_kg': 18.0, 'unit_value': 4200.00, 'warehouse': warehouses[3], 'status': 'Available', 'description': 'Pre-combed organic cotton ring yarn, ready for export dispatch.'},
            {'name': 'Industrial Grade Sodium Hypochlorite 12%', 'category': 'Chemicals & Materials', 'quantity': 60, 'unit': 'Cartons', 'weight_kg': 50.0, 'unit_value': 2800.00, 'warehouse': warehouses[1], 'status': 'Available', 'description': 'Water purification disinfectant agent. UN 1791 rated.'},
            {'name': 'Organic Basmati Rice 25kg Sacks', 'category': 'FMCG', 'quantity': 250, 'unit': 'Boxes', 'weight_kg': 25.0, 'unit_value': 2600.00, 'warehouse': warehouses[1], 'status': 'Available', 'description': 'Premium long grain export quality packed in moisture-proof bags.'},
        ]

        goods_list = []
        for g in goods_catalog:
            sku = f"GDS-{random.randint(100000, 999999)}"
            item, _ = GoodsItem.objects.get_or_create(name=g['name'], defaults={**g, 'sku': sku, 'provider': provider_user})
            if not item.provider:
                item.provider = provider_user
                item.save()
            goods_list.append(item)
            WarehouseLog.objects.get_or_create(
                goods_item=item,
                warehouse=item.warehouse,
                action_type='ADDED',
                defaults={'quantity': item.quantity, 'notes': f'Initial batch stored in {item.warehouse.name}'}
            )
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(goods_list)} goods catalog items."))

        # 5. In-Transit Shipment 1 (Active, Dispatched 6 hours ago, Linked to Consumer & Provider)
        now = timezone.now()
        dispatch_1 = now - timedelta(hours=6, minutes=24)
        s1, s1_created = Shipment.objects.get_or_create(
            tracking_number='LMS-260918-BOM781',
            defaults={
                'provider': provider_user,
                'consumer': consumer_user,
                'origin_warehouse': warehouses[0], # Mumbai
                'vehicle': vehicles[0], # MH-04-AZ-8921
                'destination_hub_or_consignee': 'Reliance Retail Hub, Pune',
                'destination_address': 'Plot 15, Chakan MIDC Phase 3, Pune',
                'destination_city': 'Pune',
                'recipient_name': 'Amit Shinde',
                'recipient_phone': '+91 98220 55667',
                'dispatch_time': dispatch_1,
                'estimated_arrival': now + timedelta(hours=2),
                'status': 'Dispatched',
                'remarks': 'Priority automotive assembly line parts. Deliver to Gate 2.'
            }
        )
        if not s1.provider:
            s1.provider = provider_user
        if not s1.consumer:
            s1.consumer = consumer_user
            s1.destination_hub_or_consignee = 'Reliance Retail Hub, Pune'
        s1.save()

        if s1_created:
            ShipmentItem.objects.create(shipment=s1, goods_item=goods_list[2], quantity_shipped=25)
            TransitCheckpoint.objects.create(shipment=s1, location_name='Bhiwandi Hub, Mumbai', status_note='Consignment loaded and security sealed. Vehicle dispatched.', timestamp=dispatch_1)
            TransitCheckpoint.objects.create(shipment=s1, location_name='Khalapur Toll Plaza', status_note='Expressway transit underway. Vehicle operating at normal speed.', timestamp=dispatch_1 + timedelta(hours=2, minutes=15))
            TransitCheckpoint.objects.create(shipment=s1, location_name='Talegaon Checkpost', status_note='Entered Pune district perimeter. Approaching Chakan MIDC.', timestamp=dispatch_1 + timedelta(hours=4, minutes=40))

        # 5b. Consumer Booking Request (Pending Provider Approval)
        ShipmentRequest.objects.get_or_create(
            consumer=consumer_user,
            goods_name='Solar Inverters 10kVA Hybrid',
            defaults={
                'preferred_provider': provider_user,
                'category': 'Electronics',
                'quantity': 12,
                'unit': 'Units',
                'origin_city': 'Mumbai',
                'destination_city': 'Pune',
                'destination_address': 'Plot 88, Chakan MIDC Phase 2, Pune - 410501',
                'special_instructions': 'Fragile electronics. Require covered transit vehicle with hydraulic tailgate lift.',
                'status': 'Pending'
            }
        )

        # 6. In-Transit Shipment 2 (Dispatched 18 hours ago)
        dispatch_2 = now - timedelta(hours=18, minutes=45)
        s2, s2_created = Shipment.objects.get_or_create(
            tracking_number='LMS-260917-DEL409',
            defaults={
                'provider': provider_user,
                'origin_warehouse': warehouses[1], # Delhi
                'vehicle': vehicles[1], # DL-1L-BX-3402
                'destination_hub_or_consignee': 'Jaipur Tech Energy Substation',
                'destination_address': 'Sitapura Industrial Area, Tonk Road, Jaipur',
                'destination_city': 'Jaipur',
                'recipient_name': 'Maheshwar Verma',
                'recipient_phone': '+91 94140 88221',
                'dispatch_time': dispatch_2,
                'estimated_arrival': now + timedelta(hours=1),
                'status': 'Dispatched',
                'remarks': 'High voltage battery packs. Ensure fire extinguisher is on board.'
            }
        )
        if not s2.provider:
            s2.provider = provider_user
            s2.save()
        if s2_created:
            ShipmentItem.objects.create(shipment=s2, goods_item=goods_list[3], quantity_shipped=15)
            TransitCheckpoint.objects.create(shipment=s2, location_name='Kundli Gateway Hub, Delhi', status_note='Dispatched on NH-48 route towards Jaipur.', timestamp=dispatch_2)
            TransitCheckpoint.objects.create(shipment=s2, location_name='Kotputli Waypoint', status_note='Mid-route inspection completed successfully.', timestamp=dispatch_2 + timedelta(hours=9))
            TransitCheckpoint.objects.create(shipment=s2, location_name='Jaipur Bypass Toll', status_note='Entered city outer ring. Expected at dock shortly.', timestamp=dispatch_2 + timedelta(hours=16))

        # 7. Completed Shipment (Delivered, Demonstrating exact duration tracking & arrival logging)
        dispatch_3 = now - timedelta(days=2, hours=8)
        arrival_3 = now - timedelta(days=1, hours=2)
        s3, s3_created = Shipment.objects.get_or_create(
            tracking_number='LMS-260916-BLR104',
            defaults={
                'provider': provider_user,
                'consumer': consumer_user,
                'origin_warehouse': warehouses[2], # Bengaluru
                'vehicle': vehicles[2],
                'destination_hub_or_consignee': 'Reliance Retail Hub, Pune',
                'destination_address': 'Genome Valley, Shamirpet, Hyderabad',
                'destination_city': 'Hyderabad',
                'recipient_name': 'Dr. K. Srinivas',
                'recipient_phone': '+91 98490 33112',
                'dispatch_time': dispatch_3,
                'estimated_arrival': arrival_3,
                'actual_arrival': arrival_3,
                'status': 'Delivered',
                'delivery_condition': 'Intact',
                'received_by_signature_name': 'K. Srinivas (Chief Pharmacist)',
                'arrival_notes': 'Vials inspected at 3.4°C. Cold chain integrity intact. Barcodes scanned and received at Bay 4.',
                'remarks': 'Cold chain temperature strictly monitored.'
            }
        )
        if not s3.provider:
            s3.provider = provider_user
        if not s3.consumer:
            s3.consumer = consumer_user
        s3.save()
        if s3_created:
            ShipmentItem.objects.create(shipment=s3, goods_item=goods_list[1], quantity_shipped=150)
            TransitCheckpoint.objects.create(shipment=s3, location_name='Peenya Logistics Hub, Bengaluru', status_note='Reefer container set to 4°C. Dispatched on NH-44.', timestamp=dispatch_3)
            TransitCheckpoint.objects.create(shipment=s3, location_name='Anantapur Toll Gateway', status_note='Temperature log checked: 4.1°C. Normal highway transit.', timestamp=dispatch_3 + timedelta(hours=12))
            TransitCheckpoint.objects.create(shipment=s3, location_name='Kurnool Transit Stop', status_note='Driver rest stop & vehicle inspection cleared.', timestamp=dispatch_3 + timedelta(hours=20))
            TransitCheckpoint.objects.create(shipment=s3, location_name='Genome Valley Terminal, Hyderabad', status_note='Safely docked. Consignment handover completed.', timestamp=arrival_3)

        # 8. Customer Enquiries (Customer Portal interaction)
        from logistics_app.models import CustomerEnquiry, Notification
        CustomerEnquiry.objects.get_or_create(
            shipment=s1,
            customer_name='Amit Shinde',
            defaults={
                'customer_email': 'amit.shinde@auto-parts.co.in',
                'customer_phone': '+91 98220 55667',
                'subject': 'Delivery Gate 2 confirmation for servo motors',
                'message': 'Kindly ensure driver approaches via Chakan Gate 2 for overhead crane unloading.',
                'status': 'Pending',
            }
        )
        CustomerEnquiry.objects.get_or_create(
            shipment=s3,
            customer_name='Dr. K. Srinivas',
            defaults={
                'customer_email': 'srinivas@biopharma.org',
                'customer_phone': '+91 98490 33112',
                'subject': 'Cold chain temperature data logger request',
                'message': 'Received goods in perfect condition. Please email the digitized temperature logger certificate.',
                'status': 'Resolved',
                'admin_response': 'Temperature compliance certificate sent to consignee email. Log confirms 3.4°C throughout transit.',
                'resolved_at': arrival_3 + timedelta(hours=2),
            }
        )

        # 9. System Notifications Feed
        Notification.objects.get_or_create(
            title=f"Consignment Dispatched: {s1.tracking_number}",
            defaults={
                'message': f"Dispatched 25x CNC Servo Motors from Mumbai Hub to Pune via MH-04-AZ-8921.",
                'category': 'DISPATCH',
                'link': f"/tracking/{s1.tracking_number}/",
                'is_read': False
            }
        )
        Notification.objects.get_or_create(
            title=f"New Customer Enquiry: {s1.tracking_number}",
            defaults={
                'message': f"From Amit Shinde (+91 98220 55667): 'Delivery Gate 2 confirmation for servo motors'",
                'category': 'ENQUIRY',
                'link': f"/enquiries/",
                'is_read': False
            }
        )
        Notification.objects.get_or_create(
            title=f"Goods Delivered: {s3.tracking_number}",
            defaults={
                'message': f"Successfully arrived at Hyderabad. Total duration: 1d 6h. Received by Dr. K. Srinivas.",
                'category': 'ARRIVAL',
                'link': f"/tracking/{s3.tracking_number}/",
                'is_read': True
            }
        )

        self.stdout.write(self.style.SUCCESS("Logistics demo data & notifications successfully seeded!"))

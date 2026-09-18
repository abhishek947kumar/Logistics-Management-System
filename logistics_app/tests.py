from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from .models import Warehouse, Vehicle, GoodsItem, Shipment, ShipmentItem, TransitCheckpoint, WarehouseLog


class LogisticsSystemTests(TestCase):
    def setUp(self):
        self.warehouse = Warehouse.objects.create(
            name="Mumbai Hub",
            code="WH-MUM",
            location="Bhiwandi",
            city="Mumbai",
            capacity=10000,
            supervisor_name="Supervisor A",
            contact_number="+919876543210"
        )
        self.vehicle = Vehicle.objects.create(
            vehicle_number="MH-04-AB-1234",
            vehicle_type="Container Truck",
            driver_name="Ramesh",
            driver_phone="+919876543211",
            capacity_kg=8000,
            status="Available"
        )
        self.goods = GoodsItem.objects.create(
            name="Electronic Sensors",
            category="Electronics",
            quantity=100,
            unit="Units",
            weight_kg=1.5,
            unit_value=2500,
            warehouse=self.warehouse,
            status="Available"
        )

    def test_goods_creation_and_sku(self):
        self.assertTrue(self.goods.sku.startswith("GDS-"))
        self.assertEqual(self.goods.quantity, 100)
        self.assertEqual(self.goods.warehouse.name, "Mumbai Hub")

    def test_shipment_dispatch_and_duration(self):
        dispatch_time = timezone.now() - timedelta(hours=5, minutes=30)
        shipment = Shipment.objects.create(
            origin_warehouse=self.warehouse,
            vehicle=self.vehicle,
            destination_hub_or_consignee="Pune Hub",
            destination_address="Pune MIDC",
            destination_city="Pune",
            recipient_name="John Doe",
            recipient_phone="+919876500000",
            dispatch_time=dispatch_time,
            status="Dispatched"
        )
        ShipmentItem.objects.create(shipment=shipment, goods_item=self.goods, quantity_shipped=20)

        duration = shipment.get_transit_duration()
        self.assertGreaterEqual(duration['hours'], 5)
        self.assertIn("h", duration['formatted'])
        self.assertFalse(shipment.is_delivered)

    def test_goods_arrival_and_final_duration(self):
        dispatch_time = timezone.now() - timedelta(hours=10)
        arrival_time = timezone.now() - timedelta(hours=2)

        shipment = Shipment.objects.create(
            origin_warehouse=self.warehouse,
            vehicle=self.vehicle,
            destination_hub_or_consignee="Nashik Center",
            destination_address="Nashik City",
            destination_city="Nashik",
            recipient_name="Jane Doe",
            recipient_phone="+919876500001",
            dispatch_time=dispatch_time,
            status="Dispatched"
        )

        # Mark arrived
        shipment.actual_arrival = arrival_time
        shipment.status = "Delivered"
        shipment.received_by_signature_name = "Jane Doe"
        shipment.delivery_condition = "Intact"
        shipment.save()

        self.assertTrue(shipment.is_delivered)
        duration = shipment.get_transit_duration()
        self.assertEqual(duration['hours'], 8)
        self.assertEqual(duration['formatted'], "8h 0m")

    def test_warehouse_activity_log(self):
        log = WarehouseLog.objects.create(
            goods_item=self.goods,
            warehouse=self.warehouse,
            action_type="ADDED",
            quantity=100,
            notes="Initial stock arrival"
        )
        self.assertEqual(log.action_type, "ADDED")
        self.assertEqual(self.warehouse.activity_logs.count(), 1)

    def test_all_views_render_properly(self):
        from django.contrib.auth.models import User
        from logistics_app.models import UserProfile
        user, _ = User.objects.get_or_create(username='tester', defaults={'email': 'tester@test.com'})
        user.set_password('password123')
        user.save()
        UserProfile.objects.get_or_create(user=user, defaults={'role': 'PROVIDER', 'company_name': 'Test Provider Corp'})
        self.client.login(username='tester', password='password123')

        shipment = Shipment.objects.create(
            origin_warehouse=self.warehouse,
            vehicle=self.vehicle,
            destination_hub_or_consignee="Test Consignee",
            destination_address="Test Address",
            destination_city="Test City",
            recipient_name="Tester",
            recipient_phone="+919876543210",
            status="Dispatched"
        )

        urls = [
            '/',
            '/goods/',
            '/goods/add/',
            f'/goods/{self.goods.id}/edit/',
            '/shipments/',
            '/shipments/dispatch/',
            '/tracking/',
            f'/tracking/{shipment.tracking_number}/',
            f'/shipments/{shipment.id}/arrival/',
            f'/shipments/{shipment.id}/invoice/',
            '/warehouses/',
            '/vehicles/',
            '/reports/',
            '/enquiries/',
            '/notifications/',
        ]

        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"URL {url} failed with status {response.status_code}")

    def test_public_tracking_and_enquiry_flow(self):
        # 1. Test unauthenticated public tracking page
        self.client.logout()
        shipment = Shipment.objects.create(
            origin_warehouse=self.warehouse,
            destination_hub_or_consignee="Public Hub",
            destination_address="123 Public St",
            destination_city="Pune",
            recipient_name="Public Consignee",
            recipient_phone="+919876543999",
            status="Dispatched"
        )
        response = self.client.get(f"/track/{shipment.tracking_number}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, shipment.tracking_number)

        # 2. Test submitting enquiry from public portal
        post_data = {
            'customer_name': 'Test Consignee',
            'customer_email': 'consignee@test.com',
            'customer_phone': '+91 98765 00000',
            'subject': 'Delivery Timing Confirmation',
            'message': 'Please confirm delivery time.'
        }
        enquiry_resp = self.client.post(f"/track/{shipment.tracking_number}/enquiry/", data=post_data, follow=True)
        self.assertEqual(enquiry_resp.status_code, 200)
        from logistics_app.models import CustomerEnquiry, Notification
        self.assertEqual(CustomerEnquiry.objects.filter(shipment=shipment).count(), 1)
        self.assertTrue(Notification.objects.filter(category='ENQUIRY').exists())

    def test_csv_audit_exports(self):
        from django.contrib.auth.models import User
        from logistics_app.models import UserProfile
        user, _ = User.objects.get_or_create(username='tester_csv', defaults={'email': 'csv@test.com'})
        user.set_password('password123')
        user.save()
        UserProfile.objects.get_or_create(user=user, defaults={'role': 'PROVIDER', 'company_name': 'Test Provider Corp'})
        self.client.login(username='tester_csv', password='password123')

        # Goods CSV Export
        goods_csv_resp = self.client.get('/reports/export/goods/')
        self.assertEqual(goods_csv_resp.status_code, 200)
        self.assertEqual(goods_csv_resp['Content-Type'], 'text/csv')
        self.assertIn('SKU', goods_csv_resp.content.decode())

        # Transit CSV Export
        transit_csv_resp = self.client.get('/reports/export/transit/')
        self.assertEqual(transit_csv_resp.status_code, 200)
        self.assertEqual(transit_csv_resp['Content-Type'], 'text/csv')
        self.assertIn('Tracking Number', transit_csv_resp.content.decode())

    def test_dual_portal_authentication_and_registration(self):
        from django.contrib.auth.models import User
        from logistics_app.models import UserProfile

        # 1. Consumer self-registration
        reg_data = {
            'username': 'new_retailer',
            'full_name': 'New Retail Hub Pvt Ltd',
            'email': 'retailer@example.com',
            'phone': '+91 99887 76655',
            'city': 'Bengaluru',
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!'
        }
        reg_resp = self.client.post('/consumer/register/', data=reg_data, follow=True)
        self.assertEqual(reg_resp.status_code, 200)
        self.assertTrue(User.objects.filter(username='new_retailer').exists())
        profile = UserProfile.objects.get(user__username='new_retailer')
        self.assertEqual(profile.role, 'CONSUMER')
        self.assertEqual(profile.city, 'Bengaluru')

        # 2. Portal Gateway Select
        self.client.logout()
        portal_resp = self.client.get('/login/')
        self.assertEqual(portal_resp.status_code, 200)
        self.assertContains(portal_resp, "Logistics Provider Portal")
        self.assertContains(portal_resp, "Consumer / Client Portal")

        # 3. Provider Login
        provider_user = User.objects.create_user(username='test_provider', password='provider_password')
        UserProfile.objects.create(user=provider_user, role='PROVIDER', company_name='Test Logistics Corp')

        prov_resp = self.client.post('/provider/login/', data={'username': 'test_provider', 'password': 'provider_password'}, follow=True)
        self.assertEqual(prov_resp.status_code, 200)
        self.assertTrue(prov_resp.context['request'].user.is_authenticated)
        self.assertEqual(prov_resp.context['user_profile'].role, 'PROVIDER')

        # 4. Consumer Login
        self.client.logout()
        cons_resp = self.client.post('/consumer/login/', data={'username': 'new_retailer', 'password': 'SecurePassword123!'}, follow=True)
        self.assertEqual(cons_resp.status_code, 200)
        self.assertTrue(cons_resp.context['request'].user.is_authenticated)
        self.assertEqual(cons_resp.context['user_profile'].role, 'CONSUMER')

    def test_consumer_booking_and_provider_approval_sync(self):
        from django.contrib.auth.models import User
        from logistics_app.models import UserProfile, ShipmentRequest, Shipment

        # Setup users
        consumer = User.objects.create_user(username='client_tata', password='password123')
        UserProfile.objects.create(user=consumer, role='CONSUMER', company_name='Tata Logistics Division', phone='+91 91234 56789', city='Pune')

        provider = User.objects.create_user(username='operator_wh', password='password123')
        UserProfile.objects.create(user=provider, role='PROVIDER', company_name='Provider Hubs')

        # 1. Consumer submits booking request
        self.client.login(username='client_tata', password='password123')
        req_data = {
            'goods_name': 'Industrial Servo Drive 15kW',
            'category': 'Industrial Equipment',
            'quantity': 10,
            'unit': 'Units',
            'origin_city': 'Mumbai',
            'destination_city': 'Pune',
            'destination_address': 'Plot 4, Chakan MIDC, Pune',
            'special_instructions': 'Handle with care'
        }
        submit_resp = self.client.post('/consumer/request/', data=req_data, follow=True)
        self.assertEqual(submit_resp.status_code, 200)

        # Verify request exists in shared database
        self.assertEqual(ShipmentRequest.objects.filter(consumer=consumer).count(), 1)
        booking_req = ShipmentRequest.objects.get(consumer=consumer)
        self.assertEqual(booking_req.status, 'Pending')

        # 2. Provider logs in and views requests inbox
        self.client.logout()
        self.client.login(username='operator_wh', password='password123')

        inbox_resp = self.client.get('/provider/requests/')
        self.assertEqual(inbox_resp.status_code, 200)
        self.assertContains(inbox_resp, "Industrial Servo Drive 15kW")
        self.assertContains(inbox_resp, "Tata Logistics Division")

        # 3. Provider approves booking request -> converts into active Shipment
        approve_data = {
            'warehouse': self.warehouse.id,
            'vehicle': self.vehicle.id,
            'estimated_arrival': (timezone.now() + timedelta(hours=8)).strftime('%Y-%m-%dT%H:%M')
        }
        approve_resp = self.client.post(f'/provider/requests/{booking_req.id}/approve/', data=approve_data, follow=True)
        self.assertEqual(approve_resp.status_code, 200)

        # Verify booking status updated to Approved and linked to new Shipment
        booking_req.refresh_from_db()
        self.assertEqual(booking_req.status, 'Approved')
        self.assertIsNotNone(booking_req.shipment)

        synced_shipment = booking_req.shipment
        self.assertEqual(synced_shipment.consumer, consumer)
        self.assertEqual(synced_shipment.status, 'Dispatched')
        self.assertTrue(synced_shipment.tracking_number.startswith('LMS-'))

        # 4. Consumer logs in and accesses their live shipment tracker
        self.client.logout()
        self.client.login(username='client_tata', password='password123')

        consumer_dash = self.client.get('/consumer/')
        self.assertEqual(consumer_dash.status_code, 200)
        self.assertContains(consumer_dash, synced_shipment.tracking_number)

        detail_resp = self.client.get(f'/consumer/shipments/{synced_shipment.tracking_number}/')
        self.assertEqual(detail_resp.status_code, 200)
        self.assertContains(detail_resp, synced_shipment.tracking_number)
        self.assertContains(detail_resp, "Tata Logistics Division")

    def test_commercial_provider_registration(self):
        from django.contrib.auth.models import User
        from logistics_app.models import UserProfile, Warehouse

        # Test dealer/provider onboarding
        provider_data = {
            'username': 'express_cargo_dealer',
            'company_name': 'Express Cargo Logistics Pvt Ltd',
            'business_type': 'Logistics Carrier / 3PL',
            'gstin_or_tax_id': '27AABCE1234F1Z5',
            'email': 'operations@expresscargo.in',
            'phone': '+91 98200 12345',
            'city': 'Hyderabad',
            'address': 'Plot 10, HiTech Logistics Park, Shamshabad',
            'password': 'SecureCarrierPass123!',
            'confirm_password': 'SecureCarrierPass123!'
        }
        resp = self.client.post('/provider/register/', data=provider_data, follow=True)
        self.assertEqual(resp.status_code, 200)

        # Verify dealer user and commercial profile
        self.assertTrue(User.objects.filter(username='express_cargo_dealer').exists())
        dealer_user = User.objects.get(username='express_cargo_dealer')
        profile = dealer_user.profile
        self.assertEqual(profile.role, 'PROVIDER')
        self.assertEqual(profile.company_name, 'Express Cargo Logistics Pvt Ltd')
        self.assertEqual(profile.gstin_or_tax_id, '27AABCE1234F1Z5')
        self.assertEqual(profile.business_type, 'Logistics Carrier / 3PL')
        self.assertEqual(profile.city, 'Hyderabad')

        # Verify auto-provisioned primary warehouse for new dealer
        dealer_warehouses = Warehouse.objects.filter(provider=dealer_user)
        self.assertEqual(dealer_warehouses.count(), 1)
        wh = dealer_warehouses.first()
        self.assertIn("Express Cargo Logistics Pvt Ltd", wh.name)
        self.assertIn("Hyderabad Terminal", wh.name)
        self.assertEqual(wh.city, 'Hyderabad')

    def test_directed_consumer_booking_and_provider_isolation(self):
        from django.contrib.auth.models import User
        from logistics_app.models import UserProfile, ShipmentRequest, Warehouse, Vehicle

        # Setup Provider A & Provider B
        provider_a = User.objects.create_user(username='carrier_alpha', password='password123')
        UserProfile.objects.create(user=provider_a, role='PROVIDER', company_name='Alpha Freight Lines', gstin_or_tax_id='27AAAAP1111A1Z1')
        wh_a = Warehouse.objects.create(name='Alpha Hub', code='WH-ALPHA', city='Mumbai', provider=provider_a, capacity=5000)
        v_a = Vehicle.objects.create(vehicle_number='MH-01-AA-1111', provider=provider_a, capacity_kg=5000, status='Available')

        provider_b = User.objects.create_user(username='carrier_beta', password='password123')
        UserProfile.objects.create(user=provider_b, role='PROVIDER', company_name='Beta Transport Co', gstin_or_tax_id='29BBBBB2222B1Z2')

        # Setup Consumer
        consumer = User.objects.create_user(username='client_pharma', password='password123')
        UserProfile.objects.create(user=consumer, role='CONSUMER', company_name='Sun Pharma Care')

        # Consumer directs request specifically to Provider A
        self.client.login(username='client_pharma', password='password123')
        req_data = {
            'preferred_provider': provider_a.id,
            'goods_name': 'Temperature-Controlled Vaccines',
            'category': 'Pharmaceuticals',
            'quantity': 50,
            'unit': 'Cartons',
            'origin_city': 'Mumbai',
            'destination_city': 'Ahmedabad',
            'destination_address': 'Cold Storage Unit 3, Ahmedabad',
            'special_instructions': 'Strict cold chain at 2-8 C'
        }
        create_resp = self.client.post('/consumer/request/', data=req_data, follow=True)
        self.assertEqual(create_resp.status_code, 200)

        # Provider B logs in -> should NOT see Provider A's private request
        self.client.logout()
        self.client.login(username='carrier_beta', password='password123')
        beta_inbox = self.client.get('/provider/requests/')
        self.assertEqual(beta_inbox.status_code, 200)
        self.assertNotContains(beta_inbox, "Temperature-Controlled Vaccines")

        # Provider A logs in -> DOES see the request
        self.client.logout()
        self.client.login(username='carrier_alpha', password='password123')
        alpha_inbox = self.client.get('/provider/requests/')
        self.assertEqual(alpha_inbox.status_code, 200)
        self.assertContains(alpha_inbox, "Temperature-Controlled Vaccines")
        self.assertContains(alpha_inbox, "Sun Pharma Care")

        # Provider A approves the directed request
        booking = ShipmentRequest.objects.get(goods_name='Temperature-Controlled Vaccines')
        self.assertEqual(booking.preferred_provider, provider_a)

        approve_data = {
            'warehouse': wh_a.id,
            'vehicle': v_a.id,
            'estimated_arrival': (timezone.now() + timedelta(hours=12)).strftime('%Y-%m-%dT%H:%M')
        }
        approve_resp = self.client.post(f'/provider/requests/{booking.id}/approve/', data=approve_data, follow=True)
        self.assertEqual(approve_resp.status_code, 200)

        booking.refresh_from_db()
        self.assertEqual(booking.status, 'Approved')
        self.assertEqual(booking.shipment.provider, provider_a)
        self.assertEqual(booking.shipment.consumer, consumer)

    def test_commercial_profile_updates(self):
        from django.contrib.auth.models import User
        from logistics_app.models import UserProfile

        # Setup Provider
        p_user = User.objects.create_user(username='profile_provider', password='password123')
        UserProfile.objects.create(user=p_user, role='PROVIDER', company_name='Old Carrier Name')

        self.client.login(username='profile_provider', password='password123')
        update_data = {
            'company_name': 'New Carrier Logistics Ltd',
            'business_type': 'Logistics Carrier / 3PL',
            'gstin_or_tax_id': '07AAAAA0000A1Z5',
            'phone': '+91 99999 88888',
            'city': 'New Delhi',
            'address': 'Cargo Terminal 3, IGI Airport'
        }
        resp = self.client.post('/provider/profile/', data=update_data, follow=True)
        self.assertEqual(resp.status_code, 200)

        p_user.profile.refresh_from_db()
        self.assertEqual(p_user.profile.company_name, 'New Carrier Logistics Ltd')
        self.assertEqual(p_user.profile.gstin_or_tax_id, '07AAAAA0000A1Z5')
        self.assertEqual(p_user.profile.city, 'New Delhi')



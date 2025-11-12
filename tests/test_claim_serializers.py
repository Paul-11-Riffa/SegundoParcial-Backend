"""
Tests exhaustivos para los serializers del sistema de reclamos
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory
from rest_framework.request import Request
from products.models import Product, Category
from sales.models import Order, OrderItem
from claims.models import Claim, ClaimImage
from claims.serializers import (
    ClaimCreateSerializer,
    ClaimUpdateSerializer,
    ClaimDetailSerializer,
    ClaimListSerializer,
    ClaimCustomerFeedbackSerializer,
    ClaimImageSerializer
)
from io import BytesIO
from PIL import Image
import base64


class ClaimCreateSerializerTest(TestCase):
    """Tests para ClaimCreateSerializer"""
    
    def setUp(self):
        """Configurar datos de prueba"""
        # Crear categoría y producto
        self.category = Category.objects.create(name="Electrónicos", slug="electronicos")
        self.product = Product.objects.create(
            name="Laptop Test",
            description="Laptop de prueba",
            price=1000.00,
            stock=10,
            category=self.category
        )
        
        # Crear cliente
        self.customer = User.objects.create_user(
            username="customer_test",
            email="customer@test.com",
            password="testpass123"
        )
        self.customer.profile.role = "CLIENT"
        self.customer.profile.save()
        
        # Crear orden completada
        self.order = Order.objects.create(
            customer=self.customer,
            total_price=1000.00,
            status=Order.OrderStatus.COMPLETED
        )
        
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            price=1000.00
        )
        
        # Request factory para contexto
        self.factory = APIRequestFactory()
    
    def get_request_context(self, user):
        """Helper para crear contexto de request"""
        request = self.factory.post('/api/claims/')
        request.user = user
        # Force authentication
        from rest_framework.test import force_authenticate
        force_authenticate(request, user=user)
        return {'request': Request(request)}
    
    def test_create_claim_valid_data(self):
        """Test: Crear reclamo con datos válidos"""
        data = {
            'order_id': self.order.id,
            'product_id': self.product.id,
            'title': 'Producto defectuoso',
            'description': 'El producto llegó con defectos de fábrica',
            'damage_type': 'FACTORY_DEFECT',
            'priority': 'HIGH'
        }
        
        serializer = ClaimCreateSerializer(
            data=data,
            context=self.get_request_context(self.customer)
        )
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
        claim = serializer.save()
        
        self.assertIsNotNone(claim.ticket_number)
        self.assertEqual(claim.customer, self.customer)
        self.assertEqual(claim.product, self.product)
        self.assertEqual(claim.order, self.order)
        print(f"✓ Reclamo creado exitosamente: {claim.ticket_number}")
    
    def test_create_claim_without_title(self):
        """Test: No permitir crear reclamo sin título"""
        data = {
            'order_id': self.order.id,
            'product_id': self.product.id,
            'description': 'Descripción del problema',
            'damage_type': 'FACTORY_DEFECT',
            'priority': 'HIGH'
        }
        
        serializer = ClaimCreateSerializer(
            data=data,
            context=self.get_request_context(self.customer)
        )
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('title', serializer.errors)
        print("✓ Validación correcta: título es requerido")
    
    def test_create_claim_empty_description(self):
        """Test: No permitir descripción vacía"""
        data = {
            'order_id': self.order.id,
            'product_id': self.product.id,
            'title': 'Producto defectuoso',
            'description': '   ',  # Solo espacios
            'damage_type': 'FACTORY_DEFECT',
            'priority': 'HIGH'
        }
        
        serializer = ClaimCreateSerializer(
            data=data,
            context=self.get_request_context(self.customer)
        )
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('description', serializer.errors)
        print("✓ Validación correcta: descripción no puede estar vacía")
    
    def test_create_claim_order_not_completed(self):
        """Test: No permitir reclamo sobre orden no completada"""
        pending_order = Order.objects.create(
            customer=self.customer,
            total_price=500.00,
            status=Order.OrderStatus.PENDING
        )
        
        OrderItem.objects.create(
            order=pending_order,
            product=self.product,
            quantity=1,
            price=500.00
        )
        
        data = {
            'order_id': pending_order.id,
            'product_id': self.product.id,
            'title': 'Producto defectuoso',
            'description': 'Descripción del problema',
            'damage_type': 'FACTORY_DEFECT',
            'priority': 'HIGH'
        }
        
        serializer = ClaimCreateSerializer(
            data=data,
            context=self.get_request_context(self.customer)
        )
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('order_id', serializer.errors)
        print("✓ Validación correcta: solo órdenes completadas")
    
    def test_create_claim_order_not_owned(self):
        """Test: No permitir reclamo sobre orden de otro usuario"""
        other_user = User.objects.create_user(
            username="other_user",
            email="other@test.com",
            password="testpass123"
        )
        
        other_order = Order.objects.create(
            customer=other_user,
            total_price=1000.00,
            status=Order.OrderStatus.COMPLETED
        )
        
        OrderItem.objects.create(
            order=other_order,
            product=self.product,
            quantity=1,
            price=1000.00
        )
        
        data = {
            'order_id': other_order.id,
            'product_id': self.product.id,
            'title': 'Producto defectuoso',
            'description': 'Descripción del problema',
            'damage_type': 'FACTORY_DEFECT',
            'priority': 'HIGH'
        }
        
        serializer = ClaimCreateSerializer(
            data=data,
            context=self.get_request_context(self.customer)
        )
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('order_id', serializer.errors)
        print("✓ Validación correcta: orden debe pertenecer al usuario")
    
    def test_create_claim_product_not_in_order(self):
        """Test: No permitir reclamo de producto que no está en la orden"""
        other_product = Product.objects.create(
            name="Otro producto",
            price=500.00,
            stock=5,
            category=self.category
        )
        
        data = {
            'order_id': self.order.id,
            'product_id': other_product.id,
            'title': 'Producto defectuoso',
            'description': 'Descripción del problema',
            'damage_type': 'FACTORY_DEFECT',
            'priority': 'HIGH'
        }
        
        serializer = ClaimCreateSerializer(
            data=data,
            context=self.get_request_context(self.customer)
        )
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('product_id', serializer.errors)
        print("✓ Validación correcta: producto debe estar en la orden")


class ClaimUpdateSerializerTest(TestCase):
    """Tests para ClaimUpdateSerializer"""
    
    def setUp(self):
        """Configurar datos de prueba"""
        # Crear categoría y producto
        self.category = Category.objects.create(name="Electrónicos", slug="electronicos")
        self.product = Product.objects.create(
            name="Laptop Test",
            price=1000.00,
            stock=10,
            category=self.category
        )
        
        # Crear cliente y admin
        self.customer = User.objects.create_user(
            username="customer_test",
            email="customer@test.com",
            password="testpass123"
        )
        
        self.admin = User.objects.create_user(
            username="admin_test",
            email="admin@test.com",
            password="adminpass123",
            is_staff=True
        )
        self.admin.profile.role = "ADMIN"
        self.admin.profile.save()
        
        # Crear orden completada
        self.order = Order.objects.create(
            customer=self.customer,
            total_price=1000.00,
            status=Order.OrderStatus.COMPLETED
        )
        
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            price=1000.00
        )
        
        # Crear reclamo
        self.claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Producto defectuoso',
            description='El producto llegó con defectos',
            damage_type='FACTORY_DEFECT',
            priority='MEDIUM',
            status='PENDING'
        )
        
        self.factory = APIRequestFactory()
    
    def get_request_context(self, user):
        """Helper para crear contexto de request"""
        request = self.factory.patch(f'/api/claims/{self.claim.id}/')
        request.user = user
        # Force authentication
        from rest_framework.test import force_authenticate
        force_authenticate(request, user=user)
        return {'request': Request(request)}
    
    def test_update_claim_status(self):
        """Test: Actualizar estado del reclamo"""
        data = {
            'status': 'IN_REVIEW',
            'admin_response': 'Estamos revisando tu caso'
        }
        
        serializer = ClaimUpdateSerializer(
            self.claim,
            data=data,
            partial=True,
            context=self.get_request_context(self.admin)
        )
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_claim = serializer.save()
        
        self.assertEqual(updated_claim.status, 'IN_REVIEW')
        self.assertEqual(updated_claim.admin_response, 'Estamos revisando tu caso')
        
        # Verificar que se creó historial
        self.assertTrue(updated_claim.history.exists())
        print("✓ Estado actualizado y registrado en historial")
    
    def test_assign_claim_to_admin(self):
        """Test: Asignar reclamo a administrador"""
        admin2 = User.objects.create_user(
            username="admin2",
            email="admin2@test.com",
            password="adminpass123",
            is_staff=True
        )
        
        data = {
            'assigned_to_id': admin2.id
        }
        
        serializer = ClaimUpdateSerializer(
            self.claim,
            data=data,
            partial=True,
            context=self.get_request_context(self.admin)
        )
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_claim = serializer.save()
        
        self.assertEqual(updated_claim.assigned_to, admin2)
        print(f"✓ Reclamo asignado a {admin2.username}")
    
    def test_cannot_assign_to_non_admin(self):
        """Test: No permitir asignar a usuario no-admin"""
        regular_user = User.objects.create_user(
            username="regular",
            email="regular@test.com",
            password="testpass123"
        )
        
        data = {
            'assigned_to_id': regular_user.id
        }
        
        serializer = ClaimUpdateSerializer(
            self.claim,
            data=data,
            partial=True,
            context=self.get_request_context(self.admin)
        )
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('assigned_to_id', serializer.errors)
        print("✓ Validación correcta: solo se puede asignar a admins")
    
    def test_update_resolution(self):
        """Test: Actualizar resolución del reclamo"""
        self.claim.status = 'IN_REVIEW'
        self.claim.save()
        
        data = {
            'status': 'RESOLVED',
            'resolution_type': 'REPLACEMENT',
            'resolution_notes': 'Producto reemplazado exitosamente'
        }
        
        serializer = ClaimUpdateSerializer(
            self.claim,
            data=data,
            partial=True,
            context=self.get_request_context(self.admin)
        )
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_claim = serializer.save()
        
        self.assertEqual(updated_claim.status, 'RESOLVED')
        self.assertEqual(updated_claim.resolution_type, 'REPLACEMENT')
        self.assertIsNotNone(updated_claim.resolved_at)
        print("✓ Resolución actualizada correctamente")


class ClaimCustomerFeedbackSerializerTest(TestCase):
    """Tests para ClaimCustomerFeedbackSerializer"""
    
    def setUp(self):
        """Configurar datos de prueba"""
        self.category = Category.objects.create(name="Electrónicos", slug="electronicos")
        self.product = Product.objects.create(
            name="Laptop Test",
            price=1000.00,
            stock=10,
            category=self.category
        )
        
        self.customer = User.objects.create_user(
            username="customer_test",
            email="customer@test.com",
            password="testpass123"
        )
        
        self.order = Order.objects.create(
            customer=self.customer,
            total_price=1000.00,
            status=Order.OrderStatus.COMPLETED
        )
        
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            price=1000.00
        )
        
        self.claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Producto defectuoso',
            description='El producto llegó con defectos',
            damage_type='FACTORY_DEFECT',
            priority='MEDIUM',
            status='RESOLVED'  # Debe estar resuelto para dar feedback
        )
        
        self.factory = APIRequestFactory()
    
    def get_request_context(self, user):
        """Helper para crear contexto de request"""
        request = self.factory.patch(f'/api/claims/{self.claim.id}/add_feedback/')
        request.user = user
        # Force authentication
        from rest_framework.test import force_authenticate
        force_authenticate(request, user=user)
        return {'request': Request(request)}
    
    def test_add_customer_feedback(self):
        """Test: Cliente agrega feedback y calificación"""
        data = {
            'customer_rating': 5,
            'customer_feedback': 'Excelente servicio, resolvieron mi problema rápidamente'
        }
        
        serializer = ClaimCustomerFeedbackSerializer(
            self.claim,
            data=data,
            context=self.get_request_context(self.customer)
        )
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_claim = serializer.save()
        
        self.assertEqual(updated_claim.customer_rating, 5)
        self.assertIn('Excelente servicio', updated_claim.customer_feedback)
        print("✓ Feedback del cliente agregado correctamente")
    
    def test_rating_out_of_range(self):
        """Test: No permitir calificación fuera de rango 1-5"""
        data = {
            'customer_rating': 6,
            'customer_feedback': 'Feedback'
        }
        
        serializer = ClaimCustomerFeedbackSerializer(
            self.claim,
            data=data,
            context=self.get_request_context(self.customer)
        )
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('customer_rating', serializer.errors)
        print("✓ Validación correcta: calificación debe estar entre 1 y 5")
    
    def test_feedback_on_unresolved_claim(self):
        """Test: No permitir feedback en reclamo no resuelto"""
        pending_claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Otro reclamo',
            description='Descripción',
            damage_type='FACTORY_DEFECT',
            priority='MEDIUM',
            status='PENDING'  # No resuelto
        )
        
        data = {
            'customer_rating': 5,
            'customer_feedback': 'Buen servicio'
        }
        
        serializer = ClaimCustomerFeedbackSerializer(
            pending_claim,
            data=data,
            context=self.get_request_context(self.customer)
        )
        
        self.assertFalse(serializer.is_valid())
        print("✓ Validación correcta: solo se puede calificar reclamos resueltos")


class ClaimListSerializerTest(TestCase):
    """Tests para ClaimListSerializer"""
    
    def setUp(self):
        """Configurar datos de prueba"""
        self.category = Category.objects.create(name="Electrónicos", slug="electronicos")
        self.product = Product.objects.create(
            name="Laptop Test",
            price=1000.00,
            stock=10,
            category=self.category
        )
        
        self.customer = User.objects.create_user(
            username="customer_test",
            email="customer@test.com",
            password="testpass123"
        )
        
        self.order = Order.objects.create(
            customer=self.customer,
            total_price=1000.00,
            status=Order.OrderStatus.COMPLETED
        )
        
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            price=1000.00
        )
        
        self.claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Producto defectuoso',
            description='El producto llegó con defectos',
            damage_type='FACTORY_DEFECT',
            priority='MEDIUM',
            status='PENDING'
        )
        
        # Agregar imágenes
        ClaimImage.objects.create(claim=self.claim)
        ClaimImage.objects.create(claim=self.claim)
    
    def test_list_serializer_fields(self):
        """Test: Serializer de lista contiene campos correctos"""
        serializer = ClaimListSerializer(self.claim)
        data = serializer.data
        
        # Verificar campos principales
        self.assertIn('ticket_number', data)
        self.assertIn('customer', data)
        self.assertIn('product_name', data)
        self.assertIn('status_display', data)
        self.assertIn('priority_display', data)
        self.assertIn('damage_type_display', data)
        self.assertIn('images_count', data)
        self.assertIn('days_open', data)
        
        # Verificar valores
        self.assertEqual(data['product_name'], 'Laptop Test')
        self.assertEqual(data['images_count'], 2)
        print("✓ ClaimListSerializer contiene todos los campos requeridos")


class ClaimDetailSerializerTest(TestCase):
    """Tests para ClaimDetailSerializer"""
    
    def setUp(self):
        """Configurar datos de prueba"""
        self.category = Category.objects.create(name="Electrónicos", slug="electronicos")
        self.product = Product.objects.create(
            name="Laptop Test",
            price=1000.00,
            stock=10,
            category=self.category
        )
        
        self.customer = User.objects.create_user(
            username="customer_test",
            email="customer@test.com",
            password="testpass123"
        )
        
        self.admin = User.objects.create_user(
            username="admin_test",
            email="admin@test.com",
            password="adminpass123",
            is_staff=True
        )
        
        self.order = Order.objects.create(
            customer=self.customer,
            total_price=1000.00,
            status=Order.OrderStatus.COMPLETED
        )
        
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            price=1000.00
        )
        
        self.claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Producto defectuoso',
            description='El producto llegó con defectos',
            damage_type='FACTORY_DEFECT',
            priority='MEDIUM',
            status='IN_REVIEW',
            assigned_to=self.admin,
            admin_response='Estamos revisando tu caso'
        )
    
    def test_detail_serializer_complete_data(self):
        """Test: Serializer de detalle contiene toda la información"""
        serializer = ClaimDetailSerializer(self.claim)
        data = serializer.data
        
        # Verificar campos completos
        self.assertIn('customer', data)
        self.assertIn('product', data)
        self.assertIn('assigned_to', data)
        self.assertIn('admin_response', data)
        self.assertIn('history', data)
        self.assertIn('images', data)
        
        # Verificar objetos anidados
        self.assertIsInstance(data['customer'], dict)
        self.assertIsInstance(data['product'], dict)
        self.assertIsInstance(data['assigned_to'], dict)
        
        print("✓ ClaimDetailSerializer contiene toda la información completa")

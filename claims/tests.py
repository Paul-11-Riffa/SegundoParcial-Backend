"""
Tests para el sistema de reclamaciones (Claims)
Fase 1: Tests de Modelos
"""
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal

from claims.models import Claim, ClaimImage, ClaimHistory
from sales.models import Order, OrderItem
from products.models import Product, Category


class ClaimModelTest(TestCase):
    """Tests para el modelo Claim"""
    
    def setUp(self):
        """Configuración inicial para los tests"""
        # Crear usuario cliente
        self.customer = User.objects.create_user(
            username='testcustomer',
            password='testpass123',
            email='customer@test.com'
        )
        
        # Crear usuario admin
        self.admin = User.objects.create_user(
            username='testadmin',
            password='adminpass123',
            email='admin@test.com',
            is_staff=True
        )
        
        # Crear categoría y producto
        self.category = Category.objects.create(
            name='Electrónicos',
            slug='electronicos'
        )
        
        self.product = Product.objects.create(
            category=self.category,
            name='Laptop Test',
            description='Laptop para testing',
            price=Decimal('999.99'),
            stock=10
        )
        
        # Crear orden completada
        self.order = Order.objects.create(
            customer=self.customer,
            status=Order.OrderStatus.COMPLETED,
            total_price=Decimal('999.99')
        )
        
        # Crear item de la orden
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            price=self.product.price
        )
    
    def test_create_claim_basic(self):
        """Test: Crear un reclamo básico"""
        claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            order_item=self.order_item,
            title='Laptop llegó dañada',
            description='La pantalla tiene una grieta',
            damage_type=Claim.DamageType.SHIPPING_DAMAGE
        )
        
        self.assertIsNotNone(claim.ticket_number)
        self.assertTrue(claim.ticket_number.startswith('CLM-'))
        self.assertEqual(claim.status, Claim.ClaimStatus.PENDING)
        self.assertEqual(claim.priority, Claim.Priority.MEDIUM)
        self.assertIsNotNone(claim.created_at)
        print(f"✓ Reclamo creado exitosamente: {claim.ticket_number}")
    
    def test_ticket_number_generation(self):
        """Test: Generación automática de número de ticket único"""
        claim1 = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Primer reclamo',
            description='Test'
        )
        
        claim2 = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Segundo reclamo',
            description='Test'
        )
        
        self.assertNotEqual(claim1.ticket_number, claim2.ticket_number)
        self.assertTrue(claim1.ticket_number.startswith('CLM-'))
        self.assertTrue(claim2.ticket_number.startswith('CLM-'))
        print(f"✓ Tickets únicos generados: {claim1.ticket_number}, {claim2.ticket_number}")
    
    def test_auto_priority_factory_defect(self):
        """Test: Prioridad automática para defectos de fábrica"""
        claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Defecto de fábrica',
            description='El producto vino defectuoso',
            damage_type=Claim.DamageType.FACTORY_DEFECT
        )
        
        self.assertEqual(claim.priority, Claim.Priority.HIGH)
        print(f"✓ Prioridad automática asignada: {claim.get_priority_display()}")
    
    def test_validation_product_not_in_order(self):
        """Test: Validación - producto debe pertenecer a la orden"""
        # Crear otro producto que NO está en la orden
        other_product = Product.objects.create(
            category=self.category,
            name='Otro Producto',
            price=Decimal('50.00'),
            stock=5
        )
        
        claim = Claim(
            customer=self.customer,
            order=self.order,
            product=other_product,  # Producto que NO está en la orden
            title='Reclamo inválido',
            description='Test'
        )
        
        with self.assertRaises(ValidationError) as context:
            claim.full_clean()
        
        self.assertIn('product', context.exception.message_dict)
        print("✓ Validación correcta: producto debe pertenecer a la orden")
    
    def test_validation_order_must_be_completed(self):
        """Test: Validación - solo se pueden reclamar órdenes completadas"""
        # Crear orden pendiente
        pending_order = Order.objects.create(
            customer=self.customer,
            status=Order.OrderStatus.PENDING
        )
        
        OrderItem.objects.create(
            order=pending_order,
            product=self.product,
            quantity=1,
            price=self.product.price
        )
        
        claim = Claim(
            customer=self.customer,
            order=pending_order,
            product=self.product,
            title='Reclamo sobre orden pendiente',
            description='Test'
        )
        
        with self.assertRaises(ValidationError) as context:
            claim.full_clean()
        
        self.assertIn('order', context.exception.message_dict)
        print("✓ Validación correcta: solo órdenes completadas pueden tener reclamos")
    
    def test_validation_customer_owns_order(self):
        """Test: Validación - el cliente debe ser dueño de la orden"""
        # Crear otro usuario
        other_customer = User.objects.create_user(
            username='othercustomer',
            password='pass123'
        )
        
        claim = Claim(
            customer=other_customer,  # Diferente al dueño de la orden
            order=self.order,
            product=self.product,
            title='Reclamo de otro usuario',
            description='Test'
        )
        
        with self.assertRaises(ValidationError) as context:
            claim.full_clean()
        
        self.assertIn('order', context.exception.message_dict)
        print("✓ Validación correcta: cliente debe ser dueño de la orden")
    
    def test_validation_customer_rating_range(self):
        """Test: Validación - calificación debe estar entre 1 y 5"""
        claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Test',
            description='Test'
        )
        
        # Calificación inválida: 6
        claim.customer_rating = 6
        with self.assertRaises(ValidationError):
            claim.full_clean()
        
        # Calificación inválida: 0
        claim.customer_rating = 0
        with self.assertRaises(ValidationError):
            claim.full_clean()
        
        # Calificación válida: 5
        claim.customer_rating = 5
        claim.full_clean()  # No debe lanzar error
        
        print("✓ Validación correcta: calificación entre 1 y 5")
    
    def test_claim_status_transitions(self):
        """Test: Transiciones de estado del reclamo"""
        claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Test status',
            description='Test'
        )
        
        # Inicialmente PENDING
        self.assertEqual(claim.status, Claim.ClaimStatus.PENDING)
        
        # Cambiar a IN_REVIEW
        claim.status = Claim.ClaimStatus.IN_REVIEW
        claim.save()
        self.assertEqual(claim.status, Claim.ClaimStatus.IN_REVIEW)
        
        # Cambiar a RESOLVED
        claim.status = Claim.ClaimStatus.RESOLVED
        claim.save()
        self.assertIsNotNone(claim.resolved_at)
        
        print("✓ Transiciones de estado funcionan correctamente")
    
    def test_is_resolved_property(self):
        """Test: Propiedad is_resolved"""
        claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Test',
            description='Test'
        )
        
        self.assertFalse(claim.is_resolved)
        
        claim.status = Claim.ClaimStatus.RESOLVED
        claim.save()
        self.assertTrue(claim.is_resolved)
        
        claim.status = Claim.ClaimStatus.CLOSED
        claim.save()
        self.assertTrue(claim.is_resolved)
        
        print("✓ Propiedad is_resolved funciona correctamente")
    
    def test_days_open_calculation(self):
        """Test: Cálculo de días abiertos"""
        claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Test',
            description='Test'
        )
        
        # Recién creado debería ser 0 días
        self.assertEqual(claim.days_open, 0)
        
        print(f"✓ Días abiertos calculados correctamente: {claim.days_open}")
    
    def test_claim_string_representation(self):
        """Test: Representación en string del reclamo"""
        claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Test',
            description='Test'
        )
        
        expected = f"Reclamo #{claim.ticket_number} - {self.customer.username} - {claim.status}"
        self.assertEqual(str(claim), expected)
        print(f"✓ String representation: {str(claim)}")


class ClaimImageModelTest(TestCase):
    """Tests para el modelo ClaimImage"""
    
    def setUp(self):
        """Configuración inicial"""
        self.customer = User.objects.create_user(
            username='testcustomer',
            password='testpass123'
        )
        
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        self.product = Product.objects.create(
            category=self.category,
            name='Test Product',
            price=Decimal('100.00'),
            stock=10
        )
        
        self.order = Order.objects.create(
            customer=self.customer,
            status=Order.OrderStatus.COMPLETED
        )
        
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            price=self.product.price
        )
        
        self.claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Test Claim',
            description='Test'
        )
    
    def test_create_claim_image(self):
        """Test: Crear imagen para un reclamo"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Crear una imagen de prueba
        image = SimpleUploadedFile(
            name='test_image.jpg',
            content=b'fake image content',
            content_type='image/jpeg'
        )
        
        claim_image = ClaimImage.objects.create(
            claim=self.claim,
            image=image,
            description='Foto del daño'
        )
        
        self.assertIsNotNone(claim_image.uploaded_at)
        self.assertEqual(claim_image.claim, self.claim)
        print(f"✓ Imagen creada exitosamente para reclamo {self.claim.ticket_number}")
    
    def test_multiple_images_per_claim(self):
        """Test: Múltiples imágenes por reclamo"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        for i in range(3):
            image = SimpleUploadedFile(
                name=f'test_image_{i}.jpg',
                content=b'fake image content',
                content_type='image/jpeg'
            )
            
            ClaimImage.objects.create(
                claim=self.claim,
                image=image,
                description=f'Imagen {i+1}'
            )
        
        self.assertEqual(self.claim.images.count(), 3)
        print(f"✓ {self.claim.images.count()} imágenes agregadas al reclamo")


class ClaimHistoryModelTest(TestCase):
    """Tests para el modelo ClaimHistory"""
    
    def setUp(self):
        """Configuración inicial"""
        self.customer = User.objects.create_user(
            username='testcustomer',
            password='testpass123'
        )
        
        self.admin = User.objects.create_user(
            username='testadmin',
            password='adminpass123',
            is_staff=True
        )
        
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        self.product = Product.objects.create(
            category=self.category,
            name='Test Product',
            price=Decimal('100.00'),
            stock=10
        )
        
        self.order = Order.objects.create(
            customer=self.customer,
            status=Order.OrderStatus.COMPLETED
        )
        
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            price=self.product.price
        )
        
        self.claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Test Claim',
            description='Test'
        )
    
    def test_create_history_entry(self):
        """Test: Crear entrada en el historial"""
        history = ClaimHistory.objects.create(
            claim=self.claim,
            user=self.admin,
            action='Cambio de estado',
            old_status=Claim.ClaimStatus.PENDING,
            new_status=Claim.ClaimStatus.IN_REVIEW,
            notes='Comenzando revisión del reclamo'
        )
        
        self.assertEqual(history.claim, self.claim)
        self.assertEqual(history.user, self.admin)
        self.assertIsNotNone(history.timestamp)
        print(f"✓ Entrada de historial creada: {history}")
    
    def test_automatic_history_on_claim_creation(self):
        """Test: Historial automático al crear reclamo (mediante signal)"""
        # Al crear el claim en setUp, debería haberse creado una entrada automática
        self.assertGreater(self.claim.history.count(), 0)
        
        first_history = self.claim.history.first()
        self.assertIn('creado', first_history.action.lower())
        print(f"✓ Historial automático creado: {first_history.action}")
    
    def test_history_ordering(self):
        """Test: Ordenamiento del historial (más reciente primero)"""
        # Crear varias entradas
        ClaimHistory.objects.create(
            claim=self.claim,
            user=self.admin,
            action='Primera acción',
            new_status=Claim.ClaimStatus.IN_REVIEW
        )
        
        ClaimHistory.objects.create(
            claim=self.claim,
            user=self.admin,
            action='Segunda acción',
            new_status=Claim.ClaimStatus.APPROVED
        )
        
        history_entries = self.claim.history.all()
        # El primero debe ser el más reciente
        self.assertEqual(history_entries[0].action, 'Segunda acción')
        print("✓ Historial ordenado correctamente (más reciente primero)")


class ClaimSignalsTest(TestCase):
    """Tests para las señales del sistema de reclamos"""
    
    def setUp(self):
        """Configuración inicial"""
        self.customer = User.objects.create_user(
            username='testcustomer',
            password='testpass123'
        )
        
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        self.product = Product.objects.create(
            category=self.category,
            name='Test Product',
            price=Decimal('100.00'),
            stock=10
        )
        
        self.order = Order.objects.create(
            customer=self.customer,
            status=Order.OrderStatus.COMPLETED
        )
        
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            price=self.product.price
        )
    
    def test_resolved_at_auto_update(self):
        """Test: Campo resolved_at se actualiza automáticamente"""
        claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Test',
            description='Test'
        )
        
        self.assertIsNone(claim.resolved_at)
        
        # Cambiar a RESOLVED
        claim.status = Claim.ClaimStatus.RESOLVED
        claim.save()
        claim.refresh_from_db()
        
        self.assertIsNotNone(claim.resolved_at)
        print(f"✓ Campo resolved_at actualizado automáticamente: {claim.resolved_at}")
    
    def test_closed_at_auto_update(self):
        """Test: Campo closed_at se actualiza automáticamente"""
        claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Test',
            description='Test'
        )
        
        self.assertIsNone(claim.closed_at)
        
        # Cambiar a CLOSED
        claim.status = Claim.ClaimStatus.CLOSED
        claim.save()
        claim.refresh_from_db()
        
        self.assertIsNotNone(claim.closed_at)
        self.assertIsNotNone(claim.resolved_at)  # También debe actualizarse
        print(f"✓ Campos resolved_at y closed_at actualizados: {claim.closed_at}")

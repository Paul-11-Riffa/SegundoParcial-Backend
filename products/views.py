from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Category, Product, ProductImage
from .serializers import CategorySerializer, ProductSerializer, ProductImageSerializer
from .filters import ProductFilter
from api.permissions import IsAdminUser
import os

class CategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestionar categorías.
    - GET: Acceso público (lectura)
    - POST/PUT/DELETE: Solo administradores
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'
    pagination_class = None  # ✅ Deshabilitar paginación
    
    def get_permissions(self):
        """
        Permisos dinámicos:
        - Lectura (GET, HEAD, OPTIONS): Público
        - Escritura (POST, PUT, PATCH, DELETE): Solo admins
        """
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]
    
    # ✅ Cache de 5 minutos para reducir carga (solo en lectura)
    @method_decorator(cache_page(60 * 5))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class ProductViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestión completa de productos.
    
    PERMISOS:
    - GET (Lectura): Acceso público
    - POST/PUT/PATCH/DELETE (Escritura): Solo administradores
    
    Incluye filtros avanzados por categoría, precio, stock y búsqueda.
    
    Ejemplos de uso:
    - GET /api/shop/products/ - Listar todos los productos
    - GET /api/shop/products/3/ - Ver detalle de producto
    - PUT /api/shop/products/3/ - Actualizar producto (admin)
    - POST /api/shop/products/ - Crear producto (admin)
    - DELETE /api/shop/products/3/ - Eliminar producto (admin)
    
    Filtros:
    - /api/shop/products/?name=laptop (buscar por nombre)
    - /api/shop/products/?category_slug=electronics (filtrar por categoría)
    - /api/shop/products/?price_min=100&price_max=500 (rango de precio)
    - /api/shop/products/?in_stock=true (solo productos disponibles)
    - /api/shop/products/?ordering=-price (ordenar por precio descendente)
    """
    # ✅ OPTIMIZADO: select_related para traer la categoría en una sola consulta
    queryset = Product.objects.select_related('category').all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at', 'name', 'stock']
    ordering = ['-created_at']  # Orden por defecto
    pagination_class = None  # ✅ Deshabilitar paginación para admin
    
    def get_queryset(self):
        """
        Filtrar productos según el usuario:
        - Admins: Ven todos los productos (activos e inactivos)
        - Usuarios normales: Solo ven productos activos
        """
        queryset = super().get_queryset()
        
        # Si es admin, mostrar todos los productos
        if self.request.user and self.request.user.is_staff:
            return queryset
        
        # Para usuarios normales y anónimos, solo mostrar productos activos
        return queryset.filter(is_active=True)
    
    def get_permissions(self):
        """
        Permisos dinámicos:
        - Lectura (GET, HEAD, OPTIONS): Público
        - Escritura (POST, PUT, PATCH, DELETE): Solo admins
        """
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]
    
    # ✅ Cache de 2 minutos para reducir carga (solo en lectura)
    @method_decorator(cache_page(60 * 2))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def upload_image(self, request, pk=None):
        """
        Endpoint personalizado para subir/actualizar imagen de un producto.
        POST /api/shop/products/{id}/upload_image/
        
        Body: FormData con campo 'image'
        """
        product = self.get_object()
        
        if 'image' not in request.FILES:
            return Response(
                {'error': 'No se proporcionó ninguna imagen. Use el campo "image".'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        image_file = request.FILES['image']
        
        # Validar tamaño (5MB máximo)
        if image_file.size > 5 * 1024 * 1024:
            return Response(
                {'error': 'La imagen no debe superar 5MB'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar extensión
        valid_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
        ext = os.path.splitext(image_file.name)[1].lower()
        if ext not in valid_extensions:
            return Response(
                {'error': f'Formato no válido. Use: {", ".join(valid_extensions)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Eliminar imagen anterior si existe
        if product.image:
            try:
                if os.path.isfile(product.image.path):
                    os.remove(product.image.path)
            except Exception:
                pass
        
        # Guardar nueva imagen
        product.image = image_file
        product.save()
        
        serializer = self.get_serializer(product)
        return Response({
            'message': 'Imagen actualizada correctamente',
            'product': serializer.data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['delete'], permission_classes=[IsAdminUser])
    def delete_image(self, request, pk=None):
        """
        Endpoint para eliminar la imagen de un producto.
        DELETE /api/shop/products/{id}/delete_image/
        """
        product = self.get_object()
        
        if not product.image:
            return Response(
                {'error': 'Este producto no tiene imagen'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Eliminar archivo físico
        try:
            if os.path.isfile(product.image.path):
                os.remove(product.image.path)
        except Exception as e:
            pass
        
        # Limpiar campo en BD
        product.image = None
        product.save()
        
        return Response(
            {'message': 'Imagen eliminada correctamente'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def toggle_active(self, request, pk=None):
        """
        Endpoint para activar/desactivar un producto rápidamente.
        
        POST /api/shop/products/{id}/toggle_active/
        
        Body (opcional):
        {
            "is_active": true  // o false para forzar un estado específico
        }
        
        Si no se envía is_active, se alterna (toggle) el estado actual.
        """
        product = self.get_object()
        
        # Si se envía is_active en el body, usar ese valor
        if 'is_active' in request.data:
            new_state = request.data.get('is_active')
            product.is_active = new_state
        else:
            # Si no, alternar (toggle) el estado actual
            product.is_active = not product.is_active
        
        product.save()
        
        status_text = "activado" if product.is_active else "desactivado"
        
        return Response({
            'success': True,
            'message': f'Producto "{product.name}" {status_text} correctamente',
            'product': {
                'id': product.id,
                'name': product.name,
                'is_active': product.is_active
            }
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def clean_broken_images(self, request):
        """
        Endpoint para limpiar referencias a imágenes rotas en la BD.
        POST /api/shop/products/clean_broken_images/
        
        Revisa todos los productos y elimina referencias a imágenes que no existen.
        """
        products = Product.objects.exclude(image='').exclude(image=None)
        cleaned_count = 0
        
        for product in products:
            try:
                # Verificar si el archivo existe
                if not os.path.isfile(product.image.path):
                    # Imagen no existe físicamente, limpiar referencia
                    product.image = None
                    product.save()
                    cleaned_count += 1
            except (ValueError, AttributeError):
                # Error al acceder a la ruta, limpiar referencia
                product.image = None
                product.save()
                cleaned_count += 1
        
        return Response({
            'message': f'Limpieza completada. {cleaned_count} imagen(es) rota(s) eliminada(s).',
            'cleaned_count': cleaned_count
        }, status=status.HTTP_200_OK)


class ProductImageViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestionar imágenes de productos (múltiples imágenes).
    
    PERMISOS:
    - GET (Lectura): Acceso público
    - POST/PUT/PATCH/DELETE (Escritura): Solo administradores
    
    Endpoints:
    - GET /api/shop/product-images/ - Listar todas las imágenes
    - GET /api/shop/product-images/{id}/ - Ver detalle de una imagen
    - POST /api/shop/product-images/ - Crear nueva imagen (admin)
    - PUT/PATCH /api/shop/product-images/{id}/ - Actualizar imagen (admin)
    - DELETE /api/shop/product-images/{id}/ - Eliminar imagen (admin)
    - POST /api/shop/product-images/bulk_upload/ - Subir múltiples imágenes (admin)
    - POST /api/shop/product-images/{id}/set_primary/ - Marcar como principal (admin)
    """
    queryset = ProductImage.objects.select_related('product').all()
    serializer_class = ProductImageSerializer
    pagination_class = None
    
    def get_permissions(self):
        """
        Permisos dinámicos:
        - Lectura (GET, HEAD, OPTIONS): Público
        - Escritura (POST, PUT, PATCH, DELETE): Solo admins
        """
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """
        Permite filtrar imágenes por producto usando query param.
        Ejemplo: /api/shop/product-images/?product=1
        """
        queryset = super().get_queryset()
        product_id = self.request.query_params.get('product', None)
        
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        return queryset.order_by('order')
    
    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def bulk_upload(self, request):
        """
        Endpoint para subir múltiples imágenes a un producto de una vez.
        
        POST /api/shop/product-images/bulk_upload/
        
        FormData:
        - product: ID del producto (requerido)
        - images: Array de archivos de imagen (requerido)
        - alt_text: Texto alternativo (opcional)
        - start_order: Orden inicial (opcional, default: 0)
        
        Ejemplo con JavaScript:
        ```javascript
        const formData = new FormData();
        formData.append('product', productId);
        files.forEach(file => {
            formData.append('images', file);
        });
        formData.append('start_order', 0);
        
        fetch('/api/shop/product-images/bulk_upload/', {
            method: 'POST',
            headers: { 'Authorization': 'Token ...' },
            body: formData
        });
        ```
        """
        # Aceptar tanto "product" como "product_id" para flexibilidad
        product_id = request.data.get('product') or request.data.get('product_id')
        
        if not product_id:
            return Response(
                {'error': 'El campo "product" o "product_id" es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Producto no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Obtener imágenes del request
        images = request.FILES.getlist('images')
        
        if not images:
            return Response(
                {'error': 'No se proporcionaron imágenes. Use el campo "images"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener configuración opcional
        alt_text = request.data.get('alt_text', '')
        start_order = int(request.data.get('start_order', 0))
        
        created_images = []
        errors = []
        
        for idx, image_file in enumerate(images):
            try:
                # Validar tamaño
                if image_file.size > 5 * 1024 * 1024:
                    errors.append(f'{image_file.name}: Imagen supera 5MB')
                    continue
                
                # Validar extensión
                valid_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
                ext = os.path.splitext(image_file.name)[1].lower()
                if ext not in valid_extensions:
                    errors.append(f'{image_file.name}: Formato no válido')
                    continue
                
                # Crear ProductImage
                product_image = ProductImage.objects.create(
                    product=product,
                    image=image_file,
                    order=start_order + idx,
                    alt_text=alt_text or f'{product.name} - Imagen {idx + 1}'
                )
                
                created_images.append(product_image)
            
            except Exception as e:
                errors.append(f'{image_file.name}: {str(e)}')
        
        # Serializar imágenes creadas
        serializer = self.get_serializer(created_images, many=True)
        
        return Response({
            'success': True,
            'message': f'{len(created_images)} imagen(es) subida(s) correctamente',
            'created_count': len(created_images),
            'error_count': len(errors),
            'images': serializer.data,
            'errors': errors if errors else None
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def set_primary(self, request, pk=None):
        """
        Marca una imagen como principal del producto.
        
        POST /api/shop/product-images/{id}/set_primary/
        
        Automáticamente desmarca las demás imágenes del mismo producto.
        """
        product_image = self.get_object()
        
        # Desmarcar todas las imágenes del producto como principales
        ProductImage.objects.filter(
            product=product_image.product,
            is_primary=True
        ).update(is_primary=False)
        
        # Marcar esta como principal
        product_image.is_primary = True
        product_image.save()
        
        serializer = self.get_serializer(product_image)
        return Response({
            'message': 'Imagen marcada como principal',
            'image': serializer.data
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def reorder(self, request):
        """
        Reordena múltiples imágenes de un producto.
        
        POST /api/shop/product-images/reorder/
        
        Body (Opción 1 - con product):
        {
            "product": 1,
            "image_orders": [
                {"id": 5, "order": 0},
                {"id": 3, "order": 1}
            ]
        }
        
        Body (Opción 2 - sin product, solo imágenes):
        {
            "image_orders": [
                {"id": 5, "order": 0},
                {"id": 3, "order": 1}
            ]
        }
        
        Body (Opción 3 - reorder_data para compatibilidad):
        {
            "reorder_data": [
                {"id": 5, "order": 0},
                {"id": 3, "order": 1}
            ]
        }
        """
        # Aceptar múltiples formatos para flexibilidad
        product_id = request.data.get('product') or request.data.get('product_id')
        image_orders = (
            request.data.get('image_orders') or 
            request.data.get('reorder_data') or 
            []
        )
        
        # Si no hay product_id pero hay image_orders, obtenerlo de la primera imagen
        if not product_id and image_orders and len(image_orders) > 0:
            first_image_id = image_orders[0].get('id')
            if first_image_id:
                try:
                    first_image = ProductImage.objects.get(id=first_image_id)
                    product_id = first_image.product.id
                except ProductImage.DoesNotExist:
                    pass
        
        if not image_orders:
            return Response(
                {'error': 'El campo "image_orders" o "reorder_data" es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar que product_id sea válido si se proporcionó
        if product_id:
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                return Response(
                    {'error': 'Producto no encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        updated_count = 0
        errors = []
        
        for item in image_orders:
            image_id = item.get('id')
            new_order = item.get('order')
            
            if image_id is not None and new_order is not None:
                try:
                    # Si tenemos product_id, verificar que la imagen pertenezca al producto
                    if product_id:
                        product_image = ProductImage.objects.get(
                            id=image_id,
                            product_id=product_id
                        )
                    else:
                        # Si no, solo buscar por ID
                        product_image = ProductImage.objects.get(id=image_id)
                    
                    product_image.order = new_order
                    product_image.save()
                    updated_count += 1
                except ProductImage.DoesNotExist:
                    errors.append(f'Imagen {image_id} no encontrada')
                except Exception as e:
                    errors.append(f'Error con imagen {image_id}: {str(e)}')
        
        response_data = {
            'success': True,
            'message': f'{updated_count} imagen(es) reordenada(s) correctamente',
            'updated_count': updated_count
        }
        
        if errors:
            response_data['errors'] = errors
        
        return Response(response_data)

from rest_framework import serializers
from .models import Category, Product, ProductImage
import os


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo de Categorías.
    """
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


class ProductImageSerializer(serializers.ModelSerializer):
    """
    Serializador para imágenes de productos.
    Devuelve URL validada de la imagen.
    """
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductImage
        fields = [
            'id',
            'image',
            'image_url',
            'order',
            'is_primary',
            'alt_text',
            'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_image_url(self, obj):
        """
        Devuelve la URL completa de la imagen si existe.
        Compatible con almacenamiento local y Cloudinary.
        """
        if obj.image:
            try:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.image.url)
                return obj.image.url
            except (ValueError, AttributeError):
                pass
        return None
    
    def validate_image(self, value):
        """
        Valida el archivo de imagen subido.
        """
        if value:
            # Validar tamaño (máximo 5MB)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("La imagen no debe superar 5MB")
            
            # Validar tipo de archivo
            valid_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
            ext = os.path.splitext(value.name)[1].lower()
            if ext not in valid_extensions:
                raise serializers.ValidationError(
                    f"Formato de imagen no válido. Use: {', '.join(valid_extensions)}"
                )
        
        return value


class ProductSerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo de Productos.
    
    CAMPOS:
    - category: ID de la categoría (lectura y escritura)
    - category_name: Nombre de la categoría (solo lectura)
    - category_slug: Slug de la categoría (solo lectura)
    - category_detail: Objeto completo de categoría (solo lectura)
    - image: Archivo de imagen legacy (puede ser null)
    - image_url: URL segura de la imagen legacy (null si no existe)
    - has_valid_image: Indica si tiene imagen legacy válida
    - images: Lista de todas las imágenes del producto (ProductImage)
    - primary_image: Imagen principal del producto
    - all_image_urls: Lista de URLs de todas las imágenes (para galería)
    """
    # Para mostrar información adicional de la categoría (solo lectura)
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.SlugField(source='category.slug', read_only=True)
    
    # ✅ Objeto completo de categoría para el frontend
    category_detail = CategorySerializer(source='category', read_only=True)
    
    # ✅ URL segura de imagen legacy que valida existencia física
    image_url = serializers.SerializerMethodField()
    has_valid_image = serializers.BooleanField(read_only=True)
    
    # ✅ NUEVO: Múltiples imágenes
    images = ProductImageSerializer(many=True, read_only=True)
    primary_image = serializers.SerializerMethodField()
    all_image_urls = serializers.SerializerMethodField()
    image_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id',
            'category',           # ID para lectura/escritura
            'category_name',      # Solo lectura: nombre de categoría
            'category_slug',      # Solo lectura: slug de categoría
            'category_detail',    # Objeto completo para formularios
            'name',
            'description',
            'price',
            'stock',
            'is_active',          # ✅ NUEVO: Estado activo/inactivo
            # Imagen legacy (retrocompatibilidad)
            'image',              # Campo de imagen legacy (puede ser null)
            'image_url',          # URL validada de la imagen legacy
            'has_valid_image',    # Indica si tiene imagen legacy válida
            # Múltiples imágenes (nuevo sistema)
            'images',             # ✅ Lista completa de imágenes
            'primary_image',      # ✅ Imagen principal
            'all_image_urls',     # ✅ Solo URLs (para galería simple)
            'image_count',        # ✅ Cantidad de imágenes
            'created_at',
            'updated_at'
        ]
    
    def get_image_url(self, obj):
        """
        Devuelve la URL de la imagen legacy si existe.
        Compatible con almacenamiento local y Cloudinary.
        Evita errores 404 en el frontend.
        """
        if obj.image:
            try:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.image.url)
                return obj.image.url
            except (ValueError, AttributeError):
                pass
        return None
    
    def get_primary_image(self, obj):
        """
        Devuelve la imagen principal del producto.
        Primero busca en ProductImage (is_primary=True),
        luego la primera por orden, y finalmente la imagen legacy.
        """
        # 1. Buscar imagen principal en ProductImage
        primary = obj.images.filter(is_primary=True).first()
        if primary:
            return ProductImageSerializer(primary, context=self.context).data
        
        # 2. Si no hay principal, tomar la primera por orden
        first_image = obj.images.order_by('order').first()
        if first_image:
            return ProductImageSerializer(first_image, context=self.context).data
        
        # 3. Si no hay imágenes nuevas, usar la imagen legacy
        if obj.image:
            try:
                request = self.context.get('request')
                image_url = request.build_absolute_uri(obj.image.url) if request else obj.image.url
                return {
                    'id': None,
                    'image': obj.image.url,
                    'image_url': image_url,
                    'order': 0,
                    'is_primary': True,
                    'alt_text': obj.name,
                    'created_at': None
                }
            except (ValueError, AttributeError):
                pass
        
        return None
    
    def get_all_image_urls(self, obj):
        """
        Devuelve una lista simple de URLs de todas las imágenes.
        Compatible con almacenamiento local y Cloudinary.
        Útil para galerías simples sin metadatos adicionales.
        """
        urls = []
        request = self.context.get('request')
        
        # Agregar todas las imágenes de ProductImage
        for img in obj.images.order_by('order'):
            if img.image:
                try:
                    url = request.build_absolute_uri(img.image.url) if request else img.image.url
                    urls.append(url)
                except (ValueError, AttributeError):
                    pass
        
        # Si no hay imágenes nuevas, agregar la imagen legacy
        if not urls and obj.image:
            try:
                url = request.build_absolute_uri(obj.image.url) if request else obj.image.url
                urls.append(url)
            except (ValueError, AttributeError):
                pass
        
        return urls
    
    def get_image_count(self, obj):
        """
        Devuelve la cantidad total de imágenes del producto.
        """
        count = obj.images.count()
        # Si no hay imágenes nuevas pero existe la legacy, contar esa
        if count == 0 and obj.image:
            return 1
        return count
    
    def validate_image(self, value):
        """
        Valida el archivo de imagen subido
        """
        if value:
            # Validar tamaño (máximo 5MB)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("La imagen no debe superar 5MB")
            
            # Validar tipo de archivo
            valid_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
            ext = os.path.splitext(value.name)[1].lower()
            if ext not in valid_extensions:
                raise serializers.ValidationError(
                    f"Formato de imagen no válido. Use: {', '.join(valid_extensions)}"
                )
        
        return value
    
    def update(self, instance, validated_data):
        """
        Actualización personalizada para manejar imágenes correctamente.
        Compatible con almacenamiento local y Cloudinary.
        """
        # Si se envía una nueva imagen, eliminar la anterior
        if 'image' in validated_data and validated_data['image']:
            if instance.image:
                try:
                    # Django y Cloudinary manejan la eliminación automáticamente
                    instance.image.delete(save=False)
                except Exception:
                    pass
        
        return super().update(instance, validated_data)
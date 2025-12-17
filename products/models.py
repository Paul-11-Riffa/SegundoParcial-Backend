from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
import os


# Importar cloudinary si está disponible
try:
    import cloudinary
    import cloudinary.uploader
    CLOUDINARY_AVAILABLE = True
except ImportError:
    CLOUDINARY_AVAILABLE = False


class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, help_text="Unique URL-friendly name for the category")

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name
    
    def clean(self):
        """Validaciones personalizadas"""
        if not self.name or not self.name.strip():
            raise ValidationError({'name': 'El nombre de la categoría no puede estar vacío.'})
        
        # Asegurar que el slug no tenga espacios
        if self.slug and ' ' in self.slug:
            raise ValidationError({'slug': 'El slug no puede contener espacios.'})


class Product(models.Model):
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    
    # ✅ NUEVO: Campo para "desactivar" productos sin eliminarlos
    is_active = models.BooleanField(
        default=True,
        help_text="Desmarcar para ocultar el producto sin eliminarlo. Protege el historial de ventas."
    )

    # Campos de fecha automáticos
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at'] # Muestra los productos más nuevos primero

    def __str__(self):
        return self.name
    
    def clean(self):
        """Validaciones personalizadas"""
        errors = {}
        
        # Validar precio
        if self.price is not None and self.price <= 0:
            errors['price'] = 'El precio debe ser mayor a 0.'
        
        # Validar nombre
        if not self.name or not self.name.strip():
            errors['name'] = 'El nombre del producto no puede estar vacío.'
        
        # Validar stock (aunque sea PositiveIntegerField, por si acaso)
        if self.stock < 0:
            errors['stock'] = 'El stock no puede ser negativo.'
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Override save para ejecutar validaciones"""
        self.full_clean()  # Ejecuta clean() y otras validaciones
        super().save(*args, **kwargs)
    
    @property
    def is_available(self):
        """Verifica si el producto está disponible"""
        return self.stock > 0
    
    @property
    def is_low_stock(self):
        """Verifica si el producto tiene stock bajo (menos de 10)"""
        return 0 < self.stock < 10
    
    @property
    def image_url(self):
        """
        Devuelve la URL de la imagen si existe, None si no existe o está rota.
        Compatible con almacenamiento local y Cloudinary.
        """
        if self.image:
            try:
                # En producción con Cloudinary, siempre devolver la URL
                # self.image.url funciona tanto para archivos locales como Cloudinary
                return self.image.url
            except (ValueError, AttributeError):
                pass
        return None
    
    @property
    def has_valid_image(self):
        """Verifica si el producto tiene una imagen válida"""
        return self.image_url is not None
    
    def delete_image(self):
        """
        Elimina la imagen física del producto.
        Compatible con almacenamiento local y Cloudinary.
        """
        if self.image:
            try:
                # Django y Cloudinary manejan la eliminación automáticamente
                # No necesitamos verificar os.path.isfile() en producción
                self.image.delete(save=False)
                self.image = None
                self.save()
                return True
            except Exception:
                pass
        return False
    
    @property
    def primary_image(self):
        """
        Devuelve la imagen principal del producto (desde ProductImage).
        Si no hay, devuelve la imagen legacy del campo 'image'.
        """
        # Intentar obtener imagen marcada como principal
        primary = self.images.filter(is_primary=True).first()
        if primary:
            return primary
        
        # Si no hay principal, devolver la primera por orden
        first_image = self.images.order_by('order').first()
        if first_image:
            return first_image
        
        # Si no hay imágenes en ProductImage, usar el campo legacy 'image'
        return None
    
    @property
    def all_images(self):
        """
        Devuelve todas las imágenes del producto ordenadas.
        Incluye la imagen legacy si existe y no hay imágenes nuevas.
        """
        product_images = self.images.order_by('order').all()
        if product_images.exists():
            return product_images
        
        # Si no hay imágenes nuevas pero existe la imagen legacy
        if self.image:
            # Retornar lista vacía, la imagen legacy se maneja por separado
            return []
        
        return []


class ProductImage(models.Model):
    """
    Modelo para gestionar múltiples imágenes por producto.
    Permite tener varias imágenes ordenadas y marcar una como principal.
    """
    product = models.ForeignKey(
        Product,
        related_name='images',
        on_delete=models.CASCADE,
        help_text="Producto al que pertenece la imagen"
    )
    image = models.ImageField(
        upload_to='products/',
        help_text="Archivo de imagen"
    )
    cloudinary_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="URL de Cloudinary (se genera automáticamente en producción)"
    )
    order = models.IntegerField(
        default=0,
        help_text="Orden de visualización (menor número = primera)"
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Marca esta imagen como la principal (solo una por producto)"
    )
    alt_text = models.CharField(
        max_length=255,
        blank=True,
        help_text="Texto alternativo para accesibilidad"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'product_images'
        ordering = ['order', 'id']
        verbose_name = 'Imagen de Producto'
        verbose_name_plural = 'Imágenes de Productos'
        indexes = [
            models.Index(fields=['product', 'order']),
            models.Index(fields=['product', 'is_primary']),
        ]
    
    def __str__(self):
        primary_text = " (Principal)" if self.is_primary else ""
        return f"{self.product.name} - Imagen {self.order}{primary_text}"
    
    def save(self, *args, **kwargs):
        """
        Override save para:
        1. Subir imagen a Cloudinary en producción
        2. Asegurar que solo hay una imagen principal por producto
        """
        # Si esta imagen se marca como principal, quitar la marca de las demás
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product,
                is_primary=True
            ).exclude(id=self.id).update(is_primary=False)
        
        # En producción, subir a Cloudinary
        if not settings.DEBUG and CLOUDINARY_AVAILABLE and self.image:
            try:
                # Subir a Cloudinary
                result = cloudinary.uploader.upload(
                    self.image,
                    folder="products",
                    resource_type="image",
                    allowed_formats=["jpg", "jpeg", "png", "webp", "gif"],
                )
                
                # Guardar URL de Cloudinary
                self.cloudinary_url = result.get('secure_url')
                print(f"✅ Imagen subida a Cloudinary: {self.cloudinary_url}")
            
            except Exception as e:
                print(f"❌ Error subiendo a Cloudinary: {e}")
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """
        Override delete para eliminar el archivo físico.
        Compatible con almacenamiento local y Cloudinary.
        """
        # Eliminar archivo (Django/Cloudinary lo manejan automáticamente)
        if self.image:
            try:
                self.image.delete(save=False)
            except Exception:
                pass
        
        super().delete(*args, **kwargs)
    
    @property
    def image_url(self):
        """
        Devuelve la URL de la imagen.
        Prioritiza la URL de Cloudinary si está disponible (funciona en desarrollo y producción).
        """
        # Si hay URL de Cloudinary disponible, usarla (funciona en desarrollo y producción)
        if self.cloudinary_url:
            return self.cloudinary_url
        
        # Si no hay URL de Cloudinary, usar la URL del archivo (solo local)
        if self.image:
            try:
                return self.image.url
            except (ValueError, AttributeError):
                pass
        
        return None
    
    def clean(self):
        """
        Validaciones personalizadas.
        """
        if self.order < 0:
            raise ValidationError({'order': 'El orden no puede ser negativo.'})
        
        # Validar tamaño de archivo (5MB máximo)
        if self.image and hasattr(self.image, 'size'):
            if self.image.size > 5 * 1024 * 1024:
                raise ValidationError({'image': 'La imagen no debe superar 5MB.'})
        
        # Validar extensión
        if self.image and hasattr(self.image, 'name'):
            valid_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
            ext = os.path.splitext(self.image.name)[1].lower()
            if ext not in valid_extensions:
                raise ValidationError({
                    'image': f'Formato de imagen no válido. Use: {", ".join(valid_extensions)}'
                })
from django.contrib import admin
from .models import Category, Product, ProductImage


class ProductImageInline(admin.TabularInline):
    """
    Inline para gestionar imágenes de producto directamente desde el admin de Product.
    Permite agregar/editar/eliminar múltiples imágenes sin salir del formulario del producto.
    """
    model = ProductImage
    extra = 1  # Cuántas filas vacías mostrar por defecto
    fields = ['image', 'order', 'is_primary', 'alt_text']
    ordering = ['order']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Administración personalizada para Categorías.
    """
    list_display = ['name', 'slug']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}  # Auto-generar slug desde el nombre


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Administración personalizada para Productos.
    Incluye gestión de múltiples imágenes inline.
    """
    list_display = ['name', 'category', 'price', 'stock', 'is_active', 'created_at', 'image_count']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'image_count']
    list_editable = ['is_active']  # ✅ Permite activar/desactivar rápidamente desde la lista
    
    # Incluir el inline de imágenes
    inlines = [ProductImageInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'category', 'description')
        }),
        ('Precio y Stock', {
            'fields': ('price', 'stock')
        }),
        ('Estado del Producto', {
            'fields': ('is_active',),
            'description': '⚠️ Desmarcar para DESACTIVAR el producto sin eliminarlo. '
                          'Esto protege el historial de ventas. El producto no se mostrará '
                          'en la tienda pero seguirá visible en reportes.'
        }),
        ('Imagen Legacy (Opcional)', {
            'fields': ('image',),
            'description': 'Imagen única antigua. Recomendado: usar "Imágenes de Productos" abajo.'
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at', 'image_count'),
            'classes': ('collapse',)
        }),
    )
    
    def image_count(self, obj):
        """Muestra la cantidad de imágenes que tiene el producto."""
        return obj.images.count()
    image_count.short_description = 'Cantidad de Imágenes'
    
    def delete_model(self, request, obj):
        """
        Sobrescribe la eliminación para mostrar advertencia.
        Si el producto tiene ventas, NO se elimina.
        """
        from django.contrib import messages
        
        # Verificar si tiene ventas (OrderItems)
        ventas_count = obj.order_items.count()
        
        if ventas_count > 0:
            messages.error(
                request,
                f'⚠️ NO SE PUEDE ELIMINAR: El producto "{obj.name}" tiene {ventas_count} '
                f'venta(s) registrada(s). En lugar de eliminarlo, DESACTÍVALO desmarcando '
                f'el campo "is_active". Esto lo ocultará de la tienda pero protegerá '
                f'el historial de ventas y reportes.'
            )
            return  # No eliminar
        
        # Si no tiene ventas, permitir eliminación
        messages.success(
            request,
            f'✅ Producto "{obj.name}" eliminado correctamente (no tenía ventas registradas).'
        )
        super().delete_model(request, obj)
    
    def delete_queryset(self, request, queryset):
        """
        Sobrescribe eliminación masiva para proteger productos con ventas.
        """
        from django.contrib import messages
        
        productos_con_ventas = []
        productos_sin_ventas = []
        
        for producto in queryset:
            if producto.order_items.count() > 0:
                productos_con_ventas.append(producto.name)
            else:
                productos_sin_ventas.append(producto)
        
        if productos_con_ventas:
            messages.error(
                request,
                f'⚠️ NO SE PUEDEN ELIMINAR {len(productos_con_ventas)} producto(s) '
                f'porque tienen ventas: {", ".join(productos_con_ventas[:5])}... '
                f'Desactívalos en lugar de eliminarlos.'
            )
        
        if productos_sin_ventas:
            count = len(productos_sin_ventas)
            for producto in productos_sin_ventas:
                producto.delete()
            messages.success(
                request,
                f'✅ {count} producto(s) sin ventas eliminado(s) correctamente.'
            )
        
        if not productos_sin_ventas and not productos_con_ventas:
            messages.info(request, 'No se seleccionaron productos para eliminar.')


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    """
    Administración independiente para imágenes de productos.
    """
    list_display = ['product', 'order', 'is_primary', 'image_thumbnail', 'created_at']
    list_filter = ['is_primary', 'created_at', 'product__category']
    search_fields = ['product__name', 'alt_text']
    readonly_fields = ['created_at', 'image_preview']
    ordering = ['product', 'order']
    
    fieldsets = (
        ('Producto', {
            'fields': ('product',)
        }),
        ('Imagen', {
            'fields': ('image', 'image_preview', 'alt_text')
        }),
        ('Configuración', {
            'fields': ('order', 'is_primary')
        }),
        ('Metadatos', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def image_thumbnail(self, obj):
        """Muestra una miniatura de la imagen en la lista."""
        if obj.image:
            return f'<img src="{obj.image.url}" width="50" height="50" style="object-fit: cover;" />'
        return '-'
    image_thumbnail.short_description = 'Miniatura'
    image_thumbnail.allow_tags = True
    
    def image_preview(self, obj):
        """Muestra una vista previa más grande de la imagen en el formulario."""
        if obj.image:
            return f'<img src="{obj.image.url}" width="300" style="max-width: 100%;" />'
        return 'No hay imagen'
    image_preview.short_description = 'Vista Previa'
    image_preview.allow_tags = True
"""
Utilidades para subir archivos directamente a Cloudinary.
Solución alternativa a django-cloudinary-storage.
"""
from django.conf import settings
import cloudinary
import cloudinary.uploader


def upload_to_cloudinary(file, folder="products"):
    """
    Sube un archivo directamente a Cloudinary.
    
    Args:
        file: Django UploadedFile object
        folder: Carpeta en Cloudinary (default: "products")
    
    Returns:
        str: URL segura de Cloudinary, o None si falla
    """
    # Solo usar Cloudinary en producción
    if settings.DEBUG:
        return None
    
    try:
        # Subir a Cloudinary
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            resource_type="image",
            allowed_formats=["jpg", "jpeg", "png", "webp", "gif"],
        )
        
        # Retornar URL segura
        return result.get('secure_url')
    
    except Exception as e:
        print(f"❌ Error subiendo a Cloudinary: {e}")
        return None


def delete_from_cloudinary(url):
    """
    Elimina una imagen de Cloudinary usando su URL.
    
    Args:
        url: URL de Cloudinary (ej: https://res.cloudinary.com/xxx/image/upload/v123/products/imagen.jpg)
    
    Returns:
        bool: True si se eliminó correctamente
    """
    if settings.DEBUG or not url or 'cloudinary.com' not in url:
        return False
    
    try:
        # Extraer public_id de la URL
        # URL formato: https://res.cloudinary.com/{cloud_name}/image/upload/v{version}/{public_id}.{format}
        parts = url.split('/upload/')
        if len(parts) == 2:
            # Remover versión (v123456/)
            public_id_with_ext = parts[1].split('/', 1)[1] if '/' in parts[1] else parts[1]
            # Remover extensión
            public_id = public_id_with_ext.rsplit('.', 1)[0]
            
            # Eliminar de Cloudinary
            cloudinary.uploader.destroy(public_id)
            return True
    
    except Exception as e:
        print(f"❌ Error eliminando de Cloudinary: {e}")
    
    return False

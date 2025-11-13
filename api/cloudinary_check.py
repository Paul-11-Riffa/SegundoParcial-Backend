"""
Vista de diagnóstico para verificar configuración de Cloudinary en producción.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.conf import settings
import os

@api_view(['GET'])
@permission_classes([AllowAny])  # Temporal para diagnóstico
def cloudinary_status(request):
    """
    Endpoint para verificar el estado de Cloudinary.
    URL: /api/cloudinary-status/
    """
    
    # Verificar DEBUG
    is_debug = settings.DEBUG
    
    # Verificar DEFAULT_FILE_STORAGE
    storage = getattr(settings, 'DEFAULT_FILE_STORAGE', 'NO CONFIGURADO')
    
    # Verificar CLOUDINARY_STORAGE
    cloudinary_config = getattr(settings, 'CLOUDINARY_STORAGE', {})
    
    # Verificar si cloudinary está disponible
    try:
        import cloudinary
        cloudinary_available = True
        cloudinary_version = getattr(cloudinary, '__version__', 'unknown')
    except ImportError:
        cloudinary_available = False
        cloudinary_version = None
    
    # Verificar variables de entorno
    env_vars = {
        'CLOUDINARY_CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME', ''),
        'CLOUDINARY_API_KEY': os.getenv('CLOUDINARY_API_KEY', ''),
        'CLOUDINARY_API_SECRET': bool(os.getenv('CLOUDINARY_API_SECRET', '')),  # No exponer el secret
        'DEBUG': os.getenv('DEBUG', ''),
    }
    
    # Verificar apps instaladas
    installed_cloudinary_apps = [
        app for app in settings.INSTALLED_APPS 
        if 'cloudinary' in app.lower()
    ]
    
    # Determinar estado
    is_configured = (
        not is_debug and
        'cloudinary' in storage.lower() and
        cloudinary_available and
        cloudinary_config.get('CLOUD_NAME') and
        cloudinary_config.get('API_KEY') and
        cloudinary_config.get('API_SECRET')
    )
    
    return Response({
        'status': 'configured' if is_configured else 'not_configured',
        'debug_mode': is_debug,
        'storage_backend': storage,
        'cloudinary_available': cloudinary_available,
        'cloudinary_version': cloudinary_version,
        'cloudinary_storage_config': {
            'CLOUD_NAME': cloudinary_config.get('CLOUD_NAME', 'NOT SET'),
            'API_KEY': cloudinary_config.get('API_KEY', 'NOT SET'),
            'API_SECRET': '***' if cloudinary_config.get('API_SECRET') else 'NOT SET',
        },
        'environment_variables': env_vars,
        'installed_apps': installed_cloudinary_apps,
        'recommendations': get_recommendations(is_debug, storage, cloudinary_available, cloudinary_config)
    })


def get_recommendations(is_debug, storage, cloudinary_available, cloudinary_config):
    """Genera recomendaciones basadas en la configuración actual."""
    recommendations = []
    
    if is_debug:
        recommendations.append("⚠️ DEBUG=True en producción. Debería ser False.")
    
    if not cloudinary_available:
        recommendations.append("❌ Módulo 'cloudinary' no está instalado. Ejecutar: pip install cloudinary django-cloudinary-storage")
    
    if 'cloudinary' not in storage.lower():
        recommendations.append("❌ DEFAULT_FILE_STORAGE no apunta a Cloudinary.")
    
    if not cloudinary_config.get('CLOUD_NAME'):
        recommendations.append("❌ CLOUDINARY_CLOUD_NAME no está configurado en las variables de entorno de Render.")
    
    if not cloudinary_config.get('API_KEY'):
        recommendations.append("❌ CLOUDINARY_API_KEY no está configurado en las variables de entorno de Render.")
    
    if not cloudinary_config.get('API_SECRET'):
        recommendations.append("❌ CLOUDINARY_API_SECRET no está configurado en las variables de entorno de Render.")
    
    if not recommendations:
        recommendations.append("✅ Todo está configurado correctamente.")
    
    return recommendations

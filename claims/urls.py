"""
URLs para el sistema de reclamaciones
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClaimViewSet, ClaimImageViewSet

# Crear router para los ViewSets
router = DefaultRouter()
router.register(r'claims', ClaimViewSet, basename='claim')
router.register(r'claim-images', ClaimImageViewSet, basename='claim-image')

urlpatterns = [
    path('', include(router.urls)),
]

"""
Vistas para el sistema de reclamaciones
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from django.db.models import Count, Q, Avg
from django.utils import timezone

from .models import Claim, ClaimImage, ClaimHistory
from .serializers import (
    ClaimListSerializer,
    ClaimDetailSerializer,
    ClaimCreateSerializer,
    ClaimUpdateSerializer,
    ClaimCustomerFeedbackSerializer,
    ClaimImageSerializer,
    ClaimHistorySerializer
)
from .permissions import IsClaimOwnerOrAdmin, IsAdminUser
from .filters import ClaimFilter


class ClaimViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar reclamos
    
    Endpoints:
    - GET /claims/ - Lista de reclamos (filtrada según rol)
    - POST /claims/ - Crear nuevo reclamo (solo clientes)
    - GET /claims/{id}/ - Detalle de un reclamo
    - PATCH /claims/{id}/ - Actualizar reclamo (admin o cliente según campo)
    - DELETE /claims/{id}/ - Eliminar reclamo (solo admin)
    - POST /claims/{id}/add_images/ - Agregar imágenes adicionales
    - PATCH /claims/{id}/update_status/ - Actualizar estado (solo admin)
    - PATCH /claims/{id}/add_feedback/ - Agregar calificación (solo cliente dueño)
    - GET /claims/my_claims/ - Reclamos del usuario actual
    - GET /claims/statistics/ - Estadísticas de reclamos (solo admin)
    """
    
    queryset = Claim.objects.all().select_related(
        'customer',
        'product',
        'order',
        'assigned_to'
    ).prefetch_related('images', 'history')
    
    permission_classes = [permissions.IsAuthenticated, IsClaimOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_class = ClaimFilter
    search_fields = ['ticket_number', 'title', 'description', 'product__name']
    ordering_fields = ['created_at', 'updated_at', 'priority', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Filtrar queryset según el rol del usuario:
        - Clientes: solo sus propios reclamos
        - Administradores: todos los reclamos
        """
        user = self.request.user
        
        # Si es admin, ver todos los reclamos
        if hasattr(user, 'profile') and user.profile.role == 'ADMIN':
            return self.queryset
        
        # Si es cliente, solo sus reclamos
        return self.queryset.filter(customer=user)
    
    def get_serializer_class(self):
        """
        Usar diferentes serializers según la acción
        """
        if self.action == 'list':
            return ClaimListSerializer
        elif self.action == 'create':
            return ClaimCreateSerializer
        elif self.action in ['update', 'partial_update', 'update_status']:
            return ClaimUpdateSerializer
        elif self.action == 'add_feedback':
            return ClaimCustomerFeedbackSerializer
        else:
            return ClaimDetailSerializer
    
    def create(self, request, *args, **kwargs):
        """
        Crear un nuevo reclamo
        Solo clientes pueden crear reclamos
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        claim = serializer.save()
        
        # Retornar con el serializer de detalle
        response_serializer = ClaimDetailSerializer(claim, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """
        Actualizar un reclamo
        - Clientes: solo pueden actualizar ciertos campos (limitado en serializer)
        - Admins: pueden actualizar todos los campos
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Si es cliente, solo permitir actualización de feedback
        if hasattr(request.user, 'profile') and request.user.profile.role == 'CLIENT':
            # Los clientes no pueden actualizar directamente, solo usar add_feedback
            return Response(
                {'error': 'Los clientes deben usar el endpoint /add_feedback/ para actualizar sus reclamos.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        claim = serializer.save()
        
        response_serializer = ClaimDetailSerializer(claim, context={'request': request})
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def add_images(self, request, pk=None):
        """
        Agregar imágenes adicionales a un reclamo existente
        POST /claims/{id}/add_images/
        Body: { "images": [archivo1, archivo2, ...] }
        """
        claim = self.get_object()
        
        # Verificar que el usuario sea el dueño o admin
        if claim.customer != request.user and not (
            hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN'
        ):
            return Response(
                {'error': 'No tienes permiso para agregar imágenes a este reclamo.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        images_data = request.FILES.getlist('images')
        
        if not images_data:
            return Response(
                {'error': 'No se proporcionaron imágenes.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_images = []
        for image_file in images_data:
            claim_image = ClaimImage.objects.create(
                claim=claim,
                image=image_file
            )
            created_images.append(claim_image)
        
        # Registrar en el historial
        ClaimHistory.objects.create(
            claim=claim,
            user=request.user,
            action=f"Se agregaron {len(created_images)} imagen(es) adicional(es)",
            notes=f"Total de imágenes: {claim.images.count()}"
        )
        
        serializer = ClaimImageSerializer(created_images, many=True, context={'request': request})
        return Response({
            'message': f'Se agregaron {len(created_images)} imágenes exitosamente.',
            'images': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['patch'], permission_classes=[IsAdminUser])
    def update_status(self, request, pk=None):
        """
        Actualizar el estado de un reclamo (solo admin)
        PATCH /claims/{id}/update_status/
        Body: { 
            "status": "IN_REVIEW",
            "admin_response": "Estamos revisando tu caso...",
            "priority": "HIGH" (opcional)
        }
        """
        claim = self.get_object()
        
        serializer = ClaimUpdateSerializer(
            claim,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        updated_claim = serializer.save()
        
        response_serializer = ClaimDetailSerializer(updated_claim, context={'request': request})
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['patch'], permission_classes=[permissions.IsAuthenticated])
    def add_feedback(self, request, pk=None):
        """
        Agregar calificación y feedback del cliente
        PATCH /claims/{id}/add_feedback/
        Body: { 
            "customer_rating": 5,
            "customer_feedback": "Excelente servicio..."
        }
        """
        claim = self.get_object()
        
        # Solo el cliente dueño puede calificar
        if claim.customer != request.user:
            return Response(
                {'error': 'Solo el dueño del reclamo puede agregar feedback.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ClaimCustomerFeedbackSerializer(
            claim,
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        updated_claim = serializer.save()
        
        response_serializer = ClaimDetailSerializer(updated_claim, context={'request': request})
        return Response(response_serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_claims(self, request):
        """
        Obtener todos los reclamos del usuario actual
        GET /claims/my_claims/
        """
        claims = self.get_queryset().filter(customer=request.user)
        
        # Aplicar filtros si existen
        claims = self.filter_queryset(claims)
        
        page = self.paginate_queryset(claims)
        if page is not None:
            serializer = ClaimListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = ClaimListSerializer(claims, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def statistics(self, request):
        """
        Obtener estadísticas de reclamos (solo admin)
        GET /claims/statistics/
        
        Query params opcionales:
        - days: número de días a analizar (default: 30)
        """
        days = int(request.query_params.get('days', 30))
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        
        # Filtrar por fecha
        claims = self.queryset.filter(created_at__gte=cutoff_date)
        
        # Estadísticas generales
        total_claims = claims.count()
        
        # Por estado
        by_status = {}
        for status_choice in Claim.ClaimStatus.choices:
            count = claims.filter(status=status_choice[0]).count()
            by_status[status_choice[0]] = {
                'count': count,
                'label': status_choice[1],
                'percentage': round((count / total_claims * 100) if total_claims > 0 else 0, 2)
            }
        
        # Por prioridad
        by_priority = {}
        for priority_choice in Claim.Priority.choices:
            count = claims.filter(priority=priority_choice[0]).count()
            by_priority[priority_choice[0]] = {
                'count': count,
                'label': priority_choice[1],
                'percentage': round((count / total_claims * 100) if total_claims > 0 else 0, 2)
            }
        
        # Por tipo de daño
        by_damage_type = {}
        for damage_choice in Claim.DamageType.choices:
            count = claims.filter(damage_type=damage_choice[0]).count()
            by_damage_type[damage_choice[0]] = {
                'count': count,
                'label': damage_choice[1],
                'percentage': round((count / total_claims * 100) if total_claims > 0 else 0, 2)
            }
        
        # Productos con más reclamos
        top_products = claims.values(
            'product__id',
            'product__name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Calificación promedio
        avg_rating = claims.filter(
            customer_rating__isnull=False
        ).aggregate(Avg('customer_rating'))['customer_rating__avg']
        
        # Tiempo promedio de resolución
        resolved_claims = claims.filter(resolved_at__isnull=False)
        avg_resolution_time = None
        if resolved_claims.exists():
            total_time = sum(
                (claim.resolved_at - claim.created_at).total_seconds()
                for claim in resolved_claims
            )
            avg_resolution_time = round(total_time / resolved_claims.count() / 3600, 2)  # En horas
        
        return Response({
            'period': {
                'days': days,
                'from': cutoff_date.isoformat(),
                'to': timezone.now().isoformat()
            },
            'summary': {
                'total_claims': total_claims,
                'resolved': claims.filter(status__in=[
                    Claim.ClaimStatus.RESOLVED,
                    Claim.ClaimStatus.CLOSED
                ]).count(),
                'pending': claims.filter(status=Claim.ClaimStatus.PENDING).count(),
                'in_review': claims.filter(status=Claim.ClaimStatus.IN_REVIEW).count(),
                'avg_rating': round(avg_rating, 2) if avg_rating else None,
                'avg_resolution_time_hours': avg_resolution_time
            },
            'by_status': by_status,
            'by_priority': by_priority,
            'by_damage_type': by_damage_type,
            'top_products': list(top_products)
        })
    
    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def history(self, request, pk=None):
        """
        Obtener el historial completo de un reclamo
        GET /claims/{id}/history/
        """
        claim = self.get_object()
        history_entries = claim.history.all()
        serializer = ClaimHistorySerializer(history_entries, many=True, context={'request': request})
        return Response(serializer.data)


class ClaimImageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet de solo lectura para imágenes de reclamos
    
    Endpoints:
    - GET /claim-images/ - Lista de todas las imágenes
    - GET /claim-images/{id}/ - Detalle de una imagen
    """
    
    queryset = ClaimImage.objects.all().select_related('claim')
    serializer_class = ClaimImageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        Filtrar imágenes según el rol del usuario
        """
        user = self.request.user
        
        # Si es admin, ver todas las imágenes
        if hasattr(user, 'profile') and user.profile.role == 'ADMIN':
            return self.queryset
        
        # Si es cliente, solo imágenes de sus reclamos
        return self.queryset.filter(claim__customer=user)

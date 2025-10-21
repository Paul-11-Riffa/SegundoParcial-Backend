# sales/views_audit.py
"""
Vistas para consultar y administrar la bitácora de auditoría.
"""

from rest_framework import views, generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Count, Q, Max
from django.utils import timezone
from datetime import timedelta
from api.permissions import IsAdminUser

from .models_audit import AuditLog, UserSession
from .serializers_audit import AuditLogSerializer, UserSessionSerializer


class AuditLogListView(generics.ListAPIView):
    """
    GET /api/sales/audit/logs/

    Lista todos los registros de auditoría con filtros avanzados.

    Query params:
    - user: Filtrar por username
    - action_type: Filtrar por tipo de acción (AUTH, CREATE, READ, etc.)
    - start_date: Fecha inicio (YYYY-MM-DD)
    - end_date: Fecha fin (YYYY-MM-DD)
    - severity: Filtrar por severidad (LOW, MEDIUM, HIGH, CRITICAL)
    - success: Filtrar por éxito (true/false)
    - ip_address: Filtrar por IP
    - search: Buscar en descripción
    - limit: Limitar resultados (default: 100, max: 1000)
    """
    permission_classes = [IsAdminUser]
    serializer_class = AuditLogSerializer

    def get_queryset(self):
        queryset = AuditLog.objects.all()

        # Filtro por usuario
        user = self.request.query_params.get('user')
        if user:
            queryset = queryset.filter(username__icontains=user)

        # Filtro por tipo de acción
        action_type = self.request.query_params.get('action_type')
        if action_type:
            queryset = queryset.filter(action_type=action_type.upper())

        # Filtro por rango de fechas
        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)

        end_date = self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)

        # Filtro por severidad
        severity = self.request.query_params.get('severity')
        if severity:
            queryset = queryset.filter(severity=severity.upper())

        # Filtro por éxito/error
        success = self.request.query_params.get('success')
        if success is not None:
            success_bool = success.lower() == 'true'
            queryset = queryset.filter(success=success_bool)

        # Filtro por IP
        ip_address = self.request.query_params.get('ip_address')
        if ip_address:
            queryset = queryset.filter(ip_address=ip_address)

        # Búsqueda en descripción
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(action_description__icontains=search) |
                Q(endpoint__icontains=search)
            )

        # Limitar resultados
        limit = int(self.request.query_params.get('limit', 100))
        limit = min(limit, 1000)  # Máximo 1000

        return queryset[:limit]


class AuditLogDetailView(generics.RetrieveAPIView):
    """
    GET /api/sales/audit/logs/<id>/

    Obtiene el detalle completo de un registro de auditoría.
    """
    permission_classes = [IsAdminUser]
    serializer_class = AuditLogSerializer
    queryset = AuditLog.objects.all()


class AuditStatisticsView(views.APIView):
    """
    GET /api/sales/audit/statistics/

    Estadísticas generales de la bitácora.

    Query params:
    - days: Días hacia atrás para analizar (default: 7)
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        days = int(request.query_params.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)

        logs = AuditLog.objects.filter(timestamp__gte=start_date)

        # Estadísticas generales
        total_actions = logs.count()
        total_errors = logs.filter(success=False).count()
        total_users = logs.values('username').distinct().count()

        # Por tipo de acción
        by_action = logs.values('action_type').annotate(
            count=Count('id')
        ).order_by('-count')

        # Por severidad
        by_severity = logs.values('severity').annotate(
            count=Count('id')
        ).order_by('-count')

        # Por día (últimos N días)
        by_day = logs.extra(
            select={'day': 'DATE(timestamp)'}
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')

        # Usuarios más activos
        top_users = logs.values('username').annotate(
            count=Count('id')
        ).order_by('-count')[:10]

        # IPs más activas
        top_ips = logs.values('ip_address').annotate(
            count=Count('id')
        ).order_by('-count')[:10]

        # Endpoints más accedidos
        top_endpoints = logs.values('endpoint').annotate(
            count=Count('id')
        ).order_by('-count')[:10]

        # Errores recientes
        recent_errors = logs.filter(success=False).order_by('-timestamp')[:10]
        recent_errors_data = AuditLogSerializer(recent_errors, many=True).data

        # Acciones críticas recientes
        critical_actions = logs.filter(severity='CRITICAL').order_by('-timestamp')[:10]
        critical_actions_data = AuditLogSerializer(critical_actions, many=True).data

        return Response({
            'period': {
                'days': days,
                'start_date': start_date.isoformat(),
                'end_date': timezone.now().isoformat()
            },
            'summary': {
                'total_actions': total_actions,
                'total_errors': total_errors,
                'total_users': total_users,
                'error_rate': f"{(total_errors / total_actions * 100) if total_actions > 0 else 0:.2f}%"
            },
            'by_action_type': list(by_action),
            'by_severity': list(by_severity),
            'by_day': list(by_day),
            'top_users': list(top_users),
            'top_ips': list(top_ips),
            'top_endpoints': list(top_endpoints),
            'recent_errors': recent_errors_data,
            'critical_actions': critical_actions_data
        })


class UserActivityView(views.APIView):
    """
    GET /api/sales/audit/user-activity/<username>/

    Actividad detallada de un usuario específico.

    Query params:
    - days: Días hacia atrás (default: 30)
    """
    permission_classes = [IsAdminUser]

    def get(self, request, username):
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)

        logs = AuditLog.objects.filter(
            username=username,
            timestamp__gte=start_date
        )

        # Estadísticas del usuario
        total_actions = logs.count()
        total_errors = logs.filter(success=False).count()

        # Últimas acciones
        recent_actions = logs.order_by('-timestamp')[:20]
        recent_actions_data = AuditLogSerializer(recent_actions, many=True).data

        # Por tipo de acción
        by_action = logs.values('action_type').annotate(
            count=Count('id')
        ).order_by('-count')

        # IPs usadas
        ips_used = logs.values('ip_address').annotate(
            count=Count('id'),
            last_used=Max('timestamp')
        ).order_by('-last_used')

        # Sesiones activas
        active_sessions = UserSession.objects.filter(
            user__username=username,
            is_active=True
        )
        active_sessions_data = UserSessionSerializer(active_sessions, many=True).data

        return Response({
            'username': username,
            'period': {
                'days': days,
                'start_date': start_date.isoformat()
            },
            'summary': {
                'total_actions': total_actions,
                'total_errors': total_errors,
                'error_rate': f"{(total_errors / total_actions * 100) if total_actions > 0 else 0:.2f}%"
            },
            'recent_actions': recent_actions_data,
            'by_action_type': list(by_action),
            'ips_used': list(ips_used),
            'active_sessions': active_sessions_data
        })


class ActiveSessionsView(generics.ListAPIView):
    """
    GET /api/sales/audit/sessions/active/

    Lista de todas las sesiones activas.
    """
    permission_classes = [IsAdminUser]
    serializer_class = UserSessionSerializer

    def get_queryset(self):
        return UserSession.objects.filter(is_active=True).order_by('-last_activity')


class SessionHistoryView(generics.ListAPIView):
    """
    GET /api/sales/audit/sessions/history/

    Historial completo de sesiones.

    Query params:
    - user: Filtrar por username
    - limit: Limitar resultados (default: 100)
    """
    permission_classes = [IsAdminUser]
    serializer_class = UserSessionSerializer

    def get_queryset(self):
        queryset = UserSession.objects.all().order_by('-login_time')

        user = self.request.query_params.get('user')
        if user:
            queryset = queryset.filter(user__username__icontains=user)

        limit = int(self.request.query_params.get('limit', 100))
        return queryset[:limit]


@api_view(['POST'])
@permission_classes([IsAdminUser])
def clean_old_logs(request):
    """
    POST /api/sales/audit/clean-old-logs/

    Elimina logs antiguos para liberar espacio.

    Body:
    {
        "days": 90  // Eliminar logs más antiguos que N días
    }
    """
    days = request.data.get('days', 90)

    if days < 30:
        return Response({
            'error': 'No se pueden eliminar logs de menos de 30 días'
        }, status=status.HTTP_400_BAD_REQUEST)

    cutoff_date = timezone.now() - timedelta(days=days)

    deleted_count = AuditLog.objects.filter(timestamp__lt=cutoff_date).delete()[0]

    return Response({
        'success': True,
        'message': f'Se eliminaron {deleted_count} registros más antiguos que {days} días',
        'cutoff_date': cutoff_date.isoformat()
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def security_alerts(request):
    """
    GET /api/sales/audit/security-alerts/

    Alertas de seguridad basadas en la bitácora.

    Detecta:
    - Múltiples intentos fallidos de login
    - Accesos desde IPs desconocidas
    - Acciones de alta severidad
    - Cambios masivos en corto tiempo
    """
    # Últimas 24 horas
    last_24h = timezone.now() - timedelta(hours=24)

    alerts = []

    # Detectar múltiples intentos fallidos de login
    failed_logins = AuditLog.objects.filter(
        timestamp__gte=last_24h,
        action_type='AUTH',
        success=False
    ).values('ip_address').annotate(
        count=Count('id')
    ).filter(count__gte=5)

    for item in failed_logins:
        alerts.append({
            'type': 'failed_login_attempts',
            'severity': 'HIGH',
            'message': f"IP {item['ip_address']} ha fallado {item['count']} veces al intentar iniciar sesión",
            'ip': item['ip_address'],
            'count': item['count']
        })

    # Detectar acciones críticas
    critical_actions = AuditLog.objects.filter(
        timestamp__gte=last_24h,
        severity='CRITICAL'
    ).count()

    if critical_actions > 0:
        alerts.append({
            'type': 'critical_actions',
            'severity': 'CRITICAL',
            'message': f"Se han registrado {critical_actions} acciones críticas en las últimas 24 horas",
            'count': critical_actions
        })

    # Detectar accesos desde múltiples IPs por el mismo usuario
    multi_ip_users = AuditLog.objects.filter(
        timestamp__gte=last_24h
    ).values('username').annotate(
        ip_count=Count('ip_address', distinct=True)
    ).filter(ip_count__gte=3)

    for item in multi_ip_users:
        if item['username'] != 'Anónimo':
            alerts.append({
                'type': 'multiple_ips',
                'severity': 'MEDIUM',
                'message': f"Usuario {item['username']} ha accedido desde {item['ip_count']} IPs diferentes",
                'username': item['username'],
                'ip_count': item['ip_count']
            })

    return Response({
        'total_alerts': len(alerts),
        'alerts': alerts,
        'period': '24 horas'
    })

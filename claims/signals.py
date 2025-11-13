from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth.models import User
from .models import Claim, ClaimHistory


@receiver(pre_save, sender=Claim)
def track_status_changes(sender, instance, **kwargs):
    """
    Rastrea cambios de estado y actualiza fechas automáticamente
    """
    if instance.pk:  # Solo si ya existe (actualización)
        try:
            old_instance = Claim.objects.get(pk=instance.pk)
            
            # Guardar el estado anterior en el instance para usar en post_save
            instance._old_status = old_instance.status
            instance._status_changed = old_instance.status != instance.status
            
            # Si cambia a RESOLVED, actualizar resolved_at
            if (old_instance.status != Claim.ClaimStatus.RESOLVED and 
                instance.status == Claim.ClaimStatus.RESOLVED):
                instance.resolved_at = timezone.now()
            
            # Si cambia a CLOSED, actualizar closed_at
            if (old_instance.status != Claim.ClaimStatus.CLOSED and 
                instance.status == Claim.ClaimStatus.CLOSED):
                instance.closed_at = timezone.now()
                if not instance.resolved_at:
                    instance.resolved_at = timezone.now()
                    
        except Claim.DoesNotExist:
            pass
    else:
        # Es una creación nueva
        instance._is_new = True


@receiver(post_save, sender=Claim)
def create_claim_history(sender, instance, created, **kwargs):
    """
    Crea entradas en el historial cuando se modifica un reclamo
    """
    if created:
        # Registro de creación
        ClaimHistory.objects.create(
            claim=instance,
            user=instance.customer,
            action="Reclamo creado por el cliente",
            new_status=instance.status,
            notes=f"Nuevo reclamo sobre {instance.product.name}"
        )


@receiver(post_save, sender=Claim)
def send_claim_notifications(sender, instance, created, **kwargs):
    """
    Envía notificaciones cuando se crea o actualiza un reclamo
    """
    from notifications.notification_service import NotificationService
    from api.models import Profile
    
    if created:
        # ✅ Notificar a TODOS los administradores cuando se crea un nuevo reclamo
        admins = User.objects.filter(
            profile__role=Profile.Role.ADMIN,
            is_active=True
        )
        
        for admin in admins:
            try:
                NotificationService.send_notification_to_user(
                    user=admin,
                    title=f"🔔 Nuevo Reclamo #{instance.ticket_number}",
                    body=f"{instance.customer.username} reportó: {instance.title}",
                    notification_type='CLAIM_CREATED',
                    data={
                        'claim_id': instance.id,
                        'ticket_number': instance.ticket_number,
                        'customer': instance.customer.username,
                        'product': instance.product.name,
                        'damage_type': instance.damage_type,
                        'priority': instance.priority,
                        'url': f'/admin/claims/{instance.id}'
                    }
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error enviando notificación a admin {admin.username}: {e}")
    
    elif hasattr(instance, '_status_changed') and instance._status_changed:
        # ✅ Notificar al cliente cuando cambia el estado de su reclamo
        old_status = getattr(instance, '_old_status', None)
        
        # Determinar el tipo de notificación según el estado
        if instance.status == Claim.ClaimStatus.RESOLVED:
            notification_type = 'CLAIM_RESOLVED'
        else:
            notification_type = 'CLAIM_UPDATED'
        
        # Mensajes personalizados según el cambio de estado
        status_messages = {
            Claim.ClaimStatus.IN_REVIEW: "Tu reclamo está siendo revisado por nuestro equipo",
            Claim.ClaimStatus.REQUIRES_INFO: "Necesitamos más información sobre tu reclamo",
            Claim.ClaimStatus.APPROVED: "¡Tu reclamo ha sido aprobado!",
            Claim.ClaimStatus.REJECTED: "Tu reclamo ha sido revisado",
            Claim.ClaimStatus.RESOLVED: "¡Tu reclamo ha sido resuelto!",
            Claim.ClaimStatus.CLOSED: "Tu reclamo ha sido cerrado"
        }
        
        message = status_messages.get(
            instance.status,
            f"El estado de tu reclamo cambió a {instance.get_status_display()}"
        )
        
        try:
            NotificationService.send_notification_to_user(
                user=instance.customer,
                title=f"📋 Actualización Reclamo #{instance.ticket_number}",
                body=message,
                notification_type=notification_type,
                data={
                    'claim_id': instance.id,
                    'ticket_number': instance.ticket_number,
                    'old_status': old_status,
                    'new_status': instance.status,
                    'admin_response': instance.admin_response,
                    'url': f'/claims/{instance.id}'
                }
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error enviando notificación a cliente {instance.customer.username}: {e}")
    
    # ✅ Notificar al admin asignado cuando se le asigna un reclamo
    if hasattr(instance, '_old_assigned_to'):
        old_assigned = getattr(instance, '_old_assigned_to', None)
        if old_assigned != instance.assigned_to and instance.assigned_to:
            try:
                NotificationService.send_notification_to_user(
                    user=instance.assigned_to,
                    title=f"📌 Reclamo Asignado #{instance.ticket_number}",
                    body=f"Se te ha asignado un reclamo de {instance.customer.username}",
                    notification_type='CLAIM_ASSIGNED',
                    data={
                        'claim_id': instance.id,
                        'ticket_number': instance.ticket_number,
                        'customer': instance.customer.username,
                        'product': instance.product.name,
                        'priority': instance.priority,
                        'url': f'/admin/claims/{instance.id}'
                    }
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error enviando notificación de asignación: {e}")


@receiver(pre_save, sender=Claim)
def track_assigned_to_changes(sender, instance, **kwargs):
    """
    Rastrea cambios en el campo assigned_to
    """
    if instance.pk:
        try:
            old_instance = Claim.objects.get(pk=instance.pk)
            instance._old_assigned_to = old_instance.assigned_to
        except Claim.DoesNotExist:
            pass

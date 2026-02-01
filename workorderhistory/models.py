import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class WorkOrderHistory(models.Model):
    """
    Histórico de eventos da Ordem de Serviço.
    Registra mudanças de status e ações relevantes.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    work_order = models.ForeignKey(
        'workorder.WorkOrder',
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name='Work order'
    )

    previous_status = models.ForeignKey(
        'workorderstatus.ServiceOrderStatus',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='previous_status_histories',
        verbose_name='Previous status'
    )

    new_status = models.ForeignKey(
        'workorderstatus.ServiceOrderStatus',
        on_delete=models.PROTECT,
        related_name='new_status_histories',
        verbose_name='New status'
    )

    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Changed by'
    )

    note = models.TextField(
        blank=True,
        verbose_name='Note / observation'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created at'
    )

    class Meta:
        verbose_name = 'Work Order History'
        verbose_name_plural = 'Work Order Histories'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['work_order']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'{self.work_order.code} -> {self.new_status.status_name}'

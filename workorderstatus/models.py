import uuid
from django.db import models


class WorkOrderStatus(models.Model):
    """
    Representa o estado atual de uma Ordem de Serviço (W.O).
    Ex: Aberta, Em Execução, Concluída, Cancelada, Reagendada
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Nome do status'
    )

    description = models.TextField(
        blank=True,
        verbose_name='Descrição'
    )


    order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='Ordem de exibição'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Criado em'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Atualizado em'
    )

    class Meta:
        verbose_name = 'Status da Ordem'
        verbose_name_plural = 'Status das Ordens'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class ServiceOrderStatus(models.Model):
    """
    Status de OS no modelo de dois niveis (Grupo + Status) do PRD.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Grupo
    group_code = models.CharField(max_length=30)
    group_name = models.CharField(max_length=50)
    group_color = models.CharField(max_length=10)

    # Status operacional
    status_code = models.CharField(max_length=50)
    status_name = models.CharField(max_length=100)
    status_order = models.IntegerField(default=0)

    is_final = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Status da OS (Grupo + Status)'
        verbose_name_plural = 'Status das OS (Grupo + Status)'
        ordering = ['status_order', 'group_name', 'status_name']
        indexes = [
            models.Index(fields=['group_code']),
            models.Index(fields=['status_code']),
            models.Index(fields=['is_active']),
            models.Index(fields=['is_final']),
        ]
        unique_together = [('group_code', 'status_code')]

    def __str__(self):
        return f'{self.group_name} - {self.status_name}'

"""
Modelo de Avaliação de Ordens de Serviço.
Criado em arquivo separado para não interferir no modelo principal já migrado.
"""
import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class WorkOrderEvaluation(models.Model):
    """
    Avaliação de uma Ordem de Serviço pelo cliente.
    Permite rating de 1 a 5 estrelas + comentário opcional.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    work_order = models.OneToOneField(
        'workorder.WorkOrder',
        on_delete=models.CASCADE,
        related_name='evaluation',
        verbose_name='Ordem de Serviço'
    )

    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Avaliação (1-5 estrelas)'
    )

    comment = models.TextField(
        blank=True,
        verbose_name='Comentário'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Avaliado em')

    class Meta:
        verbose_name = 'Avaliação'
        verbose_name_plural = 'Avaliações'
        ordering = ['-created_at']

    def __str__(self):
        return f"Avaliação {self.rating}★ - OS {self.work_order.code}"

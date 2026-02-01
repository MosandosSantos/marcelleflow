import uuid
from django.db import models


class InsuranceCompany(models.Model):
    """
    Representa a Seguradora que autoriza ou cobre o serviço.
    Ex: Caixa, Bradesco, Porto Seguro, etc.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(
        max_length=150,
        unique=True,
        verbose_name='Nome da seguradora'
    )

    trade_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Nome fantasia'
    )

    document = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='CNPJ'
    )

    
    contact_name = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Nome de contato'
    )

    contact_email = models.EmailField(
        blank=True,
        verbose_name='E-mail de contato'
    )

    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Telefone de contato'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='Ativa'
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
        verbose_name = 'Seguradora'
        verbose_name_plural = 'Seguradoras'
        ordering = ['name']

    def __str__(self):
        return self.name

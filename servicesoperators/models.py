import uuid
from django.db import models


class ServiceOperator(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Identificação institucional
    name = models.CharField(
        max_length=150,
        unique=True,
        verbose_name='Company name'
    )

    trade_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Trade name'
    )

    cnpj = models.CharField(
        max_length=18,
        unique=True,
        verbose_name='CNPJ'
    )

    # Responsável legal / operacional
    responsible_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Responsible person'
    )

    responsible_role = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Responsible role'
    )

    # Contato institucional
    email = models.EmailField(
        blank=True,
        verbose_name='Main email'
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Main phone'
    )

    website = models.URLField(
        blank=True,
        verbose_name='Website'
    )

    # Endereço
    street = models.CharField(max_length=255, blank=True)
    number = models.CharField(max_length=20, blank=True)
    complement = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=2, blank=True)
    zip_code = models.CharField(max_length=10, blank=True)

    # Controle
    is_active = models.BooleanField(default=True)

    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Service Operator'
        verbose_name_plural = 'Service Operators'
        ordering = ['name']

    def __str__(self):
        return self.trade_name or self.name

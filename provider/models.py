# apps/providers/models.py

import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Provider(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='provider_profile')

    full_name = models.CharField(max_length=150, verbose_name='Nome completo')
    email = models.EmailField(verbose_name='E-mail')
    cpf = models.CharField(max_length=14, unique=True, verbose_name='CPF')
    phone = models.CharField(max_length=20, verbose_name='Telefone')
    birth_date = models.DateField(null=True, blank=True, verbose_name='Data de nascimento')

    # Endereço
    street = models.CharField(max_length=255, verbose_name='Rua')
    number = models.CharField(max_length=10, verbose_name='Número')
    complement = models.CharField(max_length=100, blank=True, verbose_name='Complemento')
    neighborhood = models.CharField(max_length=100, verbose_name='Bairro')
    city = models.CharField(max_length=100, verbose_name='Cidade')
    state = models.CharField(max_length=2, verbose_name='UF')
    zip_code = models.CharField(max_length=9, verbose_name='CEP')

    # Dados bancários
    bank_name = models.CharField(max_length=100, verbose_name='Banco')
    bank_agency = models.CharField(max_length=10, verbose_name='Agência')
    bank_account = models.CharField(max_length=20, verbose_name='Conta')
    bank_pix_key = models.CharField(max_length=100, verbose_name='Chave PIX')

    # Observações internas
    notes = models.TextField(blank=True, verbose_name='Observações')

    service_types = models.ManyToManyField(
        'servicetype.ServiceType',
        related_name='providers',
        verbose_name='Tipos de serviço'
    )

    # M?tricas denormalizadas de avalia??o
    rating_avg = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0,
        verbose_name='M?dia de avalia??o'
    )
    rating_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Quantidade de avalia??es'
    )



    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Prestador de Serviço'
        verbose_name_plural = 'Prestadores de Serviço'
        ordering = ['full_name']

    def __str__(self):
        return self.full_name or self.user.email

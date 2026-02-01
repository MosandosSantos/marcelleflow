# apps/clients/models.py

import uuid
import re
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

class Client(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')

    full_name = models.CharField(max_length=150, verbose_name='Nome completo')
    email = models.EmailField(verbose_name='E-mail')
    cpf = models.CharField(
        max_length=14,
        unique=True,
        null=True,
        blank=True,
        verbose_name='CPF'
    )
    cnpj = models.CharField(
        max_length=18,
        unique=True,
        null=True,
        blank=True,
        verbose_name='CNPJ'
    )
    phone = models.CharField(max_length=20, verbose_name='Telefone')
    birth_date = models.DateField(null=True, blank=True, verbose_name='Data de nascimento')

    # Endereço detalhado
    street = models.CharField(max_length=255, verbose_name='Rua')
    number = models.CharField(max_length=10, verbose_name='Número')
    complement = models.CharField(max_length=100, blank=True, verbose_name='Complemento')
    neighborhood = models.CharField(max_length=100, verbose_name='Bairro')
    city = models.CharField(max_length=100, verbose_name='Cidade')
    state = models.CharField(max_length=2, verbose_name='UF')
    zip_code = models.CharField(max_length=9, verbose_name='CEP')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

    def __str__(self):
        return self.full_name or self.user.email

    def _normalize_fields(self):
        if self.cpf:
            self.cpf = re.sub(r'\D', '', self.cpf)
        if self.cnpj:
            self.cnpj = re.sub(r'\D', '', self.cnpj)
        if self.phone:
            self.phone = re.sub(r'\D', '', self.phone)
        if self.zip_code:
            digits = re.sub(r'\D', '', self.zip_code)
            if len(digits) == 8:
                self.zip_code = f'{digits[:5]}-{digits[5:]}'
            else:
                self.zip_code = digits

    def save(self, *args, **kwargs):
        self._normalize_fields()
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        from .validators import is_valid_cpf, is_valid_cnpj

        if not self.cpf and not self.cnpj:
            raise ValidationError({'cpf': 'Informe CPF ou CNPJ.'})

        if self.cpf and self.cnpj:
            raise ValidationError({'cpf': 'Informe apenas CPF ou apenas CNPJ.'})

        if self.cpf and not is_valid_cpf(self.cpf):
            raise ValidationError({'cpf': 'CPF inválido.'})

        if self.cnpj and not is_valid_cnpj(self.cnpj):
            raise ValidationError({'cnpj': 'CNPJ inválido.'})

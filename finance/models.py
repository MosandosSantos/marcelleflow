import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    """
    Modelo abstrato base para modelos financeiros.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        abstract = True


class Account(BaseModel):
    """
    Conta financeira (banco, caixa, carteira).
    """
    TIPO_CHOICES = [
        ('conta_corrente', 'Conta Corrente'),
        ('poupanca', 'Poupança'),
        ('carteira', 'Carteira (Dinheiro)'),
        ('investimento', 'Investimento'),
        ('outros', 'Outros'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='finance_accounts',
        verbose_name='Usuario'
    )
    nome = models.CharField(max_length=100, verbose_name='Nome da Conta')
    bank_code = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='Codigo do Banco'
    )
    agencia = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='Agencia'
    )
    agencia_dv = models.CharField(
        max_length=2,
        blank=True,
        verbose_name='DV Agencia'
    )
    conta_numero = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Numero da Conta'
    )
    conta_dv = models.CharField(
        max_length=2,
        blank=True,
        verbose_name='DV Conta'
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='conta_corrente',
        verbose_name='Tipo de Conta'
    )
    saldo_inicial = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Saldo Inicial'
    )
    ativa = models.BooleanField(
        default=True,
        verbose_name='Conta Ativa'
    )
    is_primary = models.BooleanField(
        default=False,
        verbose_name='Conta Principal'
    )

    class Meta:
        verbose_name = 'Conta Financeira'
        verbose_name_plural = 'Contas Financeiras'
        ordering = ['-created_at']
        unique_together = ['user', 'nome']

    def __str__(self):
        return f'{self.nome} ({self.get_tipo_display()})'

    def calcular_saldo_atual(self):
        """
        Calcula saldo com base nas transacoes realizadas.
        """
        receitas = self.transactions.filter(
            tipo='receita',
            status='realizado'
        ).aggregate(total=models.Sum('valor'))['total'] or Decimal('0.00')

        despesas = self.transactions.filter(
            tipo='despesa',
            status='realizado'
        ).aggregate(total=models.Sum('valor'))['total'] or Decimal('0.00')

        return self.saldo_inicial + receitas - despesas

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_primary:
            Account.objects.filter(user=self.user, is_primary=True).exclude(pk=self.pk).update(is_primary=False)


class Category(BaseModel):
    """
    Categoria financeira para receitas e despesas.
    """
    TIPO_CHOICES = [
        ('receita', 'Receita'),
        ('despesa', 'Despesa'),
    ]
    DRE_GROUP_CHOICES = [
        ('receita_operacional', 'Receita operacional'),
        ('impostos_venda', 'Impostos sobre a venda'),
        ('cmv', 'CMV/CPV'),
        ('despesas_venda', 'Despesas com vendas'),
        ('despesas_financeiras', 'Despesas financeiras'),
        ('receita_financeira', 'Receita financeira'),
        ('despesas_gerais_adm', 'Despesas gerais e administrativas'),
    ]

    nome = models.CharField(max_length=100, verbose_name='Nome da Categoria')
    tipo = models.CharField(
        max_length=10,
        choices=TIPO_CHOICES,
        verbose_name='Tipo'
    )
    descricao = models.TextField(blank=True, verbose_name='Descricao')
    ativa = models.BooleanField(default=True, verbose_name='Categoria Ativa')
    dre_group = models.CharField(
        max_length=40,
        choices=DRE_GROUP_CHOICES,
        blank=True,
        verbose_name='Grupo DRE'
    )

    class Meta:
        verbose_name = 'Categoria Financeira'
        verbose_name_plural = 'Categorias Financeiras'
        ordering = ['tipo', 'nome']
        unique_together = ['nome', 'tipo']

    def __str__(self):
        return f'{self.nome} ({self.get_tipo_display()})'

    def clean(self):
        super().clean()
        if self.nome:
            self.nome = self.nome.strip()


class Transaction(BaseModel):
    """
    Lancamento financeiro (conta a pagar/receber).
    """
    TIPO_CHOICES = [
        ('receita', 'Receita'),
        ('despesa', 'Despesa'),
    ]

    STATUS_CHOICES = [
        ('previsto', 'Previsto'),
        ('realizado', 'Realizado'),
        ('atrasado', 'Atrasado'),
        ('cancelado', 'Cancelado'),
    ]

    PAYMENT_ORIGIN_CHOICES = [
        ('pix', 'PIX'),
        ('ted', 'TED'),
        ('cartao', 'Cartão'),
        ('boleto', 'Boleto'),
    ]

    # Tipificação de Despesas
    EXPENSE_TYPE_CHOICES = [
        ('direto', 'Custo Direto'),
        ('indireto', 'Custo Indireto'),
        ('fixo', 'Custo Fixo'),
        ('variavel', 'Custo Variável'),
        ('administrativo', 'Despesa Administrativa'),
        ('operacional', 'Despesa Operacional'),
        ('financeiro', 'Despesa Financeira'),
    ]

    # Recorrência
    RECURRENCE_PERIOD_CHOICES = [
        ('unico', 'Único (Não Recorrente)'),
        ('mensal', 'Mensal'),
        ('bimestral', 'Bimestral'),
        ('trimestral', 'Trimestral'),
        ('semestral', 'Semestral'),
        ('anual', 'Anual'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='finance_transactions',
        verbose_name='Usuario'
    )
    work_order = models.ForeignKey(
        'workorder.WorkOrder',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='finance_transactions',
        verbose_name='Ordem de Servico',
        help_text='Vinculo automatico com OS para contas a receber.'
    )
    tipo = models.CharField(
        max_length=10,
        choices=TIPO_CHOICES,
        verbose_name='Tipo'
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='previsto',
        verbose_name='Status'
    )
    descricao = models.CharField(max_length=255, verbose_name='Descricao')
    valor = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Valor'
    )
    data_vencimento = models.DateField(verbose_name='Data de Vencimento')
    data_pagamento = models.DateField(blank=True, null=True, verbose_name='Data de Pagamento')
    payment_origin = models.CharField(
        max_length=20,
        choices=PAYMENT_ORIGIN_CHOICES,
        blank=True,
        null=True,
        verbose_name='Origem de Pagamento'
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name='transactions',
        verbose_name='Conta'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='transactions',
        verbose_name='Categoria'
    )
    observacoes = models.TextField(blank=True, verbose_name='Observacoes')

    # NOVOS CAMPOS: Tipificação e Recorrência
    expense_type = models.CharField(
        max_length=20,
        choices=EXPENSE_TYPE_CHOICES,
        blank=True,
        null=True,
        verbose_name='Tipo de Despesa',
        help_text='Classificação da despesa para controle de custos'
    )

    is_recurring = models.BooleanField(
        default=False,
        verbose_name='É Recorrente?',
        help_text='Marque se esta despesa se repete periodicamente'
    )

    recurrence_period = models.CharField(
        max_length=20,
        choices=RECURRENCE_PERIOD_CHOICES,
        default='unico',
        verbose_name='Período de Recorrência'
    )

    related_service_type = models.ForeignKey(
        'servicetype.ServiceType',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='related_transactions',
        verbose_name='Tipo de Serviço Relacionado',
        help_text='Vincule esta despesa a um tipo de serviço específico'
    )
    is_installment = models.BooleanField(
        default=False,
        verbose_name='Parcela de recebimento'
    )
    is_projection = models.BooleanField(
        default=False,
        verbose_name='Previsao de recebimento'
    )
    installment_group_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Grupo de parcelas'
    )
    installment_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Numero da parcela'
    )
    installment_total = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Total de parcelas'
    )
    invoice_number = models.CharField(
        max_length=60,
        blank=True,
        null=True,
        verbose_name='Numero da NF'
    )
    invoice_issued_at = models.DateField(
        null=True,
        blank=True,
        verbose_name='Data de emissao da NF'
    )
    invoice_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Dados da NF'
    )
    boleto_number = models.CharField(
        max_length=60,
        blank=True,
        null=True,
        verbose_name='Numero do Boleto'
    )
    boleto_issued_at = models.DateField(
        null=True,
        blank=True,
        verbose_name='Data de emissao do Boleto'
    )

    class Meta:
        verbose_name = 'Transacao'
        verbose_name_plural = 'Transacoes'
        ordering = ['-data_vencimento', '-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'tipo']),
            models.Index(fields=['data_vencimento']),
        ]

    def __str__(self):
        return f'{self.descricao} - R$ {self.valor} ({self.get_status_display()})'

    def clean(self):
        super().clean()

        if self.data_pagamento and self.data_vencimento:
            if self.data_pagamento < self.data_vencimento:
                raise ValidationError({'data_pagamento': 'Data de pagamento nao pode ser anterior a data de vencimento.'})
            if self.data_pagamento > timezone.now().date():
                raise ValidationError({'data_pagamento': 'Data de pagamento nao pode ser maior que a data de hoje.'})

        # Permite contas de outros usuários quando necessário.

        if self.category_id and self.tipo and self.category and self.tipo != self.category.tipo:
            raise ValidationError({'category': f'A categoria deve ser do tipo {self.get_tipo_display()}.'})

    def save(self, *args, **kwargs):
        if self.status == 'cancelado':
            self.data_pagamento = None
            super().save(*args, **kwargs)
            return

        if self.is_projection and not self.data_pagamento:
            self.status = 'previsto'
            self.data_pagamento = None
            super().save(*args, **kwargs)
            return

        today = timezone.now().date()
        if self.data_pagamento:
            self.status = 'realizado'
        elif self.data_vencimento < today:
            self.status = 'atrasado'
            self.data_pagamento = None
        else:
            self.status = 'previsto'
            self.data_pagamento = None

        super().save(*args, **kwargs)

    def marcar_como_realizado(self, data_pagamento=None):
        self.status = 'realizado'
        self.data_pagamento = data_pagamento or timezone.now().date()
        self.save()

    def marcar_como_previsto(self):
        self.status = 'previsto'
        self.data_pagamento = None
        self.save()

    def cancelar(self):
        self.status = 'cancelado'
        self.data_pagamento = None
        self.save()

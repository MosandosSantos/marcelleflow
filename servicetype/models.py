import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


BILLING_UNIT_CHOICES = [
    ('hora', 'Hora'),
    ('unidade', 'Unidade'),
    ('km', 'Quilômetro'),
    ('dia', 'Dia'),
    ('visita', 'Visita'),
    ('m2', 'Metro Quadrado'),
    ('consulta', 'Consulta'),
    ('sessao', 'Sessão'),
    ('servico', 'Serviço Completo'),
    ('outro', 'Outro'),
]

COST_TYPE_CHOICES = [
    ('direto', 'Direto'),
    ('indireto', 'Indireto'),
]

EXPENSE_GROUP_CHOICES = [
    ('operacional', 'Operacional'),
    ('administrativo', 'Administrativo'),
    ('imposto', 'Impostos & Taxas'),
    ('outros', 'Outros'),
]

COST_BEHAVIOR_CHOICES = [
    ('fixo', 'Fixo'),
    ('variavel', 'Variável'),
    ('mistura', 'Misto'),
]

DEFAULT_DECIMAL = Decimal('0.00')


DEFAULT_MARGIN_TARGET = Decimal('20.00')
DEFAULT_MARGIN_MINIMUM = Decimal('10.00')
DECIMAL_ZERO = Decimal('0.00')

class ServiceType(models.Model):
    """
    Tipo de serviço que pode ser executado por um Prestador (Provider).
    Ex: Consulta médica, Enfermagem, Fisioterapia, Psicologia, etc.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Nome do serviço'
    )

    description = models.TextField(
        blank=True,
        verbose_name='Descrição'
    )

    
    ferramentas = models.TextField(
        blank=True,
        verbose_name='Descrição'
    )

    duracao_estimada = models.IntegerField(
        blank=True,
        default=0,
        verbose_name='Tempo estimado'
    )

    duracao_media = models.IntegerField(
        blank=True,
        default=0,
        verbose_name='Tempo médio'
    )

    # Campos de Precificação
    billing_unit = models.CharField(
        max_length=20,
        choices=BILLING_UNIT_CHOICES,
        default='unidade',
        verbose_name='Unidade de Cobrança'
    )

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name='Valor Unitário',
        help_text='Valor por unidade (R$)'
    )


    estimated_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name='Valor Estimado',
        help_text='Valor Estimado (R$)'
    )
    tax_profile = models.ForeignKey(
        'servicetype.TaxProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Perfil Fiscal'
    )
    margin_target = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=DEFAULT_MARGIN_TARGET,
        validators=[
            MinValueValidator(Decimal('0.00')),
            MaxValueValidator(Decimal('100.00'))
        ],
        verbose_name='Margem Alvo (%)'
    )
    margin_minimum = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=DEFAULT_MARGIN_MINIMUM,
        validators=[
            MinValueValidator(Decimal('0.00')),
            MaxValueValidator(Decimal('100.00'))
        ],
        verbose_name='Margem Mínima (%)'
    )
    volume_baseline = models.PositiveIntegerField(
        default=1,
        verbose_name='Volume Base'
    )



    default_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1.00,
        verbose_name='Quantidade Padrão',
        help_text='Quantidade padrão de unidades para este serviço'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='Ativo'
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
        verbose_name = 'Tipo de Serviço'
        verbose_name_plural = 'Tipos de Serviço'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_total_price(self):
        """
        Calcula o valor total do serviço (valor unitário × quantidade padrão).
        """
        return self.unit_price * self.default_quantity

    def get_billing_unit_display_short(self):
        """
        Retorna abreviação da unidade de cobrança.
        """
        abbreviations = {
            'hora': 'h',
            'unidade': 'un',
            'km': 'km',
            'dia': 'd',
            'visita': 'vis',
            'm2': 'm²',
            'consulta': 'cons',
            'sessao': 'sess',
            'servico': 'serv',
            'outro': '-',
        }
        return abbreviations.get(self.billing_unit, self.billing_unit)

    def get_billing_unit_label(self):
        """
        Retorna rotulo legivel da unidade de cobranca.
        """
        if self.billing_unit == 'dia':
            return 'dias'
        return self.get_billing_unit_display()


    def clean(self):
        super().clean()
        if self.margin_target < self.margin_minimum:
            raise ValidationError({
                'margin_target': 'A margem alvo não pode ser inferior à margem mínima.'
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def total_estimated_cost(self):
        """
        Calcula o custo total estimado baseado na composição de custos (ServiceCost).
        Retorna a soma de (quantity × unit_cost_snapshot) de todos os custos associados.
        """
        from django.db.models import Sum, F, DecimalField
        from django.db.models.functions import Coalesce

        total = self.service_costs.aggregate(
            total=Coalesce(
                Sum(F('quantity') * F('unit_cost_snapshot'), output_field=DecimalField()),
                Decimal('0.00'),
                output_field=DecimalField()
            )
        )['total']
        return total or Decimal('0.00')

    def estimated_profit_margin_value(self):
        """
        Calcula a margem de lucro estimada em valor absoluto (R$).
        Margem = Preço Estimado - Custo Total Estimado
        """
        return self.estimated_price - self.total_estimated_cost()

    def estimated_profit_margin_percentage(self):
        """
        Calcula a margem de lucro estimada em percentual (%).
        Margem % = (Margem / Preço Estimado) × 100
        """
        if self.estimated_price == 0:
            return Decimal('0.00')
        margin_value = self.estimated_profit_margin_value()
        return (margin_value / self.estimated_price) * 100

    def get_cost_breakdown(self):
        """
        Retorna o breakdown detalhado de custos por tipo (direto, indireto, fixo, variável).
        """
        from django.db.models import Sum, F, DecimalField
        from django.db.models.functions import Coalesce

        breakdown = {
            'direto': Decimal('0.00'),
            'indireto': Decimal('0.00'),
            'fixo': Decimal('0.00'),
            'variavel': Decimal('0.00'),
        }

        # Custos por tipo
        cost_type_totals = self.service_costs.values('cost_item__cost_type').annotate(
            total=Coalesce(
                Sum(F('quantity') * F('unit_cost_snapshot'), output_field=DecimalField()),
                Decimal('0.00'),
                output_field=DecimalField()
            )
        )
        for item in cost_type_totals:
            cost_type = item['cost_item__cost_type']
            if cost_type in breakdown:
                breakdown[cost_type] = item['total']

        # Custos por comportamento
        cost_behavior_totals = self.service_costs.values('cost_item__cost_behavior').annotate(
            total=Coalesce(
                Sum(F('quantity') * F('unit_cost_snapshot'), output_field=DecimalField()),
                Decimal('0.00'),
                output_field=DecimalField()
            )
        )
        for item in cost_behavior_totals:
            cost_behavior = item['cost_item__cost_behavior']
            if cost_behavior in breakdown:
                breakdown[cost_behavior] = item['total']

        return breakdown

    def calculate_real_profit_from_workorders(self):
        """
        Calcula a margem de lucro REAL baseada em WorkOrders executadas.
        Compara labor_cost (preço cobrado) com custos reais das transações vinculadas.

        Retorna um dicionário com:
        - total_revenue: receita total de todas as OS deste serviço
        - total_real_cost: custo real total (soma das transações vinculadas)
        - profit_margin_value: margem em R$
        - profit_margin_percentage: margem em %
        - work_orders_count: quantidade de OS
        """
        from workorder.models import WorkOrder
        from finance.models import Transaction
        from django.db.models import Sum, Count, Q
        from django.db.models.functions import Coalesce

        # Buscar todas as WorkOrders concluídas deste tipo de serviço
        work_orders = WorkOrder.objects.filter(
            service_type=self,
            status__name__in=['Concluído', 'Finalizado']
        )

        # Receita total (labor_cost das OS)
        total_revenue = work_orders.aggregate(
            total=Coalesce(Sum('labor_cost'), Decimal('0.00'), output_field=DecimalField())
        )['total'] or Decimal('0.00')

        # Custo real total (transações de despesa vinculadas a este serviço)
        total_real_cost = Transaction.objects.filter(
            tipo='despesa',
            status='realizado',
            related_service_type=self
        ).aggregate(
            total=Coalesce(Sum('valor'), Decimal('0.00'), output_field=DecimalField())
        )['total'] or Decimal('0.00')

        # Quantidade de OS
        work_orders_count = work_orders.count()

        # Margem de lucro
        profit_margin_value = total_revenue - total_real_cost
        profit_margin_percentage = Decimal('0.00')
        if total_revenue > 0:
            profit_margin_percentage = (profit_margin_value / total_revenue) * 100

        return {
            'total_revenue': total_revenue,
            'total_real_cost': total_real_cost,
            'profit_margin_value': profit_margin_value,
            'profit_margin_percentage': profit_margin_percentage,
            'work_orders_count': work_orders_count,
            'average_revenue_per_order': total_revenue / work_orders_count if work_orders_count > 0 else Decimal('0.00'),
            'average_cost_per_order': total_real_cost / work_orders_count if work_orders_count > 0 else Decimal('0.00'),
        }


class TaxProfile(models.Model):
    """
    Perfil fiscal utilizado para calcular impostos e taxas agregadas ao serviço.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=140, unique=True, verbose_name='Nome do perfil fiscal')
    iss = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=DECIMAL_ZERO,
        validators=[MinValueValidator(DECIMAL_ZERO)],
        verbose_name='ISS (%)'
    )
    federal_taxes = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=DECIMAL_ZERO,
        validators=[MinValueValidator(DECIMAL_ZERO)],
        verbose_name='Impostos Federais (%)'
    )
    financial_fees = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=DECIMAL_ZERO,
        validators=[MinValueValidator(DECIMAL_ZERO)],
        verbose_name='Taxas Financeiras (%)'
    )
    is_active = models.BooleanField(default=True, verbose_name='Ativo')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Perfil Fiscal'
        verbose_name_plural = 'Perfis Fiscais'
        ordering = ['name']

    def __str__(self):
        return self.name

    def total_rate(self):
        return self.iss + self.federal_taxes + self.financial_fees

    def clean(self):
        super().clean()
        if self.total_rate() < DECIMAL_ZERO:
            raise ValidationError('As alíquotas não podem ser negativas.')


class CostItem(models.Model):
    """
    Catálogo de custos que compõem um serviço.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=140, unique=True, verbose_name='Nome do custo')
    description = models.TextField(blank=True, verbose_name='Descrição')
    cost_type = models.CharField(
        max_length=20,
        choices=COST_TYPE_CHOICES,
        default='direto',
        verbose_name='Tipo de custo'
    )
    billing_unit = models.CharField(
        max_length=20,
        choices=BILLING_UNIT_CHOICES,
        default='unidade',
        verbose_name='Unidade de cobrança'
    )
    unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=DEFAULT_DECIMAL,
        verbose_name='Custo unitário',
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    expense_group = models.CharField(
        max_length=20,
        choices=EXPENSE_GROUP_CHOICES,
        default='operacional',
        verbose_name='Grupo de despesa'
    )
    cost_behavior = models.CharField(
        max_length=10,
        choices=COST_BEHAVIOR_CHOICES,
        default='fixo',
        verbose_name='Comportamento de custo'
    )
    is_active = models.BooleanField(default=True, verbose_name='Ativo')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Item de Custo'
        verbose_name_plural = 'Itens de Custo'
        ordering = ['name']

    def __str__(self):
        return self.name


class ServiceCost(models.Model):
    """
    Associação entre serviços e custos para compor a precificação.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_type = models.ForeignKey(
        ServiceType,
        on_delete=models.CASCADE,
        related_name='service_costs',
        verbose_name='Serviço'
    )
    cost_item = models.ForeignKey(
        CostItem,
        on_delete=models.CASCADE,
        related_name='service_costs',
        verbose_name='Custo'
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Quantidade'
    )
    unit_cost_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=DEFAULT_DECIMAL,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Custo unitário congelado',
        help_text='Valor do custo no momento da associação'
    )
    is_required = models.BooleanField(
        default=True,
        verbose_name='Obrigatório'
        )
    notes = models.TextField(blank=True, verbose_name='Observações')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Custo do Serviço'
        verbose_name_plural = 'Custos dos Serviços'
        ordering = ['service_type', 'cost_item']
        constraints = [
            models.UniqueConstraint(
                fields=['service_type', 'cost_item'],
                name='unique_service_cost_per_pair'
            ),
        ]
        indexes = [
            models.Index(fields=['service_type']),
            models.Index(fields=['cost_item']),
        ]

    def __str__(self):
        return f'{self.service_type} — {self.cost_item}'

    def save(self, *args, **kwargs):
        if self._state.adding and self.cost_item and self.unit_cost_snapshot == DEFAULT_DECIMAL:
            self.unit_cost_snapshot = self.cost_item.unit_cost
        super().save(*args, **kwargs)

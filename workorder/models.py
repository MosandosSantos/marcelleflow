import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class WorkOrder(models.Model):
    """
    Ordem de Serviço (Work Order - W.O.)
    Modelo central do sistema.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Identificação operacional
    code = models.CharField(
        max_length=30,
        unique=True,
        verbose_name='Work order code'
    )
    # Ex: 01447167/02

    # Relacionamentos principais
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='work_orders',
        verbose_name='Cliente'
    )

    provider = models.ForeignKey(
        'provider.Provider',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='work_orders',
        verbose_name='Técnico'
    )

    service_type = models.ForeignKey(
        'servicetype.ServiceType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='work_orders',
        verbose_name='Tipo de serviço'
    )

    status = models.ForeignKey(
        'workorderstatus.ServiceOrderStatus',
        on_delete=models.PROTECT,
        related_name='work_orders',
        verbose_name='Status'
    )

    insurance_company = models.ForeignKey(
        'insurancecompany.InsuranceCompany',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='work_orders',
        verbose_name='Seguradora'
    )

    service_operator = models.ForeignKey(
        'servicesoperators.ServiceOperator',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='work_orders',
        verbose_name='Service operator'
    )

    # Dados do serviço
    description = models.TextField(
        verbose_name='Descriçao do Serviço'
    )

    # Endereço de atendimento (pode ser diferente do endereço cadastral do cliente)
    address = models.TextField(
        blank=True,
        verbose_name='Endere?o completo'
    )



    # Campos estruturados de endere?o
    address_zip = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='CEP'
    )
    address_street = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Rua'
    )
    address_number = models.CharField(
        max_length=30,
        blank=True,
        verbose_name='N?mero'
    )
    address_complement = models.CharField(
        max_length=120,
        blank=True,
        verbose_name='Complemento'
    )
    address_neighborhood = models.CharField(
        max_length=120,
        blank=True,
        verbose_name='Bairro'
    )
    address_city = models.CharField(
        max_length=120,
        blank=True,
        verbose_name='Cidade'
    )
    address_state = models.CharField(
        max_length=60,
        blank=True,
        verbose_name='Estado'
    )

    # Geolocaliza??o do endere?o
    latitude = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Latitude'
    )
    longitude = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Longitude'
    )
    technical_report = models.TextField(
        blank=True,
        verbose_name='Technical report'
    )
    # Campo "LAUDO"

    # Ações tomadas durante o serviço
    actions = models.TextField(
        blank=True,
        verbose_name='Actions taken'
    )

    # Datas operacionais
    scheduled_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Scheduled date'
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Início'
    )

    finished_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Término'
    )
    closed_on = models.DateField(
        null=True,
        blank=True,
        verbose_name='Data de encerramento'
    )

    # Métricas de tempo
    estimated_time_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Tempo estimado'
    )

    real_time_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Tempo real'
    )

    # Avalia??o do cliente (0 = n?o avaliado, 1-5 = satisfa??o)
    evaluation_rating = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        verbose_name='Avaliação (0-5 estrelas)'
    )

    # Controle financeiro básico (sem faturamento ainda)
    labor_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Labor cost'
    )

    # Controle
    is_active = models.BooleanField(
        default=True,
        verbose_name='Active'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created at'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated at'
    )

    class Meta:
        verbose_name = 'Work Order'
        verbose_name_plural = 'Work Orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['status']),
            models.Index(fields=['scheduled_date']),
        ]

    def __str__(self):
        return self.code

    def build_full_address(self):
        parts = [
            self.address_street,
            self.address_number,
            self.address_complement,
            self.address_neighborhood,
            self.address_city,
            self.address_state,
            self.address_zip,
        ]
        cleaned = [p.strip() for p in parts if p and str(p).strip()]
        if cleaned:
            return ', '.join(cleaned)
        return self.address or ''

    def save(self, *args, **kwargs):
        # Atualiza endere?o completo antes de salvar
        self.address = self.build_full_address()

        should_geocode = bool(self.address) and (self.latitude is None or self.longitude is None)
        if self.pk:
            previous = WorkOrder.objects.filter(pk=self.pk).only(
                'address', 'latitude', 'longitude',
                'address_zip', 'address_street', 'address_number',
                'address_complement', 'address_neighborhood',
                'address_city', 'address_state'
            ).first()
            if previous and previous.address != self.address:
                should_geocode = True

        if should_geocode:
            try:
                from .geocoding import geocode_address
                lat, lng = geocode_address(self.address)
                if lat is not None and lng is not None:
                    self.latitude = lat
                    self.longitude = lng
            except Exception:
                # Se falhar, salva sem geolocaliza??o
                pass

        super().save(*args, **kwargs)

    def is_ready_to_finalize(self):
        if not self.provider or not self.insurance_company or not self.service_operator:
            return False
        if not self.service_type:
            return False
        if not self.description or not str(self.description).strip():
            return False
        if not self.technical_report or not str(self.technical_report).strip():
            return False
        if not self.labor_cost:
            return False
        return True


class WorkOrderEvaluation(models.Model):
    """
    Avaliação de uma Ordem de Serviço pelo cliente.
    Permite rating de 1 a 5 estrelas + comentário opcional.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    work_order = models.OneToOneField(
        'WorkOrder',
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

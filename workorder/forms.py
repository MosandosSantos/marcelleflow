from django import forms
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from .models import WorkOrder, WorkOrderEvaluation
from clients.models import Client
from provider.models import Provider
from servicetype.models import ServiceType
from workorderstatus.models import ServiceOrderStatus
from insurancecompany.models import InsuranceCompany
from servicesoperators.models import ServiceOperator


class WorkOrderForm(forms.ModelForm):
    """
    Formulário para criar/editar Ordem de Serviço.
    Usado por admin/operadores.
    """

    class Meta:
        model = WorkOrder
        fields = [
            'code', 'client', 'provider', 'service_type', 'status',
            'insurance_company', 'service_operator',
            'address_zip', 'address_street', 'address_number',
            'address_complement', 'address_neighborhood',
            'address_city', 'address_state',
            'technical_report',
            'description', 'scheduled_date', 'closed_on', 'labor_cost'
        ]
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'w-full px-4 py-4 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all duration-300 text-gray-800',
                'placeholder': 'Ex: 01447167/02'
            }),
            'client': forms.Select(attrs={
                'class': 'w-full px-4 py-4 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100 transition-all duration-300 text-gray-800',
                'id': 'id_client'
            }),
            'provider': forms.Select(attrs={
                'class': 'w-full px-4 py-4 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all duration-300 text-gray-800'
            }),
            'service_type': forms.Select(attrs={
                'class': 'w-full px-4 py-4 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all duration-300 text-gray-800'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full px-4 py-4 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all duration-300 text-gray-800'
            }),
            'address_zip': forms.TextInput(attrs={
                'class': 'w-full px-4 py-4 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all duration-300 text-gray-800',
                'placeholder': 'CEP'
            }),
            'address_street': forms.TextInput(attrs={
                'class': 'w-full px-4 py-4 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all duration-300 text-gray-800',
                'placeholder': 'Rua'
            }),
            'address_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-4 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all duration-300 text-gray-800',
                'placeholder': 'Numero'
            }),
            'address_complement': forms.TextInput(attrs={
                'class': 'w-full px-4 py-4 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all duration-300 text-gray-800',
                'placeholder': 'Complemento'
            }),
            'address_neighborhood': forms.TextInput(attrs={
                'class': 'w-full px-4 py-4 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all duration-300 text-gray-800',
                'placeholder': 'Bairro'
            }),
            'address_city': forms.TextInput(attrs={
                'class': 'w-full px-4 py-4 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all duration-300 text-gray-800',
                'placeholder': 'Cidade'
            }),
            'address_state': forms.TextInput(attrs={
                'class': 'w-full px-4 py-4 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all duration-300 text-gray-800',
                'placeholder': 'Estado'
            }),
            'insurance_company': forms.Select(attrs={
                'class': 'w-full px-4 py-4 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all duration-300 text-gray-800'
            }),
            'service_operator': forms.Select(attrs={
                'class': 'w-full px-4 py-4 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all duration-300 text-gray-800'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-4 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all duration-300 text-gray-800',
                'rows': 4,
                'placeholder': 'Descreva o serviço a ser realizado...'
            }),
            'technical_report': forms.Textarea(attrs={
                'class': 'w-full px-4 py-4 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all duration-300 text-gray-800',
                'rows': 4,
                'placeholder': 'Laudo técnico (preenchido após execução)...'
            }),
            'scheduled_date': forms.DateInput(format='%Y-%m-%d', attrs={
                'type': 'date',
                'class': 'w-full px-4 py-4 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all duration-300 text-gray-800'
            }),
            'closed_on': forms.DateInput(format='%Y-%m-%d', attrs={
                'type': 'date',
                'class': 'w-full px-4 py-4 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all duration-300 text-gray-800'
            }),
            'labor_cost': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-4 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all duration-300 text-gray-800',
                'placeholder': '0.00',
                'step': '0.01'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        today = timezone.localdate()
        # Filtrar apenas itens ativos
        self.fields['client'].queryset = Client.objects.all().order_by('full_name', 'cpf', 'cnpj')
        self.fields['client'].required = True
        self.fields['client'].empty_label = 'Selecione um cliente'
        self.fields['client'].label_from_instance = lambda obj: (
            f"{obj.full_name} ({obj.cpf or obj.cnpj or 'Sem documento'})"
        )
        self.fields['provider'].queryset = Provider.objects.all().order_by('full_name')
        self.fields['service_type'].queryset = ServiceType.objects.filter(is_active=True).order_by('name')
        self.fields['status'].queryset = ServiceOrderStatus.objects.filter(is_active=True).order_by('status_order')

        # Tornar campos opcionais no formulário (já são no modelo)
        self.fields['address_zip'].required = False
        self.fields['address_street'].required = False
        self.fields['address_number'].required = False
        self.fields['address_complement'].required = False
        self.fields['address_neighborhood'].required = False
        self.fields['address_city'].required = False
        self.fields['address_state'].required = False
        self.fields['insurance_company'].required = False
        self.fields['service_operator'].required = False
        self.fields['technical_report'].required = False
        self.fields['labor_cost'].required = False
        if 'scheduled_date' in self.fields:
            self.fields['scheduled_date'].required = False
            if not self.instance or not self.instance.pk:
                self.fields['scheduled_date'].widget.attrs['min'] = today.isoformat()
            if self.instance and self.instance.pk and self.instance.scheduled_date:
                self.fields['scheduled_date'].initial = self.instance.scheduled_date
        if 'closed_on' in self.fields:
            self.fields['closed_on'].required = False
            self.fields['closed_on'].widget.attrs['max'] = today.isoformat()
            # Se houver termino registrado, sugere a data como encerramento.
            if self.instance and self.instance.pk and not self.instance.closed_on and self.instance.finished_at:
                self.fields['closed_on'].initial = self.instance.finished_at.date()
            elif self.instance and self.instance.pk and self.instance.closed_on:
                self.fields['closed_on'].initial = self.instance.closed_on

        # Ocultar status na criação (status definido automaticamente)
        if not self.instance or not self.instance.pk:
            self.fields.pop('status', None)
        elif user and 'status' in self.fields:
            # Na edição, não permitir status "aberta" nem "encerrado financeiramente"
            self.fields['status'].queryset = self.fields['status'].queryset.exclude(
                group_code='OPEN'
            ).exclude(status_code='FINANCIAL_CLOSED')
            # Filtrar status visíveis conforme perfil
            if user.is_superuser or user.role == 'admin':
                pass
            if user.role == 'operational':
                self.fields['status'].queryset = ServiceOrderStatus.objects.filter(
                    is_active=True,
                    group_code__in=['OPEN', 'IN_PROGRESS', 'CLOSED', 'VALIDATION']
                ).order_by('status_order')
            # Garante que o status atual apareça mesmo se estiver fora do filtro.
            current_status = getattr(self.instance, 'status', None)
            if current_status and current_status.pk:
                if not self.fields['status'].queryset.filter(pk=current_status.pk).exists():
                    self.fields['status'].queryset = (
                        self.fields['status'].queryset | ServiceOrderStatus.objects.filter(pk=current_status.pk)
                    ).order_by('status_order')

    def clean_client(self):
        client = self.cleaned_data.get('client')
        if not client:
            raise forms.ValidationError('Selecione um cliente cadastrado.')
        return client

    def clean_scheduled_date(self):
        scheduled_date = self.cleaned_data.get('scheduled_date')
        if not scheduled_date:
            return scheduled_date
        # Regra apenas na criação: data de abertura não pode ser anterior a hoje.
        if (not self.instance or not self.instance.pk) and scheduled_date < timezone.localdate():
            raise forms.ValidationError('A data de abertura não pode ser inferior à data de hoje.')
        return scheduled_date

    def clean_closed_on(self):
        closed_on = self.cleaned_data.get('closed_on')
        if not closed_on:
            return closed_on
        if closed_on > timezone.localdate():
            raise forms.ValidationError('A data de encerramento não pode ser posterior à data de hoje.')
        return closed_on

    def clean_labor_cost(self):
        value = self.cleaned_data.get('labor_cost')
        if value in (None, ''):
            return value
        if isinstance(value, Decimal):
            return value

        raw = str(value).strip()
        raw = raw.replace('R$', '').replace(' ', '')
        if not raw:
            return None

        def to_decimal(text):
            try:
                return Decimal(text)
            except InvalidOperation:
                raise forms.ValidationError('Valor informado é inválido.')

        if ',' in raw and '.' in raw:
            last_comma = raw.rfind(',')
            last_dot = raw.rfind('.')
            if last_comma > last_dot:
                normalized = raw.replace('.', '')
                decimals = normalized.split(',')[-1]
                if len(decimals) > 2:
                    raise forms.ValidationError('Use no máximo duas casas decimais.')
                normalized = normalized.replace(',', '.')
                return to_decimal(normalized)
            normalized = raw.replace(',', '')
            decimals = normalized.split('.')[-1]
            if len(decimals) > 2:
                raise forms.ValidationError('Use no máximo duas casas decimais.')
            return to_decimal(normalized)

        if ',' in raw:
            parts = raw.split(',')
            if len(parts) > 2:
                raise forms.ValidationError('Valor informado é inválido.')
            decimals = parts[-1]
            if len(decimals) == 3 and decimals.isdigit():
                normalized = ''.join(parts)
                return to_decimal(normalized)
            if len(decimals) > 2:
                raise forms.ValidationError('Use no máximo duas casas decimais.')
            normalized = raw.replace(',', '.')
            return to_decimal(normalized)

        if '.' in raw:
            parts = raw.split('.')
            if len(parts) > 2 and all(len(p) == 3 for p in parts[1:]):
                normalized = ''.join(parts)
                return to_decimal(normalized)
            decimals = parts[-1]
            if len(decimals) == 3 and decimals.isdigit():
                normalized = ''.join(parts)
                return to_decimal(normalized)
            if len(decimals) > 2:
                raise forms.ValidationError('Use no máximo duas casas decimais.')
            return to_decimal(raw)

        return to_decimal(raw)


class WorkOrderFilterForm(forms.Form):
    """
    Formulário para filtrar listagem de OS.
    """
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary',
            'placeholder': 'Buscar por código, cliente ou prestador...'
        })
    )

    status = forms.ModelChoiceField(
        queryset=ServiceOrderStatus.objects.filter(is_active=True),
        required=False,
        empty_label='Todos os status',
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary'
        })
    )

    service_type = forms.ModelChoiceField(
        queryset=ServiceType.objects.filter(is_active=True),
        required=False,
        empty_label='Todos os serviços',
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary'
        })
    )

    service_operator = forms.ModelChoiceField(
        queryset=ServiceOperator.objects.filter(is_active=True),
        required=False,
        empty_label='Todas as operadoras',
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary'
        })
    )

    insurance_company = forms.ModelChoiceField(
        queryset=InsuranceCompany.objects.filter(is_active=True),
        required=False,
        empty_label='Todas as seguradoras',
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary'
        })
    )


class WorkOrderEvaluationForm(forms.ModelForm):
    """
    Formulário de avaliação de OS pelo cliente.
    """
    rating = forms.ChoiceField(
        choices=[(i, f'{i} Estrelas') for i in range(1, 6)],
        widget=forms.RadioSelect(attrs={
            'class': 'rating-input'
        }),
        label='Avaliação'
    )

    class Meta:
        model = WorkOrderEvaluation
        fields = ['rating', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={
                'class': 'w-full px-4 py-4 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all duration-300 text-gray-800',
                'rows': 4,
                'placeholder': 'Conte-nos sobre sua experiência (opcional)...'
            })
        }
        labels = {
            'comment': 'Comentário (opcional)'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['comment'].required = False

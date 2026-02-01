import json
from decimal import Decimal, InvalidOperation
from urllib.request import urlopen

from django import forms

try:
    import requests
except Exception:  # pragma: no cover - optional dependency for API fetch
    requests = None
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Account, Category, Transaction


BASE_INPUT_CLASS = (
    'w-full px-4 py-3 border border-gray-300 rounded-lg '
    'focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent'
)

_BANK_CHOICES_CACHE = None
_BANK_CODE_NAME_MAP = None

_DEFAULT_BANKS = [
    {'code': '001', 'name': 'Banco do Brasil'},
    {'code': '033', 'name': 'Santander'},
    {'code': '104', 'name': 'Caixa Economica Federal'},
    {'code': '237', 'name': 'Bradesco'},
    {'code': '341', 'name': 'Itau'},
    {'code': '260', 'name': 'Nubank'},
    {'code': '323', 'name': 'Mercado Pago'},
    {'code': '336', 'name': 'Banco C6'},
    {'code': '077', 'name': 'Banco Inter'},
    {'code': '218', 'name': 'Banco BS2'},
    {'code': '637', 'name': 'Banco Sofisa Direto'},
    {'code': '655', 'name': 'Banco Votorantim'},
    {'code': '212', 'name': 'Banco Original'},
    {'code': '746', 'name': 'Banco Modal'},
    {'code': '197', 'name': 'Stone'},
    {'code': '380', 'name': 'PicPay'},
]


def _build_bank_choices(banks):
    def normalize_name(bank):
        return bank.get('name') or bank.get('fullName') or ''

    choices = []
    code_name_map = {}
    for bank in banks:
        raw_code = bank.get('code')
        code = str(raw_code).zfill(3) if raw_code is not None else ''
        name = normalize_name(bank).strip()
        if not name:
            continue
        label = f"{code} - {name}" if code.strip('0') else name
        value = code if code.strip('0') else name
        choices.append((value, label))
        if code.strip('0'):
            code_name_map[value] = name

    choices.sort(key=lambda item: item[1].lower())
    return choices, code_name_map


def _fetch_bank_choices():
    global _BANK_CHOICES_CACHE, _BANK_CODE_NAME_MAP
    if _BANK_CHOICES_CACHE is not None and _BANK_CODE_NAME_MAP is not None:
        return _BANK_CHOICES_CACHE, _BANK_CODE_NAME_MAP

    banks = None
    try:
        if requests is not None:
            response = requests.get('https://brasilapi.com.br/api/banks/v1', timeout=5)
            response.raise_for_status()
            banks = response.json() or None
        else:
            with urlopen('https://brasilapi.com.br/api/banks/v1', timeout=5) as response:
                banks = json.loads(response.read().decode('utf-8')) or None
    except Exception:
        banks = None

    if not banks:
        banks = list(_DEFAULT_BANKS)

    choices, code_name_map = _build_bank_choices(banks)
    _BANK_CHOICES_CACHE = choices
    _BANK_CODE_NAME_MAP = code_name_map
    return _BANK_CHOICES_CACHE, _BANK_CODE_NAME_MAP


class CategorySelect(forms.Select):
    def __init__(self, *args, category_type_map=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.category_type_map = category_type_map or {}

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        raw_value = value.value if hasattr(value, "value") else value
        if raw_value not in (None, ""):
            tipo = self.category_type_map.get(str(raw_value))
            if tipo:
                option["attrs"]["data-tipo"] = tipo
        return option


class AccountForm(forms.ModelForm):
    saldo_sistema = forms.CharField(
        label='Saldo no sistema',
        required=False,
        disabled=True,
        widget=forms.TextInput(attrs={'class': BASE_INPUT_CLASS})
    )

    class Meta:
        model = Account
        fields = [
            'nome',
            'bank_code',
            'agencia',
            'agencia_dv',
            'conta_numero',
            'conta_dv',
            'tipo',
            'saldo_inicial',
            'ativa',
            'is_primary',
        ]
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': BASE_INPUT_CLASS,
                'placeholder': 'Nome da instituição'
            }),
            'bank_code': forms.Select(attrs={
                'class': BASE_INPUT_CLASS,
            }),
            'agencia': forms.TextInput(attrs={
                'class': BASE_INPUT_CLASS,
                'placeholder': 'Ex: 1234'
            }),
            'agencia_dv': forms.TextInput(attrs={
                'class': BASE_INPUT_CLASS,
                'placeholder': 'Ex: 0'
            }),
            'conta_numero': forms.TextInput(attrs={
                'class': BASE_INPUT_CLASS,
                'placeholder': 'Ex: 00012345'
            }),
            'conta_dv': forms.TextInput(attrs={
                'class': BASE_INPUT_CLASS,
                'placeholder': 'Ex: 9'
            }),
            'tipo': forms.Select(attrs={
                'class': BASE_INPUT_CLASS,
            }),
            'saldo_inicial': forms.NumberInput(attrs={
                  'class': BASE_INPUT_CLASS,
                  'placeholder': '0.00',
                  'step': '0.01'
              }),
            'ativa': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-primary border-gray-300 rounded focus:ring-primary'
            }),
            'is_primary': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-primary border-gray-300 rounded focus:ring-primary'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.is_bound:
            raw_value = self.data.get(self.add_prefix('saldo_inicial'))
            if isinstance(raw_value, str) and ',' in raw_value:
                normalized = raw_value.replace('.', '').replace(',', '.')
                data = self.data.copy()
                data[self.add_prefix('saldo_inicial')] = normalized
                self.data = data

        choices, code_name_map = _fetch_bank_choices()
        choices = [('', 'Selecione a instituição')] + choices
        current_name = None
        current_code = None
        if self.instance and self.instance.pk:
            current_name = self.instance.nome
            current_code = self.instance.bank_code

        if current_name and not current_code and all(current_name != value for value, _ in choices):
            choices.insert(1, (current_name, current_name))
        if current_code and all(current_code != value for value, _ in choices):
            label = f"{current_code} - {current_name}" if current_name else current_code
            choices.insert(1, (current_code, label))

        if len(choices) > 1:
            self.fields['bank_code'] = forms.ChoiceField(
                choices=choices,
                label='Instituição Financeira',
                required=True,
                widget=forms.Select(attrs={'class': BASE_INPUT_CLASS}),
            )
            self.fields['nome'].widget = forms.HiddenInput()
            self.fields['nome'].required = False
            if current_code:
                self.fields['bank_code'].initial = current_code
            elif current_name:
                self.fields['bank_code'].initial = current_name
        else:
            self.fields['nome'] = forms.CharField(
                label='Instituição Financeira',
                required=True,
                widget=forms.TextInput(attrs={
                    'class': BASE_INPUT_CLASS,
                    'placeholder': 'Nome da instituição'
                }),
            )
            self.fields['bank_code'].required = False

        self._bank_code_name_map = code_name_map
        if self.instance and self.instance.pk:
            saldo = self.instance.calcular_saldo_atual()
            self.fields['saldo_sistema'].initial = f"R$ {saldo:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    def clean(self):
        cleaned_data = super().clean()
        bank_code = cleaned_data.get('bank_code')
        nome = cleaned_data.get('nome')

        if bank_code:
            bank_name = self._bank_code_name_map.get(bank_code)
            if bank_name:
                cleaned_data['nome'] = bank_name
            else:
                cleaned_data['nome'] = nome or bank_code
        return cleaned_data

    def clean_saldo_inicial(self):
        value = self.cleaned_data.get('saldo_inicial')
        raw_value = self.data.get(self.add_prefix('saldo_inicial'))
        if isinstance(raw_value, str) and ',' in raw_value:
            normalized = raw_value.replace('.', '').replace(',', '.')
            try:
                return Decimal(normalized)
            except InvalidOperation:
                return value
        return value


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['nome', 'tipo', 'dre_group', 'descricao', 'ativa']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': BASE_INPUT_CLASS,
                'placeholder': 'Nome da categoria'
            }),
            'tipo': forms.Select(attrs={
                'class': BASE_INPUT_CLASS,
            }),
            'dre_group': forms.Select(attrs={
                'class': BASE_INPUT_CLASS,
            }),
            'descricao': forms.Textarea(attrs={
                'class': BASE_INPUT_CLASS,
                'rows': 3,
                'placeholder': 'Descricao opcional'
            }),
            'ativa': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-primary border-gray-300 rounded focus:ring-primary'
            }),
        }


class TransactionForm(forms.ModelForm):
    installments = forms.IntegerField(
        min_value=1,
        max_value=24,
        initial=1,
        required=False,
        label='Parcelas',
        widget=forms.NumberInput(attrs={
            'class': BASE_INPUT_CLASS,
            'min': '1',
            'max': '24'
        })
    )
    class Meta:
        model = Transaction
        fields = [
            'tipo',
            'descricao',
            'valor',
            'data_vencimento',
            'data_pagamento',
            'account',
            'category',
            'expense_type',
            'is_recurring',
            'recurrence_period',
            'related_service_type',
            'observacoes',
            'installments',
        ]
        widgets = {
            'tipo': forms.Select(attrs={'class': BASE_INPUT_CLASS}),
            'descricao': forms.TextInput(attrs={
                'class': BASE_INPUT_CLASS,
                'placeholder': 'Ex: Pagamento de fornecedor'
            }),
            'valor': forms.NumberInput(attrs={
                'class': BASE_INPUT_CLASS,
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.01'
            }),
            'data_vencimento': forms.DateInput(attrs={
                'class': BASE_INPUT_CLASS,
                'type': 'date'
            }),
            'data_pagamento': forms.DateInput(attrs={
                'class': BASE_INPUT_CLASS,
                'type': 'date'
            }),
            'account': forms.Select(attrs={'class': BASE_INPUT_CLASS}),
            'category': CategorySelect(attrs={'class': BASE_INPUT_CLASS}),
            'observacoes': forms.Textarea(attrs={
                'class': BASE_INPUT_CLASS,
                'rows': 3,
                'placeholder': 'Observacoes opcionais'
            }),
            'expense_type': forms.Select(attrs={'class': BASE_INPUT_CLASS}),
            'is_recurring': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-primary border-gray-300 rounded focus:ring-primary'
            }),
            'recurrence_period': forms.Select(attrs={'class': BASE_INPUT_CLASS}),
            'related_service_type': forms.Select(attrs={'class': BASE_INPUT_CLASS}),
        }
        labels = {
            'tipo': 'Tipo de Lancamento',
            'descricao': 'Descricao',
            'valor': 'Valor (R$)',
            'data_vencimento': 'Data de Vencimento',
            'data_pagamento': 'Data de Pagamento',
            'account': 'Conta',
            'category': 'Categoria',
            'expense_type': 'Tipo de Despesa',
            'is_recurring': 'Despesa Recorrente?',
            'recurrence_period': 'Período de Recorrência',
            'related_service_type': 'Tipo de Serviço Relacionado',
            'observacoes': 'Observacoes',
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if user:
            self.fields['account'].queryset = Account.objects.filter(ativa=True)
        self.fields['category'].queryset = Category.objects.filter(ativa=True).order_by('tipo', 'nome')

        category_type_map = {
            str(category.pk): category.tipo for category in self.fields['category'].queryset
        }
        widget = self.fields['category'].widget
        if isinstance(widget, CategorySelect):
            widget.category_type_map = category_type_map
        else:
            widget = CategorySelect(
                attrs={'class': BASE_INPUT_CLASS},
                category_type_map=category_type_map,
            )
            widget.choices = self.fields['category'].choices
            self.fields['category'].widget = widget

        self.fields['data_pagamento'].required = False
        self.fields['observacoes'].required = False
        self.fields['expense_type'].required = False
        self.fields['is_recurring'].required = False
        self.fields['recurrence_period'].required = False
        self.fields['related_service_type'].required = False
        self.fields['installments'].required = False

        # Importar ServiceType para o campo relacionado
        from servicetype.models import ServiceType
        self.fields['related_service_type'].queryset = ServiceType.objects.filter(is_active=True).order_by('name')

        if self.instance and self.instance.pk:
            total = self.instance.installment_total or 1
            self.fields['installments'].initial = total
            self.fields['installments'].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        data_pagamento = cleaned_data.get('data_pagamento')
        tipo = cleaned_data.get('tipo')
        category = cleaned_data.get('category')
        installments = cleaned_data.get('installments') or 1

        if status == 'realizado' and not data_pagamento:
            cleaned_data['data_pagamento'] = timezone.now().date()

        if tipo and category and tipo != category.tipo:
            raise ValidationError({
                'category': f'A categoria deve ser do tipo {dict(Transaction.TIPO_CHOICES)[tipo]}.'
            })

        if installments < 1:
            installments = 1
        cleaned_data['installments'] = installments

        if tipo != 'despesa' and installments > 1:
            self.add_error('installments', 'Parcelamento somente para despesas.')

        if installments > 1 and not cleaned_data.get('data_vencimento'):
            self.add_error('data_vencimento', 'Informe a data de vencimento da primeira parcela.')

        if installments > 1 and data_pagamento:
            self.add_error('data_pagamento', 'Parcelas nao podem ter data de pagamento no cadastro.')

        return cleaned_data

    def clean_valor(self):
        value = self.cleaned_data.get('valor')
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
                raise ValidationError('Valor informado é inválido.')

        if ',' in raw and '.' in raw:
            last_comma = raw.rfind(',')
            last_dot = raw.rfind('.')
            if last_comma > last_dot:
                normalized = raw.replace('.', '')
                decimals = normalized.split(',')[-1]
                if len(decimals) > 2:
                    raise ValidationError('Use no máximo duas casas decimais.')
                normalized = normalized.replace(',', '.')
                return to_decimal(normalized)
            normalized = raw.replace(',', '')
            decimals = normalized.split('.')[-1]
            if len(decimals) > 2:
                raise ValidationError('Use no máximo duas casas decimais.')
            return to_decimal(normalized)

        if ',' in raw:
            parts = raw.split(',')
            if len(parts) > 2:
                raise ValidationError('Valor informado é inválido.')
            decimals = parts[-1]
            if len(decimals) == 3 and decimals.isdigit():
                normalized = ''.join(parts)
                return to_decimal(normalized)
            if len(decimals) > 2:
                raise ValidationError('Use no máximo duas casas decimais.')
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
                raise ValidationError('Use no máximo duas casas decimais.')
            return to_decimal(raw)

        return to_decimal(raw)



class TransactionFilterForm(forms.Form):
    tipo = forms.ChoiceField(
        choices=[('', 'Todos')] + Transaction.TIPO_CHOICES,
        required=False,
        label='Tipo',
        widget=forms.Select(attrs={'class': BASE_INPUT_CLASS})
    )
    status = forms.ChoiceField(
        choices=[('', 'Todos')] + Transaction.STATUS_CHOICES,
        required=False,
        label='Status',
        widget=forms.Select(attrs={'class': BASE_INPUT_CLASS})
    )
    expense_type = forms.ChoiceField(
        choices=[('', 'Todos os tipos')] + Transaction.EXPENSE_TYPE_CHOICES,
        required=False,
        label='Tipo de Despesa',
        widget=forms.Select(attrs={'class': BASE_INPUT_CLASS})
    )
    is_installment = forms.ChoiceField(
        choices=[('', 'Todas'), ('true', 'Apenas Parcelas'), ('false', 'Sem Parcelas')],
        required=False,
        label='Parcelas',
        widget=forms.Select(attrs={'class': BASE_INPUT_CLASS})
    )
    payment_origin = forms.ChoiceField(
        choices=[('', 'Todas as origens')] + Transaction.PAYMENT_ORIGIN_CHOICES,
        required=False,
        label='Origem',
        widget=forms.Select(attrs={'class': BASE_INPUT_CLASS})
    )
    is_recurring = forms.ChoiceField(
        choices=[('', 'Todas'), ('true', 'Apenas Recorrentes'), ('false', 'Apenas ?nicas')],
        required=False,
        label='Recorr?ncia',
        widget=forms.Select(attrs={'class': BASE_INPUT_CLASS})
    )
    recurrence_period = forms.ChoiceField(
        choices=[('', 'Todos os per?odos')] + Transaction.RECURRENCE_PERIOD_CHOICES,
        required=False,
        label='Per?odo',
        widget=forms.Select(attrs={'class': BASE_INPUT_CLASS})
    )
    account = forms.ModelChoiceField(
        queryset=Account.objects.none(),
        required=False,
        empty_label='Todas as contas',
        label='Conta',
        widget=forms.Select(attrs={'class': BASE_INPUT_CLASS})
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.none(),
        required=False,
        empty_label='Todas as categorias',
        label='Categoria',
        widget=forms.Select(attrs={'class': BASE_INPUT_CLASS})
    )
    data_inicio = forms.DateField(
        required=False,
        label='Data Inicio',
        widget=forms.DateInput(attrs={
            'class': BASE_INPUT_CLASS,
            'type': 'date'
        })
    )
    data_fim = forms.DateField(
        required=False,
        label='Data Fim',
        widget=forms.DateInput(attrs={
            'class': BASE_INPUT_CLASS,
            'type': 'date'
        })
    )
    search = forms.CharField(
        required=False,
        label='Buscar',
        widget=forms.TextInput(attrs={
            'class': BASE_INPUT_CLASS,
            'placeholder': 'Buscar por descricao...'
        })
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['account'].queryset = Account.objects.filter(ativa=True)
        self.fields['category'].queryset = Category.objects.filter(ativa=True).order_by('tipo', 'nome')


class MarkAsCompletedForm(forms.Form):
    confirmacao = forms.BooleanField(
        required=True,
        label='Confirmo que as informações bancárias estão corretas.'
    )
    data_pagamento = forms.DateField(
        required=False,
        label='Data de Pagamento',
        help_text='Deixe em branco para usar a data de hoje',
        widget=forms.DateInput(attrs={
            'class': BASE_INPUT_CLASS,
            'type': 'date'
        })
    )

    def clean_data_pagamento(self):
        data_pagamento = self.cleaned_data.get('data_pagamento')
        return data_pagamento or timezone.now().date()





class InstallmentInvoiceForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.installment = kwargs.pop('installment', None)
        super().__init__(*args, **kwargs)

    payment_origin = forms.ChoiceField(
        choices=[('', 'Selecione')] + list(Transaction.PAYMENT_ORIGIN_CHOICES),
        label='Forma de pagamento',
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent'
        })
    )
    generate_nf = forms.BooleanField(
        required=False,
        label='Gerar NF',
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded text-primary focus:ring-primary'
        })
    )
    invoice_number = forms.CharField(
        required=False,
        label='Numero da NF',
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent'
        })
    )
    invoice_issued_at = forms.DateField(
        required=False,
        label='Data de emissao da NF',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent'
        })
    )
    invoice_description = forms.CharField(
        required=False,
        label='Descricao do servico na NF',
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent'
        })
    )
    service_city = forms.CharField(
        required=False,
        label='Cidade de prestacao',
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent'
        })
    )
    generate_boleto = forms.BooleanField(
        required=False,
        label='Gerar boleto',
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded text-primary focus:ring-primary'
        })
    )
    boleto_number = forms.CharField(
        required=False,
        label='Numero do boleto',
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent'
        })
    )
    boleto_issued_at = forms.DateField(
        required=False,
        label='Data de emissao do boleto',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent'
        })
    )

    def clean(self):
        cleaned = super().clean()
        payment_origin = cleaned.get('payment_origin')
        generate_nf = cleaned.get('generate_nf')
        generate_boleto = cleaned.get('generate_boleto')

        if not generate_nf and not generate_boleto:
            raise forms.ValidationError('Selecione pelo menos uma opcao: NF ou boleto.')

        if payment_origin and payment_origin != 'boleto':
            if generate_boleto:
                raise forms.ValidationError('Boleto so pode ser gerado quando a forma de pagamento for boleto.')
            cleaned['generate_boleto'] = False

        if generate_nf and not cleaned.get('invoice_number'):
            self.add_error('invoice_number', 'Informe o numero da NF.')
        if generate_nf and not cleaned.get('invoice_issued_at'):
            self.add_error('invoice_issued_at', 'Informe a data de emissao da NF.')

        if generate_nf:
            invoice_number = cleaned.get('invoice_number')
            invoice_issued_at = cleaned.get('invoice_issued_at')
            if invoice_issued_at and invoice_issued_at < timezone.localdate():
                self.add_error('invoice_issued_at', 'A data da NF n?o pode ser anterior a hoje.')
            if invoice_number:
                qs = Transaction.objects.filter(invoice_number=invoice_number)
                if self.installment:
                    qs = qs.exclude(pk=self.installment.pk)
                if qs.exists():
                    self.add_error('invoice_number', 'Este n?mero de NF j? est? em uso.')

        return cleaned
class WorkOrderPaymentForm(forms.Form):
    installments = forms.IntegerField(
        min_value=1,
        max_value=24,
        initial=1,
        label='Parcelas',
        widget=forms.NumberInput(attrs={
            'class': BASE_INPUT_CLASS,
            'min': '1',
            'max': '24'
        })
    )
    confirm_regenerate = forms.BooleanField(
        required=False,
        label='Confirmo a recria??o das parcelas canceladas',
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-primary border-gray-300 rounded focus:ring-primary'
        })
    )
    first_due_date = forms.DateField(
        label='Data de vencimento da 1? parcela',
        widget=forms.DateInput(attrs={
            'class': BASE_INPUT_CLASS,
            'type': 'date'
        })
    )

    def clean(self):
        cleaned = super().clean()
        installments = cleaned.get('installments') or 1
        cleaned['installments'] = max(1, installments)
        return cleaned

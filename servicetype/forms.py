# servicetype/forms.py

from decimal import Decimal, InvalidOperation

from django import forms
from .models import (
    CostItem,
    ServiceCost,
    ServiceType,
    COST_TYPE_CHOICES,
    COST_BEHAVIOR_CHOICES,
    EXPENSE_GROUP_CHOICES,
    BILLING_UNIT_CHOICES,
)


class ServiceTypeForm(forms.ModelForm):
    default_quantity = forms.CharField(
        required=False,
        label='Quantidade Padrão',
        widget=forms.TextInput(attrs={
            'class': 'w-full pl-12 pr-4 py-4 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-green-500 focus:ring-4 focus:ring-green-100 transition-all duration-300 text-gray-800',
            'placeholder': 'Ex: 1,0',
            'inputmode': 'decimal',
        }),
    )

    class Meta:
        model = ServiceType
        fields = [
            'name',
            'description',
            'ferramentas',
            'duracao_estimada',
            'billing_unit',
            'default_quantity',
            'unit_price',
            'estimated_price',
            'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50'}),
            'description': forms.Textarea(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50', 'rows': '3'}),
            'ferramentas': forms.Textarea(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50', 'rows': '3'}),
            'duracao_estimada': forms.NumberInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50', 'placeholder': 'Minutos'}),
            'billing_unit': forms.Select(attrs={
                'class': 'w-full pl-12 pr-4 py-4 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-green-500 focus:ring-4 focus:ring-green-100 transition-all duration-300 text-gray-800',
            }),
            'unit_price': forms.NumberInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50', 'placeholder': 'R$ 0,00', 'step': '0.01', 'min': '0'}),
            'estimated_price': forms.NumberInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50', 'placeholder': 'R$ 0,00', 'step': '0.01', 'min': '0'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded border-gray-300 text-primary shadow-sm focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50'}),
        }


    def clean_duracao_estimada(self):
        value = self.cleaned_data.get('duracao_estimada')
        return 0 if value in (None, '') else value

    def clean_unit_price(self):
        value = self.cleaned_data.get('unit_price')
        return 0 if value in (None, '') else value

    def clean_estimated_price(self):
        value = self.cleaned_data.get('estimated_price')
        return 0 if value in (None, '') else value

    def clean_default_quantity(self):
        raw_value = self.data.get(self.add_prefix('default_quantity'))
        if raw_value in (None, ''):
            if self.instance and self.instance.pk:
                return self.instance.default_quantity
            return Decimal('1.00')

        if isinstance(raw_value, str):
            normalized = raw_value.strip()
            if ',' in normalized:
                normalized = normalized.replace('.', '').replace(',', '.')
            try:
                return Decimal(normalized)
            except InvalidOperation:
                raise forms.ValidationError('Informe um número válido para a quantidade.')

        return raw_value


BASE_INPUT_CLASS = (
    'w-full px-4 py-3 border border-gray-300 rounded-lg '
    'focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent'
)


class CostItemForm(forms.ModelForm):
    """
    Formulário para criar/editar itens de custo no catálogo.
    """

    class Meta:
        model = CostItem
        fields = [
            'name',
            'description',
            'cost_type',
            'billing_unit',
            'unit_cost',
            'expense_group',
            'cost_behavior',
            'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': BASE_INPUT_CLASS,
                'placeholder': 'Ex: Mão de obra especializada'
            }),
            'description': forms.Textarea(attrs={
                'class': BASE_INPUT_CLASS,
                'rows': 3,
                'placeholder': 'Descrição detalhada do item de custo'
            }),
            'cost_type': forms.Select(attrs={
                'class': BASE_INPUT_CLASS,
            }),
            'billing_unit': forms.Select(attrs={
                'class': BASE_INPUT_CLASS,
            }),
            'unit_cost': forms.NumberInput(attrs={
                'class': BASE_INPUT_CLASS,
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }),
            'expense_group': forms.Select(attrs={
                'class': BASE_INPUT_CLASS,
            }),
            'cost_behavior': forms.Select(attrs={
                'class': BASE_INPUT_CLASS,
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-primary border-gray-300 rounded focus:ring-primary'
            }),
        }
        labels = {
            'name': 'Nome do Item de Custo',
            'description': 'Descrição',
            'cost_type': 'Tipo de Custo',
            'billing_unit': 'Unidade de Cobrança',
            'unit_cost': 'Custo Unitário (R$)',
            'expense_group': 'Grupo de Despesa',
            'cost_behavior': 'Comportamento do Custo',
            'is_active': 'Ativo',
        }


class ServiceCostForm(forms.ModelForm):
    """
    Formulário para associar itens de custo a um serviço.
    """

    class Meta:
        model = ServiceCost
        fields = [
            'service_type',
            'cost_item',
            'quantity',
            'unit_cost_snapshot',
            'is_required',
            'notes',
        ]
        widgets = {
            'service_type': forms.Select(attrs={
                'class': BASE_INPUT_CLASS,
            }),
            'cost_item': forms.Select(attrs={
                'class': BASE_INPUT_CLASS,
            }),
            'quantity': forms.NumberInput(attrs={
                'class': BASE_INPUT_CLASS,
                'placeholder': '1.00',
                'step': '0.01',
                'min': '0.01'
            }),
            'unit_cost_snapshot': forms.NumberInput(attrs={
                'class': BASE_INPUT_CLASS,
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0',
                'readonly': True,
            }),
            'is_required': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-primary border-gray-300 rounded focus:ring-primary'
            }),
            'notes': forms.Textarea(attrs={
                'class': BASE_INPUT_CLASS,
                'rows': 3,
                'placeholder': 'Observações opcionais'
            }),
        }
        labels = {
            'service_type': 'Tipo de Serviço',
            'cost_item': 'Item de Custo',
            'quantity': 'Quantidade',
            'unit_cost_snapshot': 'Custo Unitário Congelado (R$)',
            'is_required': 'Custo Obrigatório?',
            'notes': 'Observações',
        }

    def __init__(self, *args, **kwargs):
        service_type_id = kwargs.pop('service_type_id', None)
        super().__init__(*args, **kwargs)

        # Filtrar apenas itens de custo ativos
        self.fields['cost_item'].queryset = CostItem.objects.filter(is_active=True).order_by('name')

        # Se for uma edição, preencher unit_cost_snapshot automaticamente
        if self.instance and self.instance.pk:
            if not self.instance.unit_cost_snapshot and self.instance.cost_item:
                self.fields['unit_cost_snapshot'].initial = self.instance.cost_item.unit_cost

        # Se service_type_id foi passado, pré-selecionar o serviço
        if service_type_id:
            self.fields['service_type'].initial = service_type_id
            # Tornar o campo service_type readonly se já foi selecionado
            self.fields['service_type'].widget.attrs['disabled'] = True

        # Tornar unit_cost_snapshot somente leitura
        self.fields['unit_cost_snapshot'].widget.attrs['readonly'] = True

    def clean_unit_cost_snapshot(self):
        """
        Garantir que unit_cost_snapshot seja preenchido com o valor atual do cost_item.
        """
        cost_item = self.cleaned_data.get('cost_item')
        unit_cost_snapshot = self.cleaned_data.get('unit_cost_snapshot')

        # Se está criando um novo ServiceCost, pegar o custo atual do CostItem
        if not self.instance.pk and cost_item:
            return cost_item.unit_cost

        # Se está editando, manter o valor congelado
        return unit_cost_snapshot


class ServiceCostFilterForm(forms.Form):
    """
    Formulário para filtrar custos de serviços.
    """
    service_type = forms.ModelChoiceField(
        queryset=ServiceType.objects.filter(is_active=True).order_by('name'),
        required=False,
        empty_label='Todos os serviços',
        label='Tipo de Serviço',
        widget=forms.Select(attrs={'class': BASE_INPUT_CLASS})
    )
    cost_item = forms.ModelChoiceField(
        queryset=CostItem.objects.filter(is_active=True).order_by('name'),
        required=False,
        empty_label='Todos os itens de custo',
        label='Item de Custo',
        widget=forms.Select(attrs={'class': BASE_INPUT_CLASS})
    )
    cost_type = forms.ChoiceField(
        choices=[('', 'Todos os tipos')] + list(COST_TYPE_CHOICES),
        required=False,
        label='Tipo de Custo',
        widget=forms.Select(attrs={'class': BASE_INPUT_CLASS})
    )
    is_required = forms.ChoiceField(
        choices=[('', 'Todos'), ('true', 'Apenas Obrigatórios'), ('false', 'Apenas Opcionais')],
        required=False,
        label='Obrigatoriedade',
        widget=forms.Select(attrs={'class': BASE_INPUT_CLASS})
    )

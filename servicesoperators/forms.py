# servicesoperators/forms.py

from django import forms
from .models import ServiceOperator


class ServiceOperatorForm(forms.ModelForm):
    class Meta:
        model = ServiceOperator
        fields = [
            'name', 'trade_name', 'cnpj', 'responsible_name', 'responsible_role',
            'email', 'phone', 'website', 'street', 'number', 'complement',
            'district', 'city', 'state', 'zip_code', 'is_active', 'notes'
        ]

        # Classe CSS melhorada para inputs com melhor visibilidade
        input_class = 'w-full px-4 py-3 pl-11 text-gray-900 bg-white border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary transition-all duration-200 placeholder-gray-400'

        widgets = {
            'name': forms.TextInput(attrs={
                'class': input_class,
                'placeholder': 'Ex: Esfera Gestão de Serviços LTDA'
            }),
            'trade_name': forms.TextInput(attrs={
                'class': input_class,
                'placeholder': 'Ex: Esfera Gestão'
            }),
            'cnpj': forms.TextInput(attrs={
                'class': input_class,
                'placeholder': '00.000.000/0000-00'
            }),
            'responsible_name': forms.TextInput(attrs={
                'class': input_class,
                'placeholder': 'Nome completo do responsável'
            }),
            'responsible_role': forms.TextInput(attrs={
                'class': input_class,
                'placeholder': 'Ex: Diretor Geral'
            }),
            'email': forms.EmailInput(attrs={
                'class': input_class,
                'placeholder': 'contato@gerenciadora.com.br'
            }),
            'phone': forms.TextInput(attrs={
                'class': input_class,
                'placeholder': '(21) 99999-9999'
            }),
            'website': forms.URLInput(attrs={
                'class': input_class,
                'placeholder': 'https://www.gerenciadora.com.br'
            }),
            'street': forms.TextInput(attrs={
                'class': input_class,
                'placeholder': 'Rua, Avenida, etc.'
            }),
            'number': forms.TextInput(attrs={
                'class': input_class,
                'placeholder': '123'
            }),
            'complement': forms.TextInput(attrs={
                'class': input_class,
                'placeholder': 'Sala, Andar, etc.'
            }),
            'district': forms.TextInput(attrs={
                'class': input_class,
                'placeholder': 'Nome do bairro'
            }),
            'city': forms.TextInput(attrs={
                'class': input_class,
                'placeholder': 'Nome da cidade'
            }),
            'state': forms.TextInput(attrs={
                'class': input_class,
                'placeholder': 'RJ',
                'maxlength': '2'
            }),
            'zip_code': forms.TextInput(attrs={
                'class': input_class,
                'placeholder': '00000-000'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 rounded border-2 border-gray-300 text-primary focus:ring-2 focus:ring-primary cursor-pointer'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 text-gray-900 bg-white border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary transition-all duration-200 placeholder-gray-400',
                'rows': '4',
                'placeholder': 'Informações adicionais sobre a gerenciadora...'
            }),
        }
        labels = {
            'name': 'Razão Social',
            'trade_name': 'Nome Fantasia',
            'cnpj': 'CNPJ',
            'responsible_name': 'Nome do Responsável',
            'responsible_role': 'Cargo do Responsável',
            'email': 'E-mail Principal',
            'phone': 'Telefone Principal',
            'website': 'Website',
            'street': 'Logradouro',
            'number': 'Número',
            'complement': 'Complemento',
            'district': 'Bairro',
            'city': 'Cidade',
            'state': 'Estado',
            'zip_code': 'CEP',
            'is_active': 'Ativo',
            'notes': 'Observações',
        }

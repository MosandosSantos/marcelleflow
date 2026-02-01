# insurancecompany/forms.py

from django import forms
from .models import InsuranceCompany


class InsuranceCompanyForm(forms.ModelForm):
    class Meta:
        model = InsuranceCompany
        fields = ['name', 'trade_name', 'document', 'contact_name', 'contact_email', 'contact_phone', 'is_active']

        # Classe CSS melhorada para inputs com melhor visibilidade
        input_class = 'w-full px-4 py-3 pl-11 text-gray-900 bg-white border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary transition-all duration-200 placeholder-gray-400'

        widgets = {
            'name': forms.TextInput(attrs={
                'class': input_class,
                'placeholder': 'Ex: Porto Seguro Companhia de Seguros Gerais'
            }),
            'trade_name': forms.TextInput(attrs={
                'class': input_class,
                'placeholder': 'Ex: Porto Seguro'
            }),
            'document': forms.TextInput(attrs={
                'class': input_class,
                'placeholder': '00.000.000/0000-00'
            }),
            'contact_email': forms.EmailInput(attrs={
                'class': input_class,
                'placeholder': 'contato@seguradora.com.br'
            }),
            'contact_name': forms.TextInput(attrs={
                'class': input_class,
                'placeholder': 'Ex: Ana Souza'
            }),
            'contact_phone': forms.TextInput(attrs={
                'class': input_class,
                'placeholder': '(21) 99999-9999'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 rounded border-2 border-gray-300 text-primary focus:ring-2 focus:ring-primary cursor-pointer'
            }),
        }
        labels = {
            'name': 'Raz?o Social',
            'trade_name': 'Nome Fantasia',
            'document': 'CNPJ',
            'contact_name': 'Nome do Contato',
            'contact_email': 'E-mail de Contato',
            'contact_phone': 'Telefone de Contato',
            'is_active': 'Ativo',
        }

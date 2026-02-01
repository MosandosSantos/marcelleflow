# clients/forms.py

from django import forms
from django.contrib.auth import get_user_model
from .models import Client
from .validators import is_valid_cpf, is_valid_cnpj, normalize_digits

User = get_user_model()


class ClientForm(forms.ModelForm):
    """
    Formulario para criacao e edicao de Clientes.
    Na criacao, cria automaticamente o User vinculado.
    """

    class Meta:
        model = Client
        fields = [
            'full_name', 'email', 'cpf', 'cnpj', 'phone', 'birth_date',
            'street', 'number', 'complement', 'neighborhood',
            'city', 'state', 'zip_code'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
                'placeholder': 'Nome completo do cliente'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
                'placeholder': 'email@exemplo.com'
            }),
            'cpf': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
                'placeholder': '000.000.000-00'
            }),
            'cnpj': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
                'placeholder': '00.000.000/0000-00'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
                'placeholder': '(00) 00000-0000'
            }),
            'birth_date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
                'type': 'date'
            }),
            'zip_code': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
                'placeholder': '00000-000'
            }),
            'street': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
                'placeholder': 'Nome da rua'
            }),
            'number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
                'placeholder': 'Numero'
            }),
            'complement': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
                'placeholder': 'Apto, Bloco, etc.'
            }),
            'neighborhood': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
                'placeholder': 'Bairro'
            }),
            'city': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
                'placeholder': 'Cidade'
            }),
            'state': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
                'placeholder': 'UF',
                'maxlength': '2'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.is_create = kwargs.pop('is_create', False)
        super().__init__(*args, **kwargs)
        self.fields['cpf'].required = False
        self.fields['cnpj'].required = False

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        if not cpf:
            return None
        cpf = normalize_digits(cpf)
        if not is_valid_cpf(cpf):
            raise forms.ValidationError('CPF inválido.')
        return cpf

    def clean_cnpj(self):
        cnpj = self.cleaned_data.get('cnpj')
        if not cnpj:
            return None
        cnpj = normalize_digits(cnpj)
        if not is_valid_cnpj(cnpj):
            raise forms.ValidationError('CNPJ inválido.')
        return cnpj

    def clean(self):
        cleaned_data = super().clean()
        cpf = cleaned_data.get('cpf')
        cnpj = cleaned_data.get('cnpj')
        if not cpf and not cnpj:
            raise forms.ValidationError('Informe CPF ou CNPJ.')
        if cpf and cnpj:
            raise forms.ValidationError('Informe apenas CPF ou apenas CNPJ.')
        return cleaned_data

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if self.is_create:
            # Verificar se email ja existe
            if User.objects.filter(email=email).exists():
                raise forms.ValidationError('Ja existe um usuario com este email.')
        else:
            # Na edicao, verificar se email pertence a outro usuario
            if self.instance and self.instance.user:
                if User.objects.filter(email=email).exclude(pk=self.instance.user.pk).exists():
                    raise forms.ValidationError('Ja existe um usuario com este email.')
        return email

# provider/forms.py

import json
from urllib.request import urlopen

from django import forms
from django.contrib.auth import get_user_model

try:
    import requests
except Exception:  # pragma: no cover - optional dependency for API fetch
    requests = None

from .models import Provider

User = get_user_model()

_BANK_CHOICES_CACHE = None


def _fetch_bank_choices():
    global _BANK_CHOICES_CACHE
    if _BANK_CHOICES_CACHE is not None:
        return _BANK_CHOICES_CACHE

    try:
        if requests is not None:
            response = requests.get('https://brasilapi.com.br/api/banks/v1', timeout=5)
            response.raise_for_status()
            banks = response.json()
        else:
            with urlopen('https://brasilapi.com.br/api/banks/v1', timeout=5) as response:
                banks = json.loads(response.read().decode('utf-8'))
    except Exception:
        _BANK_CHOICES_CACHE = []
        return _BANK_CHOICES_CACHE

    choices = []
    for bank in banks:
        name = (bank.get('name') or bank.get('fullName') or '').strip()
        if not name:
            continue
        raw_code = bank.get('code')
        code = str(raw_code).zfill(3) if raw_code is not None else ''
        label = f"{code} - {name}" if code.strip('0') else name
        choices.append((name, label))

    choices.sort(key=lambda item: item[1].lower())
    _BANK_CHOICES_CACHE = choices
    return _BANK_CHOICES_CACHE


class ProviderForm(forms.ModelForm):
    """
    Formulário para criação e edição de Prestadores.
    Na criação, cria automaticamente o User vinculado.
    """

    class Meta:
        model = Provider
        fields = [
            'full_name', 'email', 'cpf', 'phone', 'birth_date',
            'street', 'number', 'complement', 'neighborhood',
            'city', 'state', 'zip_code',
            'bank_name', 'bank_agency', 'bank_account', 'bank_pix_key',
            'service_types', 'notes'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
                'placeholder': 'Nome completo do prestador'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
                'placeholder': 'email@exemplo.com'
            }),
            'cpf': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
                'placeholder': '000.000.000-00'
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
                'placeholder': 'Número'
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
            'bank_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
                'placeholder': 'Nome do banco'
            }),
            'bank_agency': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
                'placeholder': 'Agência'
            }),
            'bank_account': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
                'placeholder': 'Conta com dígito'
            }),
            'bank_pix_key': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
                'placeholder': 'CPF, e-mail, telefone ou chave aleatória'
            }),
            'service_types': forms.CheckboxSelectMultiple(),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
                'rows': '4',
                'placeholder': 'Observações internas sobre o prestador'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.is_create = kwargs.pop('is_create', False)
        super().__init__(*args, **kwargs)

        choices = _fetch_bank_choices()
        if choices:
            choices = [('', 'Selecione o banco')] + choices
            current_name = None
            if self.instance and self.instance.pk:
                current_name = self.instance.bank_name
            if current_name and all(current_name != value for value, _ in choices):
                choices.insert(1, (current_name, current_name))

            self.fields['bank_name'] = forms.ChoiceField(
                choices=choices,
                label='Banco',
                required=True,
                widget=forms.Select(attrs={
                    'class': 'w-full pl-12 pr-4 py-4 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-orange-500 focus:ring-4 focus:ring-orange-100 transition-all duration-300 text-gray-800',
                }),
            )
            if current_name:
                self.fields['bank_name'].initial = current_name
        else:
            self.fields['bank_name'].widget = forms.TextInput(attrs={
                'class': 'w-full pl-12 pr-4 py-4 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-orange-500 focus:ring-4 focus:ring-orange-100 transition-all duration-300 text-gray-800',
                'placeholder': 'Nome do banco'
            })

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if self.is_create:
            if User.objects.filter(email=email).exists():
                raise forms.ValidationError('Já existe um usuário com este e-mail.')
        else:
            if self.instance and self.instance.user:
                if User.objects.filter(email=email).exclude(pk=self.instance.user.pk).exists():
                    raise forms.ValidationError('Já existe um usuário com este e-mail.')
        return email

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from clients.models import Client

User = get_user_model()


class ClientRegistrationForm(UserCreationForm):
    """
    Formulário de cadastro de cliente com dados completos.
    Cria User com role='customer' + perfil Client associado.
    """

    # Dados pessoais
    full_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Nome completo'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'seu@email.com'})
    )
    cpf = forms.CharField(
        max_length=14,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': '000.000.000-00'})
    )
    phone = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': '(00) 00000-0000'})
    )
    birth_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    # Endereço
    zip_code = forms.CharField(
        max_length=9,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': '00000-000'})
    )
    street = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Rua, Avenida...'})
    )
    number = forms.CharField(
        max_length=10,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Número'})
    )
    complement = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Apto, Bloco...'})
    )
    neighborhood = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Bairro'})
    )
    city = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Cidade'})
    )
    state = forms.CharField(
        max_length=2,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'UF'})
    )

    class Meta:
        model = User
        fields = ('email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'placeholder': 'Senha'})
        self.fields['password2'].widget.attrs.update({'placeholder': 'Confirmar senha'})

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Este e-mail já está cadastrado.')
        return email

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        if Client.objects.filter(cpf=cpf).exists():
            raise forms.ValidationError('Este CPF já está cadastrado.')
        return cpf

    def save(self, commit=True):
        # Cria o User com role='customer'
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.username = self.cleaned_data['email'].split('@')[0]
        user.role = User.ROLE_CUSTOMER

        if commit:
            user.save()

            # Cria o perfil Client
            Client.objects.create(
                user=user,
                full_name=self.cleaned_data['full_name'],
                email=self.cleaned_data['email'],
                cpf=self.cleaned_data['cpf'],
                phone=self.cleaned_data['phone'],
                birth_date=self.cleaned_data.get('birth_date'),
                street=self.cleaned_data['street'],
                number=self.cleaned_data['number'],
                complement=self.cleaned_data.get('complement', ''),
                neighborhood=self.cleaned_data['neighborhood'],
                city=self.cleaned_data['city'],
                state=self.cleaned_data['state'],
                zip_code=self.cleaned_data['zip_code'],
            )

        return user


class UserProfileForm(forms.ModelForm):
    """
    Formulário de edição de perfil do usuário.
    Permite editar informações básicas (não permite mudar email ou role).
    """
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
                'placeholder': 'Nome de usuário'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
                'placeholder': 'Nome'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
                'placeholder': 'Sobrenome'
            }),
        }
        labels = {
            'username': 'Nome de Usuário',
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
        }

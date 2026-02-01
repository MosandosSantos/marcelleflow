from django.contrib.auth import login, authenticate, logout, get_user_model
from django.contrib.auth.views import LogoutView
from django.shortcuts import render, redirect
from django.views.generic import CreateView, TemplateView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.views import View
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

from .forms import ClientRegistrationForm, UserProfileForm

User = get_user_model()


def custom_login_view(request):
    """
    View de login com senha.
    ATENÇÃO: Apenas para desenvolvimento!
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()

        if not email:
            messages.error(request, 'Por favor, informe seu e-mail.')
            return render(request, 'accounts/login.html')

        # Autentica com email e senha
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f'Bem-vindo, {user.first_name or user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'E-mail não encontrado. Verifique e tente novamente.')

    return render(request, 'accounts/login.html')


class CustomLogoutView(View):
    """
    View de logout que LIMPA COMPLETAMENTE a sessão e exibe página de agradecimento.
    """
    def get(self, request):
        # Fazer logout e LIMPAR completamente a sessão
        logout(request)
        request.session.flush()  # Remove TODOS os dados da sessão

        # Renderizar página de logout
        return render(request, 'accounts/logout.html')

    def post(self, request):
        # Suporta POST também (alguns sistemas usam POST para logout)
        logout(request)
        request.session.flush()
        return render(request, 'accounts/logout.html')


class ClientRegisterView(CreateView):
    """
    View de cadastro de cliente.
    Cria User + perfil Client automaticamente.
    """
    form_class = ClientRegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        # Salva e autentica automaticamente
        user = form.save()
        login(self.request, user)
        messages.success(self.request, f'Bem-vindo, {user.username}! Sua conta foi criada com sucesso.')
        return redirect(self.success_url)

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor, corrija os erros abaixo.')
        return super().form_invalid(form)


class UserProfileView(LoginRequiredMixin, UpdateView):
    """
    View de perfil do usuário com todas as configurações.
    Permite editar informações pessoais.
    """
    model = User
    form_class = UserProfileForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self, queryset=None):
        # Sempre retorna o usuário logado
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Perfil atualizado com sucesso!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor, corrija os erros abaixo.')
        return super().form_invalid(form)

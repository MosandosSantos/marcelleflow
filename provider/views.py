"""
Views CRUD para gerenciamento de Prestadores.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q, Count, Sum, Avg, DecimalField, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from django.contrib.auth import get_user_model

from .models import Provider
from .forms import ProviderForm
from accounts.mixins import IsAdminOrOperationalMixin

User = get_user_model()


class ProviderListView(LoginRequiredMixin, IsAdminOrOperationalMixin, ListView):
    model = Provider
    template_name = 'provider/list.html'
    context_object_name = 'providers'
    paginate_by = 10

    def get_queryset(self):
        cutoff = timezone.now() - timedelta(days=90)
        queryset = Provider.objects.select_related('user').prefetch_related('service_types').annotate(
            work_orders_count=Count('work_orders', distinct=True),
            revenue_90d=Coalesce(
                Sum('work_orders__labor_cost', filter=Q(work_orders__created_at__gte=cutoff)),
                Value(0),
                output_field=DecimalField()
            )
        ).order_by('full_name')

        # Busca por texto
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) |
                Q(email__icontains=search) |
                Q(cpf__icontains=search)
            )

        # Filtro por tipo de serviço
        service_type_id = self.request.GET.get('service_type')
        if service_type_id:
            queryset = queryset.filter(service_types__id=service_type_id)

        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Adicionar lista de tipos de serviço para o filtro
        from servicetype.models import ServiceType
        context['service_types_list'] = ServiceType.objects.filter(is_active=True).order_by('name')
        from workorderstatus.models import ServiceOrderStatus
        cutoff_open = timezone.now() - timedelta(days=180)
        open_statuses = ServiceOrderStatus.objects.filter(group_code__in=['OPEN', 'IN_PROGRESS'])
        context['providers_total'] = Provider.objects.count()
        context['providers_open_orders'] = Provider.objects.filter(work_orders__status__in=open_statuses).distinct().count()
        context['providers_without_orders_6m'] = Provider.objects.exclude(work_orders__created_at__gte=cutoff_open).distinct().count()
        for provider in context['providers']:
            avg = float(provider.rating_avg or 0)
            provider.rating_value = avg
            stars = []
            for i in range(1, 6):
                if avg >= i:
                    stars.append('full')
                elif avg >= i - 0.5:
                    stars.append('half')
                else:
                    stars.append('empty')
            provider.rating_stars = stars
        return context


class ProviderDetailView(LoginRequiredMixin, IsAdminOrOperationalMixin, DetailView):
    model = Provider
    template_name = 'provider/detail.html'
    context_object_name = 'provider'


class ProviderCreateView(LoginRequiredMixin, IsAdminOrOperationalMixin, CreateView):
    model = Provider
    form_class = ProviderForm
    template_name = 'provider/form.html'
    success_url = reverse_lazy('provider:list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['is_create'] = True
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        import secrets

        temp_password = secrets.token_urlsafe(12)
        base_username = (form.cleaned_data.get('email') or '').split('@')[0] or 'prestador'
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        user = User.objects.create_user(
            email=form.cleaned_data['email'],
            password=temp_password,
            first_name=form.cleaned_data['full_name'].split()[0] if form.cleaned_data['full_name'] else '',
            username=username,
            role='tech'
        )
        form.instance.user = user

        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Prestador "{self.object.full_name}" criado com sucesso! A senha deve ser definida no menu Usuários.'
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Novo Prestador'
        context['button_text'] = 'Cadastrar Prestador'
        context['is_create'] = True
        return context


class ProviderUpdateView(LoginRequiredMixin, IsAdminOrOperationalMixin, UpdateView):
    model = Provider
    form_class = ProviderForm
    template_name = 'provider/form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['is_create'] = False
        return kwargs

    def get_success_url(self):
        return reverse_lazy('provider:detail', kwargs={'pk': self.object.pk})

    @transaction.atomic
    def form_valid(self, form):
        if self.object.user:
            self.object.user.email = form.cleaned_data['email']
            self.object.user.save()

        response = super().form_valid(form)
        messages.success(self.request, f'Prestador "{self.object.full_name}" atualizado com sucesso!')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Editar Prestador: {self.object.full_name}'
        context['button_text'] = 'Salvar Alterações'
        context['is_create'] = False
        return context


class ProviderDeleteView(LoginRequiredMixin, IsAdminOrOperationalMixin, DeleteView):
    model = Provider
    template_name = 'provider/confirm_delete.html'
    success_url = reverse_lazy('provider:list')

    def delete(self, request, *args, **kwargs):
        provider = self.get_object()
        messages.success(request, f'Prestador "{provider.full_name}" excluído com sucesso!')
        return super().delete(request, *args, **kwargs)


class ProviderHistoryView(LoginRequiredMixin, IsAdminOrOperationalMixin, DetailView):
    """Exibe histórico de ordens de serviço de um prestador."""
    model = Provider
    template_name = 'provider/history.html'
    context_object_name = 'provider'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Importar aqui para evitar circular import
        from workorder.models import WorkOrder

        # Buscar todas as ordens do prestador ordenadas por data
        work_orders = WorkOrder.objects.filter(
            provider=self.object
        ).select_related(
            'client', 'service_type', 'status', 'insurance_company', 'service_operator'
        ).prefetch_related(
            'history'
        ).order_by('-created_at')

        # Estatísticas
        from django.db.models import Count, Avg, Sum
        stats = {
            'total': work_orders.count(),
            'pendentes': work_orders.filter(status__name='Pendente').count(),
            'em_andamento': work_orders.filter(status__name='Em Andamento').count(),
            'concluidas': work_orders.filter(status__name__icontains='Conclu').count(),
            'valor_total': work_orders.aggregate(
                total=Sum('labor_cost')
            )['total'] or 0,
        }

        # Avaliações (se houver)
        try:
            from workorder.models import WorkOrderEvaluation
            avaliacoes = WorkOrderEvaluation.objects.filter(
                work_order__provider=self.object
            )
            if avaliacoes.exists():
                stats['media_avaliacoes'] = avaliacoes.aggregate(
                    media=Avg('rating')
                )['media']
            else:
                stats['media_avaliacoes'] = None
        except:
            stats['media_avaliacoes'] = None

        context['work_orders'] = work_orders
        context['stats'] = stats
        return context

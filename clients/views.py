"""
Views CRUD para gerenciamento de Clientes.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q, Count, Max, Sum, DecimalField, ExpressionWrapper, F, Value, Case, When
from django.db.models.functions import Coalesce
from django.db import transaction
from django.template import TemplateDoesNotExist, Engine, RequestContext
from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from pathlib import Path
from django.utils import timezone
from django.db.models.functions import TruncMonth
from datetime import timedelta

from .models import Client
from .forms import ClientForm
from accounts.mixins import IsAdminOrOperationalMixin, IsFinancialReadOnlyClientsMixin

User = get_user_model()

def _render_clients_form_fallback(request, context, **response_kwargs):
    template_path = Path(settings.BASE_DIR) / 'templates' / 'clients' / 'form.html'
    template_string = template_path.read_text(encoding='utf-8')
    engine = Engine(
        dirs=[
            str(Path(settings.BASE_DIR) / 'templates'),
            str(Path(settings.BASE_DIR) / 'clients' / 'templates'),
        ],
        app_dirs=True,
        context_processors=[
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
            'django.template.context_processors.media',
            'django.template.context_processors.static',
            'django.template.context_processors.tz',
            'django.template.context_processors.csrf',
        ],
    )
    template = engine.from_string(template_string)
    context.setdefault('user', request.user)
    request_context = RequestContext(request, context)
    return HttpResponse(template.render(request_context), **response_kwargs)


def _render_clients_form_with_engine(request, context, **response_kwargs):
    engine = Engine(dirs=[
        str(Path(settings.BASE_DIR) / 'templates'),
        str(Path(settings.BASE_DIR) / 'clients' / 'templates'),
    ], app_dirs=True)
    template = engine.get_template('clients/form.html')
    request_context = RequestContext(request, context)
    return HttpResponse(template.render(request_context), **response_kwargs)


class ClientListView(LoginRequiredMixin, IsFinancialReadOnlyClientsMixin, ListView):
    """Lista todos os clientes com busca."""
    model = Client
    template_name = 'clients/list.html'
    context_object_name = 'clients'
    paginate_by = 10

    def get_queryset(self):
        queryset = Client.objects.select_related('user').order_by('full_name')

        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) |
                Q(email__icontains=search) |
                Q(cpf__icontains=search) |
                Q(cnpj__icontains=search) |
                Q(phone__icontains=search)
            )

        current_year = timezone.now().year

        queryset = queryset.annotate(
            total_orders=Count('work_orders', distinct=True),
            open_orders=Count(
                'work_orders',
                filter=~Q(work_orders__status__group_code='CLOSED'),
                distinct=True
            ),
            orders_year=Count(
                'work_orders',
                filter=Q(work_orders__created_at__year=current_year),
                distinct=True
            ),
            last_order=Max('work_orders__created_at'),
            total_value=Coalesce(
                Sum('work_orders__labor_cost'),
                Value(0),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            ),
        ).annotate(
            ticket_medio=Case(
                When(total_orders=0, then=Value(0)),
                default=ExpressionWrapper(
                    F('total_value') / F('total_orders'),
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                ),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cutoff_date = timezone.now() - timedelta(days=180)
        current_date = timezone.localdate()
        current_month_start = current_date.replace(day=1)

        def shift_month(base_date, months):
            year = base_date.year + ((base_date.month - 1 + months) // 12)
            month = ((base_date.month - 1 + months) % 12) + 1
            return base_date.replace(year=year, month=month, day=1)

        context['clients_total'] = Client.objects.count()
        context['clients_with_open_orders'] = Client.objects.filter(
            ~Q(work_orders__status__group_code='CLOSED')
        ).distinct().count()
        context['clients_without_orders_6m'] = Client.objects.annotate(
            last_order=Max('work_orders__created_at')
        ).filter(
            Q(last_order__lt=cutoff_date) | Q(last_order__isnull=True)
        ).count()

        from workorder.models import WorkOrder

        top_count = (
            WorkOrder.objects
            .filter(client__isnull=False)
            .values('client_id', 'client__full_name')
            .annotate(total=Count('id'))
            .order_by('-total')[:10]
        )
        context['chart_top_count_labels'] = [item['client__full_name'] for item in top_count]
        context['chart_top_count_values'] = [item['total'] for item in top_count]

        top_revenue = (
            WorkOrder.objects
            .filter(client__isnull=False)
            .values('client_id', 'client__full_name')
            .annotate(revenue=Coalesce(
                Sum('labor_cost'),
                Value(0),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            ))
            .order_by('-revenue')[:10]
        )
        context['chart_top_revenue_labels'] = [item['client__full_name'] for item in top_revenue]
        context['chart_top_revenue_values'] = [float(item['revenue']) for item in top_revenue]

        start_month = shift_month(current_month_start, -9)
        months = []
        cursor = start_month
        for _ in range(10):
            months.append(cursor)
            cursor = shift_month(cursor, 1)

        month_counts = {
            item['month'].date(): item['total']
            for item in Client.objects.filter(created_at__date__gte=start_month).annotate(
                month=TruncMonth('created_at')
            ).values('month').annotate(total=Count('id'))
        }

        month_names = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
        context['chart_new_clients_labels'] = [
            f"{month_names[item.month - 1]}/{str(item.year)[-2:]}" for item in months
        ]
        context['chart_new_clients_values'] = [month_counts.get(item, 0) for item in months]

        return context


class ClientDetailView(LoginRequiredMixin, IsFinancialReadOnlyClientsMixin, DetailView):
    """Exibe detalhes de um cliente."""
    model = Client
    template_name = 'clients/detail.html'
    context_object_name = 'client'


class ClientCreateView(LoginRequiredMixin, IsAdminOrOperationalMixin, CreateView):
    """Cria novo cliente com User automatico."""
    model = Client
    form_class = ClientForm
    template_name = 'clients/form.html'
    success_url = reverse_lazy('clients:list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['is_create'] = True
        return kwargs

    def get(self, request, *args, **kwargs):
        self.object = None
        context = self.get_context_data()
        return _render_clients_form_fallback(request, context)

    @transaction.atomic
    def form_valid(self, form):
        import secrets

        # Criar o User com senha temporaria (sera definida via menu usuarios)
        temp_password = secrets.token_urlsafe(12)
        user = User.objects.create_user(
            email=form.cleaned_data['email'],
            password=temp_password,
            first_name=form.cleaned_data['full_name'].split()[0] if form.cleaned_data['full_name'] else '',
            role='customer'
        )

        # Vincular o User ao Client
        form.instance.user = user

        response = super().form_valid(form)
        messages.success(self.request, f'Cliente "{self.object.full_name}" criado com sucesso! A senha deve ser definida no menu Usuarios.')
        return response

    def render_to_response(self, context, **response_kwargs):
        return _render_clients_form_fallback(self.request, context, **response_kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Novo Cliente'
        context['button_text'] = 'Cadastrar Cliente'
        context['is_create'] = True
        return context


class ClientUpdateView(LoginRequiredMixin, IsAdminOrOperationalMixin, UpdateView):
    """Atualiza cliente existente."""
    model = Client
    form_class = ClientForm
    template_name = 'clients/form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['is_create'] = False
        return kwargs

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data()
        return _render_clients_form_fallback(request, context)

    def get_success_url(self):
        return reverse_lazy('clients:detail', kwargs={'pk': self.object.pk})

    @transaction.atomic
    def form_valid(self, form):
        # Atualizar email do User se mudou
        if self.object.user:
            self.object.user.email = form.cleaned_data['email']
            self.object.user.save()

        response = super().form_valid(form)
        messages.success(self.request, f'Cliente "{self.object.full_name}" atualizado com sucesso!')
        return response

    def render_to_response(self, context, **response_kwargs):
        return _render_clients_form_fallback(self.request, context, **response_kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Editar Cliente: {self.object.full_name}'
        context['button_text'] = 'Salvar Alteracoes'
        context['is_create'] = False
        return context


class ClientDeleteView(LoginRequiredMixin, IsAdminOrOperationalMixin, DeleteView):
    """Deleta cliente e seu User vinculado."""
    model = Client
    template_name = 'clients/confirm_delete.html'
    success_url = reverse_lazy('clients:list')

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        client = self.get_object()
        user = client.user

        messages.success(request, f'Cliente "{client.full_name}" excluido com sucesso!')

        # Deletar o Client primeiro (por causa do CASCADE)
        response = super().delete(request, *args, **kwargs)

        # Deletar o User associado
        if user:
            user.delete()

        return response


class ClientHistoryView(LoginRequiredMixin, IsAdminOrOperationalMixin, DetailView):
    """Exibe historico de ordens de servico de um cliente."""
    model = Client
    template_name = 'clients/history.html'
    context_object_name = 'client'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Importar aqui para evitar circular import
        from workorder.models import WorkOrder

        # Buscar todas as ordens do cliente ordenadas por data
        work_orders = WorkOrder.objects.filter(
            client=self.object
        ).select_related(
            'provider', 'service_type', 'status', 'insurance_company', 'service_operator'
        ).prefetch_related(
            'history'
        ).order_by('-created_at')

        # Estatisticas
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

        # Avaliacoes (se houver)
        try:
            from workorder.models import WorkOrderEvaluation
            avaliacoes = WorkOrderEvaluation.objects.filter(
                work_order__client=self.object
            )
            if avaliacoes.exists():
                stats['media_avaliacoes'] = avaliacoes.aggregate(
                    media=Avg('rating')
                )['media']
        except:
            stats['media_avaliacoes'] = None

        context['work_orders'] = work_orders
        context['stats'] = stats
        return context

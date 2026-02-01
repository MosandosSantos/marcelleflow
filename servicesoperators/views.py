"""
Views CRUD para gerenciamento de Gerenciadoras.
"""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import date

from .models import ServiceOperator
from .forms import ServiceOperatorForm
from workorder.models import WorkOrder


class IsAdminOrManagerMixin(UserPassesTestMixin):
    """Mixin para verificar se usuário é admin ou manager."""
    def test_func(self):
        user = self.request.user
        return user.is_superuser or user.is_staff or user.role in ['admin', 'manager']


class ServiceOperatorListView(LoginRequiredMixin, IsAdminOrManagerMixin, ListView):
    """Lista todas as gerenciadoras com busca e filtros."""
    model = ServiceOperator
    template_name = 'servicesoperators/list.html'
    context_object_name = 'service_operators'
    paginate_by = 10

    def get_queryset(self):
        queryset = ServiceOperator.objects.annotate(
            work_orders_count=Count('work_orders')
        ).order_by('name')

        # Busca
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(trade_name__icontains=search) |
                Q(cnpj__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search) |
                Q(responsible_name__icontains=search) |
                Q(city__icontains=search) |
                Q(state__icontains=search)
            )

        # Filtro por status
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)

        # Filtro por estado
        state = self.request.GET.get('state')
        if state:
            queryset = queryset.filter(state=state)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Estatisticas gerais
        total_operators = ServiceOperator.objects.count()
        total_active = ServiceOperator.objects.filter(is_active=True).count()

        # Grafico: OS por gerenciadora mes a mes (12 meses a partir de janeiro)
        today = timezone.now().date()
        months = [date(today.year, month, 1) for month in range(1, 13)]

        pt_months = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
        month_labels = [f"{pt_months[m.month-1]}/{str(m.year)[2:]}" for m in months]
        month_keys = {m: idx for idx, m in enumerate(months)}

        counts = WorkOrder.objects.filter(
            service_operator__isnull=False
        ).annotate(
            month=TruncMonth('created_at')
        ).values(
            'service_operator_id', 'month'
        ).annotate(
            count=Count('id')
        )

        data_map = {}
        for row in counts:
            op_id = row['service_operator_id']
            month_key = row['month'].date().replace(day=1)
            if op_id not in data_map:
                data_map[op_id] = [0] * len(months)
            idx = month_keys.get(month_key)
            if idx is not None:
                data_map[op_id][idx] = row['count']

        colors = [
            '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
            '#06B6D4', '#84CC16', '#F97316', '#EC4899', '#6366F1'
        ]
        datasets = []
        for i, op in enumerate(ServiceOperator.objects.order_by('name')):
            datasets.append({
                'label': op.name,
                'data': data_map.get(op.id, [0] * len(months)),
                'backgroundColor': colors[i % len(colors)],
            })

        import json
        context['chart_labels_json'] = json.dumps(month_labels)
        context['chart_datasets_json'] = json.dumps(datasets)
        context['total_operators'] = total_operators
        context['total_active'] = total_active

        # Lista de estados para filtro
        context['states'] = ServiceOperator.objects.values_list('state', flat=True).distinct().order_by('state')
        return context


class ServiceOperatorDetailView(LoginRequiredMixin, IsAdminOrManagerMixin, DetailView):
    """Exibe detalhes de uma gerenciadora."""
    model = ServiceOperator
    template_name = 'servicesoperators/detail.html'
    context_object_name = 'service_operator'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class ServiceOperatorCreateView(LoginRequiredMixin, IsAdminOrManagerMixin, CreateView):
    """Cria nova gerenciadora."""
    model = ServiceOperator
    form_class = ServiceOperatorForm
    template_name = 'servicesoperators/form.html'
    success_url = reverse_lazy('servicesoperators:list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Gerenciadora "{self.object.name}" criada com sucesso!')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class ServiceOperatorUpdateView(LoginRequiredMixin, IsAdminOrManagerMixin, UpdateView):
    """Atualiza gerenciadora existente."""
    model = ServiceOperator
    form_class = ServiceOperatorForm
    template_name = 'servicesoperators/form.html'

    def get_success_url(self):
        return reverse_lazy('servicesoperators:list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Operadora "{self.object.name}" atualizada com sucesso!')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class ServiceOperatorDeleteView(LoginRequiredMixin, IsAdminOrManagerMixin, DeleteView):
    """Deleta gerenciadora."""
    model = ServiceOperator
    template_name = 'servicesoperators/confirm_delete.html'
    success_url = reverse_lazy('servicesoperators:list')

    def delete(self, request, *args, **kwargs):
        operator = self.get_object()
        messages.success(request, f'Gerenciadora "{operator.name}" excluída com sucesso!')
        return super().delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

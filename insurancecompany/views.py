"""
Views CRUD para gerenciamento de Seguradoras.
"""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q, Count, Sum, Avg
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import date

from .models import InsuranceCompany
from .forms import InsuranceCompanyForm
from workorder.models import WorkOrder


class IsAdminOrManagerMixin(UserPassesTestMixin):
    """Mixin para verificar se usuário é admin ou manager."""
    def test_func(self):
        user = self.request.user
        return user.is_superuser or user.is_staff or user.role in ['admin', 'manager']


class InsuranceCompanyListView(LoginRequiredMixin, IsAdminOrManagerMixin, ListView):
    """Lista todas as seguradoras com busca e filtros."""
    model = InsuranceCompany
    template_name = 'insurancecompany/list.html'
    context_object_name = 'insurance_companies'
    paginate_by = 10

    def get_queryset(self):
        queryset = InsuranceCompany.objects.annotate(
            work_orders_count=Count('work_orders')
        ).order_by('name')

        # Busca
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(trade_name__icontains=search) |
                Q(document__icontains=search) |
                Q(contact_name__icontains=search) |
                Q(contact_email__icontains=search) |
                Q(contact_phone__icontains=search)
            )

        # Filtro por status
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Estatísticas gerais
        total_companies = InsuranceCompany.objects.count()
        total_active = InsuranceCompany.objects.filter(is_active=True).count()

        # Gráfico: OS por seguradora mês a mês (12 meses a partir de janeiro)
        today = timezone.now().date()
        months = [date(today.year, month, 1) for month in range(1, 13)]

        pt_months = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
        month_labels = [f"{pt_months[m.month-1]}/{str(m.year)[2:]}" for m in months]
        month_keys = {m: idx for idx, m in enumerate(months)}

        counts = WorkOrder.objects.filter(
            insurance_company__isnull=False
        ).annotate(
            month=TruncMonth('created_at')
        ).values(
            'insurance_company_id', 'month'
        ).annotate(
            count=Count('id')
        )

        data_map = {}
        for row in counts:
            comp_id = row['insurance_company_id']
            month_key = row['month'].date().replace(day=1)
            if comp_id not in data_map:
                data_map[comp_id] = [0] * len(months)
            idx = month_keys.get(month_key)
            if idx is not None:
                data_map[comp_id][idx] = row['count']

        colors = [
            '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
            '#06B6D4', '#84CC16', '#F97316', '#EC4899', '#6366F1'
        ]
        datasets = []
        for i, comp in enumerate(InsuranceCompany.objects.order_by('name')):
            datasets.append({
                'label': comp.name,
                'data': data_map.get(comp.id, [0] * len(months)),
                'backgroundColor': colors[i % len(colors)],
            })

        import json
        context['chart_labels_json'] = json.dumps(month_labels)
        context['chart_datasets_json'] = json.dumps(datasets)
        context['total_companies'] = total_companies
        context['total_active'] = total_active
        return context


class InsuranceCompanyDetailView(LoginRequiredMixin, IsAdminOrManagerMixin, DetailView):
    """Exibe detalhes de uma seguradora."""
    model = InsuranceCompany
    template_name = 'insurancecompany/detail.html'
    context_object_name = 'insurance_company'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Estatisticas gerais
        total_companies = InsuranceCompany.objects.count()
        total_active = InsuranceCompany.objects.filter(is_active=True).count()

        # Grafico: OS por seguradora mes a mes (12 meses a partir de janeiro)
        today = timezone.now().date()
        months = [date(today.year, month, 1) for month in range(1, 13)]

        pt_months = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
        month_labels = [f"{pt_months[m.month-1]}/{str(m.year)[2:]}" for m in months]
        month_keys = {m: idx for idx, m in enumerate(months)}

        counts = WorkOrder.objects.filter(
            insurance_company__isnull=False
        ).annotate(
            month=TruncMonth('created_at')
        ).values(
            'insurance_company_id', 'month'
        ).annotate(
            count=Count('id')
        )

        data_map = {}
        for row in counts:
            comp_id = row['insurance_company_id']
            month_key = row['month'].date().replace(day=1)
            if comp_id not in data_map:
                data_map[comp_id] = [0] * len(months)
            idx = month_keys.get(month_key)
            if idx is not None:
                data_map[comp_id][idx] = row['count']

        colors = [
            '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
            '#06B6D4', '#84CC16', '#F97316', '#EC4899', '#6366F1'
        ]
        datasets = []
        for i, comp in enumerate(InsuranceCompany.objects.order_by('name')):
            datasets.append({
                'label': comp.name,
                'data': data_map.get(comp.id, [0] * len(months)),
                'backgroundColor': colors[i % len(colors)],
            })

        import json
        context['chart_labels_json'] = json.dumps(month_labels)
        context['chart_datasets_json'] = json.dumps(datasets)
        context['total_companies'] = total_companies
        context['total_active'] = total_active


        # Estatísticas de ordens de serviço
        work_orders = self.object.work_orders.all()
        context['work_orders_count'] = work_orders.count()

        # Estatísticas detalhadas
        if work_orders.exists():
            from django.db.models import Q
            context['stats'] = {
                'total': work_orders.count(),
                'pendentes': work_orders.filter(status__status_name='Pendente').count(),
                'em_andamento': work_orders.filter(status__status_name='Em Andamento').count(),
                'concluidas': work_orders.filter(status__status_name__icontains='Conclu').count(),
                'valor_total': work_orders.aggregate(total=Sum('labor_cost'))['total'] or 0,
            }

        # Últimas ordens de serviço
        context['recent_work_orders'] = self.object.work_orders.select_related(
            'client', 'provider', 'service_type', 'status'
        ).order_by('-created_at')[:10]

        return context


class InsuranceCompanyCreateView(LoginRequiredMixin, IsAdminOrManagerMixin, CreateView):
    """Cria nova seguradora."""
    model = InsuranceCompany
    form_class = InsuranceCompanyForm
    template_name = 'insurancecompany/form.html'
    success_url = reverse_lazy('insurancecompany:list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Seguradora "{self.object.name}" criada com sucesso!')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Estatisticas gerais
        total_companies = InsuranceCompany.objects.count()
        total_active = InsuranceCompany.objects.filter(is_active=True).count()

        # Grafico: OS por seguradora mes a mes (12 meses a partir de janeiro)
        today = timezone.now().date()
        months = [date(today.year, month, 1) for month in range(1, 13)]

        pt_months = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
        month_labels = [f"{pt_months[m.month-1]}/{str(m.year)[2:]}" for m in months]
        month_keys = {m: idx for idx, m in enumerate(months)}

        counts = WorkOrder.objects.filter(
            insurance_company__isnull=False
        ).annotate(
            month=TruncMonth('created_at')
        ).values(
            'insurance_company_id', 'month'
        ).annotate(
            count=Count('id')
        )

        data_map = {}
        for row in counts:
            comp_id = row['insurance_company_id']
            month_key = row['month'].date().replace(day=1)
            if comp_id not in data_map:
                data_map[comp_id] = [0] * len(months)
            idx = month_keys.get(month_key)
            if idx is not None:
                data_map[comp_id][idx] = row['count']

        colors = [
            '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
            '#06B6D4', '#84CC16', '#F97316', '#EC4899', '#6366F1'
        ]
        datasets = []
        for i, comp in enumerate(InsuranceCompany.objects.order_by('name')):
            datasets.append({
                'label': comp.name,
                'data': data_map.get(comp.id, [0] * len(months)),
                'backgroundColor': colors[i % len(colors)],
            })

        import json
        context['chart_labels_json'] = json.dumps(month_labels)
        context['chart_datasets_json'] = json.dumps(datasets)
        context['total_companies'] = total_companies
        context['total_active'] = total_active

        context['title'] = 'Nova Seguradora'
        context['button_text'] = 'Cadastrar Seguradora'
        return context


class InsuranceCompanyUpdateView(LoginRequiredMixin, IsAdminOrManagerMixin, UpdateView):
    """Atualiza seguradora existente."""
    model = InsuranceCompany
    form_class = InsuranceCompanyForm
    template_name = 'insurancecompany/form.html'
    success_url = reverse_lazy('insurancecompany:list')

    def get_success_url(self):
        return reverse_lazy('insurancecompany:detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Seguradora "{self.object.name}" atualizada com sucesso!')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Estatisticas gerais
        total_companies = InsuranceCompany.objects.count()
        total_active = InsuranceCompany.objects.filter(is_active=True).count()

        # Grafico: OS por seguradora mes a mes (12 meses a partir de janeiro)
        today = timezone.now().date()
        months = [date(today.year, month, 1) for month in range(1, 13)]

        pt_months = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
        month_labels = [f"{pt_months[m.month-1]}/{str(m.year)[2:]}" for m in months]
        month_keys = {m: idx for idx, m in enumerate(months)}

        counts = WorkOrder.objects.filter(
            insurance_company__isnull=False
        ).annotate(
            month=TruncMonth('created_at')
        ).values(
            'insurance_company_id', 'month'
        ).annotate(
            count=Count('id')
        )

        data_map = {}
        for row in counts:
            comp_id = row['insurance_company_id']
            month_key = row['month'].date().replace(day=1)
            if comp_id not in data_map:
                data_map[comp_id] = [0] * len(months)
            idx = month_keys.get(month_key)
            if idx is not None:
                data_map[comp_id][idx] = row['count']

        colors = [
            '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
            '#06B6D4', '#84CC16', '#F97316', '#EC4899', '#6366F1'
        ]
        datasets = []
        for i, comp in enumerate(InsuranceCompany.objects.order_by('name')):
            datasets.append({
                'label': comp.name,
                'data': data_map.get(comp.id, [0] * len(months)),
                'backgroundColor': colors[i % len(colors)],
            })

        import json
        context['chart_labels_json'] = json.dumps(month_labels)
        context['chart_datasets_json'] = json.dumps(datasets)
        context['total_companies'] = total_companies
        context['total_active'] = total_active

        context['title'] = f'Editar Seguradora: {self.object.name}'
        context['button_text'] = 'Salvar Alterações'
        return context


class InsuranceCompanyDeleteView(LoginRequiredMixin, IsAdminOrManagerMixin, DeleteView):
    """Deleta seguradora."""
    model = InsuranceCompany
    template_name = 'insurancecompany/confirm_delete.html'
    success_url = reverse_lazy('insurancecompany:list')

    def delete(self, request, *args, **kwargs):
        insurance = self.get_object()
        messages.success(request, f'Seguradora "{insurance.name}" excluída com sucesso!')
        return super().delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Estatisticas gerais
        total_companies = InsuranceCompany.objects.count()
        total_active = InsuranceCompany.objects.filter(is_active=True).count()

        # Grafico: OS por seguradora mes a mes (12 meses a partir de janeiro)
        today = timezone.now().date()
        months = [date(today.year, month, 1) for month in range(1, 13)]

        pt_months = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
        month_labels = [f"{pt_months[m.month-1]}/{str(m.year)[2:]}" for m in months]
        month_keys = {m: idx for idx, m in enumerate(months)}

        counts = WorkOrder.objects.filter(
            insurance_company__isnull=False
        ).annotate(
            month=TruncMonth('created_at')
        ).values(
            'insurance_company_id', 'month'
        ).annotate(
            count=Count('id')
        )

        data_map = {}
        for row in counts:
            comp_id = row['insurance_company_id']
            month_key = row['month'].date().replace(day=1)
            if comp_id not in data_map:
                data_map[comp_id] = [0] * len(months)
            idx = month_keys.get(month_key)
            if idx is not None:
                data_map[comp_id][idx] = row['count']

        colors = [
            '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
            '#06B6D4', '#84CC16', '#F97316', '#EC4899', '#6366F1'
        ]
        datasets = []
        for i, comp in enumerate(InsuranceCompany.objects.order_by('name')):
            datasets.append({
                'label': comp.name,
                'data': data_map.get(comp.id, [0] * len(months)),
                'backgroundColor': colors[i % len(colors)],
            })

        import json
        context['chart_labels_json'] = json.dumps(month_labels)
        context['chart_datasets_json'] = json.dumps(datasets)
        context['total_companies'] = total_companies
        context['total_active'] = total_active

        context['work_orders_count'] = self.object.work_orders.count()
        return context

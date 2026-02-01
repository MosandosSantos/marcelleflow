"""
Views CRUD para gerenciamento de Tipos de Serviço.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q, Count, Avg, Sum, F, FloatField, DecimalField, Value, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta
import json

from .models import CostItem, ServiceCost, ServiceType
from .forms import (
    CostItemForm,
    ServiceCostFilterForm,
    ServiceCostForm,
    ServiceTypeForm,
)
from workorder.models import WorkOrder
from accounts.mixins import IsAdminOrOperationalMixin


class ServiceTypeListView(LoginRequiredMixin, IsAdminOrOperationalMixin, ListView):
    """Lista todos os tipos de serviço com busca e filtros."""
    model = ServiceType
    template_name = 'servicetype/list.html'
    context_object_name = 'service_types'
    paginate_by = 10

    def get_queryset(self):
        queryset = ServiceType.objects.annotate(
            providers_count=Count('providers'),
            work_orders_count=Count('work_orders')
        ).order_by('name')

        # Busca
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
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
        cutoff = timezone.now() - timedelta(days=365)
        context['service_types_with_os_12m'] = ServiceType.objects.filter(
            work_orders__created_at__gte=cutoff
        ).distinct().count()
        context['service_types_without_os_12m'] = ServiceType.objects.exclude(
            work_orders__created_at__gte=cutoff
        ).distinct().count()
        context['service_types_without_providers'] = ServiceType.objects.annotate(
            providers_total=Count('providers')
        ).filter(providers_total=0).count()
        return context


class ServiceTypeDashboardView(LoginRequiredMixin, IsAdminOrOperationalMixin, ListView):
    """Dashboards administrativos de tipos de serviço."""
    model = ServiceType
    template_name = 'servicetype/dashboards.html'
    context_object_name = 'service_types'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 1) Top 10 serviços com mais OS
        top_os = WorkOrder.objects.filter(
            service_type__isnull=False
        ).values(
            'service_type__name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        context['top_os_labels'] = json.dumps([row['service_type__name'] for row in top_os])
        context['top_os_values'] = json.dumps([row['count'] for row in top_os])

        # 2) Top 10 serviços com maior faturamento (labor_cost)
        top_revenue = WorkOrder.objects.filter(
            service_type__isnull=False
        ).values(
            'service_type__name'
        ).annotate(
            revenue=Sum(Coalesce('labor_cost', Value(0), output_field=DecimalField()))
        ).order_by('-revenue')[:10]
        context['top_revenue_labels'] = json.dumps([row['service_type__name'] for row in top_revenue])
        context['top_revenue_values'] = json.dumps([float(row['revenue'] or 0) for row in top_revenue])

        # 3) Lucratividade (scatter): X=Qtd OS, Y=Lucro médio por OS, Bolha=Receita total
        profit_qs = WorkOrder.objects.filter(
            service_type__isnull=False
        ).annotate(
            profit=ExpressionWrapper(
                Coalesce('labor_cost', Value(0), output_field=DecimalField()) -
                Coalesce(F('service_type__estimated_price'), Value(0), output_field=DecimalField()),
                output_field=DecimalField()
            ),
        ).values(
            'service_type__name'
        ).annotate(
            qty=Count('id'),
            avg_profit=Avg('profit'),
            total_revenue=Sum(Coalesce('labor_cost', Value(0), output_field=DecimalField()))
        ).order_by('-qty')

        profit_points = []
        max_revenue = 0
        for row in profit_qs:
            total_revenue = float(row['total_revenue'] or 0)
            max_revenue = max(max_revenue, total_revenue)
            profit_points.append({
                'label': row['service_type__name'],
                'x': row['qty'],
                'y': float(row['avg_profit'] or 0),
                'revenue': total_revenue,
            })

        def bubble_radius(revenue):
            if max_revenue <= 0:
                return 6
            return 6 + (revenue / max_revenue) * 14

        for point in profit_points:
            point['r'] = bubble_radius(point['revenue'])

        context['profit_points'] = json.dumps(profit_points)

        # 4) Demanda x Tempo médio (scatter): X=Qtd OS, Y=Tempo médio
        time_qs = WorkOrder.objects.filter(
            service_type__isnull=False
        ).values(
            'service_type__name'
        ).annotate(
            qty=Count('id'),
            avg_real=Avg('real_time_minutes'),
            avg_est=Avg('estimated_time_minutes')
        )
        demand_time_points = []
        for row in time_qs:
            avg_time = row['avg_real'] if row['avg_real'] is not None else row['avg_est']
            if avg_time is None:
                continue
            demand_time_points.append({
                'label': row['service_type__name'],
                'x': row['qty'],
                'y': float(avg_time),
            })
        context['demand_time_points'] = json.dumps(demand_time_points)

        # 5) Estouro de tempo por serviço (barra)
        overrun_qs = WorkOrder.objects.filter(
            service_type__isnull=False
        ).values(
            'service_type__name'
        ).annotate(
            avg_real=Avg('real_time_minutes'),
            avg_est=Avg('estimated_time_minutes')
        )

        overrun_rows = []
        for row in overrun_qs:
            if row['avg_real'] is None or row['avg_est'] is None:
                continue
            overrun = float(row['avg_real'] - row['avg_est'])
            if overrun > 0:
                overrun_rows.append((row['service_type__name'], overrun))

        overrun_rows.sort(key=lambda item: item[1], reverse=True)
        overrun_rows = overrun_rows[:10]
        context['overrun_labels'] = json.dumps([row[0] for row in overrun_rows])
        context['overrun_values'] = json.dumps([row[1] for row in overrun_rows])

        # 6) BCG: X=Qtd OS, Y=Receita média
        bcg_qs = WorkOrder.objects.filter(
            service_type__isnull=False
        ).values(
            'service_type__name'
        ).annotate(
            qty=Count('id'),
            avg_revenue=Avg(Coalesce('labor_cost', Value(0), output_field=DecimalField()))
        )

        bcg_points = []
        xs = []
        ys = []
        for row in bcg_qs:
            qty = row['qty']
            avg_rev = float(row['avg_revenue'] or 0)
            xs.append(qty)
            ys.append(avg_rev)
            bcg_points.append({
                'label': row['service_type__name'],
                'x': qty,
                'y': avg_rev,
            })

        median_x = sorted(xs)[len(xs) // 2] if xs else 0
        median_y = sorted(ys)[len(ys) // 2] if ys else 0
        min_x = min(xs) if xs else 0
        max_x = max(xs) if xs else 1
        min_y = min(ys) if ys else 0
        max_y = max(ys) if ys else 1

        context['bcg_points'] = json.dumps(bcg_points)
        context['bcg_median_x_json'] = json.dumps(median_x)
        context['bcg_median_y_json'] = json.dumps(float(median_y))
        context['bcg_min_x_json'] = json.dumps(min_x)
        context['bcg_max_x_json'] = json.dumps(max_x)
        context['bcg_min_y_json'] = json.dumps(float(min_y))
        context['bcg_max_y_json'] = json.dumps(float(max_y))

        return context


class ServiceTypeDetailView(LoginRequiredMixin, IsAdminOrOperationalMixin, DetailView):
    """Exibe detalhes de um tipo de serviço."""
    model = ServiceType
    template_name = 'servicetype/detail.html'
    context_object_name = 'service_type'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Estatísticas
        context['providers_count'] = self.object.providers.count()
        context['work_orders_count'] = self.object.work_orders.count()

        # Últimos prestadores
        context['recent_providers'] = self.object.providers.all()[:5]

        # Últimas ordens de serviço
        context['recent_work_orders'] = self.object.work_orders.select_related(
            'client', 'provider', 'status'
        ).order_by('-created_at')[:10]

        return context


class ServiceTypeCreateView(LoginRequiredMixin, IsAdminOrOperationalMixin, CreateView):
    """Cria novo tipo de serviço."""
    model = ServiceType
    form_class = ServiceTypeForm
    template_name = 'servicetype/form.html'
    success_url = reverse_lazy('servicetype:list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Tipo de serviço "{self.object.name}" criado com sucesso!')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Novo Tipo de Serviço'
        context['button_text'] = 'Cadastrar Tipo de Serviço'
        context['is_create'] = True
        return context


class ServiceTypeUpdateView(LoginRequiredMixin, IsAdminOrOperationalMixin, UpdateView):
    """Atualiza tipo de serviço existente."""
    model = ServiceType
    form_class = ServiceTypeForm
    template_name = 'servicetype/form.html'

    def get_success_url(self):
        return reverse_lazy('servicetype:detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Tipo de serviço "{self.object.name}" atualizado com sucesso!')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Editar Tipo de Serviço: {self.object.name}'
        context['button_text'] = 'Salvar Alterações'
        context['is_create'] = False
        return context


class ServiceTypeDeleteView(LoginRequiredMixin, IsAdminOrOperationalMixin, DeleteView):
    """Deleta tipo de serviço."""
    model = ServiceType
    template_name = 'servicetype/confirm_delete.html'
    success_url = reverse_lazy('servicetype:list')

    def delete(self, request, *args, **kwargs):
        service_type = self.get_object()
        messages.success(request, f'Tipo de serviço "{service_type.name}" excluído com sucesso!')
        return super().delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['providers_count'] = self.object.providers.count()
        context['work_orders_count'] = self.object.work_orders.count()
        return context


class ServiceTypeProvidersView(LoginRequiredMixin, IsAdminOrOperationalMixin, DetailView):
    """Lista todos os prestadores que oferecem um tipo de serviço específico."""
    model = ServiceType
    template_name = 'servicetype/providers.html'
    context_object_name = 'service_type'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Buscar todos os prestadores deste tipo de serviço
        providers = self.object.providers.select_related('user').all()

        # Aplicar busca se houver
        search = self.request.GET.get('search')
        if search:
            from django.db.models import Q
            providers = providers.filter(
                Q(full_name__icontains=search) |
                Q(email__icontains=search) |
                Q(cpf__icontains=search)
            )

        context['providers'] = providers
        context['providers_count'] = providers.count()

        return context


# ============================================
# VIEWS PARA COST ITEMS (Itens de Custo)
# ============================================

class CostItemListView(LoginRequiredMixin, IsAdminOrOperationalMixin, ListView):
    """Lista todos os itens de custo com filtros."""
    model = CostItem
    template_name = 'servicetype/costitem_list.html'
    context_object_name = 'cost_items'
    paginate_by = 20

    def get_queryset(self):
        queryset = CostItem.objects.all().order_by('name')

        # Busca
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )

        # Filtro por tipo de custo
        cost_type = self.request.GET.get('cost_type')
        if cost_type:
            queryset = queryset.filter(cost_type=cost_type)

        # Filtro por comportamento de custo
        cost_behavior = self.request.GET.get('cost_behavior')
        if cost_behavior:
            queryset = queryset.filter(cost_behavior=cost_behavior)

        # Filtro por status
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_cost_items'] = CostItem.objects.count()
        context['active_cost_items'] = CostItem.objects.filter(is_active=True).count()
        context['direct_costs'] = CostItem.objects.filter(cost_type='direto').count()
        context['indirect_costs'] = CostItem.objects.filter(cost_type='indireto').count()
        return context


class CostItemDetailView(LoginRequiredMixin, IsAdminOrOperationalMixin, DetailView):
    """Exibe detalhes de um item de custo."""
    model = CostItem
    template_name = 'servicetype/costitem_detail.html'
    context_object_name = 'cost_item'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['service_costs_count'] = self.object.service_costs.count()
        context['services_using_cost'] = self.object.service_costs.select_related('service_type').all()
        return context


class CostItemCreateView(LoginRequiredMixin, IsAdminOrOperationalMixin, CreateView):
    """Cria novo item de custo."""
    model = CostItem
    form_class = CostItemForm
    template_name = 'servicetype/costitem_form.html'
    success_url = reverse_lazy('servicetype:costitem_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Item de custo "{self.object.name}" criado com sucesso!')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Novo Item de Custo'
        context['button_text'] = 'Cadastrar Item de Custo'
        context['is_create'] = True
        return context


class CostItemUpdateView(LoginRequiredMixin, IsAdminOrOperationalMixin, UpdateView):
    """Atualiza item de custo existente."""
    model = CostItem
    form_class = CostItemForm
    template_name = 'servicetype/costitem_form.html'

    def get_success_url(self):
        return reverse_lazy('servicetype:costitem_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Item de custo "{self.object.name}" atualizado com sucesso!')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Editar Item de Custo: {self.object.name}'
        context['button_text'] = 'Salvar Alterações'
        context['is_create'] = False
        return context


class CostItemDeleteView(LoginRequiredMixin, IsAdminOrOperationalMixin, DeleteView):
    """Deleta item de custo."""
    model = CostItem
    template_name = 'servicetype/costitem_confirm_delete.html'
    success_url = reverse_lazy('servicetype:costitem_list')

    def delete(self, request, *args, **kwargs):
        cost_item = self.get_object()
        messages.success(request, f'Item de custo "{cost_item.name}" excluído com sucesso!')
        return super().delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['service_costs_count'] = self.object.service_costs.count()
        return context


# ============================================
# VIEWS PARA SERVICE COSTS (Composição de Custos)
# ============================================

class ServiceCostListView(LoginRequiredMixin, IsAdminOrOperationalMixin, ListView):
    """Lista todas as associações de custos com serviços."""
    model = ServiceCost
    template_name = 'servicetype/servicecost_list.html'
    context_object_name = 'service_costs'
    paginate_by = 20

    def get_queryset(self):
        queryset = ServiceCost.objects.select_related(
            'service_type', 'cost_item'
        ).all().order_by('service_type__name', 'cost_item__name')

        # Filtro por tipo de serviço
        service_type_id = self.request.GET.get('service_type')
        if service_type_id:
            queryset = queryset.filter(service_type_id=service_type_id)

        # Filtro por item de custo
        cost_item_id = self.request.GET.get('cost_item')
        if cost_item_id:
            queryset = queryset.filter(cost_item_id=cost_item_id)

        # Filtro por tipo de custo
        cost_type = self.request.GET.get('cost_type')
        if cost_type:
            queryset = queryset.filter(cost_item__cost_type=cost_type)

        # Filtro por obrigatoriedade
        is_required = self.request.GET.get('is_required')
        if is_required == 'true':
            queryset = queryset.filter(is_required=True)
        elif is_required == 'false':
            queryset = queryset.filter(is_required=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = ServiceCostFilterForm(self.request.GET)
        context['total_service_costs'] = ServiceCost.objects.count()
        context['services_with_costs'] = ServiceType.objects.filter(
            service_costs__isnull=False
        ).distinct().count()
        return context


class ServiceCostDetailView(LoginRequiredMixin, IsAdminOrOperationalMixin, DetailView):
    """Exibe detalhes de uma associação custo-serviço."""
    model = ServiceCost
    template_name = 'servicetype/servicecost_detail.html'
    context_object_name = 'service_cost'

    def get_queryset(self):
        return ServiceCost.objects.select_related('service_type', 'cost_item')


class ServiceCostCreateView(LoginRequiredMixin, IsAdminOrOperationalMixin, CreateView):
    """Associa um item de custo a um serviço."""
    model = ServiceCost
    form_class = ServiceCostForm
    template_name = 'servicetype/servicecost_form.html'
    success_url = reverse_lazy('servicetype:servicecost_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Se service_type_id foi passado via GET, passar para o form
        service_type_id = self.request.GET.get('service_type')
        if service_type_id:
            kwargs['service_type_id'] = service_type_id
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Custo "{self.object.cost_item.name}" associado ao serviço "{self.object.service_type.name}" com sucesso!'
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Associar Custo a Serviço'
        context['button_text'] = 'Cadastrar Associação'
        context['is_create'] = True
        return context


class ServiceCostUpdateView(LoginRequiredMixin, IsAdminOrOperationalMixin, UpdateView):
    """Atualiza uma associação custo-serviço."""
    model = ServiceCost
    form_class = ServiceCostForm
    template_name = 'servicetype/servicecost_form.html'

    def get_success_url(self):
        return reverse_lazy('servicetype:servicecost_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Associação de custo atualizada com sucesso!')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Editar Associação: {self.object.service_type.name} - {self.object.cost_item.name}'
        context['button_text'] = 'Salvar Alterações'
        context['is_create'] = False
        return context


class ServiceCostDeleteView(LoginRequiredMixin, IsAdminOrOperationalMixin, DeleteView):
    """Remove uma associação custo-serviço."""
    model = ServiceCost
    template_name = 'servicetype/servicecost_confirm_delete.html'
    success_url = reverse_lazy('servicetype:servicecost_list')

    def delete(self, request, *args, **kwargs):
        service_cost = self.get_object()
        messages.success(
            request,
            f'Associação "{service_cost.service_type.name} - {service_cost.cost_item.name}" excluída com sucesso!'
        )
        return super().delete(request, *args, **kwargs)


# ============================================
# VIEWS PARA ANÁLISE DE MARGEM DE LUCRO
# ============================================

class ProfitMarginAnalysisView(LoginRequiredMixin, IsAdminOrOperationalMixin, ListView):
    """
    Análise comparativa de margem de lucro: Estimado vs Real.
    Mostra para cada tipo de serviço:
    - Custo estimado (baseado em ServiceCost)
    - Margem estimada
    - Custo real (baseado em transações de despesa vinculadas)
    - Margem real
    - Desvio entre estimado e real
    """
    model = ServiceType
    template_name = 'servicetype/profit_margin_analysis.html'
    context_object_name = 'service_types'
    paginate_by = 20

    def get_queryset(self):
        queryset = ServiceType.objects.filter(is_active=True).order_by('name')

        # Filtro: apenas serviços com custos cadastrados
        show_only_with_costs = self.request.GET.get('only_with_costs')
        if show_only_with_costs == 'true':
            queryset = queryset.filter(service_costs__isnull=False).distinct()

        # Filtro: apenas serviços com OS executadas
        show_only_with_orders = self.request.GET.get('only_with_orders')
        if show_only_with_orders == 'true':
            queryset = queryset.filter(work_orders__isnull=False).distinct()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Calcular análise para cada serviço
        analysis = []
        for service_type in context['service_types']:
            # Custos e margens estimadas
            estimated_cost = service_type.total_estimated_cost()
            estimated_margin_value = service_type.estimated_profit_margin_value()
            estimated_margin_percentage = service_type.estimated_profit_margin_percentage()

            # Custos e margens reais
            real_data = service_type.calculate_real_profit_from_workorders()

            # Desvios (Real - Estimado)
            cost_deviation = real_data['total_real_cost'] - estimated_cost
            margin_deviation_value = real_data['profit_margin_value'] - estimated_margin_value
            margin_deviation_percentage = real_data['profit_margin_percentage'] - estimated_margin_percentage

            # Indicadores de performance
            cost_accuracy = Decimal('0.00')
            if estimated_cost > 0:
                cost_accuracy = 100 - abs((cost_deviation / estimated_cost) * 100)

            margin_accuracy = Decimal('0.00')
            if estimated_margin_percentage > 0:
                margin_accuracy = 100 - abs((margin_deviation_percentage / estimated_margin_percentage) * 100)

            analysis.append({
                'service_type': service_type,
                'estimated_price': service_type.estimated_price,
                'estimated_cost': estimated_cost,
                'estimated_margin_value': estimated_margin_value,
                'estimated_margin_percentage': estimated_margin_percentage,
                'real_revenue': real_data['total_revenue'],
                'real_cost': real_data['total_real_cost'],
                'real_margin_value': real_data['profit_margin_value'],
                'real_margin_percentage': real_data['profit_margin_percentage'],
                'work_orders_count': real_data['work_orders_count'],
                'cost_deviation': cost_deviation,
                'margin_deviation_value': margin_deviation_value,
                'margin_deviation_percentage': margin_deviation_percentage,
                'cost_accuracy': cost_accuracy,
                'margin_accuracy': margin_accuracy,
            })

        context['analysis'] = analysis

        # Estatísticas gerais
        total_services = len(analysis)
        services_with_costs = sum(1 for item in analysis if item['estimated_cost'] > 0)
        services_with_orders = sum(1 for item in analysis if item['work_orders_count'] > 0)

        avg_estimated_margin = Decimal('0.00')
        avg_real_margin = Decimal('0.00')
        if services_with_orders > 0:
            avg_estimated_margin = sum(
                item['estimated_margin_percentage'] for item in analysis if item['work_orders_count'] > 0
            ) / services_with_orders
            avg_real_margin = sum(
                item['real_margin_percentage'] for item in analysis if item['work_orders_count'] > 0
            ) / services_with_orders

        context['summary'] = {
            'total_services': total_services,
            'services_with_costs': services_with_costs,
            'services_with_orders': services_with_orders,
            'avg_estimated_margin': avg_estimated_margin,
            'avg_real_margin': avg_real_margin,
            'margin_deviation_avg': avg_real_margin - avg_estimated_margin,
        }

        return context


class ServiceTypeComingSoonView(LoginRequiredMixin, IsAdminOrOperationalMixin, TemplateView):
    template_name = 'servicetype/coming_soon.html'


class ServiceTypeProfitDetailView(LoginRequiredMixin, IsAdminOrOperationalMixin, DetailView):
    """
    Detalhamento completo da margem de lucro de um serviço específico.
    Mostra:
    - Composição de custos (CostItems)
    - Histórico de WorkOrders executadas
    - Transações de despesa vinculadas
    - Gráficos de evolução
    """
    model = ServiceType
    template_name = 'servicetype/profit_detail.html'
    context_object_name = 'service_type'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Custos estimados
        context['estimated_cost'] = self.object.total_estimated_cost()
        context['estimated_margin_value'] = self.object.estimated_profit_margin_value()
        context['estimated_margin_percentage'] = self.object.estimated_profit_margin_percentage()
        context['cost_breakdown'] = self.object.get_cost_breakdown()

        # Composição de custos
        context['service_costs'] = self.object.service_costs.select_related('cost_item').all()

        # Dados reais
        real_data = self.object.calculate_real_profit_from_workorders()
        context['real_data'] = real_data

        # WorkOrders executadas
        from workorder.models import WorkOrder
        context['work_orders'] = WorkOrder.objects.filter(
            service_type=self.object,
            status__name__in=['Concluído', 'Finalizado']
        ).select_related('client', 'provider', 'status').order_by('-finished_at')[:20]

        # Transações vinculadas
        from finance.models import Transaction
        context['related_transactions'] = Transaction.objects.filter(
            tipo='despesa',
            status='realizado',
            related_service_type=self.object
        ).select_related('account', 'category').order_by('-data_pagamento')[:20]

        # Desvios
        context['cost_deviation'] = real_data['total_real_cost'] - context['estimated_cost']
        context['margin_deviation_value'] = real_data['profit_margin_value'] - context['estimated_margin_value']
        context['margin_deviation_percentage'] = real_data['profit_margin_percentage'] - context['estimated_margin_percentage']

        return context

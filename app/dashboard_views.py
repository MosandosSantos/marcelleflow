"""
Views de Dashboard por perfil de usuário.
Cada role (admin, manager, tech, customer) tem um dashboard específico.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models import Count, Avg, Q, Sum
from django.utils import timezone
from datetime import timedelta, datetime
import json
from decimal import Decimal

from workorder.models import WorkOrder, WorkOrderEvaluation
from workorderstatus.models import ServiceOrderStatus
from provider.models import Provider
from finance.models import Transaction
from servicetype.models import ServiceType
from servicetype.services import simulate_service_pricing
from workorder.sla_utils import calculate_sla_hours, get_sla_status, get_sla_color_hex


@login_required
def dashboard_router(request):
    """
    Redireciona para o dashboard específico conforme o role do usuário.
    """
    user = request.user

    if user.is_superuser or user.is_staff or user.role == 'admin':
        return admin_dashboard(request)
    elif user.role == 'operational':
        return operational_dashboard(request)
    elif user.role == 'financial':
        return financial_dashboard(request)
    elif user.role == 'tech':
        return provider_dashboard(request)
    elif user.role == 'customer':
        return customer_dashboard(request)
    else:
        return redirect('landing')


@login_required
def admin_dashboard(request):
    """
    Dashboard para Admin/Operador com métricas gerais estilo Pinterest.
    Baseado no layout da imagem fornecida, adaptado para Ordens de Serviço.
    """
    # ============= KPIs DO TOPO (5 CARDS) =============

    # Total de OS (substitui "Membros")
    total_orders = WorkOrder.objects.filter(is_active=True).count()

    current_year = timezone.now().year
    previous_year = current_year - 1
    orders_current_year = WorkOrder.objects.filter(created_at__year=current_year).count()
    orders_previous_year = WorkOrder.objects.filter(created_at__year=previous_year).count()
    if orders_previous_year > 0:
        orders_growth_percent = round(((orders_current_year - orders_previous_year) / orders_previous_year) * 100, 1)
    else:
        orders_growth_percent = None

    today = timezone.localdate()
    month_start = today.replace(day=1)
    prev_month_end = month_start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)
    orders_current_month = WorkOrder.objects.filter(created_at__date__gte=month_start).count()
    orders_previous_month = WorkOrder.objects.filter(created_at__date__gte=prev_month_start, created_at__date__lte=prev_month_end).count()
    if orders_previous_month > 0:
        orders_month_growth_percent = round(((orders_current_month - orders_previous_month) / orders_previous_month) * 100, 1)
    else:
        orders_month_growth_percent = None
    orders_previous_year = WorkOrder.objects.filter(created_at__year=previous_year).count()
    if orders_previous_year > 0:
        orders_growth_percent = round(((orders_current_year - orders_previous_year) / orders_previous_year) * 100, 1)
    else:
        orders_growth_percent = None

    # Contar por status
    status_counts = WorkOrder.objects.filter(is_active=True).values(
        'status__group_code'
    ).annotate(count=Count('id'))
    status_dict = {item['status__group_code']: item['count'] for item in status_counts}

    # OS Pendentes (substitui "Caixa")
    pending_count = status_dict.get('OPEN', 0)

    # OS Em Andamento (substitui "Despesas")
    in_progress_count = status_dict.get('IN_PROGRESS', 0)

    # OS Aguardando Aprovação (Validação)
    waiting_approval_count = status_dict.get('VALIDATION', 0)

    # Pipeline aberto (Abertas + Em Andamento + Validação)
    open_pipeline_total = pending_count + in_progress_count + waiting_approval_count
    if open_pipeline_total > 0:
        waiting_approval_share = round((waiting_approval_count / open_pipeline_total) * 100, 1)
    else:
        waiting_approval_share = None

    # OS Concluídas (substitui "Saldo" - mas em VERDE pois é positivo)
    completed_count = status_dict.get('CLOSED', 0)

    # Subtipos encerradas (por status_code)
    closed_breakdown = WorkOrder.objects.filter(
        is_active=True,
        status__status_code__in=['COMPLETED', 'FINANCIAL_CLOSED', 'CANCELED']
    ).values('status__status_code').annotate(count=Count('id'))
    closed_dict = {item['status__status_code']: item['count'] for item in closed_breakdown}
    completed_final_count = closed_dict.get('COMPLETED', 0)
    financial_closed_count = closed_dict.get('FINANCIAL_CLOSED', 0)
    canceled_count = closed_dict.get('CANCELED', 0)

    # Taxa de conclusão no prazo (para o gauge)
    completed_orders = WorkOrder.objects.filter(
        status__status_code__in=['COMPLETED', 'FINANCIAL_CLOSED'],
        finished_at__isnull=False,
        scheduled_date__isnull=False
    )
    on_time_count = 0
    for order in completed_orders:
        # Considera "no prazo" se finalizou até 24h após a data agendada
        deadline = datetime.combine(order.scheduled_date, datetime.min.time()) + timedelta(days=1)
        if order.finished_at.replace(tzinfo=None) <= deadline:
            on_time_count += 1

    completion_rate = (on_time_count / completed_orders.count() * 100) if completed_orders.count() > 0 else 0

    # ============= TOP CONSULTORES (Gráfico Barras Horizontais) =============

    top_providers = Provider.objects.filter(
        rating_count__gt=0
    ).order_by('-rating_avg')[:5]

    top_providers_names = [p.full_name for p in top_providers]
    top_providers_ratings = [float(p.rating_avg) if p.rating_avg else 0 for p in top_providers]

    # ============= VELOCÍMETROS (3 KPIs Circulares) =============

    # 1. Taxa de Conclusão no Prazo
    on_time_rate = round(completion_rate, 1)

    # 2. Satisfacao Media dos Clientes (media das avaliacoes por pedido)
    avg_satisfaction = WorkOrderEvaluation.objects.aggregate(Avg('rating'))['rating__avg']
    if avg_satisfaction is None:
        avg_satisfaction = WorkOrder.objects.filter(
            evaluation_rating__gt=0
        ).aggregate(Avg('evaluation_rating'))['evaluation_rating__avg'] or 0
    satisfaction_percent = round((avg_satisfaction / 5 * 100), 1)
    satisfaction_avg_rating = round(avg_satisfaction, 2)

# 3. Tempo Médio de Atendimento (% do tempo estimado)
    orders_with_time = WorkOrder.objects.filter(
        real_time_minutes__isnull=False,
        estimated_time_minutes__isnull=False,
        estimated_time_minutes__gt=0
    )
    if orders_with_time.exists():
        avg_real = orders_with_time.aggregate(Avg('real_time_minutes'))['real_time_minutes__avg']
        avg_estimated = orders_with_time.aggregate(Avg('estimated_time_minutes'))['estimated_time_minutes__avg']
        time_efficiency = round((avg_estimated / avg_real * 100), 1) if avg_real > 0 else 100
    else:
        time_efficiency = 50  # Valor padrão

    # ============= PRÓXIMAS OS AGENDADAS (Tabela Agenda) =============

    upcoming_orders = WorkOrder.objects.filter(
        scheduled_date__gte=timezone.localdate(),
        is_active=True
    ).exclude(
        status__status_code__in=['COMPLETED', 'FINANCIAL_CLOSED', 'CANCELED']
    ).select_related('client', 'provider', 'service_type').order_by('scheduled_date')[:5]

    # ============= TEMPO MÉDIO DE ATENDIMENTO (Card Número Grande) =============

    avg_time_minutes = WorkOrder.objects.filter(
        real_time_minutes__isnull=False
    ).aggregate(Avg('real_time_minutes'))['real_time_minutes__avg'] or 0
    avg_hours = round(avg_time_minutes / 60, 1)

    # ============= TOP 10 SERVI?OS MAIS SOLICITADOS (Gr?fico Barras Horizontais) =============
    top_services = WorkOrder.objects.filter(
        service_type__isnull=False
    ).values('service_type__name').annotate(
        total=Count('id')
    ).order_by('-total')[:5]
    top_services_labels = [item['service_type__name'] for item in top_services]
    top_services_counts = [item['total'] for item in top_services]

    # ============= CLIENTES MAIS ATIVOS (Top 5 por quantidade de OS) =============
    top_clients = WorkOrder.objects.filter(
        client__isnull=False
    ).values('client__full_name').annotate(
        total=Count('id')
    ).order_by('-total', 'client__full_name')[:5]
    top_clients_labels = [item['client__full_name'] for item in top_clients]
    top_clients_orders = [item['total'] for item in top_clients]

            # ============= ATENDIMENTOS POR M?S (?ltimos 12 meses) =============

    # ?ltimos 12 meses (linhas: total de O.S. e O.S. conclu?das)
    today = timezone.localdate()
    months = []
    for i in range(11, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        months.append((year, month))

    total_daily_counts = []
    completed_daily_counts = []
    daily_labels = []

    for year, month in months:
        month_start = datetime(year, month, 1)
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        month_end = next_month - timedelta(days=1)

        total_daily_counts.append(
            WorkOrder.objects.filter(created_at__date__gte=month_start.date(), created_at__date__lte=month_end.date()).count()
        )
        completed_daily_counts.append(
            WorkOrder.objects.filter(
                created_at__date__gte=month_start.date(),
                created_at__date__lte=month_end.date(),
                status__status_code__in=['COMPLETED', 'FINANCIAL_CLOSED']
            ).count()
        )
        daily_labels.append(month_start.strftime('%b/%y'))

# ============= INDICADORES FINANCEIROS =============

    from django.db.models import Sum

    # Receita total (soma dos labor_cost das OS conclu?das)
    total_revenue = WorkOrder.objects.filter(
        status__status_code__in=['COMPLETED', 'FINANCIAL_CLOSED'],
        labor_cost__isnull=False
    ).aggregate(Sum('labor_cost'))['labor_cost__sum'] or 0

    # Receita deste mês
    current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0)
    monthly_revenue = WorkOrder.objects.filter(
        finished_at__gte=current_month_start,
            status__status_code__in=['COMPLETED', 'FINANCIAL_CLOSED'],
            labor_cost__isnull=False
    ).aggregate(Sum('labor_cost'))['labor_cost__sum'] or 0

    # Receita dos últimos 6 meses (para gráfico de linha)
    monthly_revenue_data = []
    monthly_revenue_labels = []

    for i in range(5, -1, -1):
        month_date = datetime.now() - timedelta(days=30*i)
        month_start = month_date.replace(day=1, hour=0, minute=0, second=0)

        if i > 0:
            next_month = month_date.replace(day=28) + timedelta(days=4)
            month_end = next_month.replace(day=1) - timedelta(days=1)
        else:
            month_end = datetime.now()

        revenue = WorkOrder.objects.filter(
            finished_at__range=[month_start, month_end],
            status__status_code__in=['COMPLETED', 'FINANCIAL_CLOSED'],
            labor_cost__isnull=False
        ).aggregate(Sum('labor_cost'))['labor_cost__sum'] or 0

        monthly_revenue_data.append(float(revenue))
        monthly_revenue_labels.append(month_start.strftime('%b/%y'))

    # Ticket médio (receita total / número de OS concluídas)
    completed_with_cost = WorkOrder.objects.filter(
        status__status_code__in=['COMPLETED', 'FINANCIAL_CLOSED'],
        labor_cost__isnull=False
    ).count()
    avg_ticket = (total_revenue / completed_with_cost) if completed_with_cost > 0 else 0

    # Receita pendente (OS em andamento + pendentes)
    pending_revenue = WorkOrder.objects.filter(
        status__group_code__in=['OPEN', 'IN_PROGRESS'],
            labor_cost__isnull=False
    ).aggregate(Sum('labor_cost'))['labor_cost__sum'] or 0

    # ============= MÉTRICAS DE PEDIDOS PARA CARDS 1 E 2 =============
    last_3_years = [current_year - i for i in range(1, 4)]
    orders_last_3_years = [
        WorkOrder.objects.filter(created_at__year=year).count()
        for year in last_3_years
    ]
    orders_avg_years = sum(orders_last_3_years) / len(orders_last_3_years) if orders_last_3_years else 0

    orders_last_6_months = []
    for i in range(1, 7):
        month_ago = today - timedelta(days=30*i)
        month_ago_start = month_ago.replace(day=1)
        if month_ago.month == 12:
            next_month = month_ago.replace(year=month_ago.year + 1, month=1, day=1)
        else:
            next_month = month_ago.replace(month=month_ago.month + 1, day=1)
        month_ago_end = next_month - timedelta(days=1)
        orders_last_6_months.append(
            WorkOrder.objects.filter(created_at__date__gte=month_ago_start, created_at__date__lte=month_ago_end).count()
        )

    orders_avg_months = sum(orders_last_6_months) / len(orders_last_6_months) if orders_last_6_months else 0

    # ============= CONTEXT FINAL =============

    context = {
        # KPIs do topo
        'total_orders': total_orders,
        'orders_current_year': orders_current_year,
        'orders_previous_year': orders_previous_year,
        'orders_growth_percent': orders_growth_percent,
        'current_year': current_year,
        'previous_year': previous_year,
        'orders_current_month': orders_current_month,
        'orders_previous_month': orders_previous_month,
        'orders_month_growth_percent': orders_month_growth_percent,
        'current_month_label': today.strftime('%m/%Y'),
        'previous_month_label': prev_month_start.strftime('%m/%Y'),
        'pending_count': pending_count,
        'in_progress_count': in_progress_count,
        'waiting_approval_count': waiting_approval_count,
        'open_pipeline_total': open_pipeline_total,
        'waiting_approval_share': waiting_approval_share,
        'completed_count': completed_count,
        'completed_final_count': completed_final_count,
        'financial_closed_count': financial_closed_count,
        'canceled_count': canceled_count,
        'completion_rate': round(completion_rate, 1),
        'completion_rate_json': json.dumps(round(completion_rate, 1)),

        # Top Prestadores (JSON para Chart.js)
        'top_providers_names': json.dumps(top_providers_names),
        'top_providers_ratings': json.dumps(top_providers_ratings),

        # Velocímetros (KPIs circulares)
        'on_time_rate': on_time_rate,
        'on_time_rate_json': json.dumps(on_time_rate),
        'satisfaction_percent': satisfaction_percent,
        'satisfaction_avg_rating': satisfaction_avg_rating,
        'satisfaction_percent_json': json.dumps(satisfaction_percent),
        'time_efficiency': time_efficiency,
        'time_efficiency_json': json.dumps(time_efficiency),

        # Próximas OS
        'upcoming_orders': upcoming_orders,

        # Tempo médio
        'avg_hours': avg_hours,

        # Gráfico diário (JSON para Chart.js)
        'daily_labels': json.dumps(daily_labels),
        'daily_counts': json.dumps(total_daily_counts),
        'daily_completed_counts': json.dumps(completed_daily_counts),
        'top_services_labels': json.dumps(top_services_labels),
        'top_services_counts': json.dumps(top_services_counts),
        'top_clients_labels': json.dumps(top_clients_labels),
        'top_clients_orders': json.dumps(top_clients_orders),

        # Indicadores Financeiros
        'total_revenue': float(total_revenue),
        'monthly_revenue': float(monthly_revenue),
        'avg_ticket': float(avg_ticket),
        'pending_revenue': float(pending_revenue),
        'monthly_revenue_labels': json.dumps(monthly_revenue_labels),
        'monthly_revenue_data': json.dumps(monthly_revenue_data),

        # Métricas de Pedidos para Cards 1 e 2
        'orders_avg_years': round(orders_avg_years, 1),
        'orders_avg_months': round(orders_avg_months, 1),
    }

    return render(request, 'dashboard/admin_dashboard.html', context)


@login_required
def provider_dashboard(request):
    """
    Dashboard para Prestador (Tech).
    - Pr?ximas OS atribu?das
    - Minha avalia??o m?dia
    - OS pendentes/em andamento
    """
    try:
        provider_profile = request.user.provider_profile
    except Exception:
        # Usu?rio n?o tem perfil de prestador
        return render(request, 'dashboard/error.html', {
            'message': 'Voc? n?o possui perfil de prestador.'
        })

    # OS atribu?das ao prestador
    my_orders = WorkOrder.objects.filter(
        provider=provider_profile,
        is_active=True
    ).select_related('client', 'status', 'service_type').order_by('scheduled_date')

    # Pr?ximas OS (futuras ou sem data)
    upcoming_orders = my_orders.filter(
        Q(scheduled_date__gte=timezone.now().date()) | Q(scheduled_date__isnull=True),
        status__group_code__in=['OPEN', 'IN_PROGRESS']
    )[:5]

    # OS em andamento
    in_progress_orders = my_orders.filter(status__status_code='IN_EXECUTION')

    # Minha avalia??o m?dia
    my_avg_rating = WorkOrderEvaluation.objects.filter(
        work_order__provider=provider_profile
    ).aggregate(avg=Avg('rating'))['avg'] or 0

    # Total de OS conclu?das
    completed_count = my_orders.filter(
        status__status_code__in=['COMPLETED', 'FINANCIAL_CLOSED']
    ).count()

    context = {
        'upcoming_orders': upcoming_orders,
        'in_progress_orders': in_progress_orders,
        'my_avg_rating': round(my_avg_rating, 1),
        'completed_count': completed_count,
        'total_orders': my_orders.count(),
    }

    return render(request, 'dashboard/provider_dashboard.html', context)


@login_required
def customer_dashboard(request):
    """
    Dashboard para Cliente (Customer).
    - OS ativas
    - ?ltimas OS
    - Avalia??es pendentes
    """
    try:
        client_profile = request.user.client_profile
    except Exception:
        return render(request, 'dashboard/error.html', {
            'message': 'Voc? n?o possui perfil de cliente.'
        })

    # Minhas OS
    my_orders = WorkOrder.objects.filter(
        client=client_profile,
        is_active=True
    ).select_related('provider', 'status', 'service_type').order_by('-created_at')

    # OS ativas (n?o conclu?das/canceladas)
    active_orders = my_orders.exclude(
        status__status_code__in=['COMPLETED', 'FINANCIAL_CLOSED', 'CANCELED']
    )

    # ?ltimas 5 OS
    recent_orders = my_orders[:5]

    # OS conclu?das sem avalia??o
    pending_evaluations = my_orders.filter(
        status__status_code__in=['COMPLETED', 'FINANCIAL_CLOSED'],
    ).exclude(
        evaluation__isnull=False
    )[:3]

    context = {
        'active_orders': active_orders,
        'recent_orders': recent_orders,
        'pending_evaluations': pending_evaluations,
    }

    return render(request, 'dashboard/customer_dashboard.html', context)


@login_required
def operational_dashboard(request):
    """
    Dashboard para Operacional.
    Foco em OS, SLA, prestadores e agendamentos (sem indicadores financeiros detalhados).
    """
    # Reutiliza a maior parte da lógica do admin_dashboard, mas remove indicadores financeiros

    # ============= KPIs DO TOPO (5 CARDS) =============
    total_orders = WorkOrder.objects.filter(is_active=True).count()

    current_year = timezone.now().year
    previous_year = current_year - 1
    orders_current_year = WorkOrder.objects.filter(created_at__year=current_year).count()
    orders_previous_year = WorkOrder.objects.filter(created_at__year=previous_year).count()
    if orders_previous_year > 0:
        orders_growth_percent = round(((orders_current_year - orders_previous_year) / orders_previous_year) * 100, 1)
    else:
        orders_growth_percent = None

    today = timezone.localdate()
    month_start = today.replace(day=1)
    prev_month_end = month_start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)
    orders_current_month = WorkOrder.objects.filter(created_at__date__gte=month_start).count()
    orders_previous_month = WorkOrder.objects.filter(created_at__date__gte=prev_month_start, created_at__date__lte=prev_month_end).count()
    if orders_previous_month > 0:
        orders_month_growth_percent = round(((orders_current_month - orders_previous_month) / orders_previous_month) * 100, 1)
    else:
        orders_month_growth_percent = None

    # Contar por status
    status_counts = WorkOrder.objects.filter(is_active=True).values(
        'status__group_code'
    ).annotate(count=Count('id'))
    status_dict = {item['status__group_code']: item['count'] for item in status_counts}

    pending_count = status_dict.get('OPEN', 0)
    in_progress_count = status_dict.get('IN_PROGRESS', 0)
    waiting_approval_count = status_dict.get('VALIDATION', 0)
    completed_count = status_dict.get('CLOSED', 0)

    # ============= TOP PRESTADORES =============
    top_providers = Provider.objects.filter(
        rating_count__gt=0
    ).order_by('-rating_avg')[:5]

    top_providers_names = [p.full_name for p in top_providers]
    top_providers_ratings = [float(p.rating_avg) if p.rating_avg else 0 for p in top_providers]

    # ============= VELOCÍMETROS (3 KPIs Circulares) =============
    completed_orders = WorkOrder.objects.filter(
        status__status_code__in=['COMPLETED', 'FINANCIAL_CLOSED'],
        finished_at__isnull=False,
        scheduled_date__isnull=False
    )
    on_time_count = 0
    for order in completed_orders:
        deadline = datetime.combine(order.scheduled_date, datetime.min.time()) + timedelta(days=1)
        if order.finished_at.replace(tzinfo=None) <= deadline:
            on_time_count += 1

    completion_rate = (on_time_count / completed_orders.count() * 100) if completed_orders.count() > 0 else 0
    on_time_rate = round(completion_rate, 1)

    avg_satisfaction = WorkOrderEvaluation.objects.aggregate(Avg('rating'))['rating__avg'] or 0
    satisfaction_percent = round((avg_satisfaction / 5 * 100), 1)

    orders_with_time = WorkOrder.objects.filter(
        real_time_minutes__isnull=False,
        estimated_time_minutes__isnull=False,
        estimated_time_minutes__gt=0
    )
    if orders_with_time.exists():
        avg_real = orders_with_time.aggregate(Avg('real_time_minutes'))['real_time_minutes__avg']
        avg_estimated = orders_with_time.aggregate(Avg('estimated_time_minutes'))['estimated_time_minutes__avg']
        time_efficiency = round((avg_estimated / avg_real * 100), 1) if avg_real > 0 else 100
    else:
        time_efficiency = 50

    # ============= PRÓXIMAS OS AGENDADAS =============
    upcoming_orders = WorkOrder.objects.filter(
        scheduled_date__gte=timezone.localdate(),
        is_active=True
    ).exclude(
        status__status_code__in=['COMPLETED', 'FINANCIAL_CLOSED', 'CANCELED']
    ).select_related('client', 'provider', 'service_type').order_by('scheduled_date')[:5]

    # ============= TOP SERVIÇOS =============
    top_services = WorkOrder.objects.filter(
        service_type__isnull=False
    ).values('service_type__name').annotate(
        total=Count('id')
    ).order_by('-total')[:5]
    top_services_labels = [item['service_type__name'] for item in top_services]
    top_services_counts = [item['total'] for item in top_services]

    # ============= ATENDIMENTOS POR MÊS =============
    months = []
    for i in range(11, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        months.append((year, month))

    total_daily_counts = []
    completed_daily_counts = []
    daily_labels = []

    for year, month in months:
        month_start = datetime(year, month, 1)
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        month_end = next_month - timedelta(days=1)

        total_daily_counts.append(
            WorkOrder.objects.filter(created_at__date__gte=month_start.date(), created_at__date__lte=month_end.date()).count()
        )
        completed_daily_counts.append(
            WorkOrder.objects.filter(
                created_at__date__gte=month_start.date(),
                created_at__date__lte=month_end.date(),
                status__status_code__in=['COMPLETED', 'FINANCIAL_CLOSED']
            ).count()
        )
        daily_labels.append(month_start.strftime('%b/%y'))

    context = {
        'total_orders': total_orders,
        'orders_current_year': orders_current_year,
        'orders_previous_year': orders_previous_year,
        'orders_growth_percent': orders_growth_percent,
        'current_year': current_year,
        'previous_year': previous_year,
        'orders_current_month': orders_current_month,
        'orders_previous_month': orders_previous_month,
        'orders_month_growth_percent': orders_month_growth_percent,
        'current_month_label': today.strftime('%m/%Y'),
        'previous_month_label': prev_month_start.strftime('%m/%Y'),
        'pending_count': pending_count,
        'in_progress_count': in_progress_count,
        'waiting_approval_count': waiting_approval_count,
        'completed_count': completed_count,
        'completion_rate': round(completion_rate, 1),
        'completion_rate_json': json.dumps(round(completion_rate, 1)),
        'top_providers_names': json.dumps(top_providers_names),
        'top_providers_ratings': json.dumps(top_providers_ratings),
        'on_time_rate': on_time_rate,
        'on_time_rate_json': json.dumps(on_time_rate),
        'satisfaction_percent': satisfaction_percent,
        'satisfaction_percent_json': json.dumps(satisfaction_percent),
        'time_efficiency': time_efficiency,
        'time_efficiency_json': json.dumps(time_efficiency),
        'upcoming_orders': upcoming_orders,
        'daily_labels': json.dumps(daily_labels),
        'daily_counts': json.dumps(total_daily_counts),
        'daily_completed_counts': json.dumps(completed_daily_counts),
        'top_services_labels': json.dumps(top_services_labels),
        'top_services_counts': json.dumps(top_services_counts),
    }

    return render(request, 'dashboard/operational_dashboard.html', context)


@login_required
def financial_dashboard(request):
    """
    Dashboard para Financeiro.
    Foco em indicadores financeiros consolidados (TODAS as transações).
    """
    from django.db.models import Sum

    # ============= KPIs FINANCEIROS (4 CARDS) =============

    # Receita total (todas as transações de receita realizadas)
    total_receitas_realizadas = Transaction.objects.filter(
        tipo='receita',
        status='realizado'
    ).aggregate(Sum('valor'))['valor__sum'] or Decimal('0.00')

    # Despesas totais (todas as transações de despesa realizadas)
    total_despesas_realizadas = Transaction.objects.filter(
        tipo='despesa',
        status='realizado'
    ).aggregate(Sum('valor'))['valor__sum'] or Decimal('0.00')

    # Saldo consolidado
    saldo_consolidado = total_receitas_realizadas - total_despesas_realizadas

    # Contas em atraso (todas as transações atrasadas)
    contas_atrasadas = Transaction.objects.filter(
        status='atrasado'
    ).aggregate(Sum('valor'))['valor__sum'] or Decimal('0.00')

    # ============= FLUXO DE CAIXA MENSAL (últimos 6 meses) =============
    today = timezone.localdate()
    monthly_labels = []
    monthly_receitas = []
    monthly_despesas = []
    monthly_saldo = []

    for i in range(5, -1, -1):
        month = today.month - i
        year = today.year
        while month <= 0:
            month += 12
            year -= 1

        month_start = datetime(year, month, 1)
        if month == 12:
            month_end = datetime(year, 12, 31)
        else:
            month_end = datetime(year, month + 1, 1) - timedelta(days=1)

        receitas = Transaction.objects.filter(
            tipo='receita',
            data_vencimento__gte=month_start,
            data_vencimento__lte=month_end
        ).aggregate(Sum('valor'))['valor__sum'] or Decimal('0.00')

        despesas = Transaction.objects.filter(
            tipo='despesa',
            data_vencimento__gte=month_start,
            data_vencimento__lte=month_end
        ).aggregate(Sum('valor'))['valor__sum'] or Decimal('0.00')

        monthly_labels.append(month_start.strftime('%b/%y'))
        monthly_receitas.append(float(receitas))
        monthly_despesas.append(float(despesas))
        monthly_saldo.append(float(receitas - despesas))

    # ============= CONTAS EM ATRASO (lista) =============
    contas_em_atraso_list = Transaction.objects.filter(
        status='atrasado'
    ).select_related('account', 'category').order_by('data_vencimento')[:10]

    # ============= TOP CLIENTES POR FATURAMENTO =============
    # Receita das OS concluídas por cliente
    top_clients = WorkOrder.objects.filter(
        status__status_code__in=['COMPLETED', 'FINANCIAL_CLOSED'],
        client__isnull=False,
        labor_cost__isnull=False
    ).values('client__full_name').annotate(
        revenue=Sum('labor_cost')
    ).order_by('-revenue')[:10]

    top_clients_labels = [item['client__full_name'] for item in top_clients]
    top_clients_values = [float(item['revenue']) for item in top_clients]

    # ============= CONTEXT FINAL =============
    context = {
        'total_receitas': float(total_receitas_realizadas),
        'total_despesas': float(total_despesas_realizadas),
        'saldo_consolidado': float(saldo_consolidado),
        'contas_atrasadas': float(contas_atrasadas),
        'monthly_labels': json.dumps(monthly_labels),
        'monthly_receitas': json.dumps(monthly_receitas),
        'monthly_despesas': json.dumps(monthly_despesas),
        'monthly_saldo': json.dumps(monthly_saldo),
        'contas_em_atraso_list': contas_em_atraso_list,
        'top_clients_labels': json.dumps(top_clients_labels),
        'top_clients_values': json.dumps(top_clients_values),
    }

    return render(request, 'dashboard/financial_dashboard.html', context)


@login_required
def service_x(request):
    """
    Página Serviço X: reúne estrutura de custos, precificação, simulador e alertas de SLA/A margem.
    """
    top_services = WorkOrder.objects.filter(service_type__isnull=False).values(
        'service_type', 'service_type__name'
    ).annotate(total=Count('id')).order_by('-total')[:4]

    service_ids = [item['service_type'] for item in top_services if item['service_type']]
    services = ServiceType.objects.filter(id__in=service_ids).prefetch_related('service_costs__cost_item')
    service_map = {str(service.id): service for service in services}

    palette = ['#7C3AED', '#8B5CF6', '#A78BFA', '#4F46E5']
    price_composition = []
    for idx, record in enumerate(top_services):
        service = service_map.get(str(record['service_type']))
        if not service:
            continue
        preview = simulate_service_pricing(service)
        price_composition.append({
            'label': service.name,
            'orders': record['total'],
            'price_display': f'R$ {preview["price"]:.2f}',
            'margin_display': f'{preview["margin_rate"]:.1f}%',
            'direct_cost_display': f'R$ {preview["direct_cost"]:.2f}',
            'profit_display': f'R$ {preview["profit"]:.2f}',
            'color': palette[idx % len(palette)],
            'trend': preview['profit_margin_pct']
        })

    active_orders = WorkOrder.objects.filter(
        is_active=True
    ).exclude(status__status_code__in=['COMPLETED', 'FINANCIAL_CLOSED', 'CANCELED']).select_related(
        'client', 'provider', 'service_type', 'status'
    )

    risk_alerts = []
    for order in active_orders:
        sla_status = get_sla_status(order)
        if sla_status not in ['red', 'yellow']:
            continue
        hours_remaining = round(calculate_sla_hours(order), 1)
        risk_alerts.append({
            'code': order.code,
            'client': order.client.full_name if order.client else 'Não informado',
            'service': order.service_type.name if order.service_type else 'Sem tipo',
            'provider': order.provider.full_name if order.provider else 'A definir',
            'sla_status': sla_status,
            'sla_color': get_sla_color_hex(sla_status),
            'hours': hours_remaining,
            'status_name': order.status.status_name,
        })

    dre_revenue = Transaction.objects.filter(tipo='receita').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    dre_expense = Transaction.objects.filter(tipo='despesa').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    dre_net = dre_revenue - dre_expense
    dre_margin = (dre_net / dre_revenue * Decimal('100')) if dre_revenue > Decimal('0.00') else Decimal('0.00')

    dre_monthly_labels = []
    dre_monthly_data = []
    today = timezone.localdate()
    for offset in range(5, -1, -1):
        check_month = today.month - offset
        check_year = today.year
        while check_month <= 0:
            check_month += 12
            check_year -= 1
        start = datetime(check_year, check_month, 1)
        if check_month == 12:
            end = datetime(check_year + 1, 1, 1)
        else:
            end = datetime(check_year, check_month + 1, 1)
        revenue = Transaction.objects.filter(
            tipo='receita',
            data_vencimento__gte=start,
            data_vencimento__lt=end
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        expense = Transaction.objects.filter(
            tipo='despesa',
            data_vencimento__gte=start,
            data_vencimento__lt=end
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        dre_monthly_labels.append(start.strftime('%b/%y'))
        dre_monthly_data.append(float(revenue - expense))

    context = {
        'price_composition': price_composition,
        'risk_alerts': risk_alerts,
        'dre_summary': {
            'revenue': float(dre_revenue),
            'expense': float(dre_expense),
            'net': float(dre_net),
            'margin_pct': float(dre_margin),
        },
        'dre_monthly_labels': json.dumps(dre_monthly_labels),
        'dre_monthly_data': json.dumps(dre_monthly_data),
        'dre_alert_flag': dre_net < Decimal('0.00'),
    }
    return render(request, 'dashboard/service_x.html', context)


@login_required
def mapa_sla_api(request):
    """
    API endpoint para o Mapa de SLA / Risco Operacional.
    Retorna dados de OS ativas (pendentes + em andamento) com classificação de SLA semafórica.
    """
    from django.http import JsonResponse
    from workorder.sla_utils import calculate_sla_hours, get_sla_status, get_sla_color_hex, get_mock_coordinates

    # Somente admin/operational podem acessar
    if not (request.user.is_superuser or request.user.is_staff or request.user.role in ['admin', 'operational']):
        return JsonResponse({'error': 'Acesso negado'}, status=403)

    # Filtros opcionais
    service_type_id = request.GET.get('service_type')
    provider_id = request.GET.get('provider')
    status_name = request.GET.get('status')
    sla_status_filter = request.GET.get('sla_status')  # 'green', 'yellow', 'red'

    # Query base: apenas OS ativas (não concluídas/canceladas)
    queryset = WorkOrder.objects.filter(
        is_active=True
    ).exclude(
        status__status_code__in=['COMPLETED', 'FINANCIAL_CLOSED', 'CANCELED'],
    ).select_related(
        'client', 'provider', 'service_type', 'status', 'insurance_company', 'service_operator'
    )

    # Aplicar filtros
    if service_type_id:
        queryset = queryset.filter(service_type_id=service_type_id)

    if provider_id:
        queryset = queryset.filter(provider_id=provider_id)

    if status_name:
        queryset = queryset.filter(status__status_code=status_name)

    # Preparar dados para o mapa
    map_data = []

    for order in queryset:
        # Calcular SLA
        sla_hours = calculate_sla_hours(order)
        sla_status = get_sla_status(order)

        # Filtrar por status de SLA se especificado
        if sla_status_filter and sla_status != sla_status_filter:
            continue

        # Obter coordenadas (lat/lng do endereço ou mock)
        if order.latitude is not None and order.longitude is not None:
            coords = {'lat': float(order.latitude), 'lng': float(order.longitude)}
        else:
            client_id = getattr(order, "client_id", None)
            coords_seed = client_id if client_id is not None else order.id
            coords = get_mock_coordinates(coords_seed)

        # Dados do ponto
        point_data = {
            'id': str(order.id),
            'code': order.code,
            'lat': coords['lat'],
            'lng': coords['lng'],
            'client_name': order.client.full_name if order.client else 'NAO INFORMADO',
            'provider_name': order.provider.full_name if order.provider else 'Não atribuído',
            'service_type': order.service_type.name,
            'address': order.address if order.address else '',
            'insurance_company': order.insurance_company.name if order.insurance_company else '',
            'service_operator': order.service_operator.name if order.service_operator else '',
            'technical_report': order.technical_report if order.technical_report else '',
            'actions': order.actions if order.actions else '',
            'status': order.status.status_name,
            'sla_hours_remaining': round(sla_hours, 1),
            'sla_status': sla_status,
            'color': get_sla_color_hex(sla_status),
            'created_at': order.created_at.strftime('%d/%m/%Y %H:%M'),
        }

        map_data.append(point_data)

    return JsonResponse({
        'success': True,
        'count': len(map_data),
        'data': map_data
    })

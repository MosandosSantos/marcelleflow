"""
Views para gerenciamento de Ordens de Serviço.
Implementa CRUD completo com controle de acesso por role.
"""
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.db import transaction as db_transaction
from django.db.models import Q
from django.utils import timezone
from datetime import date, timedelta
import calendar
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.utils.text import slugify
import uuid
import re
import urllib.request
import json

from .models import WorkOrder, WorkOrderEvaluation
from .forms import WorkOrderForm, WorkOrderFilterForm, WorkOrderEvaluationForm
from workorderstatus.models import ServiceOrderStatus
from servicetype.models import ServiceType
from clients.models import Client
from workorderhistory.models import WorkOrderHistory
from accounts.mixins import IsAdminOrOperationalMixin, IsAdminMixin, IsWorkOrderReadOnlyMixin
from finance.models import Transaction


class WorkOrderListView(LoginRequiredMixin, IsWorkOrderReadOnlyMixin, ListView):
    """
    Listagem de todas as OS para admin/operadores.
    Inclui busca e filtros.
    """
    model = WorkOrder
    template_name = 'workorder/list.html'
    context_object_name = 'orders'
    paginate_by = 20

    def get_filtered_queryset(self):
        queryset = WorkOrder.objects.filter(
            is_active=True
        ).select_related(
            'client', 'provider', 'status', 'service_type'
        ).order_by('-created_at')

        # Filtros
        search = self.request.GET.get('search')
        status_id = self.request.GET.get('status')
        service_type_id = self.request.GET.get('service_type')
        operator_id = self.request.GET.get('service_operator')
        insurance_id = self.request.GET.get('insurance_company')
        filter_open = self.request.GET.get('status_open')
        filter_in_progress = self.request.GET.get('status_in_progress')
        filter_closed = self.request.GET.get('status_closed')

        if search:
            queryset = queryset.filter(
                Q(code__icontains=search) |
                Q(client__full_name__icontains=search) |
                Q(provider__full_name__icontains=search)
            )

        if status_id:
            queryset = queryset.filter(status_id=status_id)

        if service_type_id:
            queryset = queryset.filter(service_type_id=service_type_id)
        if operator_id:
            queryset = queryset.filter(service_operator_id=operator_id)
        if insurance_id:
            queryset = queryset.filter(insurance_company_id=insurance_id)

        status_groups = []
        if filter_open:
            status_groups.append('OPEN')
        if filter_in_progress:
            status_groups.append('IN_PROGRESS')
        if filter_closed:
            status_groups.extend(['CLOSED', 'VALIDATION'])
        if status_groups:
            queryset = queryset.filter(status__group_code__in=status_groups)

        return queryset

    def get_queryset(self):
        return self.get_filtered_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = WorkOrderFilterForm(self.request.GET)
        context['current_query'] = self.request.GET.urlencode()
        context['can_manage'] = self.request.user.is_superuser or self.request.user.role == 'admin'

        summary_qs = self.get_filtered_queryset()
        context['summary_stats'] = {
            'total': summary_qs.count(),
            'open': summary_qs.filter(status__group_code='OPEN').count(),
            'in_progress': summary_qs.filter(status__group_code='IN_PROGRESS').count(),
            'closed': summary_qs.filter(status__group_code__in=['CLOSED', 'VALIDATION']).count(),
            'unscheduled': summary_qs.filter(scheduled_date__isnull=True).count(),
        }
        return context


class WorkOrderCalendarView(WorkOrderListView):
    """
    Visualização em calendário para OS (admin/operadores).
    """
    template_name = 'workorder/calendar.html'
    paginate_by = None

    def _get_month_year(self):
        today = timezone.localdate()
        try:
            year = int(self.request.GET.get('year', today.year))
            month = int(self.request.GET.get('month', today.month))
        except (TypeError, ValueError):
            return today.year, today.month
        if month < 1 or month > 12:
            month = today.month
        return year, month

    def get_queryset(self):
        base_qs = self.get_filtered_queryset()
        year, month = self._get_month_year()
        last_day = calendar.monthrange(year, month)[1]
        start_date = date(year, month, 1)
        end_date = date(year, month, last_day)
        self._calendar_range = (start_date, end_date)
        self._unscheduled_orders = base_qs.filter(scheduled_date__isnull=True)
        return base_qs.filter(scheduled_date__range=(start_date, end_date))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year, month = self._get_month_year()
        start_date, end_date = getattr(self, '_calendar_range', (None, None))

        cal = calendar.Calendar(firstweekday=0)
        weeks = cal.monthdatescalendar(year, month)

        orders_by_day = {}
        for order in context['orders']:
            if order.scheduled_date:
                orders_by_day.setdefault(order.scheduled_date, []).append(order)

        calendar_weeks = []
        today = timezone.localdate()
        for week in weeks:
            week_days = []
            for day in week:
                week_days.append({
                    'date': day,
                    'in_month': day.month == month,
                    'is_today': day == today,
                    'orders': orders_by_day.get(day, []),
                })
            calendar_weeks.append(week_days)

        month_labels = [
            'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ]
        month_label = month_labels[month - 1]

        prev_month = month - 1
        prev_year = year
        if prev_month == 0:
            prev_month = 12
            prev_year -= 1
        next_month = month + 1
        next_year = year
        if next_month == 13:
            next_month = 1
            next_year += 1

        base_qs = self.get_filtered_queryset()
        month_qs = base_qs.filter(scheduled_date__range=(start_date, end_date))
        unscheduled_qs = base_qs.filter(scheduled_date__isnull=True)

        context.update({
            'calendar_weeks': calendar_weeks,
            'unscheduled_orders': getattr(self, '_unscheduled_orders', []),
            'calendar_month': month,
            'calendar_year': year,
            'calendar_month_label': month_label,
            'calendar_prev_month': prev_month,
            'calendar_prev_year': prev_year,
            'calendar_next_month': next_month,
            'calendar_next_year': next_year,
            'calendar_start_date': start_date,
            'calendar_end_date': end_date,
            'calendar_month_choices': [
                {'value': i + 1, 'label': month_labels[i]} for i in range(12)
            ],
            'calendar_year_choices': [year - 1, year, year + 1],
            'calendar_stats': {
                'month_total': month_qs.count(),
                'month_open': month_qs.filter(status__group_code='OPEN').count(),
                'month_in_progress': month_qs.filter(status__group_code='IN_PROGRESS').count(),
                'month_closed': month_qs.filter(status__group_code__in=['CLOSED', 'VALIDATION']).count(),
                'unscheduled': unscheduled_qs.count(),
            },
        })
        query_params = self.request.GET.copy()
        for key in ['month', 'year', 'page']:
            query_params.pop(key, None)
        context['calendar_query_tail'] = query_params.urlencode()
        return context


class WorkOrderKanbanView(WorkOrderListView):
    """
    Visualização em quadro Kanban para OS (admin/operadores).
    """
    template_name = 'workorder/kanban.html'
    paginate_by = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        orders = self.get_filtered_queryset()

        columns = [
            {
                'key': 'OPEN',
                'title': 'Abertas',
                'description': 'Pendentes de execução',
                'accent': 'border-yellow-400 text-yellow-700 bg-yellow-50',
            },
            {
                'key': 'IN_PROGRESS',
                'title': 'Em andamento',
                'description': 'Serviços em execução',
                'accent': 'border-blue-400 text-blue-700 bg-blue-50',
            },
            {
                'key': 'CLOSED',
                'title': 'Finalizadas',
                'description': 'Concluídas / encerradas',
                'accent': 'border-green-400 text-green-700 bg-green-50',
            },
            {
                'key': 'VALIDATION',
                'title': 'Validação',
                'description': 'Aguardando validação',
                'accent': 'border-purple-400 text-purple-700 bg-purple-50',
            },
            {
                'key': 'OTHER',
                'title': 'Outros',
                'description': 'Status alternativos',
                'accent': 'border-gray-300 text-gray-700 bg-gray-50',
            },
        ]

        orders_by_group = {col['key']: [] for col in columns}
        for order in orders:
            group = order.status.group_code if order.status else 'OTHER'
            if group not in orders_by_group:
                group = 'OTHER'
            orders_by_group[group].append(order)

        for col in columns:
            col['orders'] = orders_by_group.get(col['key'], [])
            col['count'] = len(col['orders'])

        context['kanban_columns'] = columns
        return context


class WorkOrderDetailView(LoginRequiredMixin, IsWorkOrderReadOnlyMixin, DetailView):
    """
    Detalhes de uma OS.
    Acessível por todos os usuários autenticados (com validação de permissão).
    """
    model = WorkOrder
    template_name = 'workorder/detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        return WorkOrder.objects.select_related(
            'client', 'provider', 'status', 'service_type',
            'insurance_company', 'service_operator'
        ).prefetch_related('history')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.object
        user = self.request.user

        # Verificar permissão de acesso
        has_permission = False
        if user.is_superuser or user.role in ['admin', 'operational', 'financial']:
            has_permission = True
        elif user.role == 'tech':
            try:
                has_permission = order.provider and order.provider == user.provider_profile
            except Exception:
                pass
        elif user.role == 'customer':
            try:
                has_permission = order.client and order.client == user.client_profile
            except Exception:
                pass

        if not has_permission:
            context['access_denied'] = True
            return context

        # Histórico
        context['history'] = order.history.all().order_by('-created_at')

        # Avaliação
        try:
            context['evaluation'] = order.evaluation
        except WorkOrderEvaluation.DoesNotExist:
            context['evaluation'] = None

        # Cliente pode avaliar
        context['can_evaluate'] = (
            user.role == 'customer' and
            order.status.status_code in ['COMPLETED', 'FINANCIAL_CLOSED'] and
            not context['evaluation']
        )

        # Prestador pode iniciar/concluir
        if user.role == 'tech':
            try:
                if order.provider and order.provider == user.provider_profile:
                    context['can_start'] = order.status.status_code in ['CREATED', 'WAITING_SCHEDULING', 'SCHEDULED']
                    context['can_complete'] = order.status.status_code == 'IN_EXECUTION'
            except Exception:
                pass

        return context


class WorkOrderCreateView(LoginRequiredMixin, IsAdminMixin, CreateView):
    """
    Criação de nova OS por admin/operadores.
    """
    model = WorkOrder
    form_class = WorkOrderForm
    template_name = 'workorder/form.html'
    success_url = reverse_lazy('workorder:list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Garantir que o status n?o seja escolhido na cria??o
        form.fields.pop('status', None)
        return form

    def _resolve_client_from_request(self, form):
        client = form.cleaned_data.get('client')
        if client:
            return client

        name = (self.request.POST.get('client_search') or '').strip()
        name = re.sub(r'\s+', ' ', name)
        if not name:
            return None

        address_zip = (form.cleaned_data.get('address_zip') or '').strip()
        address_street = (form.cleaned_data.get('address_street') or '').strip()
        address_number = (form.cleaned_data.get('address_number') or '').strip()
        address_neighborhood = (form.cleaned_data.get('address_neighborhood') or '').strip()
        address_city = (form.cleaned_data.get('address_city') or '').strip()
        address_state = (form.cleaned_data.get('address_state') or '').strip()

        # Normaliza dados para reduzir duplicidade
        clean_zip = re.sub(r'\D', '', address_zip)
        if len(clean_zip) == 8:
            address_zip = f'{clean_zip[:5]}-{clean_zip[5:]}'
        else:
            address_zip = clean_zip or address_zip

        if not address_zip:
            form.add_error(None, 'Informe o CEP para cadastrar novo cliente.')
            return None

        existing = Client.objects.filter(
            full_name__iexact=name,
            zip_code__iexact=address_zip
        ).first()
        if existing:
            if not existing.user_id:
                User = get_user_model()
                base = slugify(existing.full_name or name) or f'cliente-{uuid.uuid4().hex[:6]}'
                email = existing.email or f'{base}-{uuid.uuid4().hex[:6]}@esferawork.local'
                username = base[:150]
                user = User.objects.create_user(email=email, password=None, username=username, role=User.ROLE_CUSTOMER)
                user.set_unusable_password()
                user.save(update_fields=['password'])
                existing.user = user
                existing.email = existing.email or email
                existing.save(update_fields=['user', 'email'])
            return existing

        User = get_user_model()
        base = slugify(name) or f'cliente-{uuid.uuid4().hex[:6]}'
        email = f'{base}-{uuid.uuid4().hex[:6]}@esferawork.local'
        username = base[:150]
        user = User.objects.create_user(email=email, password=None, username=username, role=User.ROLE_CUSTOMER)
        user.set_unusable_password()
        user.save(update_fields=['password'])

        return Client.objects.create(
            user=user,
            full_name=name,
            email=email,
            phone='0000000000',
            street=address_street,
            number=address_number,
            complement=(form.cleaned_data.get('address_complement') or '').strip(),
            neighborhood=address_neighborhood,
            city=address_city,
            state=address_state,
            zip_code=address_zip,
        )

    def form_valid(self, form):
        resolved_client = self._resolve_client_from_request(form)
        if form.errors:
            return self.form_invalid(form)
        if resolved_client:
            form.instance.client = resolved_client

        scheduled_date = form.cleaned_data.get('scheduled_date')

        service_type = form.cleaned_data.get('service_type')
        if not service_type:
            form.add_error('service_type', 'Informe o tipo de servico.')
            return self.form_invalid(form)

        status_code = 'SCHEDULED' if scheduled_date else 'WAITING_SCHEDULING'
        new_status = ServiceOrderStatus.objects.filter(status_code=status_code).first()
        if new_status:
            form.instance.status = new_status

        try:
            with db_transaction.atomic():
                response = super().form_valid(form)

                WorkOrderHistory.objects.create(
                    work_order=self.object,
                    previous_status=None,
                    new_status=self.object.status,
                    changed_by=self.request.user,
                    note=f'OS criada por {self.request.user.username}'
                )

            messages.success(self.request, f'Ordem de Servi?o {self.object.code} criada com sucesso!')
            return response
        except Exception:
            form.add_error(None, 'Falha ao salvar a OS. Tente novamente.')
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nova Ordem de Serviço'
        context['button_text'] = 'Criar OS'
        context['is_edit'] = False
        service_type_data = {}
        for st in ServiceType.objects.filter(is_active=True):
            service_type_data[str(st.id)] = {
                'valor': float(st.estimated_price or st.unit_price or 0),
            }
        context['service_type_data_json'] = json.dumps(service_type_data)
        clients_data = []
        for client in Client.objects.all().order_by('full_name'):
            clients_data.append({
                'id': str(client.id),
                'full_name': client.full_name,
                'cpf': client.cpf,
                'email': client.email,
                'phone': client.phone,
                'street': client.street,
                'number': client.number,
                'complement': client.complement,
                'neighborhood': client.neighborhood,
                'city': client.city,
                'state': client.state,
                'zip_code': client.zip_code,
            })
        context['client_autocomplete_json'] = json.dumps(clients_data)
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class WorkOrderUpdateView(LoginRequiredMixin, IsAdminMixin, UpdateView):
    """
    Edição de OS existente por admin/operadores.
    """
    model = WorkOrder
    form_class = WorkOrderForm
    template_name = 'workorder/form.html'

    def get_success_url(self):
        return reverse_lazy('workorder:list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def _resolve_client_from_request(self, form):
        client = form.cleaned_data.get('client')
        if client:
            return client

        name = (self.request.POST.get('client_search') or '').strip()
        name = re.sub(r'\s+', ' ', name)
        if not name:
            return None

        address_zip = (form.cleaned_data.get('address_zip') or '').strip()
        address_street = (form.cleaned_data.get('address_street') or '').strip()
        address_number = (form.cleaned_data.get('address_number') or '').strip()
        address_neighborhood = (form.cleaned_data.get('address_neighborhood') or '').strip()
        address_city = (form.cleaned_data.get('address_city') or '').strip()
        address_state = (form.cleaned_data.get('address_state') or '').strip()

        # Normaliza dados para reduzir duplicidade
        clean_zip = re.sub(r'\D', '', address_zip)
        if len(clean_zip) == 8:
            address_zip = f'{clean_zip[:5]}-{clean_zip[5:]}'
        else:
            address_zip = clean_zip or address_zip

        missing = []
        if not address_zip:
            missing.append('CEP')
        if not address_street:
            missing.append('Rua')
        if not address_number:
            missing.append('Numero')
        if not address_neighborhood:
            missing.append('Bairro')
        if not address_city:
            missing.append('Cidade')
        if not address_state:
            missing.append('Estado')
        if missing:
            form.add_error(None, f'Informe {", ".join(missing)} para cadastrar novo cliente.')
            return None

        existing = Client.objects.filter(
            full_name__iexact=name,
            zip_code__iexact=address_zip,
            street__iexact=address_street,
            number__iexact=address_number
        ).first()
        if existing:
            if not existing.user_id:
                User = get_user_model()
                base = slugify(existing.full_name or name) or f'cliente-{uuid.uuid4().hex[:6]}'
                email = existing.email or f'{base}-{uuid.uuid4().hex[:6]}@esferawork.local'
                username = base[:150]
                user = User.objects.create_user(email=email, password=None, username=username, role=User.ROLE_CUSTOMER)
                user.set_unusable_password()
                user.save(update_fields=['password'])
                existing.user = user
                existing.email = existing.email or email
                existing.save(update_fields=['user', 'email'])
            return existing

        User = get_user_model()
        base = slugify(name) or f'cliente-{uuid.uuid4().hex[:6]}'
        email = f'{base}-{uuid.uuid4().hex[:6]}@esferawork.local'
        username = base[:150]
        user = User.objects.create_user(email=email, password=None, username=username, role=User.ROLE_CUSTOMER)
        user.set_unusable_password()
        user.save(update_fields=['password'])

        return Client.objects.create(
            user=user,
            full_name=name,
            email=email,
            phone='0000000000',
            street=address_street,
            number=address_number,
            complement=(form.cleaned_data.get('address_complement') or '').strip(),
            neighborhood=address_neighborhood,
            city=address_city,
            state=address_state,
            zip_code=address_zip,
        )

    def form_valid(self, form):
        resolved_client = self._resolve_client_from_request(form)
        if form.errors:
            return self.form_invalid(form)
        if resolved_client:
            form.instance.client = resolved_client

        old_obj = WorkOrder.objects.get(pk=self.object.pk)
        old_scheduled_date = old_obj.scheduled_date
        new_value = form.cleaned_data.get('labor_cost')
        value_changed = old_obj.labor_cost != new_value
        if value_changed:
            if not (self.request.user.is_superuser or self.request.user.role == 'admin'):
                form.add_error('labor_cost', 'Somente administradores podem alterar o valor final.')
                return self.form_invalid(form)
            if not new_value or new_value <= 0:
                form.add_error('labor_cost', 'Informe um valor final válido.')
                return self.form_invalid(form)

        # Verificar se o status mudou
        old_status = WorkOrder.objects.get(pk=self.object.pk).status
        if old_status and old_status.is_final:
            selected_status = form.cleaned_data.get('status')
            if selected_status and selected_status != old_status:
                form.add_error('status', 'Não é possível alterar o status de uma OS encerrada.')
                return self.form_invalid(form)

        selected_status = form.cleaned_data.get('status')
        if selected_status:
            is_in_progress = (
                selected_status.group_code == 'IN_PROGRESS' or
                selected_status.status_code == 'IN_PROGRESS'
            )
            is_validation = (
                selected_status.group_code == 'VALIDATION' or
                selected_status.status_code == 'VALIDATION'
            )
            is_closed = (
                selected_status.is_final or
                selected_status.group_code == 'CLOSED'
            )

            if is_in_progress and not form.cleaned_data.get('provider'):
                form.add_error('status', 'Defina um técnico antes de colocar a OS em andamento.')
                return self.form_invalid(form)

            if is_validation and not form.cleaned_data.get('technical_report'):
                form.add_error('status', 'Informe o laudo para enviar a OS para validação.')
                return self.form_invalid(form)

            if is_closed and not form.cleaned_data.get('closed_on'):
                form.add_error('closed_on', 'Informe a data de encerramento para finalizar a OS.')
                return self.form_invalid(form)

            if is_closed and not form.instance.is_ready_to_finalize():
                form.add_error(
                    'status',
                    'Para encerrar a OS, preencha técnico, seguradora, operadora, tipo de serviço, descrição, laudo e valor.'
                )
                return self.form_invalid(form)

            new_status = selected_status
            form.instance.status = selected_status
        else:
            scheduled_date = form.cleaned_data.get('scheduled_date')
            status_code = 'SCHEDULED' if scheduled_date else 'WAITING_SCHEDULING'
            new_status = ServiceOrderStatus.objects.filter(status_code=status_code).first()
            if new_status:
                form.instance.status = new_status
            else:
                new_status = old_status

        with db_transaction.atomic():
            response = super().form_valid(form)

            if value_changed:
                Transaction.objects.filter(work_order=self.object, is_installment=False).update(valor=new_value)

            new_scheduled_date = form.cleaned_data.get('scheduled_date')
            if new_scheduled_date != old_scheduled_date:
                due_date = new_scheduled_date or timezone.localdate()
                Transaction.objects.filter(work_order=self.object, is_installment=False).update(data_vencimento=due_date)

            # Criar histórico se status mudou
            if old_status != new_status:
                WorkOrderHistory.objects.create(
                    work_order=self.object,
                    previous_status=old_status,
                    new_status=new_status,
                    changed_by=self.request.user,
                    note=f'Status alterado de "{old_status.status_name}" para "{new_status.status_name}"'
                )

        messages.success(self.request, f'Ordem de Serviço {self.object.code} atualizada com sucesso!')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Editar OS {self.object.code}'
        context['button_text'] = 'Salvar Alterações'
        context['is_edit'] = True
        service_type_data = {}
        for st in ServiceType.objects.filter(is_active=True):
            service_type_data[str(st.id)] = {
                'valor': float(st.estimated_price or st.unit_price or 0),
            }
        context['service_type_data_json'] = json.dumps(service_type_data)
        clients_data = []
        for client in Client.objects.all().order_by('full_name'):
            clients_data.append({
                'id': str(client.id),
                'full_name': client.full_name,
                'cpf': client.cpf,
                'email': client.email,
                'phone': client.phone,
                'street': client.street,
                'number': client.number,
                'complement': client.complement,
                'neighborhood': client.neighborhood,
                'city': client.city,
                'state': client.state,
                'zip_code': client.zip_code,
            })
        context['client_autocomplete_json'] = json.dumps(clients_data)
        return context


@login_required
def my_orders_view(request):
    """
    Lista de OS do prestador logado (role=tech).
    """
    if request.user.role != 'tech':
        messages.error(request, 'Você não tem permissão para acessar esta página.')
        return redirect('dashboard')

    try:
        provider_profile = request.user.provider_profile
    except:
        messages.error(request, 'Perfil de prestador não encontrado.')
        return redirect('dashboard')

    orders = WorkOrder.objects.filter(
        provider=provider_profile,
        is_active=True
    ).select_related('client', 'status', 'service_type').order_by('-created_at')

    # Filtro por status
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status__name=status_filter)

    context = {
        'orders': orders,
        'status_filter': status_filter,
    }

    return render(request, 'workorder/my_orders.html', context)


@login_required
def my_requests_view(request):
    """
    Lista de solicitações do cliente logado (role=customer).
    """
    if request.user.role != 'customer':
        messages.error(request, 'Você não tem permissão para acessar esta página.')
        return redirect('dashboard')

    try:
        client_profile = request.user.client_profile
    except:
        messages.error(request, 'Perfil de cliente não encontrado.')
        return redirect('dashboard')

    orders = WorkOrder.objects.filter(
        client=client_profile,
        is_active=True
    ).select_related('provider', 'status', 'service_type').order_by('-created_at')

    context = {
        'orders': orders,
    }

    return render(request, 'workorder/my_requests.html', context)


@login_required
def cep_lookup(request):
    cep = request.GET.get('cep', '')
    clean = re.sub(r'\D', '', cep or '')
    if len(clean) != 8:
        return JsonResponse({'error': 'CEP inválido'}, status=400)
    try:
        url = f'https://viacep.com.br/ws/{clean}/json/'
        with urllib.request.urlopen(url, timeout=8) as response:
            data = json.loads(response.read().decode('utf-8'))
        if data.get('erro'):
            return JsonResponse({'error': 'CEP não encontrado'}, status=404)
        return JsonResponse(data)
    except Exception:
        return JsonResponse({'error': 'Falha ao consultar CEP'}, status=502)


def _is_admin_or_operational(user):
    return user.is_superuser or user.role == 'admin'


@login_required
def delete_work_order(request, pk):
    if not _is_admin_or_operational(request.user):
        messages.error(request, 'Você não tem permissão para excluir esta OS.')
        return redirect('workorder:list')

    order = get_object_or_404(WorkOrder, pk=pk)
    can_delete = order.status.group_code == 'OPEN'

    if request.method == 'GET':
        return render(request, 'workorder/confirm_delete.html', {
            'order': order,
            'can_delete': can_delete,
        })

    if not can_delete:
        messages.error(request, 'Só é possível excluir OS na fase de abertura.')
        return redirect('workorder:list')

    try:
        order.finance_transactions.all().delete()
    except Exception:
        pass

    order.is_active = False
    order.save(update_fields=['is_active'])
    WorkOrderHistory.objects.create(
        work_order=order,
        previous_status=order.status,
        new_status=order.status,
        changed_by=request.user,
        note='OS exclu?da na fase de abertura'
    )
    messages.success(request, f'OS {order.code} exclu?da com sucesso.')
    return redirect('workorder:list')

    order.is_active = False
    order.save(update_fields=['is_active'])
    WorkOrderHistory.objects.create(
        work_order=order,
        previous_status=order.status,
        new_status=order.status,
        changed_by=request.user,
        note='OS excluída na fase de abertura'
    )
    messages.success(request, f'OS {order.code} excluída com sucesso.')
    return redirect('workorder:list')


@login_required
def cancel_work_order(request, pk):
    if not _is_admin_or_operational(request.user):
        messages.error(request, 'Você não tem permissão para cancelar esta OS.')
        return redirect('workorder:list')

    order = get_object_or_404(WorkOrder, pk=pk)
    if order.status.group_code == 'OPEN':
        messages.error(request, 'OS em abertura devem ser excluídas, não canceladas.')
        return redirect('workorder:list')

    if order.status.status_code in ['COMPLETED', 'FINANCIAL_CLOSED', 'CANCELED']:
        messages.error(request, 'Esta OS já está encerrada.')
        return redirect('workorder:list')

    canceled_status = get_object_or_404(ServiceOrderStatus, status_code='CANCELED')
    previous_status = order.status
    order.status = canceled_status
    order.save(update_fields=['status'])
    WorkOrderHistory.objects.create(
        work_order=order,
        previous_status=previous_status,
        new_status=canceled_status,
        changed_by=request.user,
        note='OS cancelada pelo painel de listagem'
    )
    messages.success(request, f'OS {order.code} cancelada com sucesso.')
    return redirect('workorder:list')


@login_required
def finalize_work_order(request, pk):
    if not _is_admin_or_operational(request.user):
        messages.error(request, 'VocÃª nÃ£o tem permissÃ£o para finalizar esta OS.')
        return redirect('workorder:list')

    order = get_object_or_404(WorkOrder, pk=pk)
    if request.method != 'POST':
        return redirect('workorder:list')

    if order.status.is_final or order.status.status_code in ['COMPLETED', 'FINANCIAL_CLOSED', 'CANCELED']:
        messages.error(request, 'Esta OS jÃ¡ estÃ¡ finalizada.')
        return redirect('workorder:list')

    if not order.is_ready_to_finalize():
        messages.error(request, 'Preencha tÃ©cnico, seguradora, gestora, tipo de serviÃ§o, descriÃ§Ã£o, laudo e valor antes de finalizar.')
        return redirect('workorder:list')

    final_status = ServiceOrderStatus.objects.filter(status_code='COMPLETED').first()
    if not final_status:
        messages.error(request, 'Status de conclusÃ£o nÃ£o encontrado no sistema.')
        return redirect('workorder:list')

    finance_tx = order.finance_transactions.filter(is_installment=False).order_by('-created_at').first()
    if not finance_tx:
        messages.error(request, 'Conta a receber nÃ£o encontrada para esta OS.')
        return redirect('workorder:list')

    try:
        with db_transaction.atomic():
            old_status = order.status
            order.status = final_status
            order.finished_at = timezone.now()
            if order.started_at:
                duration = timezone.now() - order.started_at
                order.real_time_minutes = int(duration.total_seconds() / 60)
            order.save(update_fields=['status', 'finished_at', 'real_time_minutes'])

            finance_tx.data_vencimento = timezone.localdate() - timedelta(days=1)
            finance_tx.data_pagamento = None
            observacoes = (finance_tx.observacoes or '').strip()
            if observacoes:
                observacoes += ' '
            observacoes += 'Encaminhada para cobranÃ§a.'
            finance_tx.observacoes = observacoes
            finance_tx.save()

            WorkOrderHistory.objects.create(
                work_order=order,
                previous_status=old_status,
                new_status=final_status,
                changed_by=request.user,
                note='OS finalizada e enviada para cobranÃ§a.'
            )

        messages.success(request, f'OS {order.code} finalizada e enviada para cobranÃ§a.')
    except Exception:
        messages.error(request, 'Falha ao finalizar a OS. Nenhuma alteraÃ§Ã£o foi aplicada.')

    return redirect('workorder:list')


@login_required
def start_work_order(request, pk):
    """
    Prestador inicia uma OS (muda status para 'Em Andamento').
    """
    order = get_object_or_404(WorkOrder, pk=pk)

    # Validar permissão
    if request.user.role != 'tech':
        messages.error(request, 'Apenas prestadores podem iniciar serviços.')
        return redirect('workorder:detail', pk=pk)

    try:
        if order.provider != request.user.provider_profile:
            messages.error(request, 'Esta OS não está atribuída a você.')
            return redirect('workorder:detail', pk=pk)
    except:
        messages.error(request, 'Perfil de prestador não encontrado.')
        return redirect('dashboard')

    # Validar status
    if order.status.status_code not in ['CREATED', 'WAITING_SCHEDULING', 'SCHEDULED']:
        messages.warning(request, 'Esta OS não está pendente.')
        return redirect('workorder:detail', pk=pk)

    # Atualizar status
    try:
        status_em_andamento = ServiceOrderStatus.objects.get(status_code='IN_EXECUTION')
        order.status = status_em_andamento
        order.started_at = timezone.now()
        order.save()

        # Criar histórico
        old_status = order.status
        WorkOrderHistory.objects.create(
            work_order=order,
            previous_status=old_status if old_status.status_code != 'IN_EXECUTION' else None,
            new_status=status_em_andamento,
            changed_by=request.user,
            note='Serviço iniciado pelo prestador'
        )

        messages.success(request, f'Serviço {order.code} iniciado com sucesso!')
    except ServiceOrderStatus.DoesNotExist:
        messages.error(request, 'Status "IN_EXECUTION" não encontrado no sistema.')

    return redirect('workorder:detail', pk=pk)


@login_required
def complete_work_order(request, pk):
    """
    Prestador conclui uma OS (muda status para 'Concluído').
    """
    order = get_object_or_404(WorkOrder, pk=pk)

    # Validar permissão
    if request.user.role != 'tech':
        messages.error(request, 'Apenas prestadores podem concluir serviços.')
        return redirect('workorder:detail', pk=pk)

    try:
        if order.provider != request.user.provider_profile:
            messages.error(request, 'Esta OS não está atribuída a você.')
            return redirect('workorder:detail', pk=pk)
    except:
        messages.error(request, 'Perfil de prestador não encontrado.')
        return redirect('dashboard')

    # Validar status
    if order.status.status_code != 'IN_EXECUTION':
        messages.warning(request, 'Esta OS não está em andamento.')
        return redirect('workorder:detail', pk=pk)

    # Atualizar status
    try:
        status_concluido = ServiceOrderStatus.objects.filter(
            name__in=['Concluído', 'Concluida']
        ).first()

        if not status_concluido:
            messages.error(request, 'Status de conclusão não encontrado no sistema.')
            return redirect('workorder:detail', pk=pk)

        order.status = status_concluido
        order.finished_at = timezone.now()

        # Calcular tempo real (se tiver started_at)
        if order.started_at:
            duration = timezone.now() - order.started_at
            order.real_time_minutes = int(duration.total_seconds() / 60)

        order.save()

        # Criar histórico
        WorkOrderHistory.objects.create(
            work_order=order,
            previous_status=ServiceOrderStatus.objects.filter(status_code='IN_EXECUTION').first(),
            new_status=status_concluido,
            changed_by=request.user,
            note='Serviço concluído pelo prestador'
        )

        messages.success(request, f'Serviço {order.code} concluído com sucesso!')
    except Exception as e:
        messages.error(request, f'Erro ao concluir serviço: {str(e)}')

    return redirect('workorder:detail', pk=pk)


@login_required
def evaluate_work_order(request, pk):
    """
    Cliente avalia uma OS concluída.
    """
    order = get_object_or_404(WorkOrder, pk=pk)

    # Validar permissão
    if request.user.role != 'customer':
        messages.error(request, 'Apenas clientes podem avaliar serviços.')
        return redirect('workorder:detail', pk=pk)

    try:
        if order.client != request.user.client_profile:
            messages.error(request, 'Esta OS não pertence a você.')
            return redirect('workorder:detail', pk=pk)
    except:
        messages.error(request, 'Perfil de cliente não encontrado.')
        return redirect('dashboard')

    # Validar status
        context['can_evaluate'] = (
            user.role == 'customer' and
            order.status.status_code in ['COMPLETED', 'FINANCIAL_CLOSED'] and
            not context['evaluation']
        )
        messages.warning(request, 'Só é possível avaliar serviços concluídos.')
        return redirect('workorder:detail', pk=pk)

    # Verificar se já foi avaliado
    if hasattr(order, 'evaluation'):
        messages.info(request, 'Esta OS já foi avaliada.')
        return redirect('workorder:detail', pk=pk)

    if request.method == 'POST':
        form = WorkOrderEvaluationForm(request.POST)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.work_order = order
            evaluation.save()

            messages.success(request, 'Avaliação enviada com sucesso! Obrigado pelo feedback.')
            return redirect('workorder:detail', pk=pk)
    else:
        form = WorkOrderEvaluationForm()

    context = {
        'form': form,
        'order': order,
    }

    return render(request, 'workorder/evaluate.html', context)

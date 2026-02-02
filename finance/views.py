from datetime import date, timedelta
from decimal import Decimal
import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction as db_transaction
from django.db.models import Q, Sum
from django.db.models.functions import TruncMonth
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View, TemplateView

from .forms import (
    AccountForm,
    CategoryForm,
    TransactionForm,
    TransactionFilterForm,
    MarkAsCompletedForm,
    WorkOrderPaymentForm,
    InstallmentInvoiceForm,
)
from .models import Account, Category, Transaction
from workorder.models import WorkOrder
from workorderstatus.models import ServiceOrderStatus
from .services import (
    build_dre_context,
    _last_day_of_month,
    build_cashflow_context,
    get_finance_queryset,
    apply_phase_filter,
)
from accounts.mixins import IsFinancialMixin


MONTH_NAMES = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
]


class AccountListView(LoginRequiredMixin, IsFinancialMixin, ListView):
    model = Account
    template_name = 'finance/account_list.html'
    context_object_name = 'accounts'

    def get_queryset(self):
        user = self.request.user
        # Financial vê TODAS as contas (consolidado)
        if user.role == 'financial':
            return Account.objects.all().order_by('nome')
        # Admin mantém filtro por usuário se necessário
        return Account.objects.filter(user=user).order_by('nome')


class AccountCreateView(LoginRequiredMixin, IsFinancialMixin, CreateView):
    model = Account
    form_class = AccountForm
    template_name = 'finance/account_form.html'
    success_url = reverse_lazy('finance:account_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Conta "{form.instance.nome}" criada com sucesso.')
        return response


class AccountUpdateView(LoginRequiredMixin, IsFinancialMixin, UpdateView):
    model = Account
    form_class = AccountForm
    template_name = 'finance/account_form.html'
    success_url = reverse_lazy('finance:account_list')

    def get_queryset(self):
        user = self.request.user
        # Financial vê TODAS as contas (consolidado)
        if user.role == 'financial':
            return Account.objects.all()
        # Admin mantém filtro por usuário
        return Account.objects.filter(user=user)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Conta "{form.instance.nome}" atualizada com sucesso.')
        return response


class AccountDeleteView(LoginRequiredMixin, IsFinancialMixin, DeleteView):
    model = Account
    template_name = 'finance/account_confirm_delete.html'
    success_url = reverse_lazy('finance:account_list')

    def get_queryset(self):
        user = self.request.user
        # Financial vê TODAS as contas (consolidado)
        if user.role == 'financial':
            return Account.objects.all()
        # Admin mantém filtro por usuário
        return Account.objects.filter(user=user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        account = self.get_object()
        context['has_transactions'] = Transaction.objects.filter(account=account).exists()
        return context

    def delete(self, request, *args, **kwargs):
        account = self.get_object()
        nome = account.nome
        try:
            response = super().delete(request, *args, **kwargs)
        except ProtectedError:
            messages.error(
                request,
                f'Nao foi possivel excluir a conta "{nome}" porque existem movimentacoes vinculadas.'
            )
            return redirect(self.success_url)
        messages.success(request, f'Conta "{nome}" excluida com sucesso.')
        return response


class CategoryListView(LoginRequiredMixin, IsFinancialMixin, ListView):
    model = Category
    template_name = 'finance/category_list.html'
    context_object_name = 'categories'
    paginate_by = 15

    def get_queryset(self):
        queryset = Category.objects.all()
        tipo = self.request.GET.get('tipo')
        if tipo in ['receita', 'despesa']:
            queryset = queryset.filter(tipo=tipo)
        return queryset.order_by('nome')


class CategoryCreateView(LoginRequiredMixin, IsFinancialMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'finance/category_form.html'
    success_url = reverse_lazy('finance:category_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Categoria "{form.instance.nome}" criada com sucesso.')
        return response


class CategoryUpdateView(LoginRequiredMixin, IsFinancialMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'finance/category_form.html'
    success_url = reverse_lazy('finance:category_list')

    def get_queryset(self):
        return Category.objects.all()

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Categoria "{form.instance.nome}" atualizada com sucesso.')
        return response


class CategoryDeleteView(LoginRequiredMixin, IsFinancialMixin, DeleteView):
    model = Category
    template_name = 'finance/category_confirm_delete.html'
    success_url = reverse_lazy('finance:category_list')

    def get_queryset(self):
        return Category.objects.all()

    def delete(self, request, *args, **kwargs):
        category = self.get_object()
        nome = category.nome
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f'Categoria "{nome}" excluida com sucesso.')
        return response


class TransactionListView(LoginRequiredMixin, IsFinancialMixin, ListView):
    model = Transaction
    template_name = 'finance/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        # Financial vê TODAS as transações (consolidado)
        if user.role == 'financial':
            queryset = Transaction.objects.all().select_related('account', 'category')
        else:
            # Admin mantém filtro por usuário
            queryset = Transaction.objects.filter(user=user).select_related('account', 'category')

        tipo = self.request.GET.get('tipo')
        if tipo:
            queryset = queryset.filter(tipo=tipo)

        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        account = self.request.GET.get('account')
        if account:
            queryset = queryset.filter(account_id=account)

        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category_id=category)

        data_inicio = self.request.GET.get('data_inicio')
        if data_inicio:
            queryset = queryset.filter(data_vencimento__gte=data_inicio)

        data_fim = self.request.GET.get('data_fim')
        if data_fim:
            queryset = queryset.filter(data_vencimento__lte=data_fim)

        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(descricao__icontains=search) |
                Q(observacoes__icontains=search)
            )

        # NOVOS FILTROS: Tipificação de Despesas
        expense_type = self.request.GET.get('expense_type')
        if expense_type:
            queryset = queryset.filter(expense_type=expense_type)

        is_recurring = self.request.GET.get('is_recurring')
        if is_recurring == 'true':
            queryset = queryset.filter(is_recurring=True)
        elif is_recurring == 'false':
            queryset = queryset.filter(is_recurring=False)

        recurrence_period = self.request.GET.get('recurrence_period')
        if recurrence_period:
            queryset = queryset.filter(recurrence_period=recurrence_period)

        payment_origin = self.request.GET.get('payment_origin')
        if payment_origin:
            queryset = queryset.filter(payment_origin=payment_origin)

        is_installment = self.request.GET.get('is_installment')
        if is_installment == 'true':
            queryset = queryset.filter(is_installment=True)
        elif is_installment == 'false':
            queryset = queryset.filter(is_installment=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = TransactionFilterForm(
            data=self.request.GET or None,
            user=self.request.user
        )

        qs = self.get_queryset().exclude(status='cancelado')
        total_receitas = qs.filter(tipo='receita', status='realizado').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        total_despesas = qs.filter(tipo='despesa').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        receitas_realizadas = qs.filter(tipo='receita', status='realizado').aggregate(
            total=Sum('valor')
        )['total'] or Decimal('0.00')
        despesas_realizadas = qs.filter(tipo='despesa', status='realizado').aggregate(
            total=Sum('valor')
        )['total'] or Decimal('0.00')
        receitas_pendentes = qs.filter(
            tipo='receita',
            status__in=['previsto', 'atrasado']
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        despesas_pendentes = qs.filter(
            tipo='despesa',
            status__in=['previsto', 'atrasado']
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

        context['stats'] = {
            'saldo_atual': receitas_realizadas - despesas_realizadas,
            'total_receitas': total_receitas,
            'total_despesas': total_despesas,
            'receitas_em_atraso': qs.filter(tipo='receita', status='atrasado').aggregate(
                total=Sum('valor')
            )['total'] or Decimal('0.00'),
            'receitas_a_receber': qs.filter(
                tipo='receita',
                status__in=['previsto', 'atrasado']
            ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00'),
            'despesas_em_atraso': qs.filter(tipo='despesa', status='atrasado').aggregate(
                total=Sum('valor')
            )['total'] or Decimal('0.00'),
            'saldo_projetado': (receitas_realizadas - despesas_realizadas) + receitas_pendentes - despesas_pendentes,
        }

        # NOVAS ESTATÍSTICAS: Breakdown por Tipo de Despesa
        despesas_qs = qs.filter(tipo='despesa', status='realizado')
        context['expense_breakdown'] = {
            'direto': despesas_qs.filter(expense_type='direto').aggregate(total=Sum('valor'))['total'] or Decimal('0.00'),
            'indireto': despesas_qs.filter(expense_type='indireto').aggregate(total=Sum('valor'))['total'] or Decimal('0.00'),
            'fixo': despesas_qs.filter(expense_type='fixo').aggregate(total=Sum('valor'))['total'] or Decimal('0.00'),
            'variavel': despesas_qs.filter(expense_type='variavel').aggregate(total=Sum('valor'))['total'] or Decimal('0.00'),
            'administrativo': despesas_qs.filter(expense_type='administrativo').aggregate(total=Sum('valor'))['total'] or Decimal('0.00'),
            'operacional': despesas_qs.filter(expense_type='operacional').aggregate(total=Sum('valor'))['total'] or Decimal('0.00'),
            'financeiro': despesas_qs.filter(expense_type='financeiro').aggregate(total=Sum('valor'))['total'] or Decimal('0.00'),
        }

        # Estatísticas de Recorrência
        context['recurring_stats'] = {
            'total_recurring': qs.filter(is_recurring=True).count(),
            'total_unique': qs.filter(is_recurring=False).count(),
            'recurring_amount': qs.filter(is_recurring=True, tipo='despesa', status='realizado').aggregate(
                total=Sum('valor')
            )['total'] or Decimal('0.00'),
        }

        return context


class TransactionCreateView(LoginRequiredMixin, IsFinancialMixin, CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = 'finance/transaction_form.html'
    success_url = reverse_lazy('finance:transaction_list')

    def _add_months(self, base_date, months):
        year = base_date.year + ((base_date.month - 1 + months) // 12)
        month = ((base_date.month - 1 + months) % 12) + 1
        day = min(base_date.day, _last_day_of_month(date(year, month, 1)).day)
        return date(year, month, day)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        tipo = self.request.GET.get('tipo')
        if tipo in dict(Transaction.TIPO_CHOICES):
            initial['tipo'] = tipo
        return initial

    def form_valid(self, form):
        form.instance.user = self.request.user
        installments = form.cleaned_data.get('installments') or 1
        if form.cleaned_data.get('tipo') == 'despesa' and installments > 1:
            return self._create_expense_installments(form, installments)
        response = super().form_valid(form)
        messages.success(self.request, f'{form.instance.get_tipo_display()} cadastrada com sucesso.')
        return response

    def _create_expense_installments(self, form, installments):
        total_amount = form.cleaned_data.get('valor') or Decimal('0.00')
        first_due_date = form.cleaned_data.get('data_vencimento')
        descricao = form.cleaned_data.get('descricao') or 'Despesa parcelada'

        base_value = (total_amount / installments).quantize(Decimal('0.01'))
        remainder = total_amount - (base_value * installments)
        installment_group_id = uuid.uuid4()

        with db_transaction.atomic():
            for idx in range(installments):
                installment_value = base_value
                if idx == installments - 1:
                    installment_value += remainder

                due_date = self._add_months(first_due_date, idx)
                Transaction.objects.create(
                    user=self.request.user,
                    tipo='despesa',
                    descricao=f'{descricao} - Parcela {idx + 1}/{installments}',
                    valor=installment_value,
                    data_vencimento=due_date,
                    data_pagamento=None,
                    account=form.cleaned_data.get('account'),
                    category=form.cleaned_data.get('category'),
                    expense_type=form.cleaned_data.get('expense_type'),
                    is_recurring=False,
                    recurrence_period='unico',
                    related_service_type=form.cleaned_data.get('related_service_type'),
                    observacoes=form.cleaned_data.get('observacoes') or '',
                    is_installment=True,
                    installment_group_id=installment_group_id,
                    installment_number=idx + 1,
                    installment_total=installments,
                )

        messages.success(self.request, f'Despesa parcelada em {installments}x criada com sucesso.')
        return redirect(self.success_url)

    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao cadastrar lancamento. Verifique os campos e tente novamente.')
        return super().form_invalid(form)


class TransactionUpdateView(LoginRequiredMixin, IsFinancialMixin, UpdateView):
    model = Transaction
    form_class = TransactionForm
    template_name = 'finance/transaction_form.html'
    success_url = reverse_lazy('finance:transaction_list')

    def get_queryset(self):
        user = self.request.user
        # Financial vê TODAS as transações (consolidado)
        if user.role == 'financial':
            return Transaction.objects.all()
        # Admin mantém filtro por usuário
        return Transaction.objects.filter(user=user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Lancamento atualizado com sucesso.')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao atualizar lancamento. Verifique os campos e tente novamente.')
        return super().form_invalid(form)


class TransactionDeleteView(LoginRequiredMixin, IsFinancialMixin, DeleteView):
    model = Transaction
    template_name = 'finance/transaction_confirm_delete.html'
    success_url = reverse_lazy('finance:transaction_list')

    def get_queryset(self):
        user = self.request.user
        # Financial vê TODAS as transações (consolidado)
        if user.role == 'financial':
            return Transaction.objects.all()
        # Admin mantém filtro por usuário
        return Transaction.objects.filter(user=user)

    def post(self, request, *args, **kwargs):
        transaction = self.get_object()
        if transaction.is_installment:
            messages.error(
                request,
                'Parcelas n?o podem ser exclu?das. Use a op??o de cancelamento.'
            )
            return redirect('finance:transaction_list')
        if transaction.status == 'realizado' and transaction.data_pagamento:
            messages.error(
                request,
                'Não é possível excluir lançamentos realizados com data de pagamento.'
            )
            return redirect('finance:transaction_list')
        return super().post(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        transaction = self.get_object()
        if transaction.is_installment:
            messages.error(
                request,
                'Parcelas n?o podem ser exclu?das. Use a op??o de cancelamento.'
            )
            return redirect('finance:transaction_list')
        if transaction.status == 'realizado' and transaction.data_pagamento:
            messages.error(
                request,
                'Não é possível excluir lançamentos realizados com data de pagamento.'
            )
            return redirect('finance:transaction_list')
        descricao = transaction.descricao
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f'Lançamento "{descricao}" excluído com sucesso.')
        return response


class TransactionMarkAsCompletedView(LoginRequiredMixin, IsFinancialMixin, View):
    template_name = 'finance/transaction_mark_completed_confirm.html'

    def get(self, request, pk):
        transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
        form = MarkAsCompletedForm()
        account = transaction.account
        account_complete = all([account.bank_code, account.agencia, account.conta_numero])
        return render(request, self.template_name, {
            'transaction': transaction,
            'form': form,
            'account_complete': account_complete,
        })

    def post(self, request, pk):
        transaction = get_object_or_404(Transaction, pk=pk, user=request.user)

        if transaction.is_projection:
            messages.error(request, 'Este lançamento é apenas uma previsão e não pode ser pago nesta fase.')
            return redirect('finance:transaction_list')

        if transaction.status == 'cancelado':
            messages.error(request, 'Este lançamento está cancelado.')
            return redirect('finance:transaction_list')

        if transaction.status == 'realizado':
            messages.warning(request, f'O lancamento "{transaction.descricao}" ja esta realizado.')
            return redirect('finance:transaction_list')

        account = transaction.account
        account_complete = all([account.bank_code, account.agencia, account.conta_numero])
        if not account_complete:
            messages.error(request, 'Informações bancárias incompletas. Atualize a conta antes de confirmar.')
            return redirect('finance:transaction_mark_completed', pk=transaction.pk)

        form = MarkAsCompletedForm(request.POST)
        if form.is_valid():
            data_pagamento = form.cleaned_data.get('data_pagamento')
            transaction.marcar_como_realizado(data_pagamento=data_pagamento)
        else:
            messages.error(request, 'Confirme as informações bancárias para continuar.')
            return redirect('finance:transaction_mark_completed', pk=transaction.pk)

        messages.success(request, f'Lancamento "{transaction.descricao}" marcado como realizado.')
        return redirect(request.POST.get('next') or 'finance:transaction_list')


class TransactionMarkAsPendingView(LoginRequiredMixin, IsFinancialMixin, View):
    def post(self, request, pk):
        transaction = get_object_or_404(Transaction, pk=pk, user=request.user)

        if transaction.status != 'realizado':
            messages.warning(request, f'O lancamento "{transaction.descricao}" nao esta realizado.')
        return redirect('finance:transaction_list')


class TransactionCancelView(LoginRequiredMixin, IsFinancialMixin, View):
    def post(self, request, pk):
        transaction = get_object_or_404(Transaction, pk=pk, user=request.user)

        if not transaction.is_installment:
            messages.error(request, 'Apenas parcelas podem ser canceladas.')
            return redirect('finance:transaction_list')

        if transaction.status == 'realizado':
            messages.error(request, 'Parcelas realizadas não podem ser canceladas.')
            return redirect('finance:transaction_list')

        transaction.cancelar()
        messages.success(request, f'Parcela "{transaction.descricao}" cancelada com sucesso.')
        return redirect('finance:transaction_list')


class FinanceDashboardView(LoginRequiredMixin, IsFinancialMixin, TemplateView):
    template_name = 'finance/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.localdate()

        if user.role == 'financial':
            qs = Transaction.objects.all().select_related('account', 'category')
            accounts_qs = Account.objects.filter(ativa=True)
        else:
            qs = Transaction.objects.filter(user=user).select_related('account', 'category')
            accounts_qs = Account.objects.filter(user=user, ativa=True)
        base_qs = qs

        categories_qs = Category.objects.filter(ativa=True).order_by('tipo', 'nome')

        params = self.request.GET
        account_id = params.get('account') or ''
        category_id = params.get('category') or ''
        status = params.get('status') or ''
        tipo = params.get('tipo') or ''

        if account_id:
            qs = qs.filter(account_id=account_id)
            accounts_qs = accounts_qs.filter(id=account_id)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if status:
            qs = qs.filter(status=status)
        if tipo:
            qs = qs.filter(tipo=tipo)

        period = params.get('period') or ''
        data_inicio = params.get('data_inicio') or ''
        data_fim = params.get('data_fim') or ''

        start_date = None
        end_date = None

        if data_inicio:
            try:
                start_date = date.fromisoformat(data_inicio)
            except ValueError:
                start_date = None
        if data_fim:
            try:
                end_date = date.fromisoformat(data_fim)
            except ValueError:
                end_date = None

        if not start_date and not end_date:
            if period not in ['today', '7d', '30d', '90d', 'year', 'custom']:
                period = '30d'
            if period == 'today':
                start_date = today
                end_date = today
            elif period == '7d':
                start_date = today - timedelta(days=6)
                end_date = today
            elif period == '90d':
                start_date = today - timedelta(days=89)
                end_date = today
            elif period == 'year':
                start_date = date(today.year, 1, 1)
                end_date = today
            else:
                start_date = today - timedelta(days=29)
                end_date = today
        else:
            if not start_date:
                start_date = today - timedelta(days=29)
            if not end_date:
                end_date = today
            if not period:
                period = 'custom'

        period_qs = qs.filter(data_vencimento__range=(start_date, end_date))

        saldo_inicial_total = accounts_qs.aggregate(total=Sum('saldo_inicial'))['total'] or Decimal('0.00')
        realized_until_end = qs.filter(status='realizado', data_vencimento__lte=end_date)
        receitas_realizadas_until = realized_until_end.filter(tipo='receita').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        despesas_realizadas_until = realized_until_end.filter(tipo='despesa').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        saldo_atual = saldo_inicial_total + receitas_realizadas_until - despesas_realizadas_until

        receitas_realizadas = period_qs.filter(tipo='receita', status='realizado').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        despesas_realizadas = period_qs.filter(tipo='despesa', status='realizado').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        receitas_a_receber = period_qs.filter(tipo='receita', status__in=['previsto', 'atrasado']).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        despesas_em_atraso = period_qs.filter(tipo='despesa', status='atrasado').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        despesas_pendentes = period_qs.filter(tipo='despesa', status__in=['previsto', 'atrasado']).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        receitas_pendentes = receitas_a_receber
        receitas_previstas_total = base_qs.filter(tipo='receita', status__in=['previsto', 'atrasado']).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        despesas_previstas_total = base_qs.filter(tipo='despesa', status__in=['previsto', 'atrasado']).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        receitas_previstas_futuras = base_qs.filter(
            tipo='receita',
            status='previsto',
            data_vencimento__gte=today
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        despesas_previstas_futuras = base_qs.filter(
            tipo='despesa',
            status='previsto',
            data_vencimento__gte=today
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

        inadimplencia_valor = period_qs.filter(tipo='receita', status='atrasado').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        total_receber = receitas_a_receber
        inadimplencia_percent = (inadimplencia_valor / total_receber * 100) if total_receber > 0 else Decimal('0.00')

        saldo_projetado = saldo_atual + receitas_pendentes - despesas_pendentes
        resultado_periodo = receitas_realizadas - despesas_realizadas

        burn_start = today - timedelta(days=29)
        burn_qs = qs.filter(data_vencimento__range=(burn_start, today), status='realizado')
        burn_receitas = burn_qs.filter(tipo='receita').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        burn_despesas = burn_qs.filter(tipo='despesa').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        burn_rate = (burn_despesas - burn_receitas) / Decimal('30')
        runway_days = None
        if burn_rate > 0 and saldo_atual > 0:
            runway_days = int(saldo_atual / burn_rate)

        # Cashflow diário
        realized_before_start = qs.filter(status='realizado', data_vencimento__lt=start_date)
        receitas_before = realized_before_start.filter(tipo='receita').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        despesas_before = realized_before_start.filter(tipo='despesa').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        running_balance = saldo_inicial_total + receitas_before - despesas_before

        daily_data = period_qs.filter(status='realizado').values('data_vencimento', 'tipo').annotate(total=Sum('valor'))
        daily_map = {}
        for item in daily_data:
            key = item['data_vencimento']
            if key not in daily_map:
                daily_map[key] = {'receita': Decimal('0.00'), 'despesa': Decimal('0.00')}
            daily_map[key][item['tipo']] = item['total'] or Decimal('0.00')

        cashflow_labels = []
        cashflow_series = []
        current_date = start_date
        while current_date <= end_date:
            net = Decimal('0.00')
            if current_date in daily_map:
                net = daily_map[current_date]['receita'] - daily_map[current_date]['despesa']
            running_balance += net
            cashflow_labels.append(current_date.strftime('%d/%m'))
            cashflow_series.append(float(running_balance))
            current_date += timedelta(days=1)

        # Receitas vs despesas por mes
        monthly_raw = period_qs.filter(status='realizado').annotate(
            month=TruncMonth('data_vencimento')
        ).values('month', 'tipo').annotate(total=Sum('valor'))
        monthly_map = {}
        for item in monthly_raw:
            month = item['month']
            if month not in monthly_map:
                monthly_map[month] = {'receita': Decimal('0.00'), 'despesa': Decimal('0.00')}
            monthly_map[month][item['tipo']] = item['total'] or Decimal('0.00')

        month_labels = []
        month_receitas = []
        month_despesas = []
        month_cursor = date(start_date.year, start_date.month, 1)
        month_end = date(end_date.year, end_date.month, 1)
        while month_cursor <= month_end:
            label = f"{MONTH_NAMES[month_cursor.month - 1][:3]}/{month_cursor.year}"
            month_labels.append(label)
            if month_cursor in monthly_map:
                month_receitas.append(float(monthly_map[month_cursor]['receita']))
                month_despesas.append(float(monthly_map[month_cursor]['despesa']))
            else:
                month_receitas.append(0)
                month_despesas.append(0)
            if month_cursor.month == 12:
                month_cursor = date(month_cursor.year + 1, 1, 1)
            else:
                month_cursor = date(month_cursor.year, month_cursor.month + 1, 1)

        # Despesas por categoria
        category_data = period_qs.filter(tipo='despesa', status='realizado').values(
            'category__nome'
        ).annotate(total=Sum('valor')).order_by('-total')[:6]
        category_labels = [item['category__nome'] or 'Sem categoria' for item in category_data]
        category_values = [float(item['total']) for item in category_data]

        # Distribuicao por conta
        account_labels = []
        account_values = []
        for account in accounts_qs:
            account_labels.append(account.nome)
            account_values.append(float(account.calcular_saldo_atual()))

        period_label = f'{start_date.strftime("%d/%m/%Y")} a {end_date.strftime("%d/%m/%Y")}'

        os_sem_nf = WorkOrder.objects.exclude(
            finance_transactions__is_installment=True
        ).filter(
            labor_cost__gt=Decimal('0.00')
        ).distinct()
        previsao_os_sem_nf = os_sem_nf.aggregate(total=Sum('labor_cost'))['total'] or Decimal('0.00')

        context['filters'] = {
            'period': period,
            'data_inicio': start_date.isoformat(),
            'data_fim': end_date.isoformat(),
            'account': account_id,
            'category': category_id,
            'status': status,
            'tipo': tipo,
        }
        context['accounts'] = accounts_qs
        context['categories'] = categories_qs
        context['period_label'] = period_label
        context['kpis'] = {
            'saldo_atual': saldo_atual,
            'saldo_projetado': saldo_projetado,
            'receitas_realizadas': receitas_realizadas,
            'despesas_realizadas': despesas_realizadas,
            'receitas_a_receber': receitas_a_receber,
            'despesas_em_atraso': despesas_em_atraso,
            'inadimplencia_valor': inadimplencia_valor,
            'inadimplencia_percent': float(inadimplencia_percent),
            'resultado_periodo': resultado_periodo,
            'runway_days': runway_days,
            'receitas_previstas_total': receitas_previstas_total,
            'despesas_previstas_total': despesas_previstas_total,
            'receitas_previstas_futuras': receitas_previstas_futuras,
            'despesas_previstas_futuras': despesas_previstas_futuras,
            'previsao_os_sem_nf': previsao_os_sem_nf,
        }
        context['chart_data'] = {
            'cashflow': {
                'labels': cashflow_labels,
                'data': cashflow_series,
            },
            'revenue_expense': {
                'labels': month_labels,
                'revenue': month_receitas,
                'expense': month_despesas,
            },
            'expense_category': {
                'labels': category_labels,
                'data': category_values,
            },
            'balance_by_account': {
                'labels': account_labels,
                'data': account_values,
            },
        }
        return context



class BillingBaseMixin:
    def _closed_orders_queryset(self):
        closed_statuses = ServiceOrderStatus.objects.filter(
            is_active=True,
            status_code__in=['COMPLETED', 'FINANCIAL_CLOSED']
        )
        return WorkOrder.objects.filter(
            status__in=closed_statuses
        ).select_related(
            'client', 'service_type', 'status', 'insurance_company', 'service_operator'
        ).order_by('-updated_at')

    def _installments_queryset(self, closed_orders):
        return Transaction.objects.filter(
            work_order__in=closed_orders,
            is_installment=True
        ).select_related('work_order', 'work_order__client', 'work_order__service_type')

    def _billing_counts(self, closed_orders, installments_qs):
        awaiting_count = installments_qs.filter(invoice_number__isnull=True).exclude(status='cancelado').count()
        open_count = installments_qs.filter(invoice_number__isnull=False).exclude(status='cancelado').exclude(status='realizado').count()
        closed_count = installments_qs.filter(invoice_number__isnull=False, status='realizado').exclude(status='cancelado').count()
        return {
            'orders_count': closed_orders.exclude(finance_transactions__is_installment=True).distinct().count(),
            'awaiting_count': awaiting_count,
            'open_count': open_count,
            'closed_count': closed_count,
        }


class BillingOrdersView(LoginRequiredMixin, IsFinancialMixin, ListView, BillingBaseMixin):
    template_name = 'finance/billing_orders.html'
    context_object_name = 'orders'
    paginate_by = 20

    def get_queryset(self):
        closed_orders = self._closed_orders_queryset()
        awaiting_orders = closed_orders.filter(finance_transactions__is_installment=True).distinct()
        return closed_orders.exclude(pk__in=awaiting_orders.values_list('pk', flat=True))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        closed_orders = self._closed_orders_queryset()
        installments_qs = self._installments_queryset(closed_orders)
        counts = self._billing_counts(closed_orders, installments_qs)
        context.update({
            'billing_counts': counts,
            'active_tab': 'os',
        })
        return context


class BillingAwaitingNFView(LoginRequiredMixin, IsFinancialMixin, ListView, BillingBaseMixin):
    template_name = 'finance/billing_awaiting_nf.html'
    context_object_name = 'installments'
    paginate_by = 20

    def get_queryset(self):
        closed_orders = self._closed_orders_queryset()
        installments_qs = self._installments_queryset(closed_orders)
        return installments_qs.filter(invoice_number__isnull=True).exclude(status='cancelado').order_by('data_vencimento', 'installment_number')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        closed_orders = self._closed_orders_queryset()
        installments_qs = self._installments_queryset(closed_orders)
        counts = self._billing_counts(closed_orders, installments_qs)
        context.update({
            'billing_counts': counts,
            'active_tab': 'awaiting',
        })
        return context


class BillingOpenNFView(LoginRequiredMixin, IsFinancialMixin, ListView, BillingBaseMixin):
    template_name = 'finance/billing_open_nf.html'
    context_object_name = 'installments'
    paginate_by = 20

    def get_queryset(self):
        closed_orders = self._closed_orders_queryset()
        installments_qs = self._installments_queryset(closed_orders)
        return installments_qs.filter(invoice_number__isnull=False).exclude(status='cancelado').exclude(status='realizado').order_by('invoice_issued_at', 'data_vencimento')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        closed_orders = self._closed_orders_queryset()
        installments_qs = self._installments_queryset(closed_orders)
        counts = self._billing_counts(closed_orders, installments_qs)
        context.update({
            'billing_counts': counts,
            'active_tab': 'open',
        })
        return context


class BillingClosedNFView(LoginRequiredMixin, IsFinancialMixin, ListView, BillingBaseMixin):
    template_name = 'finance/billing_closed_nf.html'
    context_object_name = 'installments'
    paginate_by = 20

    def get_queryset(self):
        closed_orders = self._closed_orders_queryset()
        installments_qs = self._installments_queryset(closed_orders)
        return installments_qs.filter(invoice_number__isnull=False, status='realizado').exclude(status='cancelado').order_by('-invoice_issued_at', '-data_vencimento')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        closed_orders = self._closed_orders_queryset()
        installments_qs = self._installments_queryset(closed_orders)
        counts = self._billing_counts(closed_orders, installments_qs)
        context.update({
            'billing_counts': counts,
            'active_tab': 'closed',
        })
        return context


class InstallmentInvoiceView(LoginRequiredMixin, IsFinancialMixin, View):
    template_name = 'finance/installment_invoice_form.html'

    def _get_installment(self, pk):
        return get_object_or_404(
            Transaction,
            pk=pk,
            is_installment=True,
            tipo='receita'
        )

    def get(self, request, pk):
        installment = self._get_installment(pk)
        if installment.status == 'realizado':
            messages.error(request, 'Esta NF já foi paga e não pode ser alterada.')
            return redirect('finance:billing_open_nf')
        if installment.status == 'cancelado':
            messages.error(request, 'Esta NF está cancelada e não pode ser alterada.')
            return redirect('finance:billing_open_nf')
        form = InstallmentInvoiceForm(installment=installment, initial={
            'payment_origin': installment.payment_origin or '',
            'invoice_number': installment.invoice_number or '',
            'invoice_issued_at': installment.invoice_issued_at,
            'invoice_description': (installment.invoice_data or {}).get('descricao', ''),
            'service_city': (installment.invoice_data or {}).get('cidade', ''),
            'boleto_number': installment.boleto_number or '',
            'boleto_issued_at': installment.boleto_issued_at,
            'generate_nf': bool(installment.invoice_number),
            'generate_boleto': bool(installment.boleto_number),
        })
        return render(request, self.template_name, {
            'installment': installment,
            'order': installment.work_order,
            'form': form,
        })

    def post(self, request, pk):
        installment = self._get_installment(pk)
        if installment.status == 'realizado':
            messages.error(request, 'Esta NF já foi paga e não pode ser alterada.')
            return redirect('finance:billing_open_nf')
        if installment.status == 'cancelado':
            messages.error(request, 'Esta NF está cancelada e não pode ser alterada.')
            return redirect('finance:billing_open_nf')
        form = InstallmentInvoiceForm(request.POST, installment=installment)
        if not form.is_valid():
            return render(request, self.template_name, {
                'installment': installment,
                'order': installment.work_order,
                'form': form,
            })

        payment_origin = form.cleaned_data.get('payment_origin')
        generate_nf = form.cleaned_data.get('generate_nf')
        generate_boleto = form.cleaned_data.get('generate_boleto')

        installment.payment_origin = payment_origin or None

        if generate_nf:
            installment.invoice_number = form.cleaned_data.get('invoice_number')
            installment.invoice_issued_at = form.cleaned_data.get('invoice_issued_at')
            installment.invoice_data = {
                'descricao': form.cleaned_data.get('invoice_description') or '',
                'cidade': form.cleaned_data.get('service_city') or '',
            }
            installment.is_projection = False
        else:
            installment.invoice_number = None
            installment.invoice_issued_at = None
            installment.invoice_data = None

        if generate_boleto:
            installment.boleto_number = form.cleaned_data.get('boleto_number')
            installment.boleto_issued_at = form.cleaned_data.get('boleto_issued_at')
        else:
            installment.boleto_number = None
            installment.boleto_issued_at = None

        installment.save()

        messages.success(request, 'Dados da NF/Boleto atualizados com sucesso.')
        return redirect('finance:billing_open_nf')
class WorkOrderPaymentView(LoginRequiredMixin, IsFinancialMixin, View):
    template_name = 'finance/workorder_payment.html'

    def _get_order(self, pk):
        closed_statuses = ServiceOrderStatus.objects.filter(
            is_active=True,
            status_code__in=['COMPLETED', 'FINANCIAL_CLOSED']
        )
        return get_object_or_404(WorkOrder, pk=pk, status__in=closed_statuses)

    def _get_end_date(self, order):
        if order.closed_on:
            return order.closed_on
        if order.finished_at:
            return order.finished_at.date()
        return None

    def _add_months(self, base_date, months):
        year = base_date.year + ((base_date.month - 1 + months) // 12)
        month = ((base_date.month - 1 + months) % 12) + 1
        day = min(base_date.day, _last_day_of_month(date(year, month, 1)).day)
        return date(year, month, day)

    def get(self, request, pk):
        order = self._get_order(pk)
        end_date = self._get_end_date(order)
        if not end_date:
            messages.error(request, 'Nenhuma conta sem data término pode ir para pagamento.')
            return redirect('finance:billing_open_nf')

        existing_installments = Transaction.objects.filter(
            work_order=order,
            is_installment=True
        ).order_by('data_vencimento')
        canceled_installments = existing_installments.filter(status='cancelado')
        active_installments = existing_installments.exclude(status='cancelado')

        form = WorkOrderPaymentForm(
            initial={
                'first_due_date': timezone.localdate(),
                'installments': 1,
            }
        )

        return render(request, self.template_name, {
            'order': order,
            'end_date': end_date,
            'form': form,
            'existing_installments': existing_installments,
            'canceled_installments': canceled_installments,
            'active_installments': active_installments,
        })

    def post(self, request, pk):
        order = self._get_order(pk)
        end_date = self._get_end_date(order)
        if not end_date:
            messages.error(request, 'Nenhuma conta sem data término pode ir para pagamento.')
            return redirect('finance:billing_open_nf')

        existing_installments = Transaction.objects.filter(
            work_order=order,
            is_installment=True
        ).exclude(status='cancelado')
        if existing_installments.exists():
            messages.error(request, 'Esta OS já possui parcelas geradas.')
            return redirect('finance:workorder_payment', pk=order.pk)

        if Transaction.objects.filter(work_order=order, status='realizado').exists():
            messages.error(request, 'Esta OS já possui recebimento realizado.')
            return redirect('finance:workorder_payment', pk=order.pk)

        form = WorkOrderPaymentForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {
                'order': order,
                'end_date': end_date,
                'form': form,
                'existing_installments': existing_installments,
                'canceled_installments': Transaction.objects.filter(work_order=order, is_installment=True, status='cancelado'),
                'active_installments': existing_installments,
            })

        total_amount = order.labor_cost or Decimal('0.00')
        if not total_amount or total_amount <= 0:
            form.add_error(None, 'Valor final da OS não informado. Atualize a OS antes de gerar pagamento.')
            return render(request, self.template_name, {
                'order': order,
                'end_date': end_date,
                'form': form,
                'existing_installments': existing_installments,
            })

        base_tx = Transaction.objects.filter(work_order=order, is_installment=False).order_by('-created_at').first()
        account = base_tx.account if base_tx else None
        category = base_tx.category if base_tx else None
        if not account:
            if request.user.role == 'financial':
                account = Account.objects.filter(ativa=True, is_primary=True).first()
            else:
                account = Account.objects.filter(user=request.user, ativa=True, is_primary=True).first()
        if not category:
            category = Category.objects.filter(tipo='receita', ativa=True).order_by('nome').first()

        if not account or not category:
            form.add_error(None, 'Conta ou categoria padrão não encontrada para gerar as parcelas.')
            return render(request, self.template_name, {
                'order': order,
                'end_date': end_date,
                'form': form,
                'existing_installments': existing_installments,
                'canceled_installments': Transaction.objects.filter(work_order=order, is_installment=True, status='cancelado'),
                'active_installments': existing_installments,
            })

        installments = form.cleaned_data.get('installments') or 1
        first_due_date = form.cleaned_data.get('first_due_date')
        confirm_regenerate = form.cleaned_data.get('confirm_regenerate')

        canceled_exists = Transaction.objects.filter(
            work_order=order,
            is_installment=True,
            status='cancelado'
        ).exists()
        if canceled_exists and not confirm_regenerate:
            form.add_error('confirm_regenerate', 'Confirme a recriação das parcelas canceladas.')
            return render(request, self.template_name, {
                'order': order,
                'end_date': end_date,
                'form': form,
                'existing_installments': Transaction.objects.filter(work_order=order, is_installment=True),
                'canceled_installments': Transaction.objects.filter(work_order=order, is_installment=True, status='cancelado'),
                'active_installments': Transaction.objects.filter(work_order=order, is_installment=True).exclude(status='cancelado'),
            })

        installment_group_id = uuid.uuid4()

        base_value = (total_amount / installments).quantize(Decimal('0.01'))
        remainder = total_amount - (base_value * installments)

        with db_transaction.atomic():
            Transaction.objects.filter(
                work_order=order,
                is_installment=False,
            ).exclude(status='cancelado').exclude(status='realizado').update(
                status='cancelado',
                data_pagamento=None
            )

            for idx in range(installments):
                installment_value = base_value
                if idx == installments - 1:
                    installment_value += remainder

                due_date = first_due_date if idx == 0 else self._add_months(first_due_date, idx)
                Transaction.objects.create(
                    user=request.user,
                    work_order=order,
                    tipo='receita',
                    descricao=f'OS {order.code} - Parcela {idx + 1}/{installments}',
                    valor=installment_value,
                    data_vencimento=due_date,
                    account=account,
                    category=category,
                    observacoes='Conta a receber gerada a partir de OS encerrada.',
                    is_installment=True,
                    is_projection=True,
                    installment_group_id=installment_group_id,
                    installment_number=idx + 1,
                    installment_total=installments,
                    is_recurring=False,
                    recurrence_period='unico',
                    related_service_type=order.service_type,
                )

        messages.success(request, 'Parcelas geradas com sucesso.')
        return redirect('finance:billing_open_nf')

        transaction.marcar_como_previsto()
        messages.success(request, f'Lancamento "{transaction.descricao}" voltou para previsto.')
        return redirect(request.POST.get('next') or 'finance:transaction_list')


class DreView(LoginRequiredMixin, IsFinancialMixin, TemplateView):
    template_name = 'finance/dre.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()

        start_param = self.request.GET.get('start')
        end_param = self.request.GET.get('end')
        phase = 'consolidado'
        account_id = self.request.GET.get('account') or None
        category_id = self.request.GET.get('category') or None

        start_date = today.replace(day=1)
        end_date = _last_day_of_month(today)

        if start_param:
            try:
                start_date = timezone.datetime.fromisoformat(start_param).date()
            except ValueError:
                pass
        if end_param:
            try:
                end_date = timezone.datetime.fromisoformat(end_param).date()
            except ValueError:
                pass

        if end_date < start_date:
            start_date, end_date = end_date, start_date

        # Financial vê dados consolidados (sem filtro de usuário)
        user_param = None if self.request.user.role == 'financial' else self.request.user

        context.update(build_dre_context(
            start_date,
            end_date,
            phase,
            account_id=account_id,
            category_id=category_id,
            user=user_param,
        ))

        # Financial vê TODAS as contas
        if self.request.user.role == 'financial':
            context['accounts'] = Account.objects.filter(ativa=True).order_by('nome')
        else:
            context['accounts'] = Account.objects.filter(user=self.request.user, ativa=True).order_by('nome')
        context['categories'] = Category.objects.filter(ativa=True).order_by('nome')
        context['selected_account'] = account_id or ''
        context['selected_category'] = category_id or ''
        context['phase'] = phase
        context['phase'] = phase
        return context


def _shift_months(base_date, months):
    year = base_date.year + ((base_date.month - 1 + months) // 12)
    month = ((base_date.month - 1 + months) % 12) + 1
    return date(year, month, 1)


def _default_finance_range(today):
    start = date(today.year, 1, 1) - timedelta(days=90)
    end = date(today.year, 12, 31)
    return start, end


def _build_summary(qs, date_field, start_date, end_date):
    receitas = qs.filter(
        tipo='receita',
        **{f'{date_field}__gte': start_date, f'{date_field}__lte': end_date},
    ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    despesas = qs.filter(
        tipo='despesa',
        **{f'{date_field}__gte': start_date, f'{date_field}__lte': end_date},
    ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    return {
        'receitas': receitas,
        'despesas': despesas,
        'saldo': receitas - despesas,
    }


class CashflowView(LoginRequiredMixin, IsFinancialMixin, TemplateView):
    template_name = 'finance/fluxo_caixa.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()

        start_param = self.request.GET.get('start')
        end_param = self.request.GET.get('end')
        phase = self.request.GET.get('phase', 'consolidado')
        account_id = self.request.GET.get('account') or None
        category_id = self.request.GET.get('category') or None

        year_start = date(today.year, 1, 1)
        year_end = date(today.year, 12, 31)
        default_start, default_end = _default_finance_range(today)

        start_date = year_start
        end_date = year_end

        if start_param:
            try:
                start_date = timezone.datetime.fromisoformat(start_param).date()
            except ValueError:
                pass
        if end_param:
            try:
                end_date = timezone.datetime.fromisoformat(end_param).date()
            except ValueError:
                pass

        if end_date < start_date:
            start_date, end_date = end_date, start_date

        # Financial vê dados consolidados (sem filtro de usuário)
        user_param = None if self.request.user.role == 'financial' else self.request.user

        context.update(build_cashflow_context(
            start_date,
            end_date,
            phase,
            account_id=account_id,
            category_id=category_id,
            user=user_param,
        ))

        # Financial vê TODAS as contas
        if self.request.user.role == 'financial':
            context['accounts'] = Account.objects.filter(ativa=True).order_by('nome')
        else:
            context['accounts'] = Account.objects.filter(user=self.request.user, ativa=True).order_by('nome')
        context['categories'] = Category.objects.filter(ativa=True).order_by('nome')
        context['selected_account'] = account_id or ''
        context['selected_category'] = category_id or ''

        months = context.get('months', [])
        month_labels = []
        for item in months:
            month_labels.append({
                **item,
                'full_label': f"{MONTH_NAMES[item['month'] - 1]} {item['year']}",
            })

        totals_receita_cells = context.get('totals_receita_cells', [])
        totals_despesa_cells = context.get('totals_despesa_cells', [])
        totals_saldo_cells = context.get('totals_saldo_cells', [])

        total_entrada_values = [cell['value'] for cell in totals_receita_cells]
        total_saida_values = [cell['value'] for cell in totals_despesa_cells]
        resultado_values = [cell['value'] for cell in totals_saldo_cells]

        saldo_inicial_values = []
        saldo_final_values = []
        running_saldo = context.get('saldo_inicial_total') or Decimal('0.00')
        for value in resultado_values:
            saldo_inicial_values.append(running_saldo)
            running_saldo += value
            saldo_final_values.append(running_saldo)

        context['month_labels'] = month_labels
        context['total_entrada_values'] = total_entrada_values
        context['total_saida_values'] = total_saida_values
        context['resultado_values'] = resultado_values
        context['saldo_inicial_values'] = saldo_inicial_values
        context['saldo_final_values'] = saldo_final_values
        context['chart_labels'] = [item['full_label'] for item in month_labels]
        context['chart_saldo_final'] = [float(value) for value in saldo_final_values]
        context['chart_resultado'] = [float(value) for value in resultado_values]

        def summary_for_range(start, end):
            # Financial vê dados consolidados (sem filtro de usuário)
            user_param = None if self.request.user.role == 'financial' else self.request.user
            qs = get_finance_queryset(
                user=user_param,
                account_id=account_id,
                category_id=category_id,
            )
            filtered_qs, date_field = apply_phase_filter(qs, phase, start, end)
            return _build_summary(filtered_qs, date_field, start, end)

        current_year_start = date(today.year, 1, 1)
        current_year_end = date(today.year, 12, 31)
        previous_year_start = date(today.year - 1, 1, 1)
        previous_year_end = date(today.year - 1, 12, 31)

        current_month_start = date(today.year, today.month, 1)
        current_month_end = _last_day_of_month(today)
        previous_month_seed = _shift_months(today.replace(day=1), -1)
        previous_month_start = previous_month_seed
        previous_month_end = _last_day_of_month(previous_month_seed)

        summary_current_year = summary_for_range(current_year_start, current_year_end)
        summary_previous_year = summary_for_range(previous_year_start, previous_year_end)
        summary_current_month = summary_for_range(current_month_start, current_month_end)
        summary_previous_month = summary_for_range(previous_month_start, previous_month_end)

        resultado_ano = summary_previous_year['saldo'] + summary_current_year['receitas'] - summary_current_year['despesas']
        resultado_mes = summary_previous_month['saldo'] + summary_current_month['receitas'] - summary_current_month['despesas']

        context['summary'] = {
            'ano_atual': summary_current_year,
            'ano_anterior': summary_previous_year,
            'mes_atual': summary_current_month,
            'mes_anterior': summary_previous_month,
        }
        context['current_year'] = today.year
        context['previous_year'] = today.year - 1
        context['current_month_label'] = MONTH_NAMES[today.month - 1]
        context['previous_month_label'] = MONTH_NAMES[previous_month_seed.month - 1]
        context['previous_month_year'] = previous_month_seed.year
        context['resultado_ano'] = resultado_ano
        context['resultado_mes'] = resultado_mes

        # Financial vê dados consolidados (sem filtro de usuário)
        user_param = None if self.request.user.role == 'financial' else self.request.user
        list_qs = get_finance_queryset(
            user=user_param,
            account_id=account_id,
            category_id=category_id,
        )

        list_qs = list_qs.select_related('account', 'category')
        context['default_range_start'] = default_start
        context['default_range_end'] = default_end
        context['contas_recentes'] = list_qs.filter(
            data_vencimento__gte=default_start,
            data_vencimento__lte=default_end,
        ).order_by('-data_vencimento')[:50]
        context['contas_abertas'] = list_qs.filter(
            status='previsto',
            data_vencimento__gte=default_start,
            data_vencimento__lte=default_end,
        ).order_by('-data_vencimento')[:50]
        context['contas_atrasadas'] = list_qs.filter(
            status='atrasado',
            data_vencimento__gte=default_start,
            data_vencimento__lte=default_end,
        ).order_by('-data_vencimento')[:50]

        user = self.request.user
        context['can_manage_finance'] = (
            user.is_superuser
            or user.role in ['admin', 'financial']
            or (user.is_staff and user.role != 'operational')
        )
        return context


class AccountsPayableReportView(LoginRequiredMixin, IsFinancialMixin, TemplateView):
    """
    Relatório eficiente de contas a pagar com agrupamento por vencimento.
    """
    template_name = 'finance/accounts_payable_report.html'

    def get_context_data(self, **kwargs):
        from datetime import date, timedelta
        from django.db.models import Q, Sum, Count, Case, When, DecimalField
        from django.db.models.functions import Coalesce

        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Base queryset: apenas despesas previstas ou atrasadas
        if user.role == 'financial':
            queryset = Transaction.objects.filter(tipo='despesa')
        else:
            queryset = Transaction.objects.filter(user=user, tipo='despesa')

        queryset = queryset.filter(status__in=['previsto', 'atrasado']).select_related(
            'account', 'category', 'related_service_type'
        )

        # Aplicar filtros do GET
        account_id = self.request.GET.get('account')
        if account_id:
            queryset = queryset.filter(account_id=account_id)

        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        expense_type = self.request.GET.get('expense_type')
        if expense_type:
            queryset = queryset.filter(expense_type=expense_type)

        service_type_id = self.request.GET.get('service_type')
        if service_type_id:
            queryset = queryset.filter(related_service_type_id=service_type_id)

        # Datas de referência
        today = date.today()
        week_end = today + timedelta(days=7)
        month_end = today + timedelta(days=30)

        # Agrupar por período de vencimento
        overdue = queryset.filter(data_vencimento__lt=today).order_by('data_vencimento')
        due_today = queryset.filter(data_vencimento=today).order_by('data_vencimento')
        due_this_week = queryset.filter(data_vencimento__gt=today, data_vencimento__lte=week_end).order_by('data_vencimento')
        due_this_month = queryset.filter(data_vencimento__gt=week_end, data_vencimento__lte=month_end).order_by('data_vencimento')
        due_later = queryset.filter(data_vencimento__gt=month_end).order_by('data_vencimento')

        # Totais por período
        context['overdue_total'] = overdue.aggregate(total=Coalesce(Sum('valor'), Decimal('0.00')))['total']
        context['overdue_count'] = overdue.count()
        context['overdue_transactions'] = overdue[:20]  # Limitar a 20 mais urgentes

        context['today_total'] = due_today.aggregate(total=Coalesce(Sum('valor'), Decimal('0.00')))['total']
        context['today_count'] = due_today.count()
        context['today_transactions'] = due_today

        context['week_total'] = due_this_week.aggregate(total=Coalesce(Sum('valor'), Decimal('0.00')))['total']
        context['week_count'] = due_this_week.count()
        context['week_transactions'] = due_this_week

        context['month_total'] = due_this_month.aggregate(total=Coalesce(Sum('valor'), Decimal('0.00')))['total']
        context['month_count'] = due_this_month.count()
        context['month_transactions'] = due_this_month[:30]  # Limitar a 30

        context['later_total'] = due_later.aggregate(total=Coalesce(Sum('valor'), Decimal('0.00')))['total']
        context['later_count'] = due_later.count()

        # Total geral
        context['grand_total'] = queryset.aggregate(total=Coalesce(Sum('valor'), Decimal('0.00')))['total']
        context['grand_count'] = queryset.count()

        # Breakdown por tipo de despesa
        expense_breakdown = {}
        for expense_type_code, expense_type_label in Transaction.EXPENSE_TYPE_CHOICES:
            total = queryset.filter(expense_type=expense_type_code).aggregate(
                total=Coalesce(Sum('valor'), Decimal('0.00'))
            )['total']
            count = queryset.filter(expense_type=expense_type_code).count()
            if total > 0:
                expense_breakdown[expense_type_code] = {
                    'label': expense_type_label,
                    'total': total,
                    'count': count,
                }
        context['expense_breakdown'] = expense_breakdown

        # Breakdown por categoria (top 10)
        category_breakdown = queryset.values('category__nome').annotate(
            total=Coalesce(Sum('valor'), Decimal('0.00')),
            count=Count('id')
        ).order_by('-total')[:10]
        context['category_breakdown'] = category_breakdown

        # Filtros para o form
        context['accounts'] = Account.objects.filter(ativa=True).order_by('nome')
        context['categories'] = Category.objects.filter(tipo='despesa', ativa=True).order_by('nome')
        from servicetype.models import ServiceType
        context['service_types'] = ServiceType.objects.filter(is_active=True).order_by('name')

        # Valores selecionados
        context['selected_account'] = account_id
        context['selected_category'] = category_id
        context['selected_expense_type'] = expense_type
        context['selected_service_type'] = service_type_id

        return context


class AccountsReceivableReportView(LoginRequiredMixin, IsFinancialMixin, TemplateView):
    """
    Relatorio eficiente de contas a receber com agrupamento por vencimento.
    """
    template_name = 'finance/accounts_receivable_report.html'

    def get_context_data(self, **kwargs):
        from django.db.models import Sum
        from django.db.models.functions import Coalesce

        context = super().get_context_data(**kwargs)
        user = self.request.user

        if user.role == 'financial':
            queryset = Transaction.objects.filter(tipo='receita')
        else:
            queryset = Transaction.objects.filter(user=user, tipo='receita')

        queryset = queryset.filter(status__in=['previsto', 'atrasado']).select_related(
            'account', 'category', 'work_order', 'related_service_type'
        )

        account_id = self.request.GET.get('account')
        if account_id:
            queryset = queryset.filter(account_id=account_id)

        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        service_type_id = self.request.GET.get('service_type')
        if service_type_id:
            queryset = queryset.filter(related_service_type_id=service_type_id)

        is_installment = self.request.GET.get('is_installment')
        if is_installment == 'true':
            queryset = queryset.filter(is_installment=True)
        elif is_installment == 'false':
            queryset = queryset.filter(is_installment=False)

        today = timezone.localdate()
        week_end = today + timedelta(days=7)
        month_end = today + timedelta(days=30)

        overdue = queryset.filter(data_vencimento__lt=today).order_by('data_vencimento')
        due_today = queryset.filter(data_vencimento=today).order_by('data_vencimento')
        due_this_week = queryset.filter(data_vencimento__gt=today, data_vencimento__lte=week_end).order_by('data_vencimento')
        due_this_month = queryset.filter(data_vencimento__gt=week_end, data_vencimento__lte=month_end).order_by('data_vencimento')
        due_later = queryset.filter(data_vencimento__gt=month_end).order_by('data_vencimento')

        context['overdue_total'] = overdue.aggregate(total=Coalesce(Sum('valor'), Decimal('0.00')))['total']
        context['overdue_count'] = overdue.count()
        context['overdue_transactions'] = overdue[:20]

        context['today_total'] = due_today.aggregate(total=Coalesce(Sum('valor'), Decimal('0.00')))['total']
        context['today_count'] = due_today.count()
        context['today_transactions'] = due_today

        context['week_total'] = due_this_week.aggregate(total=Coalesce(Sum('valor'), Decimal('0.00')))['total']
        context['week_count'] = due_this_week.count()
        context['week_transactions'] = due_this_week

        context['month_total'] = due_this_month.aggregate(total=Coalesce(Sum('valor'), Decimal('0.00')))['total']
        context['month_count'] = due_this_month.count()
        context['month_transactions'] = due_this_month

        context['later_total'] = due_later.aggregate(total=Coalesce(Sum('valor'), Decimal('0.00')))['total']
        context['later_count'] = due_later.count()

        context['grand_total'] = queryset.aggregate(total=Coalesce(Sum('valor'), Decimal('0.00')))['total']
        context['grand_count'] = queryset.count()

        if self.request.user.role == 'financial':
            context['accounts'] = Account.objects.filter(ativa=True).order_by('nome')
        else:
            context['accounts'] = Account.objects.filter(user=self.request.user, ativa=True).order_by('nome')
        context['categories'] = Category.objects.filter(tipo='receita', ativa=True).order_by('nome')

        from servicetype.models import ServiceType
        context['service_types'] = ServiceType.objects.filter(is_active=True).order_by('name')

        context['selected_account'] = account_id
        context['selected_category'] = category_id
        context['selected_service_type'] = service_type_id
        context['selected_is_installment'] = is_installment

        return context


class ExpenseBreakdownView(LoginRequiredMixin, IsFinancialMixin, TemplateView):
    """
    Relatório de breakdown de despesas por tipo (Direto, Indireto, Fixo, Variável, etc).
    """
    template_name = 'finance/expense_breakdown.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Filtro de data
        today = timezone.localdate()
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')

        if start_date:
            start_date = date.fromisoformat(start_date)
        else:
            start_date = today.replace(day=1)

        if end_date:
            end_date = date.fromisoformat(end_date)
        else:
            start_date = today.replace(day=1)
            end_date = _last_day_of_month(today)

        # Pegar transações
        user_param = None if user.role == 'financial' else user
        qs = get_finance_queryset(user=user_param)
        qs = qs.filter(
            tipo='despesa',
            status='realizado',
            data_vencimento__gte=start_date,
            data_vencimento__lte=end_date
        )

        # Breakdown por tipo de despesa
        breakdown = {}
        for expense_type_code, expense_type_label in Transaction.EXPENSE_TYPE_CHOICES:
            total = qs.filter(expense_type=expense_type_code).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
            count = qs.filter(expense_type=expense_type_code).count()
            breakdown[expense_type_code] = {
                'label': expense_type_label,
                'total': total,
                'count': count,
                'percentage': 0,
            }

        # Calcular porcentagens
        total_despesas = sum(item['total'] for item in breakdown.values())
        if total_despesas > 0:
            for item in breakdown.values():
                item['percentage'] = (item['total'] / total_despesas * 100) if total_despesas > 0 else 0

        # Breakdown por categoria
        category_breakdown = qs.values('category__nome', 'expense_type').annotate(
            total=Sum('valor'),
            count=Count('id')
        ).order_by('-total')[:15]

        # Breakdown por serviço relacionado
        service_breakdown = qs.filter(related_service_type__isnull=False).values(
            'related_service_type__name', 'expense_type'
        ).annotate(
            total=Sum('valor'),
            count=Count('id')
        ).order_by('-total')[:10]

        # Despesas recorrentes vs únicas
        recurring_total = qs.filter(is_recurring=True).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        unique_total = qs.filter(is_recurring=False).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

        context['breakdown'] = breakdown
        context['category_breakdown'] = list(category_breakdown)
        context['service_breakdown'] = list(service_breakdown)
        context['total_despesas'] = total_despesas
        context['recurring_total'] = recurring_total
        context['unique_total'] = unique_total
        context['start_date'] = start_date
        context['end_date'] = end_date

        return context


@login_required
def cashflow_detail(request):
    user = request.user
    if not (
        user.is_superuser
        or user.role in ['admin', 'financial']
        or (user.is_staff and user.role != 'operational')
    ):
        return JsonResponse({'error': 'Acesso negado.'}, status=403)

    category_id = request.GET.get('category_id')
    account_id = request.GET.get('account_id')
    year = request.GET.get('year')
    month = request.GET.get('month')
    tipo = request.GET.get('tipo')
    phase = request.GET.get('phase', 'consolidado')

    if not category_id or not year or not month or tipo not in ['receita', 'despesa']:
        return HttpResponseBadRequest('Parametros invalidos.')

    try:
        year_int = int(year)
        month_int = int(month)
        start_date = date(year_int, month_int, 1)
    except ValueError:
        return HttpResponseBadRequest('Data invalida.')

    if month_int == 12:
        end_date = date(year_int, 12, 31)
    else:
        end_date = date(year_int, month_int + 1, 1) - timedelta(days=1)

    qs = get_finance_queryset(user=request.user, account_id=account_id, category_id=category_id)
    qs, date_field = apply_phase_filter(qs, phase, start_date, end_date)
    qs = qs.filter(tipo=tipo).select_related('account', 'category')
    items = [
        {
            'id': str(t.id),
            'descricao': t.descricao,
            'valor': float(t.valor),
            'data': getattr(t, date_field).strftime('%Y-%m-%d') if getattr(t, date_field) else None,
            'status': t.status,
            'conta': t.account.nome,
            'categoria': t.category.nome,
        }
        for t in qs.order_by(date_field)
    ]

    return JsonResponse({'items': items})

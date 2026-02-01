from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = 'finance'

urlpatterns = [
    path('dashboard/', views.FinanceDashboardView.as_view(), name='dashboard'),
    path('faturamento/', views.BillingOrdersView.as_view(), name='billing_orders'),
    path('faturamento/aguardando-nf/', views.BillingAwaitingNFView.as_view(), name='billing_awaiting_nf'),
    path('faturamento/nf-abertas/', views.BillingOpenNFView.as_view(), name='billing_open_nf'),
    path('faturamento/nf-fechadas/', views.BillingClosedNFView.as_view(), name='billing_closed_nf'),
    path('faturamento/legacy/', views.BillingOrdersView.as_view(), name='billing_list'),
    path('faturamento/os/<uuid:pk>/pagamento/', views.WorkOrderPaymentView.as_view(), name='workorder_payment'),
    path('faturamento/parcela/<uuid:pk>/nf/', views.InstallmentInvoiceView.as_view(), name='installment_nf'),

    path('transacoes/', views.TransactionListView.as_view(), name='transaction_list'),
    path('transacoes/novo/', views.TransactionCreateView.as_view(), name='transaction_create'),
    path('transacoes/<uuid:pk>/editar/', views.TransactionUpdateView.as_view(), name='transaction_update'),
    path('transacoes/<uuid:pk>/excluir/', views.TransactionDeleteView.as_view(), name='transaction_delete'),
    path('transacoes/<uuid:pk>/marcar-realizado/', views.TransactionMarkAsCompletedView.as_view(), name='transaction_mark_completed'),
    path('transacoes/<uuid:pk>/marcar-previsto/', views.TransactionMarkAsPendingView.as_view(), name='transaction_mark_pending'),
    path('transacoes/<uuid:pk>/cancelar/', views.TransactionCancelView.as_view(), name='transaction_cancel'),

    path('contas-financeiras/', views.AccountListView.as_view(), name='account_list'),
    path('contas-financeiras/novo/', views.AccountCreateView.as_view(), name='account_create'),
    path('contas-financeiras/<uuid:pk>/editar/', views.AccountUpdateView.as_view(), name='account_update'),
    path('contas-financeiras/<uuid:pk>/excluir/', views.AccountDeleteView.as_view(), name='account_delete'),

    path('categorias/', views.CategoryListView.as_view(), name='category_list'),
    path('categorias/novo/', views.CategoryCreateView.as_view(), name='category_create'),
    path('categorias/<uuid:pk>/editar/', views.CategoryUpdateView.as_view(), name='category_update'),
    path('categorias/<uuid:pk>/excluir/', views.CategoryDeleteView.as_view(), name='category_delete'),

    path('dre/', TemplateView.as_view(template_name='finance/coming_soon.html'), name='dre'),
    path('fluxo-caixa/', views.CashflowView.as_view(), name='cashflow'),
    path('fluxo-caixa/detalhe/', views.cashflow_detail, name='cashflow_detail'),

    path('contas-a-pagar/', views.AccountsPayableReportView.as_view(), name='accounts_payable'),
    path('contas-a-receber/', views.AccountsReceivableReportView.as_view(), name='accounts_receivable'),
    path('despesas/breakdown/', TemplateView.as_view(template_name='finance/coming_soon.html'), name='expense_breakdown'),
]

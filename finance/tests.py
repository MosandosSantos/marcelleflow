from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Account, Category, Transaction
from .forms import TransactionForm
from .services import build_dre_context, build_cashflow_context


User = get_user_model()


class FinanceViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='admin@example.com',
            password='test123',
            role='admin'
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            password='test123',
            role='admin'
        )
        self.account = Account.objects.create(
            user=self.user,
            nome='Banco Principal',
            tipo='conta_corrente',
            saldo_inicial=Decimal('1000.00')
        )
        self.category_receita = Category.objects.create(
            nome='Receitas',
            tipo='receita'
        )
        self.category_despesa = Category.objects.create(
            nome='Despesas',
            tipo='despesa'
        )

        self.other_account = Account.objects.create(
            user=self.other_user,
            nome='Conta Outra',
            tipo='conta_corrente',
            saldo_inicial=Decimal('0.00')
        )
        self.other_category = Category.objects.create(
            nome='Outra',
            tipo='despesa'
        )

        today = timezone.now().date()
        Transaction.objects.create(
            user=self.user,
            tipo='despesa',
            status='previsto',
            descricao='Conta de luz',
            valor=Decimal('120.00'),
            data_vencimento=today + timedelta(days=3),
            account=self.account,
            category=self.category_despesa
        )
        Transaction.objects.create(
            user=self.user,
            tipo='despesa',
            status='atrasado',
            descricao='Internet',
            valor=Decimal('90.00'),
            data_vencimento=today - timedelta(days=2),
            account=self.account,
            category=self.category_despesa
        )
        Transaction.objects.create(
            user=self.user,
            tipo='despesa',
            status='realizado',
            descricao='Aluguel',
            valor=Decimal('800.00'),
            data_vencimento=today - timedelta(days=10),
            data_pagamento=today - timedelta(days=9),
            account=self.account,
            category=self.category_despesa
        )
        Transaction.objects.create(
            user=self.user,
            tipo='receita',
            status='previsto',
            descricao='Pagamento cliente',
            valor=Decimal('1500.00'),
            data_vencimento=today + timedelta(days=5),
            account=self.account,
            category=self.category_receita
        )
        Transaction.objects.create(
            user=self.other_user,
            tipo='despesa',
            status='previsto',
            descricao='Outra despesa',
            valor=Decimal('10.00'),
            data_vencimento=today + timedelta(days=1),
            account=self.other_account,
            category=self.other_category
        )

    # Removido: telas de Contas a Pagar/Receber saíram do sistema.


class FinanceFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='admin2@example.com',
            password='test123',
            role='admin'
        )
        self.account = Account.objects.create(
            user=self.user,
            nome='Banco',
            tipo='conta_corrente'
        )
        self.category_receita = Category.objects.create(
            nome='Receitas',
            tipo='receita'
        )
        self.category_despesa = Category.objects.create(
            nome='Despesas',
            tipo='despesa'
        )

    def test_transaction_form_validates_category_type(self):
        form = TransactionForm(
            data={
                'tipo': 'receita',
                'status': 'previsto',
                'descricao': 'Teste',
                'valor': '10.00',
                'data_vencimento': timezone.now().date(),
                'account': self.account.id,
                'category': self.category_despesa.id,
            },
            user=self.user
        )
        self.assertFalse(form.is_valid())
        self.assertIn('category', form.errors)


class FinanceModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='admin3@example.com',
            password='test123',
            role='admin'
        )
        self.account = Account.objects.create(
            user=self.user,
            nome='Banco',
            tipo='conta_corrente'
        )
        self.category = Category.objects.create(
            nome='Receitas',
            tipo='receita'
        )

    def test_transaction_sets_payment_date_when_realized(self):
        transaction = Transaction.objects.create(
            user=self.user,
            tipo='receita',
            status='realizado',
            descricao='Teste',
            valor=Decimal('50.00'),
            data_vencimento=timezone.now().date(),
            account=self.account,
            category=self.category
        )
        self.assertIsNone(transaction.data_pagamento)


class FinanceDreTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='dre@example.com',
            password='test123',
            role='admin'
        )
        self.account = Account.objects.create(
            user=self.user,
            nome='Banco DRE',
            tipo='conta_corrente'
        )
        self.category_receita = Category.objects.create(
            nome='Servicos',
            tipo='receita'
        )
        self.category_despesa = Category.objects.create(
            nome='Despesas Operacionais',
            tipo='despesa'
        )
        self.category_imposto = Category.objects.create(
            nome='Impostos',
            tipo='despesa'
        )

        jan_5 = timezone.datetime(2026, 1, 5).date()
        jan_10 = timezone.datetime(2026, 1, 10).date()
        jan_15 = timezone.datetime(2026, 1, 15).date()
        jan_20 = timezone.datetime(2026, 1, 20).date()

        Transaction.objects.create(
            user=self.user,
            tipo='receita',
            status='realizado',
            descricao='Receita realizada',
            valor=Decimal('1000.00'),
            data_vencimento=jan_5,
            data_pagamento=jan_10,
            account=self.account,
            category=self.category_receita
        )
        Transaction.objects.create(
            user=self.user,
            tipo='receita',
            status='previsto',
            descricao='Receita prevista',
            valor=Decimal('500.00'),
            data_vencimento=jan_15,
            account=self.account,
            category=self.category_receita
        )
        Transaction.objects.create(
            user=self.user,
            tipo='despesa',
            status='realizado',
            descricao='Imposto',
            valor=Decimal('100.00'),
            data_vencimento=jan_5,
            data_pagamento=jan_10,
            account=self.account,
            category=self.category_imposto
        )
        Transaction.objects.create(
            user=self.user,
            tipo='despesa',
            status='realizado',
            descricao='Operacional',
            valor=Decimal('200.00'),
            data_vencimento=jan_20,
            data_pagamento=jan_20,
            account=self.account,
            category=self.category_despesa
        )

    def test_dre_realizado_usa_pagamento(self):
        start = timezone.datetime(2026, 1, 1).date()
        end = timezone.datetime(2026, 1, 31).date()
        context = build_dre_context(start, end, 'consolidado')

        dre_rows = {row['label']: row for row in context['dre_totals']}
        self.assertEqual(dre_rows['(+) Receita Operacional']['total'], Decimal('1000.00'))
        self.assertEqual(dre_rows['(-) Impostos sobre a venda']['total'], Decimal('100.00'))
        self.assertEqual(dre_rows['(=) Receita líquida']['total'], Decimal('900.00'))
        self.assertEqual(dre_rows['(-) Despesas operacionais']['total'], Decimal('200.00'))
        self.assertEqual(dre_rows['(=) Lucro líquido']['total'], Decimal('700.00'))

    def test_dre_projetado_usa_vencimento(self):
        start = timezone.datetime(2026, 1, 1).date()
        end = timezone.datetime(2026, 1, 31).date()
        context = build_dre_context(start, end, 'futuro')

        dre_rows = {row['label']: row for row in context['dre_totals']}
        self.assertEqual(dre_rows['(+) Receita Operacional']['total'], Decimal('1500.00'))
        self.assertEqual(dre_rows['(-) Impostos sobre a venda']['total'], Decimal('100.00'))


class FinanceCashflowTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='cashflow@example.com',
            password='test123',
            role='admin'
        )
        self.account = Account.objects.create(
            user=self.user,
            nome='Banco Cash',
            tipo='conta_corrente'
        )
        self.category_receita = Category.objects.create(
            nome='Servicos',
            tipo='receita'
        )
        self.category_despesa = Category.objects.create(
            nome='Operacional',
            tipo='despesa'
        )

        jan_5 = timezone.datetime(2026, 1, 5).date()
        feb_5 = timezone.datetime(2026, 2, 5).date()

        Transaction.objects.create(
            user=self.user,
            tipo='receita',
            status='previsto',
            descricao='Receita jan',
            valor=Decimal('1000.00'),
            data_vencimento=jan_5,
            account=self.account,
            category=self.category_receita
        )
        Transaction.objects.create(
            user=self.user,
            tipo='despesa',
            status='previsto',
            descricao='Despesa jan',
            valor=Decimal('200.00'),
            data_vencimento=jan_5,
            account=self.account,
            category=self.category_despesa
        )
        Transaction.objects.create(
            user=self.user,
            tipo='receita',
            status='realizado',
            descricao='Receita fev',
            valor=Decimal('1500.00'),
            data_vencimento=feb_5,
            data_pagamento=feb_5,
            account=self.account,
            category=self.category_receita
        )

    def test_cashflow_projetado_agrega_por_mes(self):
        start = timezone.datetime(2026, 1, 1).date()
        end = timezone.datetime(2026, 2, 28).date()
        context = build_cashflow_context(start, end, 'futuro')

        totals_receita = context['totals_receita_cells']
        totals_despesa = context['totals_despesa_cells']
        self.assertEqual(totals_receita[0]['value'], Decimal('1000.00'))
        self.assertEqual(totals_despesa[0]['value'], Decimal('200.00'))
        self.assertEqual(totals_receita[1]['value'], Decimal('1500.00'))



    def test_cashflow_realizado_usa_pagamento(self):
        start = timezone.datetime(2026, 1, 1).date()
        end = timezone.datetime(2026, 2, 28).date()
        context = build_cashflow_context(start, end, 'consolidado')

        totals_receita = context['totals_receita_cells']
        self.assertEqual(totals_receita[0]['value'], Decimal('0.00'))
        self.assertEqual(totals_receita[1]['value'], Decimal('1500.00'))


class TransactionCancelTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email='finance@example.com',
            password='senha-forte-123',
            username='finance-user',
            role=User.ROLE_FINANCIAL,
        )
        self.account = Account.objects.create(
            user=self.user,
            nome='Conta Principal',
            tipo='conta_corrente',
            saldo_inicial=Decimal('0.00'),
            ativa=True,
            is_primary=True,
        )
        self.category = Category.objects.create(
            nome='Receitas',
            tipo='receita',
            ativa=True,
        )

    def test_cancel_transaction_keeps_status(self):
        tx = Transaction.objects.create(
            user=self.user,
            tipo='receita',
            descricao='Teste cancelamento',
            valor=Decimal('100.00'),
            data_vencimento=timezone.localdate(),
            account=self.account,
            category=self.category,
            status='previsto',
        )
        tx.cancelar()
        tx.refresh_from_db()
        self.assertEqual(tx.status, 'cancelado')


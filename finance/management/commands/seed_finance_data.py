import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from finance.models import Account, Category, Transaction
from workorder.models import WorkOrder


User = get_user_model()


RECEITA_DESCRICOES = [
    'Servico prestado',
    'Atendimento tecnico',
    'Manutencao preventiva',
    'Instalacao realizada',
    'Suporte especializado',
]

DESPESA_DESCRICOES = [
    ('Aluguel', 'Aluguel da sede'),
    ('Combustivel', 'Abastecimento frota'),
    ('Energia', 'Conta de energia'),
    ('Internet', 'Assinatura internet'),
    ('Telefonia', 'Plano telefonia'),
    ('Material', 'Compra de materiais'),
    ('Impostos', 'Tributos operacionais'),
    ('Folha', 'Pagamento de folha'),
    ('Manutencao', 'Manutencao de veiculos'),
]


class Command(BaseCommand):
    help = 'Cria uma grande carga de dados financeiros (Dez/Jan/Fev) com receitas e despesas.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--seed',
            type=int,
            default=42,
            help='Seed para reproducibilidade.'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Remove dados financeiros atuais do usuario antes de inserir.'
        )
        parser.add_argument(
            '--users',
            choices=['admins', 'all'],
            default='admins',
            help='Usuarios alvo: admins (admin/manager/superuser) ou all.'
        )
        parser.add_argument(
            '--per-month',
            type=int,
            default=80,
            help='Quantidade total aproximada de transacoes por mes (por usuario).'
        )

    def handle(self, *args, **options):
        random.seed(options['seed'])

        if options['users'] == 'all':
            users = User.objects.all()
        else:
            users = User.objects.filter(
                role__in=['admin', 'manager']
            ) | User.objects.filter(is_superuser=True)
            users = users.distinct()

        if not users.exists():
            self.stdout.write(self.style.WARNING('Nenhum usuario encontrado para carga.'))
            return

        today = timezone.localdate()
        months = [
            date(2025, 12, 1),
            date(2026, 1, 1),
            date(2026, 2, 1),
        ]

        for user in users:
            with transaction.atomic():
                if options['clear']:
                    Transaction.objects.filter(user=user).delete()
                    Account.objects.filter(user=user).delete()
                    Category.objects.all().delete()

                account_main = Account.objects.filter(user=user, nome='Banco Principal').first()
                if not account_main:
                    account_main = Account.objects.create(
                        user=user,
                        nome='Banco Principal',
                        tipo='conta_corrente',
                        saldo_inicial=Decimal('15000.00')
                    )

                account_cash = Account.objects.filter(user=user, nome='Caixa Operacional').first()
                if not account_cash:
                    account_cash = Account.objects.create(
                        user=user,
                        nome='Caixa Operacional',
                        tipo='carteira',
                        saldo_inicial=Decimal('2000.00')
                    )

                account_card = Account.objects.filter(user=user, nome='Cartao Corporativo').first()
                if not account_card:
                    account_card = Account.objects.create(
                        user=user,
                        nome='Cartao Corporativo',
                        tipo='outros',
                        saldo_inicial=Decimal('5000.00')
                    )

                receita_category = self._get_or_create_category('Servicos Prestados', 'receita')
                receita_extra_category = self._get_or_create_category('Receitas Extras', 'receita')

                despesa_categories = {}
                for nome, _ in DESPESA_DESCRICOES:
                    despesa_categories[nome] = self._get_or_create_category(nome, 'despesa')

                per_month = options['per_month']
                receita_count = int(per_month * 0.45)
                despesa_count = per_month - receita_count

                for month_start in months:
                    month_end = self._month_end(month_start)
                    receitas = self._build_receitas_from_workorders(
                        user=user,
                        month_start=month_start,
                        month_end=month_end,
                        conta=account_main,
                        categoria=receita_category,
                        max_items=receita_count,
                        today=today,
                    )

                    remaining_receitas = receita_count - len(receitas)
                    if remaining_receitas > 0:
                        receitas += self._build_receitas_sinteticas(
                            user=user,
                            month_start=month_start,
                            month_end=month_end,
                            conta=account_main,
                            categoria=receita_extra_category,
                            count=remaining_receitas,
                            today=today,
                        )

                    despesas = self._build_despesas(
                        user=user,
                        month_start=month_start,
                        month_end=month_end,
                        contas=[account_main, account_cash, account_card],
                        categories=despesa_categories,
                        count=despesa_count,
                        today=today,
                    )

                    Transaction.objects.bulk_create(receitas + despesas)

            self.stdout.write(self.style.SUCCESS(
                f'Usuario {user.email}: carga financeira criada (Dez/Jan/Fev).'
            ))

    def _get_or_create_category(self, nome, tipo):
        category = Category.objects.filter(nome=nome, tipo=tipo).first()
        if category:
            return category
        return Category.objects.create(nome=nome, tipo=tipo)

    def _month_end(self, month_start):
        if month_start.month == 12:
            return date(month_start.year, 12, 31)
        next_month = date(month_start.year, month_start.month + 1, 1)
        return next_month - timedelta(days=1)

    def _random_date(self, start, end):
        delta_days = (end - start).days
        if delta_days <= 0:
            return start
        return start + timedelta(days=random.randint(0, delta_days))

    def _pick_status(self, vencimento, today, allow_realizado=True):
        if vencimento > today:
            return 'previsto'
        if allow_realizado and random.random() < 0.65:
            return 'realizado'
        return 'atrasado'

    def _build_receitas_from_workorders(self, user, month_start, month_end, conta, categoria, max_items, today):
        orders = WorkOrder.objects.filter(
            created_at__date__gte=month_start,
            created_at__date__lte=month_end,
            labor_cost__isnull=False,
        ).order_by('-created_at')

        receitas = []
        for order in orders[:max_items]:
            vencimento = order.created_at.date() + timedelta(days=random.randint(5, 20))
            status = self._pick_status(vencimento, today, allow_realizado=True)
            receitas.append(Transaction(
                user=user,
                tipo='receita',
                status=status,
                descricao=f'Servico prestado - OS {order.code}',
                valor=order.labor_cost or Decimal('0.00'),
                data_vencimento=vencimento,
                data_pagamento=(vencimento + timedelta(days=random.randint(0, 5))) if status == 'realizado' else None,
                account=conta,
                category=categoria,
                observacoes='Entrada vinculada ao servico prestado.'
            ))
        return receitas

    def _build_receitas_sinteticas(self, user, month_start, month_end, conta, categoria, count, today):
        receitas = []
        for _ in range(count):
            vencimento = self._random_date(month_start, month_end)
            status = self._pick_status(vencimento, today, allow_realizado=True)
            descricao = random.choice(RECEITA_DESCRICOES)
            valor = Decimal(str(random.randint(800, 6500)))
            receitas.append(Transaction(
                user=user,
                tipo='receita',
                status=status,
                descricao=f'{descricao} - contrato {random.randint(1000, 9999)}',
                valor=valor,
                data_vencimento=vencimento,
                data_pagamento=(vencimento + timedelta(days=random.randint(0, 3))) if status == 'realizado' else None,
                account=conta,
                category=categoria,
                observacoes='Receita prevista baseada em servicos prestados.'
            ))
        return receitas

    def _build_despesas(self, user, month_start, month_end, contas, categories, count, today):
        despesas = []
        for _ in range(count):
            nome_cat, descricao = random.choice(DESPESA_DESCRICOES)
            categoria = categories[nome_cat]
            conta = random.choice(contas)
            vencimento = self._random_date(month_start, month_end)
            status = self._pick_status(vencimento, today, allow_realizado=True)
            valor = Decimal(str(random.randint(200, 4200)))
            despesas.append(Transaction(
                user=user,
                tipo='despesa',
                status=status,
                descricao=f'{descricao} ({month_start.strftime("%m/%Y")})',
                valor=valor,
                data_vencimento=vencimento,
                data_pagamento=(vencimento + timedelta(days=random.randint(0, 4))) if status == 'realizado' else None,
                account=conta,
                category=categoria,
                observacoes='Saida operacional gerada para simulacao.'
            ))
        return despesas

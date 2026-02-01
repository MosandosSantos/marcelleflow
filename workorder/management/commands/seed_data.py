"""
Comando para popular o banco com dados de exemplo.
Uso: python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from clients.models import Client
from provider.models import Provider
from servicetype.models import ServiceType
from workorderstatus.models import ServiceOrderStatus
from workorder.models import WorkOrder
from datetime import date, timedelta

User = get_user_model()


class Command(BaseCommand):
    help = 'Popula o banco de dados com dados de exemplo'

    def handle(self, *args, **kwargs):
        self.stdout.write('Populando banco de dados...\n')

        # Criar status conforme PRD
        statuses = [
            # Abertas (OPEN)
            {'group_code': 'OPEN', 'group_name': 'Abertas', 'group_color': 'orange', 'status_code': 'CREATED', 'status_name': 'Criada', 'status_order': 1, 'is_final': False},
            {'group_code': 'OPEN', 'group_name': 'Abertas', 'group_color': 'orange', 'status_code': 'WAITING_SCHEDULING', 'status_name': 'Aguardando agendamento', 'status_order': 2, 'is_final': False},
            {'group_code': 'OPEN', 'group_name': 'Abertas', 'group_color': 'orange', 'status_code': 'SCHEDULED', 'status_name': 'Agendada', 'status_order': 3, 'is_final': False},
            # Em Andamento (IN_PROGRESS)
            {'group_code': 'IN_PROGRESS', 'group_name': 'Em Andamento', 'group_color': 'blue', 'status_code': 'IN_ROUTE', 'status_name': 'Em deslocamento', 'status_order': 4, 'is_final': False},
            {'group_code': 'IN_PROGRESS', 'group_name': 'Em Andamento', 'group_color': 'blue', 'status_code': 'IN_EXECUTION', 'status_name': 'Em execu??o', 'status_order': 5, 'is_final': False},
            {'group_code': 'IN_PROGRESS', 'group_name': 'Em Andamento', 'group_color': 'blue', 'status_code': 'PAUSED', 'status_name': 'Pausada', 'status_order': 6, 'is_final': False},
            {'group_code': 'IN_PROGRESS', 'group_name': 'Em Andamento', 'group_color': 'blue', 'status_code': 'WAITING_MATERIAL', 'status_name': 'Aguardando material', 'status_order': 7, 'is_final': False},
            # Em Valida??o (VALIDATION)
            {'group_code': 'VALIDATION', 'group_name': 'Em Valida??o', 'group_color': 'green', 'status_code': 'WAITING_VALIDATION', 'status_name': 'Aguardando valida??o', 'status_order': 8, 'is_final': False},
            {'group_code': 'VALIDATION', 'group_name': 'Em Valida??o', 'group_color': 'green', 'status_code': 'REWORK', 'status_name': 'Retrabalho', 'status_order': 9, 'is_final': False},
            # Finalizadas (CLOSED)
            {'group_code': 'CLOSED', 'group_name': 'Finalizadas', 'group_color': 'gray', 'status_code': 'COMPLETED', 'status_name': 'Conclu?da', 'status_order': 10, 'is_final': True},
            {'group_code': 'CLOSED', 'group_name': 'Finalizadas', 'group_color': 'gray', 'status_code': 'FINANCIAL_CLOSED', 'status_name': 'Encerrada financeiramente', 'status_order': 11, 'is_final': True},
            {'group_code': 'CLOSED', 'group_name': 'Finalizadas', 'group_color': 'gray', 'status_code': 'CANCELED', 'status_name': 'Cancelada', 'status_order': 12, 'is_final': True},
        ]

        for status in statuses:
            ServiceOrderStatus.objects.get_or_create(
                group_code=status['group_code'],
                status_code=status['status_code'],
                defaults={
                    'group_name': status['group_name'],
                    'group_color': status['group_color'],
                    'status_name': status['status_name'],
                    'status_order': status['status_order'],
                    'is_final': status['is_final'],
                    'is_active': True,
                }
            )
        self.stdout.write('-> Status PRD criados')

        # Criar tipos de servico
        servicos = [
            {'name': 'Instalacao Eletrica', 'description': 'Instalacao de sistemas eletricos'},
            {'name': 'Manutencao Hidraulica', 'description': 'Reparos em sistemas hidraulicos'},
            {'name': 'Pintura Residencial', 'description': 'Servicos de pintura'},
            {'name': 'Instalacao de Ar Condicionado', 'description': 'Instalacao e manutencao'},
        ]
        for servico in servicos:
            ServiceType.objects.get_or_create(name=servico['name'], defaults=servico)
        self.stdout.write('-> Tipos de servico criados')

        # ============= CRIAR USUÁRIOS PARA TODOS OS 5 PERFIS =============

        # 1. ADMIN
        if not User.objects.filter(email='admin@esferawork.com').exists():
            admin = User.objects.create_superuser(
                email='admin@esferawork.com',
                password='admin123',
                username='admin'
            )
            admin.role = 'admin'
            admin.save()
            self.stdout.write('-> Admin criado: admin@esferawork.com / admin123')

        # 2. OPERACIONAL
        if not User.objects.filter(email='operacional@esferawork.com').exists():
            operacional = User.objects.create_user(
                email='operacional@esferawork.com',
                password='operacional123',
                username='operacional'
            )
            operacional.role = 'operational'
            operacional.is_staff = True  # Permite acesso ao admin se necessário
            operacional.save()
            self.stdout.write('-> Operacional criado: operacional@esferawork.com / operacional123')

        # 3. FINANCEIRO
        if not User.objects.filter(email='financeiro@esferawork.com').exists():
            financeiro = User.objects.create_user(
                email='financeiro@esferawork.com',
                password='financeiro123',
                username='financeiro'
            )
            financeiro.role = 'financial'
            financeiro.is_staff = True  # Permite acesso ao admin se necessário
            financeiro.save()
            self.stdout.write('-> Financeiro criado: financeiro@esferawork.com / financeiro123')

        # 4. PRESTADOR (TECH)
        if not User.objects.filter(email='prestador@esferawork.com').exists():
            user_prestador = User.objects.create_user(
                email='prestador@esferawork.com',
                password='prestador123',
                username='prestador'
            )
            user_prestador.role = 'tech'
            user_prestador.save()

            Provider.objects.create(
                user=user_prestador,
                full_name='Joao Silva',
                email='prestador@esferawork.com',
                cpf='111.111.111-11',
                phone='(11) 98888-8888',
                street='Rua A',
                number='100',
                neighborhood='Centro',
                city='Sao Paulo',
                state='SP',
                zip_code='01000-000',
                bank_name='Banco do Brasil',
                bank_agency='0001',
                bank_account='12345-6',
                bank_pix_key='prestador@esferawork.com'
            )
            self.stdout.write('-> Prestador criado: prestador@esferawork.com / prestador123')

        # 5. CLIENTE (CUSTOMER)
        if not User.objects.filter(email='cliente@esferawork.com').exists():
            user_cliente = User.objects.create_user(
                email='cliente@esferawork.com',
                password='cliente123',
                username='cliente'
            )
            user_cliente.role = 'customer'
            user_cliente.save()

            Client.objects.create(
                user=user_cliente,
                full_name='Maria Santos',
                email='cliente@esferawork.com',
                cpf='222.222.222-22',
                phone='(11) 97777-7777',
                street='Rua B',
                number='200',
                neighborhood='Jardim',
                city='Sao Paulo',
                state='SP',
                zip_code='02000-000'
            )
            self.stdout.write('-> Cliente criado: cliente@esferawork.com / cliente123')

        # Criar OS de exemplo
        if WorkOrder.objects.count() == 0:
            cliente = Client.objects.first()
            prestador = Provider.objects.first()
            servico = ServiceType.objects.first()
            status_created = ServiceOrderStatus.objects.filter(status_code='CREATED').first()
            status_in_execution = ServiceOrderStatus.objects.filter(status_code='IN_EXECUTION').first()

            if cliente and prestador and servico and status_created and status_in_execution:
                WorkOrder.objects.create(
                    code='OS-2025-001',
                    client=cliente,
                    provider=prestador,
                    service_type=servico,
                    status=status_created,
                    description='Instalacao eletrica completa na sala',
                    scheduled_date=date.today() + timedelta(days=2),
                    estimated_time_minutes=240,
                    labor_cost=500.00
                )
                WorkOrder.objects.create(
                    code='OS-2025-002',
                    client=cliente,
                    provider=prestador,
                    service_type=ServiceType.objects.all()[1] if ServiceType.objects.count() > 1 else servico,
                    status=status_in_execution,
                    description='Reparo de vazamento na cozinha',
                    scheduled_date=date.today(),
                    estimated_time_minutes=120,
                    labor_cost=300.00
                )
                self.stdout.write('-> Ordens de servico criadas')

        self.stdout.write(self.style.SUCCESS('\n>>> Banco populado com sucesso!'))
        self.stdout.write('\n' + '='*60)
        self.stdout.write('CREDENCIAIS DE ACESSO - 5 PERFIS:')
        self.stdout.write('='*60)
        self.stdout.write('\n1. ADMIN (Acesso Total)')
        self.stdout.write('   Email: admin@esferawork.com')
        self.stdout.write('   Senha: admin123')
        self.stdout.write('\n2. OPERACIONAL (OS + Cadastros)')
        self.stdout.write('   Email: operacional@esferawork.com')
        self.stdout.write('   Senha: operacional123')
        self.stdout.write('\n3. FINANCEIRO (Transações Consolidadas)')
        self.stdout.write('   Email: financeiro@esferawork.com')
        self.stdout.write('   Senha: financeiro123')
        self.stdout.write('\n4. PRESTADOR (Minhas OS)')
        self.stdout.write('   Email: prestador@esferawork.com')
        self.stdout.write('   Senha: prestador123')
        self.stdout.write('\n5. CLIENTE (Minhas Solicitações)')
        self.stdout.write('   Email: cliente@esferawork.com')
        self.stdout.write('   Senha: cliente123')
        self.stdout.write('\n' + '='*60 + '\n')

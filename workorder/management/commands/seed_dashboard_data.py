"""
Comando para popular o banco com MUITOS dados de exemplo para o dashboard.
Uso: python manage.py seed_dashboard_data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from clients.models import Client
from provider.models import Provider
from servicetype.models import ServiceType
from workorderstatus.models import ServiceOrderStatus
from workorder.models import WorkOrder, WorkOrderEvaluation
from datetime import date, datetime, timedelta
import random
from decimal import Decimal

User = get_user_model()


class Command(BaseCommand):
    help = 'Popula o banco com dados realistas para o dashboard'

    def handle(self, *args, **kwargs):
        self.stdout.write('Populando banco com dados para dashboard...\n')

        # Criar status
        status_created, _ = ServiceOrderStatus.objects.get_or_create(
            group_code='OPEN',
            status_code='CREATED',
            defaults={
                'group_name': 'Abertas',
                'group_color': 'orange',
                'status_name': 'Criada',
                'status_order': 1,
                'is_final': False,
                'is_active': True,
            }
        )
        status_andamento, _ = ServiceOrderStatus.objects.get_or_create(
            group_code='IN_PROGRESS',
            status_code='IN_EXECUTION',
            defaults={
                'group_name': 'Em Andamento',
                'group_color': 'blue',
                'status_name': 'Em execu??o',
                'status_order': 5,
                'is_final': False,
                'is_active': True,
            }
        )
        status_concluido, _ = ServiceOrderStatus.objects.get_or_create(
            group_code='CLOSED',
            status_code='COMPLETED',
            defaults={
                'group_name': 'Finalizadas',
                'group_color': 'gray',
                'status_name': 'Conclu?da',
                'status_order': 10,
                'is_final': True,
                'is_active': True,
            }
        )
        self.stdout.write('-> Status criados')

        # Criar tipos de servico
        servicos_data = [
            {'name': 'Instalação Elétrica', 'description': 'Instalação de sistemas elétricos'},
            {'name': 'Manutenção Hidráulica', 'description': 'Reparos em sistemas hidráulicos'},
            {'name': 'Pintura Residencial', 'description': 'Serviços de pintura'},
            {'name': 'Instalação de Ar Condicionado', 'description': 'Instalação e manutenção'},
            {'name': 'Manutenção Preventiva', 'description': 'Manutenção preventiva geral'},
            {'name': 'Reparo de Eletrônicos', 'description': 'Conserto de eletrônicos'},
        ]
        servicos = []
        for servico_data in servicos_data:
            servico, _ = ServiceType.objects.get_or_create(
                name=servico_data['name'],
                defaults=servico_data
            )
            servicos.append(servico)
        self.stdout.write('-> Tipos de serviço criados')

        # Criar admin
        if not User.objects.filter(email='admin@esferawork.com').exists():
            admin = User.objects.create_superuser(
                email='admin@esferawork.com',
                password='admin123',
                username='admin'
            )
            admin.role = 'admin'
            admin.save()
            self.stdout.write('-> Admin criado')

        # Criar 5 prestadores
        prestadores_data = [
            {'name': 'João Silva', 'email': 'joao@provider.com', 'rating_avg': 4.8},
            {'name': 'Maria Santos', 'email': 'maria@provider.com', 'rating_avg': 4.5},
            {'name': 'Pedro Oliveira', 'email': 'pedro@provider.com', 'rating_avg': 4.2},
            {'name': 'Ana Costa', 'email': 'ana@provider.com', 'rating_avg': 4.9},
            {'name': 'Carlos Souza', 'email': 'carlos@provider.com', 'rating_avg': 3.8},
        ]

        prestadores = []
        for idx, prest_data in enumerate(prestadores_data):
            if not User.objects.filter(email=prest_data['email']).exists():
                user = User.objects.create_user(
                    email=prest_data['email'],
                    password='prestador123',
                    username=f'prestador{idx+1}'
                )
                user.role = 'tech'
                user.save()

                provider = Provider.objects.create(
                    user=user,
                    full_name=prest_data['name'],
                    email=prest_data['email'],
                    cpf=f'{111+idx}{111+idx}{111+idx}.{111+idx}{111+idx}{111+idx}-{11+idx}{11+idx}',
                    phone=f'(11) 9888{idx}-8888',
                    street=f'Rua {chr(65+idx)}',
                    number=f'{100*(idx+1)}',
                    neighborhood='Centro',
                    city='Rio de Janeiro',
                    state='RJ',
                    zip_code=f'0{idx+1}000-000',
                    bank_name='Banco do Brasil',
                    bank_agency=f'000{idx+1}',
                    bank_account=f'1234{idx}-{idx}',
                    bank_pix_key=prest_data['email']
                )
                prestadores.append((provider, prest_data['rating_avg']))
            else:
                provider = Provider.objects.get(user__email=prest_data['email'])
                prestadores.append((provider, prest_data['rating_avg']))

        self.stdout.write(f'-> {len(prestadores)} prestadores criados')

        # Criar 10 clientes
        clientes = []
        for i in range(1, 11):
            if not User.objects.filter(email=f'cliente{i}@email.com').exists():
                user = User.objects.create_user(
                    email=f'cliente{i}@email.com',
                    password='cliente123',
                    username=f'cliente{i}'
                )
                user.role = 'customer'
                user.save()

                cliente = Client.objects.create(
                    user=user,
                    full_name=f'Cliente {i}',
                    email=f'cliente{i}@email.com',
                    cpf=f'{200+i}{200+i}{200+i}.{200+i}{200+i}{200+i}-{20+i}{20+i}',
                    phone=f'(21) 9777{i}-7777',
                    street=f'Rua Cliente {i}',
                    number=f'{200+i}',
                    neighborhood='Baixada',
                    city='Nova Iguaçu' if i % 3 == 0 else 'Duque de Caxias' if i % 2 == 0 else 'São João de Meriti',
                    state='RJ',
                    zip_code=f'2{i:02d}00-000'
                )
                clientes.append(cliente)
            else:
                cliente = Client.objects.get(user__email=f'cliente{i}@email.com')
                clientes.append(cliente)

        self.stdout.write(f'-> {len(clientes)} clientes criados')

        # Criar 100 ordens de serviço distribuídas nos últimos 6 meses
        self.stdout.write('-> Criando 100 ordens de serviço...')

        today = datetime.now()
        os_created = 0

        for i in range(100):
            # Distribuir as datas nos últimos 6 meses
            days_ago = random.randint(0, 180)
            created_date = today - timedelta(days=days_ago)

            # Determinar status baseado na data (mais antigas = mais chance de estar concluída)
            if days_ago > 30:
                # OS antigas: 70% concluídas, 20% em andamento, 10% pendentes
                status_weights = [status_concluido, status_andamento, status_created]
                status = random.choices(status_weights, weights=[70, 20, 10])[0]
            elif days_ago > 7:
                # OS recentes: 40% concluídas, 40% em andamento, 20% pendentes
                status_weights = [status_concluido, status_andamento, status_created]
                status = random.choices(status_weights, weights=[40, 40, 20])[0]
            else:
                # OS muito recentes: 10% concluídas, 40% em andamento, 50% pendentes
                status_weights = [status_concluido, status_andamento, status_created]
                status = random.choices(status_weights, weights=[10, 40, 50])[0]

            cliente = random.choice(clientes)
            provider, expected_rating = random.choice(prestadores)
            servico = random.choice(servicos)

            # Gerar custos realistas
            labor_cost = Decimal(random.randint(200, 2000))
            estimated_time = random.randint(60, 480)  # 1 a 8 horas

            # Data agendada
            scheduled_date = created_date.date() + timedelta(days=random.randint(1, 7))

            # Se concluída, definir datas de início e fim
            started_at = None
            finished_at = None
            real_time = None

            if status == status_andamento:
                started_at = created_date + timedelta(days=random.randint(1, 3))
            elif status == status_concluido:
                started_at = created_date + timedelta(days=random.randint(1, 3))
                finished_at = started_at + timedelta(hours=random.randint(2, 12))
                real_time = random.randint(int(estimated_time * 0.8), int(estimated_time * 1.2))

            # Verificar se já existe
            code = f'OS-{2025}-{i+1:04d}'
            if not WorkOrder.objects.filter(code=code).exists():
                work_order = WorkOrder.objects.create(
                    code=code,
                    client=cliente,
                    provider=provider,
                    service_type=servico,
                    status=status,
                    description=f'Serviço de {servico.name} - {random.choice(["Residencial", "Comercial", "Industrial"])}',
                    scheduled_date=scheduled_date,
                    started_at=started_at,
                    finished_at=finished_at,
                    estimated_time_minutes=estimated_time,
                    real_time_minutes=real_time,
                    labor_cost=labor_cost,
                    created_at=created_date,
                    updated_at=finished_at if finished_at else created_date
                )

                # Criar avaliação para OS concluídas (80% de chance)
                if status == status_concluido and random.random() < 0.8:
                    # Rating baseado na expectativa do prestador com variação
                    rating = max(1, min(5, int(expected_rating + random.uniform(-0.5, 0.5))))

                    WorkOrderEvaluation.objects.create(
                        work_order=work_order,
                        rating=rating,
                        comment=random.choice([
                            'Excelente serviço, muito profissional!',
                            'Bom trabalho, chegou no prazo.',
                            'Serviço adequado.',
                            'Poderia melhorar a comunicação.',
                            'Ótimo atendimento e qualidade!',
                            '',  # Alguns sem comentário
                        ])
                    )

                os_created += 1

        self.stdout.write(f'-> {os_created} ordens de serviço criadas')

        self.stdout.write(self.style.SUCCESS('\n-> Banco populado com sucesso!'))
        self.stdout.write('\nEstatísticas:')
        self.stdout.write(f'  Total de OS: {WorkOrder.objects.count()}')
        self.stdout.write(f'  OS Pendentes: {WorkOrder.objects.filter(status=status_created).count()}')
        self.stdout.write(f'  OS Em Andamento: {WorkOrder.objects.filter(status=status_andamento).count()}')
        self.stdout.write(f'  OS Concluídas: {WorkOrder.objects.filter(status=status_concluido).count()}')
        self.stdout.write(f'  Avaliações: {WorkOrderEvaluation.objects.count()}')
        self.stdout.write(f'\nAcesse o dashboard: http://localhost:8000/dashboard/')
        self.stdout.write(f'Login: admin@esferawork.com / admin123')

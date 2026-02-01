"""
Comando Django para migrar roles antigos para novos.

Converte usuários com role 'manager' para 'operational' como parte da
reestruturação do sistema de 4 para 5 níveis de usuário.

Uso:
    python manage.py migrate_roles
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Migra roles antigos para novos (manager -> operational)'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Iniciando migracao de roles...'))
        self.stdout.write('')

        # Contar usuários antes da migração
        manager_users = User.objects.filter(role='manager')
        manager_count = manager_users.count()

        if manager_count == 0:
            self.stdout.write(self.style.SUCCESS('>>> Nenhum usuario com role "manager" encontrado.'))
            self.stdout.write(self.style.SUCCESS('>>> Migracao nao necessaria.'))
            return

        self.stdout.write(f'Encontrados {manager_count} usuario(s) com role "manager":')
        self.stdout.write('')

        # Listar usuários que serão migrados
        for user in manager_users:
            self.stdout.write(f'  - {user.email} (username: {user.username})')

        self.stdout.write('')
        self.stdout.write(self.style.WARNING('Convertendo "manager" -> "operational"...'))

        # Executar a migração
        updated_count = User.objects.filter(role='manager').update(role='operational')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'>>> {updated_count} usuario(s) migrado(s) com sucesso!'))
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Migracao concluida.'))
        self.stdout.write('')

        # Exibir resumo dos roles atuais
        self.stdout.write(self.style.WARNING('Resumo dos roles no sistema:'))
        self.stdout.write('')

        role_summary = (
            User.objects
            .values('role')
            .annotate(count=__import__('django.db.models', fromlist=['Count']).Count('id'))
            .order_by('role')
        )

        for item in role_summary:
            role = item['role'] or '(vazio)'
            count = item['count']
            self.stdout.write(f'  - {role}: {count} usuario(s)')

        self.stdout.write('')

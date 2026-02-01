from django.core.management.base import BaseCommand
from clients.models import Client


class Command(BaseCommand):
    help = 'Lista clientes sem usuário vinculado (user_id nulo).'

    def handle(self, *args, **options):
        queryset = Client.objects.filter(user__isnull=True)
        total = queryset.count()
        if not total:
            self.stdout.write('Nenhum cliente sem usuário vinculado.')
            return

        self.stdout.write(f'Clientes sem usuário vinculado: {total}')
        for client in queryset.order_by('full_name'):
            self.stdout.write(f'- {client.id} | {client.full_name} | {client.email}')

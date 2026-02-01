import uuid
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from clients.models import Client


class Command(BaseCommand):
    help = 'Cria usuários e vincula clientes que estiverem sem user.'

    def handle(self, *args, **options):
        User = get_user_model()
        queryset = Client.objects.filter(user__isnull=True)
        total = queryset.count()
        if not total:
            self.stdout.write('Nenhum cliente sem usuário vinculado.')
            return

        self.stdout.write(f'Clientes sem usuário vinculado: {total}')
        for client in queryset.order_by('full_name'):
            base = slugify(client.full_name) or f'cliente-{uuid.uuid4().hex[:6]}'
            email = client.email or f'{base}-{uuid.uuid4().hex[:6]}@esferawork.local'
            username = base[:150]
            user = User.objects.create_user(
                email=email,
                password=None,
                username=username,
                role=User.ROLE_CUSTOMER
            )
            user.set_unusable_password()
            user.save(update_fields=['password'])

            client.user = user
            if not client.email:
                client.email = email
            client.save(update_fields=['user', 'email'])

            self.stdout.write(f'- Vinculado: {client.full_name} ({client.id})')

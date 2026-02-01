from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings
import os


class Command(BaseCommand):
    help = "Cria usuarios padrao (admin, operacional, financeiro) com senha definida."

    def add_arguments(self, parser):
        parser.add_argument('--admin-email', default='admin@esferaflow.com')
        parser.add_argument('--operational-email', default='operacional@esferaflow.com')
        parser.add_argument('--financial-email', default='financeiro@esferaflow.com')
        parser.add_argument('--password', default=None)

    def handle(self, *args, **options):
        User = get_user_model()
        password = options.get('password') or os.getenv('ESFERA_DEFAULT_PASSWORD') or 'esfera2026'

        users = [
            {
                'email': options['admin_email'],
                'role': 'admin',
                'is_staff': True,
                'is_superuser': True,
                'first_name': 'Admin',
            },
            {
                'email': options['operational_email'],
                'role': 'operational',
                'is_staff': False,
                'is_superuser': False,
                'first_name': 'Operacional',
            },
            {
                'email': options['financial_email'],
                'role': 'financial',
                'is_staff': False,
                'is_superuser': False,
                'first_name': 'Financeiro',
            },
        ]

        for data in users:
            email = data['email']
            username = email
            if User.objects.filter(username=username).exclude(email=email).exists():
                username = email
            user, created = User.objects.update_or_create(
                email=email,
                defaults={
                    'username': username,
                    'role': data['role'],
                    'is_staff': data['is_staff'],
                    'is_superuser': data['is_superuser'],
                    'first_name': data['first_name'],
                    'is_active': True,
                }
            )
            user.set_password(password)
            user.save()
            action = 'created' if created else 'updated'
            self.stdout.write(self.style.SUCCESS(f"{action}: {email}"))

        self.stdout.write(self.style.SUCCESS('Usuarios padrao prontos.'))

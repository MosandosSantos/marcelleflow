from decimal import Decimal
import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('nome', models.CharField(max_length=100, verbose_name='Nome da Conta')),
                ('tipo', models.CharField(choices=[('conta_corrente', 'Conta Corrente'), ('poupanca', 'Poupanca'), ('carteira', 'Carteira (Dinheiro)'), ('investimento', 'Investimento'), ('outros', 'Outros')], default='conta_corrente', max_length=20, verbose_name='Tipo de Conta')),
                ('saldo_inicial', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=15, verbose_name='Saldo Inicial')),
                ('ativa', models.BooleanField(default=True, verbose_name='Conta Ativa')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='finance_accounts', to=settings.AUTH_USER_MODEL, verbose_name='Usuario')),
            ],
            options={
                'verbose_name': 'Conta Financeira',
                'verbose_name_plural': 'Contas Financeiras',
                'ordering': ['-created_at'],
                'unique_together': {('user', 'nome')},
            },
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('nome', models.CharField(max_length=100, verbose_name='Nome da Categoria')),
                ('tipo', models.CharField(choices=[('receita', 'Receita'), ('despesa', 'Despesa')], max_length=10, verbose_name='Tipo')),
                ('descricao', models.TextField(blank=True, verbose_name='Descricao')),
                ('ativa', models.BooleanField(default=True, verbose_name='Categoria Ativa')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='finance_categories', to=settings.AUTH_USER_MODEL, verbose_name='Usuario')),
            ],
            options={
                'verbose_name': 'Categoria Financeira',
                'verbose_name_plural': 'Categorias Financeiras',
                'ordering': ['tipo', 'nome'],
                'unique_together': {('user', 'nome', 'tipo')},
            },
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('tipo', models.CharField(choices=[('receita', 'Receita'), ('despesa', 'Despesa')], max_length=10, verbose_name='Tipo')),
                ('status', models.CharField(choices=[('previsto', 'Previsto'), ('realizado', 'Realizado'), ('atrasado', 'Atrasado')], default='previsto', max_length=10, verbose_name='Status')),
                ('descricao', models.CharField(max_length=255, verbose_name='Descricao')),
                ('valor', models.DecimalField(decimal_places=2, max_digits=15, verbose_name='Valor')),
                ('data_vencimento', models.DateField(verbose_name='Data de Vencimento')),
                ('data_pagamento', models.DateField(blank=True, null=True, verbose_name='Data de Pagamento')),
                ('observacoes', models.TextField(blank=True, verbose_name='Observacoes')),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='transactions', to='finance.account', verbose_name='Conta')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='transactions', to='finance.category', verbose_name='Categoria')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='finance_transactions', to=settings.AUTH_USER_MODEL, verbose_name='Usuario')),
            ],
            options={
                'verbose_name': 'Transacao',
                'verbose_name_plural': 'Transacoes',
                'ordering': ['-data_vencimento', '-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['user', 'status'], name='finance_tra_user_id_5b993e_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['user', 'tipo'], name='finance_tra_user_id_2d2484_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['data_vencimento'], name='finance_tra_data_ve_f03a62_idx'),
        ),
    ]

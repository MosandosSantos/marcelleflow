from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0003_account_bank_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='agencia',
            field=models.CharField(blank=True, max_length=10, verbose_name='Agencia'),
        ),
        migrations.AddField(
            model_name='account',
            name='agencia_dv',
            field=models.CharField(blank=True, max_length=2, verbose_name='DV Agencia'),
        ),
        migrations.AddField(
            model_name='account',
            name='conta_numero',
            field=models.CharField(blank=True, max_length=20, verbose_name='Numero da Conta'),
        ),
        migrations.AddField(
            model_name='account',
            name='conta_dv',
            field=models.CharField(blank=True, max_length=2, verbose_name='DV Conta'),
        ),
    ]

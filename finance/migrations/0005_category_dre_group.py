from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0004_account_bank_details'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='dre_group',
            field=models.CharField(blank=True, choices=[('receita_operacional', 'Receita operacional'), ('impostos_venda', 'Impostos sobre a venda'), ('cmv', 'CMV/CPV'), ('despesas_venda', 'Despesas com vendas'), ('despesas_financeiras', 'Despesas financeiras'), ('receita_financeira', 'Receita financeira'), ('despesas_gerais_adm', 'Despesas gerais e administrativas')], max_length=40, verbose_name='Grupo DRE'),
        ),
    ]

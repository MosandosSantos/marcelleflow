from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('workorder', '0009_workorder_address_city_workorder_address_complement_and_more'),
        ('finance', '0007_transaction_expense_type_transaction_is_recurring_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='work_order',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='finance_transaction',
                help_text='Vinculo automatico com OS para contas a receber.',
                to='workorder.workorder',
                verbose_name='Ordem de Servico',
            ),
        ),
    ]

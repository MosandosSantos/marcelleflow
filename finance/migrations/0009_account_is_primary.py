from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0008_transaction_work_order'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='is_primary',
            field=models.BooleanField(default=False, verbose_name='Conta Principal'),
        ),
    ]

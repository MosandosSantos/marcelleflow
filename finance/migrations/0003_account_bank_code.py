from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0002_remove_category_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='bank_code',
            field=models.CharField(blank=True, max_length=10, verbose_name='Codigo do Banco'),
        ),
    ]

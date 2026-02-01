from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0012_transaction_is_projection'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE finance_transaction "
                "ADD COLUMN IF NOT EXISTS is_projection boolean NOT NULL DEFAULT false;"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]

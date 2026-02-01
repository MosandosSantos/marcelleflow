from django.conf import settings
from django.db import migrations


def copy_forward(apps, schema_editor):
    Category = apps.get_model('finance', 'Category')
    seen = {}
    for category in Category.objects.all().order_by('id'):
        key = (category.nome, category.tipo)
        if key in seen:
            continue
        seen[key] = category.id

    Transaction = apps.get_model('finance', 'Transaction')
    for category in Category.objects.all().order_by('id'):
        key = (category.nome, category.tipo)
        canonical_id = seen.get(key)
        if canonical_id and category.id != canonical_id:
            Transaction.objects.filter(category_id=category.id).update(category_id=canonical_id)

    for category in Category.objects.all().order_by('-id'):
        key = (category.nome, category.tipo)
        canonical_id = seen.get(key)
        if canonical_id and category.id != canonical_id:
            category.delete()


def copy_backward(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(copy_forward, copy_backward),
        migrations.AlterUniqueTogether(
            name='category',
            unique_together={('nome', 'tipo')},
        ),
        migrations.RemoveField(
            model_name='category',
            name='user',
        ),
    ]

from decimal import Decimal
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import WorkOrder
from provider.models import Provider

CLOSED_STATUS_CODES = {'COMPLETED', 'FINANCIAL_CLOSED'}


@receiver(pre_save, sender=WorkOrder)
def cache_previous_workorder_state(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_evaluation_rating = None
        instance._previous_status_code = None
        instance._previous_provider_id = None
        return

    previous = WorkOrder.objects.filter(pk=instance.pk).select_related('status').first()
    if previous:
        instance._previous_evaluation_rating = previous.evaluation_rating
        instance._previous_status_code = previous.status.status_code if previous.status else None
        instance._previous_provider_id = previous.provider_id


@receiver(post_save, sender=WorkOrder)
def update_provider_rating(sender, instance, created, **kwargs):
    if not instance.provider_id:
        return

    if instance.status is None or instance.status.status_code not in CLOSED_STATUS_CODES:
        return

    rating = instance.evaluation_rating or 0
    if rating <= 0:
        return

    prev_rating = getattr(instance, '_previous_evaluation_rating', None)
    prev_status_code = getattr(instance, '_previous_status_code', None)
    if prev_status_code in CLOSED_STATUS_CODES and prev_rating and prev_rating > 0:
        return

    provider = Provider.objects.filter(pk=instance.provider_id).first()
    if not provider:
        return

    current_count = int(provider.rating_count or 0)
    current_avg = Decimal(provider.rating_avg or 0)

    new_count = current_count + 1
    new_avg = (current_avg * current_count + Decimal(rating)) / Decimal(new_count)

    provider.rating_count = new_count
    provider.rating_avg = new_avg.quantize(Decimal('0.01'))
    provider.save(update_fields=['rating_count', 'rating_avg'])

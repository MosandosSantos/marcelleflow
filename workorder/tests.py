from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from clients.models import Client
from servicetype.models import ServiceType
from workorder.forms import WorkOrderForm
from workorder.models import WorkOrder


class WorkOrderFormTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email='cliente@example.com',
            password='senha-forte-123',
            username='cliente-teste',
            role=User.ROLE_CUSTOMER,
        )
        self.client = Client.objects.create(
            user=self.user,
            full_name='Cliente Teste',
            email='cliente@example.com',
            cpf='52998224725',
            phone='11999999999',
            street='Rua A',
            number='100',
            neighborhood='Centro',
            city='Sao Paulo',
            state='SP',
            zip_code='01001000',
        )
        self.service_type = ServiceType.objects.create(
            name='Servico Teste',
            estimated_price=100,
            unit_price=100,
        )

    def _base_form_data(self, **overrides):
        data = {
            'code': 'OS-TESTE-001',
            'client': str(self.client.pk),
            'service_type': str(self.service_type.pk),
            'description': 'Descricao de teste',
        }
        data.update(overrides)
        return data

    def test_scheduled_date_before_today_is_invalid_on_create(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        form = WorkOrderForm(
            data=self._base_form_data(scheduled_date=yesterday.isoformat()),
            instance=WorkOrder(id=None),
        )
        self.assertFalse(form.is_valid())
        self.assertIn('scheduled_date', form.errors)

    def test_scheduled_date_today_is_valid_on_create(self):
        today = timezone.localdate()
        form = WorkOrderForm(
            data=self._base_form_data(scheduled_date=today.isoformat()),
            instance=WorkOrder(id=None),
        )
        self.assertTrue(form.is_valid())

    def test_estimated_time_field_is_not_exposed_in_form(self):
        form = WorkOrderForm()
        self.assertNotIn('estimated_time_minutes', form.fields)

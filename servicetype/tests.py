from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from servicetype.models import CostItem, ServiceCost, ServiceType, TaxProfile
from servicetype.services import simulate_service_pricing


class PricingEngineTest(TestCase):
    def setUp(self):
        self.tax_profile = TaxProfile.objects.create(
            name='Simples Nacional',
            iss=Decimal('5.00'),
            federal_taxes=Decimal('3.50'),
            financial_fees=Decimal('1.50')
        )
        self.service_type = ServiceType.objects.create(
            name='Instalação elétrica',
            description='Instalação exemplificativa',
            ferramentas='Escada, Multímetro',
            duracao_estimada=60,
            duracao_media=75,
            billing_unit='unidade',
            tax_profile=self.tax_profile,
            margin_target=Decimal('25.00'),
            margin_minimum=Decimal('10.00'),
            volume_baseline=2
        )
        self.cost_item = CostItem.objects.create(
            name='Mão de obra técnica',
            description='Hora técnica aplicada',
            cost_type='direto',
            billing_unit='hora',
            unit_cost=Decimal('90.00')
        )
        ServiceCost.objects.create(
            service_type=self.service_type,
            cost_item=self.cost_item,
            quantity=Decimal('1.00'),
            unit_cost_snapshot=Decimal('85.00'),
            is_required=True
        )

    def test_simulation_default_margin(self):
        result = simulate_service_pricing(self.service_type)
        self.assertEqual(result['direct_cost'], Decimal('85.00'))
        self.assertEqual(result['tax_rate'], Decimal('10.00'))
        self.assertEqual(result['tax_total'], Decimal('8.50'))
        self.assertEqual(result['net_before_margin'], Decimal('93.50'))
        self.assertEqual(result['margin_rate'], Decimal('25.00'))
        self.assertEqual(result['margin_amount'], Decimal('23.38'))
        self.assertEqual(result['price'], Decimal('116.88'))
        self.assertEqual(result['volume'], 2)
        self.assertEqual(result['revenue'], Decimal('233.76'))
        self.assertEqual(result['profit'], Decimal('46.76'))
        self.assertEqual(result['profit_margin_pct'], Decimal('20.00'))

    def test_simulation_custom_parameters(self):
        result = simulate_service_pricing(
            self.service_type,
            margin_rate=Decimal('30.00'),
            cost_adjustment=Decimal('10.00'),
            tax_rate_delta=Decimal('2.00'),
            volume=4
        )
        self.assertEqual(result['direct_cost'], Decimal('95.00'))
        self.assertEqual(result['tax_rate'], Decimal('12.00'))
        self.assertTrue(result['price'] > result['net_before_margin'])
        self.assertEqual(result['volume'], 4)
        self.assertGreater(result['profit'], Decimal('0.00'))

    def test_margin_validation(self):
        service = ServiceType(
            name='Serviço inválido',
            description='Teste',
            ferramentas='',
            duracao_estimada=10,
            duracao_media=10,
            billing_unit='unidade',
            margin_target=Decimal('5.00'),
            margin_minimum=Decimal('10.00')
        )
        with self.assertRaises(ValidationError):
            service.full_clean()

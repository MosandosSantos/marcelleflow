from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from .models import ServiceType

DECIMAL_ZERO = Decimal('0.00')
DEFAULT_MARGIN = Decimal('0.00')


def quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _unit_cost_for_each(service_cost):
    return service_cost.unit_cost_snapshot or service_cost.cost_item.unit_cost or DECIMAL_ZERO


def calculate_direct_cost(service_type: ServiceType) -> Decimal:
    total = DECIMAL_ZERO
    for service_cost in service_type.service_costs.select_related('cost_item').all():
        line_cost = _unit_cost_for_each(service_cost) * service_cost.quantity
        total += line_cost
    return quantize(total)


def calculate_tax_value(service_type: ServiceType, direct_cost: Decimal, tax_rate_override: Optional[Decimal] = None) -> Decimal:
    rate = tax_rate_override if tax_rate_override is not None else (
        service_type.tax_profile.total_rate() if service_type.tax_profile else DECIMAL_ZERO
    )
    return quantize(direct_cost * rate / Decimal('100'))


def calculate_margin_value(amount: Decimal, margin_rate: Decimal) -> Decimal:
    return quantize(amount * margin_rate / Decimal('100'))


def is_margin_valid(service_type: ServiceType, margin_rate: Optional[Decimal] = None) -> bool:
    rate = margin_rate if margin_rate is not None else service_type.margin_target
    return rate >= service_type.margin_minimum


def simulate_service_pricing(
    service_type: ServiceType,
    margin_rate: Optional[Decimal] = None,
    cost_adjustment: Optional[Decimal] = None,
    tax_rate_delta: Optional[Decimal] = None,
    volume: Optional[int] = None
) -> dict:
    direct_cost = calculate_direct_cost(service_type)
    adjusted_cost = max(
        DECIMAL_ZERO,
        direct_cost + (cost_adjustment or DECIMAL_ZERO)
    )

    base_tax_rate = service_type.tax_profile.total_rate() if service_type.tax_profile else DECIMAL_ZERO
    applied_tax_rate = base_tax_rate + (tax_rate_delta or DECIMAL_ZERO)
    tax_total = calculate_tax_value(service_type, adjusted_cost, applied_tax_rate)

    net_total = adjusted_cost + tax_total
    effective_margin_rate = margin_rate if margin_rate is not None else service_type.margin_target
    margin_amount = calculate_margin_value(net_total, effective_margin_rate)

    price = net_total + margin_amount
    safe_volume = max(1, volume or service_type.volume_baseline or 1)

    revenue = quantize(price * Decimal(safe_volume))
    cost_for_volume = quantize(adjusted_cost * Decimal(safe_volume))
    tax_for_volume = quantize(tax_total * Decimal(safe_volume))
    profit = quantize(revenue - cost_for_volume - tax_for_volume)

    profit_margin_pct = quantize((profit / revenue * Decimal('100')) if revenue > 0 else DECIMAL_ZERO)

    return {
        'direct_cost': quantize(adjusted_cost),
        'tax_rate': quantize(applied_tax_rate),
        'tax_total': tax_total,
        'net_before_margin': quantize(net_total),
        'margin_rate': quantize(effective_margin_rate),
        'margin_amount': margin_amount,
        'price': quantize(price),
        'volume': safe_volume,
        'revenue': revenue,
        'profit': profit,
        'profit_margin_pct': profit_margin_pct,
    }


def compare_estimated_vs_real_margin(service_type: ServiceType) -> dict:
    """
    Compara a margem de lucro estimada (baseada em ServiceCost) com a margem real
    (baseada em WorkOrders e Transactions).

    Retorna um dicionário com:
    - estimated_cost: custo total estimado
    - estimated_margin: margem estimada (R$ e %)
    - real_data: dados reais de receita, custo e margem
    - deviation: desvio entre estimado e real
    - accuracy: precisão da estimativa (%)
    """
    # Custo e margem estimados
    estimated_cost = service_type.total_estimated_cost()
    estimated_margin_value = service_type.estimated_profit_margin_value()
    estimated_margin_percentage = service_type.estimated_profit_margin_percentage()

    # Dados reais de WorkOrders e Transactions
    real_data = service_type.calculate_real_profit_from_workorders()

    # Desvios (Real - Estimado)
    cost_deviation = real_data['total_real_cost'] - estimated_cost
    cost_deviation_percentage = DECIMAL_ZERO
    if estimated_cost > 0:
        cost_deviation_percentage = (cost_deviation / estimated_cost) * 100

    margin_deviation_value = real_data['profit_margin_value'] - estimated_margin_value
    margin_deviation_percentage = real_data['profit_margin_percentage'] - estimated_margin_percentage

    # Precisão da estimativa (100% = perfeito, 0% = muito errado)
    cost_accuracy = DECIMAL_ZERO
    if estimated_cost > 0:
        cost_accuracy = max(DECIMAL_ZERO, 100 - abs(cost_deviation_percentage))

    margin_accuracy = DECIMAL_ZERO
    if estimated_margin_percentage > 0:
        margin_accuracy = max(DECIMAL_ZERO, 100 - abs((margin_deviation_percentage / estimated_margin_percentage) * 100))

    return {
        'estimated_cost': quantize(estimated_cost),
        'estimated_margin_value': quantize(estimated_margin_value),
        'estimated_margin_percentage': quantize(estimated_margin_percentage),
        'real_revenue': quantize(real_data['total_revenue']),
        'real_cost': quantize(real_data['total_real_cost']),
        'real_margin_value': quantize(real_data['profit_margin_value']),
        'real_margin_percentage': quantize(real_data['profit_margin_percentage']),
        'cost_deviation': quantize(cost_deviation),
        'cost_deviation_percentage': quantize(cost_deviation_percentage),
        'margin_deviation_value': quantize(margin_deviation_value),
        'margin_deviation_percentage': quantize(margin_deviation_percentage),
        'cost_accuracy': quantize(cost_accuracy),
        'margin_accuracy': quantize(margin_accuracy),
        'work_orders_count': real_data['work_orders_count'],
    }


def get_services_profit_summary() -> dict:
    """
    Retorna um resumo consolidado de margem de lucro de todos os serviços.

    Retorna:
    - total_services: total de serviços ativos
    - services_with_costs: serviços com composição de custos cadastrada
    - services_with_orders: serviços com OS executadas
    - avg_estimated_margin: margem estimada média (%)
    - avg_real_margin: margem real média (%)
    - margin_deviation_avg: desvio médio entre estimado e real (%)
    """
    from django.db.models import Avg, Count, Q

    services = ServiceType.objects.filter(is_active=True)

    total_services = services.count()
    services_with_costs = services.filter(service_costs__isnull=False).distinct().count()
    services_with_orders = services.filter(work_orders__isnull=False).distinct().count()

    # Calcular médias
    estimated_margins = []
    real_margins = []

    for service in services.filter(work_orders__isnull=False).distinct():
        estimated_margin = service.estimated_profit_margin_percentage()
        real_data = service.calculate_real_profit_from_workorders()

        if real_data['work_orders_count'] > 0:
            estimated_margins.append(estimated_margin)
            real_margins.append(real_data['profit_margin_percentage'])

    avg_estimated_margin = DECIMAL_ZERO
    avg_real_margin = DECIMAL_ZERO
    margin_deviation_avg = DECIMAL_ZERO

    if estimated_margins:
        avg_estimated_margin = sum(estimated_margins) / len(estimated_margins)
        avg_real_margin = sum(real_margins) / len(real_margins)
        margin_deviation_avg = avg_real_margin - avg_estimated_margin

    return {
        'total_services': total_services,
        'services_with_costs': services_with_costs,
        'services_with_orders': services_with_orders,
        'avg_estimated_margin': quantize(avg_estimated_margin),
        'avg_real_margin': quantize(avg_real_margin),
        'margin_deviation_avg': quantize(margin_deviation_avg),
    }

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import TruncMonth

from .models import Transaction, Account


def get_finance_queryset(user=None, account_id=None, category_id=None):
    qs = Transaction.objects.all()
    if user:
        qs = qs.filter(user=user)
    if account_id:
        qs = qs.filter(account_id=account_id)
    if category_id:
        qs = qs.filter(category_id=category_id)
    return qs


def apply_phase_filter(qs, phase, start_date, end_date):
    qs = qs.exclude(status='cancelado').filter(
        data_vencimento__gte=start_date,
        data_vencimento__lte=end_date,
    )
    if phase == 'futuro':
        qs = qs.filter(status__in=['previsto', 'atrasado'])
    else:
        qs = qs.filter(status='realizado')
    date_field = 'data_vencimento'
    return qs, date_field


def _last_day_of_month(value):
    if value.month == 12:
        return date(value.year, 12, 31)
    next_month = date(value.year, value.month + 1, 1)
    return next_month - timedelta(days=1)


def build_dre_context(start_date, end_date, phase, account_id=None, category_id=None, user=None):
    """
    Monta contexto de DRE com base em transacoes.
    phase: 'consolidado' usa realizados, 'futuro' usa previstos/atrasados.
    """
    qs = get_finance_queryset(user=user, account_id=account_id, category_id=category_id)
    qs, date_field = apply_phase_filter(qs, phase, start_date, end_date)

    months = _month_list(start_date, end_date)
    month_names = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    month_labels = [
        {
            'key': month.strftime('%Y-%m'),
            'label': f"{month_names[month.month - 1]}/{str(month.year)[-2:]}",
            'year': month.year,
            'month': month.month,
        }
        for month in months
    ]
    month_index = {label['key']: idx for idx, label in enumerate(month_labels)}

    def match_category(name, keywords):
        if not name:
            return False
        name_lower = name.lower()
        return any(keyword in name_lower for keyword in keywords)

    groups = {
        'receita_operacional': [Decimal('0.00') for _ in month_labels],
        'impostos_venda': [Decimal('0.00') for _ in month_labels],
        'cmv': [Decimal('0.00') for _ in month_labels],
        'despesas_venda': [Decimal('0.00') for _ in month_labels],
        'despesas_financeiras': [Decimal('0.00') for _ in month_labels],
        'receita_financeira': [Decimal('0.00') for _ in month_labels],
        'despesas_gerais_adm': [Decimal('0.00') for _ in month_labels],
    }

    aggregates = (
        qs.annotate(month=TruncMonth(date_field))
        .values('tipo', 'category__nome', 'category__dre_group', 'month')
        .annotate(total=Sum('valor'))
    )

    for item in aggregates:
        month_key = item['month'].strftime('%Y-%m')
        idx = month_index.get(month_key)
        if idx is None:
            continue
        total = item['total'] or Decimal('0.00')
        category_name = item['category__nome'] or ''
        dre_group = item.get('category__dre_group') or ''

        if item['tipo'] == 'receita':
            if dre_group == 'receita_financeira' or match_category(category_name, ['juros', 'rendimento', 'financeira', 'tarifa']):
                groups['receita_financeira'][idx] += total
            else:
                groups['receita_operacional'][idx] += total
        else:
            if dre_group == 'impostos_venda' or match_category(category_name, ['imposto', 'tributo', 'iss', 'icms', 'simples']):
                groups['impostos_venda'][idx] += total
            elif dre_group == 'cmv' or match_category(category_name, ['custo', 'cmv', 'cpv', 'mercadoria', 'producao']):
                groups['cmv'][idx] += total
            elif dre_group == 'despesas_venda' or match_category(category_name, ['venda', 'comissao', 'marketing', 'publicidade', 'frete']):
                groups['despesas_venda'][idx] += total
            elif dre_group == 'despesas_financeiras' or match_category(category_name, ['juros', 'tarifa', 'taxa', 'banco', 'financeira']):
                groups['despesas_financeiras'][idx] += total
            else:
                groups['despesas_gerais_adm'][idx] += total

    def sum_lists(*lists):
        return [sum(values) for values in zip(*lists)]

    receita_liquida = [
        groups['receita_operacional'][idx] - groups['impostos_venda'][idx]
        for idx in range(len(month_labels))
    ]
    lucro_bruto = [
        receita_liquida[idx] - groups['cmv'][idx]
        for idx in range(len(month_labels))
    ]
    despesas_operacionais = sum_lists(
        groups['despesas_venda'],
        groups['despesas_gerais_adm'],
    )
    lucro_liquido = [
        lucro_bruto[idx]
        - despesas_operacionais[idx]
        - groups['despesas_financeiras'][idx]
        + groups['receita_financeira'][idx]
        for idx in range(len(month_labels))
    ]

    def build_row(label, values_list, tone='neutral', emphasize=False, value_format='currency'):
        return {
            'label': label,
            'values_list': values_list,
            'total': sum(values_list),
            'tone': tone,
            'emphasize': emphasize,
            'value_format': value_format,
        }

    dre_rows = [
        build_row('(+) Receita Operacional', groups['receita_operacional'], tone='positive', emphasize=True),
        build_row('(-) Impostos sobre a venda', groups['impostos_venda'], tone='negative'),
        build_row('(=) Receita líquida', receita_liquida, tone='neutral', emphasize=True),
        build_row('(-) Custo das mercadorias vendidas', groups['cmv'], tone='negative'),
        build_row('(=) Lucro bruto', lucro_bruto, tone='neutral', emphasize=True),
        build_row('(-) Despesas operacionais', despesas_operacionais, tone='negative', emphasize=True),
        build_row('(-) Despesas com venda', groups['despesas_venda'], tone='negative'),
        build_row('(-) Despesas financeiras', groups['despesas_financeiras'], tone='negative'),
        build_row('(+) Receita financeira', groups['receita_financeira'], tone='positive'),
        build_row('(-) Despesas gerais e adm', groups['despesas_gerais_adm'], tone='negative'),
        build_row('(=) Lucro líquido', lucro_liquido, tone='neutral', emphasize=True),
    ]

    def percent_rows():
        base_receita = receita_liquida

        def percent_list(values):
            result = []
            for idx, value in enumerate(values):
                base = base_receita[idx]
                if base == 0:
                    result.append(Decimal('0.00'))
                else:
                    result.append((value / base) * Decimal('100.00'))
            return result

        return [
            build_row('Margem da receita líquida (%)', percent_list(receita_liquida), value_format='percent'),
            build_row('Margem bruta (%)', percent_list(lucro_bruto), value_format='percent'),
            build_row('Margem líquida (%)', percent_list(lucro_liquido), value_format='percent'),
        ]

    return {
        'months': month_labels,
        'dre_rows': dre_rows + percent_rows(),
        'dre_totals': [
            row for row in dre_rows
        ],
        'phase': phase,
        'start_date': start_date,
        'end_date': end_date,
    }


def _month_list(start_date, end_date):
    cursor = start_date.replace(day=1)
    end_cursor = end_date.replace(day=1)
    months = []
    while cursor <= end_cursor:
        months.append(cursor)
        year = cursor.year + (cursor.month // 12)
        month = (cursor.month % 12) + 1
        cursor = date(year, month, 1)
    return months


def build_cashflow_context(start_date, end_date, phase, account_id=None, category_id=None, user=None):
    """
    Monta dados de fluxo de caixa em formato de planilha (categorias x meses).
    phase: 'consolidado' usa realizados, 'futuro' usa previstos/atrasados.
    """
    qs = get_finance_queryset(user=user, account_id=account_id, category_id=category_id)
    qs, date_field = apply_phase_filter(qs, phase, start_date, end_date)

    months = _month_list(start_date, end_date)
    month_names = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    month_labels = [
        {
            'key': month.strftime('%Y-%m'),
            'label': f"{month_names[month.month - 1]}/{str(month.year)[-2:]}",
            'year': month.year,
            'month': month.month,
        }
        for month in months
    ]
    month_index = {label['key']: idx for idx, label in enumerate(month_labels)}

    aggregates = (
        qs.annotate(month=TruncMonth(date_field))
        .values('tipo', 'category_id', 'category__nome', 'month')
        .annotate(total=Sum('valor'))
        .order_by('tipo', 'category__nome')
    )

    rows = {}
    for item in aggregates:
        month_key = item['month'].strftime('%Y-%m')
        row_key = f"{item['tipo']}-{item['category_id']}"
        row = rows.get(row_key)
        if not row:
            row = {
                'tipo': item['tipo'],
                'category_id': item['category_id'],
                'category_name': item['category__nome'],
                'values_list': [Decimal('0.00') for _ in month_labels],
                'total': Decimal('0.00'),
            }
            rows[row_key] = row
        idx = month_index.get(month_key)
        if idx is not None:
            row['values_list'][idx] = item['total'] or Decimal('0.00')

    receita_rows = []
    despesa_rows = []
    for row in rows.values():
        row['total'] = sum(row['values_list']) if row['values_list'] else Decimal('0.00')
        if row['tipo'] == 'receita':
            receita_rows.append(row)
        else:
            despesa_rows.append(row)

    receita_rows.sort(key=lambda r: r['category_name'])
    despesa_rows.sort(key=lambda r: r['category_name'])

    totals_receita_list = [Decimal('0.00') for _ in month_labels]
    totals_despesa_list = [Decimal('0.00') for _ in month_labels]

    for row in receita_rows:
        for idx, value in enumerate(row['values_list']):
            totals_receita_list[idx] += value
    for row in despesa_rows:
        for idx, value in enumerate(row['values_list']):
            totals_despesa_list[idx] += value

    totals_saldo_list = [
        totals_receita_list[idx] - totals_despesa_list[idx]
        for idx in range(len(month_labels))
    ]

    saldo_inicial_total = Decimal('0.00')
    totals_saldo_final_list = [
        saldo_inicial_total + totals_saldo_list[idx]
        for idx in range(len(month_labels))
    ]

    def build_cells(values_list):
        cells = []
        for idx, label in enumerate(month_labels):
            cells.append({
                'value': values_list[idx] if idx < len(values_list) else Decimal('0.00'),
                'year': label['year'],
                'month': label['month'],
                'label': label['label'],
                'key': label['key'],
            })
        return cells

    for row in receita_rows:
        row['cells'] = build_cells(row['values_list'])
    for row in despesa_rows:
        row['cells'] = build_cells(row['values_list'])

    totals_receita_cells = build_cells(totals_receita_list)
    totals_despesa_cells = build_cells(totals_despesa_list)
    totals_saldo_cells = build_cells(totals_saldo_list)
    totals_saldo_final_cells = build_cells(totals_saldo_final_list)

    return {
        'months': month_labels,
        'receitas': receita_rows,
        'despesas': despesa_rows,
        'totals_receita_cells': totals_receita_cells,
        'totals_despesa_cells': totals_despesa_cells,
        'totals_saldo_cells': totals_saldo_cells,
        'totals_saldo_final_cells': totals_saldo_final_cells,
        'totals_receita_total': sum(totals_receita_list),
        'totals_despesa_total': sum(totals_despesa_list),
        'totals_saldo_total': sum(totals_saldo_list),
        'totals_saldo_final_total': sum(totals_saldo_final_list),
        'saldo_inicial_total': saldo_inicial_total,
        'phase': phase,
        'start_date': start_date,
        'end_date': end_date,
    }

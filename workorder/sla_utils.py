"""
Utilidades para cálculo de SLA (Service Level Agreement) das ordens de serviço.
"""
from datetime import datetime, timedelta
from django.utils import timezone


def calculate_sla_hours(work_order):
    """
    Calcula o SLA restante em horas para uma ordem de serviço.

    Regras de SLA:
    - Padrão: 24 horas a partir da criação
    - Se o serviço tiver um SLA específico, usa esse valor
    - SLA conta apenas horas úteis (opcional - por ora conta todas as horas)

    Returns:
        float: Horas restantes de SLA (pode ser negativo se vencido)
    """
    # Obter SLA padrão ou do tipo de serviço
    sla_hours = getattr(work_order.service_type, 'sla_hours', 24)  # Padrão: 24h

    # Data/hora de criação da ordem
    created_at = work_order.created_at

    # Calcular deadline
    sla_deadline = created_at + timedelta(hours=sla_hours)

    # Tempo atual
    now = timezone.now()

    # Calcular diferença
    time_remaining = sla_deadline - now
    hours_remaining = time_remaining.total_seconds() / 3600

    return hours_remaining


def get_sla_status(work_order):
    """
    Classifica o status do SLA em cores de semáforo.

    Returns:
        str: 'green', 'yellow' ou 'red'
    """
    # Se já foi concluída, não precisa calcular SLA
    if work_order.status.status_code in ['COMPLETED', 'FINANCIAL_CLOSED', 'CANCELED']:
        return 'completed'

    hours_remaining = calculate_sla_hours(work_order)

    # Classificação:
    # Verde: mais de 8 horas restantes
    # Amarelo: entre 2 e 8 horas
    # Vermelho: menos de 2 horas ou vencido

    if hours_remaining > 8:
        return 'green'
    elif hours_remaining > 2:
        return 'yellow'
    else:
        return 'red'


def get_sla_color_hex(sla_status):
    """
    Retorna a cor hexadecimal baseada no status do SLA.
    """
    colors = {
        'green': '#10B981',   # Verde (Tailwind green-500)
        'yellow': '#FBBF24',  # Amarelo (Tailwind yellow-400)
        'red': '#EF4444',     # Vermelho (Tailwind red-500)
        'completed': '#6B7280' # Cinza (completado)
    }
    return colors.get(sla_status, '#6B7280')


def get_mock_coordinates(client_id):
    """
    Retorna coordenadas mock baseadas no ID do cliente.
    Futuramente será substituído por coordenadas reais do banco.

    Coordenadas da Baixada Fluminense/RJ
    """
    import random

    # Seed baseado no client_id para manter consistência
    random.seed(str(client_id))

    # Coordenadas da região da Baixada Fluminense
    # Latitude: -22.71 a -22.81
    # Longitude: -43.28 a -43.56

    lat = -22.71 - random.random() * 0.10  # Entre -22.71 e -22.81
    lng = -43.28 - random.random() * 0.28  # Entre -43.28 e -43.56

    return {'lat': lat, 'lng': lng}

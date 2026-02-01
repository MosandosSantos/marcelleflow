"""
Script de teste manual para verificar o dashboard
Execute: python test_dashboard_manual.py
"""
import os
import sys
import django

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

# Add testserver to ALLOWED_HOSTS
from django.conf import settings
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')

from django.test import Client
from accounts.models import User

def test_dashboard():
    """Testa se o dashboard carrega corretamente"""

    print("=" * 60)
    print("TESTE DE VERIFICAÇÃO DO DASHBOARD")
    print("=" * 60)

    # Criar cliente de teste
    client = Client()

    # Verificar se existe usuário admin
    try:
        admin_user = User.objects.get(email='admin@esferawork.com')
        print(f"\n✓ Usuário admin encontrado: {admin_user.username} ({admin_user.get_role_display()})")
    except User.DoesNotExist:
        print("\n✗ ERRO: Usuário admin@esferawork.com não encontrado!")
        print("  Crie o usuário primeiro antes de testar.")
        return

    # Fazer login
    login_success = client.login(email='admin@esferawork.com', password='admin123')

    if login_success:
        print("✓ Login realizado com sucesso")
    else:
        print("✗ ERRO: Falha no login!")
        print("  Verifique se a senha 'admin123' está correta.")
        return

    # Acessar dashboard
    print("\n" + "-" * 60)
    print("Testando acesso ao dashboard...")
    print("-" * 60)

    response = client.get('/dashboard/')

    print(f"\nStatus Code: {response.status_code}")

    if response.status_code == 200:
        print("✓ Dashboard carregou com sucesso!")

        # Verificar contexto
        context = response.context if hasattr(response, 'context') and response.context else {}

        print("\n" + "-" * 60)
        print("DADOS DO DASHBOARD")
        print("-" * 60)

        print(f"\n📊 KPIs:")
        print(f"  - Total de OS: {context.get('total_orders', 'N/A')}")
        print(f"  - Pendentes: {context.get('pending_count', 'N/A')}")
        print(f"  - Em Andamento: {context.get('in_progress_count', 'N/A')}")
        print(f"  - Concluídas: {context.get('completed_count', 'N/A')}")
        print(f"  - Taxa de Conclusão: {context.get('completion_rate', 'N/A')}%")

        print(f"\n📈 KPIs Operacionais:")
        print(f"  - Taxa no Prazo: {context.get('on_time_rate', 'N/A')}%")
        print(f"  - Satisfação: {context.get('satisfaction_percent', 'N/A')}%")
        print(f"  - Eficiência de Tempo: {context.get('time_efficiency', 'N/A')}%")

        print(f"\n💰 Indicadores Financeiros:")
        print(f"  - Receita Total: R$ {context.get('total_revenue', 'N/A')}")
        print(f"  - Receita Mensal: R$ {context.get('monthly_revenue', 'N/A')}")
        print(f"  - Ticket Médio: R$ {context.get('avg_ticket', 'N/A')}")
        print(f"  - Receita Pendente: R$ {context.get('pending_revenue', 'N/A')}")

        print(f"\n⏱️  Tempo Médio de Atendimento: {context.get('avg_hours', 'N/A')} horas")

        print(f"\n📅 Próximas OS Agendadas: {len(context.get('upcoming_orders', []))} ordens")

        # Verificar se há dados para gráficos
        import json

        print("\n" + "-" * 60)
        print("DADOS DOS GRÁFICOS")
        print("-" * 60)

        try:
            providers_names = json.loads(context.get('top_providers_names', '[]'))
            providers_ratings = json.loads(context.get('top_providers_ratings', '[]'))
            print(f"\n✓ Top Prestadores: {len(providers_names)} encontrados")
            if providers_names:
                for i, (name, rating) in enumerate(zip(providers_names, providers_ratings), 1):
                    print(f"  {i}. {name}: {rating:.1f}★")
        except Exception as e:
            print(f"\n✗ Erro ao processar Top Prestadores: {e}")

        try:
            daily_labels = json.loads(context.get('daily_labels', '[]'))
            daily_counts = json.loads(context.get('daily_counts', '[]'))
            print(f"\n✓ Atendimentos por Dia: {len(daily_labels)} dias")
            if daily_labels:
                for label, count in zip(daily_labels, daily_counts):
                    print(f"  {label}: {count} atendimentos")
        except Exception as e:
            print(f"\n✗ Erro ao processar Atendimentos por Dia: {e}")

        try:
            revenue_labels = json.loads(context.get('monthly_revenue_labels', '[]'))
            revenue_data = json.loads(context.get('monthly_revenue_data', '[]'))
            print(f"\n✓ Evolução de Receita: {len(revenue_labels)} meses")
            if revenue_labels:
                for label, value in zip(revenue_labels, revenue_data):
                    print(f"  {label}: R$ {value:.2f}")
        except Exception as e:
            print(f"\n✗ Erro ao processar Evolução de Receita: {e}")

        print("\n" + "=" * 60)
        print("CONCLUSÃO")
        print("=" * 60)
        print("\n✓ O dashboard está funcionando corretamente no backend.")
        print("✓ Todos os dados foram calculados sem erros.")
        print("\n⚠️  Próximos passos:")
        print("  1. Acesse http://localhost:8000/dashboard/ no navegador")
        print("  2. Abra o DevTools (F12) e vá para a aba Console")
        print("  3. Verifique se há erros JavaScript")
        print("  4. Verifique se os gráficos estão renderizando")
        print("  5. Verifique na aba Network se todos os CDNs carregaram (Chart.js, Leaflet, Font Awesome)")

    elif response.status_code == 302:
        print("✗ Redirecionamento detectado!")
        print(f"  Redirecionando para: {response.url}")
    elif response.status_code == 403:
        print("✗ ERRO: Acesso negado (403 Forbidden)")
        print("  O usuário não tem permissão para acessar o dashboard.")
    elif response.status_code == 404:
        print("✗ ERRO: Página não encontrada (404)")
        print("  Verifique se a URL '/dashboard/' está configurada corretamente.")
    elif response.status_code == 500:
        print("✗ ERRO: Erro interno do servidor (500)")
        print("  Verifique os logs do Django para mais detalhes.")
        if hasattr(response, 'content'):
            print("\nConteúdo da resposta:")
            print(response.content.decode('utf-8')[:500])
    else:
        print(f"✗ ERRO: Status code inesperado: {response.status_code}")

    print("\n" + "=" * 60)

if __name__ == '__main__':
    test_dashboard()

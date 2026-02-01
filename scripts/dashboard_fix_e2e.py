"""
Script de teste E2E para validar a correção do dashboard
Verifica se todos os gráficos foram renderizados após aplicação do filtro |unlocalize
"""

from playwright.sync_api import sync_playwright, expect
import time
import json
import sys
import io

# Configurar encoding para UTF-8 no Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_dashboard_charts():
    with sync_playwright() as p:
        # Iniciar navegador
        browser = p.chromium.launch(headless=False, args=['--start-maximized'])
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True
        )
        page = context.new_page()

        # Capturar logs do console
        console_logs = []
        errors = []

        def handle_console(msg):
            console_logs.append({
                'type': msg.type,
                'text': msg.text
            })
            if msg.type == 'error':
                errors.append(msg.text)

        page.on('console', handle_console)

        print("\n" + "="*80)
        print("TESTE DE VALIDAÇÃO DO DASHBOARD - PÓS CORREÇÃO")
        print("="*80 + "\n")

        try:
            # 1. Fazer login
            print("1. Acessando página de login...")
            page.goto('http://localhost:8000/login/', wait_until='networkidle')
            page.screenshot(path='C:\\Users\\mosan\\Documents\\Sistemas\\EsferaWork\\screenshot_login.png')
            print("   ✓ Página de login carregada")

            # Preencher credenciais
            print("\n2. Preenchendo credenciais...")
            page.fill('input[name="username"]', 'admin')
            page.fill('input[name="password"]', 'admin')
            print("   ✓ Credenciais preenchidas")

            # Clicar em login
            print("\n3. Realizando login...")
            page.click('button[type="submit"]')
            page.wait_for_url('**/dashboard/', timeout=10000)
            print("   ✓ Login realizado com sucesso")

            # 4. Hard refresh (Ctrl+Shift+R)
            print("\n4. Fazendo hard refresh para limpar cache...")
            page.reload(wait_until='networkidle')
            time.sleep(2)  # Aguardar renderização inicial
            print("   ✓ Hard refresh concluído")

            # 5. Aguardar carregamento completo
            print("\n5. Aguardando carregamento dos gráficos...")
            time.sleep(5)  # Tempo para Chart.js renderizar

            # 6. Capturar screenshot do dashboard
            print("\n6. Capturando screenshot do dashboard...")
            page.screenshot(path='C:\\Users\\mosan\\Documents\\Sistemas\\EsferaWork\\screenshot_dashboard_fixed.png', full_page=True)
            print("   ✓ Screenshot salvo: screenshot_dashboard_fixed.png")

            # 7. Verificar console do navegador
            print("\n7. VERIFICAÇÃO DO CONSOLE DO NAVEGADOR:")
            print("-" * 80)

            error_count = 0
            unexpected_number_errors = 0

            for log in console_logs:
                if log['type'] == 'error':
                    error_count += 1
                    print(f"   ❌ ERRO: {log['text']}")
                    if 'Unexpected number' in log['text']:
                        unexpected_number_errors += 1

            if error_count == 0:
                print("   ✅ CONSOLE LIMPO - Nenhum erro encontrado!")
            else:
                print(f"\n   Total de erros: {error_count}")
                print(f"   Erros 'Unexpected number': {unexpected_number_errors}")

            # 8. Contar elementos canvas (gráficos)
            print("\n8. CONTAGEM DE GRÁFICOS (CANVAS):")
            print("-" * 80)

            canvas_elements = page.query_selector_all('canvas')
            print(f"   Total de canvas encontrados: {len(canvas_elements)}")

            # Verificar cada canvas individualmente
            canvas_details = []
            for idx, canvas in enumerate(canvas_elements, 1):
                canvas_id = canvas.get_attribute('id') or f"canvas-{idx}"
                width = canvas.get_attribute('width')
                height = canvas.get_attribute('height')

                # Verificar se o canvas tem conteúdo visual (não está branco)
                has_content = page.evaluate('''(canvas) => {
                    const ctx = canvas.getContext('2d');
                    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                    const data = imageData.data;

                    // Verificar se há pixels não-brancos
                    for (let i = 0; i < data.length; i += 4) {
                        if (data[i] !== 255 || data[i+1] !== 255 || data[i+2] !== 255) {
                            return true; // Encontrou pixel colorido
                        }
                    }
                    return false; // Todo branco
                }''', canvas)

                canvas_details.append({
                    'id': canvas_id,
                    'width': width,
                    'height': height,
                    'has_content': has_content
                })

                status = "✅ RENDERIZADO" if has_content else "❌ VAZIO (BRANCO)"
                print(f"   {idx}. {canvas_id} ({width}x{height}) - {status}")

            # 9. Verificar elementos específicos do dashboard
            print("\n9. VERIFICAÇÃO DE ELEMENTOS ESPECÍFICOS:")
            print("-" * 80)

            checks = {
                'Gauges Circulares (5)': {
                    'selector': 'canvas[id*="gauge"]',
                    'expected_count': 5
                },
                'Gráfico Barras Horizontais (Top Prestadores)': {
                    'selector': 'canvas[id*="topProviders"]',
                    'expected_count': 1
                },
                'Gráfico Barras Verticais (Timeline)': {
                    'selector': 'canvas[id*="timeline"]',
                    'expected_count': 1
                },
                'Mapas (2)': {
                    'selector': 'div[id*="map"]',
                    'expected_count': 2
                },
                'Gráfico Linha (Receita Mensal)': {
                    'selector': 'canvas[id*="revenue"]',
                    'expected_count': 1
                }
            }

            all_found = True
            for name, check in checks.items():
                elements = page.query_selector_all(check['selector'])
                found_count = len(elements)
                expected = check['expected_count']

                if found_count >= expected:
                    print(f"   ✅ {name}: {found_count} encontrado(s)")
                else:
                    print(f"   ❌ {name}: {found_count}/{expected} encontrado(s)")
                    all_found = False

            # 10. Resumo Final
            print("\n" + "="*80)
            print("RESUMO DA VALIDAÇÃO")
            print("="*80 + "\n")

            total_canvas = len(canvas_elements)
            rendered_canvas = sum(1 for c in canvas_details if c['has_content'])

            print(f"Canvas Totais: {total_canvas}")
            print(f"Canvas Renderizados: {rendered_canvas}")
            print(f"Canvas Vazios: {total_canvas - rendered_canvas}")
            print(f"\nErros no Console: {error_count}")
            print(f"Erros 'Unexpected number': {unexpected_number_errors}")

            # VEREDICTO FINAL
            print("\n" + "="*80)
            if error_count == 0 and rendered_canvas == total_canvas and rendered_canvas >= 9:
                print("✅✅✅ PROBLEMA RESOLVIDO! ✅✅✅")
                print("\nTodos os gráficos foram renderizados com sucesso!")
                print("Console limpo, sem erros 'Unexpected number'.")
                print("Aplicação do filtro |unlocalize foi EFETIVA!")
            elif error_count == 0 and rendered_canvas > 0:
                print("⚠️ PROBLEMA PARCIALMENTE RESOLVIDO")
                print(f"\n{rendered_canvas}/{total_canvas} gráficos renderizados.")
                print("Console limpo, mas alguns gráficos ainda não renderizaram.")
            elif error_count > 0 and unexpected_number_errors == 0:
                print("⚠️ MELHOROU, MAS AINDA HÁ OUTROS ERROS")
                print(f"\nErros 'Unexpected number' corrigidos, mas há {error_count} outros erros.")
            else:
                print("❌ PROBLEMA NÃO RESOLVIDO")
                print(f"\nAinda há {unexpected_number_errors} erros 'Unexpected number'.")
            print("="*80 + "\n")

            # Salvar relatório JSON
            report = {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_canvas': total_canvas,
                'rendered_canvas': rendered_canvas,
                'console_errors': error_count,
                'unexpected_number_errors': unexpected_number_errors,
                'canvas_details': canvas_details,
                'all_elements_found': all_found,
                'console_logs': console_logs[:50]  # Primeiros 50 logs
            }

            with open('C:\\Users\\mosan\\Documents\\Sistemas\\EsferaWork\\dashboard_validation_report.json', 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            print("Relatório detalhado salvo em: dashboard_validation_report.json\n")

        except Exception as e:
            print(f"\n❌ ERRO DURANTE O TESTE: {str(e)}")
            page.screenshot(path='C:\\Users\\mosan\\Documents\\Sistemas\\EsferaWork\\screenshot_error.png')

        finally:
            # Manter navegador aberto por 10 segundos para inspeção visual
            print("Mantendo navegador aberto por 10 segundos para inspeção visual...")
            time.sleep(10)
            browser.close()

if __name__ == '__main__':
    test_dashboard_charts()

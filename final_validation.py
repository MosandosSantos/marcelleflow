# -*- coding: utf-8 -*-
"""Validação final do dashboard após correção completa"""
from playwright.sync_api import sync_playwright
import time

print("="*80)
print("VALIDACAO FINAL DO DASHBOARD")
print("="*80)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    errors = []
    unexpected_number_errors = []

    def handle_console(msg):
        if msg.type == 'error':
            errors.append(msg.text)
            if 'Unexpected number' in msg.text:
                unexpected_number_errors.append(msg.text)
                print(f"ERRO CRITICO: {msg.text}")

    page.on('console', handle_console)

    try:
        # Login
        print("\n[1/6] Fazendo login...")
        page.goto('http://localhost:8000/login/', wait_until='networkidle')
        page.fill('input[name="email"]', 'admin@esferawork.com')
        page.click('button[type="submit"]')
        page.wait_for_url('**/dashboard/', timeout=15000)
        print("      Login OK!")

        # Hard refresh
        print("\n[2/6] Hard refresh...")
        page.reload(wait_until='networkidle')
        time.sleep(3)
        print("      Refresh OK!")

        # Contar canvas
        print("\n[3/6] Contando elementos canvas...")
        canvas_count = page.evaluate('document.querySelectorAll("canvas").length')
        print(f"      Total de canvas: {canvas_count}")

        # Screenshot
        print("\n[4/6] Capturando screenshot...")
        page.screenshot(path='screenshot_final_validation.png', full_page=True)
        print("      Screenshot salvo: screenshot_final_validation.png")

        # Aguardar renderização dos gráficos
        print("\n[5/6] Aguardando renderização dos gráficos...")
        time.sleep(5)

        # Verificar se há conteúdo nos canvas
        print("\n[6/6] Verificando conteúdo dos canvas...")
        rendered_count = 0
        canvas_list = page.query_selector_all('canvas')

        for idx, canvas in enumerate(canvas_list, 1):
            canvas_id = canvas.get_attribute('id') or f"canvas-{idx}"
            has_content = page.evaluate('''(canvas) => {
                try {
                    const ctx = canvas.getContext('2d');
                    const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                    const data = imgData.data;
                    for (let i = 0; i < data.length; i += 4) {
                        if (data[i] !== 255 || data[i+1] !== 255 || data[i+2] !== 255) {
                            return true;
                        }
                    }
                    return false;
                } catch(e) {
                    return false;
                }
            }''', canvas)

            status_symbol = "OK" if has_content else "VAZIO"
            print(f"      Canvas {idx} ({canvas_id}): {status_symbol}")

            if has_content:
                rendered_count += 1

        # Resultado final
        print("\n" + "="*80)
        print("RESULTADO FINAL")
        print("="*80)
        print(f"Total de erros no console: {len(errors)}")
        print(f"Erros 'Unexpected number': {len(unexpected_number_errors)}")
        print(f"Canvas encontrados: {canvas_count}")
        print(f"Canvas renderizados: {rendered_count}")
        print(f"Canvas vazios: {canvas_count - rendered_count}")

        if len(unexpected_number_errors) == 0 and rendered_count >= 7:
            print("\n" + "="*80)
            print("PROBLEMA RESOLVIDO COM SUCESSO!")
            print("="*80)
            print("- Console limpo (sem erros 'Unexpected number')")
            print(f"- {rendered_count} graficos renderizados corretamente")
            print("- Aplicacao do filtro |unlocalize foi EFETIVA!")
            print("="*80)
        elif len(unexpected_number_errors) == 0:
            print("\nPROBLEMA PARCIALMENTE RESOLVIDO")
            print(f"- Erros 'Unexpected number' eliminados")
            print(f"- Mas apenas {rendered_count}/{canvas_count} graficos renderizaram")
        else:
            print("\nPROBLEMA NAO RESOLVIDO")
            print(f"- Ainda ha {len(unexpected_number_errors)} erros 'Unexpected number'")

        if errors:
            print("\nOutros erros encontrados:")
            for err in errors[:5]:
                print(f"  - {err[:100]}")

        time.sleep(3)

    except Exception as e:
        print(f"\nERRO DURANTE TESTE: {e}")
        page.screenshot(path='screenshot_final_error.png')

    finally:
        browser.close()

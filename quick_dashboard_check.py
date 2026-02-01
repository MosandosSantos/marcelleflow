"""Quick dashboard validation script"""
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    console_errors = []

    def log_console(msg):
        if msg.type == 'error':
            console_errors.append(msg.text)
            print(f"CONSOLE ERROR: {msg.text}")

    page.on('console', log_console)

    print("Acessando login...")
    page.goto('http://localhost:8000/login/')
    time.sleep(1)
    page.fill('input[name="email"]', 'admin@esferawork.com')
    page.click('button[type="submit"]')

    print("Aguardando dashboard...")
    page.wait_for_url('**/dashboard/', timeout=10000)

    print("Hard refresh...")
    page.reload(wait_until='networkidle')
    time.sleep(5)

    print("Capturando screenshot...")
    page.screenshot(path='screenshot_dashboard_quick.png', full_page=True)

    print("\n" + "="*80)
    print(f"TOTAL DE ERROS NO CONSOLE: {len(console_errors)}")

    unexpected_count = sum(1 for e in console_errors if 'Unexpected number' in e)
    print(f"Erros 'Unexpected number': {unexpected_count}")

    if len(console_errors) == 0:
        print("\nSTATUS: CONSOLE LIMPO - PROBLEMA RESOLVIDO!")
    elif unexpected_count > 0:
        print("\nSTATUS: AINDA HA ERROS 'Unexpected number'")
    else:
        print("\nSTATUS: Outros erros presentes")

    print("\nErros capturados:")
    for i, err in enumerate(console_errors[:10], 1):
        print(f"{i}. {err}")

    print("="*80)

    # Canvas check
    canvas_count = page.evaluate('document.querySelectorAll("canvas").length')
    print(f"\nTotal de canvas encontrados: {canvas_count}")

    time.sleep(5)
    browser.close()

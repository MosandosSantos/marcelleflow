"""
Teste para verificar se json.dumps gera números com vírgula no Django
"""
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

import json
from decimal import Decimal

# Testar json.dumps com diferentes valores
test_values = [
    [1.5, 2.3, 4.8],
    [Decimal('1.5'), Decimal('2.3'), Decimal('4.8')],
    [float(Decimal('1.5')), float(Decimal('2.3')), float(Decimal('4.8'))],
]

print("Testando json.dumps() com locale pt-br ativo:")
print("="*80)

for i, vals in enumerate(test_values, 1):
    result = json.dumps(vals)
    print(f"\nTeste {i}: {type(vals[0]).__name__}")
    print(f"  Input:  {vals}")
    print(f"  Output: {result}")
    print(f"  Válido JSON: {'SIM' if ',' in result and '[' in result else 'VERIFICAR'}")

# Testar valores diretos (não em array)
print("\n" + "="*80)
print("Testando valores diretos:")
single_values = [1.5, Decimal('1.5'), float(Decimal('1.5'))]

for val in single_values:
    result = json.dumps(val)
    print(f"  {type(val).__name__}: {val} -> {result}")

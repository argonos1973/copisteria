#!/usr/bin/env python3
"""Test de regex para reemplazos HTML"""

import re

# HTML de prueba (igual que la plantilla)
html_test = """
<div class="cliente">
    <h2>Cliente</h2>
    <p id="razonsocial"></p>
    <p id="direccion"></p>
    <p id="cp-localidad"></p>
    <p id="nif"></p>
</div>
"""

# Datos de prueba
razonsocial = "MARQUEZ TAÑA, EDUARD"
direccion = "PAU ALSINA 64-68 ESC B 3º 1º"
cp_localidad = "08024, Barcelona, Barcelona"
nif = "36968357C"

# Función set_p (igual que en factura.py)
def _safe(s):
    return '' if s is None else str(s)

def set_p(html, elem_id, value):
    pattern = rf'<p\s+id="{re.escape(elem_id)}"[^>]*>.*?</p>'
    replacement = f'<p id="{elem_id}">{_safe(value)}</p>'
    print(f"\n[DEBUG] Buscando patrón: {pattern}")
    print(f"[DEBUG] Reemplazo: {replacement}")
    result = re.sub(pattern, replacement, html, flags=re.DOTALL|re.IGNORECASE)
    return result

print("=== HTML ORIGINAL ===")
print(html_test)

print("\n=== APLICANDO REEMPLAZOS ===")

html_modificado = set_p(html_test, 'razonsocial', razonsocial)
html_modificado = set_p(html_modificado, 'direccion', direccion)
html_modificado = set_p(html_modificado, 'cp-localidad', cp_localidad)
html_modificado = set_p(html_modificado, 'nif', nif)

print("\n=== HTML FINAL ===")
print(html_modificado)

# Verificar si los datos están presentes
print("\n=== VERIFICACIÓN ===")
if razonsocial in html_modificado:
    print(f"✅ razonsocial encontrada: {razonsocial}")
else:
    print(f"❌ razonsocial NO encontrada")

if direccion in html_modificado:
    print(f"✅ direccion encontrada: {direccion}")
else:
    print(f"❌ direccion NO encontrada")

if cp_localidad in html_modificado:
    print(f"✅ cp-localidad encontrada: {cp_localidad}")
else:
    print(f"❌ cp-localidad NO encontrada")

if nif in html_modificado:
    print(f"✅ nif encontrado: {nif}")
else:
    print(f"❌ nif NO encontrado")

#!/usr/bin/env python3
"""Test completo de generación de PDF"""

import sys
sys.path.insert(0, '/var/www/html')

# Simular el envío de una factura por correo
from factura import enviar_factura_email

id_factura = 3  # F250000

print(f"=== Intentando enviar factura {id_factura} por correo ===\n")

try:
    resultado = enviar_factura_email(id_factura)
    print(f"\n✅ Resultado: {resultado}")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

import sys
import os
from flask import Flask, session
import logging

sys.path.append('/var/www/html')

# Configurar logger básico
logging.basicConfig(level=logging.DEBUG)

from app import create_app
import factura

app = create_app()
app.config['SECRET_KEY'] = 'test'

with app.app_context():
    # Mockear sesión para que db_utils no falle
    # Pero db_utils comprueba 'empresa_db' en session.
    # Si no está, usa default. Está bien.
    
    data = {
        'numero': 'TEST_ERR_001',
        'fecha': '2025-11-22',
        'idContacto': 1, 
        'idcontacto': 1,
        'nif': '12345678Z',
        'total': 121.0,
        'detalles': [{'concepto': 'Test', 'cantidad': 1, 'precio': 100, 'impuestos': 21, 'total': 121}],
        'importe_bruto': 100.0,
        'importe_impuestos': 21.0,
        'importe_cobrado': 121.0,
        'estado': 'C', 
        'tipo': 'N'
    }
    
    print("Intentando crear factura...")
    try:
        # Ejecutar
        factura.crear_factura(data)
        print("Factura creada OK")
    except Exception as e:
        print(f"\n--- EXCEPCIÓN CAPTURADA ---")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

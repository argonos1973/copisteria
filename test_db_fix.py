import sys
import os
import hashlib
from datetime import datetime
from unittest.mock import MagicMock

# Mockear Flask ANTES de importar módulos que lo usen
sys.modules['flask'] = MagicMock()
sys.modules['flask'].jsonify = MagicMock()
sys.modules['flask'].session = {}
sys.modules['flask'].has_request_context = MagicMock(return_value=False)
sys.modules['flask'].request = MagicMock()

# Añadir ruta al path para importar módulos
sys.path.append('/var/www/html')

# Mockear logger para evitar errores de importación si falta config
import logging
logging.basicConfig(level=logging.INFO)

try:
    from facturas_proveedores import guardar_factura_bd
except ImportError as e:
    print(f"Error importando modulo: {e}")
    sys.exit(1)

# Datos de prueba
datos_factura = {
    'numero_factura': f'TEST-FIX-{datetime.now().strftime("%H%M%S")}',
    'fecha_emision': datetime.now().strftime('%Y-%m-%d'),
    'total': 123.45,
    'concepto': 'PRUEBA_FIX_SQL_GASTO_AUTOMATICO',
    'base_imponible': 100.0,
    'iva_importe': 23.45,
    'iva_porcentaje': 21.0,
    'estado': 'pagada',
    'metodo_extraccion': 'MOCK'
}

# Hash dummy
pdf_hash = hashlib.md5(b'dummy_content').hexdigest() + datetime.now().strftime("%f")

print("--- INICIANDO PRUEBA DE INSERTADO ---")
print(f"Datos: {datos_factura}")

try:
    # Usamos empresa_id=1 y proveedor_id=1 (Asumimos que existen, si no fallará por FK pero eso es otro tema)
    # Lo importante es que NO falle por 'no such column: fecha' en la tabla gastos
    
    fid = guardar_factura_bd(
        empresa_id=1,
        proveedor_id=3, # Usamos ID 3 que vimos en logs anteriores (UPDIRECTO) para asegurar existencia
        datos_factura=datos_factura,
        ruta_pdf='/tmp/dummy_test.pdf',
        pdf_hash=pdf_hash,
        usuario='test_script'
    )
    print(f"✅ ÉXITO: Factura guardada con ID {fid}")
    print("Verificar en tabla gastos si se creó el registro asociado.")
    
except Exception as e:
    print(f"❌ FALLO: {e}")
    import traceback
    traceback.print_exc()

#!/usr/bin/env python3
"""
Script para enviar facturas a la AEAT (VERI*FACTU)
"""
import sys
import os
import sqlite3
import logging

# Añadir el directorio padre al path
sys.path.insert(0, '/var/www/html')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def enviar_factura(factura_id, empresa='caca'):
    """Envía una factura específica a la AEAT"""
    
    # Configurar la base de datos
    os.environ['DB_PATH'] = f'/var/www/html/db/{empresa}/{empresa}.db'
    
    # Importar después de configurar el entorno
    from verifactu.soap.client import enviar_registro_aeat
    
    logger.info(f"Enviando factura ID {factura_id} a AEAT...")
    
    try:
        # Verificar que la factura existe
        conn = sqlite3.connect(os.environ['DB_PATH'])
        cursor = conn.cursor()
        cursor.execute('SELECT numero FROM factura WHERE id = ?', (factura_id,))
        factura = cursor.fetchone()
        conn.close()
        
        if not factura:
            logger.error(f"Factura con ID {factura_id} no encontrada")
            return False
            
        numero_factura = factura[0]
        logger.info(f"Procesando factura {numero_factura}")
        
        # Enviar a AEAT
        resultado = enviar_registro_aeat(factura_id)
        
        if resultado.get('success'):
            logger.info(f"✅ Factura {numero_factura} enviada exitosamente")
            logger.info(f"CSV: {resultado.get('csv')}")
            logger.info(f"QR generado: {resultado.get('qr_generado', False)}")
        else:
            logger.error(f"❌ Error al enviar factura {numero_factura}")
            logger.error(f"Mensaje: {resultado.get('mensaje', 'Sin mensaje')}")
            
        return resultado.get('success', False)
        
    except Exception as e:
        logger.error(f"Error crítico: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 enviar_factura_aeat.py <factura_id> [empresa]")
        print("Ejemplo: python3 enviar_factura_aeat.py 466 caca")
        sys.exit(1)
    
    factura_id = int(sys.argv[1])
    empresa = sys.argv[2] if len(sys.argv) > 2 else 'caca'
    
    # Configurar la empresa en el entorno
    os.environ['EMPRESA_CODIGO'] = empresa
    os.environ['DB_PATH'] = f'/var/www/html/db/{empresa}/{empresa}.db'
    
    success = enviar_factura(factura_id, empresa)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

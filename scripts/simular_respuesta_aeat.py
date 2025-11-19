#!/usr/bin/env python3
"""
Script para simular una respuesta exitosa de la AEAT y generar QR para pruebas
Este script es útil cuando no se tiene un certificado válido pero se quiere
probar la generación de QR y el flujo completo
"""
import sys
import os
import sqlite3
import logging
from datetime import datetime
import random
import string

# Añadir el directorio padre al path
sys.path.insert(0, '/var/www/html')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generar_csv_aleatorio():
    """Genera un CSV aleatorio similar al de la AEAT"""
    prefijo = 'A-'
    codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=13))
    return prefijo + codigo

def simular_respuesta_exitosa(factura_id, empresa='caca'):
    """Simula una respuesta exitosa de la AEAT y genera el QR"""
    
    # Configurar la base de datos
    db_path = f'/var/www/html/db/{empresa}/{empresa}.db'
    os.environ['DB_PATH'] = db_path
    os.environ['EMPRESA_CODIGO'] = empresa
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Obtener datos de la factura
        cursor.execute("""
            SELECT f.numero, f.fecha, f.total, f.hash_factura,
                   c.identificador as nif_receptor, c.razonsocial
            FROM factura f
            INNER JOIN contactos c ON f.idContacto = c.idContacto
            WHERE f.id = ?
        """, (factura_id,))
        
        factura = cursor.fetchone()
        
        if not factura:
            logger.error(f"Factura {factura_id} no encontrada")
            return False
            
        numero_factura = factura['numero']
        fecha = factura['fecha']
        total = factura['total']
        hash_factura = factura['hash_factura'] or '0' * 64
        nif_receptor = factura['nif_receptor']
        
        logger.info(f"Procesando factura {numero_factura}")
        
        # Generar CSV simulado
        csv_aeat = generar_csv_aleatorio()
        logger.info(f"CSV generado: {csv_aeat}")
        
        # Obtener NIF del emisor
        emisor_path = f'/var/www/html/emisores/{empresa}_emisor.json'
        nif_emisor = '44007535W'  # Por defecto
        if os.path.exists(emisor_path):
            import json
            with open(emisor_path, 'r') as f:
                emisor_data = json.load(f)
                nif_emisor = emisor_data.get('nif', '44007535W')
        
        # Generar QR
        from verifactu.qr.generator import generar_qr_verifactu
        
        # Separar serie y número si están juntos
        serie = ''
        numero = numero_factura
        if numero_factura and len(numero_factura) > 1:
            # Asumiendo formato F250451 -> serie=F, numero=250451
            if numero_factura[0].isalpha():
                serie = numero_factura[0]
                numero = numero_factura[1:]
        
        qr_bytes = generar_qr_verifactu(
            nif=nif_emisor,
            numero_factura=numero,
            fecha_factura=fecha,
            total_factura=float(total) if total else 0.0,
            serie_factura=serie,
            csv=csv_aeat
        )
        
        if not qr_bytes:
            logger.error("Error generando QR")
            return False
            
        # Actualizar registro_facturacion
        cursor.execute("""
            UPDATE registro_facturacion
            SET codigo_qr = ?,
                csv_aeat = ?,
                csv = ?,
                nif_emisor = ?,
                estado_envio = 'ENVIADO',
                enviado_aeat = 1,
                validado_aeat = 1,
                fecha_envio = ?,
                respuesta_xml = ?
            WHERE factura_id = ?
        """, (
            qr_bytes,
            csv_aeat,
            csv_aeat,
            nif_emisor,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            '<?xml version="1.0"?><response><status>OK</status><csv>' + csv_aeat + '</csv></response>',
            factura_id
        ))
        
        if cursor.rowcount == 0:
            logger.warning(f"No existe registro en registro_facturacion para factura_id {factura_id}, creándolo...")
            
            # Crear registro si no existe
            cursor.execute("""
                INSERT INTO registro_facturacion (
                    factura_id, numero_factura, nif_emisor, nif_receptor,
                    fecha_emision, total, hash, codigo_qr, csv_aeat, csv,
                    estado_envio, enviado_aeat, validado_aeat, fecha_envio,
                    respuesta_xml
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                factura_id, numero_factura, nif_emisor, nif_receptor,
                fecha, total, hash_factura[:64], qr_bytes, csv_aeat, csv_aeat,
                'ENVIADO', 1, 1, datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                '<?xml version="1.0"?><response><status>OK</status><csv>' + csv_aeat + '</csv></response>'
            ))
        
        conn.commit()
        
        logger.info(f"✅ Respuesta AEAT simulada exitosamente para factura {numero_factura}")
        logger.info(f"   CSV: {csv_aeat}")
        logger.info(f"   QR generado: {len(qr_bytes)} bytes")
        
        # Guardar QR en archivo temporal para verificación
        qr_path = f'/var/www/html/static/tmp_qr/qr_{numero_factura}.png'
        os.makedirs(os.path.dirname(qr_path), exist_ok=True)
        with open(qr_path, 'wb') as f:
            f.write(qr_bytes)
        logger.info(f"   QR guardado en: {qr_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 simular_respuesta_aeat.py <factura_id> [empresa]")
        print("Ejemplo: python3 simular_respuesta_aeat.py 466 caca")
        print("\nEste script simula una respuesta exitosa de la AEAT y genera el QR")
        sys.exit(1)
    
    factura_id = int(sys.argv[1])
    empresa = sys.argv[2] if len(sys.argv) > 2 else 'caca'
    
    success = simular_respuesta_exitosa(factura_id, empresa)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

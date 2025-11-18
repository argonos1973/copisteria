#!/usr/bin/env python3
"""
Script para generar códigos QR para facturas que no tienen QR de VERI*FACTU

Este script es útil para:
- Facturas antiguas que no tienen QR
- Facturas de prueba
- Facturas que no han sido enviadas a la AEAT

Uso:
    python3 generar_qr_facturas.py <numero_factura>
    python3 generar_qr_facturas.py --todas  # Genera QR para todas las facturas sin QR
"""

import sqlite3
import qrcode
from io import BytesIO
import sys
import os
from datetime import datetime

def get_db_path():
    """Obtiene la ruta de la base de datos según la empresa"""
    # Por defecto usar caca, pero se puede parametrizar
    empresa = os.environ.get('EMPRESA', 'caca')
    return f'/var/www/html/db/{empresa}/{empresa}.db'

def generar_qr_factura(conn, factura_id, numero_factura, hash_factura=None):
    """Genera un QR para una factura específica"""
    
    # Si no hay hash, usar uno de ejemplo
    if not hash_factura:
        hash_factura = "0000000000000000000000000000000000000000000000000000000000000000"
    
    # Contenido del QR según especificación VERI*FACTU
    # Formato: URL base + parámetros de la factura
    contenido_qr = f"https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/VerificarQR"
    contenido_qr += f"?nif=B16488413"  # NIF del emisor
    contenido_qr += f"&numserie={numero_factura}"
    contenido_qr += f"&fecha={datetime.now().strftime('%d-%m-%Y')}"
    contenido_qr += f"&importe=0.00"
    
    # Generar el código QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(contenido_qr)
    qr.make(fit=True)
    
    # Crear imagen PNG
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convertir a bytes
    img_buffer = BytesIO()
    img.save(img_buffer, format='PNG')
    qr_bytes = img_buffer.getvalue()
    
    cursor = conn.cursor()
    
    try:
        # Verificar si existe el registro
        cursor.execute("SELECT id, codigo_qr FROM registro_facturacion WHERE factura_id = ?", (factura_id,))
        registro = cursor.fetchone()
        
        if registro:
            # Solo actualizar si no tiene QR
            if not registro[1]:
                cursor.execute("""
                    UPDATE registro_facturacion 
                    SET codigo_qr = ?
                    WHERE factura_id = ?
                """, (qr_bytes, factura_id))
                print(f"✅ QR generado para factura {numero_factura} (ID: {factura_id})")
                return True
            else:
                print(f"ℹ️  Factura {numero_factura} ya tiene QR")
                return False
        else:
            # Crear registro si no existe
            cursor.execute("""
                INSERT INTO registro_facturacion (factura_id, numero_factura, codigo_qr, hash)
                VALUES (?, ?, ?, ?)
            """, (factura_id, numero_factura, qr_bytes, hash_factura[:64]))
            print(f"✅ Registro creado y QR generado para factura {numero_factura}")
            return True
            
    except Exception as e:
        print(f"❌ Error procesando factura {numero_factura}: {e}")
        return False

def procesar_todas_las_facturas():
    """Genera QR para todas las facturas que no tienen QR"""
    
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Buscar facturas sin QR
        cursor.execute("""
            SELECT DISTINCT f.id, f.numero, f.hash_factura
            FROM factura f
            LEFT JOIN registro_facturacion rf ON f.id = rf.factura_id
            WHERE rf.codigo_qr IS NULL OR length(rf.codigo_qr) = 0
            ORDER BY f.id DESC
            LIMIT 100
        """)
        
        facturas = cursor.fetchall()
        
        if not facturas:
            print("✅ Todas las facturas tienen QR")
            return
            
        print(f"📋 Encontradas {len(facturas)} facturas sin QR")
        
        contador = 0
        for factura_id, numero, hash_factura in facturas:
            if generar_qr_factura(conn, factura_id, numero, hash_factura):
                contador += 1
                
        conn.commit()
        print(f"\n✅ Proceso completado: {contador} QRs generados")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

def main():
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python3 generar_qr_facturas.py <numero_factura>")
        print("  python3 generar_qr_facturas.py --todas")
        sys.exit(1)
    
    if sys.argv[1] == '--todas':
        procesar_todas_las_facturas()
    else:
        numero_factura = sys.argv[1]
        
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Buscar la factura
            cursor.execute("""
                SELECT id, hash_factura 
                FROM factura 
                WHERE numero = ?
            """, (numero_factura,))
            
            factura = cursor.fetchone()
            
            if not factura:
                print(f"❌ No se encontró la factura {numero_factura}")
                sys.exit(1)
                
            factura_id, hash_factura = factura
            
            if generar_qr_factura(conn, factura_id, numero_factura, hash_factura):
                conn.commit()
                print("✅ Proceso completado")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            conn.rollback()
        finally:
            conn.close()

if __name__ == "__main__":
    main()

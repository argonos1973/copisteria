#!/usr/bin/env python3
"""
Corregir estados de facturas y resetear fecha_ultima_carta
"""
import sqlite3

DB_PATH = '/var/www/html/db/aleph70.db'

def corregir_estados():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    logger.info(f"'=== CORRECCIÓN DE ESTADOS DE FACTURAS ===\n')
    
    # 1. Corregir F250358 (marcada como vencida pero aún no lo está)
    logger.info("1. Corregir F250358:")
    cursor.execute('SELECT numero fvencimiento, estado FROM factura WHERE numero = "F250358"'")
    f = cursor.fetchone()
    if f:
        logger.info(f"f'   Estado actual: {f[2]}')
        print(f'   Vencimiento: {f[1]}')
        
        cursor.execute('UPDATE factura SET estado = "P" WHERE numero = "F250358"')
        print(f'   ✅ Estado corregido: V → P (factura aún no vencida)')
    
    # 2. Resetear fecha_ultima_carta de F250313 para forzar envío
    logger.info("\n2. Resetear F250313 para forzar envío de carta:")
    cursor.execute('SELECT numero fvencimiento, estado, fecha_ultima_carta FROM factura WHERE numero = "F250313"'")
    f = cursor.fetchone()
    if f:
        print(f'   Estado: {f[2]}')
        print(f'   Vencimiento: {f[1]} (vencida hace 17 días)')
        print(f'   Última carta: {f[3]}')
        
        cursor.execute('UPDATE factura SET fecha_ultima_carta = NULL WHERE numero = "F250313"')
        print(f'   ✅ fecha_ultima_carta reseteada → se enviará carta')
    
    conn.commit()
    conn.close()
    
    logger.info("\n✅ Correcciones completadas")

if __name__ == '__main__':
    corregir_estados()

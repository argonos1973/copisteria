#!/usr/bin/env python3
import sqlite3
from logger_config import get_logger

# Inicializar logger
logger = get_logger(__name__)

conn = sqlite3.connect('/var/www/html/db/aleph70.db')
cursor = conn.cursor()

cursor.execute('''
    SELECT id, concepto, fecha_operacion, importe_eur 
    FROM gastos 
    WHERE concepto LIKE '%Aigues%'
    AND substr(fecha_operacion, 4, 2) = '09'
    AND substr(fecha_operacion, 7, 4) = '2025'
    AND importe_eur < 0
    ORDER BY id
''')

logger.info("=== RECIBOS AIGÜES SEPTIEMBRE 2025 ===\n")
rows = cursor.fetchall()
logger.info(f"Total registros: {len(rows)}\n")

for row in rows:
    logger.info(f"ID {row[0]}: {row[2]} - {row[3]}€")
    logger.info(f"  {row[1]}")
    logger.info(f")

# Verificar si hay duplicados exactos
if len(rows) > 1:
    if rows[0][2] == rows[1][2] and rows[0][3] == rows[1][3]:
        logger.info(f"❌ DUPLICADO DETECTADO:")
        logger.info(f"   IDs {rows[0][0]} y {rows[1][0]} tienen misma fecha e importe")
        logger.info(f"   Concepto 1: {rows[0][1]}")
        logger.info(f"   Concepto 2: {rows[1][1]}")
        
        # Diferencia entre conceptos
        c1 = rows[0][1]
        c2 = rows[1][1]
        if c1.replace(' Bb' ''") == c2 or c2.replace(' Bb', '') == c1:
            logger.info(f"\n   La única diferencia es ' Bb' al final → Es un DUPLICADO REAL")
            logger.info(f"   Se debe eliminar el ID {max(rows[0][0], rows[1][0])}")

conn.close()

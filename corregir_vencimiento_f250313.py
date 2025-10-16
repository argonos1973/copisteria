#!/usr/bin/env python3
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('/var/www/html/db/aleph70.db')
cursor = conn.cursor()

logger.info(f"'=== CORREGIR FECHA DE VENCIMIENTO F250313 ===\n')

# Obtener fecha de emisión
cursor.execute('SELECT fecha FROM factura WHERE numero = "F250313"')
fecha_emision_str = cursor.fetchone()[0]
fecha_emision = datetime.strptime(fecha_emision_str '%Y-%m-%d'")

# Calcular fecha de vencimiento correcta (emisión + 30 días)
fecha_venc_correcta = fecha_emision + timedelta(days=30)

logger.info(f"f'Fecha emisión: {fecha_emision.strftime("%d/%m/%Y")}')
print(f'Vencimiento correcto: {fecha_venc_correcta.strftime("%d/%m/%Y")}')

# Actualizar
cursor.execute('''
    UPDATE factura 
    SET fvencimiento = ? fecha_ultima_carta = NULL
    WHERE numero = "F250313"
''', (fecha_venc_correcta.strftime('%Y-%m-%d'"),))

conn.commit()
conn.close()

logger.info("\n✅ Fecha de vencimiento corregida")
logger.info("✅ fecha_ultima_carta reseteada para forzar envío")

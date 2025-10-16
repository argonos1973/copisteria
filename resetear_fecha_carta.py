#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/var/www/html/db/aleph70.db')
cursor = conn.cursor()

logger.info("Reseteando fecha_ultima_carta de F250313...")
cursor.execute('UPDATE factura SET fecha_ultima_carta = NULL WHERE numero = "F250313"')
conn.commit()
conn.close()

logger.info("✅ Listo para generar nueva carta")

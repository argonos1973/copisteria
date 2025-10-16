#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/var/www/html/db/aleph70.db')
cursor = conn.cursor()

logger.info("=== CAMBIAR EMAIL A PRUEBAS ===\n")

# Cambiar email del contacto
cursor.execute('''
    UPDATE contactos 
    SET mail = 'samuel@aleph70.com'
    WHERE idContacto = 120
''')

logger.info("✅ Email cambiado a: samuel@aleph70.com")
logger.info("   (idContacto: 120 - JUAN DIEGO MARTINEZ JARAMILLO)")

conn.commit()
conn.close()

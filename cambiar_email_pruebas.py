#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/var/www/html/db/aleph70.db')
cursor = conn.cursor()

print('=== CAMBIAR EMAIL A PRUEBAS ===\n')

# Cambiar email del contacto
cursor.execute('''
    UPDATE contactos 
    SET mail = 'samuel@aleph70.com'
    WHERE idContacto = 120
''')

print('✅ Email cambiado a: samuel@aleph70.com')
print('   (idContacto: 120 - JUAN DIEGO MARTINEZ JARAMILLO)')

conn.commit()
conn.close()

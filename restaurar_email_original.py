#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/var/www/html/db/aleph70.db')
cursor = conn.cursor()

print('=== RESTAURAR EMAIL ORIGINAL ===\n')

# Restaurar email del contacto
cursor.execute('''
    UPDATE contactos 
    SET mail = 'juandimj89@gmail.com'
    WHERE idContacto = 120
''')

print('✅ Email restaurado a: juandimj89@gmail.com')
print('   (idContacto: 120 - JUAN DIEGO MARTINEZ JARAMILLO)')

conn.commit()
conn.close()

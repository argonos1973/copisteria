#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/var/www/html/db/aleph70.db')
cursor = conn.cursor()

print('=== BUSCAR CONTACTOS CON EMAIL DE PRUEBAS ===\n')

cursor.execute('''
    SELECT idContacto, razonsocial, mail
    FROM contactos
    WHERE mail = 'samuel@aleph70.com'
''')

contactos = cursor.fetchall()

if contactos:
    print(f'⚠️  Encontrados {len(contactos)} contacto(s) con email de pruebas:\n')
    for c in contactos:
        print(f'  ID: {c[0]}')
        print(f'  Cliente: {c[1]}')
        print(f'  Email: {c[2]}')
        print()
else:
    print('✅ No hay contactos con email de pruebas (samuel@aleph70.com)')

print('\n=== VERIFICAR EMAILS SOSPECHOSOS ===\n')

# Buscar emails que no sean del dominio del cliente
cursor.execute('''
    SELECT idContacto, razonsocial, mail
    FROM contactos
    WHERE mail LIKE '%@aleph70.com%'
    AND razonsocial NOT LIKE '%ALEPH%'
    AND razonsocial NOT LIKE '%SAMUEL%'
''')

sospechosos = cursor.fetchall()

if sospechosos:
    print(f'⚠️  Encontrados {len(sospechosos)} contacto(s) con email @aleph70.com:\n')
    for c in sospechosos:
        print(f'  ID: {c[0]}')
        print(f'  Cliente: {c[1]}')
        print(f'  Email: {c[2]}')
        print()
else:
    print('✅ No hay emails @aleph70.com en clientes externos')

conn.close()

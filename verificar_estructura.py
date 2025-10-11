#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/var/www/html/db/aleph70.db')
cursor = conn.cursor()

print("=== Estructura de la tabla 'factura' ===")
cursor.execute("PRAGMA table_info(factura)")
columnas = cursor.fetchall()
for col in columnas:
    print(f"{col[0]}: {col[1]} ({col[2]})")

print("\n=== Estructura de la tabla 'contactos' ===")
cursor.execute("PRAGMA table_info(contactos)")
columnas = cursor.fetchall()
for col in columnas:
    print(f"{col[0]}: {col[1]} ({col[2]})")

print("\n=== Verificar una factura de ejemplo ===")
cursor.execute("SELECT * FROM factura LIMIT 1")
factura = cursor.fetchone()
if factura:
    cursor.execute("PRAGMA table_info(factura)")
    nombres = [col[1] for col in cursor.fetchall()]
    factura_dict = dict(zip(nombres, factura))
    print(f"ID: {factura_dict.get('id')}")
    print(f"Número: {factura_dict.get('numero')}")
    print(f"Campos con 'contact' en el nombre:")
    for key in factura_dict.keys():
        if 'contact' in key.lower():
            print(f"  {key}: {factura_dict[key]}")

conn.close()

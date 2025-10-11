#!/usr/bin/env python3
"""Test de envío de factura por email"""

import sys
sys.path.insert(0, '/var/www/html')

from db_utils import get_db_connection

# ID de factura a probar (ajusta según necesites)
id_factura = 3  # Cambia esto por el ID de una factura real

print(f"=== Test de datos para factura {id_factura} ===\n")

conn = get_db_connection()
cursor = conn.cursor()

# Misma consulta que usa enviar_factura_email
query = """
    SELECT 
        f.*, 
        c.razonsocial,
        c.mail,
        c.identificador,
        c.direccion,
        c.cp,
        c.localidad,
        c.provincia
    FROM factura f
    INNER JOIN contactos c ON f.idContacto = c.idContacto
    WHERE f.id = ?
"""

cursor.execute(query, (id_factura,))
factura = cursor.fetchone()

if factura:
    nombres_columnas = [description[0] for description in cursor.description]
    factura_dict = dict(zip(nombres_columnas, factura))
    
    print(f"✅ Factura encontrada")
    print(f"\nDatos de la factura:")
    print(f"  ID: {factura_dict.get('id')}")
    print(f"  Número: {factura_dict.get('numero')}")
    print(f"  Fecha: {factura_dict.get('fecha')}")
    print(f"  Total: {factura_dict.get('total')}")
    print(f"  idContacto: {factura_dict.get('idContacto')}")
    
    print(f"\nDatos del cliente:")
    print(f"  Razón Social: '{factura_dict.get('razonsocial')}'")
    print(f"  Dirección: '{factura_dict.get('direccion')}'")
    print(f"  CP: '{factura_dict.get('cp')}'")
    print(f"  Localidad: '{factura_dict.get('localidad')}'")
    print(f"  Provincia: '{factura_dict.get('provincia')}'")
    print(f"  NIF: '{factura_dict.get('identificador')}'")
    print(f"  Email: '{factura_dict.get('mail')}'")
    
    # Verificar si los datos están vacíos
    if not factura_dict.get('razonsocial'):
        print("\n⚠️  ADVERTENCIA: razonsocial está vacía")
    if not factura_dict.get('direccion'):
        print("⚠️  ADVERTENCIA: direccion está vacía")
    if not factura_dict.get('mail'):
        print("⚠️  ADVERTENCIA: mail está vacío")
        
    # Verificar el contacto directamente
    print(f"\n=== Verificación directa del contacto ===")
    cursor.execute("SELECT * FROM contactos WHERE idContacto = ?", (factura_dict.get('idContacto'),))
    contacto = cursor.fetchone()
    if contacto:
        nombres_contacto = [description[0] for description in cursor.description]
        contacto_dict = dict(zip(nombres_contacto, contacto))
        print(f"✅ Contacto {factura_dict.get('idContacto')} encontrado:")
        print(f"  Razón Social: '{contacto_dict.get('razonsocial')}'")
        print(f"  Dirección: '{contacto_dict.get('direccion')}'")
        print(f"  CP: '{contacto_dict.get('cp')}'")
        print(f"  Localidad: '{contacto_dict.get('localidad')}'")
        print(f"  Email: '{contacto_dict.get('mail')}'")
    else:
        print(f"❌ Contacto {factura_dict.get('idContacto')} NO encontrado")
        
else:
    print(f"❌ Factura {id_factura} no encontrada")

conn.close()

#!/usr/bin/env python3
"""Test de consulta de factura para PDF"""

import sqlite3

# ID de factura a probar (ajusta según necesites)
id_factura = 1  # Cambia esto por el ID de una factura real

conn = sqlite3.connect('/var/www/html/db/aleph70.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

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
    LEFT JOIN contactos c ON f.idContacto = c.idContacto
    WHERE f.id = ?
"""

cursor.execute(query, (id_factura,))
factura = cursor.fetchone()

if factura:
    print(f"✅ Factura {id_factura} encontrada")
    print(f"\nDatos de la factura:")
    print(f"  Número: {factura['numero']}")
    print(f"  Fecha: {factura['fecha']}")
    print(f"  Total: {factura['total']}")
    print(f"  idContacto: {factura['idContacto']}")
    
    print(f"\nDatos del cliente:")
    print(f"  Razón Social: {factura['razonsocial']}")
    print(f"  Dirección: {factura['direccion']}")
    print(f"  CP: {factura['cp']}")
    print(f"  Localidad: {factura['localidad']}")
    print(f"  Provincia: {factura['provincia']}")
    print(f"  NIF: {factura['identificador']}")
    
    if not factura['razonsocial']:
        print("\n⚠️  ADVERTENCIA: No hay datos del cliente. Posibles causas:")
        print("  1. El idContacto de la factura no existe en la tabla contactos")
        print("  2. El contacto no tiene datos completos")
        
        # Verificar si existe el contacto
        cursor.execute("SELECT * FROM contactos WHERE idContacto = ?", (factura['idContacto'],))
        contacto = cursor.fetchone()
        if contacto:
            print(f"\n  ✅ Contacto {factura['idContacto']} existe:")
            print(f"     Razón Social: {contacto['razonsocial']}")
            print(f"     Dirección: {contacto['direccion']}")
        else:
            print(f"\n  ❌ Contacto {factura['idContacto']} NO existe en la tabla contactos")
else:
    print(f"❌ Factura {id_factura} no encontrada")

conn.close()

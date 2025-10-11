#!/usr/bin/env python3
"""Test de generación de PDF de factura"""

import sys
sys.path.insert(0, '/var/www/html')

from db_utils import get_db_connection
from datetime import datetime

# ID de factura a probar
id_factura = 3

print(f"=== Test de generación de PDF para factura {id_factura} ===\n")

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
    
    print("✅ Factura encontrada")
    print(f"\nDatos básicos:")
    print(f"  ID: {factura_dict.get('id')}")
    print(f"  Número: {factura_dict.get('numero')}")
    print(f"  Fecha: {factura_dict.get('fecha')}")
    
    print(f"\nDatos del cliente en factura_dict:")
    print(f"  razonsocial: '{factura_dict.get('razonsocial')}'")
    print(f"  direccion: '{factura_dict.get('direccion')}'")
    print(f"  cp: '{factura_dict.get('cp')}'")
    print(f"  localidad: '{factura_dict.get('localidad')}'")
    print(f"  provincia: '{factura_dict.get('provincia')}'")
    print(f"  identificador: '{factura_dict.get('identificador')}'")
    print(f"  mail: '{factura_dict.get('mail')}'")
    
    # Simular el reemplazo HTML
    print(f"\n=== Simulación de reemplazos HTML ===")
    
    razonsocial_html = f'<p>{factura_dict.get("razonsocial") or ""}</p>'
    direccion_html = f'<p>{factura_dict.get("direccion") or ""}</p>'
    cp_localidad = ", ".join(filter(None, [
        factura_dict.get("cp"), 
        factura_dict.get("localidad"), 
        factura_dict.get("provincia")
    ]))
    cp_localidad_html = f'<p>{cp_localidad}</p>'
    nif_html = f'<p>{factura_dict.get("identificador") or ""}</p>'
    
    print(f"Razón social HTML: {razonsocial_html}")
    print(f"Dirección HTML: {direccion_html}")
    print(f"CP-Localidad HTML: {cp_localidad_html}")
    print(f"NIF HTML: {nif_html}")
    
    # Verificar si los reemplazos funcionarían
    html_test = """
    <p id="razonsocial"></p>
    <p id="direccion"></p>
    <p id="cp-localidad"></p>
    <p id="nif"></p>
    """
    
    html_reemplazado = html_test.replace('<p id="razonsocial"></p>', razonsocial_html)
    html_reemplazado = html_reemplazado.replace('<p id="direccion"></p>', direccion_html)
    html_reemplazado = html_reemplazado.replace('<p id="cp-localidad"></p>', cp_localidad_html)
    html_reemplazado = html_reemplazado.replace('<p id="nif"></p>', nif_html)
    
    print(f"\n=== HTML después de reemplazos ===")
    print(html_reemplazado)
    
else:
    print(f"❌ Factura {id_factura} no encontrada")

conn.close()

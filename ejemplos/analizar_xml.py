#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para analizar la estructura de un archivo XML de Facturae
"""

import sys

from lxml import etree


def mostrar_estructura(elemento, ruta='', nivel=0):
    """Muestra la estructura jerárquica de un elemento XML con sus rutas"""
    # Determinar el nombre del elemento con su namespace
    if elemento.tag.startswith('{'):
        ns, tag = elemento.tag[1:].split('}', 1)
        nombre = f"{{{ns}}}{tag}"
    else:
        nombre = elemento.tag
    
    # Construir la ruta actual
    ruta_actual = f"{ruta}/{nombre}" if ruta else nombre
    
    # Mostrar información del elemento
    print(f"{'  ' * nivel}+ {nombre}")
    print(f"{'  ' * nivel}  Ruta: {ruta_actual}")
    
    if elemento.text and elemento.text.strip():
        print(f"{'  ' * nivel}  Texto: {elemento.text.strip()}")
    
    # Procesar atributos
    for atrib, valor in elemento.attrib.items():
        print(f"{'  ' * nivel}  Atributo: {atrib}={valor}")
    
    # Procesar hijos recursivamente
    for hijo in elemento:
        mostrar_estructura(hijo, ruta_actual, nivel + 1)

def analizar_xml(ruta_xml):
    """Analiza un archivo XML y muestra su estructura jerárquica"""
    try:
        # Parsear el XML
        tree = etree.parse(ruta_xml)
        root = tree.getroot()
        
        # Mostrar información del namespace
        print("\n=== INFORMACIÓN DE NAMESPACES ===")
        for prefix, uri in root.nsmap.items():
            print(f"Prefijo: {prefix or 'DEFAULT'}, URI: {uri}")
        
        # Mostrar la estructura
        print("\n=== ESTRUCTURA DEL XML ===")
        mostrar_estructura(root)
        
        # Intentar localizar elementos clave para la validación
        print("\n=== BÚSQUEDA DE ELEMENTOS CLAVE ===")
        # Registrar todos los namespaces
        namespaces = {}
        for prefix, uri in root.nsmap.items():
            # Si el prefijo es None (namespace por defecto), usamos un prefijo vacío
            namespaces[prefix or ''] = uri
        
        # Buscar elementos importantes
        for elemento in ['InvoiceLine', 'InvoiceTotals', 'TotalGrossAmount', 'TotalTaxOutputs', 'InvoiceTotal']:
            # Intentar con diferentes rutas
            resultados = []
            
            # Búsqueda global
            for resultado in root.xpath(f"//*[local-name()='{elemento}']", namespaces=namespaces):
                ruta_elemento = tree.getpath(resultado)
                resultados.append(f"{ruta_elemento} (Texto: {resultado.text.strip() if resultado.text else 'None'})")
            
            print(f"Elemento: {elemento}")
            if resultados:
                for i, ruta in enumerate(resultados, 1):
                    print(f"  {i}. {ruta}")
            else:
                print(f"  No se encontró el elemento '{elemento}'")
        
    except Exception as e:
        print(f"Error analizando XML: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python analizar_xml.py <ruta_al_xml>")
        sys.exit(1)
        
    analizar_xml(sys.argv[1])

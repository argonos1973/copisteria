#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de ejemplo para mostrar el uso de las funciones de validación
de facturas Facturae en VERI*FACTU.
"""

import logging
import os
import sys
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Añadir directorio raíz al path para importar módulos
sys.path.append('/var/www/html')

from facturae.validacion import (validar_facturae_completa,
                                 validar_xml_contra_xsd,
                                 verificar_totales_factura)


def mostrar_resultado_validacion(resultado, tipo_validacion):
    """
    Muestra el resultado de una validación de forma amigable
    
    Args:
        resultado (dict): Resultado de la validación
        tipo_validacion (str): Tipo de validación realizada
    """
    print(f"\n=== Resultado de {tipo_validacion} ===")
    
    # Determinar si es una validación XSD (tiene 'valido') o de totales (tiene 'correcto')
    es_valido = resultado.get('valido', resultado.get('correcto', False))
    
    if es_valido:
        print("✅ CORRECTO: La validación ha sido exitosa.")
    else:
        print("❌ ERROR: Se han detectado problemas:")
        for error in resultado.get('errores', []):
            print(f"  - {error}")


def validar_factura(ruta_xml):
    """
    Realiza todas las validaciones sobre una factura
    
    Args:
        ruta_xml (str): Ruta al archivo XML de Facturae a validar
    
    Returns:
        bool: True si todas las validaciones son correctas, False en caso contrario
    """
    if not os.path.exists(ruta_xml):
        logger.error(f"El archivo {ruta_xml} no existe")
        return False
        
    print(f"\nValidando factura: {os.path.basename(ruta_xml)}")
    print("=" * 50)
    
    # 1. Validación contra esquema XSD
    resultado_xsd = validar_xml_contra_xsd(ruta_xml)
    mostrar_resultado_validacion(resultado_xsd, "validación contra esquema XSD")
    
    # 2. Verificación de totales
    resultado_totales = verificar_totales_factura(ruta_xml)
    mostrar_resultado_validacion(resultado_totales, "verificación de totales")
    
    # 3. Validación completa (ambas juntas)
    resultado_completo = validar_facturae_completa(ruta_xml)
    mostrar_resultado_validacion(resultado_completo, "validación completa")
    
    return resultado_xsd.get('valido', False) and resultado_totales.get('correcto', False)


def validar_directorio(directorio):
    """
    Valida todas las facturas XML en un directorio
    
    Args:
        directorio (str): Ruta al directorio con facturas XML
    """
    if not os.path.isdir(directorio):
        logger.error(f"El directorio {directorio} no existe")
        return
    
    archivos_xml = Path(directorio).glob('*.xml')
    contador = {'total': 0, 'validos': 0, 'invalidos': 0}
    
    for ruta_xml in archivos_xml:
        contador['total'] += 1
        es_valido = validar_factura(str(ruta_xml))
        
        if es_valido:
            contador['validos'] += 1
        else:
            contador['invalidos'] += 1
    
    print("\n" + "=" * 50)
    print("Resumen de validación:")
    print(f"  - Total facturas procesadas: {contador['total']}")
    print(f"  - Facturas válidas: {contador['validos']}")
    print(f"  - Facturas con errores: {contador['invalidos']}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Validador de facturas Facturae para VERI*FACTU')
    parser.add_argument('ruta', type=str, help='Ruta a un archivo XML o directorio con XMLs')
    
    args = parser.parse_args()
    
    if os.path.isdir(args.ruta):
        validar_directorio(args.ruta)
    elif os.path.isfile(args.ruta):
        validar_factura(args.ruta)
    else:
        logger.error(f"La ruta especificada no existe: {args.ruta}")
        sys.exit(1)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para validar los totales de un archivo XSIG específico.
Útil para comprobar que los totales se conservan correctamente tras la firma.
"""

import logging
import os
import sys
import tempfile
import xml.etree.ElementTree as ET
from decimal import Decimal

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Añadir el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def validar_totales_xsig(ruta_xsig):
    """
    Valida los totales de un archivo XSIG.
    
    Args:
        ruta_xsig (str): Ruta al archivo XSIG a validar
        
    Returns:
        dict: Resultado de la validación
    """
    if not os.path.exists(ruta_xsig):
        return {
            'valido': False,
            'error': f'No se encontró el archivo: {ruta_xsig}'
        }
    
    if not ruta_xsig.lower().endswith('.xsig'):
        return {
            'valido': False,
            'error': 'El archivo no es un archivo XSIG'
        }
    
    # Extraer el XML desde el XSIG
    try:
        from facturae.firma import extraer_xml_desde_xsig
        xml_bytes, ruta_temporal = extraer_xml_desde_xsig(ruta_xsig)
        
        if not xml_bytes or not ruta_temporal:
            return {
                'valido': False,
                'error': 'No se pudo extraer el XML del archivo XSIG'
            }
            
        logger.info(f"XML extraído correctamente a: {ruta_temporal}")
        
        # Analizar los totales del XML
        try:
            # Usar ElementTree para análisis simple
            tree = ET.parse(ruta_temporal)
            root = tree.getroot()
            
            # Detectar el namespace
            ns = ''
            if '}' in root.tag:
                ns = root.tag.split('}')[0] + '}'
            
            # Buscar los elementos de totales
            total_bruto = root.find(f'.//{ns}TotalGrossAmount')
            total_impuestos = root.find(f'.//{ns}TotalTaxOutputs')
            total_factura = root.find(f'.//{ns}InvoiceTotal')
            
            # Verificar si alguno de los totales es cero
            totales = {}
            if total_bruto is not None:
                totales['total_bruto'] = total_bruto.text
                
            if total_impuestos is not None:
                totales['total_impuestos'] = total_impuestos.text
                
            if total_factura is not None:
                totales['total_factura'] = total_factura.text
            
            # Verificar si todos los totales son cero
            todos_cero = all(
                t is not None and (t == '0.00' or float(t) == 0)
                for t in [
                    total_bruto.text if total_bruto is not None else None,
                    total_impuestos.text if total_impuestos is not None else None,
                    total_factura.text if total_factura is not None else None
                ]
                if t is not None
            )
            
            # Buscar líneas de factura para verificar si tienen valores
            lineas_tiene_valores = False
            lineas = root.findall(f'.//{ns}InvoiceLine')
            
            for linea in lineas:
                base_item = linea.find(f'.//{ns}TaxableBase/{ns}TotalAmount')
                if base_item is not None and base_item.text and float(base_item.text) > 0:
                    lineas_tiene_valores = True
                    break
            
            # Resultado
            if todos_cero and lineas_tiene_valores:
                return {
                    'valido': False,
                    'error': 'Los totales generales están en cero pero las líneas tienen valores',
                    'totales': totales
                }
            elif not todos_cero:
                return {
                    'valido': True,
                    'mensaje': '¡ÉXITO! Los totales se mantienen correctamente',
                    'totales': totales
                }
            else:
                return {
                    'valido': False,
                    'error': 'No se pudieron determinar los totales',
                    'totales': totales
                }
                
        except Exception as e:
            logger.error(f"Error al analizar el XML: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'valido': False,
                'error': f'Error al analizar el XML: {str(e)}'
            }
        finally:
            # Limpiar archivo temporal
            if os.path.exists(ruta_temporal):
                os.unlink(ruta_temporal)
                
    except Exception as e:
        logger.error(f"Error al procesar el archivo XSIG: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'valido': False,
            'error': f'Error al procesar el archivo XSIG: {str(e)}'
        }
    
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python validar_xsig_totales.py ruta/al/archivo.xsig")
        sys.exit(1)
        
    ruta_xsig = sys.argv[1]
    print(f"Validando totales de archivo XSIG: {ruta_xsig}")
    
    resultado = validar_totales_xsig(ruta_xsig)
    
    if resultado['valido']:
        print(f"\n✅ {resultado['mensaje']}")
    else:
        print(f"\n❌ {resultado['error']}")
    
    if 'totales' in resultado:
        print("\nTotales encontrados:")
        for clave, valor in resultado['totales'].items():
            print(f"  - {clave}: {valor}")

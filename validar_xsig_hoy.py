#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para validar las facturas XSIG generadas en el día actual (17/06/2025).
"""

import json
import os
import sqlite3
from db_utils import get_db_connection
import sys
from datetime import datetime

# Añadir el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importar las funciones necesarias
from verifactu import (generar_datos_verifactu_para_factura,
                       validar_factura_xml_antes_procesar)



def validar_facturas_xsig_hoy():
    """Valida las facturas XSIG generadas hoy."""
    conn = get_db_connection()
    
    # Fecha actual en formato YYYY-MM-DD
    fecha_actual = datetime.now().strftime('%Y-%m-%d')
    
    # Obtener facturas XSIG generadas hoy
    cursor = conn.execute('''
        SELECT f.id, f.numero, f.ruta_xml
        FROM factura f
        WHERE f.ruta_xml IS NOT NULL 
        AND f.ruta_xml LIKE '%.xsig'
        AND DATE(f.fecha) = ?
    ''', (fecha_actual,))
    
    facturas = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    if not facturas:
        print(f"No se encontraron facturas XSIG generadas hoy ({fecha_actual}).")
        return []
    
    print(f"Se encontraron {len(facturas)} facturas XSIG generadas hoy ({fecha_actual}).")
    
    resultados = []
    facturas_validas = 0
    facturas_procesadas = 0
    
    # Procesar cada factura
    for idx, factura in enumerate(facturas, 1):
        factura_id = factura['id']
        factura_numero = factura['numero']
        ruta_xml = factura['ruta_xml']
        
        print(f"\n[{idx}/{len(facturas)}] Procesando factura {factura_numero} (ID: {factura_id})...")
        
        # Validar la factura
        resultado_validacion = validar_factura_xml_antes_procesar(factura_id)
        es_valida = resultado_validacion.get('valido', False)
        es_firmada = resultado_validacion.get('firmado', False)
        
        # Guardar el resultado
        resultado = {
            'factura_id': factura_id,
            'factura_numero': factura_numero,
            'archivo': os.path.basename(ruta_xml),
            'es_valida': es_valida,
            'es_firmada': es_firmada,
            'errores': resultado_validacion.get('errores', [])
        }
        
        # Mostrar resultado
        if es_valida:
            facturas_validas += 1
            print(f"  ✓ Factura válida y firmada: {es_firmada}")
            
            # Generar datos VERI*FACTU
            try:
                datos_verifactu = generar_datos_verifactu_para_factura(factura_id)
                if datos_verifactu.get('correcto', False):
                    facturas_procesadas += 1
                    print("  ✓ Datos VERI*FACTU generados correctamente")
                    print(f"    - Hash: {datos_verifactu.get('hash', '')[:16]}...")
                    resultado['datos_verifactu'] = datos_verifactu
                else:
                    print(f"  ✗ Error al generar datos VERI*FACTU: {datos_verifactu.get('mensaje', '')}")
                    resultado['datos_verifactu_error'] = datos_verifactu.get('mensaje', '')
            except Exception as e:
                print(f"  ✗ Excepción al generar datos VERI*FACTU: {str(e)}")
                resultado['datos_verifactu_error'] = str(e)
        else:
            print(f"  ✗ Factura con errores: {', '.join(resultado_validacion.get('errores', []))}")
        
        resultados.append(resultado)
    
    # Mostrar resumen
    print("\n" + "=" * 50)
    print("RESUMEN DE VALIDACIÓN:")
    print(f"Total de facturas XSIG de hoy: {len(facturas)}")
    print(f"Facturas válidas: {facturas_validas} ({facturas_validas/len(facturas)*100 if facturas else 0:.1f}%)")
    print(f"Facturas con errores: {len(facturas) - facturas_validas} ({(len(facturas) - facturas_validas)/len(facturas)*100 if facturas else 0:.1f}%)")
    print(f"Facturas procesadas correctamente: {facturas_procesadas} ({facturas_procesadas/len(facturas)*100 if facturas else 0:.1f}%)")
    
    # Guardar resultados en un archivo JSON
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    archivo_resultados = f'/var/www/html/validacion_xsig_hoy_{timestamp}.json'
    
    with open(archivo_resultados, 'w', encoding='utf-8') as f:
        json.dump({
            'fecha': fecha_actual,
            'timestamp': datetime.now().isoformat(),
            'total': len(facturas),
            'validas': facturas_validas,
            'con_errores': len(facturas) - facturas_validas,
            'procesadas': facturas_procesadas,
            'resultados': resultados
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\nResultados guardados en: {archivo_resultados}")
    return resultados

if __name__ == '__main__':
    validar_facturas_xsig_hoy()

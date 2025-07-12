#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para validar todas las facturas XSIG existentes en el sistema
"""

import json
import os
import sqlite3
import sys
from datetime import datetime

# Asegurar acceso a módulos de la aplicación
sys.path.append('/var/www/html')

# Importar funciones necesarias
from verifactu import (generar_datos_verifactu_para_factura,
                       validar_factura_xml_antes_procesar)


def obtener_facturas_xsig():
    """Obtener todas las facturas que tienen un archivo XSIG asociado"""
    conn = sqlite3.connect('/var/www/html/aleph70.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, numero, ruta_xml FROM factura WHERE ruta_xml LIKE '%.xsig' ORDER BY id")
    facturas = [{'id': row[0], 'numero': row[1], 'ruta_xml': row[2]} for row in cursor.fetchall()]
    conn.close()
    return facturas

def main():
    print(f"=== VALIDACIÓN DE FACTURAS XSIG ===")
    print(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Obtener todas las facturas con archivo XSIG
    facturas = obtener_facturas_xsig()
    print(f"Se encontraron {len(facturas)} facturas con archivos XSIG")
    
    # Estadísticas
    total = len(facturas)
    validadas = 0
    con_errores = 0
    procesadas_ok = 0
    
    # Resultados detallados
    resultados = []
    
    # Procesar cada factura
    for i, factura in enumerate(facturas, 1):
        print(f"\n[{i}/{total}] Procesando factura {factura['numero']} (ID: {factura['id']})...")
        
        # Validar factura
        try:
            # Validar
            resultado = validar_factura_xml_antes_procesar(factura['id'])
            es_valida = resultado.get('valido', False)
            
            # Generar datos VERI*FACTU
            datos_verifactu = None
            if es_valida:
                try:
                    datos_verifactu = generar_datos_verifactu_para_factura(factura['id'])
                    if datos_verifactu:
                        procesadas_ok += 1
                        print(f"  ✓ Datos VERI*FACTU generados correctamente")
                        print(f"    - Hash: {datos_verifactu['hash'][:16]}...")
                except Exception as e:
                    print(f"  ✗ Error al generar datos VERI*FACTU: {str(e)}")
            
            # Mostrar resultado
            if es_valida:
                validadas += 1
                print(f"  ✓ Factura válida y firmada: {resultado.get('firmado', False)}")
            else:
                con_errores += 1
                print(f"  ✗ Factura con errores: {', '.join(resultado.get('errores', ['Error desconocido']))}")
            
            # Guardar resultado
            resultados.append({
                'id': factura['id'],
                'numero': factura['numero'],
                'ruta_xml': factura['ruta_xml'],
                'valida': es_valida,
                'firmada': resultado.get('firmado', False),
                'errores': resultado.get('errores', []),
                'procesada': datos_verifactu is not None,
                'hash': datos_verifactu['hash'][:16] + '...' if datos_verifactu and 'hash' in datos_verifactu else None
            })
            
        except Exception as e:
            con_errores += 1
            print(f"  ✗ Error al validar la factura: {str(e)}")
            resultados.append({
                'id': factura['id'],
                'numero': factura['numero'],
                'ruta_xml': factura['ruta_xml'],
                'valida': False,
                'firmada': None,
                'errores': [str(e)],
                'procesada': False,
                'hash': None
            })
    
    # Mostrar resumen
    print("\n" + "=" * 50)
    print("RESUMEN DE VALIDACIÓN:")
    print(f"Total de facturas XSIG: {total}")
    print(f"Facturas válidas: {validadas} ({validadas/total*100:.1f}%)")
    print(f"Facturas con errores: {con_errores} ({con_errores/total*100:.1f}%)")
    print(f"Facturas procesadas correctamente: {procesadas_ok} ({procesadas_ok/total*100:.1f}%)")
    
    # Guardar resultados en archivo JSON
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    informe_json = f'/var/www/html/validacion_xsig_{timestamp}.json'
    with open(informe_json, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total': total,
            'validas': validadas,
            'con_errores': con_errores,
            'procesadas_ok': procesadas_ok,
            'resultados': resultados
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\nResultados guardados en: {informe_json}")

if __name__ == "__main__":
    main()

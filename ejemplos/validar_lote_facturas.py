#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para validar un lote completo de facturas Facturae
"""

import os
import sys
import glob
from datetime import datetime
import logging
from collections import Counter

# Importar el módulo de validación
sys.path.append('/var/www/html')
from facturae.validacion import validar_facturae_completa

def validar_lote_facturas(directorio):
    """
    Valida todas las facturas XML en un directorio y genera un informe resumen
    """
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger('validacion_lote')
    
    # Obtener lista de archivos XML
    patron_busqueda = os.path.join(directorio, "*.xml")
    archivos_xml = glob.glob(patron_busqueda)
    
    if not archivos_xml:
        print(f"No se encontraron archivos XML en {directorio}")
        return
    
    # Ordenar archivos
    archivos_xml.sort()
    
    print(f"\n{'=' * 80}")
    print(f"VALIDACIÓN DE LOTE DE FACTURAS")
    print(f"Directorio: {directorio}")
    print(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total facturas a validar: {len(archivos_xml)}")
    print(f"{'=' * 80}\n")
    
    # Resultados
    resultados = []
    contador = Counter()
    
    # Procesar cada archivo
    for idx, ruta_archivo in enumerate(archivos_xml, start=1):
        nombre_archivo = os.path.basename(ruta_archivo)
        print(f"{idx}/{len(archivos_xml)} - Validando: {nombre_archivo}")
        
        try:
            resultado = validar_facturae_completa(ruta_archivo)
            
            # Registrar resultado
            estado = "✅ CORRECTO" if resultado['valido'] else "❌ ERROR"
            contador[estado] += 1
            
            resultados.append({
                'archivo': nombre_archivo,
                'estado': estado,
                'errores': resultado.get('errores', [])
            })
            
            # Mostrar resultado individual
            print(f"  {estado}")
            if not resultado['valido'] and resultado.get('errores'):
                for error in resultado.get('errores'):
                    print(f"  - {error}")
            print("")
            
        except Exception as e:
            print(f"  ⚠️ EXCEPCIÓN: {str(e)}")
            contador["⚠️ EXCEPCIÓN"] += 1
            resultados.append({
                'archivo': nombre_archivo,
                'estado': "⚠️ EXCEPCIÓN",
                'errores': [str(e)]
            })
            print("")
    
    # Imprimir resumen final
    print(f"\n{'=' * 80}")
    print("RESUMEN DE RESULTADOS")
    print(f"{'=' * 80}")
    print(f"Total facturas procesadas: {len(archivos_xml)}")
    for estado, cantidad in contador.items():
        print(f"{estado}: {cantidad} ({cantidad/len(archivos_xml)*100:.1f}%)")
    
    # Agrupar facturas por tipo de error
    if contador["❌ ERROR"] > 0:
        print("\nAGRUPACIÓN POR TIPOS DE ERROR:")
        errores_agrupados = Counter()
        
        for resultado in resultados:
            if resultado['estado'] == "❌ ERROR":
                for error in resultado['errores']:
                    # Extraer tipo de error (primera parte del mensaje)
                    tipo_error = error.split(':')[0] if ':' in error else error
                    errores_agrupados[tipo_error] += 1
        
        for tipo_error, cantidad in errores_agrupados.most_common():
            print(f"- {tipo_error}: {cantidad} factura(s)")
    
    print(f"\n{'=' * 80}")
    return resultados

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python validar_lote_facturas.py <directorio>")
        sys.exit(1)
        
    directorio = sys.argv[1]
    validar_lote_facturas(directorio)

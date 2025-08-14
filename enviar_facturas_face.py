#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Envío automático de facturas a FACe

Este script envía automáticamente las facturas validadas a la plataforma FACe.
Permite procesar todas las facturas de un directorio o una factura específica.
"""

import argparse
import json
import os
import sys
from datetime import datetime

from face_integration import FaceClient, cargar_configuracion

from validar_facturas_mes import (obtener_directorio_mes,
                                  validar_facturas_directorio)


def crear_archivo_configuracion(ruta_config="/var/www/html/face_config.json"):
    """
    Crea un archivo de configuración de ejemplo para FACe si no existe
    """
    if os.path.exists(ruta_config):
        return False
        
    # Directorio para el archivo de configuración
    os.makedirs(os.path.dirname(ruta_config), exist_ok=True)
    
    # Configuración de ejemplo
    config = {
        'entorno': 'desarrollo',  # o 'produccion'
        'ruta_certificado': '/var/www/html/certs/certificado.pfx',
        'password_certificado': 'password_del_certificado',
        'email_notificaciones': 'notificaciones@example.com',
        'organo_gestor': 'L01000000',  # Códigos DIR3 para pruebas
        'unidad_tramitadora': 'L01000000',
        'oficina_contable': 'L01000000'
    }
    
    # Guardar configuración
    with open(ruta_config, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    
    print(f"✅ Archivo de configuración creado en: {ruta_config}")
    print("⚠️ IMPORTANTE: Modifique este archivo con sus datos reales antes de enviar facturas a FACe")
    
    return True

def enviar_facturas_directorio(directorio, solo_validadas=True):
    """
    Envía todas las facturas firmadas (.xsig) de un directorio a FACe
    
    Args:
        directorio (str): Directorio donde buscar las facturas
        solo_validadas (bool): Si es True, sólo envía facturas que pasan la validación
    
    Returns:
        dict: Resultado con facturas enviadas, errores, etc.
    """
    if not os.path.isdir(directorio):
        print(f"❌ Error: El directorio {directorio} no existe")
        return None
    
    print("\n=== ENVÍO DE FACTURAS A FACE ===")
    print(f"Directorio: {directorio}")
    print(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    # Validar facturas primero si es necesario
    if solo_validadas:
        print("\n🔍 Validando facturas antes del envío...")
        resultados_validacion, _, _, _ = validar_facturas_directorio(directorio)
    
    # Buscar facturas .xsig
    facturas_xsig = [os.path.join(directorio, archivo) for archivo in os.listdir(directorio) 
                    if archivo.lower().endswith('.xsig')]
    
    if not facturas_xsig:
        print(f"⚠️ No se encontraron facturas firmadas (.xsig) en {directorio}")
        return None
    
    # Cargar configuración y crear cliente FACe
    config = cargar_configuracion()
    
    try:
        face_client = FaceClient(config)
    except Exception as e:
        print(f"❌ Error al inicializar cliente FACe: {str(e)}")
        print("Revise la configuración en face_config.json")
        return None
    
    # Resultados del procesamiento
    resultados = {
        'enviadas': [],
        'errores': [],
        'omitidas': []
    }
    
    # Procesar cada factura
    for factura in facturas_xsig:
        nombre_factura = os.path.basename(factura)
        
        # Si solo_validadas es True, comprobar si la factura pasó la validación
        if solo_validadas:
            if nombre_factura in resultados_validacion and not resultados_validacion[nombre_factura]['es_valido']:
                print(f"⚠️ Omitiendo factura no válida: {nombre_factura}")
                resultados['omitidas'].append({
                    'factura': nombre_factura,
                    'motivo': f"No pasó la validación: {resultados_validacion[nombre_factura]['mensaje']}"
                })
                continue
        
        print(f"\n📤 Enviando factura: {nombre_factura}")
        
        try:
            # Enviar factura a FACe
            resultado = face_client.enviar_factura(factura)
            
            if resultado['numero_registro']:
                print("✅ Factura enviada correctamente")
                print(f"   Número de registro: {resultado['numero_registro']}")
                
                resultados['enviadas'].append({
                    'factura': nombre_factura,
                    'numero_registro': resultado['numero_registro'],
                    'timestamp': resultado['timestamp']
                })
            else:
                print("❌ Error al enviar factura")
                print(f"   Código: {resultado['codigo_registro']} - {resultado['descripcion']}")
                
                resultados['errores'].append({
                    'factura': nombre_factura,
                    'error': f"Código: {resultado['codigo_registro']} - {resultado['descripcion']}"
                })
        except Exception as e:
            print(f"❌ Error al enviar factura {nombre_factura}: {str(e)}")
            resultados['errores'].append({
                'factura': nombre_factura,
                'error': str(e)
            })
    
    # Imprimir resumen
    print("\n=== RESUMEN DE ENVÍO ===")
    print(f"Total facturas procesadas: {len(facturas_xsig)}")
    print(f"Facturas enviadas: {len(resultados['enviadas'])}")
    print(f"Facturas con error: {len(resultados['errores'])}")
    print(f"Facturas omitidas: {len(resultados['omitidas'])}")
    
    # Guardar informe de envío
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    directorio_informes = "/var/www/html/face_informes"
    os.makedirs(directorio_informes, exist_ok=True)
    
    ruta_informe = os.path.join(directorio_informes, f"informe_envio_{timestamp}.json")
    with open(ruta_informe, 'w', encoding='utf-8') as f:
        json.dump({
            'fecha': datetime.now().isoformat(),
            'directorio': directorio,
            'total_facturas': len(facturas_xsig),
            'resultados': resultados
        }, f, indent=4, ensure_ascii=False)
    
    print(f"📊 Informe de envío guardado en: {ruta_informe}")
    
    return resultados

def main():
    """Función principal"""
    # Comprobar si existe el archivo de configuración
    ruta_config = "/var/www/html/face_config.json"
    if not os.path.exists(ruta_config):
        crear_archivo_configuracion(ruta_config)
        print("Primero debe configurar los parámetros de conexión a FACe en el archivo face_config.json")
        sys.exit(1)
    
    # Definir argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Envío de facturas a FACe')
    parser.add_argument('--directorio', type=str, help='Directorio con facturas a enviar')
    parser.add_argument('--anyo', type=int, help='Año a procesar (por defecto: año actual)')
    parser.add_argument('--mes', type=int, help='Mes a procesar (por defecto: mes actual)')
    parser.add_argument('--factura', type=str, help='Enviar una única factura (ruta completa)')
    parser.add_argument('--todas', action='store_true', help='Enviar todas las facturas, incluso las no válidas')
    
    args = parser.parse_args()
    
    # Si se especifica una única factura
    if args.factura:
        if not os.path.exists(args.factura):
            print(f"❌ Error: La factura {args.factura} no existe")
            return
            
        if not args.factura.lower().endswith('.xsig'):
            print("❌ Error: La factura debe ser un archivo .xsig (firmado)")
            return
            
        print(f"📤 Enviando factura individual: {args.factura}")
        config = cargar_configuracion()
        
        try:
            face_client = FaceClient(config)
            resultado = face_client.enviar_factura(args.factura)
            
            if resultado['numero_registro']:
                print("✅ Factura enviada correctamente")
                print(f"   Número de registro: {resultado['numero_registro']}")
            else:
                print("❌ Error al enviar factura")
                print(f"   Código: {resultado['codigo_registro']} - {resultado['descripcion']}")
        except Exception as e:
            print(f"❌ Error al enviar factura: {str(e)}")
    
    # Si se especifica un directorio directamente
    elif args.directorio:
        if not os.path.isdir(args.directorio):
            print(f"❌ Error: El directorio {args.directorio} no existe")
            return
            
        enviar_facturas_directorio(args.directorio, not args.todas)
    
    # Si se especifica año y/o mes
    else:
        # Obtener el directorio del mes
        directorio = obtener_directorio_mes(
            base_dir="/var/www/html/factura_e",
            año=args.anyo,
            mes=args.mes
        )
        
        if os.path.isdir(directorio):
            enviar_facturas_directorio(directorio, not args.todas)
        else:
            print(f"❌ Error: El directorio para {args.anyo or datetime.now().year}-{args.mes or datetime.now().month} no existe")

if __name__ == "__main__":
    main()

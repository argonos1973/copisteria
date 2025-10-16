#!/usr/bin/env python3

import argparse
import logging
import os
import re
import sys

import pdfplumber
from logger_config import get_logger

# Inicializar logger
logger = get_logger(__name__)

# Configurar argumentos de línea de comandos
parser = argparse.ArgumentParser(description='Procesa archivos PDF de facturas recibidas')
parser.add_argument('--directorio', default='/mnt/swapbatch/2025/1TRIMESTRE',
                    help='Directorio donde están los PDFs (por defecto: /mnt/swapbatch/2025/1TRIMESTRE)')
parser.add_argument('--debug', action='store_true', help='Mostrar texto completo extraído de cada PDF')
parser.add_argument('--texto-completo', action='store_true', help='Mostrar todo el texto del PDF para depuración')
args = parser.parse_args()

# Configurar logging (solo consola)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Ruta del directorio donde están los PDFs
directorio = args.directorio
logging.info(f"Usando el directorio: {directorio}")

# Verificar que el directorio existe y es accesible
if not os.path.exists(directorio):
    logging.error(f"El directorio {directorio} no existe o no es accesible")
    logger.info(f"ERROR: El directorio {directorio} no existe o no es accesible")
    sys.exit(1)

# Expresiones regulares para número de factura
regex_numero_factura = [
    r'Número de factura\s*([A-Z0-9]+)',  # Adobe
    r'N.º? (?:de )?factura:?\s*([A-Z0-9\-\/]+)',  # Formato general
    r'Factura:?\s*([A-Z0-9\-\/]+)',  # Otro formato común
    r'Factura (?:N.º?|num):?\s*([A-Z0-9\-\/]+)',  # Variación
    r'(?:Referencia|Ref\.|Código) de factura:?\s*([A-Z0-9\-\/]+)'  # Más variaciones
]

# Expresiones para valores numéricos en facturas
regex_total_valores = [
    r'TOTAL\s*\(EUR\)\s*([0-9.,]+)',  # Formato exacto de las facturas Adobe
    r'TOTAL FRA\.\s*IMPORTE NETO \(EUR\)\s*([0-9.,]+)',
    r'Importe total\s*([0-9.,]+)\s*EUR',
    r'Total\s*([0-9.,]+)\s*EUR',
    r'Subtotal\s*([0-9.,]+)\s*EUR',
    r'Total factura\s*([0-9.,]+)',
    r'Total a pagar\s*([0-9.,]+)',
    r'Total EUR\s*([0-9.,]+)',
    r'EUR\s*([0-9.,]+)'
]

def buscar_numero_factura(texto):
    """Busca el número de factura en el texto completo del PDF"""
    for regex in regex_numero_factura:
        match = re.search(regex, texto, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None

def buscar_total_en_texto(texto):
    """Busca el total en el texto completo del PDF usando varias expresiones regulares"""
    for regex in regex_total_valores:
        match = re.search(regex, texto, re.IGNORECASE)
        if match:
            return match.group(1).replace(',', '.')
    return None

def identificar_emisor(texto, archivo):
    """Identifica el emisor de la factura basado en el contenido del PDF"""
    if 'Adobe' in texto:
        return "Adobe Systems Software Ireland Ltd"
    elif 'ENDESA' in texto:
        return "ENDESA ENERGÍA"
    elif 'Iberdrola' in texto:
        return "IBERDROLA"
    elif 'Naturgy' in texto:
        return "NATURGY"
    elif 'Vodafone' in texto:
        return "VODAFONE"
    elif 'Orange' in texto:
        return "ORANGE"
    elif 'Movistar' in texto or 'Telefónica' in texto:
        return "TELEFÓNICA"
    
    # Si no se puede identificar por el contenido, intentar por el nombre del archivo
    if '_AE' in archivo:
        return "Adobe Systems"
    
    return "Emisor desconocido"

def extraer_datos_factura(texto, archivo):
    """Extrae los datos de la factura del PDF"""
    total = None
    emisor = identificar_emisor(texto, archivo)
    numero_factura = buscar_numero_factura(texto)
    
    # Buscar el total
    total = buscar_total_en_texto(texto)
    
    # Si no se encuentra con expresiones regulares, buscar manualmente
    if not total:
        lineas = texto.split('\n')
        for linea in lineas:
            if "TOTAL (EUR)" in linea:
                # Extraer el número después de "TOTAL (EUR)"
                partes = linea.split("TOTAL (EUR)")
                if len(partes) > 1:
                    posible_total = partes[1].strip()
                    # Verificar que es un número
                    if re.match(r'^\d+[.,]?\d*$', posible_total):
                        total = posible_total.replace(',', '.')
                        break
    
    # Búsqueda específica para número de factura en Adobe
    if not numero_factura and 'Adobe' in emisor:
        for linea in texto.split('\n'):
            if "Número de factura" in linea:
                partes = linea.split("Número de factura")
                if len(partes) > 1:
                    posible_numero = partes[1].strip()
                    numero_factura = posible_numero
                    break
    
    # Búsqueda genérica como último recurso
    if not total:
        for linea in texto.split('\n'):
            if 'total' in linea.lower():
                # Buscar algo que parezca un importe en la línea
                posible_total = re.search(r'(\d+[.,]\d+)', linea)
                if posible_total:
                    total = posible_total.group(1).replace(',', '.')
                    break
    
    return {
        'archivo': archivo,
        'emisor': emisor,
        'numero_factura': numero_factura,
        'total': total
    }

resultados = []
errores = []

try:
    # Verificar archivos disponibles
    archivos = os.listdir(directorio)
    logging.info(f"Se encontraron {len(archivos)} archivos en el directorio")
except (PermissionError, FileNotFoundError) as e:
    logging.error(f"Error al acceder al directorio {directorio}: {str(e)}")
    logger.info(f"ERROR: No se puede acceder al directorio {directorio}")
    logger.info("Intente ejecutar el script con otro directorio usando --directorio=/ruta/a/directorio")
    sys.exit(1)

archivos_pdf = [archivo for archivo in archivos if archivo.lower().endswith('.pdf')]
logging.info(f"Se encontraron {len(archivos_pdf)} archivos PDF")

if not archivos_pdf:
    logging.warning("No se encontraron archivos PDF en el directorio")
    logger.info("ADVERTENCIA: No se encontraron archivos PDF en el directorio")
    sys.exit(0)

for archivo in archivos_pdf:
    ruta_pdf = os.path.join(directorio, archivo)
    try:
        logging.info(f"Procesando archivo: {archivo}")
        
        # Verificar que el archivo existe y es accesible
        if not os.path.isfile(ruta_pdf):
            logging.warning(f"El archivo {ruta_pdf} ya no existe o no es accesible")
            errores.append({'archivo': archivo, 'error': 'Archivo no accesible'})
            continue
            
        with pdfplumber.open(ruta_pdf) as pdf:
            texto = ''
            for pagina in pdf.pages:
                texto += pagina.extract_text() + '\n'
            
            if args.texto_completo:
                logger.info(f"\n==== TEXTO COMPLETO DE {archivo} ====")
                logger.info(f"texto)
                print("=" * 50)
            elif args.debug:
                logger.info(f"\n---- CONTENIDO DE {archivo} ----")
                print(texto[:500] + "..." if len(texto) > 500 else texto)
                print("-" * 50)
            
            resultado = extraer_datos_factura(texto archivo")
            resultados.append(resultado)
            logging.info(f"Archivo {archivo} procesado correctamente")
            
    except Exception as e:
        logging.error(f"Error al procesar {archivo}: {str(e)}")
        errores.append({'archivo': archivo, 'error': str(e)})

# Mostrar resultados
logging.info(f"Se procesaron correctamente {len(resultados)} archivos")
logger.info(f"\nResultados ({len(resultados)} archivos procesados correctamente):")
for r in resultados:
    num_factura = f" | N° Factura: {r['numero_factura']}" if r['numero_factura'] else ""
    logger.info(f"{r['archivo']}: Emisor: {r['emisor']}{num_factura} | Total: {r['total'] or 'No encontrado'} €")

# Mostrar errores
if errores:
    logging.warning(f"Se encontraron {len(errores)} archivos con errores")
    logger.info(f"\nArchivos con errores ({len(errores)}):")
    for e in errores:
        logger.info(f"{e['archivo']}: {e['error']}")

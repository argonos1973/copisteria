#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validador de facturas electrónicas del mes en curso
Este script escanea todas las facturas electrónicas (.xml y .xsig) del mes actual
y las valida, generando un informe de los resultados.
"""

import argparse
import os
from datetime import datetime

from facturae_utils import leer_contenido_xsig
from validar_facturae import validar_facturae
from logger_config import get_logger

# Inicializar logger
logger = get_logger(__name__)


def obtener_directorio_mes(base_dir="/var/www/html/factura_e", año=None, mes=None):
    """
    Obtiene la ruta del directorio para el mes especificado.
    Si no se especifica año o mes, usa el mes actual.
    
    Args:
        base_dir (str): Directorio base donde se encuentran las facturas
        año (int): Año a validar (opcional)
        mes (int): Mes a validar (opcional)
        
    Returns:
        str: Ruta del directorio para el mes especificado
    """
    if año is None or mes is None:
        ahora = datetime.now()
        if año is None:
            año = ahora.year
        if mes is None:
            mes = ahora.month
    
    # Asegurarse de que mes sea un string de 2 dígitos
    mes_str = str(mes).zfill(2)
    
    directorio = os.path.join(base_dir, str(año), mes_str)
    return directorio

def validar_facturas_directorio(directorio):
    """
    Valida todas las facturas (.xml y .xsig) en el directorio especificado.
    
    Args:
        directorio (str): Ruta del directorio a procesar
        
    Returns:
        tuple: (dict de resultados, total_facturas, facturas_válidas, facturas_inválidas)
    """
    if not os.path.isdir(directorio):
        logger.info(f"❌ El directorio {directorio} no existe")
        return {}, 0, 0, 0
    
    logger.info(f"📁 Procesando facturas en: {directorio}")
    
    resultados = {}
    total = 0
    validos = 0
    invalidos = 0
    
    # Listar todos los archivos .xml y .xsig en el directorio
    for archivo in os.listdir(directorio):
        if archivo.endswith(('.xml', '.xsig')):
            ruta_completa = os.path.join(directorio, archivo)
            total += 1
            
            logger.info(f"🔍 Validando: {archivo}...")
            try:
                es_valido, mensaje = validar_facturae(ruta_completa)
                
                if es_valido:
                    validos += 1
                    estado = "✅ VÁLIDO"
                else:
                    invalidos += 1
                    estado = "❌ INVÁLIDO"
                
                # Intentar extraer información básica de la factura
                info_adicional = ""
                try:
                    # Si es un .xsig, primero extraer el XML
                    if archivo.endswith('.xsig'):
                        contenido = leer_contenido_xsig(ruta_completa)
                    else:
                        with open(ruta_completa, 'r', encoding='utf-8') as f:
                            contenido = f.read()
                            
                    # Extraer información básica (simplificado)
                    if "TaxIdentificationNumber" in contenido:
                        import re
                        numero_match = re.search(r'<InvoiceNumber>(.*?)</InvoiceNumber>', contenido)
                        emisor_match = re.search(r'<SellerParty>.*?<TaxIdentificationNumber>(.*?)</TaxIdentificationNumber>', contenido, re.DOTALL)
                        receptor_match = re.search(r'<BuyerParty>.*?<TaxIdentificationNumber>(.*?)</TaxIdentificationNumber>', contenido, re.DOTALL)
                        
                        numero = numero_match.group(1) if numero_match else "Desconocido"
                        emisor = emisor_match.group(1) if emisor_match else "Desconocido"
                        receptor = receptor_match.group(1) if receptor_match else "Desconocido"
                        
                        info_adicional = f" - Número: {numero} - Emisor: {emisor} - Receptor: {receptor}"
                except Exception as e:
                    info_adicional = f" - Error al extraer información: {str(e)}"
                
                resultados[archivo] = {
                    'es_valido': es_valido,
                    'mensaje': mensaje,
                    'ruta': ruta_completa,
                    'info': info_adicional
                }
                
                logger.info(f"    {estado}: {mensaje}{info_adicional}")
                
            except Exception as e:
                invalidos += 1
                resultados[archivo] = {
                    'es_valido': False,
                    'mensaje': f"Error al procesar: {str(e)}",
                    'ruta': ruta_completa,
                    'info': ""
                }
                logger.info(f"    ❌ Error al procesar: {str(e)}")
    
    return resultados, total, validos, invalidos

def generar_informe(resultados, directorio, total, validos, invalidos):
    """
    Genera un informe HTML con los resultados de la validación.
    
    Args:
        resultados (dict): Resultados de la validación
        directorio (str): Directorio procesado
        total (int): Total de facturas procesadas
        validos (int): Número de facturas válidas
        invalidos (int): Número de facturas inválidas
        
    Returns:
        str: Ruta del archivo de informe generado
    """
    ahora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    ruta_informe = f"/tmp/informe_validacion_{ahora}.html"
    
    porcentaje_validos = (validos / total * 100) if total > 0 else 0
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Informe de Validación de Facturas</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #2c3e50; }}
        .resumen {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .valido {{ color: green; }}
        .invalido {{ color: red; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; }}
        tr:hover {{ background-color: #f5f5f5; }}
    </style>
</head>
<body>
    <h1>Informe de Validación de Facturas Electrónicas</h1>
    <div class="resumen">
        <p><strong>Directorio:</strong> {directorio}</p>
        <p><strong>Fecha de análisis:</strong> {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}</p>
        <p><strong>Total facturas:</strong> {total}</p>
        <p><strong>Facturas válidas:</strong> <span class="valido">{validos} ({porcentaje_validos:.1f}%)</span></p>
        <p><strong>Facturas inválidas:</strong> <span class="invalido">{invalidos}</span></p>
    </div>
    <h2>Detalle de facturas</h2>
    <table>
        <tr>
            <th>Archivo</th>
            <th>Estado</th>
            <th>Mensaje</th>
            <th>Información</th>
        </tr>
"""
    
    for archivo, datos in sorted(resultados.items()):
        estado_class = "valido" if datos['es_valido'] else "invalido"
        estado_texto = "VÁLIDO" if datos['es_valido'] else "INVÁLIDO"
        html += f"""
        <tr>
            <td>{archivo}</td>
            <td class="{estado_class}">{estado_texto}</td>
            <td>{datos['mensaje']}</td>
            <td>{datos['info']}</td>
        </tr>"""
    
    html += """
    </table>
</body>
</html>"""
    
    with open(ruta_informe, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return ruta_informe

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Validador de facturas electrónicas del mes en curso')
    parser.add_argument('--anyo', type=int, help='Año a procesar (por defecto: año actual)')
    parser.add_argument('--mes', type=int, help='Mes a procesar (por defecto: mes actual)')
    parser.add_argument('--dir', type=str, help='Directorio base (por defecto: /var/www/html/factura_e)')
    
    args = parser.parse_args()
    
    # Obtener el directorio del mes
    directorio = obtener_directorio_mes(
        base_dir=args.dir or "/var/www/html/factura_e",
        año=args.anyo,
        mes=args.mes
    )
    
    logger.info("\n=== VALIDADOR DE FACTURAS ELECTRÓNICAS ===")
    logger.info(f"Fecha actual: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    logger.info(f"Directorio a procesar: {directorio}")
    
    # Validar facturas en el directorio
    resultados, total, validos, invalidos = validar_facturas_directorio(directorio)
    
    if total == 0:
        logger.info(f"\n⚠️ No se encontraron facturas para validar en {directorio}")
        logger.info("Puede especificar otro mes o año con --anyo y --mes")
        return
    
    # Generar informe
    ruta_informe = generar_informe(resultados, directorio, total, validos, invalidos)
    
    logger.info("\n=== RESUMEN DE VALIDACIÓN ===")
    logger.info(f"Total facturas: {total}")
    logger.info(f"Facturas válidas: {validos} ({(validos/total*100):.1f}%)")
    logger.info(f"Facturas inválidas: {invalidos}")
    logger.info(f"\nInforme generado en: {ruta_informe}")
    logger.info("Puede visualizarlo en su navegador")

if __name__ == "__main__":
    main()

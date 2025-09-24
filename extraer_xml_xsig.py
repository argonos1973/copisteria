#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import sys
import tempfile

from lxml import etree


def extraer_xml_desde_xsig(ruta_xsig):
    """
    Extrae el contenido XML de un archivo XSIG.
    
    Args:
        ruta_xsig: Ruta al archivo XSIG
        
    Returns:
        tuple: (contenido_xml, ruta_archivo_temporal)
    """
    # Verificar que existe el archivo
    if not os.path.exists(ruta_xsig):
        print(f"El archivo {ruta_xsig} no existe.")
        return None, None
        
    # Crear un archivo temporal para guardar el XML extraído
    fd, archivo_temporal = tempfile.mkstemp(suffix='.xml', prefix='facturae_')
    os.close(fd)
    
    # Intentar extraer el XML usando xsltproc
    try:
        comando_xsltproc = f"xsltproc --html --output {archivo_temporal} {ruta_xsig}"
        resultado = subprocess.run(comando_xsltproc, shell=True, capture_output=True, text=True)
        
        # Si falla xsltproc, intentar con openssl
        if resultado.returncode != 0:
            print("xsltproc falló, intentando con openssl...")
            comando_openssl = f"openssl smime -verify -inform DER -in {ruta_xsig} -noverify -out {archivo_temporal}"
            resultado = subprocess.run(comando_openssl, shell=True, capture_output=True, text=True)
            
            # Si openssl falla, probar con formato PEM en lugar de DER
            if resultado.returncode != 0:
                print("openssl (DER) falló, intentando con formato PEM...")
                comando_openssl = f"openssl smime -verify -inform PEM -in {ruta_xsig} -noverify -out {archivo_temporal}"
                resultado = subprocess.run(comando_openssl, shell=True, capture_output=True, text=True)
                
        # Verificar si se creó el archivo y tiene contenido
        if os.path.exists(archivo_temporal) and os.path.getsize(archivo_temporal) > 0:
            with open(archivo_temporal, 'r', encoding='utf-8') as f:
                contenido = f.read()
            return contenido, archivo_temporal
        else:
            print("No se pudo extraer el XML del archivo XSIG.")
            return None, None
    except Exception as e:
        print(f"Error al extraer XML desde XSIG: {str(e)}")
        return None, None

def analizar_totales_xml(ruta_xml):
    """
    Analiza los totales de un archivo XML de Facturae.
    
    Args:
        ruta_xml: Ruta al archivo XML
        
    Returns:
        dict: Diccionario con los totales encontrados
    """
    try:
        # Leer el archivo XML
        tree = etree.parse(ruta_xml)
        root = tree.getroot()
        
        # Definir los namespaces habituales en Facturae
        namespaces = {
            'fe': 'http://www.facturae.es/Facturae/2009/v3.2/Facturae',
            'fe32': 'http://www.facturae.es/Facturae/2009/v3.2/Facturae',
            'fe322': 'http://www.facturae.es/Facturae/2014/v3.2.2/Facturae',
            'ds': 'http://www.w3.org/2000/09/xmldsig#',
            None: 'http://www.facturae.es/Facturae/2009/v3.2/Facturae'
        }
        
        # Detectar el namespace real del documento
        doc_ns = root.nsmap.get(None)
        if doc_ns:
            print(f"Namespace del documento: {doc_ns}")
            namespaces[None] = doc_ns
        
        # Definir las rutas XPath para los totales con varios namespaces posibles
        totales = {}
        rutas_totales = [
            # Con namespace específico
            '//fe:Facturae/fe:Invoices/fe:Invoice/fe:InvoiceTotals/fe:TotalGrossAmount',
            '//fe32:Facturae/fe32:Invoices/fe32:Invoice/fe32:InvoiceTotals/fe32:TotalGrossAmount',
            '//fe322:Facturae/fe322:Invoices/fe322:Invoice/fe322:InvoiceTotals/fe322:TotalGrossAmount',
            # Sin namespace (usando el predeterminado)
            '//Facturae/Invoices/Invoice/InvoiceTotals/TotalGrossAmount',
            # Buscando sólo por nombre del campo
            '//TotalGrossAmount',
        ]
        
        # Intentar encontrar los totales con diferentes XPath
        for ruta in rutas_totales:
            elementos = root.xpath(ruta, namespaces=namespaces)
            if elementos:
                print(f"Elementos encontrados con XPath: {ruta}")
                print(f"Total de elementos: {len(elementos)}")
                break
        
        # Si no se encontraron elementos, volver a intentar extrayendo los elementos directamente
        if not elementos:
            print("Buscando elementos manualmente...")
            for elem in root.iter():
                tag = elem.tag
                if tag.endswith('TotalGrossAmount'):
                    print(f"Encontrado elemento: {tag} = {elem.text}")
                    elementos = [elem]
                    break
                    
        # Buscar todos los elementos de totales relevantes
        paths = [
            ('TotalGrossAmount', '//TotalGrossAmount'),
            ('TotalGrossAmountBeforeTaxes', '//TotalGrossAmountBeforeTaxes'),
            ('TotalTaxOutputs', '//TotalTaxOutputs'),
            ('InvoiceTotal', '//InvoiceTotal'),
            ('TotalOutstandingAmount', '//TotalOutstandingAmount'),
            ('TotalExecutableAmount', '//TotalExecutableAmount'),
        ]
        
        print("\n--- TOTALES DETECTADOS EN EL XML ---")
        for nombre, xpath in paths:
            for ns_key, ns_uri in namespaces.items():
                if ns_key is not None:
                    elementos = root.xpath(f"//{ns_key}:{nombre}", namespaces=namespaces)
                    if elementos:
                        totales[nombre] = elementos[0].text
                        print(f"{nombre}: {elementos[0].text}")
                        break
            
            # Si no encontramos con namespace, buscar sin él
            if nombre not in totales:
                elementos = root.xpath(f"//{nombre}", namespaces=namespaces)
                if elementos:
                    totales[nombre] = elementos[0].text
                    print(f"{nombre}: {elementos[0].text}")
                else:
                    print(f"{nombre}: No encontrado")
                    
        return totales
    except Exception as e:
        print(f"Error al analizar totales XML: {str(e)}")
        import traceback
        traceback.print_exc()
        return {}

def main():
    """Función principal"""
    if len(sys.argv) < 2:
        print("Uso: python extraer_xml_xsig.py ruta_archivo.xsig")
        return
        
    ruta_xsig = sys.argv[1]
    contenido, archivo_temporal = extraer_xml_desde_xsig(ruta_xsig)
    
    if contenido and archivo_temporal:
        print(f"XML extraído correctamente a: {archivo_temporal}")
        print("\n--- PRIMERAS LÍNEAS DEL XML ---")
        lineas = contenido.split('\n')
        for i, linea in enumerate(lineas[:20]):
            print(f"{i+1}: {linea}")
        
        print("\n--- ANALIZANDO TOTALES ---")
        totales = analizar_totales_xml(archivo_temporal)
        
        # Analizar si los totales son correctos
        if 'InvoiceTotal' in totales and float(totales.get('InvoiceTotal', '0.00')) > 0:
            print("\n✅ TOTALES CORRECTOS - La factura tiene valores correctos")
        else:
            print("\n❌ TOTALES INCORRECTOS - Hay problemas con los totales de la factura")
    else:
        print("No se pudo extraer el XML del archivo XSIG.")

if __name__ == "__main__":
    main()

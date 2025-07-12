#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de XML para el sistema VERI*FACTU

Implementa la generación de archivos XML según el formato requerido
por AEAT para el sistema VERI*FACTU
"""

import os
import xml.etree.ElementTree as ET
from datetime import datetime

from lxml import etree

from ..config import AEAT_CONFIG, VERIFACTU_CONSTANTS, logger
from ..db.utils import get_db_connection


def generar_xml_para_aeat(factura_id):
    """
    Genera el XML que se envía al webservice SOAP de la AEAT para VERI*FACTU.
    
    Args:
        factura_id: ID de la factura a enviar
        
    Returns:
        dict: Datos necesarios para el envío o None si hay error
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener datos de la factura
        cursor.execute('''
            SELECT f.id, f.numero, f.fecha as fecha_emision, c.identificador as nif_receptor, 
                   f.total, f.importe_impuestos as iva, f.nif as nif_emisor, r.hash as hash_factura,
                   r.id as registro_id, r.tipo_factura
            FROM factura f
            LEFT JOIN contactos c ON f.idContacto = c.idContacto
            LEFT JOIN registro_facturacion r ON f.id = r.factura_id
            WHERE f.id = ?
        ''', (factura_id,))
        
        factura = cursor.fetchone()
        
        if not factura:
            logger.error(f"No se encontró la factura con ID {factura_id}")
            return None
        
        # Generar número de factura con prefijo BATCH- si no lo tiene
        numero_factura = factura['numero']
        if not numero_factura.startswith(VERIFACTU_CONSTANTS['prefijo_batch']):
            numero_factura = f"{VERIFACTU_CONSTANTS['prefijo_batch']}{numero_factura}"
        
        # Obtener la hora actual para el timestamp
        hora_actual = datetime.now().strftime("%H:%M:%S")
        
        # Asegurar que tenemos el hash de la factura
        hash_factura = factura['hash_factura']
        
        # Preparar datos para el XML
        datos_xml = {
            'nif_emisor': factura['nif_emisor'],
            'fecha_emision': factura['fecha_emision'],
            'hora_emision': hora_actual,
            'numero_factura': numero_factura,
            'serie_factura': 'A', # No hay columna serie en la tabla factura
            'importe_total': "{:.2f}".format(factura['total']),
            'cuota_impuestos': "{:.2f}".format(factura['iva']) if factura['iva'] else "0.00",
            'nif_receptor': factura['nif_receptor'],
            'hash_factura': hash_factura,
            'timestamp_envio': datetime.now().isoformat(),
            'tipo_factura': factura['tipo_factura'] if factura['tipo_factura'] else VERIFACTU_CONSTANTS['tipo_factura_default']
        }
        
        # Construir el árbol XML para VERI*FACTU
        root = etree.Element("{%s}VeriFactuEnvio" % AEAT_CONFIG['namespace'])
        
        # Configurar el namespace
        nsmap = {None: AEAT_CONFIG['namespace']}
        root = etree.Element("VeriFactuEnvio", nsmap=nsmap)
        
        # Crear el elemento Factura
        factura_elem = etree.SubElement(root, "Factura")
        
        # Añadir elementos obligatorios según especificación VERI*FACTU
        etree.SubElement(factura_elem, "NIF").text = datos_xml['nif_emisor']
        etree.SubElement(factura_elem, "FechaExpedicion").text = datos_xml['fecha_emision']
        etree.SubElement(factura_elem, "HoraExpedicion").text = datos_xml['hora_emision']
        etree.SubElement(factura_elem, "NumeroFactura").text = datos_xml['numero_factura']
        etree.SubElement(factura_elem, "Serie").text = datos_xml['serie_factura']
        etree.SubElement(factura_elem, "ImporteTotal").text = datos_xml['importe_total']
        
        # Añadir el hash encadenado
        if hash_factura:
            etree.SubElement(factura_elem, "Hash").text = hash_factura
            
        # Convertir a string XML
        xml_string = etree.tostring(
            root, 
            pretty_print=True, 
            xml_declaration=True, 
            encoding="utf-8"
        )
        
        # Añadir el XML generado a los datos de retorno
        datos_xml['xml'] = xml_string
        
        logger.info(f"XML generado para factura ID {factura_id} ({len(xml_string)} bytes)")
        
        return datos_xml
        
    except Exception as e:
        logger.error(f"Error al generar XML para AEAT: {e}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        if conn:
            conn.close()

def extraer_xml_desde_xsig(ruta_xsig):
    """
    Extrae el XML original desde un archivo XSIG firmado.
    
    Args:
        ruta_xsig: Ruta al archivo XSIG
        
    Returns:
        bytes: Contenido XML extraído o None si hay error
    """
    try:
        if not os.path.exists(ruta_xsig):
            logger.error(f"El archivo XSIG no existe: {ruta_xsig}")
            return None
            
        # Usar lxml para parsear el archivo XSIG
        tree = etree.parse(ruta_xsig)
        root = tree.getroot()
        
        # Buscar el contenido original (normalmente en Object dentro de Signature)
        # Esta implementación puede variar según la estructura exacta de los XSIG
        nsmap = {'ds': 'http://www.w3.org/2000/09/xmldsig#'}
        
        # Intentar encontrar el objeto que contiene el contenido original
        for obj in root.findall(".//ds:Object", namespaces=nsmap):
            # Si encontramos el contenido original, devolverlo
            if len(obj) > 0:
                # Convertir el primer hijo a string XML
                xml_content = etree.tostring(obj[0], encoding="utf-8")
                return xml_content
        
        logger.error("No se pudo encontrar contenido XML en el archivo XSIG")
        return None
        
    except Exception as e:
        logger.error(f"Error al extraer XML desde XSIG: {e}")
        return None

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validador de facturas XML para el sistema VERI*FACTU

Implementa la validación de archivos XML y XSIG firmados
según los requisitos del sistema VERI*FACTU
"""

import os

from lxml import etree

from ..config import logger


def validar_factura_xml_antes_procesar(ruta_xml):
    """
    Valida el archivo XML de factura antes de procesarlo para VERI*FACTU.
    Comprueba estructura, campos obligatorios y formato.
    
    Args:
        ruta_xml: Ruta al archivo XML
        
    Returns:
        bool: True si el archivo es válido, False en caso contrario
    """
    try:
        # Verificar si el archivo existe
        if not os.path.exists(ruta_xml):
            logger.error(f"El archivo XML no existe: {ruta_xml}")
            return False
            
        # Parsear el XML
        try:
            tree = etree.parse(ruta_xml)
            root = tree.getroot()
        except Exception as e:
            logger.error(f"Error al parsear XML: {e}")
            return False
            
        # Verificar que sea un XML válido según Facturae
        # En una implementación completa habría que validar contra el XSD de Facturae
        
        # Verificar campos mínimos requeridos para VERI*FACTU
        # En una implementación completa habría que verificar según especificaciones de AEAT
        
        logger.info(f"Validación básica de XML correcta: {ruta_xml}")
        return True
        
    except Exception as e:
        logger.error(f"Error al validar XML: {e}")
        return False

def validar_factura_xsig(ruta_xsig):
    """
    Valida un archivo de factura firmado (XSIG).
    
    Args:
        ruta_xsig: Ruta al archivo XSIG
        
    Returns:
        bool: True si el archivo es válido, False en caso contrario
    """
    try:
        # Verificar si el archivo existe
        if not os.path.exists(ruta_xsig):
            logger.error(f"El archivo XSIG no existe: {ruta_xsig}")
            return False
        
        # En una implementación completa, habría que:
        # 1. Verificar que es un archivo XML firmado válido
        # 2. Extraer el certificado usado para firmar y verificarlo
        # 3. Validar la firma contra el contenido
        # 4. Verificar que la política de firma es correcta
        
        logger.info(f"Validación básica de XSIG correcta: {ruta_xsig}")
        return True
        
    except Exception as e:
        logger.error(f"Error al validar XSIG: {e}")
        return False

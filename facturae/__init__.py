#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo principal de Facturae.
Este módulo integra la funcionalidad de generación y firma de facturas electrónicas Facturae.
"""

from facturae.validacion import es_persona_fisica, validar_nif
from facturae.utils import separar_nombre_apellidos, dividir_nombre_apellidos
from facturae.xml_template import obtener_plantilla_xml
from facturae.generador import generar_facturae
from facturae.firma import firmar_xml, corregir_etiqueta_n_por_name, leer_contenido_xsig

# Función añadida para evitar errores de importación
def extraer_xml_desde_xsig(ruta_xsig):
    """Función temporal para extraer XML desde un archivo XSIG
    
    Args:
        ruta_xsig (str): Ruta al archivo XSIG
        
    Returns:
        tuple: (éxito, ruta_archivo_temporal)
    """
    import tempfile
    import os
    import logging
    
    logger = logging.getLogger(__name__)
    logger.warning("Usando versión temporal de extraer_xml_desde_xsig")
    
    contenido = leer_contenido_xsig(ruta_xsig)
    if not contenido:
        return False, None
        
    # Crear archivo temporal con el XML
    fd, ruta_temp = tempfile.mkstemp(suffix='.xml', prefix='facturae_')
    os.write(fd, contenido.encode('utf-8'))
    os.close(fd)
    
    return True, ruta_temp

# Configuraciones
CERTIFICADO_PATH    = "/media/sami/copia500/cert_real.pem"
CLAVE_PRIVADA_PATH  = "/media/sami/copia500/clave_real.pem"

#CLAVE_PRIVADA_PATH = "/var/www/html/certs/clave_privada.key"
#CERTIFICADO_PATH = "/var/www/html/certs/certificado.crt"

__all__ = [
    'es_persona_fisica',
    'validar_nif',
    'separar_nombre_apellidos',
    'extraer_xml_desde_xsig',
    'dividir_nombre_apellidos',
    'generar_facturae',
    'firmar_xml',
    'corregir_etiqueta_n_por_name',
    'leer_contenido_xsig',
    'extraer_xml_desde_xsig',
    'CLAVE_PRIVADA_PATH',
    'CERTIFICADO_PATH'
]

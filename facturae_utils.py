#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AVISO: Este archivo ahora es un wrapper para mantener compatibilidad.
Las funcionalidades han sido migradas al nuevo paquete modular 'facturae'.
Se recomienda usar directamente las funciones desde los módulos específicos.
"""

import logging
import os
import sys
import warnings

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Advertencia sobre el uso del wrapper
warnings.warn(
    "facturae_utils.py está obsoleto. Use directamente el paquete 'facturae'.",
    DeprecationWarning, 
    stacklevel=2
)

# Definición de constantes (para compatibilidad con código antiguo)
CLAVE_PRIVADA_PATH = "/var/www/html/certs/clave_privada.key"
CERTIFICADO_PATH = "/var/www/html/certs/certificado.crt"

# Verificación de dependencias críticas
try:
    # Importar dependencias necesarias
    import lxml.etree
    from cryptography.hazmat.primitives.serialization import \
        load_pem_private_key
    from signxml import XMLSigner
    logger.info("✅ Todas las dependencias importadas correctamente")
except ImportError as e:
    logger.error(f"❌ ERROR: Problema con las dependencias: {e}")
    sys.exit(1)

from facturae.firma import (corregir_etiqueta_n_por_name, firmar_xml,
                            leer_contenido_xsig)
from facturae.generador import generar_facturae
from facturae.utils import dividir_nombre_apellidos, separar_nombre_apellidos
# Importar todas las funcionalidades desde el nuevo paquete modular
from facturae.validacion import es_persona_fisica, validar_nif
from facturae.xml_template import obtener_plantilla_xml

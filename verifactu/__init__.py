#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Paquete VERI*FACTU para integración con AEAT

Este paquete proporciona todas las funcionalidades necesarias para cumplir 
con el sistema VERI*FACTU de la AEAT, incluyendo:
- Generación de códigos QR según normativa
- Cálculo de hashes SHA-256 encadenados
- Gestión de registros de facturación
- Comunicación con servicios web SOAP de AEAT
- Integración con sistema de facturación existente
"""

from .config import AEAT_CONFIG
# Función principal que integra todo el proceso VERI*FACTU
from .core import generar_datos_verifactu_para_factura
from .db.registro import (actualizar_factura_con_hash,
                          crear_registro_facturacion)
from .hash.sha256 import generar_hash_factura, obtener_ultimo_hash
from .qr.generator import generar_qr_verifactu
from .soap.client import enviar_registro_aeat
from .utils.validator import validar_factura_xml_antes_procesar
from .xml.generator import generar_xml_para_aeat

__version__ = '1.0.0'

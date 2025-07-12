#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Archivo de compatibilidad para VERI*FACTU

Este archivo proporciona compatibilidad con código existente
que importaba funciones desde el antiguo verifactu.py monolítico.
Todas las funciones se redirigen a la nueva estructura modular.
"""

# Importar todas las funciones públicas del nuevo paquete modular
from verifactu.config import AEAT_CONFIG, logger
from verifactu.core import (generar_datos_verifactu_para_factura,
                            verificar_estado_registro_aeat)
from verifactu.db.registro import (actualizar_factura_con_hash,
                                   crear_registro_facturacion)
from verifactu.hash.sha256 import generar_hash_factura, obtener_ultimo_hash
from verifactu.qr.generator import generar_qr_verifactu
from verifactu.soap.client import enviar_registro_aeat, simular_envio_aeat
from verifactu.utils.validator import (validar_factura_xml_antes_procesar,
                                       validar_factura_xsig)
from verifactu.xml.generator import (extraer_xml_desde_xsig,
                                     generar_xml_para_aeat)

# No es necesario duplicar el código aquí, simplemente exportamos
# todas las funciones de la nueva estructura modular

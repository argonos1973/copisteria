#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuración del sistema VERI*FACTU para la integración con AEAT
"""

import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('verifactu')

# Configuración para la conexión con AEAT VERI*FACTU
AEAT_CONFIG = {
    # SOAP Endpoints
    'wsdl_url': 'https://prewww2.aeat.es/static_files/common/internet/dep/aplicaciones/es/aeat/tikeV1.0/cont/ws/SistemaFacturacion.wsdl',
    'soap_endpoint_test': 'https://prewww1.aeat.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP',
    'soap_endpoint_prod': 'https://www1.agenciatributaria.gob.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP',
    'soap_endpoint_test_sello': 'https://prewww10.aeat.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP',
    'soap_endpoint_prod_sello': 'https://www10.agenciatributaria.gob.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP',
    
    # Namespace oficial VERI*FACTU
    'namespace': 'https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/ssii/fact/ws/VeriFactu',
    
    # Certificados
    'cert_path': '/var/www/html/certs/cert.pem',  # Certificado público en formato PEM
    'key_path': '/var/www/html/certs/clave.pem',  # Clave privada en formato PEM
    
    # Configuración
    'timeout': 30,  # segundos
    'reintentos': 3,  # Número de reintentos ante fallos
    'entorno': 'test',  # Forzamos el entorno de pruebas
    'usar_sello': False,  # True para usar certificado de sello
    'verificar_ssl': True,  # Verificación SSL del servidor
    'modo_test': False,  # Indicador explícito de modo pruebas
    
    # URL para código QR
    'url_cotejo': 'https://sede.agenciatributaria.gob.es/verifactu/cotejo'
}

# Constantes para el sistema VERI*FACTU
VERIFACTU_CONSTANTS = {
    'prefijo_batch': 'BATCH-',
    'algoritmo_hash': 'SHA-256',
    'formato_fecha_qr': '%d-%m-%Y',  # Formato DD-MM-YYYY para QR
    'qr_box_size': 8,  # Tamaño del QR (30-40mm según normativa)
    'qr_border': 4,
    'qr_error_correction': 'M',  # Nivel medio (15%)
    'tipo_factura_default': 'FC',
    'nombre_sistema': 'VerifactuApp',
    'id_sistema': '01',
    'version_sistema': '1.0',
    'numero_instalacion': '0001'
}

# Códigos de error y mensajes
ERROR_CODES = {
    '0': 'Operación realizada correctamente',
    '1000': 'Error genérico',
    '1001': 'Error en la validación de la estructura del mensaje',
    '1002': 'Error de autenticación',
    '1003': 'NIF no autorizado para este servicio',
    '4118': 'Error en la dirección registrada para el NIF',
    # Añadir más códigos según documentación AEAT
}

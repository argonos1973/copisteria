#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilidades de base de datos para VERI*FACTU

Importa funciones desde el módulo db_utils.py existente
"""

# Importar funciones directamente desde el archivo db_utils.py global
import sys

# Asegurar que el directorio raíz está en el path para importar db_utils.py
sys.path.insert(0, '/var/www/html')

# Importar funciones desde db_utils.py
from db_utils import (actualizar_numerador, formatear_numero_documento,
                      get_db_connection, obtener_numerador, redondear_importe,
                      verificar_numero_factura, verificar_numero_proforma)

# Reexportar las funciones para mantener compatibilidad
__all__ = [
    'get_db_connection',
    'redondear_importe',
    'actualizar_numerador',
    'obtener_numerador',
    'formatear_numero_documento',
    'verificar_numero_factura',
    'verificar_numero_proforma'
]

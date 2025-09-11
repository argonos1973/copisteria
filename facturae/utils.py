#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Utilidades generales para el manejo de Facturae.
"""

import logging
import re

logger = logging.getLogger(__name__)

def _split_nombre(nombre_completo: str):
    """Devuelve el nombre y los apellidos por separado."""
    if not nombre_completo or nombre_completo.strip() == "":
        return ("", "", "")

    partes = nombre_completo.strip().split()

    if len(partes) == 1:
        return (partes[0], "", "")
    if len(partes) == 2:
        return (partes[0], partes[1], "")

    nombre = partes[0]
    segundo_apellido = partes[-1]
    primer_apellido = " ".join(partes[1:-1])
    return (nombre, primer_apellido, segundo_apellido)


def separar_nombre_apellidos(nombre_completo):
    """Separa un nombre completo en nombre y apellidos."""
    return _split_nombre(nombre_completo)

def dividir_nombre_apellidos(nombre_completo):
    """Alias de :func:`separar_nombre_apellidos` por compatibilidad."""
    return _split_nombre(nombre_completo)

def procesar_serie_numero(numero_completo):
    """
    Procesa un número de factura completo para separar correctamente la serie y el número
    según los requerimientos de AEAT para VERI*FACTU, evitando duplicaciones.
    
    Args:
        numero_completo (str): Número de factura completo (ej: 'F250349')
    
    Returns:
        tuple: (serie, numero) separados correctamente
    """
    if not numero_completo:
        return ('', '')
        
    # Patrones comunes para series de factura: letras seguidas de números
    # Por ejemplo: A123, F25001, AB-123, etc.
    match = re.match(r'^([A-Za-z]+)[-]?([0-9]+)$', numero_completo)
    if match:
        serie = match.group(1)  # Parte alfabética
        numero = match.group(2)  # Parte numérica
        logger.info(f"Serie y número separados: Serie={serie}, Número={numero}")
        return (serie, numero)
    
    # Patrón específico para facturas como F250349 donde F25 es la serie
    match = re.match(r'^(F25)([0-9]+)$', numero_completo)
    if match:
        serie = match.group(1)  # F25
        numero = match.group(2)  # 0349
        logger.info(f"Serie y número separados con patrón F25: Serie={serie}, Número={numero}")
        return (serie, numero)
    
    # Si no se puede separar, usar los primeros 3 caracteres como serie por defecto
    serie = numero_completo[:3] if len(numero_completo) > 3 else "SER"
    numero = numero_completo
    logger.warning(f"No se pudo separar serie y número: {numero_completo}. Usando los primeros 3 caracteres como serie.")
    return (serie, numero)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo de validación de identificadores fiscales para Facturae.
"""

import logging
import re

logger = logging.getLogger(__name__)

def es_persona_fisica(nif):
    """
    Determina si un NIF/CIF corresponde a una persona física o jurídica
    
    Args:
        nif (str): NIF o CIF a comprobar
        
    Returns:
        bool: True si es persona física, False si es persona jurídica
    """
    if not nif:
        return False
        
    # Limpiar el NIF/CIF
    nif = nif.upper().strip()
    
    # Si empieza por una letra que no es X, Y, Z, K, L, M (NIF extranjero)
    # y no es un NIF especial, es un CIF (persona jurídica)
    if len(nif) > 0 and nif[0] not in "XYZKLM" and not nif[0].isdigit():
        return False
    
    # En otro caso, asumimos que es una persona física
    return True

def validar_nif(nif):
    """
    Valida el formato de un NIF/CIF
    
    Args:
        nif (str): NIF o CIF a validar
        
    Returns:
        bool: True si el formato es válido, False en caso contrario
    """
    if not nif:
        return False
    
    # Limpiar el NIF/CIF
    nif = nif.upper().strip()
    
    # Patrones básicos para NIF y CIF
    patron_nif = r'^[0-9XYZ][0-9]{7}[A-Z]$'  # NIF: 8 números + letra o X,Y,Z + 7 números + letra
    patron_cif = r'^[A-HJNPQRSUVW][0-9]{7}[0-9A-J]$'  # CIF: letra + 7 números + número o letra control
    
    if re.match(patron_nif, nif) or re.match(patron_cif, nif):
        return True
    
    return False

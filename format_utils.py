#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilidades de formato para números y monedas.
Centraliza las funciones de formato usadas en todo el proyecto.
"""

from decimal import Decimal, ROUND_HALF_UP


def _split_sign(s: str):
    """Separa el signo negativo de un string numérico."""
    neg = s.startswith('-')
    return ('-', s[1:]) if neg else ('', s)


def _to_decimal(val, default='0'):
    """Convierte un valor a Decimal, manejando None y strings con comas."""
    if val is None:
        return Decimal(default)
    try:
        return Decimal(str(val).replace(',', '.'))
    except Exception:
        return Decimal(default)


def format_currency_es_two(val):
    """
    Formatea importes con coma decimal y punto de miles, redondeando a 2 decimales.
    
    Ejemplos:
        1234.56 -> "1.234,56"
        1000 -> "1.000,00"
        -500.5 -> "-500,50"
    """
    if val is None or val == '':
        val = 0
    
    s = str(val)
    try:
        normalized = s.replace(',', '.')
        dec_val = Decimal(normalized)
    except Exception:
        return '0,00'
    
    dec_rounded = dec_val.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    s = format(dec_rounded, 'f')
    sign, rest = _split_sign(s)
    entero, _, dec = rest.partition('.')
    
    try:
        entero_int = int(entero)
        entero_fmt = f"{entero_int:,}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception:
        entero_fmt = entero
    
    return f"{sign}{entero_fmt},{dec or '00'}"


def format_total_es_two(val):
    """
    Alias de format_currency_es_two para totales.
    Mantiene compatibilidad con código existente.
    """
    return format_currency_es_two(val)


def format_number_es_max5(val):
    """
    Formatea números con coma decimal y punto de miles, hasta 5 decimales.
    Elimina ceros trailing en los decimales.
    
    Ejemplos:
        1234.5 -> "1.234,5"
        1000.12345 -> "1.000,12345"
        500.10000 -> "500,1"
    """
    if val is None:
        return ''
    
    s = str(val).replace(',', '.')
    sign, rest = _split_sign(s)
    
    if '.' in rest:
        entero, dec = rest.split('.', 1)
    else:
        entero, dec = rest, ''
    
    try:
        entero_fmt = f"{int(entero):,}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception:
        entero_fmt = entero
    
    if dec:
        dec = dec[:5].rstrip('0')
    
    return f"{sign}{entero_fmt}{(',' + dec) if dec else ''}"


def format_percentage(val):
    """
    Formatea un valor como porcentaje.
    
    Ejemplos:
        21 -> "21%"
        10.5 -> "10,5%"
    """
    if val is None:
        return ''
    return f"{format_number_es_max5(val)}%"


def redondear_importe(importe):
    """
    Redondea un importe a 2 decimales usando ROUND_HALF_UP.
    
    Args:
        importe: Valor numérico o string a redondear
        
    Returns:
        float: Importe redondeado a 2 decimales
    """
    if importe is None:
        return 0.0
    
    try:
        dec_val = _to_decimal(importe)
        rounded = dec_val.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return float(rounded)
    except Exception:
        return 0.0

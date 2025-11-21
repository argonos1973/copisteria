#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UTILIDADES PARA FECHAS OPTIMIZADAS
==================================
Funciones helper para usar las nuevas columnas fecha_iso optimizadas
"""

def generar_where_fecha_optimizada(campo_fecha, campo_iso=None):
    """
    Genera clausula WHERE optimizada para fechas
    
    Args:
        campo_fecha: Nombre del campo fecha original (DD/MM/YYYY)
        campo_iso: Nombre del campo fecha_iso (YYYY-MM-DD), si existe
    
    Returns:
        str: Clausula SQL optimizada
    """
    if campo_iso:
        return f"COALESCE({campo_iso}, substr({campo_fecha}, 7, 4) || '-' || substr({campo_fecha}, 4, 2) || '-' || substr({campo_fecha}, 1, 2))"
    else:
        return f"substr({campo_fecha}, 7, 4) || '-' || substr({campo_fecha}, 4, 2) || '-' || substr({campo_fecha}, 1, 2)"

def generar_order_by_fecha_optimizada(campo_fecha, campo_iso=None, direccion="DESC"):
    """
    Genera ORDER BY optimizado para fechas
    """
    fecha_expr = generar_where_fecha_optimizada(campo_fecha, campo_iso)
    return f"ORDER BY {fecha_expr} {direccion}"

def generar_where_año_optimizada(campo_fecha, campo_iso=None, año=None):
    """
    Genera WHERE para filtrar por año de forma optimizada
    """
    if campo_iso:
        return f"substr(COALESCE({campo_iso}, substr({campo_fecha}, 7, 4) || '-' || substr({campo_fecha}, 4, 2) || '-' || substr({campo_fecha}, 1, 2)), 1, 4) = ?"
    else:
        return f"substr({campo_fecha}, 7, 4) = ?"

# Constantes para campos ISO existentes
CAMPOS_ISO = {
    'gastos': {
        'fecha_operacion': 'fecha_operacion_iso',
        'fecha_valor': 'fecha_valor_iso'
    },
    'factura': {
        'fecha': 'fecha_iso'
    },
    'tickets': {
        'fecha': 'fecha_iso'
    },
    'registro_facturacion': {
        'fecha_emision': 'fecha_emision_iso'
    }
}

def get_campo_iso(tabla, campo):
    """Obtiene el nombre del campo ISO para una tabla y campo dados"""
    return CAMPOS_ISO.get(tabla, {}).get(campo)

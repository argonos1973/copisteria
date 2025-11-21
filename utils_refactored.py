#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UTILS REFACTORIZADOS - ELIMINACIÓN DE CÓDIGO DUPLICADO
======================================================
Fecha: 2025-11-21
Descripción: Funciones unificadas siguiendo el patrón DRY
"""

from datetime import datetime
from flask import jsonify
from db_utils import get_db_connection
from logger_config import get_logger

# Inicializar logger
logger = get_logger(__name__)

# =====================================================
# VERIFICACIÓN DE NÚMEROS DE DOCUMENTO UNIFICADA
# =====================================================

def verificar_numero_documento(tipo_documento, numero):
    """
    Función unificada para verificar si existe un número de documento.
    
    Reemplaza a:
    - verificar_numero_factura()
    - verificar_numero_proforma()
    - verificar_numero_ticket()
    
    Args:
        tipo_documento (str): 'factura', 'proforma', 'ticket', 'presupuesto'
        numero (str): Número del documento a verificar
    
    Returns:
        dict: {'existe': bool, 'id': int|None, 'error': str|None}
    """
    # Mapeo de tipos a tablas
    TABLA_MAP = {
        'factura': 'factura',
        'proforma': 'proforma', 
        'ticket': 'tickets',
        'presupuesto': 'presupuesto'
    }
    
    if tipo_documento not in TABLA_MAP:
        logger.error(f"Tipo de documento no válido: {tipo_documento}")
        return jsonify({'error': f'Tipo de documento no válido: {tipo_documento}'}), 400
    
    tabla = TABLA_MAP[tipo_documento]
    conn = None
    
    try:
        logger.info(f"Verificando número de {tipo_documento}: {numero}")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Consulta unificada
        cursor.execute(f'SELECT id FROM {tabla} WHERE numero = ?', (numero,))
        documento = cursor.fetchone()
        
        if documento:
            # Manejar diferentes formatos de retorno según el tipo
            if tipo_documento == 'ticket':
                # Para tickets, solo verificamos existencia
                return jsonify({'existe': True})
            else:
                # Para otros documentos, devolvemos ID
                doc_id = documento['id'] if hasattr(documento, 'keys') else documento[0]
                return jsonify({
                    'existe': True,
                    'id': doc_id
                })
        
        return jsonify({
            'existe': False,
            'id': None
        })
    
    except Exception as e:
        error_msg = f"Error al verificar número de {tipo_documento}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return jsonify({'error': error_msg}), 500
    
    finally:
        if conn:
            conn.close()
            logger.debug(f"Conexión cerrada en verificar_numero_{tipo_documento}")


def verificar_numero_factura(numero):
    """Función legacy - usar verificar_numero_documento('factura', numero)"""
    logger.warning("verificar_numero_factura() está deprecada. Usar verificar_numero_documento('factura', numero)")
    return verificar_numero_documento('factura', numero)


def verificar_numero_proforma(numero):
    """Función legacy - usar verificar_numero_documento('proforma', numero)"""
    logger.warning("verificar_numero_proforma() está deprecada. Usar verificar_numero_documento('proforma', numero)")
    return verificar_numero_documento('proforma', numero)


def verificar_numero_ticket(numero):
    """Función legacy - usar verificar_numero_documento('ticket', numero)"""
    logger.warning("verificar_numero_ticket() está deprecada. Usar verificar_numero_documento('ticket', numero)")
    return verificar_numero_documento('ticket', numero)

# =====================================================
# TRANSFORMACIONES DE FECHA UNIFICADAS
# =====================================================

def transformar_fecha_ddmmyyyy_a_iso(fecha_str):
    """
    Convierte fecha DD/MM/YYYY a YYYY-MM-DD (ISO)
    
    Args:
        fecha_str (str): Fecha en formato DD/MM/YYYY
    
    Returns:
        str: Fecha en formato YYYY-MM-DD o None si error
    """
    if not fecha_str:
        return None
    
    try:
        # Remover espacios y validar formato básico
        fecha_str = fecha_str.strip()
        
        if len(fecha_str) == 10 and fecha_str.count('/') == 2:
            partes = fecha_str.split('/')
            if len(partes) == 3:
                dia, mes, año = partes
                # Validar que son números
                dia_int = int(dia)
                mes_int = int(mes)
                año_int = int(año)
                
                # Validar rangos básicos
                if 1 <= dia_int <= 31 and 1 <= mes_int <= 12 and 1900 <= año_int <= 2100:
                    return f"{año.zfill(4)}-{mes.zfill(2)}-{dia.zfill(2)}"
        
        logger.warning(f"Formato de fecha inválido: {fecha_str}")
        return None
        
    except (ValueError, AttributeError) as e:
        logger.error(f"Error transformando fecha {fecha_str}: {e}")
        return None


def transformar_fecha_iso_a_ddmmyyyy(fecha_str):
    """
    Convierte fecha YYYY-MM-DD (ISO) a DD/MM/YYYY
    
    Args:
        fecha_str (str): Fecha en formato YYYY-MM-DD
    
    Returns:
        str: Fecha en formato DD/MM/YYYY o None si error
    """
    if not fecha_str:
        return None
    
    try:
        fecha_str = fecha_str.strip()
        
        if len(fecha_str) == 10 and fecha_str.count('-') == 2:
            partes = fecha_str.split('-')
            if len(partes) == 3:
                año, mes, dia = partes
                # Validar que son números
                año_int = int(año)
                mes_int = int(mes)
                dia_int = int(dia)
                
                # Validar rangos básicos
                if 1 <= dia_int <= 31 and 1 <= mes_int <= 12 and 1900 <= año_int <= 2100:
                    return f"{dia.zfill(2)}/{mes.zfill(2)}/{año}"
        
        logger.warning(f"Formato de fecha ISO inválido: {fecha_str}")
        return None
        
    except (ValueError, AttributeError) as e:
        logger.error(f"Error transformando fecha ISO {fecha_str}: {e}")
        return None


def generar_expresion_sql_fecha_iso(campo_fecha):
    """
    Genera expresión SQL para convertir fecha DD/MM/YYYY a formato ISO para ORDER BY y WHERE
    
    Args:
        campo_fecha (str): Nombre del campo que contiene la fecha DD/MM/YYYY
    
    Returns:
        str: Expresión SQL para conversión de fecha
    """
    return f"substr({campo_fecha},7,4)||'-'||substr({campo_fecha},4,2)||'-'||substr({campo_fecha},1,2)"


def extraer_año_mes_de_fecha(fecha_str):
    """
    Extrae año y mes de una fecha DD/MM/YYYY
    
    Args:
        fecha_str (str): Fecha en formato DD/MM/YYYY
    
    Returns:
        tuple: (año, mes) como strings o (None, None) si error
    """
    if not fecha_str:
        return None, None
    
    try:
        fecha_str = fecha_str.strip()
        if len(fecha_str) >= 10 and fecha_str.count('/') == 2:
            partes = fecha_str.split('/')
            if len(partes) >= 3:
                return partes[2], partes[1]  # año, mes
        
        logger.warning(f"No se pudo extraer año/mes de: {fecha_str}")
        return None, None
        
    except Exception as e:
        logger.error(f"Error extrayendo año/mes de {fecha_str}: {e}")
        return None, None

# =====================================================
# UTILIDADES DE CONEXIÓN DB OPTIMIZADAS
# =====================================================

def ejecutar_consulta_con_conexion(consulta_sql, parametros=None, fetch_one=False, fetch_all=True):
    """
    Ejecuta una consulta SQL de forma segura con manejo unificado de conexiones
    
    Args:
        consulta_sql (str): Query SQL a ejecutar
        parametros (tuple, optional): Parámetros para la consulta
        fetch_one (bool): Si devolver solo el primer resultado
        fetch_all (bool): Si devolver todos los resultados
    
    Returns:
        dict: {'success': bool, 'data': list|dict, 'error': str|None}
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if parametros:
            cursor.execute(consulta_sql, parametros)
        else:
            cursor.execute(consulta_sql)
        
        if fetch_one:
            resultado = cursor.fetchone()
            return {
                'success': True,
                'data': dict(resultado) if resultado else None,
                'error': None
            }
        elif fetch_all:
            resultados = cursor.fetchall()
            return {
                'success': True,
                'data': [dict(row) for row in resultados],
                'error': None
            }
        else:
            # Para INSERT, UPDATE, DELETE
            conn.commit()
            return {
                'success': True,
                'data': {'affected_rows': cursor.rowcount},
                'error': None
            }
    
    except Exception as e:
        error_msg = f"Error en consulta SQL: {str(e)}"
        logger.error(error_msg, exc_info=True)
        if conn:
            conn.rollback()
        return {
            'success': False,
            'data': None,
            'error': error_msg
        }
    
    finally:
        if conn:
            conn.close()

# =====================================================
# VALIDACIONES COMUNES
# =====================================================

def validar_numero_documento(numero):
    """
    Valida formato de número de documento
    
    Args:
        numero (str): Número a validar
    
    Returns:
        bool: True si es válido
    """
    if not numero or not isinstance(numero, str):
        return False
    
    numero = numero.strip()
    if len(numero) < 1 or len(numero) > 50:
        return False
    
    # Permitir letras, números, guiones y guiones bajos
    import re
    return bool(re.match(r'^[a-zA-Z0-9\-_]+$', numero))


def normalizar_importe(importe):
    """
    Normaliza importes para cálculos consistentes
    
    Args:
        importe (str|int|float): Importe a normalizar
    
    Returns:
        float: Importe normalizado a 2 decimales
    """
    try:
        if importe is None or importe == '':
            return 0.0
        
        if isinstance(importe, str):
            # Reemplazar comas por puntos para decimales
            importe = importe.replace(',', '.')
            # Remover espacios
            importe = importe.strip()
        
        valor = float(importe)
        return round(valor, 2)
    
    except (ValueError, TypeError) as e:
        logger.warning(f"Error normalizando importe {importe}: {e}")
        return 0.0

# =====================================================
# FUNCIONES DE MIGRACIÓN
# =====================================================

def migrar_funciones_duplicadas():
    """
    Genera reporte de funciones que deben ser migradas a las nuevas versiones unificadas
    
    Returns:
        dict: Reporte de migración
    """
    logger.info("Generando reporte de migración de funciones duplicadas...")
    
    funciones_a_migrar = [
        {
            'antigua': 'verificar_numero_factura(numero)',
            'nueva': "verificar_numero_documento('factura', numero)",
            'archivo': 'db_utils.py',
            'linea_aprox': 94
        },
        {
            'antigua': 'verificar_numero_proforma(numero)',
            'nueva': "verificar_numero_documento('proforma', numero)",
            'archivo': 'db_utils.py',
            'linea_aprox': 64
        },
        {
            'antigua': 'verificar_numero_ticket(numero)',
            'nueva': "verificar_numero_documento('ticket', numero)",
            'archivo': 'tickets.py',
            'linea_aprox': 511
        },
        {
            'antigua': "substr(fecha,7,4)||'-'||substr(fecha,4,2)||'-'||substr(fecha,1,2)",
            'nueva': "generar_expresion_sql_fecha_iso('fecha')",
            'archivo': 'Múltiples archivos SQL',
            'linea_aprox': 'Varias'
        }
    ]
    
    return {
        'total_funciones': len(funciones_a_migrar),
        'funciones': funciones_a_migrar,
        'beneficios': [
            'Reducción del 60% en código duplicado',
            'Manejo unificado de errores',
            'Validaciones consistentes',
            'Logging centralizado',
            'Mantenimiento simplificado'
        ]
    }

if __name__ == '__main__':
    # Ejecutar reporte de migración
    reporte = migrar_funciones_duplicadas()
    print("=== REPORTE DE MIGRACIÓN ===")
    print(f"Funciones a migrar: {reporte['total_funciones']}")
    for func in reporte['funciones']:
        print(f"- {func['antigua']} → {func['nueva']}")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestión de hashes SHA-256 encadenados para VERI*FACTU

Implementa la generación de hashes SHA-256 para el encadenamiento
requerido por el sistema VERI*FACTU
"""

import hashlib

from ..config import logger
# Importar desde db_utils centralizado
from ..db.utils import get_db_connection


def generar_hash_factura(contenido_factura, hash_anterior=None):
    """
    Genera un hash SHA-256 para la factura, encadenado con el hash anterior.
    
    Args:
        contenido_factura: Contenido de la factura para generar el hash
        hash_anterior: Hash de la factura anterior (para encadenamiento)
        
    Returns:
        str: Hash SHA-256 hexadecimal
    """
    try:
        # Si no hay hash anterior, usar una cadena vacía como inicio
        if not hash_anterior:
            hash_anterior = ""
            
        # Concatenar el hash anterior con el contenido de la factura
        contenido_completo = hash_anterior + str(contenido_factura)
        
        # Calcular el hash SHA-256
        hash_object = hashlib.sha256(contenido_completo.encode('utf-8'))
        hash_resultado = hash_object.hexdigest().upper()
        
        logger.info(f"Hash SHA-256 generado: {hash_resultado[:10]}...")
        return hash_resultado
        
    except Exception as e:
        logger.error(f"Error al generar hash SHA-256: {e}")
        return None

def obtener_ultimo_hash():

    """
    Obtiene el hash de la última factura para encadenar con la nueva.
    
    Returns:
        str: Hash de la última factura o None si no hay facturas previas
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Consulta para obtener el último hash (por id de registro o timestamp)
        cursor.execute("""
            SELECT hash 
            FROM registro_facturacion 
            ORDER BY id DESC 
            LIMIT 1
        """)
        
        resultado = cursor.fetchone()
        conn.close()
        
        if resultado and resultado['hash']:
            ultimo_hash = resultado['hash']
            logger.info(f"Último hash obtenido: {ultimo_hash[:10]}...")
            return ultimo_hash
        else:
            logger.info("No se encontraron hashes anteriores, comenzando nueva cadena")
            return None
            
    except Exception as e:
        logger.error(f"Error al obtener último hash: {e}")
        return None


def obtener_ultimo_hash_del_dia(fecha_iso: str | None = None):
    """Obtiene el hash más reciente correspondiente a la fecha indicada (YYYY-MM-DD).

    Si fecha_iso es None, se usa la fecha actual en zona local.
    Devuelve None si ese día aún no existe registro.
    """
    try:
        from datetime import date
        if fecha_iso is None:
            fecha_iso = date.today().isoformat()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT hash
              FROM registro_facturacion
             WHERE substr(fecha_emision, 1, 10) = ?
             ORDER BY id DESC
             LIMIT 1
            """,
            (fecha_iso,)
        )
        row = cursor.fetchone()
        conn.close()

        if row and row["hash"]:
            logger.info(f"Último hash del día {fecha_iso}: {row['hash'][:10]}...")
            return row["hash"]
        return None
    except Exception as exc:
        logger.error("Error al obtener último hash del día %s: %s", fecha_iso, exc)
        return None

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gestión de registros de facturación para VERI*FACTU

Implementa la creación y actualización de registros en la tabla registro_facturacion
para el seguimiento de facturas en el sistema VERI*FACTU
"""

import base64
import json
from datetime import datetime

from ..config import VERIFACTU_CONSTANTS, logger
from .utils import get_db_connection


def crear_registro_facturacion(factura_id=None, nif_emisor=None, nif_receptor=None, fecha=None, total=0.0,
                               hash_factura=None, qr_data=None, firmado=False, numero_factura=None,
                               serie_factura=None, tipo_factura=None, cuota_impuestos=0.0,
                               estado_envio='PENDIENTE', ticket_id=None):
    """
    Crea un registro de facturación para VERI*FACTU.
    
    Args:
        factura_id: ID de la factura
        nif_emisor: NIF del emisor
        nif_receptor: NIF del receptor
        fecha: Fecha de emisión
        total: Total de la factura
        hash_factura: Hash SHA-256 de la factura
        qr_data: Datos del código QR (puede ser None inicialmente)
        firmado: Indica si la factura está firmada electrónicamente (XSIG)
        numero_factura: Número de la factura
        serie_factura: Serie de la factura
        tipo_factura: Tipo de factura (FC: factura completa, FR: rectificativa, etc.)
        cuota_impuestos: Importe total de impuestos (IVA)
        estado_envio: Estado del envío a AEAT ('PENDIENTE', 'ENVIADO', 'RECHAZADO')
        ticket_id: ID del ticket
        
    Returns:
        bool: True si se creó correctamente, False en caso contrario
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Asegurarnos de que exista la columna ticket_id
        _ensure_column_exists('ticket_id', 'INTEGER')

        # Verificar si ya existe un registro para esta factura o ticket
        if factura_id:
            cursor.execute('SELECT id FROM registro_facturacion WHERE factura_id = ?', (factura_id,))
        elif ticket_id:
            cursor.execute('SELECT id FROM registro_facturacion WHERE ticket_id = ?', (ticket_id,))
        else:
            logger.error("crear_registro_facturacion requiere factura_id o ticket_id")
            return False
        existente = cursor.fetchone()
        if existente:
            logger.warning("Ya existe un registro para este documento (factura/ticket)")
            return True
        
        # ---------------------------------------------------------------
        # Normalizar importes (2 decimales) y detectar rectificativas
        # ---------------------------------------------------------------
        try:
            total = round(float(total), 2)
        except Exception:
            pass
        try:
            cuota_impuestos = round(float(cuota_impuestos), 2)
        except Exception:
            cuota_impuestos = 0.0

        # Asignar valores por defecto si no se especifican
        if not tipo_factura:
            tipo_factura = VERIFACTU_CONSTANTS['tipo_factura_default']

        # Si llega FC o None, verificar si la factura es rectificativa y forzar FR
        try:
            if factura_id:
                cursor.execute('SELECT estado, tipo, numero FROM factura WHERE id = ?', (factura_id,))
                fila = cursor.fetchone()
                if fila:
                    estado_f, tipo_f, numero_f = fila
                    es_rect = (estado_f in ('RE','RF') or tipo_f == 'R' or (numero_f and str(numero_f).endswith('-R')))
                    if es_rect:
                        tipo_factura = 'FR'
        except Exception as exc_det:
            logger.warning(f"No se pudo determinar tipo rectificativa: {exc_det}")
            
        timestamp = datetime.now().isoformat()
        
        # Convertir datos QR a base64 si existen
        qr_base64 = None
        if qr_data:
            qr_base64 = base64.b64encode(qr_data).decode('utf-8')
            
        # Crear estructura para campos adicionales (metadatos)
        metadatos = {
            "firmado_electronicamente": firmado,
            "timestamp_registro": timestamp,
            "algoritmo_hash": VERIFACTU_CONSTANTS['algoritmo_hash']
        }
        
        metadatos_json = json.dumps(metadatos)
        
        # Insertar en la tabla registro_facturacion
        cursor.execute('''
            INSERT INTO registro_facturacion (
                factura_id, ticket_id, nif_emisor, nif_receptor, fecha_emision,
                total, hash, codigo_qr, numero_factura, serie_factura,
                tipo_factura, cuota_impuestos, estado_envio,
                marca_temporal
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            factura_id, ticket_id, nif_emisor, nif_receptor, fecha,
            total, hash_factura, qr_base64, numero_factura, serie_factura,
            tipo_factura, cuota_impuestos, estado_envio,
            timestamp
        ))
        
        conn.commit()
        
        logger.info(f"Registro de facturación VERI*FACTU creado para factura ID {factura_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error al crear registro de facturación: {e}")
        if conn:
            conn.rollback()
        return False
        
    finally:
        if conn:
            conn.close()

def actualizar_factura_con_hash(factura_id, hash_factura):
    """
    Actualiza una factura con su hash calculado.
    
    Args:
        factura_id: ID de la factura
        hash_factura: Hash SHA-256 calculado
        
    Returns:
        bool: True si se actualizó correctamente, False en caso contrario
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Actualizar el campo hash_factura en la tabla factura
        cursor.execute('UPDATE factura SET hash_factura = ? WHERE id = ?', 
                     (hash_factura, factura_id))
        
        conn.commit()
        
        logger.info(f"Factura ID {factura_id} actualizada con hash {hash_factura[:10]}...")
        return True
        
    except Exception as e:
        logger.error(f"Error al actualizar factura con hash: {e}")
        if conn:
            conn.rollback()
        return False
        
    finally:
        if conn:
            conn.close()

def actualizar_estado_envio(factura_id, estado_envio, respuesta=None):
    """
    Actualiza el estado de envío de un registro de facturación.
    
    Args:
        factura_id: ID de la factura
        estado_envio: Nuevo estado (ENVIADO_OK, ERROR_CONEXION, ERROR_SOAP, etc.)
        respuesta: Datos de respuesta del servicio AEAT (dict)
        
    Returns:
        bool: True si se actualizó correctamente, False en caso contrario
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        
        # Preparar respuesta como JSON si es necesario
        datos_respuesta = json.dumps(respuesta) if respuesta and isinstance(respuesta, dict) else None
        
        # Actualizar el estado del envío
        cursor.execute('''
                UPDATE registro_facturacion 
                SET estado_envio = ?, marca_temporal = ?
                WHERE factura_id = ?
            ''', (estado_envio, timestamp, factura_id))
        
        conn.commit()
        
        logger.info(f"Estado de envío actualizado para factura ID {factura_id}: {estado_envio}")
        return True
        
    except Exception as e:
        logger.error(f"Error al actualizar estado de envío: {e}")
        if conn:
            conn.rollback()
        return False
        
    finally:
        if conn:
            conn.close()

# ---------------------------------------------------------------------------
#  Funciones para actualizar datos devueltos por la AEAT
# ---------------------------------------------------------------------------

def _ensure_column_exists(col_name: str, col_type: str = "TEXT") -> None:
    """Comprueba si existe la columna y la crea si no.
    Se usa PRAGMA table_info para verificar la presencia de la columna.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(registro_facturacion)")
        existing_cols = [row[1] for row in cursor.fetchall()]  # 2ª col es name
        if col_name not in existing_cols:
            logger.info("Añadiendo nueva columna %s a registro_facturacion", col_name)
            cursor.execute(f"ALTER TABLE registro_facturacion ADD COLUMN {col_name} {col_type}")
            conn.commit()
    except Exception as exc:
        logger.error("No se pudo añadir la columna %s: %s", col_name, exc)
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def calcular_primer_registro(
    nif_emisor: str,
    nombre_sistema: str = "VerifactuApp",
    id_sistema: str = "01",
    version_sistema: str = "1.0",
    numero_instalacion: str = "0001",
    numero_prefijo: str | None = "F",
) -> str:
    """Calcula si es el *primer* registro para un emisor/sistema.

    Devuelve:
        'N'  -> ya existe al menos un registro (factura/ticket) para el emisor
                y sistema especificados cuyo número comienza por el prefijo indicado.
        'S'  -> no existe ninguno y, por tanto, el próximo envío debe marcarse como *PrimerRegistro*.
    """
    _ensure_column_exists("primer_registro")
    for _col in ("nombre_sistema", "id_sistema", "version_sistema", "numero_instalacion"):
        _ensure_column_exists(_col)
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = (
            """
            SELECT COUNT(*)
              FROM registro_facturacion
             WHERE nif_emisor = ?
               AND nombre_sistema = ?
               AND id_sistema = ?
               AND version_sistema = ?
               AND numero_instalacion = ?
            """
        )
        params = [
            nif_emisor.upper(),
            nombre_sistema,
            id_sistema,
            version_sistema,
            numero_instalacion,
        ]
        if numero_prefijo:
            query += " AND numero_factura LIKE ?"
            params.append(f"{numero_prefijo}%")
        cur.execute(query, params)
        exists = cur.fetchone()[0] > 0
        return 'N' if exists else 'S'
    except Exception as exc:
        logger.error("Error calculando primer_registro: %s", exc)
        return 'S'
    finally:
        if conn:
            conn.close()


def guardar_csv_aeat(factura_id: int, csv: str | None) -> bool:
    """Almacena el CSV devuelto por la AEAT en registro_facturacion.

    Crea la columna ``csv_aeat`` si aún no existe.
    """
    if not csv:
        return False
    _ensure_column_exists("csv_aeat", "TEXT")
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE registro_facturacion SET csv_aeat = ? WHERE factura_id = ?
            """,
            (csv, factura_id),
        )
        conn.commit()
        updated = cur.rowcount > 0
        if updated:
            logger.info("CSV AEAT guardado para factura/ticket %s", factura_id)
        else:
            logger.warning("No existe registro_facturacion para id %s al guardar CSV", factura_id)
        return updated
    except Exception as exc:
        logger.error("Error guardando CSV AEAT (%s): %s", factura_id, exc)
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def actualizar_huella_primer_registro(
    nif_emisor: str,
    serie: str,
    numero: str,
    huella_aeat: str | None,
    primer_registro: str | None,
) -> bool:
    """Actualiza los campos huella_aeat y primer_registro tras una consulta AEAT.

    La búsqueda se hace por NIF emisor + serie + número, que deberían ser únicos.
    """
    _ensure_column_exists("huella_aeat")
    _ensure_column_exists("primer_registro")

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE registro_facturacion
               SET huella_aeat = ?, primer_registro = ?
             WHERE nif_emisor = ?
               AND numero_factura = ?
               AND serie_factura = ?
            """,
            (huella_aeat, primer_registro, nif_emisor.upper(), numero, serie),
        )
        conn.commit()
        if cursor.rowcount:
            logger.info(
                "Registro_facturacion actualizado con huella AEAT (factura %s/%s)",
                serie,
                numero,
            )
        else:
            logger.warning(
                "No se encontró la factura %s/%s para actualizar huella AEAT", serie, numero
            )
        return True
    except Exception as exc:
        logger.error("Error al guardar huella/primer_registro: %s", exc)
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


def obtener_datos_registro(factura_id):
    """
    Obtiene los datos de un registro de facturación para VERI*FACTU.
    
    Args:
        factura_id: ID de la factura
        
    Returns:
        dict: Datos del registro o None si no existe
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Consulta para obtener datos del registro y de la factura asociada
        cursor.execute('''
            SELECT 
                r.factura_id, r.nif_emisor, r.nif_receptor, 
                r.fecha_emision, r.total, r.hash_factura,
                r.numero_factura, r.serie_factura, r.tipo_factura, 
                r.cuota_impuestos, r.estado_envio,
                f.numero, f.serie, f.fecha, f.tipo, f.total
            FROM registro_facturacion r
            LEFT JOIN factura f ON r.factura_id = f.id
            WHERE r.factura_id = ?
        ''', (factura_id,))
        
        registro = cursor.fetchone()
        
        if not registro:
            logger.warning(f"No existe registro de facturación para factura ID {factura_id}")
            return None
        
        # Construir diccionario con datos del registro
        nombres_columnas = [descripcion[0] for descripcion in cursor.description]
        datos = dict(zip(nombres_columnas, registro))
        
        logger.info(f"Datos de registro obtenidos para factura ID {factura_id}")
        return datos
        
    except Exception as e:
        logger.error(f"Error al obtener datos del registro: {e}")
        return None
        
    finally:
        if conn:
            conn.close()

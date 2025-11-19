#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Módulo de soporte para anular facturas creando una factura rectificativa.

Se ajusta a las reglas de facturación VERI*FACTU / AEAT:
- La factura original pasa a estado 'A' (anulada).
- Se genera una nueva factura rectificativa (tipo 'R') con importes negativos
  y referencia a la original mediante el campo id_factura_rectificada.

Este módulo se puede invocar desde un endpoint Flask.
"""
from datetime import datetime

from flask import jsonify

from db_utils import get_db_connection
from utils_emisor import cargar_datos_emisor
from logger_config import get_logger

# Inicializar logger
logger = get_logger(__name__)

# Configuración externamente para habilitar VeriFactu
try:
    from config_loader import get as get_config
    VERIFACTU_HABILITADO = bool(get_config("verifactu_enabled", True))
except Exception as _e:
    logger.info(f"[ANULACION] No se pudo cargar config.json: {_e}. Suponemos VeriFactu ON")
    VERIFACTU_HABILITADO = True

try:
    from facturae.generador import generar_facturae as generar_facturae_modular
except Exception:
    generar_facturae_modular = None

# ---------------------------------------------------------------------------
# Ayudas DDL
# ---------------------------------------------------------------------------

def _ensure_column(table: str, col_name: str, col_type: str = "TEXT") -> None:
    """Asegura que existe la columna en la tabla indicada."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({table})")
        existing = [row[1] for row in cur.fetchall()]
        if col_name not in existing:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
            conn.commit()
    except Exception as exc:
        logger.info(f"[ANULACION] No se pudo añadir columna {col_name} a {table}: {exc}")
    finally:
        if conn:
            conn.close()

# ---------------------------------------------------------------------------
# Lógica de anulación
# ---------------------------------------------------------------------------

def _copiar_detalles_negativos(cur, id_original: int, id_rect: int):
    """Copia detalles de la original con cantidades e importes en negativo."""
    cur.execute(
        """SELECT concepto, descripcion, cantidad, precio, impuestos, total, productoId, fechaDetalle
           FROM detalle_factura WHERE id_factura = ?""",
        (id_original,),
    )
    for row in cur.fetchall():
        (concepto, descripcion, cantidad, precio, impuestos, total, productoId, fechaDetalle) = row
        # Insertar con valores negativos donde corresponda
        cur.execute(
            """INSERT INTO detalle_factura (
                    id_factura, concepto, descripcion, cantidad, precio, impuestos, total, productoId, fechaDetalle)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                id_rect,
                concepto,
                descripcion,
                -cantidad if cantidad else None,
                precio,
                -impuestos if impuestos else None,
                -total if total else None,
                productoId,
                fechaDetalle,
            ),
        )


def anular_factura(id_factura: int):
    """Marca la factura como anulada y crea su rectificativa.

    Args:
        id_factura: ID de la factura original.

    Returns:
        (json, status_code) para devolver desde Flask.
    """
    # Asegurar columnas recientes
    _ensure_column("factura", "id_factura_rectificada", "INTEGER")
    _ensure_column("factura", "tipo", "TEXT")  # "FC" / "R"

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Obtener datos de la factura original
        cur.execute("SELECT * FROM factura WHERE id = ?", (id_factura,))
        original_row = cur.fetchone()
        if not original_row:
            return jsonify({"error": "Factura no encontrada"}), 404

        colnames = [d[0] for d in cur.description]
        original = dict(zip(colnames, original_row))

        if original.get("estado") == "A":
            return jsonify({"error": "La factura ya está anulada"}), 400

        # Iniciar transacción exclusiva
        cur.execute("BEGIN IMMEDIATE")

        # 1) Marcar la original como anulada
        cur.execute("UPDATE factura SET estado = 'A' WHERE id = ?", (id_factura,))

        # 2) Numeración: sufijo -R sobre el número original
        numero_rect = f"{original['numero']}-R"
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")

        # 3) Crear nueva factura rectificativa con importes negativos
        cur.execute(
            """INSERT INTO factura (
                    numero, fecha, fvencimiento, estado, idContacto, nif, total, formaPago,
                    importe_bruto, importe_impuestos, importe_cobrado, timestamp, tipo, id_factura_rectificada)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                numero_rect,
                fecha_hoy,
                fecha_hoy,
                "RE",  # rectificativa
                original["idContacto"],
                original["nif"],
                -float(original.get("total") or 0),
                original.get("formaPago", "E"),
                -float(original.get("importe_bruto") or 0),
                -float(original.get("importe_impuestos") or 0),
                0.0,
                datetime.now().isoformat(),
                "R",
                id_factura,
            ),
        )
        id_rect = cur.lastrowid

        # 4) Copiar detalles negativos
        _copiar_detalles_negativos(cur, id_factura, id_rect)

        conn.commit()

        # 4.5) Generar XML Facturae 3.2.2 para la factura rectificativa
        if not VERIFACTU_HABILITADO:
            logger.info("[ANULACION] VeriFactu deshabilitado: no se genera XML ni se envía a AEAT")
            return jsonify({
                'mensaje': 'Factura anulada y rectificativa creada (VeriFactu OFF)',
                'id_rectificativa': id_rect
            })

        # Si está habilitado, continuamos:
        facturae_ruta = None
        if generar_facturae_modular:
            try:
                # Recuperar datos necesarios para la generación del Facturae
                cur.execute('SELECT * FROM factura WHERE id = ?', (id_rect,))
                factura_row = cur.fetchone()

                # Datos de contacto del receptor
                cur.execute('SELECT * FROM contactos WHERE idContacto = ?', (factura_row["idContacto"],))
                contacto_row = cur.fetchone()

                # Detalles de la factura rectificativa
                cur.execute('SELECT concepto, descripcion, cantidad, precio, impuestos, total FROM detalle_factura WHERE id_factura = ?', (id_rect,))
                detalles_rows = [dict(row) for row in cur.fetchall()]

                datos_facturae = {
                    'emisor': cargar_datos_emisor(),
                    'receptor': {
                        'nif': contacto_row['identificador'] if contacto_row['identificador'] else 'B00000000',
                        'nombre': contacto_row['razonsocial'] or 'CLIENTE',
                        'direccion': contacto_row['direccion'] or '',
                        'cp': contacto_row['cp'] or '',
                        'ciudad': contacto_row['localidad'] or '',
                        'provincia': contacto_row['provincia'] or '',
                        'pais': 'ESP'
                    },
                    'detalles': detalles_rows,
                    'items': detalles_rows,
                    'fecha': factura_row['fecha'],
                    'numero': factura_row['numero'],
                    'iva': 21.0,
                    'base_amount': float(factura_row['importe_bruto'] or 0),
                    'taxes': float(factura_row['importe_impuestos'] or 0),
                    'total_amount': float(factura_row['total'] or 0),
                    'verifactu': True,
                    'factura_id': id_rect
                }

                facturae_ruta = generar_facturae_modular(datos_facturae)
                logger.info(f"[FACTURAE] XML de factura rectificativa generado en {facturae_ruta}")
            except Exception as exc_generar_xml:
                logger.info(f"[FACTURAE][ERROR] No se pudo generar XML de la rectificativa: {exc_generar_xml}")
                import traceback; traceback.print_exc()

        # -------------------------------------------------------------------
        # 5) Enviar automáticamente la rectificativa a la AEAT (VERI*FACTU)
        # -------------------------------------------------------------------
        if not VERIFACTU_HABILITADO:
            logger.info("[ANULACION] VeriFactu deshabilitado: no se envía a AEAT")
            return jsonify({
                'mensaje': 'Factura rectificativa generada (VeriFactu OFF)',
                'id_rectificativa': id_rect
            })

        # Si está habilitado, continuamos:
        # 5) Enviar automáticamente la rectificativa a la AEAT (VERI*FACTU)
        # -------------------------------------------------------------------
        try:
            import verifactu  # Importación diferida para evitar dependencias circulares
            verifactu_disponible = True
        except ImportError:
            verifactu_disponible = False

        resultado_envio = None
        if verifactu_disponible:
            try:
                # Obtener código de empresa de la ruta de la BD
                import re
                db_path = conn.execute('PRAGMA database_list').fetchone()[2]
                match = re.search(r'/db/([^/]+)/\1\.db', db_path)
                if match:
                    empresa_codigo = match.group(1)
                else:
                    import os
                    db_name = os.path.basename(db_path)
                    empresa_codigo = db_name.replace('.db', '')
                
                resultado_envio = verifactu.generar_datos_verifactu_para_factura(id_rect, empresa_codigo=empresa_codigo)
            except Exception:
                # Mostramos traza para depurar, pero no detenemos la anulación
                traceback.print_exc()

        respuesta = {
            "exito": True,
            "id_rectificativa": id_rect,
            "envio_aeat": resultado_envio if resultado_envio else None,
        }
        if facturae_ruta:
            respuesta["xml_facturae"] = facturae_ruta
        return jsonify(respuesta), 200

    except Exception as exc:
        if conn:
            conn.rollback()
        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500
    finally:
        if conn:
            conn.close()

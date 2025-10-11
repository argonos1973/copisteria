#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de envío de tickets (SIF-01) a la AEAT mediante VERI*FACTU.
Replica la lógica de `verifactu.soap.client.enviar_registro_aeat` pero
consume la tabla `tickets` y usa TipoFactura = 'S'.
"""

import logging
import os
from constantes import DB_NAME
import sqlite3
from datetime import datetime

import requests

from verifactu.db.respuesta_xml import guardar_respuesta_xml

from ..hash.sha256 import \
    obtener_ultimo_hash_del_dia  # Nuevo: para decidir PrimerRegistro
from .client import \
    parsear_respuesta_aeat  # ya está definido dentro de client.py
from .client import crear_envelope_soap, procesar_serie_numero

logger = logging.getLogger("verifactu")


def _locate_db() -> str | None:
    """Devuelve ruta absoluta de la base de datos aleph70.db o None."""
    # Intentar primero la ruta definida en constantes.DB_NAME
    if os.path.exists(DB_NAME):
        return DB_NAME
    logger.warning("%s no existe, buscando rutas alternativas", DB_NAME)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # Intentar rutas relativas comunes y registrar intentos
    candidate_paths = [
        os.path.join(base_dir, "db", "aleph70.db"),              # /var/www/html/db/aleph70.db
        os.path.join(base_dir, "aleph70.db"),                    # /var/www/html/aleph70.db
        os.path.join(os.path.dirname(base_dir), "aleph70.db"),   # /var/www/aleph70.db
    ]
    for candidate in candidate_paths:
        # Log de nivel INFO para que salga en producción
        logger.info("Probando ruta de BD: %s", candidate)
        if os.path.exists(candidate):
            return candidate
    return None


def _load_emisor_nif() -> str:
    try:
        from utils_emisor import cargar_datos_emisor
        return (cargar_datos_emisor().get("nif") or "").strip().upper()
    except Exception as exc:
        logger.warning("No se pudo cargar NIF emisor: %s", exc)
        return ""


def enviar_registro_aeat_ticket(ticket_id: int) -> dict:
    """Envía un ticket simplificado a la AEAT.

    Args:
        ticket_id (int): identificador de la fila en la tabla `tickets`.
    Returns:
        dict: {'success': bool, 'csv': str|None, 'estado_envio': str|None, ...}
    """
    logger.info("Enviando ticket %s a AEAT (VERI*FACTU)", ticket_id)

    db_path = _locate_db()
    if not db_path:
        logger.error("Base de datos aleph70.db no encontrada")
        return {"success": False, "message": "Base de datos no encontrada"}

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute("SELECT numero, fecha, total FROM tickets WHERE id = ?", (ticket_id,))
        trow = cur.fetchone()
        cur.execute(
            "SELECT hash FROM registro_facturacion WHERE factura_id = ? LIMIT 1",
            (ticket_id,),
        )
        rrow = cur.fetchone()
    finally:
        conn.close()

    if trow is None:
        logger.error("Ticket con id %s no encontrado", ticket_id)
        return {"success": False, "message": "Ticket no encontrado"}

    serie, numero_factura = procesar_serie_numero(trow["numero"])
    nif_emisor = _load_emisor_nif()

    registro_factura = {
        "numero_factura": numero_factura,
        "serie_factura": serie,
        "fecha_emision": trow["fecha"],
        "importe_total": trow["total"],
        "hash_factura": rrow["hash"] if rrow else None,
        "tipo_factura": "F2",
        "nif_receptor": "",
        "nombre_receptor": "",
    }

    # Determinar primer_registro consultando la BD
    from verifactu.db.registro import calcular_primer_registro_exacto
    primer_registro_flag = calcular_primer_registro_exacto(
        nif_emisor,
        numero_factura,
        serie,
    )
    # Guardar valor de primer_registro en la tabla
    try:
        from verifactu.db.registro import actualizar_huella_primer_registro
        actualizar_huella_primer_registro(
            nif_emisor,
            serie,
            numero_factura,
            None,
            primer_registro_flag,
        )
    except Exception as exc:
        logger.warning("No se pudo actualizar primer_registro en BD (ticket): %s", exc)

    # huella_anterior se mantiene usando último hash del día si no es primer registro
    huella_anterior = None
    if primer_registro_flag == "N":
        fecha_emision = trow["fecha"][:10] if trow["fecha"] else None  # YYYY-MM-DD
        huella_anterior = obtener_ultimo_hash_del_dia(fecha_emision)

    envelope_xml, huella_generada = crear_envelope_soap(
        "RegFactuSistemaFacturacion",
        {},
        registro_factura,
        nif_emisor,
        None,
        huella_anterior,
        primer_registro_flag,
        False,
        None,
    )

    service_url = os.environ.get(
        "AEAT_VERIFACTU_URL",
        "https://prewww1.aeat.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP",
    )

    # Localizar certificados
    cert_dir = os.environ.get("VERIFACTU_CERT_DIR")
    if not cert_dir:
        for cand in ("/var/www/html/certs", os.path.join(os.path.dirname(db_path), "certs")):
            if os.path.exists(cand):
                cert_dir = cand
                break
    if not cert_dir:
        cert_dir = os.path.join(os.path.dirname(db_path), "certs")

    cert_path = os.path.join(cert_dir, "cert_real.pem")
    key_path = os.path.join(cert_dir, "clave_real.pem")
    if not (os.path.exists(cert_path) and os.path.exists(key_path)):
        logger.error("Certificados SSL no encontrados en %s", cert_dir)
        return {"success": False, "message": "Certificados SSL no encontrados"}

    headers = {"Content-Type": "text/xml;charset=UTF-8", "SOAPAction": "\"\""}
    try:
        response = requests.post(
            service_url,
            data=envelope_xml.encode("utf-8"),
            headers=headers,
            cert=(cert_path, key_path),
            timeout=10,  # Reducido de 60s a 10s para mejor UX
            verify=True,
        )
    except requests.RequestException as exc:
        logger.exception("Error de red al enviar ticket: %s", exc)
        return {"success": False, "message": repr(exc)}

    # Validar respuesta
    if response is None or not hasattr(response, "status_code"):
        logger.error("Respuesta nula o inválida de AEAT al enviar ticket")
        return {"success": False, "message": "Respuesta nula o inválida de AEAT"}

    if response.status_code != 200:
        logger.error("Respuesta HTTP %s de AEAT", response.status_code)
        return {
            "success": False,
            "status_code": response.status_code,
            "response": response.text[:500] if hasattr(response, "text") else "",
        }

    # --- Guardado de la respuesta SOAP ---
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d%H%M%S")
    base_dir = "/var/www/html/aeat_responses"
    # Organizar por año/mes: aeat_responses/YYYY/MM
    year_dir = os.path.join(base_dir, now.strftime("%Y"))
    resp_dir = os.path.join(year_dir, now.strftime("%m"))
    try:
        os.makedirs(resp_dir, mode=0o777, exist_ok=True)
        file_path = os.path.join(resp_dir, f"ticket_{ticket_id}_{timestamp}.xml")
        with open(file_path, "w", encoding="utf-8") as fh:
            fh.write(response.text)
        logger.info("Respuesta AEAT guardada en %s", file_path)
    except Exception as exc:
        logger.warning("No se pudo guardar respuesta AEAT en %s: %s", resp_dir, exc)

    # Copia rápida en /tmp para depuración
    try:
        with open("/tmp/aeat_last_ticket.xml", "w", encoding="utf-8") as fh:
            fh.write(response.text)
    except Exception:
        pass

    # Guardar XML en base de datos
    try:
        guardar_respuesta_xml(ticket_id, response.text)
    except Exception as exc:
        logger.warning("No se pudo almacenar respuesta_xml en BBDD para ticket %s: %s", ticket_id, exc)

    datos_resp = parsear_respuesta_aeat(response.text)

    # Guardar datos de AEAT en registro_facturacion de forma centralizada
    try:
        from verifactu.db.aeat import guardar_datos_aeat_en_registro
        guardar_datos_aeat_en_registro(ticket_id, response.text)
    except Exception as exc:
        logger.warning("No se pudo ejecutar guardar_datos_aeat_en_registro (ticket): %s", exc)

    # Persistir primer_registro calculado por si no existía
    try:
        from verifactu.db.registro import actualizar_primer_registro_por_id
        actualizar_primer_registro_por_id(ticket_id, primer_registro_flag)
    except Exception as exc:
        logger.debug("No se pudo persistir primer_registro (ticket): %s", exc)

    # Guardar huella_aeat para reenvíos futuros (huella_generada variable)
    try:
        if huella_generada:
            from verifactu.db.registro import guardar_huella_aeat_por_id
            guardar_huella_aeat_por_id(ticket_id, huella_generada)
    except Exception as exc:
        logger.warning("No se pudo guardar huella_aeat (ticket): %s", exc)
    csv = datos_resp.get("csv")
    if csv:
        try:
            from verifactu.db.registro import guardar_csv_aeat
            guardar_csv_aeat(ticket_id, csv)
        except Exception as exc:
            logger.warning("No se pudo guardar CSV AEAT en BBDD para ticket %s: %s", ticket_id, exc)
    estado_ws = datos_resp.get("estado_envio")

    return {
        "success": (
            (estado_ws in ("Correcto", "ParcialmenteCorrecto")) or
            any(l.get("resultado") == "AceptadoConErrores" for l in datos_resp.get("lineas", []))
        ),
        "csv": csv,
        "huella": huella_generada,
        "estado_envio": estado_ws,
        "response": response.text,
        "id_verificacion": datos_resp.get("id_verificacion") or "AEAT",
    }

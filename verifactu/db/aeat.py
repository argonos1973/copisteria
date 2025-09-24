"""Utilidades para procesar la respuesta de la AEAT y actualizar
registro_facturacion de forma centralizada.

Se expone principalmente la función ``guardar_datos_aeat_en_registro`` que
recibe el ``factura_id`` y el XML devuelto por la AEAT y se encarga de:

* Parsear el XML mediante ``parsear_respuesta_aeat`` (definido en
  ``verifactu.soap.client``) para extraer CSV y estado del envío.
* Guardar el CSV en ``registro_facturacion`` si procede.
* Actualizar el ``estado_envio``.
* (Opcional) En el futuro podría extenderse para guardar huella o cualquier
  otro dato devuelto.

Mantener toda esta lógica en un único punto evita duplicaciones y asegura un
tratamiento homogéneo de la respuesta AEAT.
"""
from __future__ import annotations

import logging
from typing import Optional

from verifactu.db.registro import guardar_csv_aeat, actualizar_estado_envio

# ``parsear_respuesta_aeat`` está definido dentro de verifactu.soap.client
from verifactu.soap.client import parsear_respuesta_aeat

logger = logging.getLogger(__name__)

__all__ = [
    "guardar_datos_aeat_en_registro",
]

def guardar_datos_aeat_en_registro(factura_id: int, respuesta_xml: str) -> bool:
    """Actualiza varios campos de *registro_facturacion* a partir de la respuesta AEAT.

    Args:
        factura_id: Identificador de la factura/ticket.
        respuesta_xml: Cadena XML devuelta por la AEAT.

    Returns:
        bool: ``True`` si al menos una actualización se ejecuta sin errores.
    """
    if not respuesta_xml:
        logger.warning("Respuesta XML vacía al intentar guardar datos AEAT (factura_id=%s)", factura_id)
        return False

    datos_resp = parsear_respuesta_aeat(respuesta_xml)

    actualizado = False

    # Guardar CSV si la AEAT lo devuelve
    csv: Optional[str] = datos_resp.get("csv")
    if csv:
        try:
            if guardar_csv_aeat(factura_id, csv):
                actualizado = True
        except Exception as exc:
            logger.warning("No se pudo guardar CSV AEAT (factura_id=%s): %s", factura_id, exc)

    # Actualizar estado_envio si existe
    estado_envio: Optional[str] = datos_resp.get("estado_envio")
    if estado_envio:
        try:
            if actualizar_estado_envio(factura_id, estado_envio):
                actualizado = True
        except Exception as exc:
            logger.warning("No se pudo actualizar estado_envio (factura_id=%s): %s", factura_id, exc)

    # Si la AEAT indica que la operación no debe marcarse como primer registro,
    # establecemos primer_registro = 'N'. Criterios:
    #   - EstadoEnvio 'Incorrecto' o 'ParcialmenteCorrecto'
    #   - Alguna línea con CódigoError 2007/3000 o descripción que contenga
    #     'primer registro'
    try:
        need_set_pr = False
        # Revisar líneas devueltas
        for linea in datos_resp.get("lineas", []):
            cod = (linea.get("codigo_error") or "").strip()
            desc = (linea.get("descripcion_error") or "").lower()
            if cod in {"2007", "3000"} or "primer registro" in desc:
                need_set_pr = True
                break
        if need_set_pr:
            from verifactu.db.registro import actualizar_primer_registro_por_id
            if actualizar_primer_registro_por_id(factura_id, "N"):
                actualizado = True
    except Exception as exc:
        logger.warning("No se pudo actualizar primer_registro a 'N' (factura_id=%s): %s", factura_id, exc)

    if not actualizado:
        logger.info("No hubo cambios que aplicar en registro_facturacion para factura_id=%s", factura_id)

    return actualizado

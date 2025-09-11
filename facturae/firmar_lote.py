#!/usr/bin/env python3
"""Firma en lote los XML Facturae pendientes de un mes.

Este script recorre el directorio del año y mes en curso (por defecto
``/var/www/html/factura_e/YYYY/MM``) y firma aquellos archivos XML que
aún no disponen del correspondiente fichero ``.xsig``.

Uso desde CLI::

    python -m facturae.firmar_lote  # Firma mes actual
    python -m facturae.firmar_lote 2025 07  # Firma mes concreto

La firma se realiza usando :pyfunc:`facturae.firma.firmar_xml`, que
a su vez emplea AutoFirma CLI y los certificados definidos en el
módulo :pymod:`facturae`.
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
# --- Ajuste de ruta para ejecución directa ----------------------------------
from pathlib import Path
from pathlib import Path as _Path

_BASE_DIR = _Path(__file__).resolve().parent
_PARENT_DIR = _BASE_DIR.parent
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))
# -----------------------------------------------------------------------------

# Dependencias internas (tras ajustar sys.path)
from facturae import CERTIFICADO_PATH, CLAVE_PRIVADA_PATH
from facturae.firma import firmar_xml

# Alias del certificado dentro del almacén PKCS#12
ALIAS_CERT = os.getenv("AUTOFIRMA_ALIAS", "certificadora_sami")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

# -----------------------------------------------------------------------------
# Funciones auxiliares
# -----------------------------------------------------------------------------


def obtener_directorio_facturas(year: int, month: int) -> Path:
    """Devuelve la ruta al directorio donde se guardan las facturas XML."""
    return Path(f"/var/www/html/factura_e/{year}/{str(month).zfill(2)}")


def firmar_archivo(xml_path: Path) -> bool:
    """Firma un XML y guarda el .xsig junto a él.

    Args:
        xml_path: Ruta al archivo XML.

    Returns:
        True si la firma se generó correctamente.
    """
    xsig_path = xml_path.with_suffix(".xsig")
    logger.info("Firmando %s → %s", xml_path.name, xsig_path.name)
    try:
        firmado = firmar_xml(
            ruta_xml=str(xml_path),
            ruta_clave_privada=CLAVE_PRIVADA_PATH,
            ruta_certificado_publico=CERTIFICADO_PATH,
            alias=ALIAS_CERT,
        )
        with open(xsig_path, "wb") as f:
            f.write(firmado)
        logger.info("✅ Firmado correctamente: %s", xsig_path.name)
        return True
    except Exception as exc:
        logger.error("❌ Error firmando %s: %s", xml_path.name, exc)
        return False


# -----------------------------------------------------------------------------
# Ejecución principal
# -----------------------------------------------------------------------------

def main(year: int | None = None, month: int | None = None) -> None:
    if year is None or month is None:
        now = datetime.now()
        year = now.year
        month = now.month

    dir_facturas = obtener_directorio_facturas(year, month)

    if not dir_facturas.is_dir():
        logger.warning("No existe el directorio %s", dir_facturas)
        return

    pendientes: list[Path] = []
    for xml_file in dir_facturas.glob("*.xml"):
        if not xml_file.with_suffix(".xsig").exists():
            pendientes.append(xml_file)

    if not pendientes:
        logger.info("No hay XML pendientes de firma en %s", dir_facturas)
        return

    logger.info("Se firmarán %d archivo(s) XML en %s", len(pendientes), dir_facturas)

    firmados_ok = 0
    for xml_file in pendientes:
        if firmar_archivo(xml_file):
            firmados_ok += 1

    logger.info("Proceso completado: %d/%d firmados correctamente", firmados_ok, len(pendientes))


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 2:
        try:
            anio = int(args[0])
            mes = int(args[1])
        except ValueError:
            print("Uso: python -m facturae.firmar_lote [YEAR MONTH]")
            sys.exit(1)
        main(anio, mes)
    else:
        main()

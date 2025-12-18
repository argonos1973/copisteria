#!/usr/bin/env python3

import os
import json
import sqlite3
import shutil
import zipfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Cargar variables de entorno desde .env antes de importar módulos que las necesiten
load_dotenv('/var/www/html/.env')

from werkzeug.utils import secure_filename

from logger_config import get_logger
from multiempresa_config import DB_USUARIOS_PATH
from batch_utils import load_batch_params, get_batch_db_path
from factura_ocr import procesar_imagen_factura
from facturas_proveedores import (
    ensure_facturas_proveedores_tables,
    calcular_hash_pdf,
    factura_ya_procesada,
    guardar_factura_bd,
    obtener_o_crear_proveedor,
)

logger = get_logger(__name__)


def _as_float(v):
    try:
        if v is None:
            return 0.0
        s = str(v).strip().replace(',', '.')
        if not s:
            return 0.0
        return float(s)
    except Exception:
        return 0.0


def _iva_porcentaje(base, iva, default_pct=21.0):
    try:
        if base and base > 0 and iva is not None and iva >= 0:
            return round((iva / base) * 100.0, 2)
    except Exception:
        pass
    return float(default_pct)


def _get_empresa_codigo_y_cif(empresa_id: int):
    codigo = None
    cif = None
    try:
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cur = conn.cursor()
        cur.execute("SELECT codigo, cif FROM empresas WHERE id = ?", (empresa_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            codigo = row[0]
            cif = row[1]
    except Exception as e:
        logger.error(f"Error leyendo empresas desde usuarios_sistema.db: {e}")

    if cif:
        try:
            cif = str(cif).upper().replace('-', '').replace(' ', '').strip()
        except Exception:
            cif = None

    if codigo:
        try:
            codigo = str(codigo).strip()
        except Exception:
            codigo = None

    return codigo, cif


def _safe_extract_zip(zip_path: Path, dest_dir: Path):
    with zipfile.ZipFile(str(zip_path), 'r') as zf:
        for member in zf.infolist():
            name = member.filename
            if not name or name.endswith('/'):
                continue
            # Ignorar metadatos de macOS
            if name.startswith('__MACOSX/') or '/._' in name or os.path.basename(name).startswith('._'):
                continue
                
            out_path = (dest_dir / name).resolve()
            if not str(out_path).startswith(str(dest_dir.resolve()) + os.sep):
                raise ValueError(f"ZIP entry path fuera de destino: {name}")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member, 'r') as src, open(out_path, 'wb') as dst:
                shutil.copyfileobj(src, dst)


def _find_zip_to_process(input_path: Path, name_contains: Optional[str]):
    zips = [p for p in sorted(input_path.iterdir()) if p.is_file() and p.suffix.lower() == '.zip']
    if not zips:
        return None
    if not name_contains:
        return zips[0]
    needle = str(name_contains).lower().strip()
    for p in zips:
        if needle in p.name.lower():
            return p
    return None


def _process_one_file(
    path: Path,
    empresa_id: int,
    empresa_codigo: str,
    nif_cliente: Optional[str],
    proveedor_id_forced: Optional[int],
):
    raw_bytes = path.read_bytes()
    pdf_hash = calcular_hash_pdf(raw_bytes)

    if factura_ya_procesada(pdf_hash, empresa_id):
        return {'status': 'duplicate', 'path': str(path)}

    datos_ocr = procesar_imagen_factura(raw_bytes, nif_cliente)
    proveedor = datos_ocr.get('proveedor') or {}
    factura = datos_ocr.get('factura') or {}

    proveedor_id = None
    if proveedor_id_forced is not None:
        proveedor_id = int(proveedor_id_forced)
    else:
        nif_proveedor = (proveedor.get('nif') or '').upper().replace('-', '').replace(' ', '').strip()
        nombre_proveedor = (proveedor.get('nombre') or '').strip()

        if not nombre_proveedor and not nif_proveedor:
            raise ValueError('Proveedor no identificado por OCR (nombre y nif vacíos)')

        datos_adicionales = {}
        try:
            direccion = (proveedor.get('direccion') or '').strip()
            telefono = (proveedor.get('telefono') or '').strip()
            email = (proveedor.get('email') or '').strip()
            website = (proveedor.get('website') or '').strip()
            if direccion:
                datos_adicionales['direccion'] = direccion
            if telefono:
                datos_adicionales['telefono'] = telefono
            if email:
                datos_adicionales['email'] = email
            if website:
                datos_adicionales['website'] = website
            datos_adicionales['requiere_revision'] = True
            datos_adicionales['creado_automaticamente'] = 1
        except Exception:
            datos_adicionales = {'requiere_revision': True, 'creado_automaticamente': 1}

        proveedor_id = obtener_o_crear_proveedor(
            nif_proveedor or None,
            nombre_proveedor or 'PROVEEDOR DESCONOCIDO',
            empresa_id,
            datos_adicionales=datos_adicionales,
            email_origen=proveedor.get('email'),
        )

    base = _as_float(factura.get('base_imponible'))
    iva = _as_float(factura.get('iva'))
    total = _as_float(factura.get('total'))
    if total <= 0 and base > 0:
        total = base + iva

    datos_factura = {
        'numero_factura': factura.get('numero') or factura.get('numero_factura'),
        'fecha_emision': factura.get('fecha_emision'),
        'fecha_vencimiento': factura.get('fecha_vencimiento'),
        'base_imponible': base,
        'iva_porcentaje': _iva_porcentaje(base, iva, 21.0),
        'iva_importe': iva,
        'total': total,
        'concepto': factura.get('concepto'),
        'notas': '',
        'estado': 'pagada',
        'metodo_extraccion': datos_ocr.get('_metodo_ocr') or 'OCR',
        'confianza_extraccion': None,
    }

    anio = datetime.now().year
    upload_folder = f"/var/www/html/facturas_proveedores/{empresa_codigo}/{anio}"
    os.makedirs(upload_folder, exist_ok=True)

    safe_name = secure_filename(path.name)
    if not safe_name:
        safe_name = f"SCAN_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{path.suffix.lstrip('.')}"

    ruta_destino = os.path.join(upload_folder, safe_name)
    if os.path.exists(ruta_destino):
        root, ext = os.path.splitext(safe_name)
        ruta_destino = os.path.join(upload_folder, f"{root}_{datetime.now().strftime('%H%M%S')}_{os.getpid()}{ext}")

    with open(ruta_destino, 'wb') as f:
        f.write(raw_bytes)

    factura_id = guardar_factura_bd(
        empresa_id,
        proveedor_id,
        datos_factura,
        ruta_destino,
        pdf_hash,
        usuario='batch',
    )

    return {'status': 'ok', 'id': factura_id, 'path': str(path), 'dest': ruta_destino}


def main():
    params = load_batch_params()

    db_path = get_batch_db_path(params)
    if db_path:
        os.environ['EMPRESA_DB_PATH'] = str(db_path)

    empresa_id = os.getenv('EMPRESA_ID') or params.get('empresa_id')
    if empresa_id is None or str(empresa_id).strip() == '':
        raise RuntimeError('empresa_id requerido (env EMPRESA_ID o params.empresa_id)')
    empresa_id = int(empresa_id)

    empresa_codigo = (os.getenv('EMPRESA_CODE') or '').strip()
    if not empresa_codigo:
        codigo_db, _ = _get_empresa_codigo_y_cif(empresa_id)
        empresa_codigo = (codigo_db or str(empresa_id)).strip()

    _, nif_cliente = _get_empresa_codigo_y_cif(empresa_id)

    input_dir = params.get('input_dir') or params.get('carpeta_entrada')
    if not input_dir:
        raise RuntimeError('params.input_dir requerido')

    input_path = Path(str(input_dir))
    if not input_path.exists() or not input_path.is_dir():
        raise RuntimeError(f"input_dir no existe o no es directorio: {input_path}")

    processed_dir = params.get('processed_dir') or str(input_path / 'processed')
    error_dir = params.get('error_dir') or str(input_path / 'error')

    processed_path = Path(processed_dir)
    error_path = Path(error_dir)
    processed_path.mkdir(parents=True, exist_ok=True)
    error_path.mkdir(parents=True, exist_ok=True)

    processed_dup_path = processed_path / 'duplicadas'
    processed_dup_path.mkdir(parents=True, exist_ok=True)

    zip_name_contains = params.get('zip_name_contains') or params.get('zip_contiene')
    process_zip = bool(params.get('process_zip') or zip_name_contains)
    process_all_zips = bool(params.get('process_all_zips') or params.get('procesar_todos_los_zips'))

    proveedor_id_forced = params.get('proveedor_id')
    if proveedor_id_forced is not None:
        try:
            proveedor_id_forced = int(proveedor_id_forced)
        except Exception:
            raise RuntimeError('params.proveedor_id debe ser entero')

    max_files = params.get('max_files')
    try:
        max_files = int(max_files) if max_files is not None else None
    except Exception:
        max_files = None

    ensure_facturas_proveedores_tables()

    allowed_ext = {'.pdf', '.jpg', '.jpeg', '.png'}
    summary = {'ok': 0, 'duplicate': 0, 'error': 0, 'skipped': 0, 'zip_processed': 0, 'zip_error': 0}

    def _process_files_root(files_root: Path, from_zip: bool):
        files = []
        for p in files_root.rglob('*'):
            if p.is_file() and p.suffix.lower() in allowed_ext:
                files.append(p)
        files_sorted = sorted(files)
        if max_files is not None:
            files_sorted = files_sorted[:max_files]

        for p in files_sorted:
            try:
                res = _process_one_file(p, empresa_id, empresa_codigo, nif_cliente, proveedor_id_forced)
                st = res.get('status')
                if st == 'ok':
                    summary['ok'] += 1
                    if not from_zip:
                        shutil.move(str(p), str(processed_path / p.name))
                    logger.info(f"Factura OK: {p.name} -> id={res.get('id')}")
                elif st == 'duplicate':
                    summary['duplicate'] += 1
                    if not from_zip:
                        shutil.move(str(p), str(processed_dup_path / p.name))
                    logger.info(f"Factura duplicada: {p.name}")
                else:
                    summary['skipped'] += 1
                    logger.info(f"Factura omitida: {p.name}")
            except Exception as e:
                summary['error'] += 1
                if not from_zip:
                    try:
                        shutil.move(str(p), str(error_path / p.name))
                    except Exception:
                        pass
                logger.error(f"Error procesando {p.name}: {e}")

    if process_zip:
        zips_to_process = []
        if process_all_zips and not zip_name_contains:
            zips_to_process = [p for p in sorted(input_path.iterdir()) if p.is_file() and p.suffix.lower() == '.zip']
        else:
            one = _find_zip_to_process(input_path, zip_name_contains)
            if one:
                zips_to_process = [one]

        if not zips_to_process:
            raise RuntimeError('No se encontró ZIP para procesar en input_dir')

        dest_zip_dir = processed_path / 'zips'
        dest_zip_dir.mkdir(parents=True, exist_ok=True)

        for zip_path in zips_to_process:
            before_errors = summary['error']

            extract_root = input_path / f".extract_{zip_path.stem}_{uuid.uuid4().hex}"
            extract_root.mkdir(parents=True, exist_ok=True)
            _safe_extract_zip(zip_path, extract_root)

            _process_files_root(extract_root, True)

            try:
                shutil.rmtree(str(extract_root), ignore_errors=True)
            except Exception:
                pass

            errors_after = summary['error']
            zip_had_errors = (errors_after > before_errors)
            if zip_had_errors:
                summary['zip_error'] += 1
                try:
                    shutil.move(str(zip_path), str(error_path / zip_path.name))
                except Exception:
                    pass
            else:
                summary['zip_processed'] += 1
                try:
                    shutil.move(str(zip_path), str(dest_zip_dir / zip_path.name))
                except Exception:
                    pass
    else:
        _process_files_root(input_path, False)

    logger.info(f"Resumen scan facturas recibidas: {json.dumps(summary, ensure_ascii=False)}")


if __name__ == '__main__':
    main()

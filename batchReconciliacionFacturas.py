#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import os
import re
import sqlite3
import sys
from datetime import datetime

from constantes import *
# Importar directamente desde el módulo facturae en lugar del wrapper obsoleto
from facturae.generador import generar_facturae

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('batchReconciliacionFacturas')

# Conexión local a la base de datos, independiente de Flask/db_utils
try:
    DB_PATH = DB_NAME
except NameError:
    DB_PATH = '/var/www/html/aleph70.db'  # valor por defecto si no está en constantes

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA encoding="UTF-8"')
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def extraer_numero_factura(concepto):
    """
    Extrae el número de factura del campo concepto usando regex.
    Se asume que los números de factura siguen el patrón F[0-9]{6} (ejemplo: F250059).
    """
    match = re.search(r'F\d{6}', concepto)
    if match:
        return match.group(0)
    return None

def reconciliar_facturas():
    """
    Busca ingresos en gastos y concilia con facturas pendientes.
    Marca como pagadas las facturas que coincidan en número y cantidad.
    """
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("No se pudo establecer conexión con la base de datos")
            return

        cursor = conn.cursor()
        # Obtener ingresos del banco (importe positivo)
        cursor.execute('''
            SELECT id, fecha_operacion, concepto, importe_eur
            FROM gastos
            WHERE CAST(importe_eur AS REAL) > 0
        ''')
        ingresos = cursor.fetchall()

        # Obtener facturas pendientes
        cursor.execute('''
            SELECT id, numero, total, estado
            FROM factura
            WHERE estado IN ('P', 'V')
        ''')
        facturas = cursor.fetchall()
        facturas_dict = {f['numero']: f for f in facturas}

        conciliadas = 0
        conn.execute('BEGIN')
        for ingreso in ingresos:
            concepto = ingreso['concepto'] or ''
            importe = float(ingreso['importe_eur']) if ingreso['importe_eur'] is not None else 0.0
            numero_factura = extraer_numero_factura(concepto)
            if not numero_factura:
                continue
            factura = facturas_dict.get(numero_factura)
            if factura and abs(float(factura['total']) - importe) < 0.01 and factura['estado'] != 'C':
                cursor.execute('''
                    UPDATE factura
                    SET estado = 'C', importe_cobrado = ?, timestamp = ?
                    WHERE id = ?
                ''', (importe, datetime.now().isoformat(), factura['id']))
                logger.info(f"Factura {numero_factura} marcada como COBRADA por ingreso {ingreso['id']} (importe: {importe})")
                conciliadas += 1

                # === Generar y firmar XML de factura electrónica ===
                # Obtener datos completos de la factura
                cursor.execute('SELECT * FROM factura WHERE id = ?', (factura['id'],))
                factura_row = cursor.fetchone()
                if not factura_row:
                    logger.error(f"No se pudo obtener la factura completa para {numero_factura}")
                    continue
                factura_dict = dict(factura_row)

                # Obtener detalles de la factura
                cursor.execute('SELECT * FROM detalle_factura WHERE id_factura = ?', (factura['id'],))
                detalles = [dict(row) for row in cursor.fetchall()]

                # Obtener datos del contacto
                cursor.execute('SELECT * FROM contactos WHERE idcontacto = ?', (factura_dict['idContacto'],))
                contacto_row = cursor.fetchone()
                if not contacto_row:
                    logger.error(f"No se pudo obtener el contacto para la factura {numero_factura}")
                    continue
                contacto_dict = dict(contacto_row)

                # Leer datos del emisor desde emisor_config.json
                with open('emisor_config.json', 'r', encoding='utf-8') as f:
                    emisor_config = json.load(f)
                datos_factura = {
                    'emisor': emisor_config,
                    'receptor': {
                        'nif': contacto_row['identificador'],
                        'nombre': contacto_row['razonsocial'] if contacto_row['razonsocial'] is not None else '',
                        'direccion': contacto_row['direccion'] if contacto_row['direccion'] is not None else '',
                        'cp': contacto_row['cp'] if contacto_row['cp'] is not None else '',
                        'provincia': contacto_row['provincia'] if contacto_row['provincia'] is not None else '',
                        'localidad': contacto_row['localidad'] if contacto_row['localidad'] is not None else '',
                        # Añade otros campos si son necesarios
                    },
                    'detalles': detalles,
                    'fecha': factura_row['fecha'],
                    'numero': factura_row['numero'],
                    'iva': 21.0  # Ajusta si tienes el valor real
                    # Agrega otros campos si los requiere la función
                }

                # Establecer directorio de salida con permisos adecuados
                output_dir = f"/tmp/factura_e/{factura_dict['fecha'][:7].replace('-', '/')}"
                os.makedirs(output_dir, exist_ok=True)
                
                # Llamar a la función de generación y firma
                try:
                    datos_factura['output_dir'] = output_dir  # Usar directorio temporal con permisos
                    ruta_xml = generar_facturae(
                        datos_factura
                    )
                    # Verificar si es realmente XSIG (firmado)
                    if ruta_xml.lower().endswith('.xsig'):
                        logger.info(f"XML de factura electrónica generado y firmado para factura {numero_factura}: {ruta_xml}")
                        # Verificar si existe la columna factura_e
                        try:
                            # Actualizamos el campo factura_e en la BD para indicar que se ha generado correctamente
                            cursor.execute('UPDATE factura SET factura_e = 1 WHERE id = ?', (factura['id'],))
                        except sqlite3.OperationalError as e:
                            if "no such column" in str(e):
                                # Crear la columna si no existe
                                logger.info("Creando columna factura_e en la tabla factura...")
                                cursor.execute('ALTER TABLE factura ADD COLUMN factura_e INTEGER DEFAULT 0')
                                cursor.execute('UPDATE factura SET factura_e = 1 WHERE id = ?', (factura['id'],))
                            else:
                                raise
                    else:
                        logger.error(f"ERROR: No se generó archivo XSIG firmado para factura {numero_factura}. En su lugar se obtuvo: {ruta_xml}")
                        # Esto no debería ocurrir con los cambios en facturae_utils.py pero lo comprobamos por seguridad
                        continue
                except Exception as e:
                    logger.error(f"ERROR al generar factura electrónica para factura {numero_factura}: {e}")
                    # Continuamos con la siguiente factura
                    continue
        conn.commit()
        logger.info(f"Proceso de conciliación finalizado. Facturas conciliadas: {conciliadas}")
    except Exception as e:
        logger.error(f"Error en el proceso de conciliación: {e}")
        if conn:
            conn.rollback()
    finally:
        # Cerrar conexión sin generar notificaciones web
        if conn:
            conn.close()


def main():
    try:
        logger.info("Iniciando proceso de conciliación de facturas")
        reconciliar_facturas()
        logger.info("Proceso finalizado")
    except Exception as e:
        logger.error(f"Error en el proceso: {e}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())

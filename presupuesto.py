import sqlite3
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from format_utils import format_currency_es_two, format_total_es_two, format_number_es_max5, format_percentage

from flask import Blueprint, Flask, jsonify, request, send_file, session
import utilities
from db_utils import (
    actualizar_numerador,
    formatear_numero_documento,
    get_db_connection,
    obtener_numerador,
    redondear_importe,
)
from logger_config import get_logger

# Inicializar logger
logger = get_logger(__name__)

def _formatear_detalle_presupuesto(detalle_row):
    det_dict = dict(detalle_row)
    det_dict['cantidad'] = format_number_es_max5(det_dict.get('cantidad'))
    det_dict['precio'] = format_number_es_max5(det_dict.get('precio'))
    det_dict['impuestos'] = format_number_es_max5(det_dict.get('impuestos'))
    det_dict['total'] = format_currency_es_two(det_dict.get('total'))
    return det_dict


def _obtener_detalles_formateados(cursor, presupuesto_id):
    detalles_rows = cursor.execute(
        'SELECT * FROM detalle_presupuesto WHERE id_presupuesto = ? ORDER BY id', (presupuesto_id,)
    ).fetchall()
    return [_formatear_detalle_presupuesto(row) for row in detalles_rows]


def _formatear_importes_presupuesto(data):
    for key in ('importe_bruto', 'importe_impuestos', 'importe_cobrado', 'total'):
        if key in data:
            data[key] = format_currency_es_two(data.get(key))
    return data

presupuesto_bp = Blueprint('presupuestos', __name__)

app = Flask(__name__)


def _verificar_numero_presupuesto_local(numero):
    """Verifica existencia de un presupuesto con el mismo número (helper local)."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id FROM presupuesto WHERE numero = ?', (numero,))
        row = cur.fetchone()
        if row:
            return True, (row['id'] if isinstance(row, sqlite3.Row) else row[0])
        return False, None
    except Exception as e:
        logger.error(f"Error en _verificar_numero_presupuesto_local: {e}", exc_info=True)
        return False, None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def crear_presupuesto():
    conn = None
    try:
        data = request.get_json() or {}
        logger.info(f"[PRESUPUESTO] Datos recibidos en crear_presupuesto: {data}")
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400

        # Verificar duplicado
        existe, _id = _verificar_numero_presupuesto_local(data.get('numero'))
        if existe:
            return jsonify({'error': 'Ya existe un presupuesto con este número'}), 400

        conn = get_db_connection()
        conn.execute('PRAGMA busy_timeout = 10000')
        conn.execute('BEGIN TRANSACTION')
        cursor = conn.cursor()

        es_actualizacion = bool(data.get('id'))

        cursor.execute(
            '''
            INSERT INTO presupuesto (
                numero, fecha, estado, idcontacto, nif, total, formaPago,
                importe_bruto, importe_impuestos, importe_cobrado, timestamp, tipo
            ) VALUES (?, ?, 'B', ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['numero'],
                data['fecha'],
                data.get('idcontacto'),
                data.get('nif', ''),
                data.get('total', 0),
                data.get('formaPago', 'E'),
                data.get('importe_bruto', 0),
                data.get('importe_impuestos', 0),
                data.get('importe_cobrado', 0),
                datetime.now().isoformat(),
                data.get('tipo', 'N'),
            )
        )
        presupuesto_id = cursor.lastrowid

        for detalle in data.get('detalles', []):
            cursor.execute(
                '''
                INSERT INTO detalle_presupuesto (
                    id_presupuesto, concepto, descripcion, cantidad,
                    precio, impuestos, total, formaPago, productoId, fechaDetalle
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    presupuesto_id,
                    detalle['concepto'],
                    detalle.get('descripcion', ''),
                    detalle['cantidad'],
                    detalle['precio'],
                    detalle['impuestos'],
                    detalle['total'],
                    detalle.get('formaPago', 'E'),
                    detalle.get('productoId', None),
                    detalle.get('fechaDetalle', data['fecha'])
                )
            )

        if not es_actualizacion:
            try:
                numerador_actual, _ = actualizar_numerador('O', conn, commit=False)
                if numerador_actual is None:
                    conn.rollback()
                    return jsonify({"error": "Error al actualizar el numerador"}), 500
            except Exception as e:
                conn.rollback()
                return jsonify({"error": f"Error al actualizar numerador: {str(e)}"}), 500

        conn.commit()
        return jsonify({'mensaje': 'Presupuesto creado exitosamente', 'id': presupuesto_id})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error en crear_presupuesto: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


def obtener_presupuesto(id):
    try:
        conn = get_db_connection()
        conn.execute('PRAGMA busy_timeout = 10000')
        cursor = conn.cursor()

        presupuesto = cursor.execute('SELECT * FROM presupuesto WHERE id = ?', (id,)).fetchone()
        if not presupuesto:
            return jsonify({'error': 'Presupuesto no encontrado'}), 404

        resultado = _formatear_importes_presupuesto(dict(presupuesto))
        resultado['detalles'] = _obtener_detalles_formateados(cursor, id)
        
        # Buscar datos del contacto si existe idcontacto (minúscula)
        logger.info(f"[DEBUG] idcontacto en presupuesto: {resultado.get('idcontacto')}")
        if resultado.get('idcontacto'):
            contacto = cursor.execute(
                'SELECT * FROM contactos WHERE idContacto = ?', (resultado['idcontacto'],)
            ).fetchone()
            logger.info(f"[DEBUG] Contacto encontrado: {contacto}")
            if contacto:
                resultado['contacto'] = dict(contacto)
                logger.info(f"[DEBUG] Contacto añadido al resultado: {dict(contacto)}")
            else:
                logger.info(f"[DEBUG] No se encontró contacto con idcontacto: {resultado['idcontacto']}")
        else:
            logger.info("[DEBUG] No hay idcontacto en el presupuesto")
        
        return jsonify(resultado)

    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        try:
            conn.close()
        except Exception:
            pass


def actualizar_presupuesto(id, data):
    conn = None
    try:
        data = data or {}
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400

        conn = get_db_connection()
        conn.execute('PRAGMA busy_timeout = 10000')
        conn.execute('BEGIN TRANSACTION')
        cursor = conn.cursor()

        cursor.execute('SELECT numero FROM presupuesto WHERE id = ?', (id,))
        if not cursor.fetchone():
            conn.rollback()
            return jsonify({'error': 'Presupuesto no encontrado'}), 404

        total = redondear_importe(float(data.get('total', 0)))
        importe_bruto = redondear_importe(float(data.get('importe_bruto', 0)))
        importe_impuestos = redondear_importe(float(data.get('importe_impuestos', 0)))
        importe_cobrado = redondear_importe(float(data.get('importe_cobrado', 0)))

        cursor.execute(
            '''
            UPDATE presupuesto
            SET numero = ?, fecha = ?, estado = ?, idcontacto = ?, nif = ?, total = ?, formaPago = ?,
                importe_bruto = ?, importe_impuestos = ?, importe_cobrado = ?, timestamp = ?, tipo = ?
            WHERE id = ?
            ''', (
                data['numero'],
                data['fecha'],
                data.get('estado', 'B'),
                data.get('idcontacto'),
                data.get('nif', ''),
                total,
                data.get('formaPago', 'E'),
                importe_bruto,
                importe_impuestos,
                importe_cobrado,
                datetime.now().isoformat(),
                data.get('tipo', 'N'),
                id,
            )
        )

        cursor.execute('DELETE FROM detalle_presupuesto WHERE id_presupuesto = ?', (id,))

        if 'detalles' not in data or not isinstance(data['detalles'], list):
            conn.rollback()
            return jsonify({'error': 'Se requiere una lista de detalles válida'}), 400

        for detalle in data['detalles']:
            cantidad = int(detalle['cantidad'])
            precio = float(detalle['precio'])
            impuestos = float(detalle['impuestos'])
            total_detalle = redondear_importe(float(detalle['total']))

            cursor.execute(
                '''
                INSERT INTO detalle_presupuesto (
                    id_presupuesto, concepto, descripcion, cantidad,
                    precio, impuestos, total, formaPago, productoId, fechaDetalle
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    id,
                    detalle['concepto'],
                    detalle.get('descripcion', ''),
                    cantidad,
                    precio,
                    impuestos,
                    total_detalle,
                    detalle.get('formaPago', 'E'),
                    detalle.get('productoId', None),
                    detalle.get('fechaDetalle', data['fecha'])
                )
            )

        conn.commit()
        return jsonify({'mensaje': 'Presupuesto actualizado exitosamente', 'id': id})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error al actualizar presupuesto {id}: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


def obtener_presupuesto_abierto(idcontacto):
    try:
        conn = get_db_connection()
        conn.execute('PRAGMA busy_timeout = 10000')
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM contactos WHERE idContacto = ?', (idcontacto,))
        contacto = cursor.fetchone()
        if not contacto:
            return jsonify({'error': 'Contacto no encontrado'}), 404
        contacto_dict = dict(contacto)

        sql = '''
            SELECT p.id, p.numero, p.fecha, p.estado, p.tipo, p.total, p.idContacto AS idcontacto
            FROM presupuesto p
            WHERE p.idContacto = ? AND p.estado = 'B'
            ORDER BY p.fecha DESC, p.id DESC
            LIMIT 1
        '''
        cursor.execute(sql, (idcontacto,))
        presupuesto = cursor.fetchone()

        if presupuesto:
            presupuesto_dict = _formatear_importes_presupuesto(dict(presupuesto))
            detalles = _obtener_detalles_formateados(cursor, presupuesto_dict['id'])
            return jsonify({
                'modo': 'edicion',
                'id': presupuesto_dict['id'],
                'numero': presupuesto_dict['numero'],
                'fecha': presupuesto_dict['fecha'],
                'estado': presupuesto_dict['estado'],
                'tipo': presupuesto_dict['tipo'],
                'total': presupuesto_dict.get('total'),
                'contacto': contacto_dict,
                'detalles': detalles
            })
        else:
            return jsonify({
                'modo': 'nuevo',
                'contacto': {
                    'idContacto': contacto_dict['idContacto'],
                    'razonsocial': contacto_dict['razonsocial'],
                    'identificador': contacto_dict['identificador'],
                    'direccion': contacto_dict['direccion'],
                    'cp': contacto_dict['cp'],
                    'localidad': contacto_dict['localidad'],
                    'provincia': contacto_dict['provincia'],
                }
            })

    except sqlite3.Error as e:
        return jsonify({'error': f"Error de base de datos: {str(e)}"}), 500
    except Exception as e:
        return jsonify({'error': f"Error al buscar presupuesto abierto: {str(e)}"}), 500
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


def consultar_presupuestos():
    try:
        fecha_inicio = request.args.get('fecha_inicio', '')
        fecha_fin = request.args.get('fecha_fin', '')
        estado = request.args.get('estado', '')
        numero = request.args.get('numero', '')
        contacto = request.args.get('contacto', '')
        identificador = request.args.get('identificador', '')
        concepto = request.args.get('concepto', '')

        # Normalizar estado: quitar espacios y llevar a mayúsculas; mapear 'TODOS'/'ALL' a vacío
        try:
            if estado:
                estado = estado.strip().upper()
                if estado in ('TODOS', 'ALL'):
                    estado = ''
        except Exception:
            pass

        try:
            logger.info(f"[CONSULTA_PRESUPUESTOS][ARGS] fecha_inicio={fecha_inicio}, fecha_fin={fecha_fin}, estado='{estado}', numero='{numero}', contacto='{contacto}', identificador='{identificador}', concepto='{concepto}'")
        except Exception:
            pass

        hay_filtros_adicionales = any([
            estado.strip(), numero.strip(), contacto.strip(), identificador.strip(), concepto.strip()
        ])

        conn = get_db_connection()
        cursor = conn.cursor()

        base_sql = """
            SELECT 
                p.id,
                p.fecha,
                p.numero,
                p.estado,
                p.tipo,
                p.importe_bruto as base,
                p.importe_impuestos as iva,
                p.importe_cobrado,
                p.total,
                p.idContacto AS idcontacto,
                c.razonsocial,
                c.mail
            FROM presupuesto p
            LEFT JOIN contactos c ON p.idContacto = c.idContacto
            WHERE 1=1
        """
        filtros_sql = ""
        params = []

        if fecha_inicio and (not hay_filtros_adicionales):
            filtros_sql += " AND p.fecha >= ?"
            params.append(fecha_inicio)
        if fecha_fin and (not hay_filtros_adicionales):
            filtros_sql += " AND p.fecha <= ?"
            params.append(fecha_fin)
        if estado:
            filtros_sql += " AND p.estado = ?"
            params.append(estado)
        else:
            filtros_sql += " AND p.estado <> 'A0'"
        if numero:
            filtros_sql += " AND p.numero LIKE ?"
            params.append(f"%{numero}%")
        if contacto:
            filtros_sql += " AND c.razonsocial LIKE ?"
            params.append(f"%{contacto}%")
        if identificador:
            filtros_sql += " AND c.identificador LIKE ?"
            params.append(f"%{identificador}%")
        if concepto:
            filtros_sql += " AND EXISTS (SELECT 1 FROM detalle_presupuesto dp WHERE dp.id_presupuesto = p.id AND dp.concepto LIKE ?)"
            params.append(f"%{concepto}%")

        sql = f"{base_sql}{filtros_sql} ORDER BY p.fecha DESC LIMIT 100"

        try:
            logger.info(f"[CONSULTA_PRESUPUESTOS][SQL] {sql}, PARAMS: {params}")
        except Exception:
            pass

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        columnas = [desc[0] for desc in cursor.description]
        result = []
        for row in rows:
            raw = dict(zip(columnas, row))
            result.append({
                'id': raw.get('id'),
                'fecha': raw.get('fecha'),
                'numero': raw.get('numero'),
                'estado': raw.get('estado'),
                'tipo': raw.get('tipo'),
                'base': format_currency_es_two(raw.get('base')), 
                'iva': format_currency_es_two(raw.get('iva')),
                'importe_cobrado': format_currency_es_two(raw.get('importe_cobrado')),
                'total': format_currency_es_two(raw.get('total')),
                'idcontacto': raw.get('idcontacto'),
                'razonsocial': raw.get('razonsocial'),
                'mail': raw.get('mail')
            })

        totales_globales = {
            'total_base': '0,00',
            'total_iva': '0,00',
            'total_cobrado': '0,00',
            'total_total': '0,00'
        }

        totales_sql = f"""
            SELECT 
                SUM(p.importe_bruto) as total_base,
                SUM(p.importe_impuestos) as total_iva,
                SUM(p.importe_cobrado) as total_cobrado,
                SUM(p.total) as total_total
            FROM presupuesto p
            LEFT JOIN contactos c ON p.idContacto = c.idContacto
            WHERE 1=1{filtros_sql}
        """

        cursor.execute(totales_sql, params)
        tot_row = cursor.fetchone()

        if tot_row:
            if isinstance(tot_row, sqlite3.Row):
                total_base = tot_row['total_base'] or 0
                total_iva = tot_row['total_iva'] or 0
                total_cobrado = tot_row['total_cobrado'] or 0
                total_total = tot_row['total_total'] or 0
            else:
                total_base = tot_row[0] or 0
                total_iva = tot_row[1] or 0
                total_cobrado = tot_row[2] or 0
                total_total = tot_row[3] or 0

            totales_globales = {
                'total_base': format_currency_es_two(total_base),
                'total_iva': format_currency_es_two(total_iva),
                'total_cobrado': format_currency_es_two(total_cobrado),
                'total_total': format_currency_es_two(total_total)
            }

        return jsonify({
            'items': result,
            'totales_globales': totales_globales
        })

    except Exception as e:
        logger.error(f"Error en consultar_presupuestos: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500
    finally:
        try:
            conn.close()
        except Exception:
            pass


def convertir_presupuesto_a_factura(id_presupuesto):
    conn = None
    try:
        conn = get_db_connection()
        conn.execute('PRAGMA busy_timeout = 10000')
        conn.execute('BEGIN TRANSACTION')
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM presupuesto WHERE id = ?', (id_presupuesto,))
        pres = cursor.fetchone()
        if not pres:
            conn.rollback()
            return jsonify({'error': 'Presupuesto no encontrado'}), 404

        if pres['estado'] == 'F':
            conn.rollback()
            return jsonify({'error': 'Este presupuesto ya ha sido facturado'}), 400

        numerador, _ = obtener_numerador('F', conn)
        if numerador is None:
            conn.rollback()
            return jsonify({'error': 'Error al obtener el numerador de facturas'}), 500
        numero_core = formatear_numero_documento('F', conn)
        anno = datetime.now().year % 100
        numero_formateado = f"F{anno:02}{numero_core}"

        cursor.execute('SELECT * FROM detalle_presupuesto WHERE id_presupuesto = ?', (id_presupuesto,))
        detalles_pres = cursor.fetchall()

        cursor.execute(
            '''
            INSERT INTO factura (
                numero, fecha, fvencimiento, estado, idcontacto, nif, total, formaPago,
                importe_bruto, importe_impuestos, importe_cobrado, timestamp, tipo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                numero_formateado,
                datetime.now().strftime('%Y-%m-%d'),
                (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d'),
                'P',
                pres['idcontacto'],
                pres['nif'],
                pres['total'],
                pres['formaPago'],
                pres['importe_bruto'],
                pres['importe_impuestos'],
                pres['importe_cobrado'],
                datetime.now().isoformat(),
                pres['tipo']
            )
        )
        factura_id = cursor.lastrowid

        for d in detalles_pres:
            cursor.execute(
                '''
                INSERT INTO detalle_factura (
                    id_factura, concepto, descripcion, cantidad, precio,
                    impuestos, total, productoId, fechaDetalle
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    factura_id,
                    d['concepto'],
                    d['descripcion'],
                    d['cantidad'],
                    d['precio'],
                    d['impuestos'],
                    d['total'],
                    d['productoId'],
                    d['fechaDetalle']
                )
            )

        cursor.execute('UPDATE presupuesto SET estado = ? WHERE id = ?', ('AP', id_presupuesto))

        numerador_actual, _ = actualizar_numerador('F', conn, commit=False)
        if numerador_actual is None:
            conn.rollback()
            return jsonify({'error': 'Error al actualizar el numerador de facturas'}), 500

        conn.commit()
        return jsonify({
            'mensaje': 'Presupuesto convertido a factura exitosamente',
            'id_presupuesto': id_presupuesto,
            'id_factura': factura_id,
            'numero_factura': numero_formateado,
        })

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error al convertir presupuesto a factura: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


def convertir_presupuesto_a_ticket(id_presupuesto):
    from verifactu.core import generar_datos_verifactu_para_ticket

    conn = None
    try:
        conn = get_db_connection()
        conn.execute('PRAGMA busy_timeout = 10000')
        conn.execute('BEGIN TRANSACTION')
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM presupuesto WHERE id = ?', (id_presupuesto,))
        pres = cursor.fetchone()
        if not pres:
            conn.rollback()
            return jsonify({'error': 'Presupuesto no encontrado'}), 404

        numerador, _ = obtener_numerador('T', conn)
        if numerador is None:
            conn.rollback()
            return jsonify({'error': 'Error al obtener el numerador de tickets'}), 500
        numero_core = formatear_numero_documento('T', conn)
        anno = datetime.now().year % 100
        numero_ticket = f"T{anno:02}{numero_core}"

        cursor.execute('SELECT * FROM detalle_presupuesto WHERE id_presupuesto = ?', (id_presupuesto,))
        detalles_pres = cursor.fetchall()

        try:
            # Convertir sqlite3.Row a dict para poder acceder con []
            detalles_dict = [dict(d) for d in detalles_pres]
            
            importe_bruto = 0
            importe_impuestos = 0
            total_calculado = 0
            
            for d in detalles_dict:
                res = utilities.calcular_importes(d['cantidad'], d['precio'], d['impuestos'])
                importe_bruto += res['subtotal']
                importe_impuestos += res['iva']
                total_calculado += res['total']
            
            importe_bruto = redondear_importe(importe_bruto)
            importe_impuestos = redondear_importe(importe_impuestos)
            total_ticket = redondear_importe(total_calculado)
        except Exception:
            importe_bruto = redondear_importe(0)
            importe_impuestos = redondear_importe(0)
            total_ticket = redondear_importe(0)

        cursor.execute(
            '''
            INSERT INTO tickets (
                fecha, numero, importe_bruto, importe_impuestos, importe_cobrado, total,
                timestamp, estado, formaPago, tipo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().strftime('%Y-%m-%d'),
                numero_ticket,
                importe_bruto,
                importe_impuestos,
                0.0,
                total_ticket,
                datetime.now().isoformat(),
                'P',
                pres['formaPago'],
                pres['tipo']
            )
        )
        ticket_id = cursor.lastrowid

        for d in detalles_dict:
            cantidad = float(d['cantidad'])
            precio = float(d['precio'])
            impuestos = float(d['impuestos'])
            res_detalle = utilities.calcular_importes(cantidad, precio, impuestos)
            subtotal = res_detalle.get('subtotal', 0.0)
            iva_linea = res_detalle.get('iva', 0.0)
            total_detalle = res_detalle.get('total', subtotal + iva_linea)
            # Redondear el total a 2 decimales para evitar diferencias de 0.01€
            total_detalle = round(total_detalle, 2)
            cursor.execute(
                '''
                INSERT INTO detalle_tickets (
                    id_ticket, concepto, descripcion, cantidad, precio, impuestos, total, productoId
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    ticket_id,
                    d['concepto'],
                    d.get('descripcion', ''),
                    cantidad,
                    precio,
                    impuestos,
                    total_detalle,
                    d.get('productoId', None)
                )
            )

        cursor.execute('UPDATE presupuesto SET estado = ? WHERE id = ?', ('AP', id_presupuesto))

        numerador_actual, _ = actualizar_numerador('T', conn, commit=False)
        if numerador_actual is None:
            conn.rollback()
            return jsonify({'error': 'Error al actualizar el numerador de tickets'}), 500

        conn.commit()

        try:
            generar_datos_verifactu_para_ticket(ticket_id)
        except Exception as vf_exc:
            logger.info(f"[VERIFACTU][WARN] Error generando datos para ticket {ticket_id}: {vf_exc}")

        return jsonify({
            'mensaje': 'Presupuesto convertido a ticket exitosamente',
            'id_presupuesto': id_presupuesto,
            'id_ticket': ticket_id,
            'numero_ticket': numero_ticket,
        })

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error al convertir presupuesto a ticket: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


def generar_pdf_presupuesto(id):
    """Genera un PDF profesional del presupuesto"""
    try:
        from weasyprint import HTML
        import tempfile
        import os
        from datetime import datetime, timedelta
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener datos del presupuesto
        cursor.execute('''
            SELECT p.*, c.razonsocial, c.mail, c.direccion, c.localidad as poblacion, c.provincia, c.cp as codigopostal, c.telf1, c.identificador as nif
            FROM presupuesto p
            LEFT JOIN contactos c ON p.idContacto = c.idContacto
            WHERE p.id = ?
        ''', (id,))
        
        presupuesto_data = cursor.fetchone()
        if not presupuesto_data:
            return jsonify({'error': 'Presupuesto no encontrado'}), 404
            
        presupuesto_dict = dict(presupuesto_data)
        
        # Obtener detalles del presupuesto
        cursor.execute('''
            SELECT * FROM detalle_presupuesto WHERE id_presupuesto = ? ORDER BY id
        ''', (id,))
        
        detalles = [dict(row) for row in cursor.fetchall()]
        
        # Leer plantilla HTML
        with open('/var/www/html/frontend/IMPRIMIR_PRESUPUESTO.html', 'r', encoding='utf-8') as f:
            html_template = f.read()
        
        # Formatear fecha
        try:
            fecha_obj = datetime.strptime(presupuesto_dict['fecha'], '%Y-%m-%d')
            fecha_formateada = fecha_obj.strftime('%d/%m/%Y')
            fecha_validez = (fecha_obj + timedelta(days=30)).strftime('%d/%m/%Y')
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            fecha_formateada = presupuesto_dict['fecha']
            fecha_validez = 'N/A'
        
        # Estados formateados
        estados = {
            'B': 'Borrador',
            'EN': 'Enviado', 
            'AP': 'Aceptado',
            'RJ': 'Rechazado',
            'CD': 'Caducado',
            'F': 'Facturada',
            'T': 'Ticket'
        }
        estado_texto = estados.get(presupuesto_dict.get('estado', 'B'), 'Borrador')
        
        # Calcular totales
        subtotal = sum(float(d['precio']) * int(d['cantidad']) for d in detalles)
        total_iva = sum((float(d['precio']) * int(d['cantidad'])) * (float(d['impuestos']) / 100) for d in detalles)
        total_final = subtotal + total_iva
        
        # Generar filas de detalles (sin columna específica de IVA)
        detalles_html = ""
        for detalle in detalles:
            precio_unitario = float(detalle['precio'])
            cantidad = int(detalle['cantidad'])
            impuestos = float(detalle['impuestos'])
            subtotal_linea = precio_unitario * cantidad
            precio_unitario_fmt = format_number_es_max5(detalle.get('precio'))
            
            detalles_html += f"""
            <tr>
                <td>{detalle['concepto']}</td>
                <td>{detalle['descripcion'] or ''}</td>
                <td style="text-align: center;">{cantidad}</td>
                <td style="text-align: right;">{precio_unitario_fmt}€</td>
                <td style="text-align: right;">{format_currency_es_two(subtotal_linea)}€</td>
            </tr>
            """
        
        # Cargar datos del emisor
        try:
            import json
            with open('/var/www/html/emisor_config.json', 'r', encoding='utf-8') as f:
                emisor_config = json.load(f)
        except Exception as e:
            logger.error(f"Error cargando emisor_config.json: {e}", exc_info=True)
            emisor_config = {
                'nombre': 'ALEPH 70',
                'direccion': 'C/ Ejemplo, 123',
                'cp': '28001',
                'ciudad': 'Madrid',
                'provincia': 'Madrid',
                'email': 'info@aleph70.com',
                'nif': 'B12345678'
            }
        
        # Reemplazar placeholders del emisor (asegurar que no sean None)
        html_content = html_template.replace('{{EMISOR_NOMBRE}}', str(emisor_config.get('nombre', 'ALEPH 70') or 'ALEPH 70'))
        html_content = html_content.replace('{{EMISOR_DIRECCION}}', str(emisor_config.get('direccion', '') or ''))
        html_content = html_content.replace('{{EMISOR_CP}}', str(emisor_config.get('cp', '') or ''))
        html_content = html_content.replace('{{EMISOR_CIUDAD}}', str(emisor_config.get('ciudad', '') or ''))
        html_content = html_content.replace('{{EMISOR_PROVINCIA}}', str(emisor_config.get('provincia', '') or ''))
        html_content = html_content.replace('{{EMISOR_EMAIL}}', str(emisor_config.get('email', '') or ''))
        html_content = html_content.replace('{{EMISOR_NIF}}', str(emisor_config.get('nif', '') or ''))

        # Construir bloque de cliente dinámicamente (solo si hay datos)
        razon = str(presupuesto_dict.get('razonsocial', '') or '')
        direccion = str(presupuesto_dict.get('direccion', '') or '')
        poblacion = str(presupuesto_dict.get('poblacion', '') or '')
        cp = str(presupuesto_dict.get('codigopostal', '') or '')
        provincia = str(presupuesto_dict.get('provincia', '') or '')
        telefono = str(presupuesto_dict.get('telf1', '') or '')
        email = str(presupuesto_dict.get('mail', '') or '')
        # Obtener identificador (NIF/CIF)
        identificador = str(presupuesto_dict.get('identificador', '') or presupuesto_dict.get('nif', '') or '')
        
        hay_cliente = any([razon, direccion, poblacion, cp, provincia, telefono, email, identificador])
        if hay_cliente:
            cliente_html = f"""
        <div class=\"client-info\">
            <div class=\"info-box\">
                <div class=\"info-title\">RAZÓN SOCIAL</div>
                <div style=\"font-weight: bold; font-size: 16px; margin-bottom: 10px;\">{razon}</div>
                <div style=\"color: #666; font-size: 11px; margin-bottom: 3px;\">IDENTIFICADOR</div>
                <div style=\"margin-bottom: 8px;\">{identificador}</div>
                <div style=\"color: #666; font-size: 11px; margin-bottom: 3px;\">DIRECCIÓN</div>
                <div style=\"margin-bottom: 8px;\">{direccion}</div>
                <div style=\"color: #666; font-size: 11px; margin-bottom: 3px;\">CP Y LOCALIDAD</div>
                <div style=\"margin-bottom: 8px;\">{cp} {poblacion}</div>
                <div style=\"color: #666; font-size: 11px; margin-bottom: 3px;\">PROVINCIA</div>
                <div style=\"margin-bottom: 8px;\">{provincia}</div>
            </div>
        </div>
        """
        else:
            cliente_html = ''
        html_content = html_content.replace('{{CLIENTE_HTML}}', cliente_html)
        html_content = html_content.replace('{{NUMERO_PRESUPUESTO}}', presupuesto_dict['numero'])
        html_content = html_content.replace('{{FECHA_PRESUPUESTO}}', fecha_formateada)
        html_content = html_content.replace('{{ESTADO_TEXTO}}', estado_texto)
        html_content = html_content.replace('{{FECHA_VALIDEZ}}', fecha_validez)
        html_content = html_content.replace('{{DETALLES_HTML}}', detalles_html)
        html_content = html_content.replace('{{SUBTOTAL}}', format_currency_es_two(subtotal))
        html_content = html_content.replace('{{TOTAL_IVA}}', format_currency_es_two(total_iva))
        html_content = html_content.replace('{{TOTAL_FINAL}}', format_currency_es_two(total_final))
        
        # Modificar ruta del logo para usar ruta absoluta
        # Obtener logo de la empresa desde la sesión
        empresa_logo = session.get('empresa_logo', 'default_header.png')
        logo_factura = f'/static/logos/{empresa_logo}'
        # Convertir ruta web a ruta absoluta del sistema de archivos
        logo_path = logo_factura.replace('/static/logos/', '/var/www/html/static/logos/')
        html_content = html_content.replace('src="/static/img/logo.png"', f'src="file://{logo_path}"')
        
        # Asegurar ruta absoluta del logo y generar PDF
        pdf_filename = f"presupuesto_{presupuesto_dict['numero']}.pdf"
        temp_pdf_path = f"/tmp/{pdf_filename}"
        
        # Obtener logo de la empresa desde la sesión
        empresa_logo = session.get('empresa_logo', 'default_header.png')
        logo_factura = f'/static/logos/{empresa_logo}'
        # Convertir ruta web a ruta absoluta del sistema de archivos
        logo_path = logo_factura.replace('/static/logos/', '/var/www/html/static/logos/')
        html_content = html_content.replace('src="/static/img/logo.png"', f'src="file://{logo_path}"')
        HTML(string=html_content, base_url='/var/www/html').write_pdf(temp_pdf_path)
        
        # Enviar PDF como respuesta
        from flask import send_file
        return send_file(temp_pdf_path, as_attachment=True, download_name=pdf_filename, mimetype='application/pdf')
        
    except Exception as e:
        logger.error(f"Error al generar PDF del presupuesto: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


def enviar_email_presupuesto(id):
    """Envía el presupuesto por correo electrónico"""
    try:
        from weasyprint import HTML
        import tempfile
        import os
        from datetime import datetime, timedelta
        from email_utils import enviar_presupuesto_por_email
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener datos del presupuesto y contacto
        cursor.execute('''
            SELECT p.*, c.razonsocial, c.mail, c.direccion, c.localidad as poblacion, c.provincia, c.cp as codigopostal, c.telf1, c.identificador as nif
            FROM presupuesto p
            LEFT JOIN contactos c ON p.idContacto = c.idContacto
            WHERE p.id = ?
        ''', (id,))
        
        presupuesto_data = cursor.fetchone()
        if not presupuesto_data:
            return jsonify({'error': 'Presupuesto no encontrado'}), 404
            
        presupuesto_dict = dict(presupuesto_data)
        
        # Verificar que el contacto tenga email
        if not presupuesto_dict.get('mail'):
            return jsonify({'error': 'El contacto no tiene email configurado'}), 400
        
        # Obtener detalles del presupuesto
        cursor.execute('''
            SELECT * FROM detalle_presupuesto WHERE id_presupuesto = ? ORDER BY id
        ''', (id,))
        
        detalles = [dict(row) for row in cursor.fetchall()]
        
        # Generar PDF del presupuesto usando la misma lógica que generar_pdf_presupuesto
        with open('/var/www/html/frontend/IMPRIMIR_PRESUPUESTO.html', 'r', encoding='utf-8') as f:
            html_template = f.read()
        
        # Formatear fecha
        try:
            fecha_obj = datetime.strptime(presupuesto_dict['fecha'], '%Y-%m-%d')
            fecha_formateada = fecha_obj.strftime('%d/%m/%Y')
            fecha_validez = (fecha_obj + timedelta(days=30)).strftime('%d/%m/%Y')
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            fecha_formateada = presupuesto_dict['fecha']
            fecha_validez = 'N/A'
        
        # Estados formateados
        estados = {
            'B': 'Borrador',
            'EN': 'Enviado',
            'AP': 'Aceptado', 
            'RJ': 'Rechazado',
            'CD': 'Caducado',
            'F': 'Facturada',
            'T': 'Ticket'
        }
        estado_texto = estados.get(presupuesto_dict.get('estado', 'B'), 'Borrador')
        
        # Calcular totales
        subtotal = sum(float(d['precio']) * int(d['cantidad']) for d in detalles)
        total_iva = sum((float(d['precio']) * int(d['cantidad'])) * (float(d['impuestos']) / 100) for d in detalles)
        total_final = subtotal + total_iva
        
        # Generar filas de detalles
        detalles_html = ""
        for detalle in detalles:
            precio_unitario = float(detalle['precio'])
            cantidad = int(detalle['cantidad'])
            impuestos = float(detalle['impuestos'])
            # Cálculo correcto: IVA desde subtotal sin redondear
            subtotal_raw = precio_unitario * cantidad
            iva_linea = round(subtotal_raw * (impuestos / 100), 2)
            total_linea = round(subtotal_raw + iva_linea, 2)
            
            detalles_html += f"""
            <tr>
                <td>{detalle['concepto']}</td>
                <td>{detalle['descripcion'] or ''}</td>
                <td style="text-align: center;">{cantidad}</td>
                <td style="text-align: right;">{precio_unitario:.2f}€</td>
                <td style="text-align: center;">{impuestos:.0f}%</td>
                <td style="text-align: right;">{total_linea:.2f}€</td>
            </tr>
            """
        
        # Cargar datos del emisor
        try:
            import json
            with open('/var/www/html/emisor_config.json', 'r', encoding='utf-8') as f:
                emisor_config = json.load(f)
        except Exception as e:
            logger.error(f"Error cargando emisor_config.json: {e}", exc_info=True)
            emisor_config = {
                'nombre': 'ALEPH 70',
                'direccion': 'C/ Ejemplo, 123',
                'cp': '28001',
                'ciudad': 'Madrid',
                'provincia': 'Madrid',
                'email': 'info@aleph70.com',
                'nif': 'B12345678'
            }

        # Reemplazar placeholders del emisor (asegurar que no sean None)
        html_content = html_template.replace('{{EMISOR_NOMBRE}}', str(emisor_config.get('nombre', 'ALEPH 70') or 'ALEPH 70'))
        html_content = html_content.replace('{{EMISOR_DIRECCION}}', str(emisor_config.get('direccion', '') or ''))
        html_content = html_content.replace('{{EMISOR_CP}}', str(emisor_config.get('cp', '') or ''))
        html_content = html_content.replace('{{EMISOR_CIUDAD}}', str(emisor_config.get('ciudad', '') or ''))
        html_content = html_content.replace('{{EMISOR_PROVINCIA}}', str(emisor_config.get('provincia', '') or ''))
        html_content = html_content.replace('{{EMISOR_EMAIL}}', str(emisor_config.get('email', '') or ''))
        html_content = html_content.replace('{{EMISOR_NIF}}', str(emisor_config.get('nif', '') or ''))

        # Construir bloque de cliente dinámicamente (solo si hay datos)
        razon = str(presupuesto_dict.get('razonsocial', '') or '')
        direccion = str(presupuesto_dict.get('direccion', '') or '')
        poblacion = str(presupuesto_dict.get('poblacion', '') or '')
        cp = str(presupuesto_dict.get('codigopostal', '') or '')
        provincia = str(presupuesto_dict.get('provincia', '') or '')
        telefono = str(presupuesto_dict.get('telf1', '') or '')
        email = str(presupuesto_dict.get('mail', '') or '')
        # Obtener identificador (NIF/CIF)
        identificador = str(presupuesto_dict.get('identificador', '') or presupuesto_dict.get('nif', '') or '')
        
        hay_cliente = any([razon, direccion, poblacion, cp, provincia, telefono, email, identificador])
        if hay_cliente:
            cliente_html = f"""
        <div class=\"client-info\"> 
            <div class=\"info-box\">
                <div class=\"info-title\">RAZÓN SOCIAL</div>
                <div style=\"font-weight: bold; font-size: 16px; margin-bottom: 10px;\">{razon}</div>
                <div style=\"color: #666; font-size: 11px; margin-bottom: 3px;\">IDENTIFICADOR</div>
                <div style=\"margin-bottom: 8px;\">{identificador}</div>
                <div style=\"color: #666; font-size: 11px; margin-bottom: 3px;\">DIRECCIÓN</div>
                <div style=\"margin-bottom: 8px;\">{direccion}</div>
                <div style=\"color: #666; font-size: 11px; margin-bottom: 3px;\">CP Y LOCALIDAD</div>
                <div style=\"margin-bottom: 8px;\">{cp} {poblacion}</div>
                <div style=\"color: #666; font-size: 11px; margin-bottom: 3px;\">PROVINCIA</div>
                <div style=\"margin-bottom: 8px;\">{provincia}</div>
            </div>
        </div>
        """
        else:
            cliente_html = ''
        html_content = html_content.replace('{{CLIENTE_HTML}}', cliente_html)

        # Rellenar datos del documento
        html_content = html_content.replace('{{NUMERO_PRESUPUESTO}}', presupuesto_dict['numero'])
        html_content = html_content.replace('{{FECHA_PRESUPUESTO}}', fecha_formateada)
        html_content = html_content.replace('{{ESTADO_TEXTO}}', estado_texto)
        html_content = html_content.replace('{{FECHA_VALIDEZ}}', fecha_validez)
        html_content = html_content.replace('{{DETALLES_HTML}}', detalles_html)
        html_content = html_content.replace('{{SUBTOTAL}}', format_currency_es_two(subtotal))
        html_content = html_content.replace('{{TOTAL_IVA}}', format_currency_es_two(total_iva))
        html_content = html_content.replace('{{TOTAL_FINAL}}', format_currency_es_two(total_final))

        # Asegurar ruta absoluta del logo
        # Obtener logo de la empresa desde la sesión
        empresa_logo = session.get('empresa_logo', 'default_header.png')
        logo_factura = f'/static/logos/{empresa_logo}'
        # Convertir ruta web a ruta absoluta del sistema de archivos
        logo_path = logo_factura.replace('/static/logos/', '/var/www/html/static/logos/')
        html_content = html_content.replace('src="/static/img/logo.png"', f'src="file://{logo_path}"')

        # Generar PDF temporal
        pdf_filename = f"presupuesto_{presupuesto_dict['numero']}.pdf"
        temp_pdf_path = f"/tmp/{pdf_filename}"
        
        HTML(string=html_content, base_url='/var/www/html').write_pdf(temp_pdf_path)
        
        # Preparar email
        asunto = f"Presupuesto {presupuesto_dict['numero']} - {presupuesto_dict['razonsocial']}"
        cuerpo = f"""Estimado/a cliente,

Adjuntamos el presupuesto {presupuesto_dict['numero']} por un importe total de {total_final:.2f}€.

Este presupuesto tiene una validez de 30 días desde la fecha de emisión.

Si tiene cualquier consulta, no dude en contactarnos.

Saludos cordiales.
ALEPH 70"""
        
        # Enviar email
        exito, mensaje = enviar_presupuesto_por_email(
            presupuesto_dict['mail'],
            asunto,
            cuerpo,
            temp_pdf_path,
            presupuesto_dict['numero']
        )
        
        # Limpiar archivo PDF temporal
        os.unlink(temp_pdf_path)
        
        if exito:
            return jsonify({'message': f'Presupuesto enviado correctamente a {presupuesto_dict["mail"]}'})
        else:
            return jsonify({'error': mensaje}), 500
        
    except Exception as e:
        logger.error(f"Error al enviar email del presupuesto: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

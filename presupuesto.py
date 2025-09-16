import sqlite3
from datetime import datetime, timedelta

from flask import Flask, jsonify, request

from db_utils import (
    actualizar_numerador,
    formatear_numero_documento,
    get_db_connection,
    obtener_numerador,
    redondear_importe,
)

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
        print(f"Error en _verificar_numero_presupuesto_local: {e}")
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
        print("[PRESUPUESTO] Datos recibidos en crear_presupuesto:", data)
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
                numero, fecha, estado, idContacto, nif, total, formaPago,
                importe_bruto, importe_impuestos, importe_cobrado, timestamp, tipo
            ) VALUES (?, ?, 'B', ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['numero'],
                data['fecha'],
                data.get('idContacto'),
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
        print(f"Error en crear_presupuesto: {str(e)}")
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

        detalles = cursor.execute(
            'SELECT * FROM detalle_presupuesto WHERE id_presupuesto = ? ORDER BY id', (id,)
        ).fetchall()

        resultado = dict(presupuesto)
        resultado['detalles'] = [dict(detalle) for detalle in detalles]
        
        # Buscar datos del contacto si existe idContacto (con C mayúscula)
        print(f"[DEBUG] idContacto en presupuesto: {resultado.get('idContacto')}")
        if resultado.get('idContacto'):
            contacto = cursor.execute(
                'SELECT * FROM contactos WHERE idContacto = ?', (resultado['idContacto'],)
            ).fetchone()
            print(f"[DEBUG] Contacto encontrado: {contacto}")
            if contacto:
                resultado['contacto'] = dict(contacto)
                print(f"[DEBUG] Contacto añadido al resultado: {dict(contacto)}")
            else:
                print(f"[DEBUG] No se encontró contacto con idContacto: {resultado['idContacto']}")
        else:
            print("[DEBUG] No hay idContacto en el presupuesto")
        
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
            SET numero = ?, fecha = ?, estado = ?, idContacto = ?, nif = ?, total = ?, formaPago = ?,
                importe_bruto = ?, importe_impuestos = ?, importe_cobrado = ?, timestamp = ?, tipo = ?
            WHERE id = ?
            ''', (
                data['numero'],
                data['fecha'],
                data.get('estado', 'B'),
                data.get('idContacto'),
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
        print(f"Error al actualizar presupuesto {id}: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


def obtener_presupuesto_abierto(idContacto):
    try:
        conn = get_db_connection()
        conn.execute('PRAGMA busy_timeout = 10000')
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM contactos WHERE idContacto = ?', (idContacto,))
        contacto = cursor.fetchone()
        if not contacto:
            return jsonify({'error': 'Contacto no encontrado'}), 404
        contacto_dict = dict(contacto)

        sql = '''
            SELECT p.id, p.numero, p.fecha, p.estado, p.tipo, p.total, p.idcontacto
            FROM presupuesto p
            WHERE p.idcontacto = ? AND p.estado = 'B'
            ORDER BY p.fecha DESC, p.id DESC
            LIMIT 1
        '''
        cursor.execute(sql, (idContacto,))
        presupuesto = cursor.fetchone()

        if presupuesto:
            presupuesto_dict = dict(presupuesto)
            cursor.execute('''
                SELECT id, concepto, descripcion, cantidad, precio, impuestos, total,
                       formaPago, productoId, fechaDetalle
                FROM detalle_presupuesto
                WHERE id_presupuesto = ?
                ORDER BY id
            ''', (presupuesto_dict['id'],))
            detalles = cursor.fetchall()
            return jsonify({
                'modo': 'edicion',
                'id': presupuesto_dict['id'],
                'numero': presupuesto_dict['numero'],
                'fecha': presupuesto_dict['fecha'],
                'estado': presupuesto_dict['estado'],
                'tipo': presupuesto_dict.get('tipo', 'N'),
                'total': presupuesto_dict['total'],
                'contacto': {
                    'idContacto': contacto_dict['idContacto'],
                    'razonsocial': contacto_dict['razonsocial'],
                    'identificador': contacto_dict['identificador'],
                    'direccion': contacto_dict['direccion'],
                    'cp': contacto_dict['cp'],
                    'localidad': contacto_dict['localidad'],
                    'provincia': contacto_dict['provincia'],
                },
                'detalles': [dict(d) for d in detalles],
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
            print(f"[CONSULTA_PRESUPUESTOS][ARGS] fecha_inicio={fecha_inicio}, fecha_fin={fecha_fin}, estado='{estado}', numero='{numero}', contacto='{contacto}', identificador='{identificador}', concepto='{concepto}'")
        except Exception:
            pass

        hay_filtros_adicionales = any([
            estado.strip(), numero.strip(), contacto.strip(), identificador.strip(), concepto.strip()
        ])

        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
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
                p.idcontacto,
                c.razonsocial
            FROM presupuesto p
            LEFT JOIN contactos c ON p.idcontacto = c.idContacto
            WHERE 1=1
        """
        params = []

        if fecha_inicio and (not hay_filtros_adicionales):
            query += " AND p.fecha >= ?"
            params.append(fecha_inicio)
        if fecha_fin and (not hay_filtros_adicionales):
            query += " AND p.fecha <= ?"
            params.append(fecha_fin)
        if estado:
            query += " AND p.estado = ?"
            params.append(estado)
        else:
            query += " AND p.estado <> 'A0'"
        if numero:
            query += " AND p.numero LIKE ?"
            params.append(f"%{numero}%")
        if contacto:
            query += " AND c.razonsocial LIKE ?"
            params.append(f"%{contacto}%")
        if identificador:
            query += " AND c.identificador LIKE ?"
            params.append(f"%{identificador}%")
        if concepto:
            query += " AND EXISTS (SELECT 1 FROM detalle_presupuesto d WHERE d.id_presupuesto = p.id AND (lower(d.concepto) LIKE ? OR lower(d.descripcion) LIKE ?))"
            like_val = f"%{concepto.lower()}%"
            params.extend([like_val, like_val])

        query += " ORDER BY p.fecha DESC LIMIT 100"

        try:
            print("[CONSULTA_PRESUPUESTOS][SQL]", query, "PARAMS", params)
        except Exception:
            pass

        cursor.execute(query, params)
        items = cursor.fetchall()

        columnas = [desc[0] for desc in cursor.description]
        result = []
        for row in items:
            item = dict(zip(columnas, row))
            for k in ('base', 'iva', 'importe_cobrado', 'total'):
                if k in item and item[k] is not None:
                    item[k] = float(item[k])
            result.append(item)

        return jsonify(result)

    except Exception as e:
        print(f"Error en consultar_presupuestos: {str(e)}")
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
                numero, fecha, fvencimiento, estado, idContacto, nif, total, formaPago,
                importe_bruto, importe_impuestos, importe_cobrado, timestamp, tipo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                numero_formateado,
                datetime.now().strftime('%Y-%m-%d'),
                (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d'),
                'P',
                pres['idContacto'],
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

        cursor.execute('UPDATE presupuesto SET estado = ? WHERE id = ?', ('F', id_presupuesto))

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
        print(f"Error al convertir presupuesto a factura: {str(e)}")
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
            importe_bruto = redondear_importe(sum(float(d['precio']) * int(d['cantidad']) for d in detalles_pres))
            importe_impuestos = redondear_importe(sum((float(d['precio']) * int(d['cantidad'])) * (float(d['impuestos']) / 100) for d in detalles_pres))
            total_ticket = redondear_importe(float(pres['total'])) if pres['total'] else redondear_importe(importe_bruto + importe_impuestos)
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
                total_ticket,
                total_ticket,
                datetime.now().isoformat(),
                'C',
                pres['formaPago'],
                pres['tipo']
            )
        )
        ticket_id = cursor.lastrowid

        for d in detalles_pres:
            cantidad = float(d['cantidad'])
            precio = float(d['precio'])
            impuestos = float(d['impuestos'])
            subtotal = cantidad * precio
            total_detalle = redondear_importe(subtotal * (1 + impuestos / 100))
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

        cursor.execute('UPDATE presupuesto SET estado = ? WHERE id = ?', ('T', id_presupuesto))

        numerador_actual, _ = actualizar_numerador('T', conn, commit=False)
        if numerador_actual is None:
            conn.rollback()
            return jsonify({'error': 'Error al actualizar el numerador de tickets'}), 500

        conn.commit()

        try:
            generar_datos_verifactu_para_ticket(ticket_id)
        except Exception as vf_exc:
            print(f"[VERIFACTU][WARN] Error generando datos para ticket {ticket_id}: {vf_exc}")

        return jsonify({
            'mensaje': 'Presupuesto convertido a ticket exitosamente',
            'id_presupuesto': id_presupuesto,
            'id_ticket': ticket_id,
            'numero_ticket': numero_ticket,
        })

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error al convertir presupuesto a ticket: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

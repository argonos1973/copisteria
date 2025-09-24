import sqlite3
from datetime import datetime, timedelta

from flask import Blueprint, Flask, jsonify, request, send_file
import utilities
from db_utils import (
    actualizar_numerador,
    formatear_numero_documento,
    get_db_connection,
    obtener_numerador,
    redondear_importe,
)

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
        
        # Buscar datos del contacto si existe idcontacto (minúscula)
        print(f"[DEBUG] idcontacto en presupuesto: {resultado.get('idcontacto')}")
        if resultado.get('idcontacto'):
            contacto = cursor.execute(
                'SELECT * FROM contactos WHERE idContacto = ?', (resultado['idcontacto'],)
            ).fetchone()
            print(f"[DEBUG] Contacto encontrado: {contacto}")
            if contacto:
                resultado['contacto'] = dict(contacto)
                print(f"[DEBUG] Contacto añadido al resultado: {dict(contacto)}")
            else:
                print(f"[DEBUG] No se encontró contacto con idcontacto: {resultado['idcontacto']}")
        else:
            print("[DEBUG] No hay idcontacto en el presupuesto")
        
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
        print(f"Error al actualizar presupuesto {id}: {str(e)}")
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
            SELECT p.id, p.numero, p.fecha, p.estado, p.tipo, p.total, p.idcontacto
            FROM presupuesto p
            WHERE p.idcontacto = ? AND p.estado = 'B'
            ORDER BY p.fecha DESC, p.id DESC
            LIMIT 1
        '''
        cursor.execute(sql, (idcontacto,))
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

        sql = """
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
                c.razonsocial,
                c.mail
            FROM presupuesto p
            LEFT JOIN contactos c ON p.idcontacto = c.idContacto
            WHERE 1=1
        """
        params = []

        if fecha_inicio and (not hay_filtros_adicionales):
            sql += " AND p.fecha >= ?"
            params.append(fecha_inicio)
        if fecha_fin and (not hay_filtros_adicionales):
            sql += " AND p.fecha <= ?"
            params.append(fecha_fin)
        if estado:
            sql += " AND p.estado = ?"
            params.append(estado)
        else:
            sql += " AND p.estado <> 'A0'"
        if numero:
            sql += " AND p.numero LIKE ?"
            params.append(f"%{numero}%")
        if contacto:
            sql += " AND c.razonsocial LIKE ?"
            params.append(f"%{contacto}%")
        if identificador:
            sql += " AND c.identificador LIKE ?"
            params.append(f"%{identificador}%")
        if concepto:
            sql += " AND EXISTS (SELECT 1 FROM detalle_presupuesto dp WHERE dp.id_presupuesto = p.id AND dp.concepto LIKE ?)"
            params.append(f"%{concepto}%")

        sql += " ORDER BY p.fecha DESC LIMIT 100"

        try:
            print("[CONSULTA_PRESUPUESTOS][SQL]", sql, "PARAMS", params)
        except Exception:
            pass

        cursor.execute(sql, params)
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
                total_ticket,
                total_ticket,
                datetime.now().isoformat(),
                'C',
                pres['formaPago'],
                pres['tipo']
            )
        )
        ticket_id = cursor.lastrowid

        for d in detalles_dict:
            cantidad = float(d['cantidad'])
            precio = float(d['precio'])
            impuestos = float(d['impuestos'])
            subtotal = cantidad * precio
            iva_linea = subtotal * (impuestos / 100)
            total_detalle = redondear_importe(subtotal + iva_linea)
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
            LEFT JOIN contactos c ON p.idcontacto = c.idContacto
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
        except:
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
            subtotal_linea = precio_unitario * cantidad
            iva_linea = subtotal_linea * (impuestos / 100)
            total_linea = subtotal_linea + iva_linea
            
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
            print(f"Error cargando emisor_config.json: {e}")
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
        hay_cliente = any([razon, direccion, poblacion, cp, provincia, telefono, email])
        if hay_cliente:
            cliente_html = f"""
        <div class=\"client-info\">
            <div class=\"info-box\">
                <div class=\"info-title\">DATOS DEL CLIENTE</div>
                <div><strong>{razon}</strong></div>
                <div>{direccion}</div>
                <div>{poblacion} {cp}</div>
                <div>{provincia}</div>
                <div>Tel: {telefono}</div>
                <div>Email: {email}</div>
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
        html_content = html_content.replace('{{SUBTOTAL}}', f"{subtotal:.2f}")
        html_content = html_content.replace('{{TOTAL_IVA}}', f"{total_iva:.2f}")
        html_content = html_content.replace('{{TOTAL_FINAL}}', f"{total_final:.2f}")
        
        # Modificar ruta del logo para usar ruta absoluta
        html_content = html_content.replace('src="/static/img/logo.png"', 'src="file:///var/www/html/static/img/logo.png"')
        
        # Asegurar ruta absoluta del logo y generar PDF
        pdf_filename = f"presupuesto_{presupuesto_dict['numero']}.pdf"
        temp_pdf_path = f"/tmp/{pdf_filename}"
        
        html_content = html_content.replace('src="/static/img/logo.png"', 'src="file:///var/www/html/static/img/logo.png"')
        HTML(string=html_content, base_url='/var/www/html').write_pdf(temp_pdf_path)
        
        # Enviar PDF como respuesta
        from flask import send_file
        return send_file(temp_pdf_path, as_attachment=True, download_name=pdf_filename, mimetype='application/pdf')
        
    except Exception as e:
        print(f"Error al generar PDF del presupuesto: {str(e)}")
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
            LEFT JOIN contactos c ON p.idcontacto = c.idContacto
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
        except:
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
            subtotal_linea = precio_unitario * cantidad
            iva_linea = subtotal_linea * (impuestos / 100)
            total_linea = subtotal_linea + iva_linea
            
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
            print(f"Error cargando emisor_config.json: {e}")
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
        hay_cliente = any([razon, direccion, poblacion, cp, provincia, telefono, email])
        if hay_cliente:
            cliente_html = f"""
        <div class=\"client-info\"> 
            <div class=\"info-box\">
                <div class=\"info-title\">DATOS DEL CLIENTE</div>
                <div><strong>{razon}</strong></div>
                <div>{direccion}</div>
                <div>{poblacion} {cp}</div>
                <div>{provincia}</div>
                <div>Tel: {telefono}</div>
                <div>Email: {email}</div>
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
        html_content = html_content.replace('{{SUBTOTAL}}', f"{subtotal:.2f}")
        html_content = html_content.replace('{{TOTAL_IVA}}', f"{total_iva:.2f}")
        html_content = html_content.replace('{{TOTAL_FINAL}}', f"{total_final:.2f}")

        # Asegurar ruta absoluta del logo
        html_content = html_content.replace('src="/static/img/logo.png"', 'src="file:///var/www/html/static/img/logo.png"')

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
        print(f"Error al enviar email del presupuesto: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

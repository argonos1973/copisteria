import sqlite3
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from format_utils import format_currency_es_two, format_total_es_two, format_number_es_max5, format_percentage

from flask import Flask, jsonify, request

from db_utils import (actualizar_numerador, formatear_numero_documento,
                      get_db_connection, obtener_numerador, redondear_importe,
                      verificar_numero_proforma)
import utilities

app = Flask(__name__)
    try:
        return Decimal(str(val).replace(',', '.'))
    except Exception:
        return Decimal(default)


def _formatear_detalle_proforma(detalle_row):
    det_dict = dict(detalle_row)
    det_dict['cantidad'] = format_number_es_max5(det_dict.get('cantidad'))
    det_dict['precio'] = format_number_es_max5(det_dict.get('precio'))
    det_dict['impuestos'] = format_number_es_max5(det_dict.get('impuestos'))
    det_dict['total'] = format_currency_es_two(det_dict.get('total'))
    return det_dict


def _obtener_detalles_formateados(cursor, proforma_id):
    detalles_rows = cursor.execute(
        'SELECT * FROM detalle_proforma WHERE id_proforma = ? ORDER BY id', (proforma_id,)
    ).fetchall()
    return [_formatear_detalle_proforma(row) for row in detalles_rows]


def _formatear_importes_proforma(data):
    for key in ('importe_bruto', 'importe_impuestos', 'importe_cobrado', 'total'):
        if key in data:
            data[key] = format_currency_es_two(data.get(key))
    return data

def crear_proforma():
    conn = None
    try:
        data = request.get_json()
        print("Datos recibidos en crear_proforma:", data)
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400

        # Verificar si ya existe una proforma con el mismo número
        verificacion = verificar_numero_proforma(data['numero'])
        if isinstance(verificacion, tuple):
            return verificacion  # Error desde la función
        if verificacion.json['existe']:
            return jsonify({'error': 'Ya existe una proforma con este número'}), 400

        conn = get_db_connection()
        conn.execute('PRAGMA busy_timeout = 10000')
        conn.execute('BEGIN TRANSACTION')
        cursor = conn.cursor()

        # Si es una actualización (tiene ID válido), no verificamos el numerador
        es_actualizacion = 'id' in data and data['id'] is not None and data['id'] != 0
        print(f"Es actualización: {es_actualizacion}, ID: {data.get('id')}")
        print(f"Keys en data: {data.keys()}")
        
       
        # Calculate amounts using unified function
        importe_bruto = 0
        importe_impuestos = 0
        total = 0
        
        for detalle in data['detalles']:
            res = utilities.calcular_importes(detalle['cantidad'], detalle['precio'], detalle['impuestos'])
            importe_bruto += res['subtotal']
            importe_impuestos += res['iva']
            total += res['total']
            # Update detalle with calculated values
            detalle['total'] = res['total']
        
        # Update data with calculated totals
        data['importe_bruto'] = importe_bruto
        data['importe_impuestos'] = importe_impuestos
        data['total'] = total
        
        # Insertar la proforma
        cursor.execute('''
            INSERT INTO proforma (numero, fecha, estado, idContacto, nif, total, formaPago, 
                                importe_bruto, importe_impuestos, importe_cobrado, timestamp, tipo)
            VALUES (?, ?, 'A', ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['numero'],
            data['fecha'],
            data['idContacto'],
            data.get('nif', ''),
            data['total'],
            data.get('formaPago', 'E'),
            data.get('importe_bruto', 0),
            data.get('importe_impuestos', 0),
            data.get('importe_cobrado', 0),
            datetime.now().isoformat(),
            data.get('tipo', 'N')  # Por defecto, tipo 'N' si no se especifica
        ))
        
        proforma_id = cursor.lastrowid
        print(f"Proforma creada con ID: {proforma_id}")

        # Insertar los detalles
        for detalle in data['detalles']:
            cursor.execute('''
                INSERT INTO detalle_proforma (id_proforma, concepto, descripcion, cantidad, 
                                            precio, impuestos, total, formaPago, productoId, fechaDetalle)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                proforma_id,
                detalle['concepto'],
                detalle.get('descripcion', ''),
                detalle['cantidad'],
                detalle['precio'],
                detalle['impuestos'],
                detalle['total'],
                detalle.get('formaPago', 'E'),
                detalle.get('productoId', None),
                detalle.get('fechaDetalle', data['fecha'])
            ))

        if not es_actualizacion:
            try:
                # Actualizar el numerador usando la nueva función
                numerador_actual, _ = actualizar_numerador('P', conn, commit=False)
                if numerador_actual is None:
                    conn.rollback()
                    return jsonify({"error": "Error al actualizar el numerador"}), 500
            except Exception as e:
                conn.rollback()
                return jsonify({"error": f"Error al actualizar numerador: {str(e)}"}), 500

        conn.commit()
        return jsonify({
            'mensaje': 'Proforma creada exitosamente',
            'id': proforma_id
        })

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error en crear_proforma: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


def obtener_proforma(id):
    conn = None
    try:
        conn = get_db_connection()
        conn.execute('PRAGMA busy_timeout = 10000')
        cursor = conn.cursor()

        proforma = cursor.execute('SELECT * FROM proforma WHERE id = ?', (id,)).fetchone()
        if not proforma:
            return jsonify({'error': 'Proforma no encontrada'}), 404

        resultado = _formatear_importes_proforma(dict(proforma))
        resultado['detalles'] = _obtener_detalles_formateados(cursor, id)

        if resultado.get('idcontacto'):
            contacto = cursor.execute(
                'SELECT * FROM contactos WHERE idContacto = ?', (resultado['idcontacto'],)
            ).fetchone()
            if contacto:
                resultado['contacto'] = dict(contacto)

        return jsonify(resultado)

    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        if conn:
            conn.close()



def obtener_proforma_abierta(idContacto):
    try:
        print(f"Iniciando obtener_proforma_abierta para idContacto: {idContacto}")
        conn = get_db_connection()
        conn.execute('PRAGMA busy_timeout = 10000')
        cursor = conn.cursor()
        
        # Primero obtener los datos del contacto
        print("Ejecutando consulta de contacto...")
        cursor.execute('SELECT * FROM contactos WHERE idContacto = ?', (idContacto,))
        contacto = cursor.fetchone()
        
        if not contacto:
            print(f"No se encontró el contacto con idContacto: {idContacto}")
            return jsonify({'error': 'Contacto no encontrado'}), 404
            
        contacto_dict = dict(contacto)
        print(f"Datos del contacto encontrados: {contacto_dict}")
        
        # Buscar proforma abierta
        print("Ejecutando consulta de proforma abierta...")
        sql = '''
            SELECT p.id, p.numero, p.fecha, p.estado, p.tipo, p.total, p.idcontacto
            FROM proforma p
            WHERE p.idcontacto = ? 
            AND p.estado = 'A'
            ORDER BY p.fecha DESC, p.id DESC
            LIMIT 1
        '''
        print(f"SQL proforma: {sql}")
        print(f"Parámetros: idContacto = {idContacto}")
        
        cursor.execute(sql, (idContacto,))
        proforma = cursor.fetchone()
        
        if proforma:
            print(f"Proforma abierta encontrada: {dict(proforma)}")
            proforma_dict = _formatear_importes_proforma(dict(proforma))

            detalles = _obtener_detalles_formateados(cursor, proforma_dict['id'])
            print(f"Detalles formateados: {detalles}")

            response_data = {
                'modo': 'edicion',
                'id': proforma_dict['id'],
                'numero': proforma_dict['numero'],
                'fecha': proforma_dict['fecha'],
                'estado': proforma_dict['estado'],
                'tipo': proforma_dict['tipo'],
                'total': proforma_dict.get('total'),
                'contacto': {
                    'idContacto': contacto_dict['idContacto'],
                    'razonsocial': contacto_dict['razonsocial'],
                    'identificador': contacto_dict['identificador'],
                    'direccion': contacto_dict['direccion'],
                    'cp': contacto_dict['cp'],
                    'localidad': contacto_dict['localidad'],
                    'provincia': contacto_dict['provincia']
                },
                'detalles': detalles
            }
            print("Enviando respuesta modo edición")
            return jsonify(response_data)
        else:
            print("No se encontró proforma abierta, modo nuevo")
            return jsonify({
                'modo': 'nuevo',
                'contacto': {
                    'idContacto': contacto_dict['idContacto'],
                    'razonsocial': contacto_dict['razonsocial'],
                    'identificador': contacto_dict['identificador'],
                    'direccion': contacto_dict['direccion'],
                    'cp': contacto_dict['cp'],
                    'localidad': contacto_dict['localidad'],
                    'provincia': contacto_dict['provincia']
                }
            })
    
    except sqlite3.Error as e:
        print(f"Error de SQLite en obtener_proforma_abierta: {str(e)}")
        return jsonify({'error': f"Error de base de datos: {str(e)}"}), 500
            
    except Exception as e:
        print(f"Error general en obtener_proforma_abierta: {str(e)}")
        print(f"Tipo de error: {type(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f"Error al buscar proforma abierta: {str(e)}"}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
        print("Conexión cerrada en obtener_proforma_abierta")

def listar_proformas():
    """
    Lista las proformas aplicando los filtros especificados.
    """
    try:
        conn = get_db_connection()
        conn.execute('PRAGMA busy_timeout = 10000')
        cursor = conn.cursor()
        
        # Obtener parámetros de la solicitud
        id_contacto = request.args.get('idContacto')
        estado = request.args.get('estado')
        
        # Construir la consulta base
        sql = '''
            SELECT p.*, c.razonSocial as razon_social_contacto, c.identificador as nif
            FROM proforma p
            LEFT JOIN contactos c ON p.idContacto = c.id
            WHERE 1=1
        '''
        params = []
        
        # Añadir filtros según los parámetros recibidos
        if id_contacto:
            sql += ' AND p.idContacto = ?'
            params.append(id_contacto)
            
        if estado:
            sql += ' AND p.estado = ?'
            params.append(estado)

        sql += " ORDER BY p.fecha DESC"
        
        cursor.execute(sql, params)
        proformas = cursor.fetchall()
        return jsonify([dict(proforma) for proforma in proformas])
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

def consultar_proformas():
    try:
        # Obtener parámetros de la consulta
        fecha_inicio = request.args.get('fecha_inicio', '')
        fecha_fin = request.args.get('fecha_fin', '')
        estado = request.args.get('estado', '')
        numero = request.args.get('numero', '')
        contacto = request.args.get('contacto', '')
        identificador = request.args.get('identificador', '')

        # Comprobar si hay algún filtro adicional informado
        hay_filtros_adicionales = any([
            estado.strip(), 
            numero.strip(), 
            contacto.strip(), 
            identificador.strip()
        ])

        conn = get_db_connection()
        conn.execute('PRAGMA busy_timeout = 10000')
        cursor = conn.cursor()

        # Construir la consulta base
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
                p.idcontacto AS idContacto,
                c.razonsocial
            FROM proforma p
            LEFT JOIN contactos c ON p.idcontacto = c.idContacto
            WHERE 1=1
        """
        params = []

        # Añadir filtros según los parámetros recibidos
        if fecha_inicio and not hay_filtros_adicionales:
            query += " AND p.fecha >= ?"
            params.append(fecha_inicio)
        if fecha_fin and not hay_filtros_adicionales:
            query += " AND p.fecha <= ?"
            params.append(fecha_fin)
        if estado:
            query += " AND p.estado = ?"
            params.append(estado)
        if numero:
            query += " AND p.numero LIKE ?"
            params.append(f"%{numero}%")
        if contacto:
            query += " AND c.razonsocial LIKE ?"
            params.append(f"%{contacto}%")
        if identificador:
            query += " AND c.identificador LIKE ?"
            params.append(f"%{identificador}%")

        # Ordenar por fecha descendente
        query += " ORDER BY p.fecha DESC"

        # Ejecutar la consulta
        cursor.execute(query, params)
        proformas = cursor.fetchall()

        # Convertir los resultados a una lista de diccionarios formateados
        result = []
        for proforma in proformas:
            row = dict(proforma) if isinstance(proforma, sqlite3.Row) else {
                'id': proforma[0],
                'fecha': proforma[1],
                'numero': proforma[2],
                'estado': proforma[3],
                'tipo': proforma[4],
                'base': proforma[5],
                'iva': proforma[6],
                'importe_cobrado': proforma[7],
                'total': proforma[8],
                'idContacto': proforma[9],
                'razonsocial': proforma[10]
            }

            result.append({
                'id': row.get('id'),
                'fecha': row.get('fecha'),
                'numero': row.get('numero'),
                'estado': row.get('estado'),
                'tipo': row.get('tipo'),
                'base': format_currency_es_two(row.get('base')),
                'iva': format_currency_es_two(row.get('iva')),
                'importe_cobrado': format_currency_es_two(row.get('importe_cobrado')),
                'total': format_currency_es_two(row.get('total')),
                'idcontacto': row.get('idContacto', row.get('idcontacto')),
                'razonsocial': row.get('razonsocial')
            })

        # Calcular totales globales según el estado del filtro
        totales_globales = {
            'total_base': '0,00',
            'total_iva': '0,00',
            'total_cobrado': '0,00',
            'total_total': '0,00'
        }
        
        # Solo calcular totales si hay un estado específico en el filtro
        if estado:
            totales_query = """
                SELECT 
                    SUM(p.importe_bruto) as total_base,
                    SUM(p.importe_impuestos) as total_iva,
                    SUM(p.importe_cobrado) as total_cobrado,
                    SUM(p.total) as total_total
                FROM proforma p
                LEFT JOIN contactos c ON p.idcontacto = c.idContacto
                WHERE 1=1
            """
            
            # Aplicar los mismos filtros que en la consulta principal
            totales_params = []
            if fecha_inicio and not hay_filtros_adicionales:
                totales_query += " AND p.fecha >= ?"
                totales_params.append(fecha_inicio)
            if fecha_fin and not hay_filtros_adicionales:
                totales_query += " AND p.fecha <= ?"
                totales_params.append(fecha_fin)
            if estado:
                totales_query += " AND p.estado = ?"
                totales_params.append(estado)
            if numero:
                totales_query += " AND p.numero LIKE ?"
                totales_params.append(f"%{numero}%")
            if contacto:
                totales_query += " AND c.razonsocial LIKE ?"
                totales_params.append(f"%{contacto}%")
            if identificador:
                totales_query += " AND c.identificador LIKE ?"
                totales_params.append(f"%{identificador}%")
            
            cursor.execute(totales_query, totales_params)
            totales_row = cursor.fetchone()

            if totales_row:
                if isinstance(totales_row, sqlite3.Row):
                    total_base = totales_row['total_base'] or 0
                    total_iva = totales_row['total_iva'] or 0
                    total_cobrado = totales_row['total_cobrado'] or 0
                    total_total = totales_row['total_total'] or 0
                else:
                    total_base = totales_row[0] or 0
                    total_iva = totales_row[1] or 0
                    total_cobrado = totales_row[2] or 0
                    total_total = totales_row[3] or 0

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
        import traceback
        print(f"Error en consultar_proformas: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

def convertir_proforma_a_factura(id_proforma):
    """
    Convierte una proforma existente en una factura.
    """
    conn = None
    try:
        conn = get_db_connection()
        conn.execute('PRAGMA busy_timeout = 10000')
        conn.execute('BEGIN TRANSACTION')
        cursor = conn.cursor()
        
        # Verificar si la proforma existe
        cursor.execute('SELECT * FROM proforma WHERE id = ?', (id_proforma,))
        proforma = cursor.fetchone()
        
        if not proforma:
            conn.rollback()
            return jsonify({'error': 'Proforma no encontrada'}), 404
        
        # Verificar si la proforma ya está facturada
        if proforma['estado'] == 'F':
            conn.rollback()
            return jsonify({'error': 'Esta proforma ya ha sido facturada'}), 400
        
        # Obtener el siguiente número de factura
        numerador, prefijo = obtener_numerador('F')
        if numerador is None:
            conn.rollback()
            return jsonify({'error': 'Error al obtener el numerador de facturas'}), 500
        
        prefijo = 'F'
        # formatear_numero_documento devuelve NNNN (padded). Construir F+AA+NNNN
        numero_core = formatear_numero_documento('F', conn)
        anno = datetime.now().year % 100
        numero_formateado = f"{prefijo}{anno:02}{numero_core}"
        
        # Obtener los detalles de la proforma
        cursor.execute('SELECT * FROM detalle_proforma WHERE id_proforma = ?', (id_proforma,))
        detalles_proforma = cursor.fetchall()
        
        # Crear la factura
        cursor.execute('''
            INSERT INTO factura (
                numero, fecha, fvencimiento, estado, idContacto, nif, total, formaPago, 
                importe_bruto, importe_impuestos, importe_cobrado, timestamp, tipo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            numero_formateado,
            datetime.now().strftime('%Y-%m-%d'), (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d'),  # Fecha actual y vencimiento a 15 días
            'P',  # Estado Pendiente
            proforma['idContacto'],
            proforma['nif'],
            proforma['total'],
            proforma['formaPago'],
            proforma['importe_bruto'],
            proforma['importe_impuestos'],
            proforma['importe_cobrado'],
            datetime.now().isoformat(),
            proforma['tipo']  # Transferir el tipo de la proforma a la factura
        ))
        
        factura_id = cursor.lastrowid
        
        # Insertar los detalles de la factura
        for detalle in detalles_proforma:
            cursor.execute('''
                INSERT INTO detalle_factura (
                    id_factura, concepto, descripcion, cantidad, precio, 
                    impuestos, total, productoId, fechaDetalle
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                factura_id,
                detalle['concepto'],
                detalle['descripcion'],
                detalle['cantidad'],
                detalle['precio'],
                detalle['impuestos'],
                detalle['total'],
                detalle['productoId'],
                detalle['fechaDetalle']
            ))
        
        # Actualizar el estado de la proforma a 'Facturada'
        cursor.execute('UPDATE proforma SET estado = ? WHERE id = ?', ('F', id_proforma))
        
        # Actualizar el numerador de facturas
        numerador_actual, _ = actualizar_numerador('F', conn, commit=False)
        if numerador_actual is None:
            conn.rollback()
            return jsonify({'error': 'Error al actualizar el numerador de facturas'}), 500
        
        conn.commit()
        
        return jsonify({
            'mensaje': 'Proforma convertida a factura exitosamente',
            'id_proforma': id_proforma,
            'id_factura': factura_id,
            'numero_factura': numero_formateado
        })
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error al convertir proforma a factura: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

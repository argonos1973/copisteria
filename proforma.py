import sqlite3
from datetime import datetime, timedelta

from flask import Flask, jsonify, request

from db_utils import (actualizar_numerador, formatear_numero_documento,
                      get_db_connection, obtener_numerador, redondear_importe,
                      verificar_numero_proforma)

app = Flask(__name__)

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
    try:
        conn = get_db_connection()
        conn.execute('PRAGMA busy_timeout = 10000')
        cursor = conn.cursor()
        
        # Obtener proforma
        proforma = cursor.execute('SELECT * FROM proforma WHERE id = ?', (id,)).fetchone()
        if not proforma:
            return jsonify({'error': 'Proforma no encontrada'}), 404
        
        # Obtener detalles ordenados por id
        detalles = cursor.execute('SELECT * FROM detalle_proforma WHERE id_proforma = ? ORDER BY id', (id,)).fetchall()
        
        resultado = dict(proforma)
        resultado['detalles'] = [dict(detalle) for detalle in detalles]
        
        return jsonify(resultado)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()

def actualizar_proforma(id, data):
    conn = None
    try:
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400

        print(f"Iniciando actualización de proforma {id} con datos:", data)
        
        conn = get_db_connection()
        conn.execute('PRAGMA busy_timeout = 10000')
        conn.execute('BEGIN TRANSACTION')
        cursor = conn.cursor()

        # Verificar si la proforma existe
        cursor.execute('SELECT numero FROM proforma WHERE id = ?', (id,))
        proforma_existente = cursor.fetchone()
        
        if not proforma_existente:
            print(f"No se encontró la proforma con ID {id}")
            conn.rollback()
            return jsonify({'error': 'Proforma no encontrada'}), 404

        print(f"Proforma {id} encontrada, datos actuales:", dict(proforma_existente))

        # Validar datos requeridos
        campos_requeridos = ['numero', 'fecha', 'estado', 'idContacto', 'total']
        for campo in campos_requeridos:
            if campo not in data:
                conn.rollback()
                return jsonify({'error': f'Falta el campo requerido: {campo}'}), 400

        # Validar y convertir datos numéricos
        try:
            total = redondear_importe(float(data.get('total', 0)))
            importe_bruto = redondear_importe(float(data.get('importe_bruto', 0)))
            importe_impuestos = redondear_importe(float(data.get('importe_impuestos', 0)))
            importe_cobrado = redondear_importe(float(data.get('importe_cobrado', 0)))
        except (ValueError, TypeError) as e:
            conn.rollback()
            return jsonify({'error': f'Error en conversión de importes: {str(e)}'}), 400

        # Actualizar la proforma
        cursor.execute('''
            UPDATE proforma 
            SET numero = ?, 
                fecha = ?, 
                estado = ?, 
                idContacto = ?, 
                nif = ?, 
                total = ?, 
                formaPago = ?, 
                importe_bruto = ?, 
                importe_impuestos = ?,
                importe_cobrado = ?, 
                timestamp = ?,
                tipo = ?
            WHERE id = ?
        ''', (
            data['numero'],
            data['fecha'],
            data['estado'],
            data['idContacto'],
            data.get('nif', ''),
            total,
            data.get('formaPago', 'E'),
            importe_bruto,
            importe_impuestos,
            importe_cobrado,
            datetime.now().isoformat(),
            data.get('tipo', 'N'),  # Por defecto, tipo 'A' si no se especifica
            id
        ))

        print(f"Proforma {id} actualizada, procediendo a actualizar detalles")

        # Eliminar detalles existentes
        cursor.execute('DELETE FROM detalle_proforma WHERE id_proforma = ?', (id,))

        # Validar detalles
        if 'detalles' not in data or not isinstance(data['detalles'], list):
            conn.rollback()
            return jsonify({'error': 'Se requiere una lista de detalles válida'}), 400

        # Insertar los nuevos detalles
        for detalle in data['detalles']:
            try:
                # Validar campos requeridos del detalle
                campos_detalle = ['concepto', 'cantidad', 'precio', 'impuestos', 'total']
                for campo in campos_detalle:
                    if campo not in detalle:
                        raise ValueError(f'Falta el campo {campo} en el detalle')

                # Convertir valores numéricos
                cantidad = int(detalle['cantidad'])
                precio = float(detalle['precio'])
                impuestos = float(detalle['impuestos'])
                total_detalle = redondear_importe(float(detalle['total']))

                cursor.execute('''
                    INSERT INTO detalle_proforma (id_proforma, concepto, descripcion, cantidad, 
                                                precio, impuestos, total, formaPago, productoId, fechaDetalle)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                ))
            except (ValueError, TypeError) as e:
                conn.rollback()
                return jsonify({'error': f'Error en detalle: {str(e)}'}), 400

        conn.commit()
        print(f"Proforma {id} y sus detalles actualizados correctamente")
        
        return jsonify({
            'mensaje': 'Proforma actualizada exitosamente',
            'id': id
        })

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error al actualizar proforma {id}: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()
        print(f"Conexión cerrada para proforma {id}")



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
            proforma_dict = dict(proforma)
            
            # Obtener los detalles de la proforma
            print(f"Buscando detalles para proforma id: {proforma_dict['id']}")
            cursor.execute('''
                SELECT id, concepto, descripcion, cantidad, precio, impuestos, total, 
                       formaPago, productoId, fechaDetalle
                FROM detalle_proforma 
                WHERE id_proforma = ?
                ORDER BY id
            ''', (proforma_dict['id'],))
            detalles = cursor.fetchall()
            print(f"Detalles encontrados: {[dict(d) for d in detalles]}")
            
            # Construir respuesta completa
            response_data = {
                'modo': 'edicion',
                'id': proforma_dict['id'],
                'numero': proforma_dict['numero'],
                'fecha': proforma_dict['fecha'],
                'estado': proforma_dict['estado'],
                'tipo': proforma_dict['tipo'],
                'total': proforma_dict['total'],
                'contacto': {
                    'idContacto': contacto_dict['idContacto'],
                    'razonsocial': contacto_dict['razonsocial'],
                    'identificador': contacto_dict['identificador'],
                    'direccion': contacto_dict['direccion'],
                    'cp': contacto_dict['cp'],
                    'localidad': contacto_dict['localidad'],
                    'provincia': contacto_dict['provincia']
                },
                'detalles': [dict(d) for d in detalles]
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
                p.idcontacto,
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

        # Convertir los resultados a una lista de diccionarios
        result = []
        for proforma in proformas:
            result.append({
                'id': proforma[0],
                'fecha': proforma[1],
                'numero': proforma[2],
                'estado': proforma[3],
                'tipo': proforma[4],
                'base': float(proforma[5]) if proforma[5] is not None else 0,
                'iva': float(proforma[6]) if proforma[6] is not None else 0,
                'importe_cobrado': float(proforma[7]) if proforma[7] is not None else 0,
                'total': float(proforma[8]) if proforma[8] is not None else 0,
                'idcontacto': proforma[9],
                'razonsocial': proforma[10]
            })

        return jsonify(result)

    except Exception as e:
        print(f"Error en consultar_proformas: {str(e)}")
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

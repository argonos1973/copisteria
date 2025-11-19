#!/usr/bin/env python3
"""
Módulo de gestión de tickets
Contiene todas las funciones relacionadas con la gestión de tickets
"""

import json
import sqlite3
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from format_utils import format_currency_es_two, format_total_es_two, format_number_es_max5, format_percentage

from flask import jsonify, request
from db_utils import get_db_connection, formatear_numero_documento
from verifactu.core import generar_datos_verifactu_para_ticket
from logger_config import get_tickets_logger

# Inicializar logger
logger = get_tickets_logger()
from utilities import calcular_importes

# Cargar configuración de Verifactu
try:
    from config_loader import get as get_config
    VERIFACTU_HABILITADO = bool(get_config("verifactu_enabled", False))
except Exception:
    VERIFACTU_HABILITADO = False

def D(x):
    """Conversión segura a Decimal"""
    try:
        return Decimal(str(x if x is not None else '0'))
    except Exception:
        return Decimal('0')

def _to_decimal(val, default='0'):
    """Convierte un valor a Decimal de forma segura"""
    try:
        return Decimal(str(val).replace(',', '.'))
    except Exception:
        return Decimal(default)

def tickets_paginado():
    """Obtiene tickets con paginación y filtros"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Filtros
        fecha_inicio = request.args.get('fecha_inicio', '').strip()
        fecha_fin = request.args.get('fecha_fin', '').strip()
        estado = request.args.get('estado', '').strip()
        numero = request.args.get('numero', '').strip()
        forma_pago = request.args.get('formaPago', '').strip()
        concepto = request.args.get('concepto', '').strip()

        # Paginación/orden
        try:
            page = int(request.args.get('page', 1))
        except Exception:
            page = 1
        try:
            page_size = int(request.args.get('page_size', 10))
        except Exception:
            page_size = 10
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 1
        if page_size > 100:
            page_size = 100

        sort = (request.args.get('sort', 'fecha') or 'fecha').lower()
        order = (request.args.get('order', 'DESC') or 'DESC').upper()
        if order not in ('ASC', 'DESC'):
            order = 'DESC'

        # Whitelist de columnas ordenables
        allowed_sorts = {
            'fecha': 't.fecha',
            'timestamp': 't.timestamp',
            'numero': 't.numero',
            'importe_bruto': 't.importe_bruto',
            'importe_impuestos': 't.importe_impuestos',
            'importe_cobrado': 't.importe_cobrado',
            'total': 't.total',
            'estado': 't.estado',
            'formapago': 't.formaPago'
        }
        sort_col = allowed_sorts.get(sort, 't.fecha')

        where_sql = ' WHERE 1=1'
        params = []
        if fecha_inicio:
            where_sql += ' AND t.fecha >= ?'
            params.append(fecha_inicio)
        if fecha_fin:
            where_sql += ' AND t.fecha <= ?'
            params.append(fecha_fin)
        if estado:
            where_sql += ' AND t.estado = ?'
            params.append(estado)
        if numero:
            where_sql += ' AND t.numero LIKE ?'
            params.append(f"%{numero}%")
        if forma_pago:
            where_sql += ' AND t.formaPago = ?'
            params.append(forma_pago)
        if concepto:
            where_sql += ' AND EXISTS (SELECT 1 FROM detalle_tickets d WHERE d.id_ticket = t.id AND (lower(d.concepto) LIKE ? OR lower(d.descripcion) LIKE ?))'
            like_val = f"%{concepto.lower()}%"
            params.extend([like_val, like_val])

        # Total de filas
        count_sql = f"SELECT COUNT(*) as total FROM tickets t{where_sql}"
        cursor.execute(count_sql, params)
        total_rows = int(cursor.fetchone()['total'])

        # Datos paginados
        offset = (page - 1) * page_size
        order_by = f" ORDER BY {sort_col} {order}"
        # Si el orden principal es por fecha, añadir timestamp para estabilidad
        if sort_col == 't.fecha':
            order_by += ", t.timestamp DESC"

        data_sql = f"SELECT t.* FROM tickets t{where_sql}{order_by} LIMIT ? OFFSET ?"
        cursor.execute(data_sql, (*params, page_size, offset))
        raw_rows = cursor.fetchall()
        items = []
        for row in raw_rows:
            ticket_dict = dict(row)
            ticket_dict['importe_bruto'] = format_currency_es_two(ticket_dict.get('importe_bruto'))
            ticket_dict['importe_impuestos'] = format_currency_es_two(ticket_dict.get('importe_impuestos'))
            ticket_dict['importe_cobrado'] = format_currency_es_two(ticket_dict.get('importe_cobrado'))
            ticket_dict['total'] = format_currency_es_two(ticket_dict.get('total'))
            items.append(ticket_dict)

        # Calcular totales globales según el estado del filtro
        totales_globales = {
            'total_base': '0,00',
            'total_iva': '0,00',
            'total_cobrado': '0,00',
            'total_total': '0,00'
        }
        
        # Solo calcular totales si hay un estado específico en el filtro
        if estado:
            # Si hay filtro de concepto, sumar solo las líneas que coinciden
            if concepto:
                totales_sql = f'''
                    SELECT 
                        SUM(d.precio * d.cantidad) as total_base,
                        SUM(d.total - (d.precio * d.cantidad)) as total_iva,
                        SUM(d.total) as total_total
                    FROM detalle_tickets d
                    JOIN tickets t ON d.id_ticket = t.id
                    WHERE t.estado = ?
                    AND (lower(d.concepto) LIKE ? OR lower(d.descripcion) LIKE ?)
                '''
                totales_params = [estado, like_val, like_val]
                
                # Añadir filtros de fecha si existen
                if fecha_inicio:
                    totales_sql += ' AND t.fecha >= ?'
                    totales_params.append(fecha_inicio)
                if fecha_fin:
                    totales_sql += ' AND t.fecha <= ?'
                    totales_params.append(fecha_fin)
                if numero:
                    totales_sql += ' AND t.numero LIKE ?'
                    totales_params.append(f"%{numero}%")
                if forma_pago:
                    totales_sql += ' AND t.formaPago = ?'
                    totales_params.append(forma_pago)
                
                cursor.execute(totales_sql, totales_params)
                totales_row = cursor.fetchone()
                
                if totales_row:
                    total_base = totales_row['total_base'] or 0
                    total_iva = totales_row['total_iva'] or 0
                    total_total = totales_row['total_total'] or 0
                    totales_globales = {
                        'total_base': format_currency_es_two(total_base),
                        'total_iva': format_currency_es_two(total_iva),
                        'total_cobrado': format_currency_es_two(total_total),  # Cobrado = Total para líneas
                        'total_total': format_currency_es_two(total_total)
                    }
            else:
                # Sin filtro de concepto, usar totales del ticket completo
                totales_sql = f'''
                    SELECT 
                        SUM(t.importe_bruto) as total_base,
                        SUM(t.importe_impuestos) as total_iva,
                        SUM(t.importe_cobrado) as total_cobrado,
                        SUM(t.total) as total_total
                    FROM tickets t{where_sql}
                '''
                cursor.execute(totales_sql, params)
                totales_row = cursor.fetchone()
                
                if totales_row:
                    totales_dict = dict(totales_row)
                    totales_globales = {
                        'total_base': format_currency_es_two(totales_dict.get('total_base', 0)),
                        'total_iva': format_currency_es_two(totales_dict.get('total_iva', 0)),
                        'total_cobrado': format_currency_es_two(totales_dict.get('total_cobrado', 0)),
                        'total_total': format_currency_es_two(totales_dict.get('total_total', 0))
                    }

        total_pages = (total_rows + page_size - 1) // page_size if page_size else 1

        return jsonify({
            'items': items,
            'total': total_rows,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'sort': sort,
            'order': order,
            'totales_globales': totales_globales
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

def guardar_ticket():
    """Guarda un nuevo ticket con lógica unificada de cálculo"""
    conn = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No se recibieron datos"}), 400
        
        # Validar que todos los campos requeridos estén presentes
        campos_requeridos = ['fecha', 'numero', 'total', 'detalles', 'estado', 'formaPago', 'importe_cobrado']
        campos_faltantes = [campo for campo in campos_requeridos if campo not in data]
        
        if campos_faltantes:
            return jsonify({
                "error": f"Faltan campos requeridos: {', '.join(campos_faltantes)}",
                "datos_recibidos": data
            }), 400
        
        # Obtener y redondear los importes
        importes = calcular_importes(1, data.get('importe_cobrado', 0), 0)
        importe_cobrado = importes['total']
        
        importes = calcular_importes(1, data.get('total', 0), 0)
        total = importes['total']
        
        # Convertir fecha de DD/MM/YYYY a YYYY-MM-DD
        try:
            fecha_str = data.get('fecha')
            if not fecha_str:
                return jsonify({"error": "La fecha es requerida"}), 400
            
            # Convertir la fecha al formato correcto
            if '/' in fecha_str:
                dia, mes, anio = fecha_str.split('/')
                fecha = f"{anio}-{mes.zfill(2)}-{dia.zfill(2)}"
            else:
                fecha = fecha_str
        except Exception as e:
            return jsonify({
                "error": "Error al procesar la fecha",
                "detalle": str(e),
                "fecha_recibida": fecha_str
            }), 400

        numero = data.get('numero')
        detalles = data.get('detalles')
        estado = data.get('estado')
        formaPago = data.get('formaPago', 'E')

        if not fecha or not numero or total is None or not detalles:
            return jsonify({
                "error": "Datos incompletos",
                "datos_recibidos": {
                    "fecha": fecha,
                    "numero": numero,
                    "total": total,
                    "detalles": len(detalles) if detalles else 0
                }
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            conn.execute('BEGIN EXCLUSIVE TRANSACTION')
            
            # Comprobar si ya existe un ticket con el mismo número
            cursor.execute("SELECT id FROM tickets WHERE numero = ?", (numero,))
            existe_ticket = cursor.fetchone()

            if existe_ticket:
                conn.rollback()
                return jsonify({"error": f"Ya existe un ticket con el número {numero}"}), 400

            # USAR LÓGICA UNIFICADA: Calcular importes por línea
            importe_bruto = 0
            importe_impuestos = 0
            total_calculado = 0
            
            # APLICAR MISMA LÓGICA QUE FRONTEND UNIFICADO
            for detalle in detalles:
                res = calcular_importes(detalle['cantidad'], detalle['precio'], detalle['impuestos'])
                subtotal = res['subtotal']
                iva_linea = res['iva']
                total_linea = res['total']
                
                importe_bruto += subtotal
                importe_impuestos += iva_linea
                total_calculado += total_linea
            
            # Insertar el ticket en la tabla tickets
            cursor.execute('''
                INSERT INTO tickets (fecha, numero, importe_bruto, importe_impuestos, importe_cobrado, total, timestamp, estado, formaPago)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (fecha, numero, importe_bruto, importe_impuestos, importe_cobrado, total_calculado, datetime.now().isoformat(), estado, formaPago))
            
            id_ticket = cursor.lastrowid

            # Insertar los detalles en la tabla detalle_tickets
            for detalle in detalles:
                res = calcular_importes(detalle['cantidad'], detalle['precio'], detalle['impuestos'])
                subtotal = res['subtotal']
                iva_linea = res['iva']
                total_linea = res['total']
                
                cursor.execute('''
                    INSERT INTO detalle_tickets (
                        id_ticket, concepto, descripcion, cantidad, 
                        precio, impuestos, total, productoId
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    id_ticket,
                    detalle['concepto'],
                    detalle.get('descripcion', ''),
                    float(detalle['cantidad']),
                    float(detalle['precio']),
                    float(detalle['impuestos']),
                    float(total_linea),
                    detalle.get('productoId', None)
                ))

            # Actualizar el numerador solo si no estamos en modo edición
            if not existe_ticket:
                cursor.execute("SELECT numerador FROM numerador WHERE tipo = 'T' AND ejercicio = ?", (datetime.now().year,))
                resultado = cursor.fetchone()
                if resultado:
                    numerador = resultado[0]
                    cursor.execute("UPDATE numerador SET numerador = ? WHERE tipo = 'T' AND ejercicio = ?", 
                              (numerador + 1, datetime.now().year))
            
            # Hacer commit de toda la transacción
            conn.commit()

            # Generar datos VERI*FACTU para el ticket (solo si está habilitado)
            if VERIFACTU_HABILITADO:
                logger.info(f"[VERIFACTU] Generando datos VERI*FACTU para ticket {id_ticket}...")
                try:
                    # Obtener código de empresa de la ruta de la BD (para tickets no hay sesión)
                    # conn es la conexión actual, extraer empresa_codigo de su ruta
                    import re
                    db_path = conn.execute('PRAGMA database_list').fetchone()[2]
                    # Ruta típica: /var/www/html/db/caca/caca.db
                    match = re.search(r'/db/([^/]+)/\1\.db', db_path)
                    if match:
                        empresa_codigo = match.group(1)
                    else:
                        # Fallback: extraer del nombre de archivo
                        import os
                        db_name = os.path.basename(db_path)
                        empresa_codigo = db_name.replace('.db', '')
                    
                    logger.info(f"[VERIFACTU] Usando empresa_codigo={empresa_codigo} (extraído de BD: {db_path})")
                    
                    resultado = generar_datos_verifactu_para_ticket(id_ticket, empresa_codigo=empresa_codigo)
                    if resultado:
                        logger.info(f"[VERIFACTU] Datos generados correctamente para ticket {id_ticket}")
                    else:
                        logger.warning(f"[VERIFACTU] No se generaron datos para ticket {id_ticket}")
                except Exception as vf_exc:
                    logger.error(f"[VERIFACTU] Error generando datos VERI*FACTU para ticket {id_ticket}: {vf_exc}", exc_info=True)
            else:
                logger.info("[VERIFACTU] VERIFACTU_HABILITADO=False, omitiendo generación")

            return jsonify({"mensaje": "Ticket guardado correctamente", "id": id_ticket})

        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            return jsonify({
                "error": "Error al guardar en la base de datos",
                "detalle": str(e)
            }), 500

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error al guardar ticket: {str(e)}", exc_info=True)
        return jsonify({
            "error": "Error al procesar la solicitud",
            "detalle": str(e)
        }), 500
    finally:
        if conn:
            conn.close()

def obtener_ticket_con_detalles(id_ticket):
    """Obtiene un ticket con sus detalles usando lógica unificada para recalcular totales"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener el ticket
        cursor.execute('SELECT * FROM tickets WHERE id = ?', (id_ticket,))
        ticket = cursor.fetchone()

        if not ticket:
            return jsonify({'error': 'Ticket no encontrado'}), 404

        # Obtener los detalles del ticket
        cursor.execute('SELECT * FROM detalle_tickets WHERE id_ticket = ?', (id_ticket,))
        detalles = cursor.fetchall()

        # Convertir los resultados a diccionarios
        ticket_dict = dict(ticket)
        detalles_list = [dict(detalle) for detalle in detalles]

        base_total_dec = _to_decimal(ticket_dict.get('importe_bruto'))
        iva_total_dec = _to_decimal(ticket_dict.get('importe_impuestos'))
        total_total_dec = _to_decimal(ticket_dict.get('total'))

        ticket_dict['importe_bruto'] = format_currency_es_two(base_total_dec)
        ticket_dict['importe_impuestos'] = format_currency_es_two(iva_total_dec)
        ticket_dict['total'] = format_currency_es_two(total_total_dec)
        ticket_dict['importe_cobrado'] = format_currency_es_two(ticket_dict.get('importe_cobrado'))

        # Obtener datos VERI*FACTU (QR, CSV, estado y errores) si existen
        # Para tickets, el ID se guarda en factura_id (registro unificado con facturas)
        cursor.execute('SELECT codigo_qr, csv, estado_envio, errores FROM registro_facturacion WHERE factura_id = ?', (id_ticket,))
        reg = cursor.fetchone()
        codigo_qr = reg['codigo_qr'] if reg else None
        csv = reg['csv'] if reg else None
        estado_envio = reg['estado_envio'] if reg else None
        errores_aeat = reg['errores'] if reg else None

        formatted_detalles = []
        for detalle in detalles_list:
            detalle_fmt = detalle.copy()
            detalle_fmt['cantidad'] = format_number_es_max5(detalle.get('cantidad'))
            detalle_fmt['precio'] = format_number_es_max5(detalle.get('precio'))
            detalle_fmt['impuestos'] = format_percentage(detalle.get('impuestos'))
            detalle_fmt['total'] = format_currency_es_two(detalle.get('total'))
            formatted_detalles.append(detalle_fmt)

        # Combinar ticket, detalles y datos VERI*FACTU
        resultado = {
            'ticket': ticket_dict,
            'detalles': formatted_detalles,
            'codigo_qr': codigo_qr,
            'csv': csv,
            'estado_envio': estado_envio,
            'errores_aeat': errores_aeat,
            'verifactu_enabled': VERIFACTU_HABILITADO
        }
        
        # Log de debug para verificar datos VERIFACTU
        logger.info(f"[API] Ticket {id_ticket}: verifactu_enabled={VERIFACTU_HABILITADO}, "
                   f"tiene_qr={bool(codigo_qr)}, qr_len={len(codigo_qr) if codigo_qr else 0}, "
                   f"csv={csv}, estado={estado_envio}")

        return jsonify(resultado)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

def obtener_numero_ticket(tipoNum):
    """Obtiene el numerador actual para el tipo indicado"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        ejercicio = datetime.now().year

        cursor.execute("SELECT numerador FROM numerador WHERE tipo = ? AND ejercicio = ?", (tipoNum, ejercicio))
        resultado = cursor.fetchone()
        
        if resultado:
            numerador = resultado[0]
        else:
            numerador = 1
            cursor.execute("INSERT INTO numerador (tipo, ejercicio, numerador) VALUES (?, ?, ?)", 
                          (tipoNum, ejercicio, numerador))
            conn.commit()

        return jsonify({"numerador": numerador})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

def verificar_numero_ticket(numero):
    """Verifica si existe un ticket con el número dado"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM tickets WHERE numero = ?", (numero,))
        resultado = cursor.fetchone()
        existe = resultado['count'] > 0
        
        return jsonify({"existe": existe})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

def obtener_actualizar_numero_ticket(tipoNum):
    """Obtiene y actualiza el numerador para el tipo indicado"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        ejercicio = datetime.now().year

        cursor.execute("SELECT numerador FROM numerador WHERE tipo = ? AND ejercicio = ?", (tipoNum, ejercicio))
        resultado = cursor.fetchone()
        
        if resultado:
            numerador = resultado[0]
        else:
            numerador = 1
            cursor.execute("INSERT INTO numerador (tipo, ejercicio, numerador) VALUES (?, ?, ?)", 
                          (tipoNum, ejercicio, numerador))
        
        # Actualizar el numerador
        cursor.execute("UPDATE numerador SET numerador = ? WHERE tipo = ? AND ejercicio = ?", 
                      (numerador + 1, tipoNum, ejercicio))
        conn.commit()

        return jsonify({"numerador": numerador})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

def total_tickets_cobrados_ano_actual():
    """Obtiene el total de tickets cobrados del año actual y anterior con porcentaje de diferencia"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener el año actual
        año_actual = datetime.now().year
        año_anterior = año_actual - 1

        try:
            # Consulta para el año actual
            cursor.execute('''
                SELECT COALESCE(SUM(total), 0) as total
                FROM tickets
                WHERE estado = 'C'
                AND strftime('%Y', fecha) = ?
            ''', (str(año_actual),))
            total_actual = cursor.fetchone()['total'] or 0

            # Consulta para el año anterior
            cursor.execute('''
                SELECT COALESCE(SUM(total), 0) as total
                FROM tickets
                WHERE estado = 'C'
                AND strftime('%Y', fecha) = ?
            ''', (str(año_anterior),))
            total_anterior = cursor.fetchone()['total'] or 0

            # Calcular el porcentaje de diferencia
            if float(total_anterior) > 0:
                porcentaje_diferencia = ((float(total_actual) - float(total_anterior)) / float(total_anterior)) * 100
            else:
                porcentaje_diferencia = 100 if float(total_actual) > 0 else 0

            return jsonify({
                'total_actual': float(total_actual),
                'total_anterior': float(total_anterior),
                'porcentaje_diferencia': float(porcentaje_diferencia)
            })

        except Exception as e:
            logger.error(f"Error en la consulta SQL (total_tickets_cobrados): {str(e)}", exc_info=True)
            return jsonify({'error': f"Error en la consulta SQL: {str(e)}"}), 500

    except Exception as e:
        logger.error(f"Error en total_tickets_cobrados_ano_actual: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def media_ventas_mensual():
    """Obtiene la media de ventas mensual del año actual"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Consulta simplificada
            cursor.execute('''
                SELECT COALESCE(AVG(total_mensual), 0) as media
                FROM (
                    SELECT SUM(total) as total_mensual
                    FROM tickets
                    WHERE estado = 'C'
                    AND strftime('%Y', fecha) = strftime('%Y', 'now')
                    GROUP BY strftime('%m', fecha)
                )
            ''')
            resultado = cursor.fetchone()
            media = float(resultado['media'] if resultado['media'] is not None else 0)

            return jsonify({"media_ventas_mensual": media})

        except Exception as e:
            logger.error(f"Error en la consulta SQL (media_ventas_mensual): {str(e)}", exc_info=True)
            return jsonify({'error': f"Error en la consulta SQL: {str(e)}"}), 500

    except Exception as e:
        logger.error(f"Error en media_ventas_mensual: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def media_ventas_diaria():
    """Obtiene la media de ventas diaria del año actual"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Consulta simplificada
            cursor.execute('''
                SELECT COALESCE(AVG(total_diario), 0) as media
                FROM (
                    SELECT SUM(total) as total_diario
                    FROM tickets
                    WHERE estado = 'C'
                    AND strftime('%Y', fecha) = strftime('%Y', 'now')
                    GROUP BY fecha
                )
            ''')
            resultado = cursor.fetchone()
            media = float(resultado['media'] if resultado['media'] is not None else 0)

            return jsonify({"media_ventas_diaria": media})

        except Exception as e:
            logger.error(f"Error en la consulta SQL (media_ventas_diaria): {str(e)}", exc_info=True)
            return jsonify({'error': f"Error en la consulta SQL: {str(e)}"}), 500

    except Exception as e:
        logger.error(f"Error en media_ventas_diaria: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def media_gasto_por_ticket():
    """Obtiene la media de gasto por ticket del año actual"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Consulta simplificada
            cursor.execute('''
                SELECT 
                    COALESCE(AVG(total), 0) as media_gasto,
                    COUNT(*) as num_tickets
                FROM tickets
                WHERE estado = 'C'
                AND strftime('%Y', fecha) = strftime('%Y', 'now')
            ''')
            resultado = cursor.fetchone()
            
            media_gasto = float(resultado['media_gasto'] if resultado['media_gasto'] is not None else 0)
            num_tickets = int(resultado['num_tickets'])

            return jsonify({
                'media_gasto': media_gasto,
                'media_gasto_formateado': "{:.2f}".format(media_gasto),
                'num_tickets': num_tickets
            })

        except Exception as e:
            logger.error(f"Error en la consulta SQL (media_gasto_por_ticket): {str(e)}", exc_info=True)
            return jsonify({'error': f"Error en la consulta SQL: {str(e)}"}), 500

    except Exception as e:
        logger.error(f"Error en media_gasto_por_ticket: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def actualizar_ticket():
    """Actualiza un ticket existente con lógica unificada de cálculo"""
    conn = None
    try:
        # Parseo robusto de JSON: leer primero el cuerpo crudo y parsear manualmente
        data = {}
        try:
            ct = request.headers.get('Content-Type')
            cl = request.headers.get('Content-Length')
        except Exception:
            ct = None
            cl = None
        try:
            raw = request.get_data(cache=True, as_text=True) or ''
        except Exception:
            raw = ''
        try:
            preview = raw[:200] if isinstance(raw, str) else str(raw)[:200]
            logger.debug(f"[/api/tickets/actualizar] CT={ct} CL={cl} len_raw={len(raw) if isinstance(raw,str) else 'NA'} raw_preview={preview}")
        except Exception:
            pass
        if raw and raw.strip():
            try:
                data = json.loads(raw)
            except Exception:
                data = {}
        if not data:
            # Fallback a get_json por si el servidor ya decodificó el body
            data = request.get_json(force=True, silent=True) or {}
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400

        id_ticket = data.get('id')
        if not id_ticket:
            return jsonify({'error': 'El campo id es requerido'}), 400

        # Procesar fecha (aceptar DD/MM/YYYY o YYYY-MM-DD)
        fecha_str = data.get('fecha')
        if not fecha_str:
            return jsonify({'error': 'La fecha es requerida'}), 400
        try:
            if '/' in fecha_str:
                dia, mes, anio = fecha_str.split('/')
                fecha = f"{anio}-{mes.zfill(2)}-{dia.zfill(2)}"
            else:
                fecha = fecha_str
        except Exception as e:
            return jsonify({'error': 'Error al procesar la fecha', 'detalle': str(e), 'fecha_recibida': fecha_str}), 400

        numero = data.get('numero')
        detalles = data.get('detalles') or []
        estado = (data.get('estado') or 'C')
        formaPago = data.get('formaPago', 'E')

        try:
            importes = calcular_importes(1, data.get('importe_cobrado', 0), 0)
            importe_cobrado = importes['total']
            importes = calcular_importes(1, data.get('total', 0), 0)
            total_ticket = importes['total']
        except Exception as e:
            return jsonify({'error': 'Importes inválidos', 'detalle': str(e)}), 400

        if not numero or not detalles:
            return jsonify({'error': 'Datos incompletos', 'datos_recibidos': {'numero': numero, 'detalles': len(detalles)}}), 400

        # Recalcular importes usando LÓGICA UNIFICADA (redondeo por línea)
        importe_bruto = 0
        importe_impuestos = 0
        total_calculado = 0
        
        # APLICAR MISMA LÓGICA QUE FRONTEND UNIFICADO
        for detalle in detalles:
            resultado = calcular_importes(detalle['cantidad'], detalle['precio'], detalle['impuestos'])
            importe_bruto += resultado['subtotal']
            importe_impuestos += resultado['iva']
            total_calculado += resultado['total']
        
        conn = get_db_connection()
        cursor = conn.cursor()

        # Verificar existencia del ticket y unicidad de número si cambia
        cursor.execute('SELECT id, numero FROM tickets WHERE id = ?', (id_ticket,))
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'Ticket no encontrado'}), 404
        numero_actual = row['numero'] if isinstance(row, sqlite3.Row) else row[1]
        if numero != numero_actual:
            cursor.execute('SELECT id FROM tickets WHERE numero = ? AND id <> ?', (numero, id_ticket))
            if cursor.fetchone():
                return jsonify({'error': f'Ya existe un ticket con el número {numero}'}), 400

        try:
            conn.execute('BEGIN TRANSACTION')
            cursor.execute('''
                UPDATE tickets 
                SET fecha = ?, numero = ?, importe_bruto = ?, importe_impuestos = ?,
                    importe_cobrado = ?, total = ?, timestamp = ?, estado = ?, formaPago = ?
                WHERE id = ?
            ''', (
                fecha, numero, importe_bruto, importe_impuestos,
                importe_cobrado, total_ticket, datetime.now().isoformat(), estado, formaPago,
                id_ticket
            ))

            cursor.execute('DELETE FROM detalle_tickets WHERE id_ticket = ?', (id_ticket,))
            for d in detalles:
                resultado = calcular_importes(d['cantidad'], d['precio'], d['impuestos'])
                cursor.execute('''
                    INSERT INTO detalle_tickets (
                        id_ticket, concepto, descripcion, cantidad, 
                        precio, impuestos, total, productoId
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    id_ticket,
                    d.get('concepto', ''),
                    d.get('descripcion', ''),
                    float(d['cantidad']),
                    float(d['precio']),
                    float(d['impuestos']),
                    float(resultado['total']),
                    d.get('productoId', None)
                ))

            conn.commit()
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            return jsonify({'error': 'Error al actualizar en la base de datos', 'detalle': str(e)}), 500

        return jsonify({'mensaje': 'Ticket actualizado correctamente', 'id': id_ticket})
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return jsonify({'error': 'Error al procesar la solicitud', 'detalle': str(e)}), 500
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

def consulta_tickets():
    """Consulta tickets con filtros"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener parámetros de la consulta
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        estado = request.args.get('estado')
        numero = request.args.get('numero')
        forma_pago = request.args.get('formaPago')
        concepto = request.args.get('concepto')

        # Construir la consulta SQL base
        sql = '''
            SELECT t.*
            FROM tickets t
            WHERE 1=1
        '''
        params = []

        # Añadir condiciones según los parámetros
        if fecha_inicio:
            sql += ' AND t.fecha >= ?'
            params.append(fecha_inicio)
        if fecha_fin:
            sql += ' AND t.fecha <= ?'
            params.append(fecha_fin)
        if estado:
            sql += ' AND t.estado = ?'
            params.append(estado)
        if numero:
            sql += ' AND t.numero LIKE ?'
            params.append(f'%{numero}%')
        if forma_pago:
            sql += ' AND t.formaPago = ?'
            params.append(forma_pago)
        if concepto:
            sql += ' AND EXISTS (SELECT 1 FROM detalle_tickets d WHERE d.id_ticket = t.id AND (lower(d.concepto) LIKE ? OR lower(d.descripcion) LIKE ?))'
            like_val = f"%{concepto.lower()}%"
            params.extend([like_val, like_val])

        sql += ' ORDER BY t.fecha DESC, t.timestamp DESC'

        logger.debug(f"SQL Query: {sql}")
        logger.debug(f"Params: {params}")

        # Ejecutar la consulta
        cursor.execute(sql, params)
        tickets = cursor.fetchall()

        # Convertir los resultados a una lista de diccionarios
        tickets_list = []
        for ticket in tickets:
            ticket_dict = dict(ticket)
            tickets_list.append(ticket_dict)

        return jsonify(tickets_list)

    except Exception as e:
        logger.error(f"Error en consulta_tickets: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

def actualizar_estado_ticket(id):
    """Actualiza el estado de un ticket"""
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        if not nuevo_estado:
            return jsonify({'error': 'El estado es requerido'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verificar si el ticket existe
        cursor.execute('SELECT id FROM tickets WHERE id = ?', (id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Ticket no encontrado'}), 404

        # Actualizar el estado
        cursor.execute('UPDATE tickets SET estado = ? WHERE id = ?', (nuevo_estado, id))
        conn.commit()

        return jsonify({'mensaje': 'Estado actualizado correctamente'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

def actualizar_ticket_legacy():
    """Función legacy para actualizar tickets (mantener compatibilidad)"""
    try:
        data = request.get_json()
        if not data or 'id' not in data:
            return jsonify({"error": "No se recibieron datos o falta el ID"}), 400

        id_ticket = data['id']
        
        # Validar y convertir el importe_cobrado
        try:
            # Asegurarnos de que el importe_cobrado esté presente en los datos
            if 'importe_cobrado' not in data:
                logger.warning("importe_cobrado no está presente en los datos")
                return jsonify({"error": "El campo importe_cobrado es requerido"}), 400

            # Convertir el importe_cobrado a float, reemplazando comas por puntos
            importe_cobrado_str = str(data['importe_cobrado']).replace(',', '.')
            importes = calcular_importes(1, importe_cobrado_str, 0)
            importe_cobrado = importes['total']
            logger.debug(f"Datos completos recibidos: {data}")
            logger.debug(f"Importe cobrado recibido (raw): {data['importe_cobrado']}")
            logger.debug(f"Importe cobrado convertido: {importe_cobrado}")
        except (ValueError, TypeError) as e:
            logger.error(f"Error al convertir importe_cobrado: {e}", exc_info=True)
            return jsonify({"error": f"Error al procesar importe_cobrado: {str(e)}"}), 400

        total = float(Decimal(str(data.get('total', 0))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        estado = data.get('estado')
        formaPago = data.get('formaPago')
        detalles_nuevos = data.get('detalles', [])

        conn = get_db_connection()
        conn.execute('BEGIN EXCLUSIVE TRANSACTION')
        cursor = conn.cursor()

        # Verificar si el ticket existe y obtener datos actuales
        cursor.execute('SELECT id, importe_cobrado, total FROM tickets WHERE id = ?', (id_ticket,))
        ticket_actual = cursor.fetchone()
        if not ticket_actual:
            conn.rollback()
            return jsonify({"error": "Ticket no encontrado"}), 404

        logger.debug(f"Datos actuales del ticket: {dict(ticket_actual)}")

        # 1. Recuperar todos los detalles existentes
        cursor.execute('''
            SELECT id, concepto, descripcion, cantidad, precio, impuestos, total
            FROM detalle_tickets 
            WHERE id_ticket = ?
        ''', (id_ticket,))
        detalles_existentes = {str(row['id']): dict(row) for row in cursor.fetchall()}

        # 2. Procesar los detalles
        detalles_finales = []
        for detalle in detalles_nuevos:
            detalle_procesado = detalle.copy()
            
            if 'id' in detalle and detalle['id'] and str(detalle['id']) in detalles_existentes:
                # Es un detalle existente
                detalle_original = detalles_existentes[str(detalle['id'])]
                # Comparar si el detalle ha sido modificado
                ha_cambiado = (
                    detalle['concepto'] != detalle_original['concepto'] or
                    detalle.get('descripcion', '') != detalle_original['descripcion'] or
                    float(detalle['cantidad']) != float(detalle_original['cantidad']) or
                    float(detalle['precio']) != float(detalle_original['precio']) or
                    float(detalle['impuestos']) != float(detalle_original['impuestos']) or
                    float(detalle['total']) != float(detalle_original['total'])
                )
                
                if ha_cambiado:
                    # Si el detalle ha sido modificado, usar la nueva forma de pago
                    detalle_procesado['formaPago'] = formaPago
                    logger.debug(f"Detalle {detalle['id']} modificado, asignando nueva formaPago: {formaPago}")
                else:
                    # Si no ha sido modificado, mantener la forma de pago original
                    detalle_procesado['formaPago'] = detalle_original['formaPago']
                    logger.debug(f"Detalle {detalle['id']} sin cambios, manteniendo formaPago: {detalle_original['formaPago']}")
            else:
                # Es un detalle nuevo, asignar la nueva forma de pago
                detalle_procesado['formaPago'] = formaPago
                logger.debug(f"Detalle nuevo, asignando formaPago: {formaPago}")
            
            detalles_finales.append(detalle_procesado)

        # Calcular importes
        importe_bruto = 0
        importe_impuestos = 0
        total_calculado = 0
        for d in detalles_finales:
            resultado = calcular_importes(d['cantidad'], d['precio'], d['impuestos'])
            importe_bruto += resultado['subtotal']
            importe_impuestos += resultado['iva']
            total_calculado += resultado['total']
        
        # Actualizar todos los campos de una vez, incluyendo el importe_cobrado
        cursor.execute('''
            UPDATE tickets 
            SET importe_bruto = ?,
                importe_impuestos = ?,
                importe_cobrado = ?,
                total = ?,
                estado = ?,
                formaPago = ?,
                timestamp = ?
            WHERE id = ?
        ''', (
            importe_bruto,
            importe_impuestos,
            importe_cobrado,
            total_calculado,
            estado,
            formaPago,
            datetime.now().isoformat(),
            id_ticket
        ))

        # Verificar el estado final
        cursor.execute('SELECT importe_cobrado, total FROM tickets WHERE id = ?', (id_ticket,))
        resultado_final = cursor.fetchone()
        logger.debug(f"Estado final del ticket: importe_cobrado={resultado_final['importe_cobrado']}, total={resultado_final['total']}")

        # Actualizar detalles
        cursor.execute('DELETE FROM detalle_tickets WHERE id_ticket = ?', (id_ticket,))

        for detalle in detalles_finales:
            # Recalcular el total correctamente en el backend
            resultado = calcular_importes(detalle['cantidad'], detalle['precio'], detalle['impuestos'])
            cursor.execute('''
                INSERT INTO detalle_tickets (
                    id_ticket, concepto, descripcion, cantidad, 
                    precio, impuestos, total, productoId
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                id_ticket,
                detalle['concepto'],
                detalle.get('descripcion', ''),
                float(detalle['cantidad']),
                float(detalle['precio']),
                float(detalle['impuestos']),
                float(resultado['total']),
                detalle.get('productoId', None)
            ))

        conn.commit()
        logger.info(f"Ticket {id_ticket} actualizado correctamente. Importe cobrado final: {importe_cobrado}")
        
        return jsonify({
            "mensaje": "Ticket actualizado correctamente",
            "id": id_ticket,
            "importe_cobrado": importe_cobrado,
            "total": total_calculado
        })

    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        logger.error(f"Error al actualizar ticket: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()
import sqlite3
import traceback
from datetime import datetime

from flask import Blueprint, jsonify, request

from db_utils import get_db_connection, redondear_importe

# Crear Blueprint para las rutas del dashboard
dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/estadisticas_gastos', methods=['GET'])
def estadisticas_gastos():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Parámetros de período seleccionados (año y mes que el usuario ha elegido)
        ahora = datetime.now()
        anio_param = request.args.get('anio')
        mes_param = request.args.get('mes')
        año = int(anio_param) if anio_param and anio_param.isdigit() else ahora.year
        mes = int(mes_param) if mes_param and mes_param.isdigit() else ahora.month
        cur.execute("SELECT COALESCE(SUM(importe_eur),0) FROM gastos WHERE importe_eur > 0 AND substr(fecha_operacion, 7, 4) = ?", (str(año),))
        total_ingresos = cur.fetchone()[0] or 0
        cur.execute("SELECT COALESCE(SUM(importe_eur),0) FROM gastos WHERE importe_eur < 0 AND substr(fecha_operacion, 7, 4) = ?", (str(año),))
        total_gastos = cur.fetchone()[0] or 0
        balance = total_ingresos + total_gastos  # Balance total anual (correcto porque gastos es negativo)

        # Balance del mes actual
       

        cur.execute("SELECT MAX(fecha_operacion) FROM gastos")
        ultima_fecha = cur.fetchone()[0]
        # Calcular ingresos y gastos del mes actual
        ahora = datetime.now()
        anio_param = request.args.get('anio')
        mes_param = request.args.get('mes')
        año = int(anio_param) if anio_param and anio_param.isdigit() else ahora.year
        mes = int(mes_param) if mes_param and mes_param.isdigit() else ahora.month
        cur.execute("""
            SELECT COALESCE(SUM(importe_eur),0) FROM gastos 
            WHERE importe_eur > 0 AND substr(fecha_operacion, 4, 2) = ? AND substr(fecha_operacion, 7, 4) = ?
        """, (str(mes).zfill(2), str(año)))
        ingresos_mes_actual = cur.fetchone()[0] or 0
        cur.execute("""
            SELECT COALESCE(SUM(importe_eur),0) FROM gastos 
            WHERE importe_eur < 0 AND substr(fecha_operacion, 4, 2) = ? AND substr(fecha_operacion, 7, 4) = ?
        """, (str(mes).zfill(2), str(año)))
        gastos_mes_actual = cur.fetchone()[0] or 0

        balance_mes = gastos_mes_actual + ingresos_mes_actual

        # Obtener el saldo y ts del último registro del mes actual
        # Buscar la última fecha_operacion del mes actual
        cur.execute("""
            SELECT fecha_operacion FROM gastos
            WHERE substr(fecha_operacion, 4, 2) = ? AND substr(fecha_operacion, 7, 4) = ?
            AND saldo IS NOT NULL
            ORDER BY fecha_operacion DESC LIMIT 1
        """, (str(mes).zfill(2), str(año)))
        row_fecha = cur.fetchone()
        ultima_fecha_operacion = row_fecha[0] if row_fecha else None

        saldo_mes_actual = None
        ts_ultima_actualizacion = None
        if ultima_fecha_operacion:
            # Buscar el ÚLTIMO registro de esa fecha (por TS descendente, rowid descendente)
            cur.execute("""
                SELECT saldo, TS FROM gastos
                WHERE fecha_operacion = ? AND saldo IS NOT NULL
                ORDER BY TS DESC, rowid DESC LIMIT 1
            """, (ultima_fecha_operacion,))
            row_saldo = cur.fetchone()
            saldo_mes_actual = row_saldo[0] if row_saldo else None
            ts_ultima_actualizacion = row_saldo[1] if row_saldo else None

        conn.close()
        return jsonify({
            'total_ingresos': redondear_importe(total_ingresos),
            'total_gastos': redondear_importe(total_gastos),
            'balance': redondear_importe(balance),
            'ultima_actualizacion': ts_ultima_actualizacion,
            'ingresos_mes_actual': redondear_importe(ingresos_mes_actual),
            'gastos_mes_actual': redondear_importe(gastos_mes_actual),
            'balance_mes_actual': redondear_importe(balance_mes),
            'saldo_mes_actual': redondear_importe(saldo_mes_actual) if saldo_mes_actual is not None else None
        })
    except Exception as e:
        print('ERROR EN /estadisticas_gastos:', str(e))
        print(traceback.format_exc())
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


def calcular_porcentaje(actual, anterior):
    try:
        if anterior == 0:
            return 100.0 if actual > 0 else 0.0
        return round(((actual - anterior) / anterior) * 100, 2)
    except:
        return 0.0

def get_tickets_data(year):
    query = '''
        SELECT COUNT(*) as num_documentos, 
               COALESCE(AVG(total), 0) as media, 
               COALESCE(SUM(total), 0) as total
        FROM tickets 
        WHERE estado = 'C' AND strftime('%Y', fecha) = ?
    '''
    return fetch_data(query, (str(year),))

def get_tickets_data_mes(year, month):
    query = '''
        SELECT COUNT(*) as num_documentos, 
               COALESCE(AVG(total), 0) as media, 
               COALESCE(SUM(total), 0) as total
        FROM tickets 
        WHERE estado = 'C' AND strftime('%Y', fecha) = ? AND strftime('%m', fecha) = ?
    '''
    # Solo devolvemos datos del mes solicitado, nunca del anterior
    result = fetch_data(query, (str(year), str(month).zfill(2)))
    return result

def get_facturas_data(year):
    query = '''
        SELECT COUNT(*) as num_documentos, 
               COALESCE(AVG(total), 0) as media, 
               COALESCE(SUM(total), 0) as total
        FROM factura 
        WHERE estado = 'C' AND strftime('%Y', fecha) = ?
    '''
    return fetch_data(query, (str(year),))

def get_facturas_data_mes(year, month):
    query = '''
        SELECT COUNT(*) as num_documentos, 
               COALESCE(AVG(total), 0) as media, 
               COALESCE(SUM(total), 0) as total
        FROM factura 
        WHERE estado = 'C' AND strftime('%Y', fecha) = ? AND strftime('%m', fecha) = ?
    '''
    # Solo devolvemos datos del mes solicitado, nunca del anterior
    result = fetch_data(query, (str(year), str(month).zfill(2)))
    return result

def get_proformas_data(year):
    query = '''
        SELECT COUNT(DISTINCT p.id) as num_documentos, 
               COALESCE(SUM(d.total), 0) as total
        FROM proforma p
        JOIN detalle_proforma d ON p.id = d.id_proforma
        WHERE p.estado = 'A' 
          AND strftime('%Y', d.fechaDetalle) = ?
    '''
    return fetch_data(query, (str(year),))

def get_proformas_data_mes(year, month):
    """Devuelve estadísticas de proformas para el mes indicado (num_documentos, total)."""
    query = '''
        SELECT COUNT(DISTINCT p.id) as num_documentos,
               COALESCE(SUM(d.total), 0) as total
        FROM proforma p
        JOIN detalle_proforma d ON p.id = d.id_proforma
        WHERE p.estado = 'A'
          AND strftime('%Y', d.fechaDetalle) = ?
          AND strftime('%m', d.fechaDetalle) = ?
    '''
    return fetch_data(query, (str(year), str(month).zfill(2)))


def fetch_data(query, params=()):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        result = cursor.fetchone()
        return dict(result) if result else {'num_documentos': 0, 'media': 0, 'total': 0}
    except sqlite3.Error as e:
        print(f"Error en la consulta SQL: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500
    finally:
        cursor.close()
        conn.close()


@dashboard_bp.route('/ventas/total_mes', methods=['GET'])
@dashboard_bp.route('/api/ventas/total_mes', methods=['GET'])
def ventas_total_mes():
    """Devuelve totales mensuales de tickets, facturas y su global para un año dado."""
    anio_param = request.args.get('anio')
    ahora = datetime.now()
    año = int(anio_param) if anio_param and anio_param.isdigit() else ahora.year

    conn = get_db_connection()
    cursor = conn.cursor()

    def obtener_totales(tabla):
        cursor.execute(
            f"""
            SELECT strftime('%m', fecha) as mes, COALESCE(SUM(total),0) as total
            FROM {tabla}
            WHERE estado = 'C' AND strftime('%Y', fecha) = ?
            GROUP BY mes
            """,
            (str(año),)
        )
        datos = {row['mes']: float(row['total'] or 0) for row in cursor.fetchall()}
        # Asegurar 12 meses presentes con 0
        return {str(m).zfill(2): datos.get(str(m).zfill(2), 0.0) for m in range(1,13)}

    tickets = obtener_totales('tickets')
    facturas = obtener_totales('factura')
    globales = {mes: redondear_importe(tickets[mes] + facturas[mes]) for mes in tickets}

    total_tickets = redondear_importe(sum(tickets.values()))
    total_facturas = redondear_importe(sum(facturas.values()))
    total_global = redondear_importe(sum(globales.values()))

    return jsonify({
        'anio': año,
        'tickets': tickets,
        'facturas': facturas,
        'global': globales,
        'totales_ano': {
            'tickets': total_tickets,
            'facturas': total_facturas,
            'global': total_global
        }
    })


@dashboard_bp.route('/ventas/cantidad_mes', methods=['GET'])
@dashboard_bp.route('/api/ventas/cantidad_mes', methods=['GET'])
def ventas_cantidad_mes():
    """Devuelve cantidades mensuales de tickets, facturas y su global para un año dado."""
    anio_param = request.args.get('anio')
    ahora = datetime.now()
    año = int(anio_param) if anio_param and anio_param.isdigit() else ahora.year

    conn = get_db_connection()
    cursor = conn.cursor()

    def obtener_cantidades(tabla):
        cursor.execute(
            f"""
            SELECT strftime('%m', fecha) as mes, COUNT(*) as cantidad
            FROM {tabla}
            WHERE estado = 'C' AND strftime('%Y', fecha) = ?
            GROUP BY mes
            """,
            (str(año),)
        )
        datos = {row['mes']: int(row['cantidad'] or 0) for row in cursor.fetchall()}
        # Asegurar 12 meses presentes con 0
        return {str(m).zfill(2): datos.get(str(m).zfill(2), 0) for m in range(1,13)}

    tickets = obtener_cantidades('tickets')
    facturas = obtener_cantidades('factura')
    globales = {mes: tickets[mes] + facturas[mes] for mes in tickets}

    conn.close()

    return jsonify({
        'anio': año,
        'tickets': tickets,
        'facturas': facturas,
        'global': globales
    })


@dashboard_bp.route('/ventas/media_por_documento', methods=['GET'])
@dashboard_bp.route('/api/ventas/media_por_documento', methods=['GET'])
def media_ventas_por_documento():
    anio_param = request.args.get('anio')
    mes_param = request.args.get('mes')
    ahora = datetime.now()

    # Período base: año y mes seleccionados (o fecha actual si no se pasó ninguno)
    año_actual = int(anio_param) if anio_param and anio_param.isdigit() else ahora.year
    mes_actual = int(mes_param) if mes_param and mes_param.isdigit() else ahora.month

    # Período comparativo: mismo mes del año anterior
    año_anterior = año_actual - 1
    mes_selector = mes_actual

    # Obtener datos actuales (proformas solo para su sección)
    tickets_actual = get_tickets_data(año_actual)
    facturas_actual = get_facturas_data(año_actual)
    proformas_actual = get_proformas_data(año_actual)

    # Obtener datos del mes actual (sin proformas)
    tickets_mes_actual = get_tickets_data_mes(año_actual, mes_actual)
    facturas_mes_actual = get_facturas_data_mes(año_actual, mes_actual)
    proformas_mes_actual = get_proformas_data_mes(año_actual, mes_actual)
    
    # Obtener datos del período comparativo (selector)
    tickets_mes_anterior = get_tickets_data_mes(año_anterior, mes_selector)
    facturas_mes_anterior = get_facturas_data_mes(año_anterior, mes_selector)
    proformas_mes_anterior = get_proformas_data_mes(año_anterior, mes_selector)

    # Calcular totales globales del mes
    global_mes_actual_total = tickets_mes_actual['total'] + facturas_mes_actual['total']
    global_mes_anterior_total = tickets_mes_anterior['total'] + facturas_mes_anterior['total']

    # Obtener datos anteriores (proformas solo para su sección)
    tickets_anterior = get_tickets_data(año_anterior)
    facturas_anterior = get_facturas_data(año_anterior)
    proformas_anterior = get_proformas_data(año_anterior)

    # Calcular totales globales SIN PROFORMAS
    global_actual_total = tickets_actual['total'] + facturas_actual['total']
    global_anterior_total = tickets_anterior['total'] + facturas_anterior['total']

    # Calcular medias mensuales SIN PROFORMAS, EXCLUYENDO EL MES ACTUAL
    def calcular_media_mensual_excluyendo_mes_actual(total, mes_actual):
        # Si estamos en enero, no hay meses completos previos
        if mes_actual <= 1:
            return 0
        # Dividir el total entre el número de meses completos (hasta el mes actual sin incluirlo)
        return total / (mes_actual - 1)

    # Procesar tickets
    tickets_media_mensual = calcular_media_mensual_excluyendo_mes_actual(tickets_actual['total'] - tickets_mes_actual['total'], mes_actual)
    tickets_media = tickets_actual['media'] if tickets_actual['num_documentos'] > 0 else 0

    # Procesar facturas
    facturas_media_mensual = calcular_media_mensual_excluyendo_mes_actual(facturas_actual['total'] - facturas_mes_actual['total'], mes_actual)
    facturas_media = facturas_actual['media'] if facturas_actual['num_documentos'] > 0 else 0

    # Procesar proformas (solo para su sección)
    proformas_media = (
        proformas_actual['total'] / proformas_actual['num_documentos'] 
        if proformas_actual['num_documentos'] > 0 
        else 0
    )
    proformas_media_mensual = calcular_media_mensual_excluyendo_mes_actual(proformas_actual['total'], mes_actual)

    # Procesar global SIN PROFORMAS
    total_documentos_global = tickets_actual['num_documentos'] + facturas_actual['num_documentos']
    global_media = (
        (tickets_actual['total'] + facturas_actual['total']) / total_documentos_global
        if total_documentos_global > 0 
        else 0
    )
    global_media_mensual = calcular_media_mensual_excluyendo_mes_actual(global_actual_total - global_mes_actual_total, mes_actual)

    return jsonify({
        'año_actual': año_actual,
        'año_anterior': año_anterior,
        'mes_actual': mes_actual,
        
        'tickets': {
            'actual': {
                'total': redondear_importe(tickets_actual['total']),
                'media': redondear_importe(tickets_media),
                'media_mensual': redondear_importe(tickets_media_mensual),
                'cantidad': tickets_actual['num_documentos'],
                'mes_actual': {
                    'total': redondear_importe(tickets_mes_actual['total']),
                    'cantidad': tickets_mes_actual['num_documentos']
                }
            },
            'anterior': {
                'total': redondear_importe(tickets_anterior['total']),
                'media': redondear_importe(tickets_anterior['media']),
                'cantidad': tickets_anterior['num_documentos'],
                'mismo_mes': {
                    'total': redondear_importe(tickets_mes_anterior['total']),
                    'cantidad': tickets_mes_anterior['num_documentos']
                }
            },
            'porcentaje_diferencia': redondear_importe(
                calcular_porcentaje(
                    tickets_actual['total'], 
                    tickets_anterior['total']
                )
            ),
            'porcentaje_diferencia_mes': redondear_importe(
                calcular_porcentaje(
                    tickets_mes_actual['total'], 
                    tickets_mes_anterior['total']
                )
            )
        },
        
        'facturas': {
            'actual': {
                'total': redondear_importe(facturas_actual['total']),
                'media': redondear_importe(facturas_media),
                'media_mensual': redondear_importe(facturas_media_mensual),
                'cantidad': facturas_actual['num_documentos'],
                'mes_actual': {
                    'total': redondear_importe(facturas_mes_actual['total']),
                    'cantidad': facturas_mes_actual['num_documentos']
                }
            },
            'anterior': {
                'total': redondear_importe(facturas_anterior['total']),
                'media': redondear_importe(facturas_anterior['media']),
                'cantidad': facturas_anterior['num_documentos'],
                'mismo_mes': {
                    'total': redondear_importe(facturas_mes_anterior['total']),
                    'cantidad': facturas_mes_anterior['num_documentos']
                }
            },
            'porcentaje_diferencia': redondear_importe(
                calcular_porcentaje(
                    facturas_actual['total'], 
                    facturas_anterior['total']
                )
            ),
            'porcentaje_diferencia_mes': redondear_importe(
                calcular_porcentaje(
                    facturas_mes_actual['total'], 
                    facturas_mes_anterior['total']
                )
            )
        },
        
        'proformas': {
            'actual': {
                'total': redondear_importe(proformas_actual['total']),
                'media': redondear_importe(proformas_media),
                'media_mensual': redondear_importe(proformas_media_mensual),
                'cantidad': proformas_actual['num_documentos'],
                'mes_actual': {
                    'total': redondear_importe(proformas_mes_actual['total']),
                    'cantidad': proformas_mes_actual['num_documentos']
                }
            },
            'anterior': {
                'total': redondear_importe(proformas_anterior['total']),
                'media': redondear_importe(
                    proformas_anterior['total'] / proformas_anterior['num_documentos'] 
                    if proformas_anterior['num_documentos'] > 0 
                    else 0
                ),
                'cantidad': proformas_anterior['num_documentos'],
                'mismo_mes': {
                    'total': redondear_importe(proformas_mes_anterior['total']),
                    'cantidad': proformas_mes_anterior['num_documentos']
                }
            },
            'porcentaje_diferencia': redondear_importe(
                calcular_porcentaje(
                    proformas_actual['total'], 
                    proformas_anterior['total']
                )
            ),
            'porcentaje_diferencia_mes': redondear_importe(
                calcular_porcentaje(
                    proformas_mes_actual['total'],
                    proformas_mes_anterior['total']
                )
            )
        },
        'global': {
            'actual': {
                'total': redondear_importe(global_actual_total),
                'media': redondear_importe(global_media),
                'media_mensual': redondear_importe(global_media_mensual),
                'cantidad': total_documentos_global,
                'mes_actual': {
                    'total': redondear_importe(global_mes_actual_total),
                    'cantidad': tickets_mes_actual['num_documentos'] + facturas_mes_actual['num_documentos']
                }
            },
            'anterior': {
                'total': redondear_importe(global_anterior_total),
                'media': redondear_importe(
                    (tickets_anterior['total'] + facturas_anterior['total']) / (tickets_anterior['num_documentos'] + facturas_anterior['num_documentos'])
                    if (tickets_anterior['num_documentos'] + facturas_anterior['num_documentos']) > 0 else 0
                ),
                'cantidad': tickets_anterior['num_documentos'] + facturas_anterior['num_documentos'],
                'mismo_mes': {
                    'total': redondear_importe(global_mes_anterior_total),
                    'cantidad': tickets_mes_anterior['num_documentos'] + facturas_mes_anterior['num_documentos']
                }
            },
            'porcentaje_diferencia': redondear_importe(calcular_porcentaje(global_actual_total, global_anterior_total)),
            'porcentaje_diferencia_mes': redondear_importe(calcular_porcentaje(global_mes_actual_total, global_mes_anterior_total))
        }
    })
    """
                'media': redondear_importe(proformas_media),
                'media_mensual': redondear_importe(proformas_media_mensual),
                'cantidad': proformas_actual['num_documentos']
            },
            'anterior': {
                'total': redondear_importe(proformas_anterior['total']),
                'media': redondear_importe(
                    proformas_anterior['total'] / proformas_anterior['num_documentos'] 
                    if proformas_anterior['num_documentos'] > 0 
                    else 0
                ),
                'cantidad': proformas_anterior['num_documentos']
            },
            'porcentaje_diferencia': redondear_importe(
            )
        )
    },
    
    'facturas': {
        'actual': {
            'total': redondear_importe(facturas_actual['total']),
            'media': redondear_importe(facturas_media),
            'media_mensual': redondear_importe(facturas_media_mensual),
            'cantidad': facturas_actual['num_documentos'],
            'mes_actual': {
                'total': redondear_importe(facturas_mes_actual['total']),
                'cantidad': facturas_mes_actual['num_documentos']
            }
        },
        'anterior': {
            'total': redondear_importe(facturas_anterior['total']),
            'media': redondear_importe(facturas_anterior['media']),
            'cantidad': facturas_anterior['num_documentos'],
            'mismo_mes': {
                'total': redondear_importe(facturas_mes_anterior['total']),
                'cantidad': facturas_mes_anterior['num_documentos']
            }
        },
        'porcentaje_diferencia': redondear_importe(
            calcular_porcentaje(
                facturas_actual['total'], 
                facturas_anterior['total']
                'cantidad': (
                    tickets_actual['num_documentos'] + 
                    facturas_actual['num_documentos']  # Sin proformas
                ),
                'mes_actual': {
                    'total': redondear_importe(global_mes_actual_total),
                    'cantidad': tickets_mes_actual['num_documentos'] + facturas_mes_actual['num_documentos']
                }
            },
            'anterior': {
                'total': redondear_importe(global_anterior_total),
                'media': redondear_importe(
                    (tickets_anterior['total'] + facturas_anterior['total']) /
                    (tickets_anterior['num_documentos'] + facturas_anterior['num_documentos'])
                    if (tickets_anterior['num_documentos'] + facturas_anterior['num_documentos']) > 0
                    else 0
                ),
                'cantidad': (
                    tickets_anterior['num_documentos'] + 
                    facturas_anterior['num_documentos']  # Sin proformas
                ),
                'mismo_mes': {
                    'total': redondear_importe(global_mes_anterior_total),
                    'cantidad': tickets_mes_anterior['num_documentos'] + facturas_mes_anterior['num_documentos']
                }
            },
            'porcentaje_diferencia': redondear_importe(
                calcular_porcentaje(
                    global_actual_total, 
                    global_anterior_total
                )
            ),
            'porcentaje_diferencia_mes': redondear_importe(
                calcular_porcentaje(
                    global_mes_actual_total, 
                    global_mes_anterior_total
                )
            )
        }
    })

"""
@dashboard_bp.route('/clientes/top_ventas', methods=['GET'])
@dashboard_bp.route('/api/clientes/top_ventas', methods=['GET'])
def top_clientes_ventas():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        anio_param = request.args.get('anio')
        ahora = datetime.now()
        # Año seleccionado (o el actual si no se pasa ninguno)
        año_actual = int(anio_param) if anio_param and anio_param.isdigit() else ahora.year
        # Año comparativo: mismo periodo del año anterior
        año_anterior = año_actual - 1

        # Consulta para clientes
        cursor.execute('''
            SELECT 
                c.idContacto as cliente_id,
                c.razonsocial as cliente_nombre,
                COALESCE(SUM(CASE WHEN strftime('%Y', f.fecha) = ? THEN f.total ELSE 0 END), 0) as total_actual,
                COALESCE(SUM(CASE WHEN strftime('%Y', f.fecha) = ? THEN f.total ELSE 0 END), 0) as total_anterior
            FROM contactos c
            INNER JOIN factura f ON c.idContacto = f.idContacto AND f.estado = 'C'
            GROUP BY c.idContacto, c.razonsocial
            HAVING total_actual > 0
            ORDER BY total_actual DESC
            LIMIT 10
        ''', (str(año_actual), str(año_anterior)))
        
        clientes = []
        for row in cursor.fetchall():
            total_actual = float(row['total_actual'])
            total_anterior = float(row['total_anterior'])
            
            porcentaje = 0
            if total_anterior > 0:
                porcentaje = ((total_actual - total_anterior) / total_anterior) * 100
            elif total_actual > 0:
                porcentaje = 100
            
            clientes.append({
                'id': row['cliente_id'],
                'nombre': row['cliente_nombre'],
                'total_actual': redondear_importe(total_actual),
                'total_anterior': redondear_importe(total_anterior),
                'porcentaje_diferencia': redondear_importe(porcentaje)
            })

        # Consulta para productos
        cursor.execute('''
            SELECT 
                p.id as producto_id,
                p.nombre as producto_nombre,
                COALESCE(SUM(CASE WHEN strftime('%Y', f.fecha) = ? THEN df.cantidad ELSE 0 END), 0) as cantidad_actual,
                COALESCE(SUM(CASE WHEN strftime('%Y', f.fecha) = ? THEN df.total ELSE 0 END), 0) as total_actual,
                COALESCE(SUM(CASE WHEN strftime('%Y', f.fecha) = ? THEN df.cantidad ELSE 0 END), 0) as cantidad_anterior,
                COALESCE(SUM(CASE WHEN strftime('%Y', f.fecha) = ? THEN df.total ELSE 0 END), 0) as total_anterior
            FROM productos p
            LEFT JOIN detalle_factura df ON p.id = df.productoId
            LEFT JOIN factura f ON df.id_factura = f.id AND f.estado = 'C'
            GROUP BY p.id, p.nombre
            HAVING total_actual > 0
            ORDER BY total_actual DESC
            LIMIT 10
        ''', (str(año_actual), str(año_actual), str(año_anterior), str(año_anterior)))
        
        productos = []
        for row in cursor.fetchall():
            total_actual = float(row['total_actual'])
            total_anterior = float(row['total_anterior'])
            
            porcentaje = 0
            if total_anterior > 0:
                porcentaje = ((total_actual - total_anterior) / total_anterior) * 100
            elif total_actual > 0:
                porcentaje = 100
            
            productos.append({
                'id': row['producto_id'],
                'nombre': row['producto_nombre'],
                'cantidad_actual': row['cantidad_actual'],
                'total_actual': redondear_importe(total_actual),
                'cantidad_anterior': row['cantidad_anterior'],
                'total_anterior': redondear_importe(total_anterior),
                'porcentaje_diferencia': redondear_importe(porcentaje)
            })

        return jsonify({
            'año_actual': año_actual,
            'año_anterior': año_anterior,
            'clientes': clientes,
            'productos': productos
        })
        
    except sqlite3.Error as e:
        return jsonify({'error': f"Error en la consulta SQL: {str(e)}"}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# ----------------------- VENTAS MENSUALES POR CLIENTE ----------------------- #
@dashboard_bp.route('/clientes/ventas_mes', methods=['GET'])
@dashboard_bp.route('/api/clientes/ventas_mes', methods=['GET'])
def ventas_cliente_mes():
    """Devuelve las ventas mensuales (facturas cobradas) de un cliente para el año dado."""
    try:
        cliente_id = request.args.get('cliente_id') or request.args.get('id')
        if not cliente_id:
            return jsonify({'error': 'Parámetro cliente_id requerido'}), 400

        anio_param = request.args.get('anio')
        ahora = datetime.now()
        año = int(anio_param) if anio_param and anio_param.isdigit() else ahora.year

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT strftime('%m', fecha) as mes,
                   COALESCE(SUM(total), 0) as total
            FROM factura
            WHERE estado = 'C'
              AND idContacto = ?
              AND strftime('%Y', fecha) = ?
            GROUP BY mes
            ''',
            (cliente_id, str(año))
        )
        filas = cursor.fetchall()
        datos = {row['mes']: float(row['total'] or 0) for row in filas}
        # Asegurar los 12 meses
        datos_completos = {str(m).zfill(2): redondear_importe(datos.get(str(m).zfill(2), 0.0)) for m in range(1, 13)}
        return jsonify(datos_completos)
    except sqlite3.Error as e:
        return jsonify({'error': f"Error en la consulta SQL: {str(e)}"}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass

# ----------------------- VENTAS MENSUALES POR PRODUCTO ----------------------- #
@dashboard_bp.route('/productos/ventas_mes', methods=['GET'])
@dashboard_bp.route('/api/productos/ventas_mes', methods=['GET'])
def ventas_producto_mes():
    """Devuelve la cantidad vendida (unidades) de un producto para cada mes del año dado."""
    try:
        producto_id = request.args.get('producto_id') or request.args.get('id')
        if not producto_id:
            return jsonify({'error': 'Parámetro producto_id requerido'}), 400

        anio_param = request.args.get('anio')
        ahora = datetime.now()
        año = int(anio_param) if anio_param and anio_param.isdigit() else ahora.year

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT mes,
                   SUM(cantidad) AS cantidad,
                   SUM(euros)    AS euros
            FROM (
                SELECT strftime('%m', f.fecha) AS mes,
                       SUM(df.cantidad) AS cantidad,
                       SUM(df.total)    AS euros
                FROM detalle_factura df
                JOIN factura f ON f.id = df.id_factura AND f.estado = 'C'
                WHERE df.productoId = ?
                  AND strftime('%Y', f.fecha) = ?
                GROUP BY mes
                UNION ALL
                SELECT strftime('%m', t.fecha) AS mes,
                       SUM(dt.cantidad) AS cantidad,
                       SUM(dt.total)    AS euros
                FROM detalle_tickets dt
                JOIN tickets t ON t.id = dt.id_ticket AND t.estado = 'C'
                WHERE dt.productoId = ?
                  AND strftime('%Y', t.fecha) = ?
                GROUP BY mes
            )
            GROUP BY mes
            ''',
            (producto_id, str(año), producto_id, str(año))
        )
        filas = cursor.fetchall()
        cantidades = {row['mes']: float(row['cantidad'] or 0) for row in filas}
        euros      = {row['mes']: float(row['euros'] or 0) for row in filas}

        datos_cant = {str(m).zfill(2): cantidades.get(str(m).zfill(2), 0.0) for m in range(1, 13)}
        datos_eur  = {str(m).zfill(2): redondear_importe(euros.get(str(m).zfill(2), 0.0)) for m in range(1, 13)}
        return jsonify({'cantidad': datos_cant, 'euros': datos_eur})
    except sqlite3.Error as e:
        return jsonify({'error': f"Error en la consulta SQL: {str(e)}"}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass

# ----------------------- TOP GASTOS ----------------------- #
@dashboard_bp.route('/gastos/top_gastos', methods=['GET'])
def top_gastos():
    """Devuelve los 10 conceptos de gastos con mayor importe absoluto en el año
    seleccionado y su variación respecto al año anterior."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        anio_param = request.args.get('anio')
        ahora = datetime.now()
        anio_actual = int(anio_param) if anio_param and anio_param.isdigit() else ahora.year
        anio_anterior = anio_actual - 1

        cursor.execute(
            '''
            SELECT lower(concepto) AS concepto,
                   ABS(SUM(CASE WHEN substr(fecha_operacion, 7, 4) = ? THEN importe_eur ELSE 0 END)) AS total_actual,
                   ABS(SUM(CASE WHEN substr(fecha_operacion, 7, 4) = ? THEN importe_eur ELSE 0 END)) AS total_anterior
            FROM gastos
            WHERE importe_eur < 0
            GROUP BY lower(concepto)
            HAVING total_actual > 0
            ORDER BY total_actual DESC
            LIMIT 10
            ''', (str(anio_actual), str(anio_anterior)))

        conceptos = []
        for row in cursor.fetchall():
            total_actual = float(row['total_actual'])
            total_anterior = float(row['total_anterior'])
            porcentaje = 0.0
            if total_anterior > 0:
                porcentaje = ((total_actual - total_anterior) / total_anterior) * 100
            elif total_actual > 0:
                porcentaje = 100.0
            conceptos.append({
                'concepto': row['concepto'],
                'total_actual': redondear_importe(total_actual),
                'total_anterior': redondear_importe(total_anterior),
                'porcentaje_diferencia': redondear_importe(porcentaje)
            })
        return jsonify({'año_actual': anio_actual, 'año_anterior': anio_anterior, 'gastos': conceptos})
    except Exception as e:
        print('ERROR EN /gastos/top_gastos:', str(e))
        print(traceback.format_exc())
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

@dashboard_bp.route('/productos/top_ventas', methods=['GET'])
@dashboard_bp.route('/api/productos/top_ventas', methods=['GET'])
def top_productos_ventas():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        anio_param = request.args.get('anio')
        ahora = datetime.now()
        # Año seleccionado (o el actual si no se pasa ninguno)
        año_actual = int(anio_param) if anio_param and anio_param.isdigit() else ahora.year
        # Año comparativo: mismo periodo del año anterior
        año_anterior = año_actual - 1

        cursor.execute('''
            WITH ventas_facturas AS (
                SELECT 
                    p.id as producto_id,
                    p.nombre as producto_nombre,
                    COALESCE(SUM(CASE WHEN strftime('%Y', f.fecha) = ? THEN df.cantidad ELSE 0 END), 0) as cantidad_actual_f,
                    COALESCE(SUM(CASE WHEN strftime('%Y', f.fecha) = ? THEN df.total ELSE 0 END), 0) as total_actual_f,
                    COALESCE(SUM(CASE WHEN strftime('%Y', f.fecha) = ? THEN df.cantidad ELSE 0 END), 0) as cantidad_anterior_f,
                    COALESCE(SUM(CASE WHEN strftime('%Y', f.fecha) = ? THEN df.total ELSE 0 END), 0) as total_anterior_f
                FROM productos p
                LEFT JOIN detalle_factura df ON p.id = df.productoId
                LEFT JOIN factura f ON df.id_factura = f.id AND f.estado = 'C'
                GROUP BY p.id, p.nombre
            ),
            ventas_tickets AS (
                SELECT 
                    p.id as producto_id,
                    p.nombre as producto_nombre,
                    COALESCE(SUM(CASE WHEN strftime('%Y', t.fecha) = ? THEN dt.cantidad ELSE 0 END), 0) as cantidad_actual_t,
                    COALESCE(SUM(CASE WHEN strftime('%Y', t.fecha) = ? THEN dt.total ELSE 0 END), 0) as total_actual_t,
                    COALESCE(SUM(CASE WHEN strftime('%Y', t.fecha) = ? THEN dt.cantidad ELSE 0 END), 0) as cantidad_anterior_t,
                    COALESCE(SUM(CASE WHEN strftime('%Y', t.fecha) = ? THEN dt.total ELSE 0 END), 0) as total_anterior_t
                FROM productos p
                LEFT JOIN detalle_tickets dt ON p.id = dt.productoId
                LEFT JOIN tickets t ON dt.id_ticket = t.id AND t.estado = 'C'
                GROUP BY p.id, p.nombre
            )
            SELECT 
                vf.producto_id,
                vf.producto_nombre,
                (vf.cantidad_actual_f + COALESCE(vt.cantidad_actual_t, 0)) as cantidad_actual,
                (vf.total_actual_f + COALESCE(vt.total_actual_t, 0)) as total_actual,
                (vf.cantidad_anterior_f + COALESCE(vt.cantidad_anterior_t, 0)) as cantidad_anterior,
                (vf.total_anterior_f + COALESCE(vt.total_anterior_t, 0)) as total_anterior
            FROM ventas_facturas vf
            LEFT JOIN ventas_tickets vt ON vf.producto_id = vt.producto_id
            WHERE (vf.total_actual_f + COALESCE(vt.total_actual_t, 0)) > 0
            ORDER BY total_actual DESC
            LIMIT 10
        ''', (str(año_actual), str(año_actual), str(año_anterior), str(año_anterior), 
             str(año_actual), str(año_actual), str(año_anterior), str(año_anterior)))
        
        productos = []
        for row in cursor.fetchall():
            total_actual = float(row['total_actual'])
            total_anterior = float(row['total_anterior'])
            
            porcentaje = 0
            if total_anterior > 0:
                porcentaje = ((total_actual - total_anterior) / total_anterior) * 100
            elif total_actual > 0:
                porcentaje = 100
            
            productos.append({
                'id': row['producto_id'],
                'nombre': row['producto_nombre'],
                'cantidad_actual': row['cantidad_actual'],
                'total_actual': redondear_importe(total_actual),
                'cantidad_anterior': row['cantidad_anterior'],
                'total_anterior': redondear_importe(total_anterior),
                'porcentaje_diferencia': redondear_importe(porcentaje)
            })

        return jsonify({
            'año_actual': año_actual,
            'año_anterior': año_anterior,
            'productos': productos
        })
        
    except sqlite3.Error as e:
        return jsonify({'error': f"Error en la consulta SQL: {str(e)}"}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()
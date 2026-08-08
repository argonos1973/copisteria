import sqlite3
import traceback
from datetime import datetime

from flask import Blueprint, jsonify, request

from db_utils import get_db_connection, redondear_importe
from logger_config import get_logger
from auth_middleware import login_required

# Inicializar logger
logger = get_logger(__name__)

# Fecha efectiva para facturas: si está cobrada, usar fechaCobro; si no, usar fecha de emisión
FECHA_EFECTIVA_FACTURA = 'fecha'
FECHA_EFECTIVA_COBRADA = "COALESCE(NULLIF(fechaCobro, ''), fecha)"

# Crear Blueprint para las rutas del dashboard
dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/estadisticas_gastos', methods=['GET'])
@dashboard_bp.route('/api/dashboard/estadisticas_gastos', methods=['GET'])
@login_required
def estadisticas_gastos():
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            # DEBUG: Verificar BD conectada
            try:
                cur.execute("PRAGMA database_list")
                dbs = cur.fetchall()
                for db_info in dbs:
                    logger.info(f"[DASHBOARD] BD CONECTADA: {db_info}")
            except Exception as e:
                logger.error(f"[DASHBOARD] Error verificando BD: {e}")
    
            # Parámetros de período seleccionados (año y mes que el usuario ha elegido)
            ahora = datetime.now()
            anio_param = request.args.get('anio')
            mes_param = request.args.get('mes')
            año = int(anio_param) if anio_param and anio_param.isdigit() else ahora.year
            mes = int(mes_param) if mes_param and mes_param.isdigit() else ahora.month

            gasto_empresa_param = request.args.get('gasto_empresa', '1')
            gasto_empresa_filter = ''
            gasto_empresa_params = []
            if gasto_empresa_param != 'todos':
                gasto_empresa_filter = ' AND gasto_empresa = ?'
                gasto_empresa_params = [int(gasto_empresa_param)]

            # Calcular Total Facturado (Tickets + Facturas) del año para INGRESOS
            logger.info(f"[DASHBOARD] Calculando ingresos para año: {año}")
            
            # Tickets - año completo
            cur.execute("""
                SELECT COALESCE(SUM(total), 0) 
                FROM tickets 
                WHERE estado = 'C' AND substr(fecha, 1, 4) = ?
            """, (str(año),))
            res_tickets = cur.fetchone()
            total_tickets_anio = res_tickets[0] if res_tickets else 0
            logger.info(f"[DASHBOARD] Total Tickets Año {año}: {total_tickets_anio}")
            
            # Facturas - año completo
            cur.execute("""
                SELECT COALESCE(SUM(total), 0) 
                FROM factura 
                WHERE estado = 'C' AND substr(fecha, 1, 4) = ?
            """, (str(año),))
            res_facturas = cur.fetchone()
            total_facturas_anio = res_facturas[0] if res_facturas else 0
            logger.info(f"[DASHBOARD] Total Facturas Año {año}: {total_facturas_anio}")
            
            total_ingresos = total_tickets_anio + total_facturas_anio
            logger.info(f"[DASHBOARD] Total Ingresos Calculado: {total_ingresos}")

            # Gastos desde facturas_proveedores (facturas recibidas) - año completo
            cur.execute(f"SELECT COALESCE(SUM(total), 0) FROM facturas_proveedores WHERE año = ?{gasto_empresa_filter}", (año, *gasto_empresa_params))
            total_gastos = cur.fetchone()[0] or 0
            total_gastos = -abs(total_gastos)  # Convertir a negativo para mantener compatibilidad con balance
            
            balance = total_ingresos + total_gastos  # Balance total anual

            # Balance del mes actual
            cur.execute("SELECT MAX(fecha_operacion) FROM gastos")
            ultima_fecha = cur.fetchone()[0]
            
            # Calcular ingresos y gastos del mes actual
            # Ingresos = Facturado en el mes
            cur.execute("""
                SELECT COALESCE(SUM(total), 0) 
                FROM tickets 
                WHERE estado = 'C' AND strftime('%m', fecha) = ? AND strftime('%Y', fecha) = ?
            """, (str(mes).zfill(2), str(año)))
            tickets_mes = cur.fetchone()[0] or 0
            
            cur.execute("""
                SELECT COALESCE(SUM(total), 0) 
                FROM factura 
                WHERE estado = 'C' AND strftime('%m', fecha) = ? AND strftime('%Y', fecha) = ?
            """, (str(mes).zfill(2), str(año)))
            facturas_mes = cur.fetchone()[0] or 0
            
            ingresos_mes_actual = tickets_mes + facturas_mes

            # Gastos del mes desde facturas_proveedores
            cur.execute(f"""
                SELECT COALESCE(SUM(total), 0) FROM facturas_proveedores 
                WHERE año = ? AND substr(fecha_emision, 6, 2) = ?{gasto_empresa_filter}
            """, (año, str(mes).zfill(2), *gasto_empresa_params))
            gastos_mes_actual = cur.fetchone()[0] or 0
            gastos_mes_actual = -abs(gastos_mes_actual)  # Negativo para balance
    
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
        logger.error(f"ERROR EN /estadisticas_gastos: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


def calcular_porcentaje(actual, anterior):
    try:
        if anterior == 0:
            return 100.0 if actual > 0 else 0.0
        return round(((actual - anterior) / anterior) * 100, 2)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 0.0

def get_tickets_data(year):
    query = '''
        SELECT COUNT(*) as num_documentos, 
               COALESCE(AVG(CASE WHEN CAST(strftime('%w', fecha) AS INTEGER) NOT IN (0, 6) THEN total END), 0) as media, 
               COALESCE(SUM(total), 0) as total
        FROM tickets 
        WHERE estado = 'C' AND strftime('%Y', fecha) = ?
    '''
    return fetch_data(query, (str(year),))

def get_tickets_data_mes(year, month):
    query = '''
        SELECT COUNT(*) as num_documentos, 
               COALESCE(AVG(CASE WHEN CAST(strftime('%w', fecha) AS INTEGER) NOT IN (0, 6) THEN total END), 0) as media, 
               COALESCE(SUM(total), 0) as total
        FROM tickets 
        WHERE estado = 'C' AND strftime('%Y', fecha) = ? AND strftime('%m', fecha) = ?
    '''
    # Solo devolvemos datos del mes solicitado, nunca del anterior
    result = fetch_data(query, (str(year), str(month).zfill(2)))
    return result

def get_tickets_data_mes_hasta_dia(year, month, day):
    """Tickets del mes indicado hasta el día indicado (inclusive)"""
    query = '''
        SELECT COUNT(*) as num_documentos, 
               COALESCE(SUM(total), 0) as total
        FROM tickets 
        WHERE estado = 'C' AND strftime('%Y', fecha) = ? AND strftime('%m', fecha) = ?
        AND CAST(strftime('%d', fecha) AS INTEGER) <= ?
    '''
    return fetch_data(query, (str(year), str(month).zfill(2), day))

def get_facturas_data(year):
    query = f'''
        SELECT COUNT(*) as num_documentos, 
               COALESCE(AVG(total), 0) as media, 
               COALESCE(SUM(total), 0) as total
        FROM factura 
        WHERE estado IN ('C', 'P', 'V') AND strftime('%Y', {FECHA_EFECTIVA_FACTURA}) = ?
    '''
    return fetch_data(query, (str(year),))

def get_facturas_data_cobradas(year):
    query = f'''
        SELECT COUNT(*) as num_documentos, 
               COALESCE(AVG(total), 0) as media,
               COALESCE(SUM(total), 0) as total
        FROM factura 
        WHERE estado = 'C' AND strftime('%Y', {FECHA_EFECTIVA_COBRADA}) = ?
    '''
    return fetch_data(query, (str(year),))

def get_facturas_data_mes(year, month):
    query = f'''
        SELECT COUNT(*) as num_documentos, 
               COALESCE(AVG(total), 0) as media, 
               COALESCE(SUM(total), 0) as total
        FROM factura 
        WHERE estado IN ('C', 'P', 'V') AND strftime('%Y', {FECHA_EFECTIVA_FACTURA}) = ? AND strftime('%m', {FECHA_EFECTIVA_FACTURA}) = ?
    '''
    # Solo devolvemos datos del mes solicitado, nunca del anterior
    result = fetch_data(query, (str(year), str(month).zfill(2)))
    return result

def get_facturas_data_mes_cobradas(year, month):
    query = f'''
        SELECT COUNT(*) as num_documentos, 
               COALESCE(AVG(total), 0) as media,
               COALESCE(SUM(total), 0) as total
        FROM factura 
        WHERE estado = 'C' AND strftime('%Y', {FECHA_EFECTIVA_COBRADA}) = ? AND strftime('%m', {FECHA_EFECTIVA_COBRADA}) = ?
    '''
    return fetch_data(query, (str(year), str(month).zfill(2)))

def get_tickets_data_anio_hasta_fecha(year, month, day):
    """Tickets del año indicado hasta la fecha indicada (mes/día inclusive)"""
    query = '''
        SELECT COUNT(*) as num_documentos, 
               COALESCE(SUM(total), 0) as total
        FROM tickets 
        WHERE estado = 'C' AND strftime('%Y', fecha) = ?
        AND (strftime('%m', fecha) < ? OR (strftime('%m', fecha) = ? AND CAST(strftime('%d', fecha) AS INTEGER) <= ?))
    '''
    return fetch_data(query, (str(year), str(month).zfill(2), str(month).zfill(2), day))

def get_facturas_data_anio_hasta_fecha(year, month, day):
    """Facturas del año indicado hasta la fecha indicada (mes/día inclusive)"""
    query = f'''
        SELECT COUNT(*) as num_documentos, 
               COALESCE(SUM(total), 0) as total
        FROM factura 
        WHERE estado IN ('C', 'P', 'V') AND strftime('%Y', {FECHA_EFECTIVA_FACTURA}) = ?
        AND (strftime('%m', {FECHA_EFECTIVA_FACTURA}) < ? OR (strftime('%m', {FECHA_EFECTIVA_FACTURA}) = ? AND CAST(strftime('%d', {FECHA_EFECTIVA_FACTURA}) AS INTEGER) <= ?))
    '''
    return fetch_data(query, (str(year), str(month).zfill(2), str(month).zfill(2), day))

def get_facturas_data_anio_hasta_fecha_cobradas(year, month, day):
    """Facturas cobradas del año hasta la fecha indicada"""
    query = f'''
        SELECT COUNT(*) as num_documentos, 
               COALESCE(AVG(total), 0) as media,
               COALESCE(SUM(total), 0) as total
        FROM factura 
        WHERE estado = 'C' AND strftime('%Y', {FECHA_EFECTIVA_COBRADA}) = ?
        AND (strftime('%m', {FECHA_EFECTIVA_COBRADA}) < ? OR (strftime('%m', {FECHA_EFECTIVA_COBRADA}) = ? AND CAST(strftime('%d', {FECHA_EFECTIVA_COBRADA}) AS INTEGER) <= ?))
    '''
    return fetch_data(query, (str(year), str(month).zfill(2), str(month).zfill(2), day))

def get_facturas_data_mes_hasta_dia(year, month, day):
    """Facturas del mes indicado hasta el día indicado (inclusive)"""
    query = f'''
        SELECT COUNT(*) as num_documentos, 
               COALESCE(SUM(total), 0) as total
        FROM factura 
        WHERE estado IN ('C', 'P', 'V') AND strftime('%Y', {FECHA_EFECTIVA_FACTURA}) = ? AND strftime('%m', {FECHA_EFECTIVA_FACTURA}) = ?
        AND CAST(strftime('%d', {FECHA_EFECTIVA_FACTURA}) AS INTEGER) <= ?
    '''
    return fetch_data(query, (str(year), str(month).zfill(2), day))

def get_facturas_data_mes_hasta_dia_cobradas(year, month, day):
    """Facturas cobradas del mes hasta el día indicado"""
    query = f'''
        SELECT COUNT(*) as num_documentos, 
               COALESCE(AVG(total), 0) as media,
               COALESCE(SUM(total), 0) as total
        FROM factura 
        WHERE estado = 'C' AND strftime('%Y', {FECHA_EFECTIVA_COBRADA}) = ? AND strftime('%m', {FECHA_EFECTIVA_COBRADA}) = ?
        AND CAST(strftime('%d', {FECHA_EFECTIVA_COBRADA}) AS INTEGER) <= ?
    '''
    return fetch_data(query, (str(year), str(month).zfill(2), day))

def get_facturas_data_mes_emitidas_cobradas(year, month):
    """Facturas emitidas y cobradas en el mismo mes"""
    query = '''
        SELECT COUNT(*) as num_documentos, 
               COALESCE(AVG(total), 0) as media,
               COALESCE(SUM(total), 0) as total
        FROM factura 
        WHERE estado = 'C' 
          AND strftime('%Y', fecha) = ? AND strftime('%m', fecha) = ?
          AND strftime('%Y', COALESCE(NULLIF(fechaCobro, ''), fecha)) = ?
          AND strftime('%m', COALESCE(NULLIF(fechaCobro, ''), fecha)) = ?
    '''
    return fetch_data(query, (str(year), str(month).zfill(2), str(year), str(month).zfill(2)))

def get_facturas_data_mes_hasta_dia_emitidas_cobradas(year, month, day):
    """Facturas emitidas y cobradas en el mismo mes hasta el día indicado"""
    query = '''
        SELECT COUNT(*) as num_documentos, 
               COALESCE(AVG(total), 0) as media,
               COALESCE(SUM(total), 0) as total
        FROM factura 
        WHERE estado = 'C' 
          AND strftime('%Y', fecha) = ? AND strftime('%m', fecha) = ?
          AND CAST(strftime('%d', fecha) AS INTEGER) <= ?
          AND strftime('%Y', COALESCE(NULLIF(fechaCobro, ''), fecha)) = ?
          AND strftime('%m', COALESCE(NULLIF(fechaCobro, ''), fecha)) = ?
          AND CAST(strftime('%d', COALESCE(NULLIF(fechaCobro, ''), fecha)) AS INTEGER) <= ?
    '''
    return fetch_data(query, (str(year), str(month).zfill(2), day, str(year), str(month).zfill(2), day))

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
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchone()
            return dict(result) if result else {'num_documentos': 0, 'media': 0, 'total': 0}
    except Exception as e:
        logger.error(f"Error en fetch_data: {str(e)}", exc_info=True)
        return {'num_documentos': 0, 'media': 0, 'total': 0}


@dashboard_bp.route('/ventas/total_mes', methods=['GET'])
@dashboard_bp.route('/api/ventas/total_mes', methods=['GET'])
def ventas_total_mes():
    """Devuelve totales mensuales de tickets, facturas y su global para un año dado."""
    anio_param = request.args.get('anio')
    ahora = datetime.now()
    año = int(anio_param) if anio_param and anio_param.isdigit() else ahora.year

    with get_db_connection() as conn:
        cursor = conn.cursor()

        def obtener_totales(tabla, solo_cobradas=False):
            if tabla == 'factura' and not solo_cobradas:
                estado_filter = "estado IN ('C', 'P', 'V')"
                fecha_expr = FECHA_EFECTIVA_FACTURA
            else:
                estado_filter = "estado = 'C'"
                fecha_expr = FECHA_EFECTIVA_COBRADA if tabla == 'factura' else 'fecha'
            cursor.execute(
                f"""
                SELECT strftime('%m', {fecha_expr}) as mes, COALESCE(SUM(total),0) as total
                FROM {tabla}
                WHERE {estado_filter} AND strftime('%Y', {fecha_expr}) = ?
                GROUP BY mes
                """,
                (str(año),)
            )
            datos = {row['mes']: float(row['total'] or 0) for row in cursor.fetchall()}
            # Asegurar 12 meses presentes con 0
            return {str(m).zfill(2): datos.get(str(m).zfill(2), 0.0) for m in range(1,13)}

        tickets = obtener_totales('tickets')
        facturas = obtener_totales('factura', solo_cobradas=True)
    
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


@dashboard_bp.route('/ventas/total_dia_semana', methods=['GET'])
@dashboard_bp.route('/api/ventas/total_dia_semana', methods=['GET'])
def ventas_total_dia_semana():
    """Devuelve totales por cada día del mes (1..día_actual) para el mes/año dado
    y el mismo mes del año anterior. Para líneas comparativas día a día."""
    anio_param = request.args.get('anio')
    mes_param = request.args.get('mes')
    ahora = datetime.now()
    año = int(anio_param) if anio_param and anio_param.isdigit() else ahora.year
    mes = int(mes_param) if mes_param and mes_param.isdigit() else ahora.month

    # Hasta qué día mostrar: si es el mes actual, hasta hoy; si no, mes completo
    import calendar
    if año == ahora.year and mes == ahora.month:
        dia_hasta = ahora.day
    else:
        dia_hasta = calendar.monthrange(año, mes)[1]

    # Días del mes anterior (completo)
    año_anterior = año - 1
    dias_mes_anterior = calendar.monthrange(año_anterior, mes)[1]

    with get_db_connection() as conn:
        cursor = conn.cursor()

        def obtener_por_dia(tabla, año_q, mes_q, max_dia, solo_cobradas=False):
            if tabla == 'factura' and not solo_cobradas:
                estado_filter = "estado IN ('C', 'P', 'V')"
                fecha_expr = FECHA_EFECTIVA_FACTURA
            else:
                estado_filter = "estado = 'C'"
                fecha_expr = FECHA_EFECTIVA_COBRADA if tabla == 'factura' else 'fecha'
            cursor.execute(
                f"""
                SELECT CAST(strftime('%d', {fecha_expr}) AS INTEGER) as dia,
                       COALESCE(SUM(total), 0) as total,
                       COUNT(*) as cantidad
                FROM {tabla}
                WHERE {estado_filter}
                  AND strftime('%Y', {fecha_expr}) = ?
                  AND strftime('%m', {fecha_expr}) = ?
                  AND CAST(strftime('%d', {fecha_expr}) AS INTEGER) <= ?
                GROUP BY dia
                """,
                (str(año_q), str(mes_q).zfill(2), max_dia)
            )
            raw = {row['dia']: {'total': float(row['total'] or 0), 'cantidad': int(row['cantidad'] or 0)} for row in cursor.fetchall()}
            result = {}
            for d in range(1, max_dia + 1):
                v = raw.get(d, {'total': 0, 'cantidad': 0})
                result[str(d)] = {'total': redondear_importe(v['total']), 'cantidad': v['cantidad']}
            return result

        tickets_actual = obtener_por_dia('tickets', año, mes, dia_hasta)
        facturas_actual = obtener_por_dia('factura', año, mes, dia_hasta)
        facturas_actual_cobradas = obtener_por_dia('factura', año, mes, dia_hasta, solo_cobradas=True)
        tickets_anterior = obtener_por_dia('tickets', año_anterior, mes, dias_mes_anterior)
        facturas_anterior = obtener_por_dia('factura', año_anterior, mes, dias_mes_anterior)
        facturas_anterior_cobradas = obtener_por_dia('factura', año_anterior, mes, dias_mes_anterior, solo_cobradas=True)

        # Calcular globales (solo facturas cobradas)
        global_actual = {}
        for d in range(1, dia_hasta + 1):
            k = str(d)
            global_actual[k] = {
                'total': redondear_importe(tickets_actual[k]['total'] + facturas_actual_cobradas[k]['total']),
                'cantidad': tickets_actual[k]['cantidad'] + facturas_actual_cobradas[k]['cantidad']
            }
        global_anterior = {}
        for d in range(1, dias_mes_anterior + 1):
            k = str(d)
            global_anterior[k] = {
                'total': redondear_importe(tickets_anterior[k]['total'] + facturas_anterior_cobradas[k]['total']),
                'cantidad': tickets_anterior[k]['cantidad'] + facturas_anterior_cobradas[k]['cantidad']
            }

    return jsonify({
        'anio': año,
        'anio_anterior': año_anterior,
        'mes': mes,
        'dia_hasta': dia_hasta,
        'dias_mes_anterior': dias_mes_anterior,
        'tickets': {'actual': tickets_actual, 'anterior': tickets_anterior},
        'facturas': {'actual': facturas_actual, 'anterior': facturas_anterior},
        'global': {'actual': global_actual, 'anterior': global_anterior}
    })


@dashboard_bp.route('/ventas/total_semana', methods=['GET'])
@dashboard_bp.route('/api/ventas/total_semana', methods=['GET'])
def ventas_total_semana():
    """Devuelve totales por semana ISO (lunes a domingo) del año indicado y del
    año anterior. Las semanas se numeran 1..53 según strftime('%W') (lunes como
    primer día de la semana). Para líneas comparativas semana a semana."""
    anio_param = request.args.get('anio')
    ahora = datetime.now()
    año = int(anio_param) if anio_param and anio_param.isdigit() else ahora.year
    año_anterior = año - 1

    # Hasta qué semana mostrar: si es el año actual, hasta la semana en curso
    semana_actual_now = int(ahora.strftime('%W')) or 1
    if año == ahora.year:
        semana_hasta = max(1, semana_actual_now)
    else:
        semana_hasta = 53
    semanas_anio_anterior = 53

    # Año anterior HASTA la misma fecha exacta (para alinear con el dashboard)
    tickets_anio_anterior_hasta_fecha = get_tickets_data_anio_hasta_fecha(año_anterior, ahora.month, ahora.day)
    facturas_anio_anterior_hasta_fecha = get_facturas_data_anio_hasta_fecha(año_anterior, ahora.month, ahora.day)
    facturas_anio_anterior_hasta_fecha_cobradas = get_facturas_data_anio_hasta_fecha_cobradas(año_anterior, ahora.month, ahora.day)
    global_anio_anterior_hasta_fecha_total = tickets_anio_anterior_hasta_fecha['total'] + facturas_anio_anterior_hasta_fecha_cobradas['total']

    # Semana que contiene la fecha de corte del año anterior
    try:
        fecha_corte_anterior = ahora.replace(year=año_anterior)
    except ValueError:
        # 29 de febrero en año no bisiesto
        fecha_corte_anterior = ahora.replace(year=año_anterior, day=ahora.day - 1)
    semana_hasta_anterior = max(1, int(fecha_corte_anterior.strftime('%W')) or 1)

    with get_db_connection() as conn:
        cursor = conn.cursor()

        def obtener_por_semana(tabla, año_q, max_semana, solo_cobradas=False):
            if tabla == 'factura' and not solo_cobradas:
                estado_filter = "estado IN ('C', 'P', 'V')"
                fecha_expr = FECHA_EFECTIVA_FACTURA
            else:
                estado_filter = "estado = 'C'"
                fecha_expr = FECHA_EFECTIVA_COBRADA if tabla == 'factura' else 'fecha'
            cursor.execute(
                f"""
                SELECT CAST(strftime('%W', {fecha_expr}) AS INTEGER) as semana,
                       COALESCE(SUM(total), 0) as total,
                       COUNT(*) as cantidad
                FROM {tabla}
                WHERE {estado_filter}
                  AND strftime('%Y', {fecha_expr}) = ?
                GROUP BY semana
                """,
                (str(año_q),)
            )
            raw = {}
            for row in cursor.fetchall():
                # strftime('%W') devuelve 00..53; la semana 0 (días previos al
                # primer lunes) se agrupa en la semana 1.
                s = int(row['semana'] or 0)
                if s < 1:
                    s = 1
                acc = raw.setdefault(s, {'total': 0.0, 'cantidad': 0})
                acc['total'] += float(row['total'] or 0)
                acc['cantidad'] += int(row['cantidad'] or 0)
            result = {}
            for s in range(1, max_semana + 1):
                v = raw.get(s, {'total': 0, 'cantidad': 0})
                result[str(s)] = {'total': redondear_importe(v['total']), 'cantidad': v['cantidad']}
            return result

        tickets_actual = obtener_por_semana('tickets', año, semana_hasta)
        facturas_actual = obtener_por_semana('factura', año, semana_hasta)
        facturas_actual_cobradas = obtener_por_semana('factura', año, semana_hasta, solo_cobradas=True)
        tickets_anterior = obtener_por_semana('tickets', año_anterior, semanas_anio_anterior)
        facturas_anterior = obtener_por_semana('factura', año_anterior, semanas_anio_anterior)
        facturas_anterior_cobradas = obtener_por_semana('factura', año_anterior, semanas_anio_anterior, solo_cobradas=True)

        def combinar_global(tix, fac, max_semana):
            g = {}
            for s in range(1, max_semana + 1):
                k = str(s)
                g[k] = {
                    'total': redondear_importe(tix[k]['total'] + fac[k]['total']),
                    'cantidad': tix[k]['cantidad'] + fac[k]['cantidad']
                }
            return g

        global_actual = combinar_global(tickets_actual, facturas_actual_cobradas, semana_hasta)
        global_anterior = combinar_global(tickets_anterior, facturas_anterior_cobradas, semanas_anio_anterior)

    return jsonify({
        'anio': año,
        'anio_anterior': año_anterior,
        'semana_hasta': semana_hasta,
        'semanas_anio_anterior': semanas_anio_anterior,
        'semana_hasta_anterior': semana_hasta_anterior,
        'global_anterior_hasta_fecha': {
            'total': redondear_importe(global_anio_anterior_hasta_fecha_total),
            'semana': semana_hasta_anterior,
            'dia': ahora.day,
            'mes': ahora.month
        },
        'tickets': {'actual': tickets_actual, 'anterior': tickets_anterior},
        'facturas': {'actual': facturas_actual, 'anterior': facturas_anterior},
        'global': {'actual': global_actual, 'anterior': global_anterior}
    })


@dashboard_bp.route('/ventas/cantidad_mes', methods=['GET'])
@dashboard_bp.route('/api/ventas/cantidad_mes', methods=['GET'])
def ventas_cantidad_mes():
    """Devuelve cantidades mensuales de tickets, facturas y su global para un año dado."""
    anio_param = request.args.get('anio')
    ahora = datetime.now()
    año = int(anio_param) if anio_param and anio_param.isdigit() else ahora.year

    with get_db_connection() as conn:
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
    facturas_actual = get_facturas_data_cobradas(año_actual)
    proformas_actual = get_proformas_data(año_actual)

    # Obtener datos del mes actual (sin proformas)
    tickets_mes_actual = get_tickets_data_mes(año_actual, mes_actual)
    facturas_mes_actual = get_facturas_data_mes_cobradas(año_actual, mes_actual)
    proformas_mes_actual = get_proformas_data_mes(año_actual, mes_actual)
    
    # Obtener datos del período comparativo (selector)
    tickets_mes_anterior = get_tickets_data_mes(año_anterior, mes_selector)
    facturas_mes_anterior = get_facturas_data_mes_cobradas(año_anterior, mes_selector)
    proformas_mes_anterior = get_proformas_data_mes(año_anterior, mes_selector)

    # Mismo mes año anterior HASTA el día actual (comparación justa)
    dia_actual = ahora.day
    tickets_mes_anterior_hasta_dia = get_tickets_data_mes_hasta_dia(año_anterior, mes_selector, dia_actual)
    facturas_mes_anterior_hasta_dia = get_facturas_data_mes_hasta_dia_cobradas(año_anterior, mes_selector, dia_actual)
    facturas_mes_anterior_hasta_dia_emitidas_cobradas = get_facturas_data_mes_hasta_dia_emitidas_cobradas(año_anterior, mes_selector, dia_actual)
    global_mes_anterior_hasta_dia_total = tickets_mes_anterior_hasta_dia['total'] + facturas_mes_anterior_hasta_dia['total']

    # Año anterior HASTA la misma fecha (mes/día) para comparación justa del total anual
    tickets_anio_anterior_hasta_fecha = get_tickets_data_anio_hasta_fecha(año_anterior, mes_actual, dia_actual)
    facturas_anio_anterior_hasta_fecha = get_facturas_data_anio_hasta_fecha_cobradas(año_anterior, mes_actual, dia_actual)
    global_anio_anterior_hasta_fecha_total = tickets_anio_anterior_hasta_fecha['total'] + facturas_anio_anterior_hasta_fecha['total']

    # Calcular totales globales del mes (solo cobradas para global)
    global_mes_actual_total = tickets_mes_actual['total'] + facturas_mes_actual['total']
    global_mes_anterior_total = tickets_mes_anterior['total'] + facturas_mes_anterior['total']

    # Facturas emitidas y cobradas en el mes (para visualización diferenciada)
    facturas_mes_actual_emitidas_cobradas = get_facturas_data_mes_emitidas_cobradas(año_actual, mes_actual)
    facturas_mes_anterior_emitidas_cobradas = get_facturas_data_mes_emitidas_cobradas(año_anterior, mes_selector)

    # Obtener datos anteriores (proformas solo para su sección)
    tickets_anterior = get_tickets_data(año_anterior)
    facturas_anterior = get_facturas_data_cobradas(año_anterior)
    proformas_anterior = get_proformas_data(año_anterior)

    # Calcular totales globales SIN PROFORMAS (solo facturas cobradas)
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

    # Procesar facturas (cobradas)
    facturas_media_mensual = calcular_media_mensual_excluyendo_mes_actual(facturas_actual['total'] - facturas_mes_actual['total'], mes_actual)
    facturas_media = facturas_actual['media'] if facturas_actual['num_documentos'] > 0 else 0

    # Facturas porcentajes mes (emitidas y cobradas)
    porcentaje_diferencia_mes_emitidas_cobradas = redondear_importe(
        calcular_porcentaje(
            facturas_mes_actual_emitidas_cobradas['total'], 
            facturas_mes_anterior_emitidas_cobradas['total']
        )
    )
    porcentaje_diferencia_mes_hasta_dia_emitidas_cobradas = redondear_importe(
        calcular_porcentaje(
            facturas_mes_actual_emitidas_cobradas['total'], 
            facturas_mes_anterior_hasta_dia_emitidas_cobradas['total']
        )
    )

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
    global_media_mensual_anterior = calcular_media_mensual_excluyendo_mes_actual(global_anio_anterior_hasta_fecha_total - global_mes_anterior_hasta_dia_total, mes_actual)

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
                    tickets_anio_anterior_hasta_fecha['total']
                )
            ),
            'porcentaje_diferencia_mes': redondear_importe(
                calcular_porcentaje(
                    tickets_mes_actual['total'], 
                    tickets_mes_anterior['total']
                )
            ),
            'porcentaje_diferencia_mes_hasta_dia': redondear_importe(
                calcular_porcentaje(
                    tickets_mes_actual['total'],
                    tickets_mes_anterior_hasta_dia['total']
                )
            ),
            'mismo_mes_hasta_dia': {
                'total': redondear_importe(tickets_mes_anterior_hasta_dia['total']),
                'dia': dia_actual
            },
            'porcentaje_diferencia_anio_hasta_fecha': redondear_importe(
                calcular_porcentaje(
                    tickets_actual['total'],
                    tickets_anio_anterior_hasta_fecha['total']
                )
            ),
            'anio_anterior_hasta_fecha': {
                'total': redondear_importe(tickets_anio_anterior_hasta_fecha['total']),
                'dia': dia_actual,
                'mes': mes_actual
            }
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
                },
                'mes_actual_emitidas_cobradas': {
                    'total': redondear_importe(facturas_mes_actual_emitidas_cobradas['total']),
                    'cantidad': facturas_mes_actual_emitidas_cobradas['num_documentos']
                }
            },
            'anterior': {
                'total': redondear_importe(facturas_anterior['total']),
                'media': redondear_importe(facturas_anterior['media']),
                'cantidad': facturas_anterior['num_documentos'],
                'mismo_mes': {
                    'total': redondear_importe(facturas_mes_anterior['total']),
                    'cantidad': facturas_mes_anterior['num_documentos']
                },
                'mismo_mes_emitidas_cobradas': {
                    'total': redondear_importe(facturas_mes_anterior_emitidas_cobradas['total']),
                    'cantidad': facturas_mes_anterior_emitidas_cobradas['num_documentos']
                }
            },
            'porcentaje_diferencia': redondear_importe(
                calcular_porcentaje(
                    facturas_actual['total'], 
                    facturas_anio_anterior_hasta_fecha['total']
                )
            ),
            'porcentaje_diferencia_mes': redondear_importe(
                calcular_porcentaje(
                    facturas_mes_actual['total'], 
                    facturas_mes_anterior['total']
                )
            ),
            'porcentaje_diferencia_mes_hasta_dia': redondear_importe(
                calcular_porcentaje(
                    facturas_mes_actual['total'],
                    facturas_mes_anterior_hasta_dia['total']
                )
            ),
            'mismo_mes_hasta_dia': {
                'total': redondear_importe(facturas_mes_anterior_hasta_dia['total']),
                'dia': dia_actual
            },
            'porcentaje_diferencia_mes_emitidas_cobradas': redondear_importe(porcentaje_diferencia_mes_emitidas_cobradas),
            'porcentaje_diferencia_mes_hasta_dia_emitidas_cobradas': redondear_importe(porcentaje_diferencia_mes_hasta_dia_emitidas_cobradas),
            'mismo_mes_hasta_dia_emitidas_cobradas': {
                'total': redondear_importe(facturas_mes_anterior_hasta_dia_emitidas_cobradas['total']),
                'dia': dia_actual
            },
            'porcentaje_diferencia_anio_hasta_fecha': redondear_importe(
                calcular_porcentaje(
                    facturas_actual['total'],
                    facturas_anio_anterior_hasta_fecha['total']
                )
            ),
            'anio_anterior_hasta_fecha': {
                'total': redondear_importe(facturas_anio_anterior_hasta_fecha['total']),
                'dia': dia_actual,
                'mes': mes_actual
            }
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
            ), # Proformas: no hay YTD anterior disponible, mantener comparacion anual
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
                'media_mensual': redondear_importe(global_media_mensual_anterior),
                'cantidad': tickets_anterior['num_documentos'] + facturas_anterior['num_documentos'],
                'mismo_mes': {
                    'total': redondear_importe(global_mes_anterior_total),
                    'cantidad': tickets_mes_anterior['num_documentos'] + facturas_mes_anterior['num_documentos']
                }
            },
            'porcentaje_diferencia': redondear_importe(calcular_porcentaje(global_actual_total, global_anio_anterior_hasta_fecha_total)),
            'porcentaje_diferencia_mes': redondear_importe(calcular_porcentaje(global_mes_actual_total, global_mes_anterior_total)),
            'porcentaje_diferencia_mes_hasta_dia': redondear_importe(calcular_porcentaje(global_mes_actual_total, global_mes_anterior_hasta_dia_total)),
            'mismo_mes_hasta_dia': {
                'total': redondear_importe(global_mes_anterior_hasta_dia_total),
                'dia': dia_actual
            },
            'porcentaje_diferencia_anio_hasta_fecha': redondear_importe(calcular_porcentaje(global_actual_total, global_anio_anterior_hasta_fecha_total)),
            'anio_anterior_hasta_fecha': {
                'total': redondear_importe(global_anio_anterior_hasta_fecha_total),
                'dia': dia_actual,
                'mes': mes_actual
            }
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
        anio_param = request.args.get('anio')
        ahora = datetime.now()
        # Año seleccionado (o el actual si no se pasa ninguno)
        año_actual = int(anio_param) if anio_param and anio_param.isdigit() else ahora.year
        # Año comparativo: mismo periodo del año anterior
        año_anterior = año_actual - 1

        with get_db_connection() as conn:
            cursor = conn.cursor()
            
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

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT strftime('%m', fechaCobro) as mes,
                       COALESCE(SUM(total), 0) as total
                FROM factura
                WHERE estado = 'C'
                  AND idContacto = ?
                  AND strftime('%Y', fechaCobro) = ?
                  AND fechaCobro IS NOT NULL
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

# ----------------------- VENTAS MENSUALES POR PRODUCTO ----------------------- #
@dashboard_bp.route('/productos/ventas_mes', methods=['GET'])
@dashboard_bp.route('/api/productos/ventas_mes', methods=['GET'])
def ventas_producto_mes():
    """Devuelve la cantidad vendida (unidades) de un producto para cada mes del año dado.
    Busca por NOMBRE del producto para evitar problemas con IDs duplicados."""
    try:
        producto_id = request.args.get('producto_id') or request.args.get('id')
        if not producto_id:
            return jsonify({'error': 'Parámetro producto_id requerido'}), 400

        anio_param = request.args.get('anio')
        ahora = datetime.now()
        año = int(anio_param) if anio_param and anio_param.isdigit() else ahora.year

        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Primero obtener el nombre del producto
            cursor.execute('SELECT nombre FROM productos WHERE id = ?', (producto_id,))
            prod_row = cursor.fetchone()
            if not prod_row:
                return jsonify({'error': 'Producto no encontrado'}), 404
            
            nombre_producto = prod_row['nombre'].strip().upper()
            
            # Buscar por NOMBRE (TRIM UPPER) para incluir productos duplicados
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
                    WHERE TRIM(UPPER(df.concepto)) = ?
                      AND strftime('%Y', f.fecha) = ?
                    GROUP BY mes
                    UNION ALL
                    SELECT strftime('%m', t.fecha) AS mes,
                           SUM(dt.cantidad) AS cantidad,
                           SUM(dt.total)    AS euros
                    FROM detalle_tickets dt
                    JOIN tickets t ON t.id = dt.id_ticket AND t.estado = 'C'
                    WHERE TRIM(UPPER(dt.concepto)) = ?
                      AND strftime('%Y', t.fecha) = ?
                    GROUP BY mes
                )
                GROUP BY mes
                ''',
                (nombre_producto, str(año), nombre_producto, str(año))
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
        logger.error(f"ERROR EN /gastos/top_gastos: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
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

        # Consulta que agrupa por NOMBRE (TRIM) para comparar entre años
        # Usa UNION para evitar producto cartesiano entre facturas y tickets
        cursor.execute('''
            WITH ventas AS (
                SELECT TRIM(dt.concepto) as producto_nombre, 
                       strftime('%Y', t.fecha) as anio,
                       SUM(dt.cantidad) as cantidad,
                       SUM(dt.total) as total
                FROM detalle_tickets dt
                JOIN tickets t ON dt.id_ticket = t.id AND t.estado = 'C'
                WHERE strftime('%Y', t.fecha) IN (?, ?)
                GROUP BY TRIM(dt.concepto), strftime('%Y', t.fecha)
                UNION ALL
                SELECT TRIM(df.concepto) as producto_nombre,
                       strftime('%Y', f.fecha) as anio,
                       SUM(df.cantidad) as cantidad,
                       SUM(df.total) as total
                FROM detalle_factura df
                JOIN factura f ON df.id_factura = f.id AND f.estado = 'C'
                WHERE strftime('%Y', f.fecha) IN (?, ?)
                GROUP BY TRIM(df.concepto), strftime('%Y', f.fecha)
            )
            SELECT 
                UPPER(MAX(producto_nombre)) as producto_nombre,
                SUM(CASE WHEN anio = ? THEN cantidad ELSE 0 END) as cantidad_actual,
                SUM(CASE WHEN anio = ? THEN total ELSE 0 END) as total_actual,
                SUM(CASE WHEN anio = ? THEN cantidad ELSE 0 END) as cantidad_anterior,
                SUM(CASE WHEN anio = ? THEN total ELSE 0 END) as total_anterior
            FROM ventas
            WHERE TRIM(LOWER(producto_nombre)) IN (
                SELECT TRIM(LOWER(nombre)) FROM productos WHERE nombre IS NOT NULL
            )
            AND TRIM(LOWER(producto_nombre)) != 'libre'
            GROUP BY TRIM(LOWER(producto_nombre))
            HAVING total_actual > 0
            ORDER BY total_actual DESC
            LIMIT 10
        ''', (str(año_actual), str(año_anterior), str(año_actual), str(año_anterior),
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
            
            # Buscar el ID del producto más reciente (ejercicio actual) en la tabla productos
            producto_id = 0
            nombre_producto = row['producto_nombre']
            cursor.execute('SELECT MAX(id) as id FROM productos WHERE TRIM(LOWER(nombre)) = TRIM(LOWER(?) COLLATE NOCASE)', (nombre_producto,))
            prod_row = cursor.fetchone()
            if prod_row and prod_row['id']:
                producto_id = prod_row['id']
            
            productos.append({
                'id': producto_id,
                'nombre': nombre_producto,
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
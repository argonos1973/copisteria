from datetime import datetime
from traceback import format_exc

from flask import Blueprint, jsonify, request

from db_utils import get_db_connection

gastos_bp = Blueprint('gastos', __name__)


@gastos_bp.route('/ingresos_gastos_mes', methods=['GET'])
def ingresos_gastos_mes():
    """Devuelve los ingresos y gastos (suma de importes positivos y negativos)
    para cada mes de un año concreto. Formato de respuesta:
    {
        "anio": 2025,
        "ingresos": {"01": 1234.5, ... "12": 0},
        "gastos":   {"01": -987.6, ... "12": 0}
    }
    """
    try:
        ahora = datetime.now()
        anio_param = request.args.get('anio')
        anio = int(anio_param) if anio_param and anio_param.isdigit() else ahora.year

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT substr(fecha_operacion, 4, 2) as mes,
                   SUM(CASE WHEN importe_eur > 0 THEN importe_eur ELSE 0 END) as ingresos,
                   SUM(CASE WHEN importe_eur < 0 THEN importe_eur ELSE 0 END) as gastos
            FROM gastos
            WHERE substr(fecha_operacion, 7, 4) = ?
            GROUP BY mes
            """,
            (str(anio),)
        )
        rows = cur.fetchall()
        conn.close()

        # Inicializar diccionarios con meses en 0
        ingresos = {str(m).zfill(2): 0.0 for m in range(1, 13)}
        gastos = {str(m).zfill(2): 0.0 for m in range(1, 13)}

        for r in rows:
            mes = str(r['mes']).zfill(2)
            ingresos[mes] = float(r['ingresos'] or 0)
            gastos[mes] = float(r['gastos'] or 0)

        return jsonify({
            'anio': anio,
            'ingresos': ingresos,
            'gastos': gastos
        })
    except Exception as e:
        print('ERROR EN /ingresos_gastos_mes:', str(e))
        print(format_exc())
        return jsonify({'error': str(e), 'trace': format_exc()}), 500

@gastos_bp.route('/gastos', methods=['GET'])
@gastos_bp.route('/api/gastos', methods=['GET'])
def consulta_gastos():
    try:
        fecha_inicio = request.args.get('fecha_inicio', '')
        if not fecha_inicio:
            hoy = datetime.now()
            fecha_inicio = hoy.strftime('%Y-%m-01')
        fecha_fin = request.args.get('fecha_fin', '')
        concepto = request.args.get('concepto', '')
        tipo = request.args.get('tipo', 'todos')

        query = "SELECT fecha_operacion, fecha_valor, concepto, importe_eur FROM gastos WHERE 1=1"
        params = []
        if fecha_inicio:
            query += " AND date(substr(fecha_operacion,7,4)||'-'||substr(fecha_operacion,4,2)||'-'||substr(fecha_operacion,1,2)) >= ?"
            params.append(fecha_inicio)
        if fecha_fin:
            query += " AND date(substr(fecha_operacion,7,4)||'-'||substr(fecha_operacion,4,2)||'-'||substr(fecha_operacion,1,2)) <= ?"
            params.append(fecha_fin)
        if concepto:
            query += " AND lower(concepto) LIKE ?"
            params.append(f'%{concepto.lower()}%')
        if tipo == 'ingresos':
            query += " AND importe_eur > 0"
        elif tipo == 'gastos':
            query += " AND importe_eur < 0"
        # Ordenar por fecha_valor (transformada a formato ISO para orden cronológico correcto)
        query += " ORDER BY date(substr(fecha_valor,7,4)||'-'||substr(fecha_valor,4,2)||'-'||substr(fecha_valor,1,2)) DESC"

        conn = get_db_connection()
        gastos = conn.execute(query, params).fetchall()
        conn.close()
        # Validar y limpiar resultados
        gastos_list = []
        total_negativos = 0.0
        total_positivos = 0.0
        for g in gastos:
            try:
                importe = float(g['importe_eur']) if g['importe_eur'] is not None else 0.0
            except Exception:
                importe = 0.0
            if importe < 0:
                total_negativos += importe
            elif importe > 0:
                total_positivos += importe
            gastos_list.append({
                'fecha_operacion': g['fecha_operacion'],
                'fecha_valor': g['fecha_valor'],
                'concepto': g['concepto'],
                'importe_eur': importe
            })
        diferencia = total_positivos + total_negativos
        return jsonify({
            'gastos': gastos_list,
            'total_negativos': total_negativos,
            'total_positivos': total_positivos,
            'diferencia': diferencia
        })
    except Exception as e:
        print('ERROR EN CONSULTA_GASTOS:', str(e))
        print(format_exc())
        return jsonify({'error': str(e), 'trace': format_exc()}), 500


# -------------------------------------------------------------------------
#  NUEVO ENDPOINT: INGRESOS Y GASTOS TOTALES POR AÑO
# -------------------------------------------------------------------------
@gastos_bp.route('/ingresos_gastos_totales', methods=['GET'])
@gastos_bp.route('/api/ingresos_gastos_totales', methods=['GET'])
def ingresos_gastos_totales():
    """Totales anuales de ingresos y gastos y variación vs. año anterior."""
    try:
        ahora = datetime.now()
        anio_param = request.args.get('anio')
        anio_actual = int(anio_param) if anio_param and anio_param.isdigit() else ahora.year
        anio_anterior = anio_actual - 1

        conn = get_db_connection()
        cur = conn.cursor()

        def totales(anio:int):
            cur.execute(
                """
                SELECT 
                    SUM(CASE WHEN importe_eur > 0 THEN importe_eur ELSE 0 END) AS ingresos,
                    SUM(CASE WHEN importe_eur < 0 THEN importe_eur ELSE 0 END) AS gastos
                FROM gastos
                WHERE substr(fecha_operacion, 7, 4) = ?
                """,
                (str(anio),)
            )
            row = cur.fetchone() or {'ingresos':0,'gastos':0}
            return float(row['ingresos'] or 0), float(row['gastos'] or 0)

        ingresos_act, gastos_act = totales(anio_actual)
        ingresos_prev, gastos_prev = totales(anio_anterior)

        def pct(actual:float, prev:float):
            if prev == 0:
                return 100.0 if actual != 0 else 0.0
            return ((actual - prev) / prev) * 100

        pct_ingresos = pct(ingresos_act, ingresos_prev)
        pct_gastos   = pct(abs(gastos_act), abs(gastos_prev))

        return jsonify({
            'año_actual': anio_actual,
            'año_anterior': anio_anterior,
            'ingresos': {
                'total_actual': ingresos_act,
                'total_anterior': ingresos_prev,
                'porcentaje_diferencia': pct_ingresos
            },
            'gastos': {
                'total_actual': gastos_act,
                'total_anterior': gastos_prev,
                'porcentaje_diferencia': pct_gastos
            }
        })
    except Exception as e:
        print('ERROR EN /ingresos_gastos_totales:', str(e))
        print(format_exc())
        return jsonify({'error': str(e), 'trace': format_exc()}), 500

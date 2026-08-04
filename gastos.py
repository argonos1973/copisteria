from datetime import datetime
from traceback import format_exc

from flask import Blueprint, jsonify, request

from db_utils import get_db_connection
from logger_config import get_logger

# Inicializar logger
logger = get_logger(__name__)

gastos_bp = Blueprint('gastos', __name__)


@gastos_bp.route('/ingresos_gastos_mes', methods=['GET'])
@gastos_bp.route('/api/ingresos_gastos_mes', methods=['GET'])
def ingresos_gastos_mes():
    """Devuelve los ingresos (facturas + tickets) y gastos (tabla gastos)
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

        gasto_empresa_param = request.args.get('gasto_empresa', '1')
        gasto_empresa_filter = ''
        gasto_empresa_params = []
        if gasto_empresa_param != 'todos':
            gasto_empresa_filter = ' AND gasto_empresa = ?'
            gasto_empresa_params = [int(gasto_empresa_param)]

        conn = get_db_connection()
        cur = conn.cursor()
        
        # Inicializar diccionarios con meses en 0
        ingresos = {str(m).zfill(2): 0.0 for m in range(1, 13)}
        gastos_dict = {str(m).zfill(2): 0.0 for m in range(1, 13)}
        
        # INGRESOS: Facturas emitidas (formato fecha: YYYY-MM-DD)
        cur.execute(
            """
            SELECT substr(fecha, 6, 2) as mes,
                   SUM(total) as total_facturas
            FROM factura
            WHERE substr(fecha, 1, 4) = ?
            GROUP BY mes
            """,
            (str(anio),)
        )
        for r in cur.fetchall():
            mes = str(r['mes']).zfill(2)
            ingresos[mes] += float(r['total_facturas'] or 0)
        
        # INGRESOS: Tickets (formato fecha: YYYY-MM-DD)
        cur.execute(
            """
            SELECT substr(fecha, 6, 2) as mes,
                   SUM(total) as total_tickets
            FROM tickets
            WHERE substr(fecha, 1, 4) = ?
            GROUP BY mes
            """,
            (str(anio),)
        )
        for r in cur.fetchall():
            mes = str(r['mes']).zfill(2)
            ingresos[mes] += float(r['total_tickets'] or 0)
        
        # GASTOS: Desde facturas_proveedores (formato fecha_emision: YYYY-MM-DD)
        cur.execute(
            f"""
            SELECT substr(fecha_emision, 6, 2) as mes,
                   SUM(total) as total_gastos
            FROM facturas_proveedores
            WHERE año = ?{gasto_empresa_filter}
            GROUP BY mes
            """,
            (anio, *gasto_empresa_params)
        )
        for r in cur.fetchall():
            mes = str(r['mes']).zfill(2)
            # Negativo para mantener compatibilidad con gráficos
            gastos_dict[mes] = -abs(float(r['total_gastos'] or 0))
        
        conn.close()

        return jsonify({
            'anio': anio,
            'ingresos': ingresos,
            'gastos': gastos_dict
        })
    except Exception as e:
        logger.error(f"ERROR EN /ingresos_gastos_mes: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# -------------------------------------------------------------------------
#  NUEVO ENDPOINT: INGRESOS Y GASTOS TOTALES POR AÑO
# -------------------------------------------------------------------------
@gastos_bp.route('/ingresos_gastos_totales', methods=['GET'])
@gastos_bp.route('/api/ingresos_gastos_totales', methods=['GET'])
def ingresos_gastos_totales():
    """Totales anuales de ingresos y gastos y variación vs. año anterior."""
    try:
        from datetime import datetime
        anio_actual = int(request.args.get('anio', datetime.now().year))
        # Si se especifica un mes, filtramos por mes. Si no, devolvemos el año completo.
        mes = request.args.get('mes', None)
        anio_anterior = anio_actual - 1

        gasto_empresa_param = request.args.get('gasto_empresa', '1')
        gasto_empresa_filter = ''
        gasto_empresa_params = []
        if gasto_empresa_param != 'todos':
            gasto_empresa_filter = ' AND gasto_empresa = ?'
            gasto_empresa_params = [int(gasto_empresa_param)]

        conn = get_db_connection()
        try:
            cur = conn.cursor()

            def totales(anio:int):
                # 1. Calcular Ingresos: Suma de Facturas y Tickets cobrados (estado 'C')
                cur.execute("SELECT COALESCE(SUM(total), 0) FROM tickets WHERE estado = 'C' AND substr(fecha, 1, 4) = ?", (str(anio),))
                val = cur.fetchone()
                t_tickets = val[0] if val else 0
                
                cur.execute("""
                    SELECT COALESCE(SUM(total), 0) 
                    FROM factura 
                    WHERE estado = 'C' AND substr(COALESCE(NULLIF(fechaCobro, ''), fecha), 1, 4) = ?
                """, (str(anio),))
                val = cur.fetchone()
                t_facturas = val[0] if val else 0
                
                ingresos = t_tickets + t_facturas

                # 2. Calcular Gastos: Suma de totales de facturas_proveedores
                cur.execute(
                    f"""
                    SELECT COALESCE(SUM(total), 0)
                    FROM facturas_proveedores
                    WHERE año = ?{gasto_empresa_filter}
                    """,
                    (anio, *gasto_empresa_params)
                )
                row = cur.fetchone()
                # Convertir a negativo para mantener compatibilidad con balance
                gastos = -abs(float(row[0] or 0)) if row else 0.0
                
                return float(ingresos), gastos

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
        finally:
            if conn:
                conn.close()
    except Exception as e:
        logger.error(f"ERROR EN /ingresos_gastos_totales: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

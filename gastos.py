from datetime import datetime
from traceback import format_exc

from flask import Blueprint, jsonify, request

from db_utils import get_db_connection

gastos_bp = Blueprint('gastos', __name__)

@gastos_bp.route('/gastos', methods=['GET'])
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
        query += " ORDER BY fecha_operacion DESC"

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

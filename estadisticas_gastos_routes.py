from flask import Blueprint, jsonify, request
from datetime import datetime
import sqlite3
from db_utils import get_db_connection
from logger_config import get_estadisticas_logger

logger = get_estadisticas_logger()

# Fecha efectiva para facturas de clientes: si está cobrada, usar fechaCobro; si no, usar fecha de emisión
FECHA_EFECTIVA_FACTURA = "CASE WHEN estado = 'C' AND fechaCobro IS NOT NULL AND fechaCobro != '' THEN fechaCobro ELSE fecha END"
FECHA_EFECTIVA_COBRADA = "COALESCE(NULLIF(fechaCobro, ''), fecha)"

estadisticas_gastos_bp = Blueprint('estadisticas_gastos', __name__)

# ===== FUNCIONES AUXILIARES COMPARTIDAS =====

def _calcular_media_mensual_sin_puntuales(conn, anio, mes=None, gasto_empresa_filter='', gasto_empresa_params=None):
    """
    Calcula la media mensual excluyendo gastos puntuales

    Args:
        conn: conexión a la base de datos
        anio: año para calcular
        mes: mes hasta el cual calcular (opcional)
        gasto_empresa_filter: str con filtro SQL adicional (ej. ' AND gasto_empresa = ?')
        gasto_empresa_params: lista de parámetros para el filtro

    Returns:
        tuple: (media_mensual, total_gastos_sin_puntuales, num_meses)
    """
    gasto_empresa_params = gasto_empresa_params or []
    # NOTA: la identificación/marcado de gastos puntuales la realiza el endpoint
    # llamante una sola vez. Esta función solo calcula la media a partir de
    # facturas_proveedores, por lo que no se repite ese trabajo (ni sus escrituras).
    cursor = conn.cursor()
    if mes:
        cursor.execute(f'''
            SELECT
                COALESCE(SUM(total), 0) as total_sin_puntuales,
                COUNT(*) as cantidad_sin_puntuales
            FROM facturas_proveedores
            WHERE año = ?
            AND CAST(substr(fecha_emision, 6, 2) AS INTEGER) <= ?{gasto_empresa_filter}
        ''', (anio, mes, *gasto_empresa_params))
    else:
        cursor.execute(f'''
            SELECT
                COALESCE(SUM(total), 0) as total_sin_puntuales,
                COUNT(*) as cantidad_sin_puntuales
            FROM facturas_proveedores
            WHERE año = ?{gasto_empresa_filter}
        ''', (anio, *gasto_empresa_params))

    resultado = cursor.fetchone()
    total_sin_puntuales = float(resultado['total_sin_puntuales'] or 0)
    cantidad_sin_puntuales = int(resultado['cantidad_sin_puntuales'] or 0)

    # Calcular media mensual
    num_meses = mes if mes else 12
    media_mensual = total_sin_puntuales / num_meses if num_meses > 0 else 0

    return media_mensual, total_sin_puntuales, num_meses


@estadisticas_gastos_bp.route('/api/gastos/estadisticas', methods=['GET'])
def obtener_estadisticas_gastos():
    """
    Devuelve estadísticas completas de gastos para un año específico
    Similar a las estadísticas de ventas pero para gastos (importe negativo)
    """
    try:
        anio = request.args.get('anio', datetime.now().year, type=int)
        mes = request.args.get('mes', datetime.now().month, type=int)

        gasto_empresa_param = request.args.get('gasto_empresa', '1')
        gasto_empresa_filter = ''
        gasto_empresa_params = []
        if gasto_empresa_param != 'todos':
            gasto_empresa_filter = ' AND gasto_empresa = ?'
            gasto_empresa_params = [int(gasto_empresa_param)]

        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Gastos totales del año actual (año completo)
            # AHORA USA facturas_proveedores en lugar de gastos
            cursor.execute(f'''
                SELECT
                    COALESCE(SUM(total), 0) as total_gastos_anio,
                    COUNT(*) as cantidad_gastos_anio
                FROM facturas_proveedores
                WHERE año = ?{gasto_empresa_filter}
            ''', (anio, *gasto_empresa_params))
    
            datos_anio = cursor.fetchone()
            total_gastos_anio = float(datos_anio['total_gastos_anio'] or 0)
            cantidad_gastos_anio = int(datos_anio['cantidad_gastos_anio'] or 0)

            # Gastos del MES seleccionado (por fecha_emision)
            cursor.execute(f'''
                SELECT
                    COALESCE(SUM(total), 0) as total,
                    COUNT(*) as cantidad
                FROM facturas_proveedores
                WHERE año = ?
                AND CAST(substr(fecha_emision, 6, 2) AS INTEGER) = ?{gasto_empresa_filter}
            ''', (anio, mes, *gasto_empresa_params))
            datos_mes_solo = cursor.fetchone()
            total_gastos_mes_solo = float(datos_mes_solo['total'] or 0)
            cantidad_gastos_mes_solo = int(datos_mes_solo['cantidad'] or 0)

            # Gastos del mismo mes del año anterior (por fecha_emision)
            anio_anterior = anio - 1
            cursor.execute(f'''
                SELECT COALESCE(SUM(total), 0) as total
                FROM facturas_proveedores
                WHERE año = ?
                AND CAST(substr(fecha_emision, 6, 2) AS INTEGER) = ?{gasto_empresa_filter}
            ''', (anio_anterior, mes, *gasto_empresa_params))
            total_gastos_mes_solo_anterior = float(cursor.fetchone()['total'] or 0)

            # Gastos del mes anterior (mes-1) para comparación mes a mes
            mes_prev = mes - 1
            anio_prev = anio
            if mes_prev < 1:
                mes_prev = 12
                anio_prev = anio - 1
            cursor.execute(f'''
                SELECT COALESCE(SUM(total), 0) as total
                FROM facturas_proveedores
                WHERE año = ?
                AND CAST(substr(fecha_emision, 6, 2) AS INTEGER) = ?{gasto_empresa_filter}
            ''', (anio_prev, mes_prev, *gasto_empresa_params))
            total_gastos_mes_previo = float(cursor.fetchone()['total'] or 0)
            pct_mes_previo = ((total_gastos_mes_solo - total_gastos_mes_previo) / total_gastos_mes_previo * 100) if total_gastos_mes_previo > 0 else 0

            # Gastos del TRIMESTRE actual (según el mes seleccionado)
            # Limitar al mes actual para no incluir meses futuros
            trimestre = ((mes - 1) // 3) + 1
            mes_inicio_trimestre = (trimestre - 1) * 3 + 1
            mes_fin_trimestre = min(mes_inicio_trimestre + 2, mes)  # No pasar del mes actual
            cursor.execute(f'''
                SELECT
                    COALESCE(SUM(total), 0) as total_gastos_mes,
                    COUNT(*) as cantidad_gastos_mes
                FROM facturas_proveedores
                WHERE año = ?
                AND CAST(substr(fecha_emision, 6, 2) AS INTEGER) BETWEEN ? AND ?{gasto_empresa_filter}
            ''', (anio, mes_inicio_trimestre, mes_fin_trimestre, *gasto_empresa_params))

            datos_mes = cursor.fetchone()
            total_gastos_mes = float(datos_mes['total_gastos_mes'] or 0)
            cantidad_gastos_mes = int(datos_mes['cantidad_gastos_mes'] or 0)
    
            # Gastos del año anterior HASTA el mismo mes (para comparación justa)
            cursor.execute(f'''
                SELECT COALESCE(SUM(total), 0) as total_gastos_anio_anterior
                FROM facturas_proveedores
                WHERE año = ?
                AND CAST(substr(fecha_emision, 6, 2) AS INTEGER) <= ?{gasto_empresa_filter}
            ''', (anio_anterior, mes, *gasto_empresa_params))
    
            total_gastos_anio_anterior = float(cursor.fetchone()['total_gastos_anio_anterior'] or 0)

            # Gastos del mismo TRIMESTRE del año anterior
            cursor.execute(f'''
                SELECT COALESCE(SUM(total), 0) as total_gastos_mes_anterior
                FROM facturas_proveedores
                WHERE año = ?
                AND CAST(substr(fecha_emision, 6, 2) AS INTEGER) BETWEEN ? AND ?{gasto_empresa_filter}
            ''', (anio_anterior, mes_inicio_trimestre, mes_fin_trimestre, *gasto_empresa_params))

            total_gastos_mes_anterior = float(cursor.fetchone()['total_gastos_mes_anterior'] or 0)
            
            # Media mensual de gastos (excluyendo gastos puntuales)
            media_mensual, total_gastos_sin_puntuales, meses_transcurridos = _calcular_media_mensual_sin_puntuales(conn, anio, mes, gasto_empresa_filter, gasto_empresa_params)
            
            # Previsión de gastos hasta fin de año
            meses_restantes = 12 - mes
            prevision_gastos = total_gastos_anio + (media_mensual * meses_restantes)
            
            # Calcular porcentajes
            pct_anio = ((total_gastos_anio - total_gastos_anio_anterior) / total_gastos_anio_anterior * 100) if total_gastos_anio_anterior > 0 else 0
            pct_mes = ((total_gastos_mes - total_gastos_mes_anterior) / total_gastos_mes_anterior * 100) if total_gastos_mes_anterior > 0 else 0
            pct_mes_solo = ((total_gastos_mes_solo - total_gastos_mes_solo_anterior) / total_gastos_mes_solo_anterior * 100) if total_gastos_mes_solo_anterior > 0 else 0
        
        return jsonify({
            'anio': anio,
            'mes': mes,
            'total_gastos_anio': total_gastos_anio,
            'cantidad_gastos_anio': cantidad_gastos_anio,
            'total_gastos_mes': total_gastos_mes,
            'cantidad_gastos_mes': cantidad_gastos_mes,
            'total_gastos_mes_solo': total_gastos_mes_solo,
            'cantidad_gastos_mes_solo': cantidad_gastos_mes_solo,
            'total_gastos_mes_solo_anterior': total_gastos_mes_solo_anterior,
            'total_gastos_mes_previo': total_gastos_mes_previo,
            'porcentaje_mes_solo': round(pct_mes_solo, 2),
            'porcentaje_mes_previo': round(pct_mes_previo, 2),
            'total_gastos_anio_anterior': total_gastos_anio_anterior,
            'total_gastos_mes_anterior': total_gastos_mes_anterior,
            'media_mensual': media_mensual,
            'prevision_gastos_anio': prevision_gastos,
            'porcentaje_anio': round(pct_anio, 2),
            'porcentaje_mes': round(pct_mes, 2),
            'meses_transcurridos': meses_transcurridos
        })
        
    except Exception as e:
        logger.error(f"Error en estadísticas gastos: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@estadisticas_gastos_bp.route('/api/gastos/top10', methods=['GET'])
def obtener_top10_gastos():
    """
    Devuelve el top 10 de conceptos de gastos del año actual
    Agrupados por CONCEPTO NORMALIZADO (usando _normalizar_concepto en Python)
    """
    try:
        anio = request.args.get('anio', datetime.now().year, type=int)

        gasto_empresa_param = request.args.get('gasto_empresa', '1')
        gasto_empresa_filter = ''
        gasto_empresa_params = []
        if gasto_empresa_param != 'todos':
            gasto_empresa_filter = ' AND fp.gasto_empresa = ?'
            gasto_empresa_params = [int(gasto_empresa_param)]
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            conn.row_factory = sqlite3.Row
            
            # 1. Obtener TODOS los gastos del año desde facturas_proveedores
            # Agrupar por proveedor
            cursor.execute(f'''
                SELECT 
                    p.nombre as proveedor_nombre,
                    fp.concepto,
                    fp.total as importe
                FROM facturas_proveedores fp
                LEFT JOIN proveedores p ON fp.proveedor_id = p.id
                WHERE fp.año = ?{gasto_empresa_filter}
            ''', (anio, *gasto_empresa_params))
            
            gastos_anio = cursor.fetchall()
            
            # 2. Agrupar por proveedor
            agrupados = {}
            
            for gasto in gastos_anio:
                proveedor = gasto['proveedor_nombre'] or gasto['concepto'] or 'Sin proveedor'
                importe = float(gasto['importe'] or 0)
                
                if proveedor not in agrupados:
                    agrupados[proveedor] = {
                        'total': 0.0,
                        'cantidad': 0,
                        'cantidad_puntuales': 0,
                        'total_puntuales': 0.0
                    }
                
                agrupados[proveedor]['total'] += importe
                agrupados[proveedor]['cantidad'] += 1
            
            # 3. Convertir a lista y ordenar
            lista_gastos = []
            for concepto, datos in agrupados.items():
                total_gasto = datos['total']
                total_puntuales = datos['total_puntuales']
                
                # Determinar si es mayormente puntual
                es_mayormente_puntual = (total_puntuales / total_gasto > 0.5) if total_gasto > 0 else False
                
                lista_gastos.append({
                    'concepto': concepto,
                    'total': round(total_gasto, 2),
                    'cantidad': datos['cantidad'],
                    'es_puntual': es_mayormente_puntual,
                    'total_puntuales': round(total_puntuales, 2),
                    'cantidad_puntuales': datos['cantidad_puntuales']
                })
            
            # Ordenar descendentemente por total
            lista_gastos.sort(key=lambda x: x['total'], reverse=True)
            
            # Quedarse con el Top 10
            top_gastos = lista_gastos[:10]
            
            # 4. Obtener datos del año anterior para comparación
            anio_anterior = anio - 1
            cursor.execute(f'''
                SELECT 
                    p.nombre as proveedor_nombre,
                    fp.concepto,
                    fp.total as importe
                FROM facturas_proveedores fp
                LEFT JOIN proveedores p ON fp.proveedor_id = p.id
                WHERE fp.año = ?{gasto_empresa_filter}
            ''', (anio_anterior, *gasto_empresa_params))
            
            gastos_anterior = cursor.fetchall()
            
            # Agrupar año anterior por proveedor
            agrupados_anterior = {}
            for gasto in gastos_anterior:
                proveedor = gasto['proveedor_nombre'] or gasto['concepto'] or 'Sin proveedor'
                importe = float(gasto['importe'] or 0)
                agrupados_anterior[proveedor] = agrupados_anterior.get(proveedor, 0.0) + importe
                
            # 5. Calcular diferencias
            for gasto in top_gastos:
                concepto = gasto['concepto']
                total_anterior = agrupados_anterior.get(concepto, 0.0)
                
                diferencia = gasto['total'] - total_anterior
                pct_diferencia = (diferencia / total_anterior * 100) if total_anterior > 0 else 0
                
                gasto['total_anterior'] = round(total_anterior, 2)
                gasto['diferencia'] = round(diferencia, 2)
                gasto['porcentaje_diferencia'] = round(pct_diferencia, 2)
        
        return jsonify({
            'anio': anio,
            'top_gastos': top_gastos
        })
        
    except Exception as e:
        logger.error(f"Error en top10 gastos: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@estadisticas_gastos_bp.route('/api/gastos/detalles', methods=['GET'])
def obtener_detalles_gasto():
    """
    Devuelve los detalles de todos los gastos de un proveedor específico
    """
    try:
        concepto_buscado = request.args.get('concepto', '')
        anio = request.args.get('anio', datetime.now().year, type=int)

        gasto_empresa_param = request.args.get('gasto_empresa', '1')
        gasto_empresa_filter = ''
        gasto_empresa_params = []
        if gasto_empresa_param != 'todos':
            gasto_empresa_filter = ' AND fp.gasto_empresa = ?'
            gasto_empresa_params = [int(gasto_empresa_param)]
        
        if not concepto_buscado:
            return jsonify({'error': 'Se requiere el parámetro concepto'}), 400
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            conn.row_factory = sqlite3.Row
            
            # Obtener facturas del proveedor buscado
            cursor.execute(f'''
                SELECT 
                    fp.id,
                    p.nombre as proveedor_nombre,
                    fp.concepto,
                    fp.numero_factura,
                    fp.fecha_emision,
                    fp.total as importe,
                    fp.base_imponible,
                    fp.iva_importe
                FROM facturas_proveedores fp
                LEFT JOIN proveedores p ON fp.proveedor_id = p.id
                WHERE fp.año = ?{gasto_empresa_filter}
                ORDER BY fp.fecha_emision DESC
            ''', (anio, *gasto_empresa_params))
            
            gastos_filtrados = []
            importes = []
            
            for row in cursor.fetchall():
                proveedor = row['proveedor_nombre'] or row['concepto'] or 'Sin proveedor'
                importe = float(row['importe'] or 0)
                fecha = row['fecha_emision']
                
                # Si coincide con el proveedor buscado
                if proveedor == concepto_buscado:
                    gastos_filtrados.append({
                        'concepto': proveedor,
                        'concepto_real': row['concepto'] or row['numero_factura'] or 'Factura',
                        'fecha': fecha,
                        'importe': round(importe, 2),
                        'es_razon_social': True
                    })
                    importes.append(importe)
            
            if not gastos_filtrados:
                 return jsonify({
                    'concepto': concepto_buscado,
                    'anio': anio,
                    'estadisticas': {
                        'cantidad': 0, 'total': 0, 'promedio': 0, 'minimo': 0, 'maximo': 0
                    },
                    'gastos_agrupados': []
                })

            # Calcular estadísticas
            cantidad = len(importes)
            total = sum(importes)
            promedio = total / cantidad if cantidad > 0 else 0
            minimo = min(importes) if importes else 0
            maximo = max(importes) if importes else 0
            
            estadisticas = {
                'cantidad': cantidad,
                'total': round(total, 2),
                'promedio': round(promedio, 2),
                'minimo': round(minimo, 2),
                'maximo': round(maximo, 2)
            }
            
            # Agrupar por TRIMESTRE para mejor visualización
            trimestres = {}
            for g in gastos_filtrados:
                fecha = g['fecha']
                if fecha:
                    mes = int(fecha[5:7])
                    trimestre = f"Q{(mes - 1) // 3 + 1}"
                else:
                    trimestre = "Q?"
                
                if trimestre not in trimestres:
                    trimestres[trimestre] = {
                        'conceptos': [],
                        'importes': [],
                        'fechas': []
                    }
                
                trimestres[trimestre]['conceptos'].append(g['concepto_real'])
                trimestres[trimestre]['importes'].append(g['importe'])
                trimestres[trimestre]['fechas'].append(fecha)
            
            gastos_view = []
            for trimestre in sorted(trimestres.keys()):
                data = trimestres[trimestre]
                total_trim = sum(data['importes'])
                cantidad_trim = len(data['importes'])
                promedio_trim = total_trim / cantidad_trim if cantidad_trim > 0 else 0
                fechas_ordenadas = sorted([f for f in data['fechas'] if f])
                
                gastos_view.append({
                    'concepto': trimestre,
                    'cantidad': cantidad_trim,
                    'total': round(total_trim, 2),
                    'promedio': round(promedio_trim, 2),
                    'primera_fecha': fechas_ordenadas[0] if fechas_ordenadas else '',
                    'ultima_fecha': fechas_ordenadas[-1] if fechas_ordenadas else '',
                    'conceptos_originales': data['conceptos'][:5]  # Max 5 ejemplos
                })

        return jsonify({
            'concepto': concepto_buscado,
            'anio': anio,
            'estadisticas': estadisticas,
            'gastos_agrupados': gastos_view
        })
        
    except Exception as e:
        logger.error(f"Error al obtener detalles de gasto: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@estadisticas_gastos_bp.route('/api/gastos/evolucion-trimestral', methods=['GET'])
def obtener_evolucion_trimestral():
    """
    Devuelve gastos agrupados por trimestre desde facturas_proveedores
    """
    try:
        anio = request.args.get('anio', datetime.now().year, type=int)

        gasto_empresa_param = request.args.get('gasto_empresa', '1')
        gasto_empresa_filter = ''
        gasto_empresa_params = []
        if gasto_empresa_param != 'todos':
            gasto_empresa_filter = ' AND gasto_empresa = ?'
            gasto_empresa_params = [int(gasto_empresa_param)]
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Obtener gastos por trimestre desde facturas_proveedores
            cursor.execute(f'''
                SELECT 
                    trimestre,
                    COALESCE(SUM(total), 0) as total,
                    COUNT(*) as cantidad
                FROM facturas_proveedores
                WHERE año = ?{gasto_empresa_filter}
                GROUP BY trimestre
                ORDER BY trimestre
            ''', (anio, *gasto_empresa_params))
            
            # Inicializar trimestres
            trimestres_data = {
                'Q1': {'nombre': 'Q1 (Ene-Mar)', 'total': 0, 'cantidad': 0},
                'Q2': {'nombre': 'Q2 (Abr-Jun)', 'total': 0, 'cantidad': 0},
                'Q3': {'nombre': 'Q3 (Jul-Sep)', 'total': 0, 'cantidad': 0},
                'Q4': {'nombre': 'Q4 (Oct-Dic)', 'total': 0, 'cantidad': 0}
            }
            
            for row in cursor.fetchall():
                trimestre = row['trimestre'] or 'Q1'
                if trimestre in trimestres_data:
                    trimestres_data[trimestre]['total'] = round(float(row['total'] or 0), 2)
                    trimestres_data[trimestre]['cantidad'] = int(row['cantidad'] or 0)
            
            # Convertir a lista ordenada
            meses = [
                trimestres_data['Q1'],
                trimestres_data['Q2'],
                trimestres_data['Q3'],
                trimestres_data['Q4']
            ]
            
            total_anual = sum(t['total'] for t in meses)
        
        return jsonify({
            'anio': anio,
            'meses': meses,
            'total_anual': round(total_anual, 2)
        })
        
    except Exception as e:
        logger.error(f"Error en evolución trimestral: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@estadisticas_gastos_bp.route('/api/gastos/por-categoria-mes-solo', methods=['GET'])
def obtener_gastos_por_categoria_mes_solo():
    """
    Devuelve gastos del mes seleccionado agrupados por PROVEEDOR para gráfico de pastel
    Basado en facturas_proveedores (facturas recibidas)
    """
    try:
        anio = request.args.get('anio', datetime.now().year, type=int)
        mes = request.args.get('mes', datetime.now().month, type=int)

        gasto_empresa_param = request.args.get('gasto_empresa', '1')
        gasto_empresa_filter = ''
        gasto_empresa_params = []
        if gasto_empresa_param != 'todos':
            gasto_empresa_filter = ' AND fp.gasto_empresa = ?'
            gasto_empresa_params = [int(gasto_empresa_param)]
        
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Obtener gastos del mes desde facturas_proveedores agrupados por proveedor
            # Criterio: fecha_emision
            cursor.execute(f'''
                SELECT 
                    COALESCE(p.nombre, fp.concepto, 'Sin proveedor') as categoria,
                    COALESCE(SUM(fp.total), 0) as total
                FROM facturas_proveedores fp
                LEFT JOIN proveedores p ON fp.proveedor_id = p.id
                WHERE fp.año = ?
                AND CAST(substr(fp.fecha_emision, 6, 2) AS INTEGER) = ?{gasto_empresa_filter}
                GROUP BY categoria
                HAVING total > 0
                ORDER BY total DESC
            ''', (anio, mes, *gasto_empresa_params))
            
            lista_categorias = [{'categoria': row['categoria'], 'total': float(row['total'])} for row in cursor.fetchall()]
            
            # "Otros" solo para facturas sin proveedor identificado
            nombres_genericos = {'Sin proveedor', 'GASTOS VARIOS', 'SIN NOMBRE', 'NO IDENTIFICADO', ''}
            
            final_categorias = []
            total_otros = 0.0
            
            for c in lista_categorias:
                if c['categoria'] in nombres_genericos or not c['categoria'] or len(c['categoria'].strip()) < 2:
                    total_otros += c['total']
                else:
                    final_categorias.append(c)
            
            if total_otros > 0:
                final_categorias.append({'categoria': 'Otros', 'total': round(total_otros, 2)})
            
            resultado = []
            for c in final_categorias:
                resultado.append({
                    'categoria': c['categoria'],
                    'total': round(c['total'], 2)
                })
        
        return jsonify({
            'anio': anio,
            'mes': mes,
            'categorias': resultado
        })
        
    except Exception as e:
        logger.error(f"Error al obtener gastos por categoría del mes: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@estadisticas_gastos_bp.route('/api/gastos/por-categoria-mes', methods=['GET'])
def obtener_gastos_por_categoria_mes():
    """
    Devuelve gastos del trimestre actual agrupados por PROVEEDOR para gráfico de pastel
    Basado en facturas_proveedores (facturas recibidas)
    """
    try:
        anio = request.args.get('anio', datetime.now().year, type=int)
        mes = request.args.get('mes', datetime.now().month, type=int)

        gasto_empresa_param = request.args.get('gasto_empresa', '1')
        gasto_empresa_filter = ''
        gasto_empresa_params = []
        if gasto_empresa_param != 'todos':
            gasto_empresa_filter = ' AND fp.gasto_empresa = ?'
            gasto_empresa_params = [int(gasto_empresa_param)]
        
        with get_db_connection() as conn:
            cursor = conn.cursor()

            trimestre = ((mes - 1) // 3) + 1
            mes_inicio_trimestre = (trimestre - 1) * 3 + 1
            mes_fin_trimestre = min(mes_inicio_trimestre + 2, mes)

            # Obtener gastos del trimestre desde facturas_proveedores agrupados por proveedor
            cursor.execute(f'''
                SELECT 
                    COALESCE(p.nombre, fp.concepto, 'Sin proveedor') as categoria,
                    COALESCE(SUM(fp.total), 0) as total
                FROM facturas_proveedores fp
                LEFT JOIN proveedores p ON fp.proveedor_id = p.id
                WHERE fp.año = ?
                AND CAST(substr(fp.fecha_emision, 6, 2) AS INTEGER) BETWEEN ? AND ?{gasto_empresa_filter}
                GROUP BY categoria
                HAVING total > 0
                ORDER BY total DESC
            ''', (anio, mes_inicio_trimestre, mes_fin_trimestre, *gasto_empresa_params))
            
            lista_categorias = [{'categoria': row['categoria'], 'total': float(row['total'])} for row in cursor.fetchall()]
            
            # "Otros" solo para facturas sin proveedor identificado
            # Proveedores reales siempre tienen su propia categoría
            nombres_genericos = {'Sin proveedor', 'GASTOS VARIOS', 'SIN NOMBRE', 'NO IDENTIFICADO', ''}
            
            final_categorias = []
            total_otros = 0.0
            
            for c in lista_categorias:
                if c['categoria'] in nombres_genericos or not c['categoria'] or len(c['categoria'].strip()) < 2:
                    total_otros += c['total']
                else:
                    final_categorias.append(c)
            
            if total_otros > 0:
                final_categorias.append({'categoria': 'Otros', 'total': round(total_otros, 2)})
            
            # Formatear salida
            resultado = []
            for c in final_categorias:
                resultado.append({
                    'categoria': c['categoria'],
                    'total': round(c['total'], 2),
                    'total_bruto': round(c['total'], 2),
                    'total_puntuales': 0
                })
        
        return jsonify({
            'anio': anio,
            'mes': mes,
            'categorias': resultado
        })
        
    except Exception as e:
        logger.error(f"Error al obtener gastos por categoría: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@estadisticas_gastos_bp.route('/api/gastos/por-categoria-anio', methods=['GET'])
def obtener_gastos_por_categoria_anio():
    """
    Devuelve gastos del año completo agrupados por PROVEEDOR para gráfico de pastel
    Basado en facturas_proveedores (facturas recibidas)
    """
    try:
        anio = request.args.get('anio', datetime.now().year, type=int)

        gasto_empresa_param = request.args.get('gasto_empresa', '1')
        gasto_empresa_filter = ''
        gasto_empresa_params = []
        if gasto_empresa_param != 'todos':
            gasto_empresa_filter = ' AND fp.gasto_empresa = ?'
            gasto_empresa_params = [int(gasto_empresa_param)]
        
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Obtener gastos del año desde facturas_proveedores agrupados por proveedor
            cursor.execute(f'''
                SELECT 
                    COALESCE(p.nombre, fp.concepto, 'Sin proveedor') as categoria,
                    COALESCE(SUM(fp.total), 0) as total
                FROM facturas_proveedores fp
                LEFT JOIN proveedores p ON fp.proveedor_id = p.id
                WHERE fp.año = ?{gasto_empresa_filter}
                GROUP BY categoria
                HAVING total > 0
                ORDER BY total DESC
            ''', (anio, *gasto_empresa_params))
            
            lista_categorias = [{'categoria': row['categoria'], 'total': float(row['total'])} for row in cursor.fetchall()]
            
            # "Otros" solo para facturas sin proveedor identificado
            nombres_genericos = {'Sin proveedor', 'GASTOS VARIOS', 'SIN NOMBRE', 'NO IDENTIFICADO', ''}
            
            final_categorias = []
            total_otros = 0.0
            
            for c in lista_categorias:
                if c['categoria'] in nombres_genericos or not c['categoria'] or len(c['categoria'].strip()) < 2:
                    total_otros += c['total']
                else:
                    final_categorias.append(c)
            
            if total_otros > 0:
                final_categorias.append({'categoria': 'Otros', 'total': round(total_otros, 2)})

            # Formatear
            resultado = []
            for c in final_categorias:
                resultado.append({
                    'categoria': c['categoria'],
                    'total': round(c['total'], 2)
                })
        
        return jsonify({
            'anio': anio,
            'categorias': resultado
        })
        
    except Exception as e:
        logger.error(f"Error al obtener gastos por categoría del año: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@estadisticas_gastos_bp.route('/api/gastos/detalles-proveedor', methods=['GET'])
def obtener_detalles_proveedor():
    """
    Devuelve las facturas de un proveedor específico para un año, con filtro opcional por mes o trimestre.
    Basado en facturas_proveedores.
    """
    try:
        proveedor = request.args.get('proveedor', type=str)
        anio = request.args.get('anio', datetime.now().year, type=int)
        mes = request.args.get('mes', type=int)
        trimestre = request.args.get('trimestre', type=int)

        gasto_empresa_param = request.args.get('gasto_empresa', '1')
        gasto_empresa_filter = ''
        gasto_empresa_params = []
        if gasto_empresa_param != 'todos':
            gasto_empresa_filter = ' AND fp.gasto_empresa = ?'
            gasto_empresa_params = [int(gasto_empresa_param)]

        if not proveedor:
            return jsonify({'error': 'Proveedor requerido'}), 400

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Construir query base
            query = f'''
                SELECT fp.id, fp.numero_factura, fp.fecha_emision, fp.concepto,
                       fp.base_imponible, fp.iva_porcentaje, fp.total, fp.estado,
                       COALESCE(p.nombre, fp.concepto, 'Sin proveedor') as proveedor_nombre
                FROM facturas_proveedores fp
                LEFT JOIN proveedores p ON fp.proveedor_id = p.id
                WHERE fp.año = ?{gasto_empresa_filter}
            '''
            params = [anio, *gasto_empresa_params]

            # Filtro por proveedor (puede ser "Otros")
            # "Otros" = solo facturas sin proveedor identificado
            nombres_genericos = {'Sin proveedor', 'GASTOS VARIOS', 'SIN NOMBRE', 'NO IDENTIFICADO', ''}
            
            if proveedor == 'Otros':
                # Filtrar solo facturas sin proveedor real
                query += ''' AND (
                    p.nombre IS NULL 
                    OR p.nombre IN ('Sin proveedor', 'GASTOS VARIOS', 'SIN NOMBRE', 'NO IDENTIFICADO', '')
                    OR LENGTH(TRIM(COALESCE(p.nombre, ''))) < 2
                )'''
            else:
                query += ' AND COALESCE(p.nombre, fp.concepto, \'Sin proveedor\') = ?'
                params.append(proveedor)

            # Filtro temporal
            if mes:
                query += ' AND CAST(substr(fp.fecha_emision, 6, 2) AS INTEGER) = ?'
                params.append(mes)
            elif trimestre and 1 <= trimestre <= 4:
                mes_inicio = (trimestre - 1) * 3 + 1
                mes_fin = min(mes_inicio + 2, 12)
                query += ' AND CAST(substr(fp.fecha_emision, 6, 2) AS INTEGER) BETWEEN ? AND ?'
                params.extend([mes_inicio, mes_fin])

            query += ' ORDER BY fp.fecha_emision DESC'
            cursor.execute(query, params)
            rows = cursor.fetchall()

            facturas = []
            total = 0.0
            for row in rows:
                importe = float(row['total'] or 0)
                total += importe
                facturas.append({
                    'numero_factura': row['numero_factura'] or '-',
                    'fecha': row['fecha_emision'] or '-',
                    'concepto': row['concepto'] or row['proveedor_nombre'],
                    'base_imponible': round(float(row['base_imponible'] or 0), 2),
                    'iva': float(row['iva_porcentaje'] or 0),
                    'total': round(importe, 2),
                    'estado': row['estado'] or 'pendiente'
                })

            cantidad = len(facturas)
            promedio = total / cantidad if cantidad > 0 else 0
            minimo = min((f['total'] for f in facturas), default=0)
            maximo = max((f['total'] for f in facturas), default=0)

        return jsonify({
            'proveedor': proveedor,
            'anio': anio,
            'mes': mes,
            'trimestre': trimestre,
            'estadisticas': {
                'total': round(total, 2),
                'cantidad': cantidad,
                'promedio': round(promedio, 2),
                'minimo': round(minimo, 2),
                'maximo': round(maximo, 2)
            },
            'facturas': facturas
        })

    except Exception as e:
        logger.error(f"Error al obtener detalles de proveedor: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@estadisticas_gastos_bp.route('/api/gastos/detalles-categoria', methods=['GET'])
def obtener_detalles_categoria():
    """
    Devuelve los detalles de gastos de una categoría específica para un mes/trimestre/año
    Adaptado para soportar la nueva agrupación dinámica (Top 9 + Otros)
    """
    try:
        categoria = request.args.get('categoria', type=str)
        anio = request.args.get('anio', datetime.now().year, type=int)
        mes = request.args.get('mes', type=int)  # Opcional
        trimestre = request.args.get('trimestre', type=int)  # Opcional (1-4)
        
        if not categoria:
            return jsonify({'error': 'Categoría requerida'}), 400
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            conn.row_factory = sqlite3.Row
            
            # Gastos desde facturas_proveedores (fuente de verdad), por proveedor.
            # La categoría corresponde al nombre del proveedor (o 'Otros' para genéricos),
            # de forma consistente con los gráficos de pastel del dashboard.
            query = '''
                SELECT
                    COALESCE(p.nombre, fp.concepto, 'Sin proveedor') as categoria,
                    fp.concepto as concepto,
                    fp.numero_factura as numero_factura,
                    fp.total as importe,
                    fp.fecha_emision as fecha_emision
                FROM facturas_proveedores fp
                LEFT JOIN proveedores p ON fp.proveedor_id = p.id
                WHERE fp.año = ?
            '''
            params = [anio]

            if trimestre and trimestre >= 1 and trimestre <= 4:
                mes_inicio = (trimestre - 1) * 3 + 1
                mes_fin = mes_inicio + 2
                query += ' AND CAST(substr(fp.fecha_emision, 6, 2) AS INTEGER) BETWEEN ? AND ?'
                params.extend([mes_inicio, mes_fin])
            elif mes:
                query += ' AND CAST(substr(fp.fecha_emision, 6, 2) AS INTEGER) = ?'
                params.append(mes)

            query += ' ORDER BY fp.fecha_emision DESC'

            cursor.execute(query, params)
            filas = cursor.fetchall()

            logger.info(f"Detalles Categoria: buscando '{categoria}' en año {anio} ({len(filas)} facturas)")

            # Nombres genéricos que se agrupan en 'Otros' (igual que en los gráficos)
            nombres_genericos = {'Sin proveedor', 'GASTOS VARIOS', 'SIN NOMBRE', 'NO IDENTIFICADO', ''}

            def _es_generico(cat):
                return (cat in nombres_genericos) or (not cat) or (len(cat.strip()) < 2)

            # Filtrar las facturas que pertenecen a la categoría (proveedor) solicitada
            gastos_view = []
            for row in filas:
                cat = row['categoria']
                if categoria == 'Otros':
                    if not _es_generico(cat):
                        continue
                else:
                    if cat != categoria:
                        continue

                importe = float(row['importe'] or 0)
                # Convertir fecha_emision (YYYY-MM-DD) a DD/MM/YYYY para visualización
                fe = row['fecha_emision'] or ''
                if fe and len(fe) >= 10 and fe[4:5] == '-':
                    fecha_fmt = f"{fe[8:10]}/{fe[5:7]}/{fe[0:4]}"
                else:
                    fecha_fmt = fe
                concepto_real = row['concepto'] or row['numero_factura'] or 'Factura'

                gastos_view.append({
                    'concepto': concepto_real,
                    'cantidad': 1,
                    'importe': round(importe, 2),
                    'total': round(importe, 2),
                    'promedio': round(importe, 2),
                    'fecha': fecha_fmt,
                    'primera_fecha': fecha_fmt,
                    'ultima_fecha': fecha_fmt,
                    'conceptos_originales': [concepto_real],
                    'es_puntual': False
                })

            # Ya vienen ordenadas por fecha_emision DESC desde la consulta

            # Calcular estadísticas del conjunto filtrado
            total = sum(g['importe'] for g in gastos_view)
            cantidad = len(gastos_view)
            promedio = total / cantidad if cantidad > 0 else 0
            minimo = min((g['importe'] for g in gastos_view), default=0)
            maximo = max((g['importe'] for g in gastos_view), default=0)
            
            estadisticas = {
                'total': round(total, 2),
                'total_sin_puntuales': round(total, 2), # Simplificado aquí
                'cantidad': cantidad,
                'cantidad_sin_puntuales': cantidad,
                'promedio': round(promedio, 2),
                'promedio_sin_puntuales': round(promedio, 2),
                'minimo': round(minimo, 2),
                'maximo': round(maximo, 2)
            }

        return jsonify({
            'categoria': categoria,
            'anio': anio,
            'mes': mes,
            'estadisticas': estadisticas,
            'gastos': gastos_view # El frontend espera 'gastos' en este endpoint
        })
        
    except Exception as e:
        logger.error(f"Error al obtener detalles de categoría: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@estadisticas_gastos_bp.route('/api/gastos/evolucion-mensual', methods=['GET'])
def obtener_evolucion_mensual():
    """
    Devuelve la evolución mensual de gastos para una categoría específica
    EXCLUYENDO gastos puntuales (>1000€ no recurrentes)
    """
    try:
        categoria = request.args.get('categoria', 'global', type=str)
        anio = request.args.get('anio', datetime.now().year, type=int)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Crear array con todos los meses (0 si no hay datos)
            meses_data = {i: {'total': 0.0, 'cantidad': 0, 'total_puntuales': 0.0, 'cantidad_puntuales': 0, 'total_bruto': 0.0} for i in range(1, 13)}

            if categoria == 'global':
                # Total global: todas las facturas de proveedores del año
                cursor.execute('''
                    SELECT
                        CAST(substr(fecha_emision, 6, 2) AS INTEGER) as mes,
                        COALESCE(SUM(total), 0) as total,
                        COUNT(*) as cantidad
                    FROM facturas_proveedores
                    WHERE año = ?
                    GROUP BY mes
                    ORDER BY mes
                ''', (anio,))
            else:
                # Categoría específica = proveedor (o 'Otros' para genéricos),
                # consistente con los gráficos de pastel del dashboard.
                nombres_genericos = ('Sin proveedor', 'GASTOS VARIOS', 'SIN NOMBRE', 'NO IDENTIFICADO', '')
                if categoria == 'Otros':
                    cond = ("(COALESCE(p.nombre, fp.concepto, 'Sin proveedor') IN (?,?,?,?,?) "
                            "OR LENGTH(TRIM(COALESCE(p.nombre, fp.concepto, ''))) < 2)")
                    cat_params = list(nombres_genericos)
                else:
                    cond = "COALESCE(p.nombre, fp.concepto, 'Sin proveedor') = ?"
                    cat_params = [categoria]
                cursor.execute(f'''
                    SELECT
                        CAST(substr(fp.fecha_emision, 6, 2) AS INTEGER) as mes,
                        COALESCE(SUM(fp.total), 0) as total,
                        COUNT(*) as cantidad
                    FROM facturas_proveedores fp
                    LEFT JOIN proveedores p ON fp.proveedor_id = p.id
                    WHERE fp.año = ? AND {cond}
                    GROUP BY mes
                    ORDER BY mes
                ''', [anio] + cat_params)

            for row in cursor.fetchall():
                mes = int(row['mes'])
                total_bruto = float(row['total'] or 0)
                cantidad_total = int(row['cantidad'])
                meses_data[mes] = {
                    'total': round(total_bruto, 2),
                    'cantidad': cantidad_total,
                    'total_puntuales': 0.0,
                    'cantidad_puntuales': 0,
                    'total_bruto': round(total_bruto, 2)
                }
        
        # Convertir a lista ordenada
        resultado = []
        nombres_meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        
        for mes in range(1, 13):
            resultado.append({
                'mes': mes,
                'nombre': nombres_meses[mes - 1],
                'total': meses_data[mes]['total'],
                'cantidad': meses_data[mes]['cantidad'],
                'total_puntuales': meses_data[mes]['total_puntuales'],
                'cantidad_puntuales': meses_data[mes]['cantidad_puntuales'],
                'total_bruto': meses_data[mes]['total_bruto']
            })
        
        return jsonify({
            'categoria': categoria,
            'anio': anio,
            'meses': resultado
        })
        
    except Exception as e:
        logger.error(f"Error al obtener evolución mensual: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@estadisticas_gastos_bp.route('/api/informe-situacion', methods=['GET'])
def generar_informe_situacion():
    """
    Genera un informe completo de situación financiera analizando ventas y gastos
    """
    try:
        anio = request.args.get('anio', datetime.now().year, type=int)
        mes = request.args.get('mes', datetime.now().month, type=int)

        gasto_empresa_param = request.args.get('gasto_empresa', '1')
        gasto_empresa_filter = ''
        gasto_empresa_params = []
        if gasto_empresa_param != 'todos':
            gasto_empresa_filter = ' AND gasto_empresa = ?'
            gasto_empresa_params = [int(gasto_empresa_param)]
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # ===== DATOS DE VENTAS =====
            # Total ventas del año hasta el mes actual (FACTURAS + TICKETS)
            mes_str = str(mes).zfill(2)
            
            # Facturas del año (solo cobradas)
            cursor.execute(f'''
                SELECT 
                    COALESCE(SUM(total), 0) as total_ventas,
                    COUNT(*) as num_facturas
                FROM factura
                WHERE CAST(substr({FECHA_EFECTIVA_COBRADA}, 1, 4) AS INTEGER) = ?
                AND CAST(substr({FECHA_EFECTIVA_COBRADA}, 6, 2) AS INTEGER) <= ?
                AND estado = 'C'
            ''', (anio, mes))
            facturas_anio = cursor.fetchone()
            total_facturas = float(facturas_anio['total_ventas'] or 0)
            num_facturas = int(facturas_anio['num_facturas'] or 0)
            
            # Tickets del año (solo cobrados) - usar total para consistencia
            cursor.execute('''
                SELECT 
                    COALESCE(SUM(total), 0) as total_ventas,
                    COUNT(*) as num_tickets
                FROM tickets
                WHERE CAST(substr(fecha, 1, 4) AS INTEGER) = ?
                AND CAST(substr(fecha, 6, 2) AS INTEGER) <= ?
                AND estado = 'C'
            ''', (anio, mes))
            tickets_anio = cursor.fetchone()
            total_tickets = float(tickets_anio['total_ventas'] or 0)
            num_tickets = int(tickets_anio['num_tickets'] or 0)
            
            # Contadores separados para pendientes/vencidas (solo para mostrar en UI)
            cursor.execute('''
                SELECT 
                    COALESCE(SUM(CASE WHEN estado = 'P' THEN total ELSE 0 END), 0) as total_pendientes,
                    COUNT(CASE WHEN estado = 'P' THEN 1 END) as num_pendientes,
                    COALESCE(SUM(CASE WHEN estado = 'V' THEN total ELSE 0 END), 0) as total_vencidas,
                    COUNT(CASE WHEN estado = 'V' THEN 1 END) as num_vencidas
                FROM factura
                WHERE estado IN ('P', 'V')
                AND CAST(substr(fecha, 1, 4) AS INTEGER) = ?
            ''', (anio,))
            fact_pv = cursor.fetchone()
            total_fact_pendientes = float(fact_pv['total_pendientes'] or 0)
            num_fact_pendientes = int(fact_pv['num_pendientes'] or 0)
            total_fact_vencidas = float(fact_pv['total_vencidas'] or 0)
            num_fact_vencidas = int(fact_pv['num_vencidas'] or 0)
            
            # Total ventas (ya incluye todo en total_facturas)
            total_ventas = total_facturas + total_tickets
            num_documentos = num_facturas + num_tickets
            
            # Ventas del mes actual (facturas solo cobradas)
            cursor.execute(f'''
                SELECT COALESCE(SUM(total), 0) as total_mes
                FROM factura
                WHERE substr({FECHA_EFECTIVA_COBRADA}, 1, 4) = ?
                AND substr({FECHA_EFECTIVA_COBRADA}, 6, 2) = ?
                AND estado = 'C'
            ''', (str(anio), mes_str))
            facturas_mes = float(cursor.fetchone()['total_mes'] or 0)
            
            # Ventas del mes actual (tickets cobrados) - usar total para consistencia
            cursor.execute('''
                SELECT COALESCE(SUM(total), 0) as total_mes
                FROM tickets
                WHERE substr(fecha, 1, 4) = ?
                AND substr(fecha, 6, 2) = ?
                AND estado = 'C'
            ''', (str(anio), mes_str))
            tickets_mes = float(cursor.fetchone()['total_mes'] or 0)
            
            # Total mes (facturas + tickets)
            ventas_mes = facturas_mes + tickets_mes
            
            # ===== DATOS DE GASTOS (desde facturas_proveedores) =====
            # Total gastos del año completo
            cursor.execute(f'''
                SELECT
                    COALESCE(SUM(total), 0) as total_gastos,
                    COUNT(*) as num_gastos
                FROM facturas_proveedores
                WHERE año = ?{gasto_empresa_filter}
            ''', (anio, *gasto_empresa_params))
            gastos_anio = cursor.fetchone()
            total_gastos = float(gastos_anio['total_gastos'] or 0)
            num_gastos = int(gastos_anio['num_gastos'] or 0)
    
            # Gastos del mes actual
            cursor.execute(f'''
                SELECT COALESCE(SUM(total), 0) as total_mes
                FROM facturas_proveedores
                WHERE año = ?
                AND substr(fecha_emision, 6, 2) = ?{gasto_empresa_filter}
            ''', (anio, mes_str, *gasto_empresa_params))
            gastos_mes = float(cursor.fetchone()['total_mes'] or 0)
            
            # ===== ANÁLISIS Y MÉTRICAS =====
            balance_anio = total_ventas - total_gastos
            balance_mes = ventas_mes - gastos_mes
            
            # Ratios financieros
            margen_beneficio_anio = (balance_anio / total_ventas * 100) if total_ventas > 0 else 0
            margen_beneficio_mes = (balance_mes / ventas_mes * 100) if ventas_mes > 0 else 0
            ratio_gastos_ventas = (total_gastos / total_ventas * 100) if total_ventas > 0 else 0
            
            # Medias mensuales - EXCLUIR mes actual para consistencia con dashboard
            # Fórmula dashboard: (total - mes_actual) / (mes - 1)
            ventas_sin_mes_actual = total_ventas - ventas_mes
            media_ventas_mensual = ventas_sin_mes_actual / (mes - 1) if mes > 1 else 0
            media_gastos_mensual, gastos_sin_puntuales, _ = _calcular_media_mensual_sin_puntuales(conn, anio, mes, gasto_empresa_filter, gasto_empresa_params)
            media_balance_mensual = balance_anio / mes if mes > 0 else 0
            
            # Proyecciones para fin de año - usar fórmula dashboard
            meses_restantes = 12 - mes
            proyeccion_ventas = total_ventas + (media_ventas_mensual * meses_restantes)
            proyeccion_gastos = total_gastos + (media_gastos_mensual * meses_restantes)
            proyeccion_balance = proyeccion_ventas - proyeccion_gastos
            
            # Top 10 gastos por proveedor (desde facturas_proveedores) - año completo
            cursor.execute(f'''
                SELECT 
                    COALESCE(p.nombre, fp.concepto, 'Sin proveedor') as nombre_gasto,
                    COALESCE(SUM(fp.total), 0) as total,
                    COUNT(*) as cantidad
                FROM facturas_proveedores fp
                LEFT JOIN proveedores p ON fp.proveedor_id = p.id
                WHERE fp.año = ?{gasto_empresa_filter}
                GROUP BY nombre_gasto
                ORDER BY total DESC
                LIMIT 10
            ''', (anio, *gasto_empresa_params))
            
            top_categorias_gastos = []
            for row in cursor.fetchall():
                top_categorias_gastos.append({
                    'categoria': row['nombre_gasto'] or 'Sin nombre',
                    'total': round(float(row['total']), 2),
                    'cantidad': int(row['cantidad']),
                    'porcentaje': round((float(row['total']) / total_gastos * 100) if total_gastos > 0 else 0, 1)
                })
        
        # Determinar estado financiero
        if margen_beneficio_anio >= 20:
            estado = 'Excelente'
            color = 'green'
        elif margen_beneficio_anio >= 10:
            estado = 'Bueno'
            color = 'lightgreen'
        elif margen_beneficio_anio >= 5:
            estado = 'Aceptable'
            color = 'orange'
        elif margen_beneficio_anio > 0:
            estado = 'Precaución'
            color = 'darkorange'
        else:
            estado = 'Crítico'
            color = 'red'
        
        return jsonify({
            'anio': anio,
            'mes': mes,
            'periodo': f'Enero - {["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"][mes-1]} {anio}',
            'ventas': {
                'total_anio': round(total_ventas, 2),
                'total_mes': round(ventas_mes, 2),
                'num_facturas': num_facturas,
                'num_tickets': num_tickets,
                'num_documentos': num_documentos,
                'total_facturas': round(total_facturas, 2),
                'total_tickets': round(total_tickets, 2),
                'total_facturas_pendientes': round(total_fact_pendientes, 2),
                'num_facturas_pendientes': num_fact_pendientes,
                'total_facturas_vencidas': round(total_fact_vencidas, 2),
                'num_facturas_vencidas': num_fact_vencidas,
                'media_mensual': round(media_ventas_mensual, 2),
                'media_por_documento': round(total_ventas / num_documentos, 2) if num_documentos > 0 else 0
            },
            'gastos': {
                'total_anio': round(total_gastos, 2),
                'total_mes': round(gastos_mes, 2),
                'num_gastos': num_gastos,
                'media_mensual': round(media_gastos_mensual, 2),
                'top_categorias': top_categorias_gastos
            },
            'balance': {
                'anio': round(balance_anio, 2),
                'mes': round(balance_mes, 2),
                'media_mensual': round(media_balance_mensual, 2)
            },
            'ratios': {
                'margen_beneficio_anio': round(margen_beneficio_anio, 2),
                'margen_beneficio_mes': round(margen_beneficio_mes, 2),
                'ratio_gastos_ventas': round(ratio_gastos_ventas, 2)
            },
            'proyecciones': {
                'ventas': round(proyeccion_ventas, 2),
                'gastos': round(proyeccion_gastos, 2),
                'balance': round(proyeccion_balance, 2),
                'margen_proyectado': round((proyeccion_balance / proyeccion_ventas * 100) if proyeccion_ventas > 0 else 0, 2)
            },
            'estado': {
                'clasificacion': estado,
                'color': color
            }
        })
        
    except Exception as e:
        logger.error(f"Error al generar informe de situación: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@estadisticas_gastos_bp.route('/api/simulador-financiero', methods=['POST'])
def simular_escenarios():
    """
    Simula diferentes escenarios financieros para ver cómo cuadrar los números
    """
    try:
        data = request.json
        anio = data.get('anio', datetime.now().year)
        mes = data.get('mes', datetime.now().month)
        
        # Parámetros de simulación
        ajuste_ventas_pct = float(data.get('ajuste_ventas_pct', 0))  # % de incremento/reducción
        ajuste_gastos_pct = float(data.get('ajuste_gastos_pct', 0))
        incremento_precios_pct = float(data.get('incremento_precios_pct', 0))  # % de incremento en precios
        nuevas_ventas_mes = float(data.get('nuevas_ventas_mes', 0))  # Ventas adicionales por mes
        reduccion_gastos_mes = float(data.get('reduccion_gastos_mes', 0))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener datos reales actuales - EXCLUYENDO GASTOS PUNTUALES
        # Facturas cobradas (año completo)
        cursor.execute('''
            SELECT COALESCE(SUM(importe_cobrado), 0) as total
            FROM factura
            WHERE CAST(substr(fecha, 1, 4) AS INTEGER) = ?
            AND estado = 'C'
        ''', (anio,))
        ventas_facturas = float(cursor.fetchone()['total'] or 0)

        # Facturas pendientes (año completo)
        cursor.execute('''
            SELECT COALESCE(SUM(total), 0) as total
            FROM factura
            WHERE CAST(substr(fecha, 1, 4) AS INTEGER) = ?
            AND estado IN ('P', 'V')
        ''', (anio,))
        ventas_pendientes = float(cursor.fetchone()['total'] or 0)

        # Tickets cobrados (año completo)
        cursor.execute('''
            SELECT COALESCE(SUM(importe_cobrado), 0) as total
            FROM tickets
            WHERE CAST(substr(fecha, 1, 4) AS INTEGER) = ?
            AND estado = 'C'
        ''', (anio,))
        ventas_tickets = float(cursor.fetchone()['total'] or 0)

        # Gastos (desde facturas_proveedores) - año completo
        cursor.execute('''
            SELECT COALESCE(SUM(total), 0) as total
            FROM facturas_proveedores
            WHERE año = ?
        ''', (anio,))
        gastos_totales = float(cursor.fetchone()['total'] or 0)
        
        # Datos reales (incluye pendientes)
        ventas_reales = ventas_facturas + ventas_tickets + ventas_pendientes
        balance_real = ventas_reales - gastos_totales
        margen_real = (balance_real / ventas_reales * 100) if ventas_reales > 0 else 0
        
        # SIMULACIÓN: Aplicar ajustes
        # Incremento de precios aumenta el valor de las ventas actuales
        ventas_simuladas = ventas_reales * (1 + incremento_precios_pct / 100)
        # Incremento de ventas (por volumen)
        ventas_simuladas = ventas_simuladas * (1 + ajuste_ventas_pct / 100)
        # Ventas adicionales acumuladas
        ventas_simuladas += (nuevas_ventas_mes * mes)
        
        gastos_simulados = gastos_totales * (1 + ajuste_gastos_pct / 100)
        gastos_simulados -= (reduccion_gastos_mes * mes)  # Reducción acumulada
        
        balance_simulado = ventas_simuladas - gastos_simulados
        margen_simulado = (balance_simulado / ventas_simuladas * 100) if ventas_simuladas > 0 else 0
        
        # Proyección fin de año
        meses_restantes = 12 - mes
        
        # Real
        media_ventas_real = ventas_reales / mes if mes > 0 else 0
        media_gastos_real, gastos_sin_puntuales, _ = _calcular_media_mensual_sin_puntuales(conn, anio, mes)
        proyeccion_ventas_real = ventas_reales + (media_ventas_real * meses_restantes)
        proyeccion_gastos_real = gastos_totales + (media_gastos_real * meses_restantes)
        proyeccion_balance_real = proyeccion_ventas_real - proyeccion_gastos_real
        
        # Simulado
        media_ventas_sim = ventas_simuladas / mes if mes > 0 else 0
        media_gastos_sim = gastos_simulados / mes if mes > 0 else 0
        proyeccion_ventas_sim = ventas_simuladas + (media_ventas_sim * meses_restantes)
        proyeccion_gastos_sim = gastos_simulados + (media_gastos_sim * meses_restantes)
        proyeccion_balance_sim = proyeccion_ventas_sim - proyeccion_gastos_sim
        
        # Calcular punto de equilibrio
        if gastos_simulados > 0:
            ventas_necesarias_equilibrio = gastos_simulados
            incremento_necesario = ventas_necesarias_equilibrio - ventas_reales
            pct_incremento_necesario = (incremento_necesario / ventas_reales * 100) if ventas_reales > 0 else 0
        else:
            ventas_necesarias_equilibrio = 0
            incremento_necesario = 0
            pct_incremento_necesario = 0
        
        return jsonify({
            'anio': anio,
            'mes': mes,
            'real': {
                'ventas': round(ventas_reales, 2),
                'gastos': round(gastos_totales, 2),
                'balance': round(balance_real, 2),
                'margen': round(margen_real, 2),
                'proyeccion_balance': round(proyeccion_balance_real, 2)
            },
            'simulado': {
                'ventas': round(ventas_simuladas, 2),
                'gastos': round(gastos_simulados, 2),
                'balance': round(balance_simulado, 2),
                'margen': round(margen_simulado, 2),
                'proyeccion_balance': round(proyeccion_balance_sim, 2)
            },
            'diferencias': {
                'ventas': round(ventas_simuladas - ventas_reales, 2),
                'gastos': round(gastos_simulados - gastos_totales, 2),
                'balance': round(balance_simulado - balance_real, 2),
                'margen': round(margen_simulado - margen_real, 2),
                'proyeccion': round(proyeccion_balance_sim - proyeccion_balance_real, 2)
            },
            'equilibrio': {
                'ventas_necesarias': round(ventas_necesarias_equilibrio, 2),
                'incremento_necesario': round(incremento_necesario, 2),
                'pct_incremento': round(pct_incremento_necesario, 2)
            }
        })
        
    except Exception as e:
        logger.error(f"Error en simulador financiero: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500
    finally:
        # Cerrar conexión siempre
        if 'conn' in locals():
            conn.close()

@estadisticas_gastos_bp.route('/api/productos-mas-vendidos', methods=['GET'])
def productos_mas_vendidos():
    """
    Devuelve los productos más vendidos con cálculo de nuevo precio según porcentaje
    """
    try:
        porcentaje = float(request.args.get('porcentaje', 0))
        limite = int(request.args.get('limite', 20))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Usar la misma lógica que /api/productos/top_ventas: facturas + tickets, ordenado por total vendido
        anio = request.args.get('anio') or str(datetime.now().year)
        ejercicio_actual = datetime.now().year
        
        # Ventas del año seleccionado - sin filtrar por ejercicio ya que las ventas usan IDs originales
        cursor.execute('''
            WITH ventas_facturas AS (
                SELECT 
                    p.id as producto_id,
                    p.nombre,
                    p.subtotal as precio_sin_iva,
                    p.impuestos as iva_pct,
                    p.total as precio_con_iva,
                    COALESCE(SUM(CASE WHEN strftime('%Y', f.fecha) = ? THEN df.cantidad ELSE 0 END), 0) as cantidad_f,
                    COALESCE(SUM(CASE WHEN strftime('%Y', f.fecha) = ? THEN df.total ELSE 0 END), 0) as total_f
                FROM productos p
                LEFT JOIN detalle_factura df ON p.id = df.productoId
                LEFT JOIN factura f ON df.id_factura = f.id AND f.estado = 'C'
                WHERE p.subtotal > 0
                GROUP BY p.id, p.nombre
            ),
            ventas_tickets AS (
                SELECT 
                    p.id as producto_id,
                    COALESCE(SUM(CASE WHEN strftime('%Y', t.fecha) = ? THEN dt.cantidad ELSE 0 END), 0) as cantidad_t,
                    COALESCE(SUM(CASE WHEN strftime('%Y', t.fecha) = ? THEN dt.total ELSE 0 END), 0) as total_t
                FROM productos p
                LEFT JOIN detalle_tickets dt ON p.id = dt.productoId
                LEFT JOIN tickets t ON dt.id_ticket = t.id AND t.estado = 'C'
                WHERE p.subtotal > 0
                GROUP BY p.id
            )
            SELECT 
                vf.producto_id as id,
                vf.nombre,
                vf.precio_sin_iva,
                vf.iva_pct,
                vf.precio_con_iva,
                ROUND(vf.precio_sin_iva * (1 + ? / 100.0), 2) as nuevo_sin_iva,
                ROUND(vf.precio_con_iva * (1 + ? / 100.0), 2) as nuevo_con_iva,
                ROUND(vf.precio_sin_iva * ? / 100.0, 2) as incremento_sin_iva,
                ROUND(vf.precio_con_iva * ? / 100.0, 2) as incremento_con_iva,
                (vf.cantidad_f + COALESCE(vt.cantidad_t, 0)) as unidades_vendidas,
                (vf.total_f + COALESCE(vt.total_t, 0)) as total_vendido
            FROM ventas_facturas vf
            LEFT JOIN ventas_tickets vt ON vf.producto_id = vt.producto_id
            WHERE (vf.total_f + COALESCE(vt.total_t, 0)) > 0
            ORDER BY total_vendido DESC
            LIMIT ?
        ''', (anio, anio, anio, anio, porcentaje, porcentaje, porcentaje, porcentaje, limite))
        
        def to_float(val):
            if val is None:
                return 0.0
            if isinstance(val, (int, float)):
                return float(val)
            return float(str(val).replace(',', '.'))
        
        productos = []
        for row in cursor.fetchall():
            productos.append({
                'id': row['id'],
                'nombre': row['nombre'],
                'precio_sin_iva': round(to_float(row['precio_sin_iva']), 2),
                'precio_con_iva': round(to_float(row['precio_con_iva']), 2),
                'iva_pct': int(row['iva_pct'] or 21),
                'nuevo_sin_iva': round(to_float(row['nuevo_sin_iva']), 2),
                'nuevo_con_iva': round(to_float(row['nuevo_con_iva']), 2),
                'incremento_sin_iva': round(to_float(row['incremento_sin_iva']), 2),
                'incremento_con_iva': round(to_float(row['incremento_con_iva']), 2),
                'unidades_vendidas': int(row['unidades_vendidas'] or 0)
            })
        
        conn.close()
        
        return jsonify({
            'porcentaje': porcentaje,
            'productos': productos
        })
        
    except Exception as e:
        logger.error(f"Error al obtener productos más vendidos: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@estadisticas_gastos_bp.route('/api/duplicar-productos-ejercicio', methods=['POST'])
def duplicar_productos_ejercicio():
    """
    Duplica todos los productos del ejercicio anterior al nuevo ejercicio
    """
    try:
        data = request.json
        ejercicio_nuevo = int(data.get('ejercicio_nuevo', datetime.now().year))
        ejercicio_anterior = ejercicio_nuevo - 1
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si ya existen productos para el nuevo ejercicio
        cursor.execute('SELECT COUNT(*) as count FROM productos WHERE ejercicio = ?', (ejercicio_nuevo,))
        count = cursor.fetchone()['count']
        
        if count > 0:
            conn.close()
            return jsonify({
                'success': False,
                'mensaje': f'Ya existen {count} productos para el ejercicio {ejercicio_nuevo}',
                'productos_existentes': count
            })
        
        # Obtener productos del ejercicio anterior
        cursor.execute('''
            SELECT nombre, descripcion, subtotal, iva, impuestos, total,
                   calculo_automatico, franja_inicial, numero_franjas, ancho_franja,
                   descuento_inicial, incremento_franja, no_generar_franjas
            FROM productos 
            WHERE ejercicio = ?
        ''', (ejercicio_anterior,))
        
        productos_anteriores = cursor.fetchall()
        
        if not productos_anteriores:
            conn.close()
            return jsonify({
                'success': False,
                'mensaje': f'No hay productos en el ejercicio {ejercicio_anterior} para duplicar'
            })
        
        # Duplicar productos con el nuevo ejercicio
        productos_duplicados = 0
        franjas_duplicadas = 0
        
        for p in productos_anteriores:
            # Obtener el ID del producto original
            cursor.execute('SELECT id FROM productos WHERE nombre = ? AND ejercicio = ?', 
                          (p['nombre'], ejercicio_anterior))
            producto_original = cursor.fetchone()
            producto_id_original = producto_original['id'] if producto_original else None
            
            # Insertar el nuevo producto
            cursor.execute('''
                INSERT INTO productos (nombre, descripcion, subtotal, iva, impuestos, total,
                                       calculo_automatico, franja_inicial, numero_franjas, ancho_franja,
                                       descuento_inicial, incremento_franja, no_generar_franjas, ejercicio)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (p['nombre'], p['descripcion'], p['subtotal'], p['iva'], p['impuestos'], p['total'],
                  p['calculo_automatico'], p['franja_inicial'], p['numero_franjas'], p['ancho_franja'],
                  p['descuento_inicial'], p['incremento_franja'], p['no_generar_franjas'], ejercicio_nuevo))
            
            nuevo_producto_id = cursor.lastrowid
            productos_duplicados += 1
            
            # Duplicar franjas del producto si existen
            if producto_id_original:
                cursor.execute('''
                    SELECT min_cantidad, max_cantidad, porcentaje_descuento, calculo_automatico
                    FROM descuento_producto_franja
                    WHERE producto_id = ? AND ejercicio = ?
                ''', (producto_id_original, ejercicio_anterior))
                
                franjas = cursor.fetchall()
                for f in franjas:
                    cursor.execute('''
                        INSERT INTO descuento_producto_franja 
                        (producto_id, min_cantidad, max_cantidad, porcentaje_descuento, calculo_automatico, ejercicio)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (nuevo_producto_id, f['min_cantidad'], f['max_cantidad'], 
                          f['porcentaje_descuento'], f['calculo_automatico'], ejercicio_nuevo))
                    franjas_duplicadas += 1
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'mensaje': f'Se han duplicado {productos_duplicados} productos y {franjas_duplicadas} franjas al ejercicio {ejercicio_nuevo}',
            'productos_duplicados': productos_duplicados,
            'franjas_duplicadas': franjas_duplicadas
        })
        
    except Exception as e:
        logger.error(f"Error al duplicar productos: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

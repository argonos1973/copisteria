from flask import Blueprint, jsonify, request
from datetime import datetime
from db_utils import get_db_connection
import re

estadisticas_gastos_bp = Blueprint('estadisticas_gastos', __name__)

@estadisticas_gastos_bp.route('/api/gastos/estadisticas', methods=['GET'])
def obtener_estadisticas_gastos():
    """
    Devuelve estadísticas completas de gastos para un año específico
    Similar a las estadísticas de ventas pero para gastos (importe negativo)
    """
    try:
        anio = request.args.get('anio', datetime.now().year, type=int)
        mes = request.args.get('mes', datetime.now().month, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Gastos totales del año actual HASTA el mes seleccionado (inclusive)
        mes_str = str(mes).zfill(2)
        cursor.execute('''
            SELECT 
                COALESCE(SUM(ABS(importe_eur)), 0) as total_gastos_anio,
                COUNT(*) as cantidad_gastos_anio
            FROM gastos
            WHERE substr(fecha_operacion, 7, 4) = ?
            AND CAST(substr(fecha_operacion, 4, 2) AS INTEGER) <= ?
            AND importe_eur < 0
        ''', (str(anio), mes))
        
        datos_anio = cursor.fetchone()
        total_gastos_anio = float(datos_anio['total_gastos_anio'] or 0)
        cantidad_gastos_anio = int(datos_anio['cantidad_gastos_anio'] or 0)
        
        # Gastos del mes actual
        cursor.execute('''
            SELECT 
                COALESCE(SUM(ABS(importe_eur)), 0) as total_gastos_mes,
                COUNT(*) as cantidad_gastos_mes
            FROM gastos
            WHERE substr(fecha_operacion, 7, 4) = ?
            AND substr(fecha_operacion, 4, 2) = ?
            AND importe_eur < 0
        ''', (str(anio), mes_str))
        
        datos_mes = cursor.fetchone()
        total_gastos_mes = float(datos_mes['total_gastos_mes'] or 0)
        cantidad_gastos_mes = int(datos_mes['cantidad_gastos_mes'] or 0)
        
        # Gastos del año anterior HASTA el mismo mes (para comparación justa)
        anio_anterior = anio - 1
        cursor.execute('''
            SELECT COALESCE(SUM(ABS(importe_eur)), 0) as total_gastos_anio_anterior
            FROM gastos
            WHERE substr(fecha_operacion, 7, 4) = ?
            AND CAST(substr(fecha_operacion, 4, 2) AS INTEGER) <= ?
            AND importe_eur < 0
        ''', (str(anio_anterior), mes))
        
        total_gastos_anio_anterior = float(cursor.fetchone()['total_gastos_anio_anterior'] or 0)
        
        # Gastos del mismo mes del año anterior
        cursor.execute('''
            SELECT COALESCE(SUM(ABS(importe_eur)), 0) as total_gastos_mes_anterior
            FROM gastos
            WHERE substr(fecha_operacion, 7, 4) = ?
            AND substr(fecha_operacion, 4, 2) = ?
            AND importe_eur < 0
        ''', (str(anio_anterior), mes_str))
        
        total_gastos_mes_anterior = float(cursor.fetchone()['total_gastos_mes_anterior'] or 0)
        
        # Media mensual de gastos (meses transcurridos del año)
        meses_transcurridos = mes
        media_mensual = total_gastos_anio / meses_transcurridos if meses_transcurridos > 0 else 0
        
        # Previsión de gastos hasta fin de año
        meses_restantes = 12 - mes
        prevision_gastos = total_gastos_anio + (media_mensual * meses_restantes)
        
        # Calcular porcentajes
        pct_anio = ((total_gastos_anio - total_gastos_anio_anterior) / total_gastos_anio_anterior * 100) if total_gastos_anio_anterior > 0 else 0
        pct_mes = ((total_gastos_mes - total_gastos_mes_anterior) / total_gastos_mes_anterior * 100) if total_gastos_mes_anterior > 0 else 0
        
        conn.close()
        
        return jsonify({
            'anio': anio,
            'mes': mes,
            'total_gastos_anio': total_gastos_anio,
            'cantidad_gastos_anio': cantidad_gastos_anio,
            'total_gastos_mes': total_gastos_mes,
            'cantidad_gastos_mes': cantidad_gastos_mes,
            'total_gastos_anio_anterior': total_gastos_anio_anterior,
            'total_gastos_mes_anterior': total_gastos_mes_anterior,
            'media_mensual': media_mensual,
            'prevision_gastos_anio': prevision_gastos,
            'porcentaje_anio': round(pct_anio, 2),
            'porcentaje_mes': round(pct_mes, 2),
            'meses_transcurridos': meses_transcurridos
        })
        
    except Exception as e:
        print(f"Error en estadísticas gastos: {str(e)}")
        return jsonify({'error': str(e)}), 500


@estadisticas_gastos_bp.route('/api/gastos/top10', methods=['GET'])
def obtener_top10_gastos():
    """
    Devuelve el top 10 de conceptos de gastos del año actual
    Agrupados por concepto (primera palabra del concepto para simplificar)
    """
    try:
        anio = request.args.get('anio', datetime.now().year, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Top 10 gastos por concepto (agrupando por primeras palabras)
        cursor.execute('''
            SELECT 
                CASE 
                    WHEN concepto LIKE 'Recibo%' THEN 'Recibos'
                    WHEN concepto LIKE 'Liquidacion%' THEN 'Liquidaciones TPV'
                    WHEN concepto LIKE '%Transferencia%' THEN 'Transferencias'
                    WHEN concepto LIKE '%Bizum%' THEN 'Bizum'
                    WHEN concepto LIKE '%Tarjeta%' OR concepto LIKE '%Compra%' THEN 'Compras Tarjeta'
                    ELSE substr(concepto, 1, 30)
                END as concepto_resumido,
                COALESCE(SUM(ABS(importe_eur)), 0) as total_gasto,
                COUNT(*) as cantidad
            FROM gastos
            WHERE substr(fecha_operacion, 7, 4) = ?
            AND importe_eur < 0
            GROUP BY concepto_resumido
            ORDER BY total_gasto DESC
            LIMIT 10
        ''', (str(anio),))
        
        top_gastos = []
        for row in cursor.fetchall():
            top_gastos.append({
                'concepto': row['concepto_resumido'],
                'total': round(float(row['total_gasto'] or 0), 2),
                'cantidad': int(row['cantidad'] or 0)
            })
        
        # Obtener totales del año anterior para comparación
        anio_anterior = anio - 1
        for gasto in top_gastos:
            cursor.execute('''
                SELECT COALESCE(SUM(ABS(importe_eur)), 0) as total_anterior
                FROM gastos
                WHERE substr(fecha_operacion, 7, 4) = ?
                AND importe_eur < 0
                AND (
                    CASE 
                        WHEN concepto LIKE 'Recibo%' THEN 'Recibos'
                        WHEN concepto LIKE 'Liquidacion%' THEN 'Liquidaciones TPV'
                        WHEN concepto LIKE '%Transferencia%' THEN 'Transferencias'
                        WHEN concepto LIKE '%Bizum%' THEN 'Bizum'
                        WHEN concepto LIKE '%Tarjeta%' OR concepto LIKE '%Compra%' THEN 'Compras Tarjeta'
                        ELSE substr(concepto, 1, 30)
                    END
                ) = ?
            ''', (str(anio_anterior), gasto['concepto']))
            
            total_anterior = float(cursor.fetchone()['total_anterior'] or 0)
            diferencia = gasto['total'] - total_anterior
            pct_diferencia = (diferencia / total_anterior * 100) if total_anterior > 0 else 0
            
            gasto['total_anterior'] = round(total_anterior, 2)
            gasto['diferencia'] = round(diferencia, 2)
            gasto['porcentaje_diferencia'] = round(pct_diferencia, 2)
        
        conn.close()
        
        return jsonify({
            'anio': anio,
            'top_gastos': top_gastos
        })
        
    except Exception as e:
        print(f"Error en top10 gastos: {str(e)}")
        return jsonify({'error': str(e)}), 500

@estadisticas_gastos_bp.route('/api/gastos/detalles', methods=['GET'])
def obtener_detalles_gasto():
    """
    Devuelve los detalles de todos los gastos de un concepto específico
    """
    try:
        concepto = request.args.get('concepto', '')
        anio = request.args.get('anio', datetime.now().year, type=int)
        
        if not concepto:
            return jsonify({'error': 'Se requiere el parámetro concepto'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Construir el WHERE según el concepto
        where_clause = '''
            CASE 
                WHEN concepto LIKE 'Recibo%' THEN 'Recibos'
                WHEN concepto LIKE 'Liquidacion%' THEN 'Liquidaciones TPV'
                WHEN concepto LIKE '%Transferencia%' THEN 'Transferencias'
                WHEN concepto LIKE '%Bizum%' THEN 'Bizum'
                WHEN concepto LIKE '%Tarjeta%' OR concepto LIKE '%Compra%' THEN 'Compras Tarjeta'
                ELSE substr(concepto, 1, 30)
            END
        '''
        
        # Función para normalizar conceptos (eliminar números de recibo, referencias, etc.)
        def normalizar_concepto(concepto_original):
            # Eliminar números de recibo, referencias, códigos
            concepto = re.sub(r'N[ºo°]\s*Recibo[:\s]+[\d\s]+', '', concepto_original, flags=re.IGNORECASE)
            concepto = re.sub(r'Nº\s*[\d\s]+', '', concepto)
            concepto = re.sub(r'Ref[:\.\s]+.*?Mandato[:\s]+[\w\d\-]+', '', concepto, flags=re.IGNORECASE)
            concepto = re.sub(r'Ref[:\.\s]+[\w\d\-]+', '', concepto, flags=re.IGNORECASE)
            concepto = re.sub(r'Mandato[:\s]+[\w\d\-]+', '', concepto, flags=re.IGNORECASE)
            concepto = re.sub(r'Factura[:\s]+[\d\-\/]+', '', concepto, flags=re.IGNORECASE)
            concepto = re.sub(r'Contracte?\s+(Num\.?|N[ºo°])?\s*[\d\s]*', '', concepto, flags=re.IGNORECASE)
            concepto = re.sub(r'Subministrament\s+D\s+Aigua\s+Contracte\s+Num\.?', 'Subministrament D Aigua', concepto, flags=re.IGNORECASE)
            concepto = re.sub(r'\d{2}\/\d{2}\/\d{4}', '', concepto)  # Fechas
            concepto = re.sub(r'\d{4}-\d{2}-\d{2}', '', concepto)  # Fechas ISO
            concepto = re.sub(r'\bBb[a-z]{5}\b', '', concepto, flags=re.IGNORECASE)  # Códigos tipo Bbfztpn
            
            # === NORMALIZACIÓN ESPECÍFICA POR TIPO ===
            
            # TRANSFERENCIAS: Normalizar "Concepto:" y variaciones
            concepto = re.sub(r'Concepto:\s*', 'Concepto: ', concepto, flags=re.IGNORECASE)
            concepto = re.sub(r'\bConcepto\b(?!:)', 'Concepto:', concepto, flags=re.IGNORECASE)
            # Agrupar transferencias por destinatario (eliminar variaciones del concepto)
            if 'Transferencia' in concepto:
                # Normalizar "Transferencia Inmediata" → "Transferencia"
                concepto = re.sub(r'Transferencia\s+Inmediata\s+', 'Transferencia ', concepto, flags=re.IGNORECASE)
                # TRUYOL: Normalizar "Truyol Digital" → "Truyol"
                if 'truyol' in concepto.lower():
                    concepto = re.sub(r'Truyol\s+Digital', 'Truyol', concepto, flags=re.IGNORECASE)
                # Si tiene "A Favor De", mantener solo hasta el nombre
                match = re.search(r'(Transferencia.*?A\s+Favor\s+De\s+[\w\s]+?)\s+Concepto', concepto, re.IGNORECASE)
                if match:
                    concepto = match.group(1)
            
            # COMPRAS TARJETA: Eliminar info de tarjeta y localización
            if 'Compra' in concepto or 'Tarjeta' in concepto:
                # Normalizar "Compra Internet En" → "Compra En"
                concepto = re.sub(r'Compra\s+Internet\s+En\s+', 'Compra En ', concepto, flags=re.IGNORECASE)
                
                # AMAZON: Normalizar todas las compras de Amazon
                if 'amazon' in concepto.lower() or 'amzn' in concepto.lower():
                    concepto = 'Compra Amazon Business'
                
                # UBER EATS: Normalizar variaciones
                if 'uber' in concepto.lower() and 'eats' in concepto.lower():
                    concepto = 'Compra Uber Eats'
                
                # TAXI: Normalizar taxis (Llic, Lic., etc.)
                if 'taxi' in concepto.lower() or 'autotaxi' in concepto.lower():
                    concepto = 'Compra Taxi'
                
                # Eliminar todo después de la segunda coma (ciudad, tarjeta, comisión)
                partes = concepto.split(',')
                if len(partes) > 2:
                    concepto = ','.join(partes[:2])
                # Eliminar ", [Ciudad]" al final
                concepto = re.sub(r',\s*[A-Z][\w\s]+$', '', concepto)
                # Eliminar "Tarjeta , Comision" y variaciones
                concepto = re.sub(r',?\s*Tarjeta\s*,?\s*Comision\s*', '', concepto, flags=re.IGNORECASE)
                concepto = re.sub(r',?\s*Tarjeta\s*$', '', concepto, flags=re.IGNORECASE)
                concepto = re.sub(r',?\s*Tarj\.\s*:?\*?\d*\s*$', '', concepto, flags=re.IGNORECASE)
            
            # Eliminar ", De" al final y variaciones
            concepto = re.sub(r',\s*De\s*$', '', concepto, flags=re.IGNORECASE)
            concepto = re.sub(r',\s*D\s*$', '', concepto)  # Solo ", D" al final
            
            # REPSOL: Eliminar texto duplicado y redundante
            if 'repsol' in concepto.lower():
                # Eliminar "repsol Comercializadora D"
                concepto = re.sub(r'repsol\s+Comercializadora\s+D?', 'Repsol', concepto, flags=re.IGNORECASE)
                # Eliminar "Repsol XXXX" donde XXXX son números (códigos de contrato)
                concepto = re.sub(r'(Repsol)\s+\d+', r'\1', concepto, flags=re.IGNORECASE)
                # Si aparece "Repsol" duplicado, dejarlo una vez
                concepto = re.sub(r'(Repsol)[,\s]+(Repsol)', r'\1', concepto, flags=re.IGNORECASE)
            
            # ORANGE: Normalizar todas las variaciones
            if 'orange' in concepto.lower():
                # Normalizar TODO a "Recibo Orange"
                if 'Recibo' in concepto:
                    concepto = 'Recibo Orange Espagne'
            
            # Eliminar TODOS los números que quedan (muy agresivo)
            concepto = re.sub(r'\b\d+\b', '', concepto)  # Números aislados
            concepto = re.sub(r'\s+[A-Z]?\d+[A-Z]?\s*$', '', concepto)  # Códigos alfanuméricos al final
            
            # Eliminar texto redundante común
            concepto = re.sub(r'Periodo\s+Liquidacion[:\s]*[\/-]*\s*,?\s*', '', concepto, flags=re.IGNORECASE)
            concepto = re.sub(r',?\s*De\s+(No|Not\s+Provided)\s*$', '', concepto, flags=re.IGNORECASE)
            concepto = re.sub(r'\s*[\/-]+\s*', ' ', concepto)  # Barras y guiones sueltos
            concepto = re.sub(r'\s*R\.e\.\s*', ' ', concepto, flags=re.IGNORECASE)  # R.e. (régimen especial)
            concepto = re.sub(r'\bautonomos\b', 'Autónomos', concepto, flags=re.IGNORECASE)
            
            # Normalizar puntuación: S.l.u. → Slu, S.a.u → Sau, etc.
            concepto = re.sub(r'S\.[lL]\.[uU]\.', 'Slu', concepto)
            concepto = re.sub(r'S\.[aA]\.[uU]\.', 'Sau', concepto)
            concepto = re.sub(r'S\.[lL]\.', 'Sl', concepto)
            concepto = re.sub(r'S\.c\.c\.l\.', 'Sccl', concepto, flags=re.IGNORECASE)
            concepto = re.sub(r'S\.a\.', 'Sa', concepto, flags=re.IGNORECASE)
            concepto = re.sub(r'C\s+B\b', 'CB', concepto)
            
            # Eliminar múltiples espacios y puntuación redundante
            concepto = re.sub(r'\s+', ' ', concepto).strip()
            concepto = re.sub(r'[,\.\s]+$', '', concepto)
            concepto = re.sub(r'\s*,\s*,\s*', ', ', concepto)  # Comas duplicadas
            
            return concepto
        
        # Obtener todos los gastos y normalizarlos
        cursor.execute(f'''
            SELECT 
                concepto as concepto_original,
                ABS(importe_eur) as importe,
                fecha_operacion
            FROM gastos
            WHERE substr(fecha_operacion, 7, 4) = ?
            AND importe_eur < 0
            AND ({where_clause}) = ?
            ORDER BY fecha_operacion DESC
        ''', (str(anio), concepto))
        
        # Agrupar manualmente por concepto normalizado
        agrupados = {}
        for row in cursor.fetchall():
            concepto_norm = normalizar_concepto(row['concepto_original'])
            
            if concepto_norm not in agrupados:
                agrupados[concepto_norm] = {
                    'conceptos_originales': set(),
                    'importes': [],
                    'fechas': []
                }
            
            agrupados[concepto_norm]['conceptos_originales'].add(row['concepto_original'])
            agrupados[concepto_norm]['importes'].append(float(row['importe']))
            agrupados[concepto_norm]['fechas'].append(row['fecha_operacion'])
        
        # Convertir a lista ordenada por total
        gastos_agrupados = []
        for concepto_norm, datos in agrupados.items():
            total = sum(datos['importes'])
            cantidad = len(datos['importes'])
            promedio = total / cantidad if cantidad > 0 else 0
            
            gastos_agrupados.append({
                'concepto': concepto_norm,
                'cantidad': cantidad,
                'total': round(total, 2),
                'promedio': round(promedio, 2),
                'primera_fecha': min(datos['fechas']),
                'ultima_fecha': max(datos['fechas']),
                'conceptos_originales': list(datos['conceptos_originales'])[:3]  # Primeros 3 ejemplos
            })
        
        # Ordenar por total descendente
        gastos_agrupados.sort(key=lambda x: x['total'], reverse=True)
        
        # Calcular estadísticas del concepto
        cursor.execute(f'''
            SELECT 
                COUNT(*) as cantidad,
                COALESCE(SUM(ABS(importe_eur)), 0) as total,
                COALESCE(AVG(ABS(importe_eur)), 0) as promedio,
                COALESCE(MIN(ABS(importe_eur)), 0) as minimo,
                COALESCE(MAX(ABS(importe_eur)), 0) as maximo
            FROM gastos
            WHERE substr(fecha_operacion, 7, 4) = ?
            AND importe_eur < 0
            AND ({where_clause}) = ?
        ''', (str(anio), concepto))
        
        stats = cursor.fetchone()
        estadisticas = {
            'cantidad': int(stats['cantidad']),
            'total': round(float(stats['total']), 2),
            'promedio': round(float(stats['promedio']), 2),
            'minimo': round(float(stats['minimo']), 2),
            'maximo': round(float(stats['maximo']), 2)
        }
        
        conn.close()
        
        return jsonify({
            'concepto': concepto,
            'anio': anio,
            'estadisticas': estadisticas,
            'gastos_agrupados': gastos_agrupados
        })
        
    except Exception as e:
        print(f"Error al obtener detalles de gasto: {str(e)}")
        return jsonify({'error': str(e)}), 500

@estadisticas_gastos_bp.route('/api/gastos/por-categoria-mes', methods=['GET'])
def obtener_gastos_por_categoria_mes():
    """
    Devuelve gastos del mes actual agrupados por categoría para gráfico de pastel
    """
    try:
        anio = request.args.get('anio', datetime.now().year, type=int)
        mes = request.args.get('mes', datetime.now().month, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener gastos del mes actual por categoría
        cursor.execute('''
            SELECT 
                CASE 
                    WHEN concepto LIKE 'Recibo%' THEN 'Recibos'
                    WHEN concepto LIKE 'Liquidacion%' THEN 'Liquidaciones TPV'
                    WHEN concepto LIKE '%Transferencia%' THEN 'Transferencias'
                    WHEN concepto LIKE '%Bizum%' THEN 'Bizum'
                    WHEN concepto LIKE '%Tarjeta%' OR concepto LIKE '%Compra%' THEN 'Compras Tarjeta'
                    ELSE 'Otros'
                END as categoria,
                COALESCE(SUM(ABS(importe_eur)), 0) as total
            FROM gastos
            WHERE substr(fecha_operacion, 4, 2) = ?
            AND substr(fecha_operacion, 7, 4) = ?
            AND importe_eur < 0
            GROUP BY categoria
            ORDER BY total DESC
        ''', (str(mes).zfill(2), str(anio)))
        
        categorias = []
        for row in cursor.fetchall():
            categorias.append({
                'categoria': row['categoria'],
                'total': round(float(row['total'] or 0), 2)
            })
        
        conn.close()
        
        return jsonify({
            'anio': anio,
            'mes': mes,
            'categorias': categorias
        })
        
    except Exception as e:
        print(f"Error al obtener gastos por categoría: {str(e)}")
        return jsonify({'error': str(e)}), 500

@estadisticas_gastos_bp.route('/api/gastos/por-categoria-anio', methods=['GET'])
def obtener_gastos_por_categoria_anio():
    """
    Devuelve gastos del año completo agrupados por categoría para gráfico de pastel
    """
    try:
        anio = request.args.get('anio', datetime.now().year, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener gastos del año completo por categoría
        cursor.execute('''
            SELECT 
                CASE 
                    WHEN concepto LIKE 'Recibo%' THEN 'Recibos'
                    WHEN concepto LIKE 'Liquidacion%' THEN 'Liquidaciones TPV'
                    WHEN concepto LIKE '%Transferencia%' THEN 'Transferencias'
                    WHEN concepto LIKE '%Bizum%' THEN 'Bizum'
                    WHEN concepto LIKE '%Tarjeta%' OR concepto LIKE '%Compra%' THEN 'Compras Tarjeta'
                    ELSE 'Otros'
                END as categoria,
                COALESCE(SUM(ABS(importe_eur)), 0) as total
            FROM gastos
            WHERE substr(fecha_operacion, 7, 4) = ?
            AND importe_eur < 0
            GROUP BY categoria
            ORDER BY total DESC
        ''', (str(anio),))
        
        categorias = []
        for row in cursor.fetchall():
            categorias.append({
                'categoria': row['categoria'],
                'total': round(float(row['total'] or 0), 2)
            })
        
        conn.close()
        
        return jsonify({
            'anio': anio,
            'categorias': categorias
        })
        
    except Exception as e:
        print(f"Error al obtener gastos por categoría del año: {str(e)}")
        return jsonify({'error': str(e)}), 500

@estadisticas_gastos_bp.route('/api/gastos/detalles-categoria', methods=['GET'])
def obtener_detalles_categoria():
    """
    Devuelve los detalles de gastos de una categoría específica para un mes/año
    """
    try:
        categoria = request.args.get('categoria', type=str)
        anio = request.args.get('anio', datetime.now().year, type=int)
        mes = request.args.get('mes', type=int)  # Opcional
        
        if not categoria:
            return jsonify({'error': 'Categoría requerida'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Determinar el filtro de categoría
        if categoria == 'Recibos':
            filtro_categoria = "concepto LIKE 'Recibo%'"
        elif categoria == 'Liquidaciones TPV':
            filtro_categoria = "concepto LIKE 'Liquidacion%'"
        elif categoria == 'Transferencias':
            filtro_categoria = "concepto LIKE '%Transferencia%'"
        elif categoria == 'Bizum':
            filtro_categoria = "concepto LIKE '%Bizum%'"
        elif categoria == 'Compras Tarjeta':
            filtro_categoria = "(concepto LIKE '%Tarjeta%' OR concepto LIKE '%Compra%')"
        else:
            filtro_categoria = "1=1"  # Otros
        
        # Función para normalizar conceptos (igual que en Top 10)
        def normalizar_concepto(concepto_original):
            # Eliminar números de recibo, referencias, códigos
            concepto = re.sub(r'N[ºo°]\s*Recibo[:\s]+[\d\s]+', '', concepto_original, flags=re.IGNORECASE)
            concepto = re.sub(r'Nº\s*[\d\s]+', '', concepto)
            concepto = re.sub(r'Ref[:\.\s]+.*?Mandato[:\s]+[\w\d\-]+', '', concepto, flags=re.IGNORECASE)
            concepto = re.sub(r'Ref[:\.\s]+[\w\d\-]+', '', concepto, flags=re.IGNORECASE)
            concepto = re.sub(r'Mandato[:\s]+[\w\d\-]+', '', concepto, flags=re.IGNORECASE)
            concepto = re.sub(r'Factura[:\s]+[\d\-\/]+', '', concepto, flags=re.IGNORECASE)
            concepto = re.sub(r'Contracte?\s+(Num\.?|N[ºo°])?\s*[\d\s]*', '', concepto, flags=re.IGNORECASE)
            concepto = re.sub(r'Subministrament\s+D\s+Aigua\s+Contracte\s+Num\.?', 'Subministrament D Aigua', concepto, flags=re.IGNORECASE)
            concepto = re.sub(r'\d{2}\/\d{2}\/\d{4}', '', concepto)  # Fechas
            concepto = re.sub(r'\d{4}-\d{2}-\d{2}', '', concepto)  # Fechas ISO
            concepto = re.sub(r'\bBb[a-z]{5}\b', '', concepto, flags=re.IGNORECASE)  # Códigos tipo Bbfztpn
            
            # === NORMALIZACIÓN ESPECÍFICA POR TIPO ===
            
            # TRANSFERENCIAS: Normalizar "Concepto:" y variaciones
            concepto = re.sub(r'Concepto:\s*', 'Concepto: ', concepto, flags=re.IGNORECASE)
            concepto = re.sub(r'\bConcepto\b(?!:)', 'Concepto:', concepto, flags=re.IGNORECASE)
            # Agrupar transferencias por destinatario (eliminar variaciones del concepto)
            if 'Transferencia' in concepto:
                # Normalizar "Transferencia Inmediata" → "Transferencia"
                concepto = re.sub(r'Transferencia\s+Inmediata\s+', 'Transferencia ', concepto, flags=re.IGNORECASE)
                # TRUYOL: Normalizar "Truyol Digital" → "Truyol"
                if 'truyol' in concepto.lower():
                    concepto = re.sub(r'Truyol\s+Digital', 'Truyol', concepto, flags=re.IGNORECASE)
                # Si tiene "A Favor De", mantener solo hasta el nombre
                match = re.search(r'(Transferencia.*?A\s+Favor\s+De\s+[\w\s]+?)\s+Concepto', concepto, re.IGNORECASE)
                if match:
                    concepto = match.group(1)
            
            # COMPRAS TARJETA: Eliminar info de tarjeta y localización
            if 'Compra' in concepto or 'Tarjeta' in concepto:
                # Normalizar "Compra Internet En" → "Compra En"
                concepto = re.sub(r'Compra\s+Internet\s+En\s+', 'Compra En ', concepto, flags=re.IGNORECASE)
                
                # AMAZON: Normalizar todas las compras de Amazon
                if 'amazon' in concepto.lower() or 'amzn' in concepto.lower():
                    concepto = 'Compra Amazon Business'
                
                # UBER EATS: Normalizar variaciones
                if 'uber' in concepto.lower() and 'eats' in concepto.lower():
                    concepto = 'Compra Uber Eats'
                
                # TAXI: Normalizar taxis (Llic, Lic., etc.)
                if 'taxi' in concepto.lower() or 'autotaxi' in concepto.lower():
                    concepto = 'Compra Taxi'
                
                # Eliminar todo después de la segunda coma (ciudad, tarjeta, comisión)
                partes = concepto.split(',')
                if len(partes) > 2:
                    concepto = ','.join(partes[:2])
                # Eliminar ", [Ciudad]" al final
                concepto = re.sub(r',\s*[A-Z][\w\s]+$', '', concepto)
                # Eliminar "Tarjeta , Comision" y variaciones
                concepto = re.sub(r',?\s*Tarjeta\s*,?\s*Comision\s*', '', concepto, flags=re.IGNORECASE)
                concepto = re.sub(r',?\s*Tarjeta\s*$', '', concepto, flags=re.IGNORECASE)
                concepto = re.sub(r',?\s*Tarj\.\s*:?\*?\d*\s*$', '', concepto, flags=re.IGNORECASE)
            
            # Eliminar ", De" al final y variaciones
            concepto = re.sub(r',\s*De\s*$', '', concepto, flags=re.IGNORECASE)
            concepto = re.sub(r',\s*D\s*$', '', concepto)  # Solo ", D" al final
            
            # REPSOL: Eliminar texto duplicado y redundante
            if 'repsol' in concepto.lower():
                # Eliminar "repsol Comercializadora D"
                concepto = re.sub(r'repsol\s+Comercializadora\s+D?', 'Repsol', concepto, flags=re.IGNORECASE)
                # Eliminar "Repsol XXXX" donde XXXX son números (códigos de contrato)
                concepto = re.sub(r'(Repsol)\s+\d+', r'\1', concepto, flags=re.IGNORECASE)
                # Si aparece "Repsol" duplicado, dejarlo una vez
                concepto = re.sub(r'(Repsol)[,\s]+(Repsol)', r'\1', concepto, flags=re.IGNORECASE)
            
            # ORANGE: Normalizar todas las variaciones
            if 'orange' in concepto.lower():
                # Normalizar TODO a "Recibo Orange"
                if 'Recibo' in concepto:
                    concepto = 'Recibo Orange Espagne'
            
            # Eliminar TODOS los números que quedan (muy agresivo)
            concepto = re.sub(r'\b\d+\b', '', concepto)  # Números aislados
            concepto = re.sub(r'\s+[A-Z]?\d+[A-Z]?\s*$', '', concepto)  # Códigos alfanuméricos al final
            
            # Eliminar texto redundante común
            concepto = re.sub(r'Periodo\s+Liquidacion[:\s]*[\/-]*\s*,?\s*', '', concepto, flags=re.IGNORECASE)
            concepto = re.sub(r',?\s*De\s+(No|Not\s+Provided)\s*$', '', concepto, flags=re.IGNORECASE)
            concepto = re.sub(r'\s*[\/-]+\s*', ' ', concepto)  # Barras y guiones sueltos
            concepto = re.sub(r'\s*R\.e\.\s*', ' ', concepto, flags=re.IGNORECASE)  # R.e. (régimen especial)
            concepto = re.sub(r'\bautonomos\b', 'Autónomos', concepto, flags=re.IGNORECASE)
            
            # Normalizar puntuación: S.l.u. → Slu, S.a.u → Sau, etc.
            concepto = re.sub(r'S\.[lL]\.[uU]\.', 'Slu', concepto)
            concepto = re.sub(r'S\.[aA]\.[uU]\.', 'Sau', concepto)
            concepto = re.sub(r'S\.[lL]\.', 'Sl', concepto)
            concepto = re.sub(r'S\.c\.c\.l\.', 'Sccl', concepto, flags=re.IGNORECASE)
            concepto = re.sub(r'S\.a\.', 'Sa', concepto, flags=re.IGNORECASE)
            concepto = re.sub(r'C\s+B\b', 'CB', concepto)
            
            # Eliminar múltiples espacios y puntuación redundante
            concepto = re.sub(r'\s+', ' ', concepto).strip()
            concepto = re.sub(r'[,\.\s]+$', '', concepto)
            concepto = re.sub(r'\s*,\s*,\s*', ', ', concepto)  # Comas duplicadas
            
            return concepto
        
        # Obtener gastos sin agrupar para poder normalizarlos
        if mes:
            query = f'''
                SELECT 
                    concepto,
                    fecha_operacion,
                    ABS(importe_eur) as importe
                FROM gastos
                WHERE substr(fecha_operacion, 4, 2) = ?
                AND substr(fecha_operacion, 7, 4) = ?
                AND importe_eur < 0
                AND {filtro_categoria}
            '''
            cursor.execute(query, (str(mes).zfill(2), str(anio)))
        else:
            query = f'''
                SELECT 
                    concepto,
                    fecha_operacion,
                    ABS(importe_eur) as importe
                FROM gastos
                WHERE substr(fecha_operacion, 7, 4) = ?
                AND importe_eur < 0
                AND {filtro_categoria}
            '''
            cursor.execute(query, (str(anio),))
        
        # Agrupar manualmente por concepto normalizado
        gastos_agrupados = {}
        for row in cursor.fetchall():
            concepto_norm = normalizar_concepto(row['concepto'])
            if concepto_norm not in gastos_agrupados:
                gastos_agrupados[concepto_norm] = {
                    'concepto': concepto_norm,
                    'fecha': row['fecha_operacion'],
                    'importe': 0.0,
                    'cantidad': 0
                }
            gastos_agrupados[concepto_norm]['importe'] += float(row['importe'] or 0)
            gastos_agrupados[concepto_norm]['cantidad'] += 1
        
        # Convertir a lista y ordenar
        gastos = sorted(gastos_agrupados.values(), key=lambda x: x['importe'], reverse=True)[:100]
        
        # Redondear importes
        for g in gastos:
            g['importe'] = round(g['importe'], 2)
        
        # Estadísticas
        total = sum(g['importe'] for g in gastos)
        cantidad = sum(g['cantidad'] for g in gastos)
        promedio = total / cantidad if cantidad > 0 else 0
        
        conn.close()
        
        return jsonify({
            'categoria': categoria,
            'anio': anio,
            'mes': mes,
            'estadisticas': {
                'total': round(total, 2),
                'cantidad': cantidad,
                'promedio': round(promedio, 2)
            },
            'gastos': gastos
        })
        
    except Exception as e:
        print(f"Error al obtener detalles de categoría: {str(e)}")
        return jsonify({'error': str(e)}), 500

@estadisticas_gastos_bp.route('/api/gastos/evolucion-mensual', methods=['GET'])
def obtener_evolucion_mensual():
    """
    Devuelve la evolución mensual de gastos para una categoría específica
    """
    try:
        categoria = request.args.get('categoria', 'global', type=str)
        anio = request.args.get('anio', datetime.now().year, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Determinar el filtro de categoría
        if categoria == 'global':
            filtro_categoria = "1=1"
        elif categoria == 'Recibos':
            filtro_categoria = "concepto LIKE 'Recibo%'"
        elif categoria == 'Liquidaciones TPV':
            filtro_categoria = "concepto LIKE 'Liquidacion%'"
        elif categoria == 'Transferencias':
            filtro_categoria = "concepto LIKE '%Transferencia%'"
        elif categoria == 'Bizum':
            filtro_categoria = "concepto LIKE '%Bizum%'"
        elif categoria == 'Compras Tarjeta':
            filtro_categoria = "(concepto LIKE '%Tarjeta%' OR concepto LIKE '%Compra%')"
        else:
            filtro_categoria = "1=1"
        
        # Query para obtener gastos por mes
        query = f'''
            SELECT 
                CAST(substr(fecha_operacion, 4, 2) AS INTEGER) as mes,
                SUM(ABS(importe_eur)) as total,
                COUNT(*) as cantidad
            FROM gastos
            WHERE substr(fecha_operacion, 7, 4) = ?
            AND importe_eur < 0
            AND {filtro_categoria}
            GROUP BY mes
            ORDER BY mes
        '''
        
        cursor.execute(query, (str(anio),))
        
        # Crear array con todos los meses (0 si no hay datos)
        meses_data = {i: {'total': 0.0, 'cantidad': 0} for i in range(1, 13)}
        
        for row in cursor.fetchall():
            mes = int(row['mes'])
            meses_data[mes] = {
                'total': round(float(row['total'] or 0), 2),
                'cantidad': int(row['cantidad'])
            }
        
        # Convertir a lista ordenada
        resultado = []
        nombres_meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        
        for mes in range(1, 13):
            resultado.append({
                'mes': mes,
                'nombre': nombres_meses[mes - 1],
                'total': meses_data[mes]['total'],
                'cantidad': meses_data[mes]['cantidad']
            })
        
        conn.close()
        
        return jsonify({
            'categoria': categoria,
            'anio': anio,
            'meses': resultado
        })
        
    except Exception as e:
        print(f"Error al obtener evolución mensual: {str(e)}")
        return jsonify({'error': str(e)}), 500

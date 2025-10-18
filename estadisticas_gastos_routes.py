from flask import Blueprint, jsonify, request
from datetime import datetime
from db_utils import get_db_connection
import re
from logger_config import get_estadisticas_logger

logger = get_estadisticas_logger()

estadisticas_gastos_bp = Blueprint('estadisticas_gastos', __name__)

# ===== FUNCIONES AUXILIARES COMPARTIDAS =====

def _inicializar_campo_puntual(conn):
    """
    Inicializa el campo 'puntual' en la tabla gastos si no existe.
    El campo puntual indica si un gasto es puntual (1) o recurrente (0).
    """
    try:
        cursor = conn.cursor()

        # Verificar si el campo ya existe
        cursor.execute("PRAGMA table_info(gastos)")
        columnas = cursor.fetchall()
        columnas_nombres = [col['name'] for col in columnas]

        if 'puntual' not in columnas_nombres:
            logger.info("Agregando campo 'puntual' a tabla gastos")
            cursor.execute("ALTER TABLE gastos ADD COLUMN puntual INTEGER DEFAULT 0")

        conn.commit()
        logger.debug("Campo 'puntual' inicializado correctamente")
    except Exception as e:
        logger.error(f"Error al inicializar campo puntual: {e}", exc_info=True)
        conn.rollback()

def _marcar_gastos_puntuales(conn, gastos_puntuales_ids):
    """
    Marca los gastos puntuales en la base de datos.
    puntual = 1: gastos puntuales automáticos (>1000€ no recurrentes)
    puntual = 2: gastos excluidos manualmente (ej: devoluciones)
    Args:
        conn: conexión a la base de datos
        gastos_puntuales_ids: set o lista de IDs de gastos que son puntuales
    """
    if not gastos_puntuales_ids:
        # Si no hay gastos puntuales automáticos, desmarcar solo los automáticos (puntual=1)
        # Preservar los manuales (puntual=2)
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE gastos SET puntual = 0 WHERE puntual = 1")
            conn.commit()
        except Exception as e:
            logger.error(f"Error al desmarcar gastos puntuales automáticos: {e}", exc_info=True)
            conn.rollback()
        return

    try:
        cursor = conn.cursor()

        # Convertir set a lista si es necesario
        ids_lista = list(gastos_puntuales_ids) if isinstance(gastos_puntuales_ids, set) else gastos_puntuales_ids

        # Marcar gastos puntuales automáticos (solo si no están marcados manualmente)
        placeholders = ','.join('?' * len(ids_lista))
        cursor.execute(f"""
            UPDATE gastos
            SET puntual = 1
            WHERE id IN ({placeholders})
            AND (puntual = 0 OR puntual IS NULL OR puntual = 1)
        """, ids_lista)

        # Desmarcar SOLO gastos automáticos (puntual=1) que ya no son puntuales
        # NO tocar los manuales (puntual=2)
        cursor.execute(f"""
            UPDATE gastos
            SET puntual = 0
            WHERE puntual = 1 AND id NOT IN ({placeholders})
        """, ids_lista)

        conn.commit()
        logger.info(f"Marcados {len(gastos_puntuales_ids)} gastos como puntuales")
    except Exception as e:
        logger.error(f"Error al marcar gastos puntuales: {e}", exc_info=True)
        conn.rollback()

def _identificar_gastos_puntuales(conn, anio, mes=None):
    """
    Identifica gastos puntuales según los criterios específicos del usuario:
    - Gastos individuales >1000€ que no se repitan durante 3 meses
    - Múltiples gastos del mismo día que sumen >1000€ y no se repitan durante 3 meses

    Args:
        conn: conexión a la base de datos
        anio: año para analizar
        mes: mes hasta el cual analizar (opcional)

    Returns:
        set: IDs de gastos que son puntuales según los criterios
    """
    cursor = conn.cursor()

    # Obtener todos los gastos del año
    if mes:
        cursor.execute('''
            SELECT id, concepto, ABS(importe_eur) as importe, fecha_operacion
            FROM gastos
            WHERE substr(fecha_operacion, 7, 4) = ?
            AND CAST(substr(fecha_operacion, 4, 2) AS INTEGER) <= ?
            AND importe_eur < 0
        ''', (str(anio), mes))
    else:
        cursor.execute('''
            SELECT id, concepto, ABS(importe_eur) as importe, fecha_operacion
            FROM gastos
            WHERE substr(fecha_operacion, 7, 4) = ?
            AND importe_eur < 0
        ''', (str(anio),))

    gastos = cursor.fetchall()

    if not gastos:
        return set()

    gastos_puntuales = set()

    # 1. Agrupar todos los gastos por (concepto normalizado + fecha)
    gastos_por_concepto_fecha = {}
    for gasto in gastos:
        concepto_norm = _normalizar_concepto(gasto['concepto'])
        fecha = gasto['fecha_operacion']
        clave = (concepto_norm, fecha)
        
        if clave not in gastos_por_concepto_fecha:
            gastos_por_concepto_fecha[clave] = []
        gastos_por_concepto_fecha[clave].append(gasto)

    # 2. Identificar grupos que sumen >1000€ (individual o agregado del mismo día)
    gastos_altos_por_concepto = {}
    
    for (concepto_norm, fecha), gastos_del_dia in gastos_por_concepto_fecha.items():
        total_dia = sum(g['importe'] for g in gastos_del_dia)
        
        # Si el total del día >1000€, considerarlo como gasto alto
        if total_dia > 1000:
            if concepto_norm not in gastos_altos_por_concepto:
                gastos_altos_por_concepto[concepto_norm] = []
            
            # Guardar todos los gastos de ese día junto con la fecha
            gastos_altos_por_concepto[concepto_norm].append({
                'gastos': gastos_del_dia,
                'fecha': fecha,
                'total': total_dia
            })

    # 3. Para cada concepto, verificar en cuántos meses diferentes aparece
    for concepto_norm, dias_con_gastos in gastos_altos_por_concepto.items():
        # Obtener los meses únicos en los que aparece este concepto con gastos >1000€
        meses_unicos = set()
        for dia_info in dias_con_gastos:
            mes_gasto = dia_info['fecha'][3:5]  # Extraer MM de dd/MM/yyyy
            meses_unicos.add(mes_gasto)

        # Si este concepto aparece en menos de 3 meses diferentes, todos sus gastos son puntuales
        if len(meses_unicos) < 3:
            for dia_info in dias_con_gastos:
                for g in dia_info['gastos']:
                    gastos_puntuales.add(g['id'])

    return gastos_puntuales

def _calcular_media_mensual_sin_puntuales(conn, anio, mes=None):
    """
    Calcula la media mensual excluyendo gastos puntuales

    Args:
        conn: conexión a la base de datos
        anio: año para calcular
        mes: mes hasta el cual calcular (opcional)

    Returns:
        tuple: (media_mensual, total_gastos_sin_puntuales, num_meses)
    """
    # Inicializar campo puntual si no existe
    _inicializar_campo_puntual(conn)

    # Identificar y marcar gastos puntuales
    gastos_puntuales_ids = _identificar_gastos_puntuales(conn, anio, mes)
    _marcar_gastos_puntuales(conn, gastos_puntuales_ids)

    # Calcular gastos excluyendo puntuales marcados
    cursor = conn.cursor()
    if mes:
        cursor.execute('''
            SELECT
                COALESCE(SUM(ABS(importe_eur)), 0) as total_sin_puntuales,
                COUNT(*) as cantidad_sin_puntuales
            FROM gastos
            WHERE substr(fecha_operacion, 7, 4) = ?
            AND CAST(substr(fecha_operacion, 4, 2) AS INTEGER) <= ?
            AND importe_eur < 0
            AND (puntual IS NULL OR puntual = 0)
        ''', (str(anio), mes))
    else:
        cursor.execute('''
            SELECT
                COALESCE(SUM(ABS(importe_eur)), 0) as total_sin_puntuales,
                COUNT(*) as cantidad_sin_puntuales
            FROM gastos
            WHERE substr(fecha_operacion, 7, 4) = ?
            AND importe_eur < 0
            AND (puntual IS NULL OR puntual = 0)
        ''', (str(anio),))

    resultado = cursor.fetchone()
    total_sin_puntuales = float(resultado['total_sin_puntuales'] or 0)
    cantidad_sin_puntuales = int(resultado['cantidad_sin_puntuales'] or 0)

    # Calcular media mensual
    num_meses = mes if mes else 12
    media_mensual = total_sin_puntuales / num_meses if num_meses > 0 else 0

    return media_mensual, total_sin_puntuales, num_meses

def _obtener_case_categoria_sql():
    """Devuelve el CASE SQL para categorizar gastos"""
    return '''
        CASE 
            WHEN concepto LIKE 'Recibo%' THEN 'Recibos'
            WHEN concepto LIKE 'Liquidacion%' THEN 'Liquidaciones TPV'
            WHEN concepto LIKE '%Transferencia%' THEN 'Transferencias'
            WHEN concepto LIKE '%Bizum%' THEN 'Bizum'
            WHEN (concepto LIKE '%Tarjeta%' OR concepto LIKE '%Compra%') AND concepto NOT LIKE 'Liquidacion%' THEN 'Compras Tarjeta'
            ELSE substr(concepto, 1, 30)
        END
    '''

def _obtener_filtro_categoria(categoria):
    """Devuelve el filtro SQL WHERE para una categoría específica"""
    filtros = {
        'Recibos': "concepto LIKE 'Recibo%'",
        'Liquidaciones TPV': "concepto LIKE 'Liquidacion%'",
        'Transferencias': "concepto LIKE '%Transferencia%'",
        'Bizum': "concepto LIKE '%Bizum%'",
        'Compras Tarjeta': "((concepto LIKE '%Tarjeta%' OR concepto LIKE '%Compra%') AND concepto NOT LIKE 'Liquidacion%')",
        'Otros': """(concepto NOT LIKE 'Recibo%' 
                    AND concepto NOT LIKE 'Liquidacion%' 
                    AND concepto NOT LIKE '%Transferencia%' 
                    AND concepto NOT LIKE '%Bizum%' 
                    AND concepto NOT LIKE '%Tarjeta%' 
                    AND concepto NOT LIKE '%Compra%')"""
    }
    return filtros.get(categoria, "1=1")

def _normalizar_concepto(concepto_original):
    """Normaliza un concepto de gasto eliminando referencias, números y código redundante"""
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
    
    # TRANSFERENCIAS: Agrupar por destinatario (eliminar variaciones del concepto)
    if 'Transferencia' in concepto:
        # Normalizar "Transferencia Inmediata" → "Transferencia"
        concepto = re.sub(r'Transferencia\s+Inmediata\s+', 'Transferencia ', concepto, flags=re.IGNORECASE)
        # TRUYOL: Normalizar "Truyol Digital" → "Truyol"
        if 'truyol' in concepto.lower():
            concepto = re.sub(r'Truyol\s+Digital', 'Truyol', concepto, flags=re.IGNORECASE)
        # Si tiene "A Favor De", mantener solo hasta el nombre (eliminar todo después)
        match = re.search(r'(Transferencia.*?A\s+Favor\s+De\s+[\w\s,]+?)\s+Concepto', concepto, re.IGNORECASE)
        if match:
            concepto = match.group(1).strip()
    
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
        
        # Eliminar información de tarjeta y comisión (con números)
        # Formato: ", Tarjeta 4176570108340631 , Comision 0" o "Comision 0,00"
        concepto = re.sub(r',\s*Tarjeta\s+[\d\s]+,\s*Comision\s+[\d,\.]+', '', concepto, flags=re.IGNORECASE)
        # Formato más simple: ", Tarjeta , Comision"
        concepto = re.sub(r',?\s*Tarjeta\s*,?\s*Comision\s*', '', concepto, flags=re.IGNORECASE)
        # Eliminar solo ", Tarjeta" al final
        concepto = re.sub(r',?\s*Tarjeta\s*$', '', concepto, flags=re.IGNORECASE)
        concepto = re.sub(r',?\s*Tarj\.\s*:?\*?\d*\s*$', '', concepto, flags=re.IGNORECASE)
        
        # Eliminar todo después de la segunda coma (ciudad)
        partes = concepto.split(',')
        if len(partes) > 2:
            concepto = ','.join(partes[:2])
        # Eliminar ", [Ciudad]" al final
        concepto = re.sub(r',\s*[A-Z][\w\s]+$', '', concepto)
    
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
    concepto = re.sub(r'Periodo\s+Liquidacion[:\s]*[\/\-]*\s*,?\s*', '', concepto, flags=re.IGNORECASE)
    concepto = re.sub(r',?\s*De\s+(No|Not\s+Provided)\s*$', '', concepto, flags=re.IGNORECASE)
    concepto = re.sub(r'\s*[\/\-]+\s*', ' ', concepto)  # Barras y guiones sueltos
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
    concepto = re.sub(r'[,.\s]+$', '', concepto)
    concepto = re.sub(r'\s*,\s*,\s*', ', ', concepto)  # Comas duplicadas
    
    return concepto

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
        
        # Inicializar campo puntual si no existe
        _inicializar_campo_puntual(conn)

        # Identificar y marcar gastos puntuales
        gastos_puntuales_ids = _identificar_gastos_puntuales(conn, anio, mes)
        _marcar_gastos_puntuales(conn, gastos_puntuales_ids)

        # Gastos totales del año actual HASTA el mes seleccionado (inclusive) - EXCLUYENDO PUNTUALES
        mes_str = str(mes).zfill(2)
        cursor.execute('''
            SELECT
                COALESCE(SUM(ABS(importe_eur)), 0) as total_gastos_anio,
                COUNT(*) as cantidad_gastos_anio
            FROM gastos
            WHERE substr(fecha_operacion, 7, 4) = ?
            AND CAST(substr(fecha_operacion, 4, 2) AS INTEGER) <= ?
            AND importe_eur < 0
            AND (puntual IS NULL OR puntual = 0)
        ''', (str(anio), mes))

        datos_anio = cursor.fetchone()
        total_gastos_anio = float(datos_anio['total_gastos_anio'] or 0)
        cantidad_gastos_anio = int(datos_anio['cantidad_gastos_anio'] or 0)

        # Gastos del mes actual - EXCLUYENDO PUNTUALES
        cursor.execute('''
            SELECT
                COALESCE(SUM(ABS(importe_eur)), 0) as total_gastos_mes,
                COUNT(*) as cantidad_gastos_mes
            FROM gastos
            WHERE substr(fecha_operacion, 7, 4) = ?
            AND substr(fecha_operacion, 4, 2) = ?
            AND importe_eur < 0
            AND (puntual IS NULL OR puntual = 0)
        ''', (str(anio), mes_str))

        datos_mes = cursor.fetchone()
        total_gastos_mes = float(datos_mes['total_gastos_mes'] or 0)
        cantidad_gastos_mes = int(datos_mes['cantidad_gastos_mes'] or 0)

        # Gastos del año anterior HASTA el mismo mes (para comparación justa) - EXCLUYENDO PUNTUALES
        anio_anterior = anio - 1
        cursor.execute('''
            SELECT COALESCE(SUM(ABS(importe_eur)), 0) as total_gastos_anio_anterior
            FROM gastos
            WHERE substr(fecha_operacion, 7, 4) = ?
            AND CAST(substr(fecha_operacion, 4, 2) AS INTEGER) <= ?
            AND importe_eur < 0
            AND (puntual IS NULL OR puntual = 0)
        ''', (str(anio_anterior), mes))

        total_gastos_anio_anterior = float(cursor.fetchone()['total_gastos_anio_anterior'] or 0)

        # Gastos del mismo mes del año anterior - EXCLUYENDO PUNTUALES
        cursor.execute('''
            SELECT COALESCE(SUM(ABS(importe_eur)), 0) as total_gastos_mes_anterior
            FROM gastos
            WHERE substr(fecha_operacion, 7, 4) = ?
            AND substr(fecha_operacion, 4, 2) = ?
            AND importe_eur < 0
            AND (puntual IS NULL OR puntual = 0)
        ''', (str(anio_anterior), mes_str))

        total_gastos_mes_anterior = float(cursor.fetchone()['total_gastos_mes_anterior'] or 0)
        
        # Media mensual de gastos (excluyendo gastos puntuales)
        media_mensual, total_gastos_sin_puntuales, meses_transcurridos = _calcular_media_mensual_sin_puntuales(conn, anio, mes)
        
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
        logger.error(f"Error en estadísticas gastos: {str(e)}", exc_info=True)
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
        
        # Inicializar y marcar gastos puntuales
        _inicializar_campo_puntual(conn)
        gastos_puntuales_ids = _identificar_gastos_puntuales(conn, anio)
        _marcar_gastos_puntuales(conn, gastos_puntuales_ids)
        
        # Top 10 gastos por concepto (agrupando por primeras palabras)
        case_categoria = _obtener_case_categoria_sql()
        cursor.execute(f'''
            SELECT 
                {case_categoria} as concepto_resumido,
                COALESCE(SUM(ABS(importe_eur)), 0) as total_gasto,
                COUNT(*) as cantidad,
                SUM(CASE WHEN puntual = 1 THEN 1 ELSE 0 END) as cantidad_puntuales,
                COALESCE(SUM(CASE WHEN puntual = 1 THEN ABS(importe_eur) ELSE 0 END), 0) as total_puntuales
            FROM gastos
            WHERE substr(fecha_operacion, 7, 4) = ?
            AND importe_eur < 0
            GROUP BY concepto_resumido
            ORDER BY total_gasto DESC
            LIMIT 10
        ''', (str(anio),))
        
        top_gastos = []
        for row in cursor.fetchall():
            cantidad_puntuales = int(row['cantidad_puntuales'] or 0)
            total_puntuales = float(row['total_puntuales'] or 0)
            total_gasto = float(row['total_gasto'] or 0)
            
            # Determinar si es principalmente puntual (más del 50% del total es puntual)
            es_mayormente_puntual = (total_puntuales / total_gasto > 0.5) if total_gasto > 0 else False
            
            top_gastos.append({
                'concepto': row['concepto_resumido'],
                'total': round(total_gasto, 2),
                'cantidad': int(row['cantidad'] or 0),
                'es_puntual': es_mayormente_puntual,
                'total_puntuales': round(total_puntuales, 2),
                'cantidad_puntuales': cantidad_puntuales
            })
        
        # Obtener totales del año anterior para comparación
        anio_anterior = anio - 1
        for gasto in top_gastos:
            cursor.execute(f'''
                SELECT COALESCE(SUM(ABS(importe_eur)), 0) as total_anterior
                FROM gastos
                WHERE substr(fecha_operacion, 7, 4) = ?
                AND importe_eur < 0
                AND ({case_categoria}) = ?
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
        logger.error(f"Error en top10 gastos: {str(e)}", exc_info=True)
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
        where_clause = _obtener_case_categoria_sql()
        
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
            concepto_norm = _normalizar_concepto(row['concepto_original'])
            
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
        logger.error(f"Error al obtener detalles de gasto: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@estadisticas_gastos_bp.route('/api/gastos/por-categoria-mes', methods=['GET'])
def obtener_gastos_por_categoria_mes():
    """
    Devuelve gastos del mes actual agrupados por categoría para gráfico de pastel
    EXCLUYENDO gastos puntuales (>1000€ no recurrentes)
    """
    try:
        anio = request.args.get('anio', datetime.now().year, type=int)
        mes = request.args.get('mes', datetime.now().month, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Identificar y marcar gastos puntuales
        gastos_puntuales_ids = _identificar_gastos_puntuales(conn, anio, mes)
        _marcar_gastos_puntuales(conn, gastos_puntuales_ids)
        
        # Obtener gastos del mes actual por categoría EXCLUYENDO puntuales
        case_categoria = _obtener_case_categoria_sql().replace('ELSE substr(concepto, 1, 30)', 'ELSE \'Otros\'')
        cursor.execute(f'''
            SELECT 
                {case_categoria} as categoria,
                COALESCE(SUM(ABS(importe_eur)), 0) as total,
                COALESCE(SUM(CASE WHEN puntual = 1 THEN ABS(importe_eur) ELSE 0 END), 0) as total_puntuales
            FROM gastos
            WHERE substr(fecha_operacion, 4, 2) = ?
            AND substr(fecha_operacion, 7, 4) = ?
            AND importe_eur < 0
            GROUP BY categoria
            ORDER BY total DESC
        ''', (str(mes).zfill(2), str(anio)))
        
        categorias = []
        for row in cursor.fetchall():
            total_bruto = float(row['total'] or 0)
            total_puntuales = float(row['total_puntuales'] or 0)
            total_sin_puntuales = total_bruto - total_puntuales
            
            categorias.append({
                'categoria': row['categoria'],
                'total': round(total_sin_puntuales, 2),  # Mostrar sin puntuales
                'total_bruto': round(total_bruto, 2),
                'total_puntuales': round(total_puntuales, 2)
            })
        
        conn.close()
        
        return jsonify({
            'anio': anio,
            'mes': mes,
            'categorias': categorias
        })
        
    except Exception as e:
        logger.error(f"Error al obtener gastos por categoría: {str(e)}", exc_info=True)
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
        case_categoria = _obtener_case_categoria_sql().replace('ELSE substr(concepto, 1, 30)', 'ELSE \'Otros\'')
        cursor.execute(f'''
            SELECT 
                {case_categoria} as categoria,
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
        logger.error(f"Error al obtener gastos por categoría del año: {str(e)}", exc_info=True)
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
        
        # Inicializar y marcar gastos puntuales
        _inicializar_campo_puntual(conn)
        gastos_puntuales_ids = _identificar_gastos_puntuales(conn, anio, mes)
        _marcar_gastos_puntuales(conn, gastos_puntuales_ids)
        
        # Determinar el filtro de categoría
        filtro_categoria = _obtener_filtro_categoria(categoria)
        
        # Obtener gastos sin agrupar para poder normalizarlos
        if mes:
            query = f'''
                SELECT 
                    concepto,
                    fecha_operacion,
                    ABS(importe_eur) as importe,
                    puntual
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
                    ABS(importe_eur) as importe,
                    puntual
                FROM gastos
                WHERE substr(fecha_operacion, 7, 4) = ?
                AND importe_eur < 0
                AND {filtro_categoria}
            '''
            cursor.execute(query, (str(anio),))
        
        # Agrupar manualmente por concepto normalizado
        gastos_agrupados = {}
        for row in cursor.fetchall():
            concepto_norm = _normalizar_concepto(row['concepto'])
            if concepto_norm not in gastos_agrupados:
                gastos_agrupados[concepto_norm] = {
                    'concepto': concepto_norm,
                    'fecha': row['fecha_operacion'],
                    'importe': 0.0,
                    'importe_sin_puntuales': 0.0,
                    'cantidad': 0,
                    'es_puntual': False,
                    'cantidad_puntuales': 0
                }
            gastos_agrupados[concepto_norm]['importe'] += float(row['importe'] or 0)
            gastos_agrupados[concepto_norm]['cantidad'] += 1
            
            # Sumar solo si NO es puntual (ni automático ni manual)
            if row['puntual'] not in (1, 2):
                gastos_agrupados[concepto_norm]['importe_sin_puntuales'] += float(row['importe'] or 0)
            else:
                gastos_agrupados[concepto_norm]['cantidad_puntuales'] += 1
        
        # Determinar si cada concepto es mayormente puntual y filtrar los que son 100% puntuales
        gastos_filtrados = []
        for concepto_norm, datos in gastos_agrupados.items():
            if datos['cantidad_puntuales'] > 0 and datos['cantidad_puntuales'] >= datos['cantidad'] * 0.5:
                datos['es_puntual'] = True
            
            # Excluir conceptos que son 100% puntuales (todas sus transacciones son puntuales)
            if datos['cantidad_puntuales'] < datos['cantidad']:
                gastos_filtrados.append(datos)
        
        # Convertir a lista y ordenar
        gastos = sorted(gastos_filtrados, key=lambda x: x['importe'], reverse=True)[:100]
        
        # Redondear importes
        for g in gastos:
            g['importe'] = round(g['importe'], 2)
            g['importe_sin_puntuales'] = round(g.get('importe_sin_puntuales', g['importe']), 2)
        
        # Estadísticas
        total = sum(g['importe'] for g in gastos)
        total_sin_puntuales = sum(g['importe_sin_puntuales'] for g in gastos)
        cantidad = sum(g['cantidad'] for g in gastos)
        cantidad_sin_puntuales = sum(g['cantidad'] - g.get('cantidad_puntuales', 0) for g in gastos)
        promedio = total / cantidad if cantidad > 0 else 0
        promedio_sin_puntuales = total_sin_puntuales / cantidad_sin_puntuales if cantidad_sin_puntuales > 0 else 0
        
        conn.close()
        
        return jsonify({
            'categoria': categoria,
            'anio': anio,
            'mes': mes,
            'estadisticas': {
                'total': round(total, 2),
                'total_sin_puntuales': round(total_sin_puntuales, 2),
                'cantidad': cantidad,
                'cantidad_sin_puntuales': cantidad_sin_puntuales,
                'promedio': round(promedio, 2),
                'promedio_sin_puntuales': round(promedio_sin_puntuales, 2)
            },
            'gastos': gastos
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
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Inicializar campo puntual si no existe
        _inicializar_campo_puntual(conn)
        
        # Identificar y marcar gastos puntuales para todo el año
        gastos_puntuales_ids = _identificar_gastos_puntuales(conn, anio)
        _marcar_gastos_puntuales(conn, gastos_puntuales_ids)
        
        # Determinar el filtro de categoría
        if categoria == 'global':
            # Para global, no aplicar filtro de categoría (todas las categorías)
            query = f'''
                SELECT 
                    CAST(substr(fecha_operacion, 4, 2) AS INTEGER) as mes,
                    SUM(ABS(importe_eur)) as total,
                    COUNT(*) as cantidad,
                    COALESCE(SUM(CASE WHEN puntual = 1 THEN ABS(importe_eur) ELSE 0 END), 0) as total_puntuales,
                    COALESCE(SUM(CASE WHEN puntual = 1 THEN 1 ELSE 0 END), 0) as cantidad_puntuales
                FROM gastos
                WHERE substr(fecha_operacion, 7, 4) = ?
                AND importe_eur < 0
                GROUP BY mes
                ORDER BY mes
            '''
        else:
            # Para categorías específicas, aplicar filtro
            filtro_categoria = _obtener_filtro_categoria(categoria)
            query = f'''
                SELECT 
                    CAST(substr(fecha_operacion, 4, 2) AS INTEGER) as mes,
                    SUM(ABS(importe_eur)) as total,
                    COUNT(*) as cantidad,
                    COALESCE(SUM(CASE WHEN puntual = 1 THEN ABS(importe_eur) ELSE 0 END), 0) as total_puntuales,
                    COALESCE(SUM(CASE WHEN puntual = 1 THEN 1 ELSE 0 END), 0) as cantidad_puntuales
                FROM gastos
                WHERE substr(fecha_operacion, 7, 4) = ?
                AND importe_eur < 0
                AND {filtro_categoria}
                GROUP BY mes
                ORDER BY mes
            '''
        
        cursor.execute(query, (str(anio),))
        
        # Crear array con todos los meses (0 si no hay datos)
        meses_data = {i: {'total': 0.0, 'cantidad': 0, 'total_puntuales': 0.0, 'cantidad_puntuales': 0, 'total_bruto': 0.0} for i in range(1, 13)}
        
        for row in cursor.fetchall():
            mes = int(row['mes'])
            total_bruto = float(row['total'] or 0)
            total_puntuales = float(row['total_puntuales'] or 0)
            cantidad_total = int(row['cantidad'])
            cantidad_puntuales = int(row['cantidad_puntuales'] or 0)
            
            meses_data[mes] = {
                'total': round(total_bruto - total_puntuales, 2),  # Excluir puntuales
                'cantidad': cantidad_total - cantidad_puntuales,
                'total_puntuales': round(total_puntuales, 2),
                'cantidad_puntuales': cantidad_puntuales,
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
        
        conn.close()
        
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
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # ===== DATOS DE VENTAS =====
        # Total ventas del año hasta el mes actual (FACTURAS + TICKETS)
        mes_str = str(mes).zfill(2)
        
        # Facturas del año (solo cobradas)
        cursor.execute('''
            SELECT 
                COALESCE(SUM(importe_cobrado), 0) as total_ventas,
                COUNT(*) as num_facturas
            FROM factura
            WHERE CAST(substr(fecha, 1, 4) AS INTEGER) = ?
            AND CAST(substr(fecha, 6, 2) AS INTEGER) <= ?
            AND estado = 'C'
        ''', (anio, mes))
        facturas_anio = cursor.fetchone()
        total_facturas = float(facturas_anio['total_ventas'] or 0)
        num_facturas = int(facturas_anio['num_facturas'] or 0)
        
        # Tickets del año (solo cobrados)
        cursor.execute('''
            SELECT 
                COALESCE(SUM(importe_cobrado), 0) as total_ventas,
                COUNT(*) as num_tickets
            FROM tickets
            WHERE CAST(substr(fecha, 1, 4) AS INTEGER) = ?
            AND CAST(substr(fecha, 6, 2) AS INTEGER) <= ?
            AND estado = 'C'
        ''', (anio, mes))
        tickets_anio = cursor.fetchone()
        total_tickets = float(tickets_anio['total_ventas'] or 0)
        num_tickets = int(tickets_anio['num_tickets'] or 0)
        
        # Facturas pendientes del año (para incluir en cálculos)
        cursor.execute('''
            SELECT 
                COALESCE(SUM(total), 0) as total_pendientes,
                COUNT(*) as num_pendientes
            FROM factura
            WHERE estado = 'P'
            AND CAST(substr(fecha, 1, 4) AS INTEGER) = ?
        ''', (anio,))
        facturas_pend = cursor.fetchone()
        total_fact_pendientes = float(facturas_pend['total_pendientes'] or 0)
        num_fact_pendientes = int(facturas_pend['num_pendientes'] or 0)
        
        # Total ventas (facturas cobradas + tickets + facturas pendientes)
        total_ventas = total_facturas + total_tickets + total_fact_pendientes
        num_documentos = num_facturas + num_tickets + num_fact_pendientes
        
        # Ventas del mes actual (facturas cobradas)
        cursor.execute('''
            SELECT COALESCE(SUM(importe_cobrado), 0) as total_mes
            FROM factura
            WHERE substr(fecha, 1, 4) = ?
            AND substr(fecha, 6, 2) = ?
            AND estado = 'C'
        ''', (str(anio), mes_str))
        facturas_mes = float(cursor.fetchone()['total_mes'] or 0)
        
        # Ventas del mes actual (tickets cobrados)
        cursor.execute('''
            SELECT COALESCE(SUM(importe_cobrado), 0) as total_mes
            FROM tickets
            WHERE substr(fecha, 1, 4) = ?
            AND substr(fecha, 6, 2) = ?
            AND estado = 'C'
        ''', (str(anio), mes_str))
        tickets_mes = float(cursor.fetchone()['total_mes'] or 0)
        
        # Total mes (facturas + tickets)
        ventas_mes = facturas_mes + tickets_mes
        
        # Inicializar campo puntual si no existe
        _inicializar_campo_puntual(conn)

        # Identificar y marcar gastos puntuales
        gastos_puntuales_ids = _identificar_gastos_puntuales(conn, anio, mes)
        _marcar_gastos_puntuales(conn, gastos_puntuales_ids)

        # ===== DATOS DE GASTOS =====
        # Total gastos del año hasta el mes actual - EXCLUYENDO PUNTUALES
        cursor.execute('''
            SELECT
                COALESCE(SUM(ABS(importe_eur)), 0) as total_gastos,
                COUNT(*) as num_gastos
            FROM gastos
            WHERE substr(fecha_operacion, 7, 4) = ?
            AND CAST(substr(fecha_operacion, 4, 2) AS INTEGER) <= ?
            AND importe_eur < 0
            AND (puntual IS NULL OR puntual = 0)
        ''', (str(anio), mes))
        gastos_anio = cursor.fetchone()
        total_gastos = float(gastos_anio['total_gastos'] or 0)
        num_gastos = int(gastos_anio['num_gastos'] or 0)

        # Gastos del mes actual - EXCLUYENDO PUNTUALES
        cursor.execute('''
            SELECT COALESCE(SUM(ABS(importe_eur)), 0) as total_mes
            FROM gastos
            WHERE substr(fecha_operacion, 7, 4) = ?
            AND substr(fecha_operacion, 4, 2) = ?
            AND importe_eur < 0
            AND (puntual IS NULL OR puntual = 0)
        ''', (str(anio), mes_str))
        gastos_mes = float(cursor.fetchone()['total_mes'] or 0)
        
        # ===== ANÁLISIS Y MÉTRICAS =====
        balance_anio = total_ventas - total_gastos
        balance_mes = ventas_mes - gastos_mes
        
        # Ratios financieros
        margen_beneficio_anio = (balance_anio / total_ventas * 100) if total_ventas > 0 else 0
        margen_beneficio_mes = (balance_mes / ventas_mes * 100) if ventas_mes > 0 else 0
        ratio_gastos_ventas = (total_gastos / total_ventas * 100) if total_ventas > 0 else 0
        
        # Medias mensuales
        media_ventas_mensual = total_ventas / mes if mes > 0 else 0
        media_gastos_mensual, gastos_sin_puntuales, _ = _calcular_media_mensual_sin_puntuales(conn, anio, mes)
        media_balance_mensual = balance_anio / mes if mes > 0 else 0
        
        # Proyecciones para fin de año
        meses_restantes = 12 - mes
        proyeccion_ventas = total_ventas + (media_ventas_mensual * meses_restantes)
        proyeccion_gastos = total_gastos + (media_gastos_mensual * meses_restantes)
        proyeccion_balance = proyeccion_ventas - proyeccion_gastos
        
        # Top 5 categorías de gastos
        case_categoria = _obtener_case_categoria_sql().replace('ELSE substr(concepto, 1, 30)', 'ELSE \'Otros\'')
        cursor.execute(f'''
            SELECT 
                {case_categoria} as categoria,
                COALESCE(SUM(ABS(importe_eur)), 0) as total,
                COUNT(*) as cantidad
            FROM gastos
            WHERE substr(fecha_operacion, 7, 4) = ?
            AND CAST(substr(fecha_operacion, 4, 2) AS INTEGER) <= ?
            AND importe_eur < 0
            GROUP BY categoria
            ORDER BY total DESC
            LIMIT 5
        ''', (str(anio), mes))
        
        top_categorias_gastos = []
        for row in cursor.fetchall():
            top_categorias_gastos.append({
                'categoria': row['categoria'],
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
        
        conn.close()
        
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
        
        # Inicializar campo puntual si no existe
        _inicializar_campo_puntual(conn)

        # Identificar y marcar gastos puntuales
        gastos_puntuales_ids = _identificar_gastos_puntuales(conn, anio, mes)
        _marcar_gastos_puntuales(conn, gastos_puntuales_ids)

        # Obtener datos reales actuales - EXCLUYENDO GASTOS PUNTUALES
        # Facturas cobradas
        cursor.execute('''
            SELECT COALESCE(SUM(importe_cobrado), 0) as total
            FROM factura
            WHERE CAST(substr(fecha, 1, 4) AS INTEGER) = ?
            AND CAST(substr(fecha, 6, 2) AS INTEGER) <= ?
            AND estado = 'C'
        ''', (anio, mes))
        ventas_facturas = float(cursor.fetchone()['total'] or 0)

        # Tickets cobrados
        cursor.execute('''
            SELECT COALESCE(SUM(importe_cobrado), 0) as total
            FROM tickets
            WHERE CAST(substr(fecha, 1, 4) AS INTEGER) = ?
            AND CAST(substr(fecha, 6, 2) AS INTEGER) <= ?
            AND estado = 'C'
        ''', (anio, mes))
        ventas_tickets = float(cursor.fetchone()['total'] or 0)

        # Gastos - EXCLUYENDO PUNTUALES
        cursor.execute('''
            SELECT COALESCE(SUM(ABS(importe_eur)), 0) as total
            FROM gastos
            WHERE substr(fecha_operacion, 7, 4) = ?
            AND CAST(substr(fecha_operacion, 4, 2) AS INTEGER) <= ?
            AND importe_eur < 0
            AND (puntual IS NULL OR puntual = 0)
        ''', (str(anio), mes))
        gastos_totales = float(cursor.fetchone()['total'] or 0)
        
        # Datos reales
        ventas_reales = ventas_facturas + ventas_tickets
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

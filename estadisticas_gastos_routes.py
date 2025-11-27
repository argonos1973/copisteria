from flask import Blueprint, jsonify, request
from datetime import datetime
import sqlite3
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

        if 'razon_social' not in columnas_nombres:
            logger.info("Agregando campo 'razon_social' a tabla gastos")
            cursor.execute("ALTER TABLE gastos ADD COLUMN razon_social TEXT")

        conn.commit()
        logger.debug("Campos 'puntual' y 'razon_social' verificados/inicializados")
    except Exception as e:
        logger.error(f"Error al inicializar campos gastos: {e}", exc_info=True)
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
            SELECT id, concepto, ABS(importe_eur) as importe, fecha_valor
            FROM gastos
            WHERE substr(fecha_valor, 7, 4) = ?
            AND CAST(substr(fecha_valor, 4, 2) AS INTEGER) <= ?
            AND importe_eur < 0
        ''', (str(anio), mes))
    else:
        cursor.execute('''
            SELECT id, concepto, ABS(importe_eur) as importe, fecha_valor
            FROM gastos
            WHERE substr(fecha_valor, 7, 4) = ?
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
        fecha = gasto['fecha_valor']
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
            WHERE substr(fecha_valor, 7, 4) = ?
            AND CAST(substr(fecha_valor, 4, 2) AS INTEGER) <= ?
            AND importe_eur < 0
            AND (puntual IS NULL OR puntual = 0)
        ''', (str(anio), mes))
    else:
        cursor.execute('''
            SELECT
                COALESCE(SUM(ABS(importe_eur)), 0) as total_sin_puntuales,
                COUNT(*) as cantidad_sin_puntuales
            FROM gastos
            WHERE substr(fecha_valor, 7, 4) = ?
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
            WHEN (concepto LIKE '%Tarjeta%' OR concepto LIKE '%Tarj.%' OR concepto LIKE '%Compra%' OR concepto LIKE 'Pago Movil%' OR concepto LIKE 'Pago Con Tarjeta%') AND concepto NOT LIKE 'Liquidacion%' THEN 'Compras Tarjeta'
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
        'Compras Tarjeta': "((concepto LIKE '%Tarjeta%' OR concepto LIKE '%Tarj.%' OR concepto LIKE '%Compra%' OR concepto LIKE 'Pago Movil%' OR concepto LIKE 'Pago Con Tarjeta%') AND concepto NOT LIKE 'Liquidacion%')",
        'Otros': """(concepto NOT LIKE 'Recibo%' 
                    AND concepto NOT LIKE 'Liquidacion%' 
                    AND concepto NOT LIKE '%Transferencia%' 
                    AND concepto NOT LIKE '%Bizum%' 
                    AND concepto NOT LIKE '%Tarjeta%' 
                    AND concepto NOT LIKE '%Tarj.%'
                    AND concepto NOT LIKE '%Compra%'
                    AND concepto NOT LIKE 'Pago Movil%'
                    AND concepto NOT LIKE 'Pago Con Tarjeta%')"""
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
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Inicializar campo puntual si no existe
            _inicializar_campo_puntual(conn)
    
            # Identificar y marcar gastos puntuales
            gastos_puntuales_ids = _identificar_gastos_puntuales(conn, anio, mes)
            _marcar_gastos_puntuales(conn, gastos_puntuales_ids)
    
            # Gastos totales del año actual HASTA el mes seleccionado (inclusive) - TOTAL REAL (INCLUYE PUNTUALES)
            mes_str = str(mes).zfill(2)
            cursor.execute('''
                SELECT
                    COALESCE(SUM(ABS(importe_eur)), 0) as total_gastos_anio,
                    COUNT(*) as cantidad_gastos_anio
                FROM gastos
                WHERE substr(fecha_valor, 7, 4) = ?
                AND CAST(substr(fecha_valor, 4, 2) AS INTEGER) <= ?
                AND importe_eur < 0
            ''', (str(anio), mes))
    
            datos_anio = cursor.fetchone()
            total_gastos_anio = float(datos_anio['total_gastos_anio'] or 0)
            cantidad_gastos_anio = int(datos_anio['cantidad_gastos_anio'] or 0)
    
            # Gastos del mes actual - TOTAL REAL (INCLUYE PUNTUALES)
            cursor.execute('''
                SELECT
                    COALESCE(SUM(ABS(importe_eur)), 0) as total_gastos_mes,
                    COUNT(*) as cantidad_gastos_mes
                FROM gastos
                WHERE substr(fecha_valor, 7, 4) = ?
                AND substr(fecha_valor, 4, 2) = ?
                AND importe_eur < 0
            ''', (str(anio), mes_str))
    
            datos_mes = cursor.fetchone()
            total_gastos_mes = float(datos_mes['total_gastos_mes'] or 0)
            cantidad_gastos_mes = int(datos_mes['cantidad_gastos_mes'] or 0)
    
            # Gastos del año anterior HASTA el mismo mes (para comparación justa) - TOTAL REAL
            anio_anterior = anio - 1
            cursor.execute('''
                SELECT COALESCE(SUM(ABS(importe_eur)), 0) as total_gastos_anio_anterior
                FROM gastos
                WHERE substr(fecha_valor, 7, 4) = ?
                AND CAST(substr(fecha_valor, 4, 2) AS INTEGER) <= ?
                AND importe_eur < 0
            ''', (str(anio_anterior), mes))
    
            total_gastos_anio_anterior = float(cursor.fetchone()['total_gastos_anio_anterior'] or 0)
    
            # Gastos del mismo mes del año anterior - TOTAL REAL
            cursor.execute('''
                SELECT COALESCE(SUM(ABS(importe_eur)), 0) as total_gastos_mes_anterior
                FROM gastos
                WHERE substr(fecha_valor, 7, 4) = ?
                AND substr(fecha_valor, 4, 2) = ?
                AND importe_eur < 0
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
    Agrupados por CONCEPTO NORMALIZADO (usando _normalizar_concepto en Python)
    """
    try:
        anio = request.args.get('anio', datetime.now().year, type=int)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            conn.row_factory = sqlite3.Row
            
            # Inicializar y marcar gastos puntuales
            _inicializar_campo_puntual(conn)
            gastos_puntuales_ids = _identificar_gastos_puntuales(conn, anio)
            _marcar_gastos_puntuales(conn, gastos_puntuales_ids)
            
            # 1. Obtener TODOS los gastos del año actual
            # Incluir columna razon_social en la consulta (si existe en la tabla, SQLite no da error si seleccionamos NULL as razon_social si no existiera, 
            # pero ya hemos garantizado que existe con _inicializar_campo_puntual)
            
            # Verificar si razon_social existe antes de hacer la query (por seguridad)
            cursor.execute("PRAGMA table_info(gastos)")
            cols = [c['name'] for c in cursor.fetchall()]
            
            col_razon = "razon_social" if "razon_social" in cols else "NULL as razon_social"

            cursor.execute(f'''
                SELECT concepto, ABS(importe_eur) as importe, puntual, {col_razon}
                FROM gastos
                WHERE substr(fecha_valor, 7, 4) = ?
                AND importe_eur < 0
            ''', (str(anio),))
            
            gastos_anio = cursor.fetchall()
            
            # 2. Agrupar por concepto normalizado en Python
            agrupados = {}
            
            for gasto in gastos_anio:
                concepto_raw = gasto['concepto']
                importe = float(gasto['importe'] or 0)
                es_puntual = int(gasto['puntual'] or 0) == 1
                razon_social = gasto['razon_social']
                
                # Si tenemos razon_social (proveedor identificado), la usamos.
                # Si no, normalizamos el concepto del banco.
                if razon_social and razon_social.strip():
                    concepto_norm = razon_social.strip()
                else:
                    concepto_norm = _normalizar_concepto(concepto_raw)
                
                if concepto_norm not in agrupados:
                    agrupados[concepto_norm] = {
                        'total': 0.0,
                        'cantidad': 0,
                        'cantidad_puntuales': 0,
                        'total_puntuales': 0.0
                    }
                
                agrupados[concepto_norm]['total'] += importe
                agrupados[concepto_norm]['cantidad'] += 1
                if es_puntual:
                    agrupados[concepto_norm]['cantidad_puntuales'] += 1
                    agrupados[concepto_norm]['total_puntuales'] += importe
            
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
            cursor.execute('''
                SELECT concepto, ABS(importe_eur) as importe
                FROM gastos
                WHERE substr(fecha_valor, 7, 4) = ?
                AND importe_eur < 0
            ''', (str(anio_anterior),))
            
            gastos_anterior = cursor.fetchall()
            
            # Agrupar año anterior
            agrupados_anterior = {}
            for gasto in gastos_anterior:
                concepto_norm = _normalizar_concepto(gasto['concepto'])
                importe = float(gasto['importe'] or 0)
                agrupados_anterior[concepto_norm] = agrupados_anterior.get(concepto_norm, 0.0) + importe
                
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
    Devuelve los detalles de todos los gastos de un concepto específico (normalizado o razon social)
    """
    try:
        concepto_buscado = request.args.get('concepto', '')
        anio = request.args.get('anio', datetime.now().year, type=int)
        
        if not concepto_buscado:
            return jsonify({'error': 'Se requiere el parámetro concepto'}), 400
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            conn.row_factory = sqlite3.Row
            
            # Verificar si razon_social existe
            cursor.execute("PRAGMA table_info(gastos)")
            cols = [c['name'] for c in cursor.fetchall()]
            col_razon = "razon_social" if "razon_social" in cols else "NULL as razon_social"
            
            # Obtener TODOS los gastos del año para filtrar en memoria (igual que en top10)
            cursor.execute(f'''
                SELECT 
                    concepto as concepto_original,
                    ABS(importe_eur) as importe,
                    fecha_valor,
                    {col_razon}
                FROM gastos
                WHERE substr(fecha_valor, 7, 4) = ?
                AND importe_eur < 0
                ORDER BY fecha_valor DESC
            ''', (str(anio),))
            
            gastos_filtrados = []
            importes = []
            
            for row in cursor.fetchall():
                concepto_raw = row['concepto_original']
                importe = float(row['importe'] or 0)
                fecha = row['fecha_valor']
                razon_social = row['razon_social']
                
                # Lógica de normalización idéntica a top10
                if razon_social and razon_social.strip():
                    concepto_norm = razon_social.strip()
                else:
                    concepto_norm = _normalizar_concepto(concepto_raw)
                
                # Si coincide con el concepto buscado
                if concepto_norm == concepto_buscado:
                    gastos_filtrados.append({
                        'concepto': concepto_norm, # Concepto agrupado
                        'concepto_real': concepto_raw, # Concepto original del banco
                        'fecha': fecha,
                        'importe': round(importe, 2),
                        'es_razon_social': bool(razon_social and razon_social.strip())
                    })
                    importes.append(importe)
            
            if not gastos_filtrados:
                 return jsonify({
                    'concepto': concepto_buscado,
                    'anio': anio,
                    'estadisticas': {
                        'cantidad': 0, 'total': 0, 'promedio': 0, 'minimo': 0, 'maximo': 0
                    },
                    'gastos_agrupados': [] # Para compatibilidad con frontend, mandamos lista vacía o adaptada
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
            
            # Agrupar para la vista de "gastos_agrupados" que espera el frontend
            # El usuario ha pedido VER EL DETALLE COMPLETO (sin agrupar por concepto original)
            # Así que devolvemos cada transacción individualmente
            
            gastos_view = []
            for g in gastos_filtrados:
                gastos_view.append({
                    'concepto': g['concepto_real'], # Concepto original del banco/factura
                    'cantidad': 1,
                    'total': g['importe'],
                    'promedio': g['importe'],
                    'primera_fecha': g['fecha'],
                    'ultima_fecha': g['fecha'], # Al ser individual, inicio y fin es la misma fecha
                    'conceptos_originales': [g['concepto_real']]
                })
                
            # Ordenar por fecha descendente (lo más reciente primero) para ver el detalle cronológico
            gastos_view.sort(key=lambda x: x['primera_fecha'], reverse=True)

        return jsonify({
            'concepto': concepto_buscado,
            'anio': anio,
            'estadisticas': estadisticas,
            'gastos_agrupados': gastos_view
        })
        
    except Exception as e:
        logger.error(f"Error al obtener detalles de gasto: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@estadisticas_gastos_bp.route('/api/gastos/por-categoria-mes', methods=['GET'])
def obtener_gastos_por_categoria_mes():
    """
    Devuelve gastos del mes actual agrupados por CONCEPTO NORMALIZADO para gráfico de pastel
    EXCLUYENDO gastos puntuales (>1000€ no recurrentes)
    """
    try:
        anio = request.args.get('anio', datetime.now().year, type=int)
        mes = request.args.get('mes', datetime.now().month, type=int)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            conn.row_factory = sqlite3.Row
            
            # Identificar y marcar gastos puntuales
            _inicializar_campo_puntual(conn)
            gastos_puntuales_ids = _identificar_gastos_puntuales(conn, anio, mes)
            _marcar_gastos_puntuales(conn, gastos_puntuales_ids)
            
            # Verificar columna razon_social
            cursor.execute("PRAGMA table_info(gastos)")
            cols = [c['name'] for c in cursor.fetchall()]
            col_razon = "razon_social" if "razon_social" in cols else "NULL as razon_social"

            # Obtener TODOS los gastos del mes
            cursor.execute(f'''
                SELECT 
                    concepto, ABS(importe_eur) as importe, puntual, {col_razon}
                FROM gastos
                WHERE substr(fecha_valor, 4, 2) = ?
                AND substr(fecha_valor, 7, 4) = ?
                AND importe_eur < 0
            ''', (str(mes).zfill(2), str(anio)))
            
            agrupados = {}
            total_general = 0.0
            
            for row in cursor.fetchall():
                importe = float(row['importe'] or 0)
                es_puntual = int(row['puntual'] or 0) == 1
                
                # Excluir puntuales automáticos del gráfico mensual (según lógica anterior)
                # if es_puntual:
                #    continue

                razon_social = row['razon_social']
                concepto_raw = row['concepto']

                if razon_social and razon_social.strip():
                    concepto_norm = razon_social.strip()
                else:
                    concepto_norm = _normalizar_concepto(concepto_raw)
                
                if concepto_norm not in agrupados:
                    agrupados[concepto_norm] = 0.0
                
                agrupados[concepto_norm] += importe
                total_general += importe
            
            # Convertir a lista
            lista_categorias = [{'categoria': k, 'total': v} for k, v in agrupados.items()]
            
            # Ordenar por total descendente
            lista_categorias.sort(key=lambda x: x['total'], reverse=True)
            
            # Agrupar en "Otros" si hay muchos (Top 9 + Otros)
            if len(lista_categorias) > 9:
                top_9 = lista_categorias[:9]
                otros = lista_categorias[9:]
                total_otros = sum(c['total'] for c in otros)
                
                final_categorias = top_9
                if total_otros > 0:
                    final_categorias.append({'categoria': 'Otros', 'total': round(total_otros, 2)})
            else:
                final_categorias = lista_categorias
            
            # Formatear salida
            resultado = []
            for c in final_categorias:
                resultado.append({
                    'categoria': c['categoria'],
                    'total': round(c['total'], 2),
                    'total_bruto': round(c['total'], 2), # Compatibilidad
                    'total_puntuales': 0 # Ya excluidos
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
    Devuelve gastos del año completo agrupados por CONCEPTO NORMALIZADO para gráfico de pastel
    """
    try:
        anio = request.args.get('anio', datetime.now().year, type=int)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            conn.row_factory = sqlite3.Row
            
            # Verificar columna razon_social
            _inicializar_campo_puntual(conn) # Asegurar columnas
            
            cursor.execute("PRAGMA table_info(gastos)")
            cols = [c['name'] for c in cursor.fetchall()]
            col_razon = "razon_social" if "razon_social" in cols else "NULL as razon_social"

            # Obtener gastos del año completo
            cursor.execute(f'''
                SELECT 
                    concepto, ABS(importe_eur) as importe, {col_razon}
                FROM gastos
                WHERE substr(fecha_valor, 7, 4) = ?
                AND importe_eur < 0
            ''', (str(anio),))
            
            agrupados = {}
            
            for row in cursor.fetchall():
                importe = float(row['importe'] or 0)
                razon_social = row['razon_social']
                concepto_raw = row['concepto']

                if razon_social and razon_social.strip():
                    concepto_norm = razon_social.strip()
                else:
                    concepto_norm = _normalizar_concepto(concepto_raw)
                
                if concepto_norm not in agrupados:
                    agrupados[concepto_norm] = 0.0
                
                agrupados[concepto_norm] += importe
            
            # Convertir a lista
            lista_categorias = [{'categoria': k, 'total': v} for k, v in agrupados.items()]
            
            # Ordenar por total descendente
            lista_categorias.sort(key=lambda x: x['total'], reverse=True)
            
            # Agrupar en "Otros" (Top 9 + Otros)
            if len(lista_categorias) > 9:
                top_9 = lista_categorias[:9]
                otros = lista_categorias[9:]
                total_otros = sum(c['total'] for c in otros)
                
                final_categorias = top_9
                if total_otros > 0:
                    final_categorias.append({'categoria': 'Otros', 'total': round(total_otros, 2)})
            else:
                final_categorias = lista_categorias

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

@estadisticas_gastos_bp.route('/api/gastos/detalles-categoria', methods=['GET'])
def obtener_detalles_categoria():
    """
    Devuelve los detalles de gastos de una categoría específica para un mes/año
    Adaptado para soportar la nueva agrupación dinámica (Top 9 + Otros)
    """
    try:
        categoria = request.args.get('categoria', type=str)
        anio = request.args.get('anio', datetime.now().year, type=int)
        mes = request.args.get('mes', type=int)  # Opcional
        
        if not categoria:
            return jsonify({'error': 'Categoría requerida'}), 400
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            conn.row_factory = sqlite3.Row
            
            # Inicializar y marcar gastos puntuales
            _inicializar_campo_puntual(conn)
            gastos_puntuales_ids = _identificar_gastos_puntuales(conn, anio, mes)
            _marcar_gastos_puntuales(conn, gastos_puntuales_ids)
            
            # Verificar columna razon_social
            cursor.execute("PRAGMA table_info(gastos)")
            cols = [c['name'] for c in cursor.fetchall()]
            col_razon = "razon_social" if "razon_social" in cols else "NULL as razon_social"
            
            # 1. Obtener TODOS los gastos (del año o del mes según corresponda)
            query = f'''
                SELECT 
                    id, fecha_valor, concepto, ABS(importe_eur) as importe, puntual, {col_razon}
                FROM gastos
                WHERE substr(fecha_valor, 7, 4) = ?
                AND importe_eur < 0
            '''
            params = [str(anio)]
            
            if mes:
                query += ' AND substr(fecha_valor, 4, 2) = ?'
                params.append(str(mes).zfill(2))
                
            query += ' ORDER BY fecha_valor DESC'
            
            cursor.execute(query, params)
            todos_los_gastos = cursor.fetchall()
            
            # 2. Procesar y Agrupar para identificar el TOP 9
            agrupados_totales = {}
            gastos_procesados = []
            
            logger.info(f"Detalles Categoria debug: Buscando '{categoria}' en año {anio}")
            
            for row in todos_los_gastos:
                importe = float(row['importe'] or 0)
                razon_social = row['razon_social']
                concepto_raw = row['concepto']
                fecha = row['fecha_valor']
                
                if razon_social and razon_social.strip():
                    concepto_norm = razon_social.strip()
                else:
                    concepto_norm = _normalizar_concepto(concepto_raw)
                
                if concepto_norm not in agrupados_totales:
                    agrupados_totales[concepto_norm] = 0.0
                agrupados_totales[concepto_norm] += importe
                
                gastos_procesados.append({
                    'concepto_norm': concepto_norm,
                    'concepto_real': concepto_raw,
                    'fecha': fecha,
                    'importe': importe
                })
            
            # Identificar Top 9 Conceptos
            lista_conceptos = [{'concepto': k, 'total': v} for k, v in agrupados_totales.items()]
            lista_conceptos.sort(key=lambda x: x['total'], reverse=True)
            top_9_conceptos = set(c['concepto'] for c in lista_conceptos[:9])
            
            # 3. Filtrar según la categoría solicitada
            gastos_filtrados = []
            
            if categoria == 'Otros':
                # Devolver todo lo que NO esté en el Top 9
                gastos_filtrados = [g for g in gastos_procesados if g['concepto_norm'] not in top_9_conceptos]
                logger.info(f"Categoria Otros: {len(gastos_filtrados)} gastos encontrados")
            else:
                # Devolver exactamente lo que coincida con la categoría (concepto)
                gastos_filtrados = [g for g in gastos_procesados if g['concepto_norm'] == categoria]
                logger.info(f"Categoria '{categoria}': {len(gastos_filtrados)} gastos encontrados")
                if len(gastos_filtrados) == 0:
                     # Debug si no encuentra nada
                     ejemplos = [g['concepto_norm'] for g in gastos_procesados[:5]]
                     logger.info(f"Ejemplos de conceptos normalizados en BD: {ejemplos}")
                     # Buscar si existe algo parecido
                     parecidos = [g['concepto_norm'] for g in gastos_procesados if categoria.lower() in g['concepto_norm'].lower()]
                     if parecidos:
                         logger.info(f"Posibles coincidencias parciales: {list(set(parecidos))[:5]}")
                
            # 4. Formatear respuesta para el frontend (formato lista de transacciones)
            gastos_view = []
            for g in gastos_filtrados:
                gastos_view.append({
                    'concepto': g['concepto_real'], # Mostrar concepto original
                    'cantidad': 1,
                    'importe': round(g['importe'], 2), # Frontend espera 'importe'
                    'total': round(g['importe'], 2),   # Mantener 'total' por compatibilidad
                    'promedio': round(g['importe'], 2),
                    'fecha': g['fecha'],               # Frontend espera 'fecha'
                    'primera_fecha': g['fecha'],
                    'ultima_fecha': g['fecha'],
                    'conceptos_originales': [g['concepto_real']],
                    'es_puntual': False
                })
            
            # Ordenar cronológicamente descendente
            gastos_view.sort(key=lambda x: x['fecha'], reverse=True)

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
                        CAST(substr(fecha_valor, 4, 2) AS INTEGER) as mes,
                        SUM(ABS(importe_eur)) as total,
                        COUNT(*) as cantidad,
                        COALESCE(SUM(CASE WHEN puntual = 1 THEN ABS(importe_eur) ELSE 0 END), 0) as total_puntuales,
                        COALESCE(SUM(CASE WHEN puntual = 1 THEN 1 ELSE 0 END), 0) as cantidad_puntuales
                    FROM gastos
                    WHERE substr(fecha_valor, 7, 4) = ?
                    AND importe_eur < 0
                    GROUP BY mes
                    ORDER BY mes
                '''
            else:
                # Para categorías específicas, aplicar filtro
                filtro_categoria = _obtener_filtro_categoria(categoria)
                query = f'''
                    SELECT 
                        CAST(substr(fecha_valor, 4, 2) AS INTEGER) as mes,
                        SUM(ABS(importe_eur)) as total,
                        COUNT(*) as cantidad,
                        COALESCE(SUM(CASE WHEN puntual = 1 THEN ABS(importe_eur) ELSE 0 END), 0) as total_puntuales,
                        COALESCE(SUM(CASE WHEN puntual = 1 THEN 1 ELSE 0 END), 0) as cantidad_puntuales
                    FROM gastos
                    WHERE substr(fecha_valor, 7, 4) = ?
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
        
        with get_db_connection() as conn:
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
            
            # Facturas vencidas del año (para incluir en cálculos)
            cursor.execute('''
                SELECT 
                    COALESCE(SUM(total), 0) as total_vencidas,
                    COUNT(*) as num_vencidas
                FROM factura
                WHERE estado = 'V'
                AND CAST(substr(fecha, 1, 4) AS INTEGER) = ?
            ''', (anio,))
            facturas_venc = cursor.fetchone()
            total_fact_vencidas = float(facturas_venc['total_vencidas'] or 0)
            num_fact_vencidas = int(facturas_venc['num_vencidas'] or 0)
            
            # Total ventas (facturas cobradas + tickets + facturas pendientes + facturas vencidas)
            total_ventas = total_facturas + total_tickets + total_fact_pendientes + total_fact_vencidas
            num_documentos = num_facturas + num_tickets + num_fact_pendientes + num_fact_vencidas
            
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
                WHERE substr(fecha_valor, 7, 4) = ?
                AND CAST(substr(fecha_valor, 4, 2) AS INTEGER) <= ?
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
                WHERE substr(fecha_valor, 7, 4) = ?
                AND substr(fecha_valor, 4, 2) = ?
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
                WHERE substr(fecha_valor, 7, 4) = ?
                AND CAST(substr(fecha_valor, 4, 2) AS INTEGER) <= ?
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
            WHERE substr(fecha_valor, 7, 4) = ?
            AND CAST(substr(fecha_valor, 4, 2) AS INTEGER) <= ?
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

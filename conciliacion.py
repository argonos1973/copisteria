# conciliacion.py
# Sistema de conciliación automática entre gastos bancarios y facturas/tickets
import sqlite3
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from constantes import DB_NAME

conciliacion_bp = Blueprint('conciliacion', __name__)

def get_db_connection():
    """Obtener conexión a la base de datos"""
    conn = sqlite3.connect(DB_NAME, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def crear_tabla_conciliacion():
    """Crear tabla para almacenar conciliaciones si no existe"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conciliacion_gastos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gasto_id INTEGER NOT NULL,
            tipo_documento TEXT NOT NULL, -- 'factura', 'ticket', 'proforma'
            documento_id INTEGER NOT NULL,
            fecha_conciliacion TEXT NOT NULL,
            importe_gasto REAL NOT NULL,
            importe_documento REAL NOT NULL,
            diferencia REAL,
            estado TEXT DEFAULT 'conciliado', -- 'conciliado', 'pendiente', 'rechazado'
            metodo TEXT, -- 'automatico', 'manual'
            notas TEXT,
            notificado INTEGER DEFAULT 0, -- 0: no notificado, 1: notificado
            FOREIGN KEY(gasto_id) REFERENCES gastos(id),
            UNIQUE(gasto_id, tipo_documento, documento_id)
        )
    ''')
    
    # Índices para mejorar rendimiento
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_conciliacion_gasto ON conciliacion_gastos(gasto_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_conciliacion_documento ON conciliacion_gastos(tipo_documento, documento_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_conciliacion_estado ON conciliacion_gastos(estado)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_conciliacion_notificado ON conciliacion_gastos(notificado)')
    
    conn.commit()
    conn.close()

def buscar_coincidencias_automaticas(gasto):
    """
    Buscar coincidencias automáticas para un gasto bancario
    Criterios:
    1. Importe exacto o muy cercano (±0.02€)
    2. Fecha cercana (±15 días) - EXCEPTO si hay número de factura/ticket en concepto
    """
    import re
    conn = get_db_connection()
    cursor = conn.cursor()
    
    gasto_id = gasto['id']
    importe = abs(gasto['importe_eur'])
    concepto = (gasto.get('concepto') or '').upper()
    
    # Detectar si hay un número de factura o ticket en el concepto
    # Patrones: F250046, T255678, etc.
    patron_numero = re.search(r'[FT](\d{6})', concepto)
    tiene_numero_documento = bool(patron_numero)
    
    tolerancia = 0.02
    coincidencias = []
    
    if tiene_numero_documento:
        # Si hay número de documento, buscar SOLO por número e importe (sin filtro de fecha)
        numero_buscado = patron_numero.group(0)  # F250046 o T255678
        tipo_doc = 'factura' if numero_buscado.startswith('F') else 'ticket'
        
        if tipo_doc == 'factura':
            cursor.execute('''
                SELECT 
                    'factura' as tipo,
                    id,
                    numero,
                    fecha,
                    total,
                    estado,
                    importe_cobrado
                FROM factura
                WHERE estado = 'C'
                AND numero = ?
                AND ABS(total - ?) <= ?
                AND id NOT IN (
                    SELECT documento_id FROM conciliacion_gastos 
                    WHERE tipo_documento = 'factura' AND estado = 'conciliado'
                )
            ''', (numero_buscado, importe, tolerancia))
        else:
            cursor.execute('''
                SELECT 
                    'ticket' as tipo,
                    id,
                    numero,
                    fecha,
                    total,
                    estado,
                    importe_cobrado
                FROM tickets
                WHERE estado = 'C'
                AND numero = ?
                AND ABS(total - ?) <= ?
                AND id NOT IN (
                    SELECT documento_id FROM conciliacion_gastos 
                    WHERE tipo_documento = 'ticket' AND estado = 'conciliado'
                )
            ''', (numero_buscado, importe, tolerancia))
        
        for row in cursor.fetchall():
            coincidencias.append({
                'tipo': row['tipo'],
                'id': row['id'],
                'numero': row['numero'],
                'fecha': row['fecha'],
                'importe': row['total'],
                'estado': row['estado'],
                'diferencia': abs(row['total'] - importe),
                'score': calcular_score(gasto, dict(row))
            })
    else:
        # Si NO hay número, buscar por fecha e importe (lógica original)
        # Manejar múltiples formatos de fecha
        fecha_gasto_str = gasto['fecha_operacion']
        try:
            if '/' in fecha_gasto_str:
                fecha_gasto = datetime.strptime(fecha_gasto_str, '%d/%m/%Y')
            else:
                fecha_gasto = datetime.strptime(fecha_gasto_str, '%Y-%m-%d')
        except:
            fecha_gasto = datetime.strptime(fecha_gasto_str, '%Y-%m-%d')
        
        fecha_inicio = (fecha_gasto - timedelta(days=15)).strftime('%Y-%m-%d')
        fecha_fin = (fecha_gasto + timedelta(days=15)).strftime('%Y-%m-%d')
        
        # Buscar en facturas cobradas
        cursor.execute('''
            SELECT 
                'factura' as tipo,
                id,
                numero,
                fecha,
                total,
                estado,
                importe_cobrado
            FROM factura
            WHERE estado = 'C'
            AND fecha BETWEEN ? AND ?
            AND ABS(total - ?) <= ?
            AND id NOT IN (
                SELECT documento_id FROM conciliacion_gastos 
                WHERE tipo_documento = 'factura' AND estado = 'conciliado'
            )
        ''', (fecha_inicio, fecha_fin, importe, tolerancia))
        
        for row in cursor.fetchall():
            coincidencias.append({
                'tipo': 'factura',
                'id': row['id'],
                'numero': row['numero'],
                'fecha': row['fecha'],
                'importe': row['total'],
                'diferencia': abs(row['total'] - importe),
                'score': calcular_score(gasto, dict(row))
            })
        
        # Buscar en tickets cobrados
        cursor.execute('''
            SELECT 
                'ticket' as tipo,
                id,
                numero,
                fecha,
                total,
                estado,
                importe_cobrado
            FROM tickets
            WHERE estado = 'C'
            AND fecha BETWEEN ? AND ?
            AND ABS(total - ?) <= ?
            AND id NOT IN (
                SELECT documento_id FROM conciliacion_gastos 
                WHERE tipo_documento = 'ticket' AND estado = 'conciliado'
            )
        ''', (fecha_inicio, fecha_fin, importe, tolerancia))
        
        for row in cursor.fetchall():
            coincidencias.append({
                'tipo': 'ticket',
                'id': row['id'],
                'numero': row['numero'],
                'fecha': row['fecha'],
                'importe': row['total'],
                'diferencia': abs(row['total'] - importe),
                'score': calcular_score(gasto, dict(row))
            })
    
    conn.close()
    
    # Ordenar por score (mayor score = mejor coincidencia)
    coincidencias.sort(key=lambda x: x['score'], reverse=True)
    
    return coincidencias

def calcular_score(gasto, documento):
    """
    Calcular score de coincidencia (0-120, luego normalizado a 100)
    Factores:
    - Diferencia de importe (40 puntos)
    - Diferencia de fecha (30 puntos)
    - Exactitud del importe (20 puntos)
    - Coincidencia en concepto (30 puntos)
    
    CASO ESPECIAL: Si número de documento aparece en concepto + importe exacto = 100%
    """
    import re
    
    score = 0
    
    # Score por diferencia de importe (40 puntos)
    diferencia_importe = abs(abs(gasto['importe_eur']) - documento['total'])
    if diferencia_importe == 0:
        score += 40
    elif diferencia_importe <= 0.01:
        score += 35
    elif diferencia_importe <= 0.02:
        score += 30
    else:
        score += max(0, 40 - (diferencia_importe * 100))
    
    # Score por diferencia de fecha (30 puntos)
    # Manejar múltiples formatos de fecha
    fecha_gasto_str = gasto['fecha_operacion']
    try:
        if '/' in fecha_gasto_str:
            fecha_gasto = datetime.strptime(fecha_gasto_str, '%d/%m/%Y')
        else:
            fecha_gasto = datetime.strptime(fecha_gasto_str, '%Y-%m-%d')
    except:
        # Si falla, asumir formato ISO
        fecha_gasto = datetime.strptime(fecha_gasto_str, '%Y-%m-%d')
    
    fecha_doc = datetime.strptime(documento['fecha'], '%Y-%m-%d')
    diferencia_dias = abs((fecha_gasto - fecha_doc).days)
    
    if diferencia_dias == 0:
        score += 30
    elif diferencia_dias <= 1:
        score += 25
    elif diferencia_dias <= 3:
        score += 20
    elif diferencia_dias <= 7:
        score += 15
    elif diferencia_dias <= 15:
        score += 10
    
    # Score por exactitud del importe (20 puntos)
    if diferencia_importe == 0:
        score += 20
    elif diferencia_importe <= 0.01:
        score += 15
    
    # Score por coincidencia en concepto (30 puntos)
    concepto_gasto = (gasto.get('concepto') or '').upper()
    numero_documento = (documento.get('numero') or '').upper()
    puntos_concepto = 0
    coincidencia_numero = False
    
    if numero_documento and concepto_gasto:
        # Extraer solo los dígitos del número de documento
        digitos_doc = re.sub(r'[^0-9]', '', numero_documento)
        
        # Si el número completo aparece en el concepto
        if numero_documento in concepto_gasto:
            puntos_concepto = 30  # Coincidencia exacta
            coincidencia_numero = True
        # Si los dígitos del número aparecen en el concepto
        elif digitos_doc and len(digitos_doc) >= 4 and digitos_doc in concepto_gasto:
            puntos_concepto = 25  # Coincidencia de dígitos
            coincidencia_numero = True
        # Si aparece parte del número (últimos 4 dígitos)
        elif digitos_doc and len(digitos_doc) >= 4:
            ultimos_4 = digitos_doc[-4:]
            if ultimos_4 in concepto_gasto:
                puntos_concepto = 20  # Coincidencia parcial
                coincidencia_numero = True
    
    score += puntos_concepto
    
    # CASO ESPECIAL: Número en concepto + importe exacto = 100%
    if coincidencia_numero and diferencia_importe == 0:
        return 100
    
    # Normalizar a escala 0-100
    # Máximo posible: 40 + 30 + 20 + 30 = 120
    score_normalizado = min(100, int((score / 120) * 100))
    
    return score_normalizado

def conciliar_automaticamente(gasto_id, tipo_documento, documento_id, metodo='automatico'):
    """Crear una conciliación entre un gasto y un documento"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Obtener datos del gasto
        cursor.execute('SELECT * FROM gastos WHERE id = ?', (gasto_id,))
        gasto = dict(cursor.fetchone())
        
        # Obtener datos del documento
        if tipo_documento == 'factura':
            cursor.execute('SELECT * FROM factura WHERE id = ?', (documento_id,))
        elif tipo_documento == 'ticket':
            cursor.execute('SELECT * FROM tickets WHERE id = ?', (documento_id,))
        else:
            raise ValueError(f'Tipo de documento no válido: {tipo_documento}')
        
        documento = dict(cursor.fetchone())
        
        # Calcular diferencia
        diferencia = abs(gasto['importe_eur']) - documento['total']
        
        # Insertar conciliación
        cursor.execute('''
            INSERT INTO conciliacion_gastos 
            (gasto_id, tipo_documento, documento_id, fecha_conciliacion, 
             importe_gasto, importe_documento, diferencia, estado, metodo)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'conciliado', ?)
        ''', (
            gasto_id,
            tipo_documento,
            documento_id,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            gasto['importe_eur'],
            documento['total'],
            diferencia,
            metodo
        ))
        
        conn.commit()
        return True, 'Conciliación creada exitosamente'
        
    except sqlite3.IntegrityError:
        return False, 'Esta conciliación ya existe'
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()

# ============================================================================
# RUTAS API
# ============================================================================

@conciliacion_bp.route('/api/conciliacion/inicializar', methods=['POST'])
def inicializar_sistema():
    """Crear tabla de conciliación"""
    try:
        crear_tabla_conciliacion()
        return jsonify({'success': True, 'message': 'Sistema de conciliación inicializado'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@conciliacion_bp.route('/api/conciliacion/buscar/<int:gasto_id>', methods=['GET'])
def buscar_coincidencias(gasto_id):
    """Buscar coincidencias automáticas para un gasto"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener el gasto
        cursor.execute('SELECT * FROM gastos WHERE id = ?', (gasto_id,))
        gasto = cursor.fetchone()
        
        if not gasto:
            conn.close()
            return jsonify({'success': False, 'error': 'Gasto no encontrado'}), 404
        
        gasto_dict = dict(gasto)
        
        # Verificar si la tabla existe
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='conciliacion_gastos'
        """)
        
        tabla_existe = cursor.fetchone() is not None
        conn.close()
        
        if not tabla_existe:
            # Crear tabla automáticamente
            crear_tabla_conciliacion()
        
        # Buscar coincidencias
        coincidencias = buscar_coincidencias_automaticas(gasto_dict)
        
        return jsonify({
            'success': True,
            'gasto': gasto_dict,
            'coincidencias': coincidencias
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@conciliacion_bp.route('/api/conciliacion/conciliar', methods=['POST'])
def conciliar():
    """Conciliar un gasto con un documento"""
    try:
        data = request.json
        gasto_id = data.get('gasto_id')
        tipo_documento = data.get('tipo_documento')
        documento_id = data.get('documento_id')
        metodo = data.get('metodo', 'manual')
        
        if not all([gasto_id, tipo_documento, documento_id]):
            return jsonify({'success': False, 'error': 'Faltan parámetros'}), 400
        
        success, message = conciliar_automaticamente(gasto_id, tipo_documento, documento_id, metodo)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@conciliacion_bp.route('/api/conciliacion/gastos-pendientes', methods=['GET'])
def gastos_pendientes():
    """Obtener gastos sin conciliar"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si la tabla existe
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='conciliacion_gastos'
        """)
        
        tabla_existe = cursor.fetchone() is not None
        
        # Obtener parámetros de filtro
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        # Filtrar solo año actual (formato fecha DD/MM/YYYY)
        ano_actual = datetime.now().year
        
        if tabla_existe:
            query = '''
                SELECT g.*
                FROM gastos g
                WHERE g.id NOT IN (
                    SELECT gasto_id FROM conciliacion_gastos WHERE estado = 'conciliado'
                )
                AND g.importe_eur > 0
                AND g.concepto NOT LIKE '%Liquidacion Efectuada%'
                AND (
                    substr(g.fecha_operacion, -4) = ?
                    OR strftime('%Y', g.fecha_operacion) = ?
                )
            '''
        else:
            # Si no existe la tabla, todos los gastos son pendientes (excepto liquidaciones)
            query = '''
                SELECT g.*
                FROM gastos g
                WHERE g.importe_eur > 0
                AND g.concepto NOT LIKE '%Liquidacion Efectuada%'
                AND (
                    substr(g.fecha_operacion, -4) = ?
                    OR strftime('%Y', g.fecha_operacion) = ?
                )
            '''
        
        params = [str(ano_actual), str(ano_actual)]
        if fecha_inicio:
            query += ' AND g.fecha_operacion >= ?'
            params.append(fecha_inicio)
        if fecha_fin:
            query += ' AND g.fecha_operacion <= ?'
            params.append(fecha_fin)
        
        # Ordenar por fecha descendente (más recientes primero)
        # Convertir DD/MM/YYYY a formato ordenable YYYY-MM-DD
        query += ''' ORDER BY 
            CASE 
                WHEN g.fecha_operacion LIKE '__/__/____' THEN 
                    substr(g.fecha_operacion, 7, 4) || '-' || substr(g.fecha_operacion, 4, 2) || '-' || substr(g.fecha_operacion, 1, 2)
                ELSE g.fecha_operacion 
            END DESC, 
            g.id DESC'''
        
        cursor.execute(query, params)
        gastos = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'gastos': gastos,
            'total': len(gastos)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@conciliacion_bp.route('/api/conciliacion/conciliados', methods=['GET'])
def conciliados():
    """Obtener conciliaciones realizadas"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si la tabla existe
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='conciliacion_gastos'
        """)
        
        if not cursor.fetchone():
            # Tabla no existe, devolver vacío
            conn.close()
            return jsonify({
                'success': True,
                'conciliaciones': [],
                'total': 0
            })
        
        # Filtrar solo año actual y ordenar por fecha descendente (formato DD/MM/YYYY)
        ano_actual = datetime.now().year
        
        # Obtener conciliaciones normales (no liquidaciones TPV)
        cursor.execute('''
            SELECT 
                c.*,
                g.fecha_operacion,
                g.concepto as concepto_gasto,
                CASE 
                    WHEN c.tipo_documento = 'factura' THEN f.numero
                    WHEN c.tipo_documento = 'ticket' THEN t.numero
                END as numero_documento
            FROM conciliacion_gastos c
            LEFT JOIN gastos g ON c.gasto_id = g.id
            LEFT JOIN factura f ON c.tipo_documento = 'factura' AND c.documento_id = f.id
            LEFT JOIN tickets t ON c.tipo_documento = 'ticket' AND c.documento_id = t.id
            WHERE c.estado = 'conciliado'
            AND c.tipo_documento != 'liquidacion_tpv'
            AND (
                substr(g.fecha_operacion, -4) = ?
                OR strftime('%Y', g.fecha_operacion) = ?
            )
            ORDER BY 
                CASE 
                    WHEN g.fecha_operacion LIKE '__/__/____' THEN 
                        substr(g.fecha_operacion, 7, 4) || '-' || substr(g.fecha_operacion, 4, 2) || '-' || substr(g.fecha_operacion, 1, 2)
                    ELSE g.fecha_operacion 
                END DESC,
                c.fecha_conciliacion DESC
        ''', (str(ano_actual), str(ano_actual)))
        
        conciliaciones_normales = [dict(row) for row in cursor.fetchall()]
        
        # Obtener liquidaciones TPV agrupadas por fecha
        cursor.execute('''
            SELECT 
                MIN(c.id) as id,
                g.fecha_operacion,
                'Liquidación TPV ' || g.fecha_operacion as concepto_gasto,
                'liquidacion_tpv' as tipo_documento,
                COUNT(c.id) as num_liquidaciones,
                SUM(c.importe_gasto) as importe_gasto,
                0 as importe_documento,
                0 as diferencia,
                'conciliado' as estado,
                'automatico' as metodo,
                MAX(c.fecha_conciliacion) as fecha_conciliacion,
                GROUP_CONCAT(c.notas, ' | ') as notas
            FROM conciliacion_gastos c
            LEFT JOIN gastos g ON c.gasto_id = g.id
            WHERE c.estado = 'conciliado'
            AND c.tipo_documento = 'liquidacion_tpv'
            GROUP BY g.fecha_operacion
            ORDER BY MAX(c.fecha_conciliacion) DESC
        ''')
        
        liquidaciones_agrupadas = [dict(row) for row in cursor.fetchall()]
        
        # Combinar ambas listas
        conciliaciones = conciliaciones_normales + liquidaciones_agrupadas
        
        # Ordenar por fecha de conciliación
        conciliaciones.sort(key=lambda x: x['fecha_conciliacion'], reverse=True)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'conciliaciones': conciliaciones,
            'total': len(conciliaciones)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@conciliacion_bp.route('/api/conciliacion/eliminar/<int:conciliacion_id>', methods=['DELETE'])
def eliminar_conciliacion(conciliacion_id):
    """Eliminar una conciliación"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM conciliacion_gastos WHERE id = ?', (conciliacion_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Conciliación eliminada'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@conciliacion_bp.route('/api/conciliacion/procesar-automatico', methods=['POST'])
def procesar_automatico():
    """Procesar conciliaciones automáticas para todos los gastos pendientes"""
    try:
        data = request.json or {}
        umbral_score = data.get('umbral_score', 85)  # Score mínimo reducido a 85%
        auto_conciliar = data.get('auto_conciliar', True)  # Por defecto concilia automáticamente
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si la tabla existe
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='conciliacion_gastos'
        """)
        
        tabla_existe = cursor.fetchone() is not None
        
        if not tabla_existe:
            # Tabla no existe, no se puede conciliar
            conn.close()
            return jsonify({
                'success': True,
                'resultados': {
                    'procesados': 0,
                    'conciliados': 0,
                    'pendientes': 0,
                    'sugerencias': 0,
                    'detalles': [],
                    'mensaje': 'Sistema no inicializado. Por favor, haz clic en "Inicializar Sistema" primero.'
                }
            })
        
        # Obtener gastos pendientes (solo ingresos positivos)
        cursor.execute('''
            SELECT * FROM gastos
            WHERE id NOT IN (
                SELECT gasto_id FROM conciliacion_gastos WHERE estado = 'conciliado'
            )
            AND importe_eur > 0
            ORDER BY fecha_operacion DESC
        ''')
        
        gastos_pendientes = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        resultados = {
            'procesados': 0,
            'conciliados': 0,
            'pendientes': 0,
            'sugerencias': 0,
            'detalles': []
        }
        
        for gasto in gastos_pendientes:
            resultados['procesados'] += 1
            
            # Buscar coincidencias
            coincidencias = buscar_coincidencias_automaticas(gasto)
            
            if coincidencias and len(coincidencias) > 0:
                mejor = coincidencias[0]
                
                # Si el score es muy alto (>=85), conciliar automáticamente
                if mejor['score'] >= umbral_score and auto_conciliar:
                    success, message = conciliar_automaticamente(
                        gasto['id'],
                        mejor['tipo'],
                        mejor['id'],
                        'automatico'
                    )
                    
                    if success:
                        resultados['conciliados'] += 1
                        resultados['detalles'].append({
                            'gasto_id': gasto['id'],
                            'fecha': gasto['fecha_operacion'],
                            'concepto': gasto['concepto'],
                            'importe': gasto['importe_eur'],
                            'documento': f"{mejor['tipo'].upper()} {mejor['numero']}",
                            'score': mejor['score'],
                            'estado': 'conciliado'
                        })
                    else:
                        resultados['pendientes'] += 1
                        resultados['detalles'].append({
                            'gasto_id': gasto['id'],
                            'error': message
                        })
                # Si el score es medio (70-84), marcar como sugerencia
                elif mejor['score'] >= 70:
                    resultados['sugerencias'] += 1
                    resultados['detalles'].append({
                        'gasto_id': gasto['id'],
                        'fecha': gasto['fecha_operacion'],
                        'concepto': gasto['concepto'],
                        'importe': gasto['importe_eur'],
                        'documento': f"{mejor['tipo'].upper()} {mejor['numero']}",
                        'score': mejor['score'],
                        'estado': 'sugerencia'
                    })
                else:
                    resultados['pendientes'] += 1
            else:
                resultados['pendientes'] += 1
        
        return jsonify({
            'success': True,
            'resultados': resultados
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@conciliacion_bp.route('/api/conciliacion/ejecutar-cron', methods=['GET'])
def ejecutar_cron():
    """
    Endpoint para ejecutar desde cron
    Procesa automáticamente todos los gastos pendientes
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener gastos pendientes
        cursor.execute('''
            SELECT * FROM gastos
            WHERE id NOT IN (
                SELECT gasto_id FROM conciliacion_gastos WHERE estado = 'conciliado'
            )
            AND importe_eur > 0
            ORDER BY fecha_operacion DESC
        ''')
        
        gastos_pendientes = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        conciliados = 0
        
        for gasto in gastos_pendientes:
            # Buscar coincidencias
            coincidencias = buscar_coincidencias_automaticas(gasto)
            
            # Solo conciliar si hay una coincidencia con score >= 90%
            if coincidencias and coincidencias[0]['score'] >= 90:
                mejor = coincidencias[0]
                success, _ = conciliar_automaticamente(
                    gasto['id'],
                    mejor['tipo'],
                    mejor['id'],
                    'automatico'
                )
                
                if success:
                    conciliados += 1
        
        return jsonify({
            'success': True,
            'procesados': len(gastos_pendientes),
            'conciliados': conciliados,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@conciliacion_bp.route('/api/conciliacion/notificaciones', methods=['GET'])
def obtener_notificaciones():
    """Obtener notificaciones generales y de conciliación"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        todas_notificaciones = []
        
        # 1. Obtener notificaciones generales de la tabla notificaciones
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='notificaciones'
        """)
        
        if cursor.fetchone():
            cursor.execute('''
                SELECT 
                    id,
                    tipo,
                    mensaje,
                    timestamp as fecha_conciliacion,
                    'general' as origen
                FROM notificaciones
                ORDER BY timestamp DESC
                LIMIT 50
            ''')
            notificaciones_generales = [dict(row) for row in cursor.fetchall()]
            todas_notificaciones.extend(notificaciones_generales)
        
        # 2. Obtener notificaciones de conciliación
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='conciliacion_gastos'
        """)
        
        if cursor.fetchone():
            cursor.execute('''
                SELECT 
                    c.id,
                    c.fecha_conciliacion,
                    c.importe_gasto,
                    c.importe_documento,
                    c.diferencia,
                    c.metodo,
                    g.fecha_operacion,
                    g.concepto as concepto_gasto,
                    CASE 
                        WHEN c.tipo_documento = 'factura' THEN f.numero
                        WHEN c.tipo_documento = 'ticket' THEN t.numero
                    END as numero_documento,
                    c.tipo_documento,
                    'conciliacion' as origen
                FROM conciliacion_gastos c
                LEFT JOIN gastos g ON c.gasto_id = g.id
                LEFT JOIN factura f ON c.tipo_documento = 'factura' AND c.documento_id = f.id
                LEFT JOIN tickets t ON c.tipo_documento = 'ticket' AND c.documento_id = t.id
                WHERE c.notificado = 0 AND c.estado = 'conciliado'
                ORDER BY c.fecha_conciliacion DESC
                LIMIT 50
            ''')
            notificaciones_conciliacion = [dict(row) for row in cursor.fetchall()]
            todas_notificaciones.extend(notificaciones_conciliacion)
        
        # Ordenar todas por fecha
        todas_notificaciones.sort(key=lambda x: x.get('fecha_conciliacion', ''), reverse=True)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'notificaciones': todas_notificaciones,
            'total': len(todas_notificaciones)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@conciliacion_bp.route('/api/notificaciones/eliminar', methods=['POST'])
def eliminar_notificaciones():
    """Eliminar notificaciones generales"""
    try:
        data = request.json
        ids = data.get('ids', [])
        
        if not ids:
            return jsonify({'success': False, 'error': 'No se proporcionaron IDs'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Eliminar notificaciones generales
        placeholders = ','.join('?' * len(ids))
        cursor.execute(f'''
            DELETE FROM notificaciones
            WHERE id IN ({placeholders})
        ''', ids)
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'eliminadas': cursor.rowcount
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@conciliacion_bp.route('/api/conciliacion/marcar-notificadas', methods=['POST'])
def marcar_notificadas():
    """Marcar notificaciones como leídas"""
    try:
        data = request.json
        ids = data.get('ids', [])
        
        if not ids:
            return jsonify({'success': False, 'error': 'No se proporcionaron IDs'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        placeholders = ','.join('?' * len(ids))
        cursor.execute(f'''
            UPDATE conciliacion_gastos 
            SET notificado = 1 
            WHERE id IN ({placeholders})
        ''', ids)
        
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'{affected} notificaciones marcadas como leídas'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@conciliacion_bp.route('/api/conciliacion/contador-notificaciones', methods=['GET'])
def contador_notificaciones():
    """Obtener contador de notificaciones no leídas"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) as total
            FROM conciliacion_gastos
            WHERE notificado = 0 AND estado = 'conciliado'
        ''')
        
        resultado = cursor.fetchone()
        conn.close()
        
        return jsonify({
            'success': True,
            'total': resultado['total']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@conciliacion_bp.route('/api/conciliacion/liquidaciones-tpv', methods=['GET'])
def obtener_liquidaciones_tpv():
    """Obtener liquidaciones TPV agrupadas por fecha y compararlas con tickets"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Filtrar solo año actual (formato DD/MM/YYYY)
        ano_actual = datetime.now().year
        
        # Obtener todas las liquidaciones
        # Filtro específico: "Liquidacion Efectuada" para evitar capturar otros conceptos
        cursor.execute('''
            SELECT 
                id,
                fecha_operacion,
                concepto,
                importe_eur
            FROM gastos
            WHERE concepto LIKE '%Liquidacion Efectuada%'
            AND id NOT IN (
                SELECT gasto_id FROM conciliacion_gastos WHERE estado = 'conciliado'
            )
            AND (
                substr(fecha_operacion, -4) = ?
                OR strftime('%Y', fecha_operacion) = ?
            )
            ORDER BY 
                CASE 
                    WHEN fecha_operacion LIKE '__/__/____' THEN 
                        substr(fecha_operacion, 7, 4) || '-' || substr(fecha_operacion, 4, 2) || '-' || substr(fecha_operacion, 1, 2)
                    ELSE fecha_operacion 
                END DESC
        ''', (str(ano_actual), str(ano_actual)))
        
        liquidaciones_raw = cursor.fetchall()
        
        # Agrupar por fecha extraída del concepto
        import re
        liquidaciones_agrupadas = {}
        
        for liq in liquidaciones_raw:
            # Extraer fecha del concepto: "Liquidacion Efectuada El 31/01/2025..."
            match = re.search(r'El (\d{2}/\d{2}/\d{4})', liq['concepto'])
            if match:
                fecha_liquidacion = match.group(1)
            else:
                fecha_liquidacion = liq['fecha_operacion']
            
            if fecha_liquidacion not in liquidaciones_agrupadas:
                liquidaciones_agrupadas[fecha_liquidacion] = {
                    'ids': [],
                    'total': 0,
                    'count': 0
                }
            
            liquidaciones_agrupadas[fecha_liquidacion]['ids'].append(str(liq['id']))
            liquidaciones_agrupadas[fecha_liquidacion]['total'] += liq['importe_eur']
            liquidaciones_agrupadas[fecha_liquidacion]['count'] += 1
        
        resultado = []
        
        # Ordenar por fecha descendente (más recientes primero)
        liquidaciones_ordenadas = sorted(
            liquidaciones_agrupadas.items(),
            key=lambda x: datetime.strptime(x[0], '%d/%m/%Y') if '/' in x[0] else datetime.strptime(x[0], '%Y-%m-%d'),
            reverse=True
        )
        
        for fecha_str, datos in liquidaciones_ordenadas:
            # Convertir fecha a formato YYYY-MM-DD para buscar tickets
            try:
                if '/' in fecha_str:
                    fecha_obj = datetime.strptime(fecha_str, '%d/%m/%Y')
                else:
                    fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
                fecha_busqueda = fecha_obj.strftime('%Y-%m-%d')
            except:
                continue
            
            # Buscar tickets con tarjeta de esa fecha
            cursor.execute('''
                SELECT 
                    COUNT(*) as num_tickets,
                    SUM(total) as total_tickets
                FROM tickets
                WHERE fecha = ?
                AND formaPago = 'T'
                AND estado = 'C'
            ''', (fecha_busqueda,))
            
            tickets_info = cursor.fetchone()
            total_tickets = tickets_info['total_tickets'] or 0
            num_tickets = tickets_info['num_tickets'] or 0
            
            # Buscar facturas con tarjeta de esa fecha
            cursor.execute('''
                SELECT 
                    COUNT(*) as num_facturas,
                    SUM(total) as total_facturas
                FROM factura
                WHERE fecha = ?
                AND formaPago = 'T'
                AND estado = 'C'
            ''', (fecha_busqueda,))
            
            facturas_info = cursor.fetchone()
            total_facturas = facturas_info['total_facturas'] or 0
            num_facturas = facturas_info['num_facturas'] or 0
            
            # Sumar tickets y facturas
            total_documentos = total_tickets + total_facturas
            num_documentos = num_tickets + num_facturas
            
            # Calcular diferencia
            total_liq = datos['total']
            diferencia = abs(total_liq - total_documentos)
            porcentaje_diferencia = (diferencia / abs(total_liq) * 100) if total_liq != 0 else 0
            
            # Determinar estado
            if diferencia <= 0.02:
                estado = 'exacto'
            elif porcentaje_diferencia <= 5:
                estado = 'aceptable'
            else:
                estado = 'revisar'
            
            # Conciliar automáticamente si diferencia <= 1€
            if diferencia <= 1.0 and num_documentos > 0:
                try:
                    # Conciliar cada liquidación de esta fecha
                    for gasto_id in datos['ids']:
                        cursor.execute('SELECT importe_eur FROM gastos WHERE id = ?', (int(gasto_id),))
                        gasto_row = cursor.fetchone()
                        if gasto_row:
                            importe_gasto = gasto_row['importe_eur']
                            cursor.execute('''
                                INSERT OR IGNORE INTO conciliacion_gastos 
                                (gasto_id, tipo_documento, documento_id, fecha_conciliacion, 
                                 importe_gasto, importe_documento, diferencia, estado, metodo, notificado, notas)
                                VALUES (?, ?, ?, datetime('now'), ?, ?, ?, 'conciliado', 'automatico', 0, ?)
                            ''', (int(gasto_id), 'liquidacion_tpv', 0, 
                                  importe_gasto, total_documentos, diferencia,
                                  f'Liquidación TPV {fecha_str} - {num_documentos} documentos - Conciliado automáticamente (dif: {round(diferencia, 2)}€)'))
                    conn.commit()
                    # No añadir a resultado si se concilió automáticamente
                    continue
                except Exception as e:
                    print(f"Error conciliando automáticamente liquidación {fecha_str}: {e}")
                    # Si falla, continuar y mostrar en la lista
            
            resultado.append({
                'fecha': fecha_str,
                'num_liquidaciones': datos['count'],
                'total_liquidaciones': round(total_liq, 2),
                'num_tickets': num_tickets,
                'num_facturas': num_facturas,
                'total_tickets': round(total_tickets, 2),
                'total_facturas': round(total_facturas, 2),
                'total_documentos': round(total_documentos, 2),
                'diferencia': round(diferencia, 2),
                'porcentaje_diferencia': round(porcentaje_diferencia, 2),
                'estado': estado,
                'ids_gastos': ','.join(datos['ids'])
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'liquidaciones': resultado
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@conciliacion_bp.route('/api/conciliacion/ingresos-efectivo', methods=['GET'])
def obtener_ingresos_efectivo():
    """Obtener ingresos en efectivo del banco agrupados por fecha y compararlos con facturas/tickets en efectivo"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Filtrar solo año actual (formato DD/MM/YYYY)
        ano_actual = datetime.now().year
        
        # Obtener ingresos en efectivo del banco (case-insensitive)
        cursor.execute('''
            SELECT 
                id,
                fecha_operacion,
                concepto,
                importe_eur
            FROM gastos
            WHERE (
                LOWER(concepto) LIKE '%ingreso%efectivo%'
                OR LOWER(concepto) LIKE '%ingreso%efvo%'
                OR LOWER(concepto) LIKE '%deposito%efectivo%'
                OR LOWER(concepto) LIKE '%ingreso%caja%'
            )
            AND importe_eur > 0
            AND id NOT IN (
                SELECT gasto_id FROM conciliacion_gastos WHERE estado = 'conciliado'
            )
            AND (
                substr(fecha_operacion, -4) = ?
                OR strftime('%Y', fecha_operacion) = ?
            )
            ORDER BY 
                CASE 
                    WHEN fecha_operacion LIKE '__/__/____' THEN 
                        substr(fecha_operacion, 7, 4) || '-' || substr(fecha_operacion, 4, 2) || '-' || substr(fecha_operacion, 1, 2)
                    ELSE fecha_operacion 
                END DESC
        ''', (str(ano_actual), str(ano_actual)))
        
        ingresos_raw = cursor.fetchall()
        
        # Agrupar por fecha
        ingresos_agrupados = {}
        
        for ing in ingresos_raw:
            fecha = ing['fecha_operacion']
            
            if fecha not in ingresos_agrupados:
                ingresos_agrupados[fecha] = {
                    'ids': [],
                    'total': 0,
                    'count': 0
                }
            
            ingresos_agrupados[fecha]['ids'].append(str(ing['id']))
            ingresos_agrupados[fecha]['total'] += ing['importe_eur']
            ingresos_agrupados[fecha]['count'] += 1
        
        resultado = []
        
        for fecha_str, datos in ingresos_agrupados.items():
            # Convertir fecha a formato YYYY-MM-DD para buscar documentos
            try:
                if '/' in fecha_str:
                    fecha_obj = datetime.strptime(fecha_str, '%d/%m/%Y')
                else:
                    fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
                fecha_busqueda = fecha_obj.strftime('%Y-%m-%d')
                
                # Buscar en rango de ±30 días (el efectivo se deposita después)
                fecha_inicio = (fecha_obj - timedelta(days=30)).strftime('%Y-%m-%d')
                fecha_fin = fecha_obj.strftime('%Y-%m-%d')
            except:
                continue
            
            # Buscar facturas con efectivo en el rango
            cursor.execute('''
                SELECT 
                    COUNT(*) as num_facturas,
                    SUM(total) as total_facturas
                FROM factura
                WHERE fecha BETWEEN ? AND ?
                AND formaPago = 'E'
                AND estado = 'C'
            ''', (fecha_inicio, fecha_fin))
            
            facturas_info = cursor.fetchone()
            total_facturas = facturas_info['total_facturas'] or 0
            num_facturas = facturas_info['num_facturas'] or 0
            
            # Buscar tickets con efectivo en el rango
            cursor.execute('''
                SELECT 
                    COUNT(*) as num_tickets,
                    SUM(total) as total_tickets
                FROM tickets
                WHERE fecha BETWEEN ? AND ?
                AND formaPago = 'E'
                AND estado = 'C'
            ''', (fecha_inicio, fecha_fin))
            
            tickets_info = cursor.fetchone()
            total_tickets = tickets_info['total_tickets'] or 0
            num_tickets = tickets_info['num_tickets'] or 0
            
            # Sumar facturas y tickets
            total_documentos = total_facturas + total_tickets
            num_documentos = num_facturas + num_tickets
            
            # Calcular diferencia
            total_ing = datos['total']
            diferencia = abs(total_ing - total_documentos)
            porcentaje_diferencia = (diferencia / abs(total_ing) * 100) if total_ing != 0 else 0
            
            # Determinar estado
            if diferencia <= 1.0:
                estado = 'exacto'
            elif porcentaje_diferencia <= 5:
                estado = 'aceptable'
            else:
                estado = 'revisar'
            
            # Conciliar automáticamente si diferencia <= 1€
            if diferencia <= 1.0 and num_documentos > 0:
                try:
                    for gasto_id in datos['ids']:
                        cursor.execute('SELECT importe_eur FROM gastos WHERE id = ?', (int(gasto_id),))
                        gasto_row = cursor.fetchone()
                        if gasto_row:
                            importe_gasto = gasto_row['importe_eur']
                            cursor.execute('''
                                INSERT OR IGNORE INTO conciliacion_gastos 
                                (gasto_id, tipo_documento, documento_id, fecha_conciliacion, 
                                 importe_gasto, importe_documento, diferencia, estado, metodo, notificado, notas)
                                VALUES (?, ?, ?, datetime('now'), ?, ?, ?, 'conciliado', 'automatico', 0, ?)
                            ''', (int(gasto_id), 'ingreso_efectivo', 0, 
                                  importe_gasto, total_documentos, diferencia,
                                  f'Ingreso efectivo {fecha_str} - {num_documentos} documentos - Conciliado automáticamente (dif: {round(diferencia, 2)}€)'))
                    conn.commit()
                    continue
                except Exception as e:
                    print(f"Error conciliando automáticamente ingreso {fecha_str}: {e}")
            
            resultado.append({
                'fecha': fecha_str,
                'num_ingresos': datos['count'],
                'total_ingresos': round(total_ing, 2),
                'num_facturas': num_facturas,
                'num_tickets': num_tickets,
                'total_facturas': round(total_facturas, 2),
                'total_tickets': round(total_tickets, 2),
                'total_documentos': round(total_documentos, 2),
                'diferencia': round(diferencia, 2),
                'porcentaje_diferencia': round(porcentaje_diferencia, 2),
                'estado': estado,
                'ids_gastos': ','.join(datos['ids']),
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'ingresos': resultado
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@conciliacion_bp.route('/api/conciliacion/conciliar-ingreso-efectivo', methods=['POST'])
def conciliar_ingreso_efectivo():
    """Conciliar un ingreso en efectivo con sus facturas/tickets"""
    try:
        data = request.json
        ids_gastos = data.get('ids_gastos', '').split(',')
        fecha = data.get('fecha')
        fecha_inicio = data.get('fecha_inicio')
        fecha_fin = data.get('fecha_fin')
        
        if not ids_gastos or not fecha:
            return jsonify({'success': False, 'error': 'Faltan parámetros'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener facturas y tickets con efectivo en el rango
        cursor.execute('''
            SELECT 'factura' as tipo, id, numero, total
            FROM factura
            WHERE fecha BETWEEN ? AND ? AND formaPago = 'E' AND estado = 'C'
        ''', (fecha_inicio, fecha_fin))
        facturas = cursor.fetchall()
        
        cursor.execute('''
            SELECT 'ticket' as tipo, id, numero, total
            FROM tickets
            WHERE fecha BETWEEN ? AND ? AND formaPago = 'E' AND estado = 'C'
        ''', (fecha_inicio, fecha_fin))
        tickets = cursor.fetchall()
        
        documentos = list(facturas) + list(tickets)
        
        if not documentos:
            conn.close()
            return jsonify({'success': False, 'error': 'No hay documentos para conciliar'}), 400
        
        conciliados = 0
        total_documentos = sum(doc['total'] for doc in documentos)
        
        # Marcar cada ingreso como conciliado
        for gasto_id in ids_gastos:
            if not gasto_id.strip():
                continue
            
            cursor.execute('SELECT importe_eur FROM gastos WHERE id = ?', (int(gasto_id),))
            gasto_row = cursor.fetchone()
            if not gasto_row:
                continue
            
            importe_gasto = gasto_row['importe_eur']
            diferencia = abs(importe_gasto - total_documentos)
            
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO conciliacion_gastos 
                    (gasto_id, tipo_documento, documento_id, fecha_conciliacion, 
                     importe_gasto, importe_documento, diferencia, estado, metodo, notificado, notas)
                    VALUES (?, ?, ?, datetime('now'), ?, ?, ?, 'conciliado', 'manual', 0, ?)
                ''', (int(gasto_id), 'ingreso_efectivo', 0, 
                      importe_gasto, total_documentos, diferencia,
                      f'Ingreso efectivo {fecha} - {len(documentos)} documentos ({len(facturas)} facturas, {len(tickets)} tickets)'))
                
                if cursor.rowcount > 0:
                    conciliados += 1
            except Exception as e:
                print(f"Error conciliando ingreso {gasto_id}: {e}")
                continue
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'conciliados': conciliados,
            'mensaje': f'Ingreso conciliado: {conciliados} registros'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@conciliacion_bp.route('/api/conciliacion/conciliar-liquidacion', methods=['POST'])
def conciliar_liquidacion():
    """Conciliar una liquidación TPV con sus tickets/facturas"""
    try:
        data = request.json
        ids_gastos = data.get('ids_gastos', '').split(',')
        fecha = data.get('fecha')
        
        if not ids_gastos or not fecha:
            return jsonify({'success': False, 'error': 'Faltan parámetros'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Convertir fecha a formato YYYY-MM-DD
        try:
            if '/' in fecha:
                fecha_obj = datetime.strptime(fecha, '%d/%m/%Y')
            else:
                fecha_obj = datetime.strptime(fecha, '%Y-%m-%d')
            fecha_busqueda = fecha_obj.strftime('%Y-%m-%d')
        except:
            return jsonify({'success': False, 'error': 'Formato de fecha inválido'}), 400
        
        # Obtener tickets y facturas con tarjeta de esa fecha
        cursor.execute('''
            SELECT 'ticket' as tipo, id, numero, total
            FROM tickets
            WHERE fecha = ? AND formaPago = 'T' AND estado = 'C'
        ''', (fecha_busqueda,))
        tickets = cursor.fetchall()
        
        cursor.execute('''
            SELECT 'factura' as tipo, id, numero, total
            FROM factura
            WHERE fecha = ? AND formaPago = 'T' AND estado = 'C'
        ''', (fecha_busqueda,))
        facturas = cursor.fetchall()
        
        documentos = list(tickets) + list(facturas)
        
        if not documentos:
            conn.close()
            return jsonify({'success': False, 'error': 'No hay documentos para conciliar'}), 400
        
        # Conciliar liquidaciones TPV: marcar como conciliados
        # Estrategia: marcar cada gasto y cada documento como conciliado
        # sin crear relaciones 1:1 (porque son agrupaciones por fecha)
        conciliados = 0
        
        # Marcar cada liquidación como conciliada con una referencia genérica
        for gasto_id in ids_gastos:
            if not gasto_id.strip():
                continue
            
            # Obtener el importe del gasto
            cursor.execute('SELECT importe_eur FROM gastos WHERE id = ?', (int(gasto_id),))
            gasto_row = cursor.fetchone()
            if not gasto_row:
                continue
            
            importe_gasto = gasto_row['importe_eur']
            
            # Crear UNA SOLA entrada de conciliación por liquidación
            # usando el primer documento como referencia
            if documentos:
                doc = documentos[0]
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO conciliacion_gastos 
                        (gasto_id, tipo_documento, documento_id, fecha_conciliacion, 
                         importe_gasto, importe_documento, diferencia, estado, metodo, notificado, notas)
                        VALUES (?, ?, ?, datetime('now'), ?, ?, 
                                0, 'conciliado', 'automatico', 0, ?)
                    ''', (int(gasto_id), 'liquidacion_tpv', 0, 
                          importe_gasto, 0,
                          f'Liquidación TPV {fecha} - {len(documentos)} documentos'))
                    
                    if cursor.rowcount > 0:
                        conciliados += 1
                except Exception as e:
                    print(f"Error conciliando liquidación {gasto_id}: {e}")
                    continue
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'conciliados': conciliados,
            'mensaje': f'Liquidación conciliada: {conciliados} documentos'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

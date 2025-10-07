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
    2. Fecha cercana (±7 días)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    gasto_id = gasto['id']
    importe = abs(gasto['importe_eur'])
    
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
    
    tolerancia = 0.02
    
    coincidencias = []
    
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
        
        if tabla_existe:
            query = '''
                SELECT g.*
                FROM gastos g
                WHERE g.id NOT IN (
                    SELECT gasto_id FROM conciliacion_gastos WHERE estado = 'conciliado'
                )
                AND g.importe_eur > 0
            '''
        else:
            # Si no existe la tabla, todos los gastos son pendientes
            query = '''
                SELECT g.*
                FROM gastos g
                WHERE g.importe_eur > 0
            '''
        
        params = []
        if fecha_inicio:
            query += ' AND g.fecha_operacion >= ?'
            params.append(fecha_inicio)
        if fecha_fin:
            query += ' AND g.fecha_operacion <= ?'
            params.append(fecha_fin)
        
        query += ' ORDER BY g.fecha_operacion DESC'
        
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
            ORDER BY c.fecha_conciliacion DESC
        ''')
        
        conciliaciones = [dict(row) for row in cursor.fetchall()]
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
    """Obtener conciliaciones no notificadas"""
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
                'notificaciones': [],
                'total': 0
            })
        
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
                c.tipo_documento
            FROM conciliacion_gastos c
            LEFT JOIN gastos g ON c.gasto_id = g.id
            LEFT JOIN factura f ON c.tipo_documento = 'factura' AND c.documento_id = f.id
            LEFT JOIN tickets t ON c.tipo_documento = 'ticket' AND c.documento_id = t.id
            WHERE c.notificado = 0 AND c.estado = 'conciliado'
            ORDER BY c.fecha_conciliacion DESC
            LIMIT 50
        ''')
        
        notificaciones = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            'success': True,
            'notificaciones': notificaciones,
            'total': len(notificaciones)
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
        
        # Verificar si la tabla existe
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='conciliacion_gastos'
        """)
        
        if not cursor.fetchone():
            # Tabla no existe, devolver 0
            conn.close()
            return jsonify({
                'success': True,
                'total': 0
            })
        
        cursor.execute('''
            SELECT COUNT(*) as total
            FROM conciliacion_gastos
            WHERE notificado = 0 AND estado = 'conciliado'
        ''')
        
        result = cursor.fetchone()
        total = result['total'] if result else 0
        conn.close()
        
        return jsonify({
            'success': True,
            'total': total
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

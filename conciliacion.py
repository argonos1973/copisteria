# conciliacion.py
# Sistema de conciliación automática entre gastos bancarios y facturas/tickets
import sqlite3
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from constantes import DB_NAME
from db_utils import get_db_connection
from logger_config import get_logger

# Inicializar logger
logger = get_logger(__name__)

conciliacion_bp = Blueprint('conciliacion', __name__)

# ============================================================================
# CONFIGURACIÓN CENTRALIZADA (JSON)
# ============================================================================

from config_conciliacion import get_tolerancia_conciliacion, set_tolerancia_conciliacion

def encontrar_mejor_combinacion_documentos(documentos, importe_objetivo, tolerancia=1.0):
    """
    Encuentra la mejor combinación de documentos que se aproxime al importe objetivo.
    Usa programación dinámica para encontrar la combinación óptima.
    
    Args:
        documentos: Lista de dicts con 'id', 'tipo', 'importe'
        importe_objetivo: Importe a alcanzar
        tolerancia: Diferencia máxima aceptable
    
    Returns:
        (mejor_combinacion, diferencia) o (None, None) si no encuentra combinación válida
    """
    if not documentos:
        return None, None
    
    # Convertir importes a centavos para evitar problemas de punto flotante
    objetivo_centavos = int(round(importe_objetivo * 100))
    tolerancia_centavos = int(round(tolerancia * 100))
    
    # Preparar documentos con importes en centavos
    docs_centavos = []
    for doc in documentos:
        importe_centavos = int(round(doc['importe'] * 100))
        if importe_centavos > 0:  # Solo documentos con importe positivo
            docs_centavos.append({
                'id': doc['id'],
                'tipo': doc['tipo'],
                'importe': doc['importe'],
                'importe_centavos': importe_centavos
            })
    
    if not docs_centavos:
        return None, None
    
    # Intentar encontrar combinación exacta o muy cercana
    mejor_combinacion = None
    mejor_diferencia = float('inf')
    
    # Programación dinámica: dp[i] = (suma, lista de índices)
    # Limitamos a combinaciones de hasta 50 documentos para evitar explosión combinatoria
    max_docs = min(len(docs_centavos), 50)
    
    # Probar con diferentes tamaños de combinación (empezar con pocas para ser más rápido)
    for max_size in [1, 2, 3, 5, 10, 20, max_docs]:
        if max_size > len(docs_centavos):
            continue
            
        # Generar combinaciones de forma greedy
        # Ordenar por cercanía al objetivo
        docs_ordenados = sorted(docs_centavos, 
                               key=lambda d: abs(d['importe_centavos'] - objetivo_centavos))
        
        # Probar combinación greedy
        combinacion_actual = []
        suma_actual = 0
        
        for doc in docs_ordenados:
            if len(combinacion_actual) >= max_size:
                break
            
            # Agregar documento si mejora la aproximación o si aún no llegamos al objetivo
            nueva_suma = suma_actual + doc['importe_centavos']
            diferencia_con_doc = abs(objetivo_centavos - nueva_suma)
            diferencia_sin_doc = abs(objetivo_centavos - suma_actual)
            
            # Agregar si:
            # 1. Mejora la diferencia, O
            # 2. Aún no hemos llegado al objetivo y no nos pasamos demasiado
            if (diferencia_con_doc < diferencia_sin_doc or 
                (suma_actual < objetivo_centavos and nueva_suma <= objetivo_centavos + tolerancia_centavos * 2)):
                combinacion_actual.append(doc)
                suma_actual = nueva_suma
        
        diferencia_actual = abs(objetivo_centavos - suma_actual)
        
        if diferencia_actual < mejor_diferencia:
            mejor_diferencia = diferencia_actual
            mejor_combinacion = combinacion_actual[:]
            
            # Si encontramos combinación dentro de tolerancia, retornar
            if diferencia_actual <= tolerancia_centavos:
                return mejor_combinacion, mejor_diferencia / 100.0
    
    # Retornar mejor combinación encontrada si está dentro de tolerancia
    if mejor_diferencia <= tolerancia_centavos:
        return mejor_combinacion, mejor_diferencia / 100.0
    
    return None, None

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
    1. Importe exacto o muy cercano (tolerancia configurable desde BD)
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
    
    # Obtener tolerancia desde configuración centralizada
    tolerancia = get_tolerancia_conciliacion()
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
                    importe_cobrado,
                    fechaCobro
                FROM factura
                WHERE estado IN ('C', 'P', 'V')
                AND numero = ?
                AND ABS(total - ?) <= ?
                AND NOT EXISTS (
                    SELECT 1 FROM conciliacion_gastos cg
                    WHERE cg.tipo_documento = 'factura' 
                    AND cg.documento_id = id
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
                AND NOT EXISTS (
                    SELECT 1 FROM conciliacion_gastos cg
                    WHERE cg.tipo_documento = 'ticket'
                    AND cg.documento_id = id
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
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            fecha_gasto = datetime.strptime(fecha_gasto_str, '%Y-%m-%d')
        
        fecha_inicio = (fecha_gasto - timedelta(days=15)).strftime('%Y-%m-%d')
        fecha_fin = (fecha_gasto + timedelta(days=15)).strftime('%Y-%m-%d')
        
        # Buscar en facturas (cobradas y pendientes)
        # Para facturas cobradas, usar fechaCobro; para pendientes, usar fecha
        cursor.execute('''
            SELECT 
                'factura' as tipo,
                id,
                numero,
                fecha,
                total,
                estado,
                importe_cobrado,
                fechaCobro
            FROM factura
            WHERE estado IN ('C', 'P', 'V')
            AND (
                (estado = 'C' AND COALESCE(fechaCobro, fecha) BETWEEN ? AND ?)
                OR (estado IN ('P', 'V') AND fecha BETWEEN ? AND ?)
            )
            AND ABS(total - ?) <= ?
            AND NOT EXISTS (
                SELECT 1 FROM conciliacion_gastos cg
                WHERE cg.tipo_documento = 'factura'
                AND cg.documento_id = id
            )
        ''', (fecha_inicio, fecha_fin, fecha_inicio, fecha_fin, importe, tolerancia))
        
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
            AND NOT EXISTS (
                SELECT 1 FROM conciliacion_gastos cg
                WHERE cg.tipo_documento = 'ticket'
                AND cg.documento_id = id
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
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        # Si falla, asumir formato ISO
        fecha_gasto = datetime.strptime(fecha_gasto_str, '%Y-%m-%d')
    
    # Para facturas cobradas, usar fechaCobro si está disponible
    fecha_documento_str = documento.get('fechaCobro') if documento.get('fechaCobro') else documento['fecha']
    fecha_doc = datetime.strptime(fecha_documento_str, '%Y-%m-%d')
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
        
        # REGLA: No permitir conciliación manual de facturas pendientes
        if metodo == 'manual' and tipo_documento == 'factura' and documento.get('estado') == 'P':
            return False, 'No se pueden conciliar manualmente facturas pendientes. Solo facturas cobradas.'
        
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
        
        # REGLA: Marcar factura como cobrada solo si:
        # 1. Es una factura pendiente (estado = 'P') o vencida (estado = 'V')
        # 2. Diferencia exacta (< 0.01€)
        # 3. Coincidencia por número de factura en el concepto del gasto
        factura_marcada_cobrada = False
        numero_factura_cobrada = None
        
        if tipo_documento == 'factura' and documento.get('estado') in ['P', 'V'] and abs(diferencia) < 0.01:
            # Verificar si el número de factura está en el concepto del gasto
            numero_factura = documento.get('numero', '')
            concepto_gasto = gasto.get('concepto', '').upper()
            
            # Buscar el número de factura en el concepto (puede estar como F250046 o similar)
            tiene_numero_factura = numero_factura and numero_factura.upper() in concepto_gasto
            
            if tiene_numero_factura:
                fecha_hoy = datetime.now()
                cursor.execute('''
                    UPDATE factura 
                    SET estado = 'C',
                        importe_cobrado = ?,
                        timestamp = ?,
                        fechaCobro = ?
                    WHERE id = ? AND estado IN ('P', 'V')
                ''', (documento['total'], fecha_hoy.isoformat(), fecha_hoy.strftime('%Y-%m-%d'), documento_id))
                
                if cursor.rowcount > 0:
                    factura_marcada_cobrada = True
                    numero_factura_cobrada = numero_factura
                    estado_anterior = documento.get('estado', 'P')
                    logger.info(f"✓ Factura {numero_factura} marcada como COBRADA (estado: {estado_anterior} → C) - Coincidencia exacta por número")
            else:
                logger.info(f"⊗ Factura {numero_factura} NO marcada como cobrada - Sin coincidencia por número en concepto")
        
        conn.commit()
        
        # Retornar mensaje con información de factura marcada como cobrada
        mensaje = 'Conciliación creada exitosamente'
        if factura_marcada_cobrada:
            mensaje += f' | Factura {numero_factura_cobrada} marcada como COBRADA'
        
        return True, mensaje
        
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
            faltantes = []
            if not gasto_id: faltantes.append('gasto_id')
            if not tipo_documento: faltantes.append('tipo_documento')
            if not documento_id: faltantes.append('documento_id')
            return jsonify({'success': False, 'error': f'Faltan parámetros: {", ".join(faltantes)}'}), 400
        
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
                SELECT DISTINCT g.*
                FROM gastos g
                WHERE g.id NOT IN (
                    SELECT DISTINCT gasto_id FROM conciliacion_gastos WHERE estado = 'conciliado'
                )
                AND g.importe_eur > 0
                AND g.concepto NOT LIKE '%Liquidacion Efectuada%'
                AND g.concepto NOT LIKE '%Bonificacio%'
                AND g.concepto NOT LIKE '%Bonificación%'
                AND g.concepto NOT LIKE '%Devol%'
                AND g.concepto NOT LIKE '%Devolución%'
                AND (
                    substr(g.fecha_operacion, -4) = ?
                    OR strftime('%Y', g.fecha_operacion) = ?
                )
            '''
        else:
            # Si no existe la tabla, todos los gastos son pendientes (excepto liquidaciones, bonificaciones y devoluciones)
            query = '''
                SELECT g.*
                FROM gastos g
                WHERE g.importe_eur > 0
                AND g.concepto NOT LIKE '%Liquidacion Efectuada%'
                AND g.concepto NOT LIKE '%Bonificacio%'
                AND g.concepto NOT LIKE '%Bonificación%'
                AND g.concepto NOT LIKE '%Devol%'
                AND g.concepto NOT LIKE '%Devolución%'
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
        
        # Obtener liquidaciones TPV agrupadas por fecha extraída del concepto
        cursor.execute('''
            SELECT 
                MIN(c.id) as id,
                SUBSTR(g.concepto, INSTR(g.concepto, 'El ') + 3, 10) as fecha_operacion,
                'Liquidación TPV ' || SUBSTR(g.concepto, INSTR(g.concepto, 'El ') + 3, 10) as concepto_gasto,
                'liquidacion_tpv' as tipo_documento,
                COUNT(c.id) as num_liquidaciones,
                SUM(c.importe_gasto) as importe_gasto,
                SUM(c.importe_documento) as importe_documento,
                SUM(c.importe_gasto) - SUM(c.importe_documento) as diferencia,
                'conciliado' as estado,
                'automatico' as metodo,
                MAX(c.fecha_conciliacion) as fecha_conciliacion,
                GROUP_CONCAT(c.notas, ' | ') as notas
            FROM conciliacion_gastos c
            LEFT JOIN gastos g ON c.gasto_id = g.id
            WHERE c.estado = 'conciliado'
            AND c.tipo_documento = 'liquidacion_tpv'
            GROUP BY SUBSTR(g.concepto, INSTR(g.concepto, 'El ') + 3, 10)
            ORDER BY MAX(c.fecha_conciliacion) DESC
        ''')
        
        liquidaciones_agrupadas = [dict(row) for row in cursor.fetchall()]
        
        # Combinar ambas listas
        conciliaciones = conciliaciones_normales + liquidaciones_agrupadas
        
        # Ordenar por fecha de operación (más recientes primero)
        def get_fecha_sort(x):
            fecha = x.get('fecha_operacion', '')
            # Convertir formato DD/MM/YYYY a YYYY-MM-DD para ordenar correctamente
            if '/' in fecha:
                partes = fecha.split('/')
                if len(partes) == 3:
                    return f"{partes[2]}-{partes[1]}-{partes[0]}"
            return fecha
        
        conciliaciones.sort(key=get_fecha_sort, reverse=True)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'conciliaciones': conciliaciones,
            'total': len(conciliaciones)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@conciliacion_bp.route('/api/conciliacion/detalles/<int:gasto_id>', methods=['GET'])
def detalles_conciliacion(gasto_id):
    """Obtener detalles de los documentos que conciliaron un gasto"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener información del gasto
        cursor.execute('''
            SELECT id, fecha_operacion as fecha, concepto, importe_eur as importe
            FROM gastos
            WHERE id = ?
        ''', (gasto_id,))
        
        gasto_row = cursor.fetchone()
        if not gasto_row:
            conn.close()
            return jsonify({'success': False, 'error': 'Gasto no encontrado'}), 404
        
        gasto = dict(gasto_row)
        
        # Obtener información de la conciliación
        cursor.execute('''
            SELECT id, tipo_documento
            FROM conciliacion_gastos
            WHERE gasto_id = ? AND estado = 'conciliado'
            LIMIT 1
        ''', (gasto_id,))
        
        conciliacion_row = cursor.fetchone()
        if not conciliacion_row:
            conn.close()
            return jsonify({'success': False, 'error': 'Conciliación no encontrada'}), 404
        
        conciliacion_id = conciliacion_row['id']
        tipo_documento = conciliacion_row['tipo_documento']
        
        # Si es ingreso_efectivo, obtener documentos de la tabla intermedia
        if tipo_documento == 'ingreso_efectivo':
            cursor.execute('''
                SELECT 
                    cd.tipo_documento as tipo,
                    cd.documento_id,
                    cd.importe,
                    CASE 
                        WHEN cd.tipo_documento = 'factura' THEN f.numero
                        WHEN cd.tipo_documento = 'ticket' THEN t.numero
                    END as numero,
                    CASE 
                        WHEN cd.tipo_documento = 'factura' THEN COALESCE(f.fechaCobro, f.fecha)
                        WHEN cd.tipo_documento = 'ticket' THEN t.fecha
                    END as fecha
                FROM conciliacion_documentos cd
                LEFT JOIN factura f ON cd.tipo_documento = 'factura' AND cg.documento_id = f.id
                LEFT JOIN tickets t ON cd.tipo_documento = 'ticket' AND cg.documento_id = t.id
                WHERE cd.conciliacion_id = ?
                ORDER BY fecha, numero
            ''', (conciliacion_id,))
        else:
            # Para otros tipos, obtener de la forma tradicional
            cursor.execute('''
                SELECT 
                    c.tipo_documento as tipo,
                    c.documento_id,
                    c.importe_documento as importe,
                    CASE 
                        WHEN c.tipo_documento = 'factura' THEN f.numero
                        WHEN c.tipo_documento = 'ticket' THEN t.numero
                        WHEN c.tipo_documento = 'proforma' THEN p.numero
                    END as numero,
                    CASE 
                        WHEN c.tipo_documento = 'factura' THEN f.fecha
                        WHEN c.tipo_documento = 'ticket' THEN t.fecha
                        WHEN c.tipo_documento = 'proforma' THEN p.fecha
                    END as fecha
                FROM conciliacion_gastos c
                LEFT JOIN factura f ON c.tipo_documento = 'factura' AND c.documento_id = f.id
                LEFT JOIN tickets t ON c.tipo_documento = 'ticket' AND c.documento_id = t.id
                LEFT JOIN proforma p ON c.tipo_documento = 'proforma' AND c.documento_id = p.id
                WHERE c.gasto_id = ? AND c.estado = 'conciliado'
                ORDER BY c.fecha_conciliacion
            ''', (gasto_id,))
        
        documentos = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'gasto': gasto,
            'documentos': documentos
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@conciliacion_bp.route('/api/conciliacion/liquidacion-tpv-detalles', methods=['GET'])
def detalles_liquidacion_tpv():
    """Obtener detalles de una liquidación TPV agrupada por fecha"""
    try:
        fecha = request.args.get('fecha')
        if not fecha:
            return jsonify({'success': False, 'error': 'Fecha requerida'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Convertir fecha de DD/MM/YYYY a YYYY-MM-DD para buscar tickets
        partes_fecha = fecha.split('/')
        if len(partes_fecha) == 3:
            fecha_tickets = f"{partes_fecha[2]}-{partes_fecha[1]}-{partes_fecha[0]}"
        else:
            fecha_tickets = fecha
        
        # Obtener IDs de conciliaciones para esta fecha
        cursor.execute('''
            SELECT c.id
            FROM conciliacion_gastos c
            LEFT JOIN gastos g ON c.gasto_id = g.id
            WHERE c.tipo_documento = 'liquidacion_tpv'
            AND g.concepto LIKE '%El ' || ? || '%'
            AND c.estado = 'conciliado'
        ''', (fecha,))
        
        conciliacion_ids = [row['id'] for row in cursor.fetchall()]
        
        if not conciliacion_ids:
            # Si no hay conciliaciones, mostrar todos los documentos disponibles
            cursor.execute('''
                SELECT 
                    'ticket' as tipo,
                    t.numero as numero,
                    t.fecha as fecha,
                    t.total as importe
                FROM tickets t
                WHERE t.fecha = ?
                AND t.formaPago = 'T'
                ORDER BY t.numero
            ''', (fecha_tickets,))
            
            tickets = [dict(row) for row in cursor.fetchall()]
            total_tickets = sum(t['importe'] for t in tickets)
        else:
            # Obtener solo los tickets que están en conciliacion_documentos
            placeholders = ','.join('?' * len(conciliacion_ids))
            cursor.execute(f'''
                SELECT DISTINCT
                    'ticket' as tipo,
                    t.numero as numero,
                    t.fecha as fecha,
                    t.total as importe
                FROM tickets t
                INNER JOIN conciliacion_documentos cd ON cd.documento_id = t.id AND cd.tipo_documento = 'ticket'
                WHERE cd.conciliacion_id IN ({placeholders})
                ORDER BY t.numero
            ''', conciliacion_ids)
            
            tickets = [dict(row) for row in cursor.fetchall()]
            total_tickets = sum(t['importe'] for t in tickets)
        
        # Obtener el total de las liquidaciones bancarias de esa fecha desde la tabla gastos
        # Extraer fecha del concepto "Liquidacion Efectuada El DD/MM/YYYY"
        cursor.execute('''
            SELECT 
                SUM(importe_eur) as total_liquidaciones,
                COUNT(id) as num_liquidaciones
            FROM gastos
            WHERE concepto LIKE '%Liquidacion Efectuada%'
            AND concepto NOT LIKE '%Bonificacio%'
            AND concepto NOT LIKE '%Bonificación%'
            AND concepto NOT LIKE '%Devol%'
            AND concepto NOT LIKE '%Devolución%'
            AND concepto LIKE '%El ' || ? || '%'
        ''', (fecha,))
        
        liquidacion_info = cursor.fetchone()
        if liquidacion_info:
            liquidacion_info = dict(liquidacion_info)
        else:
            liquidacion_info = {'total_liquidaciones': 0, 'num_liquidaciones': 0}
        
        total_liquidaciones = liquidacion_info['total_liquidaciones'] or 0
        diferencia = total_liquidaciones - total_tickets
        
        # Buscar facturas TPV del mismo día
        if not conciliacion_ids:
            # Si no hay conciliaciones, mostrar todas las facturas disponibles
            cursor.execute('''
                SELECT 
                    'factura' as tipo,
                    f.numero as numero,
                    COALESCE(f.fechaCobro, f.fecha) as fecha,
                    f.total as importe
                FROM factura f
                WHERE COALESCE(f.fechaCobro, f.fecha) = ?
                AND f.formaPago = 'T'
                AND f.estado = 'C'
                ORDER BY f.numero
            ''', (fecha_tickets,))
            
            facturas = [dict(row) for row in cursor.fetchall()]
            total_facturas = sum(f['importe'] for f in facturas)
        else:
            # Obtener solo las facturas que están en conciliacion_documentos
            cursor.execute(f'''
                SELECT DISTINCT
                    'factura' as tipo,
                    f.numero as numero,
                    COALESCE(f.fechaCobro, f.fecha) as fecha,
                    f.total as importe
                FROM factura f
                INNER JOIN conciliacion_documentos cd ON cd.documento_id = f.id AND cd.tipo_documento = 'factura'
                WHERE cd.conciliacion_id IN ({placeholders})
                ORDER BY f.numero
            ''', conciliacion_ids)
            
            facturas = [dict(row) for row in cursor.fetchall()]
            total_facturas = sum(f['importe'] for f in facturas)
        
        # Recalcular diferencia incluyendo facturas del día
        diferencia = total_liquidaciones - (total_tickets + total_facturas)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'tickets': tickets,
            'facturas': facturas,
            'liquidacion_info': liquidacion_info,
            'diferencia': diferencia,
            'fecha': fecha
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
        
        # Obtener todas las liquidaciones TPV
        # Filtro específico: "Liquidacion Efectuada" pero NO "Bonificacion" ni "Devolucion"
        cursor.execute('''
            SELECT 
                id,
                fecha_operacion,
                concepto,
                importe_eur
            FROM gastos
            WHERE concepto LIKE '%Liquidacion Efectuada%'
            AND concepto NOT LIKE '%Bonificacio%'
            AND concepto NOT LIKE '%Bonificación%'
            AND concepto NOT LIKE '%Devol%'
            AND concepto NOT LIKE '%Devolución%'
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
            except Exception as e:
                logger.error(f"Error: {e}", exc_info=True)
                continue
            
            # Buscar tickets con tarjeta de esa fecha (excluir ya conciliados)
            cursor.execute('''
                SELECT 
                    COUNT(*) as num_tickets,
                    SUM(total) as total_tickets
                FROM tickets
                WHERE fecha = ?
                AND formaPago = 'T'
                AND estado = 'C'
                AND NOT EXISTS (
                    SELECT 1 FROM conciliacion_gastos cg
                    WHERE cg.tipo_documento = 'ticket'
                    AND cg.documento_id = id
                )
            ''', (fecha_busqueda,))
            
            tickets_info = cursor.fetchone()
            total_tickets = tickets_info['total_tickets'] or 0
            num_tickets = tickets_info['num_tickets'] or 0
            
            # Inicialmente solo contar tickets
            total_documentos = total_tickets
            num_documentos = num_tickets
            num_facturas = 0
            total_facturas = 0
            
            # Calcular diferencia inicial (solo con tickets)
            total_liq = datos['total']
            diferencia = total_liq - total_documentos
            porcentaje_diferencia = (abs(diferencia) / abs(total_liq) * 100) if total_liq != 0 else 0
            
            # Obtener tolerancia configurada
            tolerancia_config = get_tolerancia_conciliacion()
            
            # Determinar estado usando tolerancia dinámica
            if abs(diferencia) <= tolerancia_config:
                estado = 'exacto'
            elif porcentaje_diferencia <= 5:
                estado = 'aceptable'
            else:
                estado = 'revisar'
            
            # Lógica de conciliación
            puede_conciliar = False
            
            if abs(diferencia) <= tolerancia_config and num_documentos > 0:
                # Diferencia <= tolerancia con solo tickets → conciliar directamente
                puede_conciliar = True
            elif abs(diferencia) > tolerancia_config:
                # Diferencia > tolerancia → buscar facturas y usar algoritmo de varita mágica
                cursor.execute('''
                    SELECT id, numero, total
                    FROM factura
                    WHERE COALESCE(fechaCobro, fecha) = ?
                    AND formaPago = 'T'
                    AND estado = 'C'
                    AND NOT EXISTS (
                        SELECT 1 FROM conciliacion_gastos cg
                        WHERE cg.tipo_documento = 'factura' 
                        AND cg.documento_id = id
                    )
                ''', (fecha_busqueda,))
                
                facturas_disponibles = cursor.fetchall()
                
                if facturas_disponibles:
                    # Preparar lista de documentos para el algoritmo
                    documentos = []
                    # Agregar tickets existentes
                    cursor.execute('''
                        SELECT id, numero, total
                        FROM tickets
                        WHERE fecha = ? AND formaPago = 'T' AND estado = 'C'
                        AND NOT EXISTS (
                            SELECT 1 FROM conciliacion_gastos cg
                            WHERE cg.tipo_documento = 'ticket' AND cg.documento_id = id
                        )
                    ''', (fecha_busqueda,))
                    for ticket in cursor.fetchall():
                        documentos.append({'id': ticket['id'], 'tipo': 'ticket', 'importe': ticket['total']})
                    
                    # Agregar facturas disponibles
                    for factura in facturas_disponibles:
                        documentos.append({'id': factura['id'], 'tipo': 'factura', 'importe': factura['total']})
                    
                    # Usar algoritmo de varita mágica para encontrar mejor combinación
                    mejor_combinacion, mejor_diferencia = encontrar_mejor_combinacion_documentos(
                        documentos, total_liq, tolerancia_config
                    )
                    
                    if mejor_combinacion and mejor_diferencia is not None:
                        # Recalcular totales con la mejor combinación
                        total_documentos = 0
                        total_tickets = 0
                        total_facturas = 0
                        num_tickets = 0
                        num_facturas = 0
                        
                        for doc in mejor_combinacion:
                            total_documentos += doc['importe']
                            if doc['tipo'] == 'ticket':
                                total_tickets += doc['importe']
                                num_tickets += 1
                            else:
                                total_facturas += doc['importe']
                                num_facturas += 1
                        
                        num_documentos = num_tickets + num_facturas
                        diferencia = total_liq - total_documentos
                        puede_conciliar = True
            
            # Conciliación automática si diferencia <= tolerancia
            if puede_conciliar and abs(diferencia) <= tolerancia_config:
                try:
                    # Conciliar cada liquidación de esta fecha con algoritmo de varita mágica
                    for gasto_id in datos['ids']:
                        cursor.execute('SELECT importe_eur FROM gastos WHERE id = ?', (int(gasto_id),))
                        gasto_row = cursor.fetchone()
                        if gasto_row:
                            importe_gasto = gasto_row['importe_eur']
                            
                            notas_docs = f'{num_tickets} ticket(s)' if num_facturas == 0 else f'{num_tickets} ticket(s) + {num_facturas} factura(s)'
                            cursor.execute('''
                                INSERT OR IGNORE INTO conciliacion_gastos 
                                (gasto_id, tipo_documento, documento_id, fecha_conciliacion, 
                                 importe_gasto, importe_documento, diferencia, estado, metodo, notificado, notas)
                                VALUES (?, ?, ?, datetime('now'), ?, ?, ?, 'conciliado', 'automatico_tpv', 0, ?)
                            ''', (int(gasto_id), 'liquidacion_tpv', 0, 
                                  importe_gasto, total_documentos, diferencia,
                                  f'Liquidación TPV {fecha_str} - {notas_docs} - Dif: {round(diferencia, 2)}€'))
                    conn.commit()
                    logger.info(f"Liquidación TPV {fecha_str} conciliada automáticamente: {notas_docs}, dif={round(diferencia, 2)}€")
                    # No añadir a resultado si se concilió automáticamente
                    continue
                except Exception as e:
                    logger.error(f"Error conciliando automáticamente liquidación {fecha_str}: {e}", exc_info=True)
                    # Si falla, continuar y mostrar en la lista
            
            # Convertir -0.0 a 0.0
            diferencia_final = round(diferencia, 2)
            if diferencia_final == 0:
                diferencia_final = 0.0
            
            resultado.append({
                'fecha': fecha_str,
                'num_liquidaciones': datos['count'],
                'total_liquidaciones': round(total_liq, 2),
                'num_tickets': num_tickets,
                'num_facturas': num_facturas,
                'total_tickets': round(total_tickets, 2),
                'total_facturas': round(total_facturas, 2),
                'total_documentos': round(total_documentos, 2),
                'diferencia': diferencia_final,
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
    # Log al inicio del endpoint
    try:
        with open('/var/www/html/conciliacion_debug.log', 'a') as f:
            f.write(f"🔍 INICIO: Endpoint ingresos-efectivo llamado\n")
            f.flush()
    except Exception as e:
        pass  # Ignorar errores de log
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Filtrar solo año actual (formato DD/MM/YYYY)
        ano_actual = datetime.now().year
        
        # Obtener ingresos en efectivo del banco (case-insensitive, excluir Bizum)
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
            AND LOWER(concepto) NOT LIKE '%bizum%'
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
                
                # Buscar en rango de 15 días previos al ingreso
                fecha_inicio = (fecha_obj - timedelta(days=15)).strftime('%Y-%m-%d')
                fecha_fin = fecha_obj.strftime('%Y-%m-%d')
            except Exception as e:
                logger.error(f"Error: {e}", exc_info=True)
                continue
            
            # Buscar facturas cobradas en efectivo NO CONCILIADAS en el rango (usar fechaCobro)
            cursor.execute('''
                SELECT 
                    COUNT(*) as num_facturas,
                    SUM(f.total) as total_facturas
                FROM factura f
                WHERE COALESCE(f.fechaCobro, f.fecha) BETWEEN ? AND ?
                AND f.formaPago = 'E'
                AND f.estado = 'C'
                AND NOT EXISTS (
                    SELECT 1 FROM conciliacion_gastos cg
                    WHERE cg.tipo_documento = 'factura' AND cg.documento_id = f.id
                )
            ''', (fecha_inicio, fecha_fin))
            
            facturas_info = cursor.fetchone()
            total_facturas = facturas_info['total_facturas'] or 0
            num_facturas = facturas_info['num_facturas'] or 0
            
            # Buscar tickets con efectivo NO CONCILIADOS en el rango
            cursor.execute('''
                SELECT 
                    COUNT(*) as num_tickets,
                    SUM(t.total) as total_tickets
                FROM tickets t
                WHERE t.fecha BETWEEN ? AND ?
                AND t.formaPago = 'E'
                AND t.estado = 'C'
                AND NOT EXISTS (
                    SELECT 1 FROM conciliacion_gastos cg
                    WHERE cg.tipo_documento = 'ticket' AND cg.documento_id = t.id
                )
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
            tolerancia_config = get_tolerancia_conciliacion()
            
            # Determinar estado
            if diferencia <= tolerancia_config:
                estado = 'exacto'
            elif porcentaje_diferencia <= 5:
                estado = 'aceptable'
            else:
                estado = 'revisar'
            
            # Intentar encontrar mejor combinación de documentos
            # Obtener lista detallada de documentos NO CONCILIADOS
            cursor.execute('''
                SELECT f.id, f.numero, f.total as importe, 'factura' as tipo
                FROM factura f
                WHERE COALESCE(f.fechaCobro, f.fecha) BETWEEN ? AND ?
                AND f.formaPago = 'E'
                AND f.estado = 'C'
                AND NOT EXISTS (
                    SELECT 1 FROM conciliacion_gastos cg
                    WHERE cg.tipo_documento = 'factura' AND cg.documento_id = f.id
                )
            ''', (fecha_inicio, fecha_fin))
            facturas_lista = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute('''
                SELECT t.id, t.numero, t.total as importe, 'ticket' as tipo
                FROM tickets t
                WHERE t.fecha BETWEEN ? AND ?
                AND t.formaPago = 'E'
                AND t.estado = 'C'
                AND NOT EXISTS (
                    SELECT 1 FROM conciliacion_gastos cg
                    WHERE cg.tipo_documento = 'ticket' AND cg.documento_id = t.id
                )
            ''', (fecha_inicio, fecha_fin))
            tickets_lista = [dict(row) for row in cursor.fetchall()]
            
            # Combinar todos los documentos
            todos_documentos = facturas_lista + tickets_lista
            
            # Buscar mejor combinación
            with open('/var/www/html/conciliacion_debug.log', 'a') as f:
                f.write(f"🔍 Buscando combinación para {fecha_str}: {len(todos_documentos)} documentos disponibles, objetivo: {total_ing}€\n")
                f.flush()
            
            mejor_combinacion, diferencia_combinacion = encontrar_mejor_combinacion_documentos(
                todos_documentos, total_ing, tolerancia=1.0
            )
            
            with open('/var/www/html/conciliacion_debug.log', 'a') as f:
                if mejor_combinacion:
                    f.write(f"✅ Combinación encontrada: {len(mejor_combinacion)} docs, diferencia: {diferencia_combinacion}€\n")
                else:
                    f.write(f"❌ NO se encontró combinación válida para {fecha_str}\n")
                f.flush()
            
            # Conciliar automáticamente si se encontró combinación válida
            if mejor_combinacion and diferencia_combinacion is not None and diferencia_combinacion <= tolerancia_config:
                try:
                    # Calcular total de la combinación
                    total_combinacion = sum(doc['importe'] for doc in mejor_combinacion)
                    
                    # Log directo a archivo
                    with open('/var/www/html/conciliacion_debug.log', 'a') as f:
                        f.write(f"🔍 DEBUG: Conciliando ingreso {fecha_str}, {len(mejor_combinacion)} documentos, total: {total_combinacion}€\n")
                        f.flush()
                    
                    for gasto_id in datos['ids']:
                        cursor.execute('SELECT importe_eur FROM gastos WHERE id = ?', (int(gasto_id),))
                        gasto_row = cursor.fetchone()
                        if gasto_row:
                            importe_gasto = gasto_row['importe_eur']
                            
                            # Insertar conciliación principal
                            cursor.execute('''
                                INSERT INTO conciliacion_gastos 
                                (gasto_id, tipo_documento, documento_id, fecha_conciliacion, 
                                 importe_gasto, importe_documento, diferencia, estado, metodo, notificado, notas)
                                VALUES (?, ?, ?, datetime('now'), ?, ?, ?, 'conciliado', 'automatico', 0, ?)
                            ''', (int(gasto_id), 'ingreso_efectivo', 0, 
                                  importe_gasto, total_combinacion, diferencia_combinacion,
                                  f'Ingreso efectivo {fecha_str} - {len(mejor_combinacion)} documentos - Conciliado automáticamente (dif: {round(diferencia_combinacion, 2)}€)'))
                            
                            conciliacion_id = cursor.lastrowid
                            
                            with open('/var/www/html/conciliacion_debug.log', 'a') as f:
                                f.write(f"🔍 DEBUG: Conciliación insertada, ID: {conciliacion_id}, gasto_id: {gasto_id}\n")
                                f.flush()
                            
                            # Guardar cada documento de la combinación en tabla intermedia
                            if conciliacion_id and conciliacion_id > 0:
                                with open('/var/www/html/conciliacion_debug.log', 'a') as f:
                                    f.write(f"🔍 DEBUG: Guardando {len(mejor_combinacion)} documentos...\n")
                                    f.flush()
                                
                                for idx, doc in enumerate(mejor_combinacion):
                                    cursor.execute('''
                                        INSERT INTO conciliacion_documentos 
                                        (conciliacion_id, tipo_documento, documento_id, importe)
                                        VALUES (?, ?, ?, ?)
                                    ''', (conciliacion_id, doc['tipo'], doc['id'], doc['importe']))
                                    
                                    if idx < 3:  # Log solo primeros 3
                                        with open('/var/www/html/conciliacion_debug.log', 'a') as f:
                                            f.write(f"  - {doc['tipo']} ID {doc['id']}: {doc['importe']}€\n")
                                            f.flush()
                                
                                with open('/var/www/html/conciliacion_debug.log', 'a') as f:
                                    f.write(f"✅ DEBUG: {len(mejor_combinacion)} documentos guardados\n")
                                    f.flush()
                            else:
                                with open('/var/www/html/conciliacion_debug.log', 'a') as f:
                                    f.write(f"⚠️ Error: conciliacion_id inválido ({conciliacion_id}) para gasto {gasto_id}\n")
                                    f.flush()
                    
                    conn.commit()
                    with open('/var/www/html/conciliacion_debug.log', 'a') as f:
                        f.write(f"✅ DEBUG: Commit realizado para ingreso {fecha_str}\n")
                        f.flush()
                    continue
                except Exception as e:
                    with open('/var/www/html/conciliacion_debug.log', 'a') as f:
                        f.write(f"❌ Error conciliando automáticamente ingreso {fecha_str}: {e}\n")
                        import traceback
                        f.write(traceback.format_exc())
                        f.flush()
            
            # Convertir -0.0 a 0.0
            diferencia_final = round(diferencia, 2)
            if diferencia_final == 0:
                diferencia_final = 0.0
            
            resultado.append({
                'fecha': fecha_str,
                'num_ingresos': datos['count'],
                'total_ingresos': round(total_ing, 2),
                'num_facturas': num_facturas,
                'num_tickets': num_tickets,
                'total_facturas': round(total_facturas, 2),
                'total_tickets': round(total_tickets, 2),
                'total_documentos': round(total_documentos, 2),
                'diferencia': diferencia_final,
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

@conciliacion_bp.route('/api/conciliacion/documentos-efectivo', methods=['GET'])
def obtener_documentos_efectivo():
    """Obtener lista de facturas/tickets en efectivo disponibles para seleccionar"""
    try:
        fecha_ingreso = request.args.get('fecha')
        
        if not fecha_ingreso:
            return jsonify({'success': False, 'error': 'Falta parámetro fecha'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Convertir fecha a formato YYYY-MM-DD
        try:
            if '/' in fecha_ingreso:
                fecha_obj = datetime.strptime(fecha_ingreso, '%d/%m/%Y')
            else:
                fecha_obj = datetime.strptime(fecha_ingreso, '%Y-%m-%d')
            
            fecha_fin = fecha_obj.strftime('%Y-%m-%d')
            fecha_inicio = (fecha_obj - timedelta(days=15)).strftime('%Y-%m-%d')
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            return jsonify({'success': False, 'error': 'Formato de fecha inválido'}), 400
        
        # Obtener facturas cobradas en efectivo con nombre del cliente (usar fechaCobro, excluir ya conciliadas)
        cursor.execute('''
            SELECT 
                'factura' as tipo,
                f.id,
                f.numero,
                COALESCE(f.fechaCobro, f.fecha) as fecha,
                f.total,
                COALESCE(c.razonsocial, '') as cliente
            FROM factura f
            LEFT JOIN contactos c ON f.idContacto = c.idContacto
            WHERE COALESCE(f.fechaCobro, f.fecha) BETWEEN ? AND ?
            AND f.formaPago = 'E'
            AND f.estado = 'C'
            AND NOT EXISTS (
                SELECT 1 FROM conciliacion_gastos cg
                WHERE cg.tipo_documento = 'factura' 
                AND cg.documento_id = f.id
            )
            ORDER BY COALESCE(f.fechaCobro, f.fecha) DESC, f.numero DESC
        ''', (fecha_inicio, fecha_fin))
        
        facturas = [dict(row) for row in cursor.fetchall()]
        
        # Obtener tickets en efectivo (excluir ya conciliados)
        cursor.execute('''
            SELECT 
                'ticket' as tipo,
                id,
                numero,
                fecha,
                total,
                '' as cliente
            FROM tickets
            WHERE fecha BETWEEN ? AND ?
            AND formaPago = 'E'
            AND estado = 'C'
            AND NOT EXISTS (
                SELECT 1 FROM conciliacion_gastos cg
                WHERE cg.tipo_documento = 'ticket' 
                AND cg.documento_id = id
            )
            ORDER BY fecha DESC, numero DESC
        ''', (fecha_inicio, fecha_fin))
        
        tickets = [dict(row) for row in cursor.fetchall()]
        
        # Combinar y ordenar por fecha
        documentos = facturas + tickets
        documentos.sort(key=lambda x: (x['fecha'], x['numero']), reverse=True)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'documentos': documentos,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@conciliacion_bp.route('/api/conciliacion/conciliar-ingreso-efectivo', methods=['POST'])
def conciliar_ingreso_efectivo():
    """Conciliar un ingreso en efectivo con facturas/tickets seleccionados"""
    try:
        data = request.json
        ids_gastos = data.get('ids_gastos', '').split(',')
        fecha = data.get('fecha')
        documentos_seleccionados = data.get('documentos_seleccionados', [])
        
        if not ids_gastos or not fecha:
            return jsonify({'success': False, 'error': 'Faltan parámetros'}), 400
        
        if not documentos_seleccionados:
            return jsonify({'success': False, 'error': 'No hay documentos seleccionados'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Calcular total de documentos seleccionados
        total_documentos = sum(doc['total'] for doc in documentos_seleccionados)
        num_facturas = sum(1 for doc in documentos_seleccionados if doc['tipo'] == 'factura')
        num_tickets = sum(1 for doc in documentos_seleccionados if doc['tipo'] == 'ticket')
        
        conciliados = 0
        
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
                # Crear lista de números de documentos para las notas
                nums_docs = ', '.join([f"{doc['tipo'][0].upper()}{doc['numero']}" for doc in documentos_seleccionados])
                
                cursor.execute('''
                    INSERT INTO conciliacion_gastos 
                    (gasto_id, tipo_documento, documento_id, fecha_conciliacion, 
                     importe_gasto, importe_documento, diferencia, estado, metodo, notificado, notas)
                    VALUES (?, ?, ?, datetime('now'), ?, ?, ?, 'conciliado', 'manual', 0, ?)
                ''', (int(gasto_id), 'ingreso_efectivo', 0, 
                      importe_gasto, total_documentos, diferencia,
                      f'Ingreso efectivo {fecha} - {len(documentos_seleccionados)} docs ({num_facturas}F, {num_tickets}T): {nums_docs}'))
                
                conciliacion_id = cursor.lastrowid
                
                # Guardar cada documento en la tabla intermedia
                if conciliacion_id and conciliacion_id > 0:
                    for doc in documentos_seleccionados:
                        cursor.execute('''
                            INSERT INTO conciliacion_documentos 
                            (conciliacion_id, tipo_documento, documento_id, importe)
                            VALUES (?, ?, ?, ?)
                        ''', (conciliacion_id, doc['tipo'], doc['id'], doc['total']))
                    conciliados += 1
            except Exception as e:
                logger.error(f"Error conciliando ingreso {gasto_id}: {e}", exc_info=True)
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
        fecha = data.get('fecha')
        documentos = data.get('documentos', [])  # Para varita mágica
        ids_gastos_str = data.get('ids_gastos', '')  # Para conciliación manual
        
        if not fecha:
            return jsonify({'success': False, 'error': 'Fecha requerida'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Convertir fecha a formato YYYY-MM-DD
        try:
            if '/' in fecha:
                fecha_obj = datetime.strptime(fecha, '%d/%m/%Y')
            else:
                fecha_obj = datetime.strptime(fecha, '%Y-%m-%d')
            fecha_busqueda = fecha_obj.strftime('%Y-%m-%d')
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            return jsonify({'success': False, 'error': 'Formato de fecha inválido'}), 400
        
        # Obtener IDs de liquidaciones bancarias de esa fecha
        if ids_gastos_str:
            ids_gastos = ids_gastos_str.split(',')
        else:
            # Buscar liquidaciones por fecha en el concepto
            cursor.execute('''
                SELECT id
                FROM gastos
                WHERE concepto LIKE '%Liquidacion Efectuada%'
                AND concepto NOT LIKE '%Bonificacio%'
                AND concepto NOT LIKE '%Bonificación%'
                AND concepto NOT LIKE '%Devol%'
                AND concepto NOT LIKE '%Devolución%'
                AND concepto LIKE '%El ' || ? || '%'
            ''', (fecha,))
            ids_gastos = [str(row['id']) for row in cursor.fetchall()]
        
        if not ids_gastos:
            conn.close()
            return jsonify({'success': False, 'error': 'No se encontraron liquidaciones para esa fecha'}), 400
        
        if not documentos:
            conn.close()
            return jsonify({'success': False, 'error': 'No se proporcionaron documentos'}), 400
        
        # Calcular total de documentos y total de liquidaciones
        total_documentos = sum(float(doc.get('importe', 0)) for doc in documentos)
        
        # Calcular total de todas las liquidaciones
        total_liquidaciones = 0
        for gasto_id in ids_gastos:
            if gasto_id.strip():
                cursor.execute('SELECT importe_eur FROM gastos WHERE id = ?', (int(gasto_id),))
                gasto_row = cursor.fetchone()
                if gasto_row:
                    total_liquidaciones += gasto_row['importe_eur']
        
        diferencia_total = total_liquidaciones - total_documentos
        
        # Verificar si alguna ya está conciliada
        conciliados = 0
        todos_ya_conciliados = True
        
        for gasto_id in ids_gastos:
            if not gasto_id.strip():
                continue
            
            cursor.execute('SELECT id FROM conciliacion_gastos WHERE gasto_id = ? AND estado = "conciliado"', (int(gasto_id),))
            if cursor.fetchone():
                continue
            
            todos_ya_conciliados = False
            break
        
        if todos_ya_conciliados:
            conn.close()
            return jsonify({
                'success': True,
                'conciliados': 0,
                'todos_ya_conciliados': True,
                'mensaje': 'Todas las liquidaciones ya estaban conciliadas'
            })
        
        # Crear UNA SOLA conciliación para todas las liquidaciones de esta fecha
        # Esto evita duplicar documentos cuando hay múltiples liquidaciones
        try:
            # Crear una conciliación por cada liquidación individual
            for gasto_id in ids_gastos:
                if not gasto_id.strip():
                    continue
                
                # Verificar si ya está conciliado
                cursor.execute('SELECT id FROM conciliacion_gastos WHERE gasto_id = ? AND estado = "conciliado"', (int(gasto_id),))
                if cursor.fetchone():
                    continue
                
                # Obtener el importe del gasto individual
                cursor.execute('SELECT importe_eur FROM gastos WHERE id = ?', (int(gasto_id),))
                gasto_row = cursor.fetchone()
                if not gasto_row:
                    continue
                
                importe_gasto = gasto_row['importe_eur']
                
                # Crear entrada de conciliación (sin documentos individuales, se comparten)
                cursor.execute('''
                    INSERT INTO conciliacion_gastos 
                    (gasto_id, tipo_documento, documento_id, fecha_conciliacion, 
                     importe_gasto, importe_documento, diferencia, estado, metodo, notificado, notas)
                    VALUES (?, ?, ?, datetime('now'), ?, ?, ?, 'conciliado', 'automatico', 0, ?)
                ''', (int(gasto_id), 'liquidacion_tpv', 0, 
                      importe_gasto, 0,  # importe_documento = 0 para cada liquidación individual
                      0,  # diferencia = 0 para cada liquidación individual
                      f'Liquidación TPV {fecha} - Parte de grupo con {len(documentos)} documentos'))
                
                conciliacion_id = cursor.lastrowid
                conciliados += 1
                
                # Solo la PRIMERA liquidación registra los documentos
                if conciliados == 1:
                    # Registrar los documentos una sola vez
                    for doc in documentos:
                        cursor.execute('''
                            INSERT OR IGNORE INTO conciliacion_documentos 
                            (conciliacion_id, tipo_documento, documento_id, importe)
                            VALUES (?, ?, ?, ?)
                        ''', (conciliacion_id, doc['tipo'], int(doc['id']), float(doc.get('importe', 0))))
                    
                    # Actualizar la primera conciliación con el total de documentos y diferencia real
                    cursor.execute('''
                        UPDATE conciliacion_gastos 
                        SET importe_documento = ?, diferencia = ?, notas = ?
                        WHERE id = ?
                    ''', (total_documentos, diferencia_total, 
                          f'Liquidación TPV {fecha} - {len(ids_gastos)} liquidaciones, {len(documentos)} documentos',
                          conciliacion_id))
        except Exception as e:
            logger.error(f"Error conciliando liquidaciones: {e}", exc_info=True)
            conn.close()
            return jsonify({'success': False, 'error': str(e)}), 500
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'conciliados': conciliados,
            'todos_ya_conciliados': todos_ya_conciliados,
            'mensaje': f'Liquidación conciliada: {conciliados} registros'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@conciliacion_bp.route('/api/conciliacion/documentos_tarjeta', methods=['GET'])
def obtener_documentos_tarjeta():
    """Obtener lista de facturas/tickets con tarjeta disponibles para una fecha (rango de 30 días)"""
    try:
        fecha_liquidacion = request.args.get('fecha')
        if not fecha_liquidacion:
            return jsonify({'success': False, 'error': 'Fecha requerida'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Convertir fecha a formato YYYY-MM-DD
        try:
            if '/' in fecha_liquidacion:
                fecha_obj = datetime.strptime(fecha_liquidacion, '%d/%m/%Y')
            else:
                fecha_obj = datetime.strptime(fecha_liquidacion, '%Y-%m-%d')
            
            fecha_fin = fecha_obj.strftime('%Y-%m-%d')
            # Para liquidaciones TPV: buscar SOLO documentos de la fecha exacta
            # Esto evita que liquidaciones antiguas usen documentos de fechas futuras
            fecha_inicio = fecha_fin
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            return jsonify({'success': False, 'error': 'Formato de fecha inválido'}), 400
        
        # Obtener facturas cobradas con tarjeta en el rango (usar fechaCobro, excluir ya conciliadas)
        # El algoritmo de varita mágica encontrará la combinación exacta
        cursor.execute('''
            SELECT
                'factura' as tipo,
                f.id,
                f.numero,
                COALESCE(f.fechaCobro, f.fecha) as fecha,
                f.total as importe,
                COALESCE(c.razonsocial, '') as cliente
            FROM factura f
            LEFT JOIN contactos c ON f.idContacto = c.idContacto
            WHERE COALESCE(f.fechaCobro, f.fecha) BETWEEN ? AND ?
            AND f.formaPago = 'T'
            AND f.estado = 'C'
            AND NOT EXISTS (
                SELECT 1 FROM conciliacion_gastos cg
                WHERE cg.tipo_documento = 'factura'
                AND cg.documento_id = f.id
            )
            ORDER BY COALESCE(f.fechaCobro, f.fecha) DESC, f.numero DESC
        ''', (fecha_inicio, fecha_fin))
        
        facturas = [dict(row) for row in cursor.fetchall()]
        
        # Obtener tickets con tarjeta en el rango (excluir ya conciliados)
        cursor.execute('''
            SELECT
                'ticket' as tipo,
                t.id,
                t.numero,
                t.fecha,
                t.total as importe,
                '' as cliente
            FROM tickets t
            WHERE t.fecha BETWEEN ? AND ?
            AND t.formaPago = 'T'
            AND t.estado = 'C'
            AND NOT EXISTS (
                SELECT 1 FROM conciliacion_gastos cg
                WHERE cg.tipo_documento = 'ticket'
                AND cg.documento_id = t.id
            )
            ORDER BY t.fecha DESC, t.numero DESC
        ''', (fecha_inicio, fecha_fin))
        
        tickets = [dict(row) for row in cursor.fetchall()]
        
        # Combinar ambas listas
        documentos = facturas + tickets
        
        # Ordenar por fecha (más recientes primero)
        documentos.sort(key=lambda x: x['fecha'], reverse=True)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'documentos': documentos,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# CONFIGURACIÓN - ENDPOINTS API
# ============================================================================

@conciliacion_bp.route('/api/conciliacion/config/tolerancia', methods=['GET'])
def get_config_tolerancia():
    """Obtener configuración de tolerancia de conciliación"""
    try:
        tolerancia = get_tolerancia_conciliacion()
        return jsonify({
            'success': True,
            'tolerancia': tolerancia
        })
    except Exception as e:
        logger.error(f"Error obteniendo tolerancia: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@conciliacion_bp.route('/api/conciliacion/config/tolerancia', methods=['POST'])
def update_config_tolerancia():
    """Actualizar configuración de tolerancia de conciliación"""
    try:
        data = request.get_json()
        nueva_tolerancia = data.get('tolerancia')
        
        if nueva_tolerancia is None:
            return jsonify({'success': False, 'error': 'Falta parámetro tolerancia'}), 400
        
        # Validar rango razonable
        if nueva_tolerancia < 0 or nueva_tolerancia > 100:
            return jsonify({'success': False, 'error': 'Tolerancia debe estar entre 0 y 100 euros'}), 400
        
        # Actualizar tolerancia (crea archivo si no existe)
        set_tolerancia_conciliacion(nueva_tolerancia)
        
        logger.info(f"Tolerancia de conciliación actualizada a {nueva_tolerancia}€")
        
        return jsonify({
            'success': True,
            'message': f'Tolerancia actualizada a {nueva_tolerancia}€',
            'tolerancia': nueva_tolerancia
        })
    except Exception as e:
        logger.error(f"Error actualizando tolerancia: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

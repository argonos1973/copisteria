import sqlite3
from datetime import datetime

from flask import jsonify, session
from logger_config import get_logger
from constantes import DB_NAME
from database_pool import get_database_pool

# Inicializar logger
logger = get_logger(__name__)


def get_db_connection():
    """
    Crea y retorna una conexión a la base de datos SQLite.
    En sistema multiempresa, SIEMPRE usa la BD de la empresa activa en sesión.
    Si no hay sesión activa, lanza un error claro.
    La conexión usa Row como row_factory para acceder a las columnas por nombre.
    """
    try:
        db_path = None
        
        # Obtener BD de sesión (OBLIGATORIO en sistema multiempresa)
        try:
            from flask import has_request_context
            if has_request_context() and 'empresa_db' in session:
                db_path = session['empresa_db']
                logger.debug(f"[MULTIEMPRESA] Usando BD de empresa: {db_path}")
            elif has_request_context():
                # Contexto de petición pero sin empresa_db en sesión - usar BD por defecto
                logger.warning("[MULTIEMPRESA] No hay empresa_db en sesión, usando BD por defecto")
                db_path = DB_NAME
            else:
                logger.warning("[MULTIEMPRESA] No hay contexto de petición disponible")
        except ImportError:
            logger.warning("[MULTIEMPRESA] Flask no disponible, usando BD por defecto")
        
        if not db_path:
            db_path = DB_NAME
            logger.info(f"Usando BD por defecto: {db_path}")
        
        # Temporalmente deshabilitado el pool mientras se soluciona
        # pool = get_database_pool(db_path)
        # return pool.get_connection().connection
        
        # Conexión directa como antes
        conn = sqlite3.connect(db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA encoding="UTF-8"')
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn
        
    except Exception as e:
        logger.error(f"Error al conectar a la base de datos: {str(e)}", exc_info=True)
        raise

def get_db_connection_pooled():
    """
    Context manager que usa el pool de conexiones automáticamente
    
    Usage:
        with get_db_connection_pooled() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM table")
    """
    db_path = None
    
    # Determinar DB path (mismo código que get_db_connection)
    if 'empresa_seleccionada' in session:
        empresa = session['empresa_seleccionada']
        db_path = f"db/{empresa}/{empresa}.db"
    else:
        from flask import request
        if request and hasattr(request, 'headers'):
            empresa_header = request.headers.get('X-Empresa-DB')
            if empresa_header:
                db_path = f"db/{empresa_header}/{empresa_header}.db"
    
    if not db_path:
        db_path = DB_NAME
    
    # Usar pool con context manager
    pool = get_database_pool(db_path)
    return pool.get_db_connection()

# =====================================================
# FUNCIONES REFACTORIZADAS - CÓDIGO UNIFICADO
# =====================================================

def verificar_numero_documento(tipo_documento, numero):
    """
    Función unificada para verificar números de documento.
    Reemplaza verificar_numero_factura() y verificar_numero_proforma()
    
    Args:
        tipo_documento (str): 'factura', 'proforma', 'ticket'
        numero (str): Número del documento
    
    Returns:
        JSON response con existe e id
    """
    TABLAS = {'factura': 'factura', 'proforma': 'proforma', 'ticket': 'tickets'}
    
    if tipo_documento not in TABLAS:
        return jsonify({'error': 'Tipo documento inválido'}), 400
    
    conn = None
    try:
        logger.info(f"Verificando número de {tipo_documento}: {numero}")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        tabla = TABLAS[tipo_documento]
        cursor.execute(f'SELECT id FROM {tabla} WHERE numero = ?', (numero,))
        documento = cursor.fetchone()
        
        if documento:
            doc_id = documento['id'] if hasattr(documento, 'keys') else documento[0]
            return jsonify({'existe': True, 'id': doc_id})
        
        return jsonify({'existe': False, 'id': None})
    
    except Exception as e:
        logger.error(f"Error verificando {tipo_documento}: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()
            logger.info(f"Conexión cerrada en verificar_numero_{tipo_documento}")


def transformar_fecha_ddmmyyyy_a_iso(fecha_str):
    """
    Convierte DD/MM/YYYY a YYYY-MM-DD
    Función unificada para transformaciones de fecha
    """
    if not fecha_str or len(fecha_str) != 10:
        return None
    
    try:
        partes = fecha_str.split('/')
        if len(partes) == 3:
            dia, mes, año = partes
            return f"{año}-{mes.zfill(2)}-{dia.zfill(2)}"
    except:
        pass
    return None


# Funciones legacy (mantener compatibilidad)
def verificar_numero_proforma(numero):
    """DEPRECATED: Usar verificar_numero_documento('proforma', numero)"""
    return verificar_numero_documento('proforma', numero)


def verificar_numero_factura(numero):
    """DEPRECATED: Usar verificar_numero_documento('factura', numero)"""  
    return verificar_numero_documento('factura', numero)


def redondear_importe(valor):
    """
    Redondea un importe a 2 decimales usando ROUND_HALF_UP.
    Acepta números, cadenas numéricas, None o cadenas vacías.
    Si el valor no es convertible, devuelve 0.0.

    Args:
        valor (float | str | None): Valor a redondear.
    Returns:
        float: Valor redondeado a 2 decimales.
    """
    # Importar desde format_utils para mantener consistencia
    from format_utils import redondear_importe as _redondear
    return _redondear(valor)



def actualizar_numerador(tipo, conn=None, commit=True):
    debe_cerrar = False
    try:
        if conn is None:
            conn = get_db_connection()
            debe_cerrar = True
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")
        else:
            cursor = conn.cursor()
        
        ejercicio = datetime.now().year
        
        # Actualizar con una única consulta
        cursor.execute("""
            UPDATE numerador 
            SET numerador = numerador + 1 
            WHERE tipo = ? AND ejercicio = ? 
            RETURNING numerador
        """, (tipo, ejercicio))
        
        resultado = cursor.fetchone()
        
        if commit and debe_cerrar:
            conn.commit()
            
        if resultado:
            return resultado[0], resultado[0] + 1
        return None, None
        
    except Exception as e:
        if conn and debe_cerrar:
            conn.rollback()
        logger.error(f"Error en actualizar_numerador: {str(e)}", exc_info=True)
        raise
    finally:
        if debe_cerrar and conn:
            conn.close()

def obtener_numerador(tipoNum, conn=None):
    debe_cerrar = False
    try:
        if conn is None:
            conn = get_db_connection()
            debe_cerrar = True
        
        ejercicio = datetime.now().year
        cursor = conn.cursor()

        # Usar IMMEDIATE para prevenir bloqueos
        if debe_cerrar:
            cursor.execute("BEGIN IMMEDIATE")

        cursor.execute("SELECT numerador FROM numerador WHERE tipo = ? AND ejercicio = ?", (tipoNum, ejercicio))
        resultado = cursor.fetchone()

        if not resultado:
            return None, None

        numerador = resultado[0]
        # Usar el tipo como prefijo por defecto
        prefijo = tipoNum
        return numerador, prefijo
    except Exception as e:
        logger.error(f"Error en obtener_numerador: {str(e)}", exc_info=True)
        if conn and debe_cerrar:
            conn.rollback()
        raise
    finally:
        if debe_cerrar and conn:
            conn.close()

def formatear_numero_documento(tipo, conn=None):
    """
    Obtiene y formatea el número de documento (proforma, factura, ticket) con el formato:
    [TIPO][AÑO][NUMERO] - Ejemplo: F2500001, P2500002, T2500003
    
    Args:
        tipo (str): Tipo de documento ('F' para facturas, 'P' para proformas, 'T' para tickets)
        conn (Connection, optional): Conexión a la base de datos. Si es None, se crea una nueva.
        
    Returns:
        str: Número formateado o None si hay error
    """
    try:
        numerador, _ = obtener_numerador(tipo, conn)
        
        if numerador is None:
            return None
        
        # Formatear el número: numerador con cero a la izquierda (4 dígitos)
        numero_formateado = f"{int(numerador):04}"
        
        return numero_formateado
    except Exception as e:
        logger.error(f"Error en formatear_numero_documento: {str(e)}", exc_info=True)
        return None

# ------------------- Optimización: creación de índices ------------------- #

def ensure_gastos_indices():
    """Crea índices útiles para acelerar filtros y ordenación en la tabla gastos."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Índice por año+mes+día de fecha_valor para ordenar y filtrar rápido
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_gastos_fecha_valor_iso
            ON gastos (date(substr(fecha_valor,7,4)||'-'||substr(fecha_valor,4,2)||'-'||substr(fecha_valor,1,2)))
            """
        )
        # Índice por concepto en minúsculas para acelerar LIKE '%texto%'
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_gastos_concepto_lower
            ON gastos (lower(concepto))
            """
        )
        conn.commit()
    except Exception as e:
        logger.info(f"[DB_UTILS] Error al crear índices de gastos: {e}")
    finally:
        try:
            conn.close()
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            pass

def ensure_factura_indices():
    """
    Crea índices que optimizan las consultas más frecuentes sobre la tabla
    factura. Se ejecuta en cada arranque, pero usa CREATE INDEX IF NOT EXISTS
    por lo que no impacta si los índices ya existen.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Índice simple por estado
        cur.execute("CREATE INDEX IF NOT EXISTS FACTURA_ESTADO ON factura (estado)")
        # Índice compuesto estado + fecha para consultas con ambos filtros
        cur.execute("CREATE INDEX IF NOT EXISTS FACTURA_ESTADO_FECHA ON factura (estado, fecha)")
        conn.commit()
    except Exception as e:
        logger.info(f"[DB_UTILS] Error al crear índices: {e}")
    finally:
        try:
            conn.close()
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            pass

# Ejecutar al importar el módulo para garantizar que existan
ensure_factura_indices()
ensure_gastos_indices()
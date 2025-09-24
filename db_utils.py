import sqlite3
from datetime import datetime

from flask import jsonify

from constantes import DB_NAME


def get_db_connection():
    """
    Crea y retorna una conexión a la base de datos SQLite.
    La conexión usa Row como row_factory para acceder a las columnas por nombre.
    """
    try:
        conn = sqlite3.connect(DB_NAME, timeout=30)  # Aumentar timeout
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA encoding="UTF-8"')  # Asegura UTF-8
        conn.execute("PRAGMA journal_mode=WAL;") 
        return conn
    except Exception as e:
        print(f"Error al conectar a la base de datos: {str(e)}")
        raise

def verificar_numero_proforma(numero):
    try:
        print(f"Verificando número de proforma: {numero}")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Buscar proforma con el mismo número
        cursor.execute('SELECT id FROM proforma WHERE numero = ?', (numero,))
        proforma = cursor.fetchone()
        
        if proforma:
            return jsonify({
                'existe': True,
                'id': proforma['id']
            })
        
        return jsonify({
            'existe': False,
            'id': None
        })
    
    except Exception as e:
        print(f"Error al verificar número de proforma: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()
            print("Conexión cerrada en verificar_numero_proforma")


def verificar_numero_factura(numero):
    try:
        print(f"Verificando número de factura: {numero}")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Buscar factura con el mismo número
        cursor.execute('SELECT id FROM factura WHERE numero = ?', (numero,))
        factura = cursor.fetchone()
        
        if factura:
            return jsonify({
                'existe': True,
                'id': factura[0]
            })
        
        return jsonify({
            'existe': False,
            'id': None
        })
    
    except Exception as e:
        print(f"Error al verificar número de proforma: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()
            print("Conexión cerrada en verificar_numero_proforma")


def redondear_importe(valor):
    """
    Redondea un importe a 5 decimales para precios base, 2 decimales para totales.
    Acepta números, cadenas numéricas, None o cadenas vacías.
    Si el valor no es convertible a float, devuelve 0.0 en su lugar.

    Args:
        valor (float | str | None): Valor a redondear.
    Returns:
        float: Valor redondeado a 5 decimales.
    """
    # Tratar None o cadenas vacías como 0
    if valor is None or (isinstance(valor, str) and valor.strip() == ""):
        return 0.0
    try:
        return round(float(valor), 5)
    except (ValueError, TypeError):
        return 0.0



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
        print(f"Error en actualizar_numerador: {str(e)}")
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
        print(f"Error en obtener_numerador: {str(e)}")
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
        print(f"Error en formatear_numero_documento: {str(e)}")
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
        print(f"[DB_UTILS] Error al crear índices de gastos: {e}")
    finally:
        try:
            conn.close()
        except:
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
        print(f"[DB_UTILS] Error al crear índices: {e}")
    finally:
        try:
            conn.close()
        except:
            pass

# Ejecutar al importar el módulo para garantizar que existan
ensure_factura_indices()
ensure_gastos_indices()
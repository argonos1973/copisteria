import sqlite3
from functools import lru_cache

from constantes import *
from db_utils import get_db_connection, redondear_importe
from flask import jsonify, request
from logger_config import get_productos_logger

# Inicializar logger
logger = get_productos_logger()


def obtener_productos():
    """
    Obtiene todos los productos ordenados por nombre.
    
    Returns:
        list: Lista de diccionarios con los datos de los productos.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT *, 
                       calculo_automatico, franja_inicial, numero_franjas, 
                       ancho_franja, descuento_inicial, incremento_franja, no_generar_franjas
                FROM productos 
                ORDER BY nombre ASC
            ''')
            productos = cursor.fetchall()
            
            return [dict(producto) for producto in productos]
        
    except sqlite3.Error as e:
        logger.error(f"Error de base de datos al obtener productos: {str(e)}", exc_info=True)
        raise Exception("Error al obtener los productos de la base de datos")
    except Exception as e:
        logger.error(f"Error inesperado al obtener productos: {str(e)}", exc_info=True)
        raise Exception("Error inesperado al obtener los productos")


def aplicar_franjas_a_todos(ancho: int = 10, max_unidades: int = 500, descuento_max: float = 60.0):
    """
    Genera e inserta franjas de descuento para TODOS los productos existentes.
    - Bandas de `ancho` unidades (por defecto 10) hasta cubrir `max_unidades` (por defecto 500).
    - Descuento máximo `descuento_max` (por defecto 60%).
    - Garantiza que el precio total (con IVA) sea estrictamente decreciente entre franjas.

    Retorna dict con resumen.
    """
    if ancho < 1:
        ancho = 10
    if max_unidades < ancho:
        max_unidades = ancho
    if descuento_max < 0:
        descuento_max = 0.0
    if descuento_max > 60.0:
        descuento_max = 60.0

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Obtener todos los productos con sus valores base
        cur.execute('SELECT id, subtotal, impuestos FROM productos ORDER BY id ASC')
        productos_rows = cur.fetchall()

        total = 0
        afectados = 0
        errores = []

        # Calcular número de bandas necesarias
        import math
        num_bandas = int(math.ceil(max_unidades / float(ancho)))
        if num_bandas < 1:
            num_bandas = 1

        # Plan de descuentos lineal desde 0 hasta descuento_max en num_bandas-1 pasos
        descuento_inicial = 0.0
        incremento = (float(descuento_max) - descuento_inicial) / max(1, (num_bandas - 1))

        ensure_tabla_descuentos_bandas()

        for row in productos_rows:
            try:
                producto_id = int(row['id'] if isinstance(row, sqlite3.Row) else row[0])
                base_subtotal = float(row['subtotal'] if isinstance(row, sqlite3.Row) else row[1])
                iva_pct = float(row['impuestos'] if isinstance(row, sqlite3.Row) else row[2])

                franjas_cfg = {
                    'bandas': num_bandas,
                    'ancho': ancho,
                    'descuento_inicial': descuento_inicial,
                    'incremento': incremento
                }
                franjas = _generar_franjas_automaticas(base_subtotal, iva_pct, franjas_cfg)
                reemplazar_franjas_descuento_producto(producto_id, franjas)
                afectados += 1
            except Exception as e_prod:
                errores.append({'producto_id': row['id'] if isinstance(row, sqlite3.Row) else row[0], 'error': str(e_prod)})
            finally:
                total += 1

        return {
            'success': True,
            'procesados': total,
            'actualizados': afectados,
            'errores': errores
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}
    finally:
        if 'conn' in locals():
            conn.close()

def _generar_franjas_automaticas(base_subtotal: float, iva_pct: float, franjas_cfg: dict):
    """
    Genera las franjas automáticas respetando parámetros enviados por el frontend.
    franjas_cfg keys esperadas: bandas, ancho, descuento_inicial, incremento
    Devuelve lista de dicts [{min, max, descuento}]
    """
    # Normalización de parámetros
    bandas_val = franjas_cfg.get('bandas')
    num_bandas = int(bandas_val) if bandas_val is not None else 3
    ancho_val = franjas_cfg.get('ancho')
    ancho = int(ancho_val) if ancho_val is not None else 10
    desc_ini_val = franjas_cfg.get('descuento_inicial')
    inc_val = franjas_cfg.get('incremento')
    desc_inicial = float(desc_ini_val) if desc_ini_val is not None else 5.0
    incremento = float(inc_val) if inc_val is not None else 5.0
    
    logger.debug(f"Parámetros recibidos: bandas={bandas_val}, ancho={ancho_val}, desc_inicial={desc_ini_val}, incremento={inc_val}")
    logger.debug(f"Valores normalizados: num_bandas={num_bandas}, ancho={ancho}, desc_inicial={desc_inicial}, incremento={incremento}")
    if 0.0 < desc_inicial <= 1.0:
        desc_inicial *= 100.0
    if 0.0 < incremento <= 1.0:
        incremento *= 100.0
    if desc_inicial < 0.0: desc_inicial = 0.0
    if desc_inicial > 60.0: desc_inicial = 60.0
    if incremento < 0.0: incremento = 0.0
    if incremento > 60.0: incremento = 60.0
    if num_bandas < 1: num_bandas = 1
    if num_bandas > 60: num_bandas = 60
    if ancho < 1: ancho = 1

    def precio_con_iva_por_descuento(pct_desc: float) -> float:
        aplicado = max(0.0, base_subtotal * (1.0 - max(0.0, min(60.0, pct_desc)) / 100.0))
        return aplicado * (1.0 + max(0.0, float(iva_pct)) / 100.0)

    franjas = []
    inicio = 1

    # Precalcular precio base con IVA y objetivo final con dmax
    base_con_iva = base_subtotal * (1.0 + max(0.0, float(iva_pct)) / 100.0)
    dmax = min(60.0, max(0.0, desc_inicial + (num_bandas - 1) * incremento))
    floor_con_iva = base_con_iva * (1.0 - dmax / 100.0)
    if floor_con_iva < 0:
        floor_con_iva = 0.0

    # Distribución en MILÉSIMAS (0,001 €) para permitir más precios distintos y bajada estricta
    base_thou = int(round(base_con_iva * 1000))
    floor60_thou = int(round(floor_con_iva * 1000))
    # permitir al menos 1 milésima por paso si hay margen
    min_floor_thou = max(0, base_thou - max(0, num_bandas - 1))
    floor_eff_thou = max(floor60_thou, min_floor_thou)
    if floor_eff_thou > base_thou:
        floor_eff_thou = base_thou

    span_thou = max(0, base_thou - floor_eff_thou)
    steps = []
    if num_bandas <= 1:
        steps = []
    else:
        q, r = divmod(span_thou, num_bandas - 1)
        if span_thou >= (num_bandas - 1):
            base_step = max(1, q)
            steps = [base_step] * (num_bandas - 1)
            exceso = base_step * (num_bandas - 1) - span_thou
            idx = len(steps) - 1
            while exceso > 0 and idx >= 0:
                if steps[idx] > 1:
                    steps[idx] -= 1
                    exceso -= 1
                idx -= 1
        else:
            # Distribuir 1 milésima en las primeras 'span_thou' bandas
            steps = [0] * (num_bandas - 1)
            for i in range(span_thou):
                steps[i] = 1

    prev_price_red = None
    prev_pct = 0.0
    last_overall_max = inicio + ancho * num_bandas - 1
    for i in range(num_bandas):
        min_c = inicio + i * ancho
        max_c = min_c + ancho - 1

        if num_bandas == 1:
            target_price = base_con_iva
        else:
            drop_thou = sum(steps[:i]) if i > 0 else 0
            target_thou = base_thou - drop_thou
            if target_thou < 0:
                target_thou = 0
            if target_thou > base_thou:
                target_thou = base_thou
            target_price = target_thou / 1000.0  # no redondear a 2 decimales aquí

        # Asegurar estricto descenso de al menos 0.001; si no es posible, fusionar resto de bandas
        if prev_price_red is not None and target_price >= prev_price_red:
            # ¿es posible bajar 0.001?
            candidate = max(0.0, round(prev_price_red - 0.001, 3))
            if candidate >= 0.0 and candidate < prev_price_red:
                target_price = candidate
            else:
                # No hay margen real para bajar. Fusionar resto de bandas.
                if franjas:
                    franjas[-1]['max'] = last_overall_max
                else:
                    # Si es la primera, crear una única banda completa sin bajar precio
                    pct_tmp = 0.0
                    franjas.append({'min': min_c, 'max': last_overall_max, 'descuento': round(float(pct_tmp), 5)})
                return franjas

        # Convertir precio objetivo a descuento (%) respecto al base_con_iva
        pct_raw = 0.0
        if base_con_iva > 0:
            pct_raw = (1.0 - (target_price / base_con_iva)) * 100.0
        # Plan suave: no superar este máximo para la franja i
        pct_plan_cap = min(60.0, max(0.0, desc_inicial + i * incremento))

        # Primera franja siempre 0%, siguientes incrementales desde descuento_inicial
        if i == 0:
            pct = 0.0
        else:
            # Usar valores con decimales significativos para generar progresión real
            pct = desc_inicial + ((i - 1) * incremento)

        # Aplicar límites: nunca > 60%
        pct = min(60.0, max(0.0, pct))

        # Asegurar precisión de 5 decimales EXACTOS
        pct = round(float(pct), 5)

        # Si se alcanzaría el 60% antes de la última banda, fusionar resto
        if pct >= 60.0 and i < (num_bandas - 1):
            applied_price = precio_con_iva_por_descuento(pct)
            prev_price_red = applied_price
            if franjas:
                franjas[-1]['max'] = last_overall_max
            else:
                franjas.append({'min': min_c, 'max': last_overall_max, 'descuento': 60.0})
            return franjas

        # Recalcular precio con ese pct para registrar prev_price_red real aplicado
        applied_price = precio_con_iva_por_descuento(pct)
        if prev_price_red is not None and applied_price >= prev_price_red:
            # Intentar microajuste dentro del cap del plan para garantizar bajada >= 0.001€
            objetivo = max(0.0, round(prev_price_red - 0.001, 3))
            if base_con_iva > 0:
                pct_needed = (1.0 - (objetivo / base_con_iva)) * 100.0
                # No superar el cap del plan en esta franja
                pct_target = min(pct_plan_cap, max(prev_pct, pct_needed))
                # Microajuste hacia arriba en pasos de 0.0001 dentro del cap
                guard = 0
                while applied_price >= prev_price_red and pct < pct_target and guard < 100000:
                    pct = min(pct_target, pct + 0.0001)
                    applied_price = precio_con_iva_por_descuento(pct)
                    guard += 1
                # Si aún no baja, no forzar superar el cap: fusionar resto de bandas
                if applied_price >= prev_price_red:
                    if franjas:
                        franjas[-1]['max'] = last_overall_max
                    else:
                        franjas.append({'min': min_c, 'max': last_overall_max, 'descuento': round(float(pct), 5)})
                    return franjas

        prev_price_red = applied_price
        prev_pct = max(prev_pct, pct)
        franjas.append({'min': min_c, 'max': max_c, 'descuento': round(float(pct), 5)})
    return franjas


def ensure_tabla_productos():
    """
    Crea la tabla 'productos' si no existe con un esquema mínimo requerido.
    Asegura que 'id' sea INTEGER PRIMARY KEY AUTOINCREMENT.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1) Crear si no existe con el esquema correcto
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                descripcion TEXT DEFAULT '',
                subtotal REAL NOT NULL DEFAULT 0,
                iva REAL NOT NULL DEFAULT 0,
                impuestos INTEGER NOT NULL DEFAULT 21,
                total REAL NOT NULL DEFAULT 0
            )
            """
        )

        # 2) Verificar si la tabla existente carece de PK en 'id'
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='productos'")
        if cur.fetchone():
            cur.execute('PRAGMA table_info(productos)')
            cols = cur.fetchall()
            pk_on_id = False
            for c in cols:
                # PRAGMA table_info: (cid, name, type, notnull, dflt_value, pk)
                name = c[1] if not isinstance(c, sqlite3.Row) else c['name']
                pkflag = c[5] if not isinstance(c, sqlite3.Row) else c['pk']
                if str(name).lower() == 'id' and int(pkflag or 0) > 0:
                    pk_on_id = True
                    break

            if not pk_on_id:
                logger.warning('[MIGRACION] Detectada tabla productos sin PRIMARY KEY en id. Iniciando migración...')
                # Creamos tabla nueva con el esquema correcto
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS productos_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT NOT NULL,
                        descripcion TEXT DEFAULT '',
                        subtotal REAL NOT NULL DEFAULT 0,
                        iva REAL NOT NULL DEFAULT 0,
                        impuestos INTEGER NOT NULL DEFAULT 21,
                        total REAL NOT NULL DEFAULT 0
                    )
                    """
                )
                # Copiar datos (incluido id existente si lo hubiera)
                cur.execute(
                    """
                    INSERT INTO productos_new (id, nombre, descripcion, subtotal, iva, impuestos, total)
                    SELECT id, nombre, descripcion, subtotal, iva, impuestos, total FROM productos
                    """
                )
                # Reemplazar tabla
                cur.execute('DROP TABLE productos')
                cur.execute('ALTER TABLE productos_new RENAME TO productos')
                logger.info('[MIGRACION] Migración completada. Tabla productos ahora con id AUTOINCREMENT')

        # 3) Índices útiles
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_productos_nombre ON productos (nombre)
            """
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Error asegurando/migrando tabla productos: {e}", exc_info=True)
    finally:
        try:
            conn.close()
        except Exception:
            pass

# Asegurar tabla al importar el módulo
try:
    ensure_tabla_productos()
except Exception as _e:
    logger.error(f"No se pudo asegurar la tabla al importar: {_e}", exc_info=True)

def eliminar_todas_franjas_producto(producto_id: int):
    """
    Elimina todas las franjas de descuento de un producto específico.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM descuento_producto_franja WHERE producto_id = ?', (producto_id,))
        conn.commit()
        logger.info(f"Eliminadas {cur.rowcount} franjas del producto {producto_id}")
        return True
    finally:
        if conn:
            conn.close()

def regenerar_franjas_producto(producto_id: int, franjas_cfg: dict):
    """
    Regenera y reemplaza las franjas del producto a partir de su subtotal/iva actuales
    y la configuración recibida.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT subtotal, impuestos FROM productos WHERE id = ?', (producto_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"No existe el producto {producto_id}")
        base_subtotal = float(row['subtotal'])
        iva_pct = float(row['impuestos'])
        franjas = _generar_franjas_automaticas(base_subtotal, iva_pct, franjas_cfg or {})
        ensure_tabla_descuentos_bandas()
        reemplazar_franjas_descuento_producto(producto_id, franjas)
        return True
    finally:
        if conn:
            conn.close()
# ===================== Franjas de descuento por producto ===================== #
def ensure_tabla_descuentos_bandas():
    """
    Crea la tabla de franjas de descuento por producto si no existe.
    Estructura:
      - id INTEGER PK
      - producto_id INTEGER NOT NULL
      - min_cantidad INTEGER NOT NULL
      - max_cantidad INTEGER NOT NULL
      - porcentaje_descuento REAL NOT NULL (0-100)
    Constraints:
      - UNIQUE(producto_id, min_cantidad, max_cantidad)
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS descuento_producto_franja (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id INTEGER NOT NULL,
                min_cantidad INTEGER NOT NULL,
                max_cantidad INTEGER NOT NULL,
                porcentaje_descuento REAL NOT NULL,
                UNIQUE(producto_id, min_cantidad, max_cantidad)
            )
            """
        )
        # Índices útiles
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_desc_franja_producto
            ON descuento_producto_franja (producto_id, min_cantidad, max_cantidad)
            """
        )
        # Normalización preventiva: asegurar tope 60% en registros existentes
        cur.execute(
            """
            UPDATE descuento_producto_franja
            SET porcentaje_descuento = 60.0
            WHERE porcentaje_descuento > 60.0
            """
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Error creando tabla de franjas: {e}", exc_info=True)
        raise
    finally:
        try:
            conn.close()
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            pass


def obtener_franjas_descuento_por_producto(producto_id):
    """
    Devuelve lista de franjas de descuento para un producto dado, ordenadas por min_cantidad.
    Retorna lista de dicts: [{min, max, descuento}]
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT min_cantidad, max_cantidad, porcentaje_descuento
            FROM descuento_producto_franja
            WHERE producto_id = ?
            ORDER BY min_cantidad ASC, max_cantidad ASC
            """,
            (producto_id,)
        )
        filas = cur.fetchall()
        return [
            {
                'min_cantidad': int(row[0]),
                'max_cantidad': int(row[1]),
                # Servir 6 decimales para preservar granularidad fina
                'porcentaje_descuento': round(float(row[2]), 6)
            }
            for row in filas
        ]
    except Exception as e:
        logger.error(f"Error consultando franjas de producto {producto_id}: {e}", exc_info=True)
        raise
    finally:
        if 'conn' in locals():
            conn.close()


def reemplazar_franjas_descuento_producto(producto_id, franjas):
    """
    Reemplaza atómicamente todas las franjas del producto por las recibidas.
    Param franjas: lista de dicts con keys: min, max, descuento
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        conn.execute('BEGIN IMMEDIATE')
        cur.execute('DELETE FROM descuento_producto_franja WHERE producto_id = ?', (producto_id,))
        for fr in franjas:
            min_c = int(fr.get('min', 0))
            max_c = int(fr.get('max', 0))
            # Registrar valores originales recibidos
            try:
                original_desc = fr.get('descuento', 0)
                desc = float(original_desc)
            except Exception as _e:
                logger.warning(f"Valor de descuento no numérico para producto {producto_id}, franja {fr}: {_e}. Se usará 0.0")
                desc = 0.0
                original_desc = original_desc if 'original_desc' in locals() else None
            if min_c <= 0 or max_c <= 0 or max_c < min_c:
                raise ValueError(f"Franja inválida: {fr}")
            # Limitar rango de porcentaje a [0, 60]
            clamped_desc = desc
            if clamped_desc < 0:
                clamped_desc = 0.0
            if clamped_desc > 60.0:
                clamped_desc = 60.0
            # Redondeo a 6 decimales para consistencia de almacenamiento
            clamped_desc = round(float(clamped_desc), 6)
            if clamped_desc != desc:
                logger.debug(f"Clamp aplicado producto {producto_id}: desc_original={desc} -> desc_clamp={clamped_desc}")
            else:
                logger.debug(f"Descuento dentro de rango producto {producto_id}: desc={desc}")
            cur.execute(
                'INSERT INTO descuento_producto_franja (producto_id, min_cantidad, max_cantidad, porcentaje_descuento) VALUES (?,?,?,?)',
                (producto_id, min_c, max_c, clamped_desc)
            )
            logger.debug(f"Insertada franja producto {producto_id}: min={min_c}, max={max_c}, desc={clamped_desc}")
        conn.commit()
        return True
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        logger.error(f"Error reemplazando franjas del producto {producto_id}: {e}", exc_info=True)
        raise
    finally:
        if 'conn' in locals():
            conn.close()


def obtener_productos_paginados(filtros, page=1, page_size=20, sort='nombre', order='ASC'):
    """
    Obtiene productos con paginación y filtros opcionales.

    Args:
        filtros (dict): { 'nombre': str }
        page (int): Número de página (1-indexado)
        page_size (int): Tamaño de página
        sort (str): Campo de ordenación ('nombre', 'subtotal', 'impuestos', 'total')
        order (str): 'ASC' o 'DESC'

    Returns:
        dict: {
            'items': [ {producto...} ],
            'total': int,
            'page': int,
            'page_size': int,
            'total_pages': int
        }
    """
    try:
        # Saneamiento de parámetros
        try:
            page = int(page) if int(page) > 0 else 1
        except Exception:
            page = 1
        try:
            page_size = int(page_size)
            if page_size <= 0:
                page_size = 20
            page_size = min(page_size, 100)
        except Exception:
            page_size = 20

        allowed_sort = {'nombre', 'subtotal', 'impuestos', 'total'}
        sort = sort if sort in allowed_sort else 'nombre'
        order = 'DESC' if str(order).upper() == 'DESC' else 'ASC'

        conn = get_db_connection()
        cursor = conn.cursor()

        where_sql = 'WHERE 1=1'
        params = []

        if filtros.get('nombre'):
            where_sql += ' AND LOWER(nombre) LIKE LOWER(?)'
            params.append(f"%{filtros['nombre']}%")

        # Conteo total
        count_sql = f'SELECT COUNT(*) as total FROM productos {where_sql}'
        cursor.execute(count_sql, params)
        row = cursor.fetchone()
        total = row['total'] if isinstance(row, sqlite3.Row) else (row[0] if row else 0)

        offset = (page - 1) * page_size
        sql = f'''SELECT * FROM productos
                  {where_sql}
                  ORDER BY {sort} {order}
                  LIMIT ? OFFSET ?'''
        params_limit = params + [page_size, offset]
        cursor.execute(sql, params_limit)
        items = [dict(r) for r in cursor.fetchall()]

        total_pages = (int(total) + page_size - 1) // page_size if page_size else 1

        return {
            'items': items,
            'total': int(total),
            'page': page,
            'page_size': page_size,
            'total_pages': int(total_pages)
        }
    except sqlite3.Error as e:
        logger.error(f"Error de base de datos en obtener_productos_paginados: {str(e)}", exc_info=True)
        raise Exception(f"Error al obtener productos paginados: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()


def obtener_producto(id_producto):
    """
    Devuelve un producto específico por su ID.
    
    Args:
        id_producto (int): ID del producto a buscar
        
    Returns:
        dict: Datos del producto si se encuentra
        None: Si no se encuentra el producto
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Buscar el producto específico incluyendo campos de franjas automáticas
        query = '''
            SELECT *, 
                   calculo_automatico, franja_inicial, numero_franjas, 
                   ancho_franja, descuento_inicial, incremento_franja, no_generar_franjas
            FROM productos 
            WHERE id = ?
        '''
        cursor.execute(query, (id_producto,))
        producto = cursor.fetchone()
        
        if producto:
            resultado = dict(producto)
            return resultado
        else:
            return None
            
    except sqlite3.Error:
        raise
    except Exception:
        raise
    finally:
        if 'conn' in locals():
            conn.close()


def buscar_productos(filtros):
    """
    Busca productos que coincidan con los filtros proporcionados.
    
    Args:
        filtros (dict): Diccionario con los filtros a aplicar:
                        - nombre: Filtro por nombre (parcial)
                        - descripcion: Filtro por descripción (parcial)
                        - impuestos: Filtro por porcentaje de impuestos (exacto)
                        
    Returns:
        list: Lista de diccionarios con los datos de los productos que coinciden.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Construir la consulta SQL base
        sql = 'SELECT * FROM productos WHERE 1=1'
        params = []
        
        # Añadir condiciones según los filtros
        if filtros.get('nombre'):
            sql += ' AND LOWER(nombre) LIKE LOWER(?)'
            params.append(f'%{filtros["nombre"]}%')
        
        if filtros.get('descripcion'):
            sql += ' AND LOWER(descripcion) LIKE LOWER(?)'
            params.append(f'%{filtros["descripcion"]}%')
        
        if filtros.get('impuestos') is not None:
            try:
                # Convertir a entero si es string
                impuestos_valor = int(filtros['impuestos'])
                sql += ' AND impuestos = ?'
                params.append(impuestos_valor)
            except (ValueError, TypeError):
                logger.warning(f"Error: impuestos no es un valor numérico: {filtros['impuestos']}")
                # Si no es convertible, ignoramos este filtro
        
        # Ordenar y limitar
        sql += ' ORDER BY nombre ASC LIMIT 100'
        
        # Ejecutar la consulta
        cursor.execute(sql, params)
        productos = cursor.fetchall()
        
        return [dict(producto) for producto in productos]
        
    except sqlite3.Error as e:
        logger.error(f"Error de base de datos en buscar_productos: {str(e)}", exc_info=True)
        raise Exception(f"Error al buscar productos: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()


def crear_producto(data):
    """
    Crea un nuevo producto.
    
    Args:
        data (dict): Diccionario con los datos del producto:
                    - nombre: Nombre del producto
                    - descripcion: Descripción del producto
                    - subtotal: Precio base
                    - impuestos: Porcentaje de impuestos (entero)
                    - iva: Importe de IVA
                    - total: Precio total
                    
    Returns:
        dict: Resultado de la operación con mensaje de éxito/error y el ID
    """
    
    # Asegurar existencia de tabla y log de entrada
    try:
        ensure_tabla_productos()
    except Exception as e:
        logger.error(f"Error al asegurar tabla antes de crear: {e}", exc_info=True)

    logger.debug(f"crear_producto payload: {data}")
    # Validar campos requeridos
    nombre = data.get('nombre')
    if not nombre:
        return {"success": False, "message": "El campo 'nombre' es obligatorio."}
    
    try:
        # Calcular campos derivados si no están presentes
        subtotal = float(data.get('subtotal', 0))
        impuestos = int(data.get('impuestos', 0))
        
        # Si no se proporciona IVA, calcularlo a partir de subtotal e impuestos
        if 'iva' not in data:
            iva = round(subtotal * (impuestos / 100), 2)
        else:
            iva = float(data.get('iva', 0))
        
        # Si no se proporciona total, calcularlo
        if 'total' not in data:
            total = subtotal + iva
        else:
            total = float(data.get('total', 0))
        
        # Redondear valores - subtotal a 5 decimales, iva y total a 2 decimales
        subtotal = round(float(subtotal), 5)
        iva = round(float(iva), 2)
        total = round(float(total), 2)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si ya existe un producto con el mismo nombre
        cursor.execute('SELECT id FROM productos WHERE LOWER(nombre) = LOWER(?)', (nombre,))
        existente = cursor.fetchone()
        if existente:
            return {
                "success": False,
                "message": f"Ya existe un producto con el nombre '{nombre}'. Por favor, utilice otro nombre."
            }
        
        # Insertar el nuevo producto incluyendo configuración de franjas
        # Usar directamente los campos del data en lugar de config_franjas anidado
        cursor.execute('''
            INSERT INTO productos (nombre, descripcion, subtotal, iva, impuestos, total,
                                 calculo_automatico, franja_inicial, numero_franjas, 
                                 ancho_franja, descuento_inicial, incremento_franja, no_generar_franjas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            nombre,
            data.get('descripcion', ''),
            subtotal,
            iva,
            impuestos,
            total,
            data.get('calculo_automatico', 0),
            data.get('franja_inicial', 1),
            data.get('numero_franjas', 50),
            data.get('ancho_franja', 10),
            data.get('descuento_inicial', 5.0),
            data.get('incremento_franja', 5.0),
            data.get('no_generar_franjas', 0)
        ))
        
        conn.commit()
        last_id = cursor.lastrowid
        logger.info(f"Producto insertado. ID={last_id}, nombre='{nombre}'")
        
        # Gestionar franjas según configuración
        try:
            # Si está marcado "no generar franjas", no crear franjas
            if data.get('no_generar_franjas', 0):
                logger.debug(f"No se generan franjas para producto {last_id} (no_generar_franjas=1)")
            elif data.get('calculo_automatico', 0):
                # Usar directamente los valores del data enviado por el usuario
                franjas_cfg = {
                    'franja_inicio': data.get('franja_inicial', 1),
                    'bandas': data.get('numero_franjas', 50),
                    'ancho': data.get('ancho_franja', 10),
                    'descuento_inicial': data.get('descuento_inicial', 5.0),
                    'incremento': data.get('incremento_franja', 5.0)
                }
                
                logger.debug(f"Generando franjas con config del usuario: {franjas_cfg}")
                
                # Generar franjas siempre con los parámetros de configuración
                base_subtotal = float(data.get('subtotal') or 0)
                iva_pct = float(data.get('impuestos') or 0)
                franjas = _generar_franjas_automaticas(base_subtotal, iva_pct, franjas_cfg)
                ensure_tabla_descuentos_bandas()
                reemplazar_franjas_descuento_producto(last_id, franjas)
                logger.info(f"Franjas generadas para producto {last_id} con config: {franjas_cfg}")
            else:
                logger.debug(f"No se generan franjas para producto {last_id} (calculo_automatico=0)")
        except Exception as e_fr:
            # No fallar la creación de producto si las franjas fallan, solo registrar
            logger.warning(f"Advertencia al gestionar franjas automáticas para producto {last_id}: {e_fr}")
        
        return {
            "success": True,
            "message": "Producto creado exitosamente.",
            "id": last_id
        }
        
    except sqlite3.Error as e:
        logger.error(f"Error de base de datos al crear producto: {str(e)}", exc_info=True)
        return {"success": False, "message": f"Error de base de datos: {str(e)}"}
    except Exception as e:
        logger.error(f"Error inesperado al crear producto: {str(e)}", exc_info=True)
        return {"success": False, "message": f"Error inesperado: {str(e)}"}
    finally:
        if 'conn' in locals():
            conn.close()


def actualizar_producto(id_producto, data):
    """
    Actualiza un producto existente por su ID.
    
    Args:
        id_producto (int): ID del producto a actualizar
        data (dict): Diccionario con los datos a actualizar
                    
    Returns:
        dict: Resultado de la operación con mensaje de éxito/error
    """
    
    # Validar campos requeridos
    nombre = data.get('nombre')
    if not nombre:
        return {"success": False, "message": "El campo 'nombre' es obligatorio."}
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si existe el producto
        cursor.execute('SELECT id FROM productos WHERE id = ?', (id_producto,))
        producto = cursor.fetchone()
        if not producto:
            return {
                "success": False,
                "message": f"No existe un producto con el ID {id_producto}."
            }
        
        # Verificar si el nuevo nombre ya existe para otro producto
        cursor.execute('SELECT id FROM productos WHERE LOWER(nombre) = LOWER(?) AND id != ?', (nombre, id_producto))
        existente = cursor.fetchone()
        if existente:
            return {
                "success": False,
                "message": f"Ya existe otro producto con el nombre '{nombre}'. Por favor, utilice otro nombre."
            }
        
        # Calcular campos derivados si no están presentes
        subtotal = float(data.get('subtotal', 0))
        impuestos = int(data.get('impuestos', 0))
        
        # Si no se proporciona IVA, calcularlo a partir de subtotal e impuestos
        if 'iva' not in data:
            iva = round(subtotal * (impuestos / 100), 2)
        else:
            iva = float(data.get('iva', 0))
        
        # Si no se proporciona total, calcularlo
        if 'total' not in data:
            total = subtotal + iva
        else:
            total = float(data.get('total', 0))
        
        # Redondear valores - subtotal a 5 decimales, iva y total a 2 decimales
        subtotal = round(float(subtotal), 5)
        iva = round(float(iva), 2)
        total = round(float(total), 2)
        
        # Actualizar el producto incluyendo configuración de franjas
        config_franjas = data.get('config_franjas', {})
        no_generar_franjas_val = 1 if config_franjas.get('no_generar_franjas') else 0
        
        logger.debug(f"actualizar_producto - ID: {id_producto}")
        logger.debug(f"config_franjas recibido: {config_franjas}")
        logger.debug(f"Valores a actualizar: franja_inicial={config_franjas.get('franja_inicial', 1)}, "
                    f"numero_franjas={config_franjas.get('numero_franjas', 50)}, "
                    f"ancho_franja={config_franjas.get('ancho_franja', 10)}, "
                    f"descuento_inicial={config_franjas.get('descuento_inicial', 5.0)}, "
                    f"incremento_franja={config_franjas.get('incremento_franja', 5.0)}, "
                    f"no_generar_franjas={no_generar_franjas_val}")
        
        cursor.execute('''
            UPDATE productos
            SET nombre=?,
                descripcion=?,
                subtotal=?,
                iva=?,
                impuestos=?,
                total=?,
                calculo_automatico=?,
                franja_inicial=?,
                numero_franjas=?,
                ancho_franja=?,
                descuento_inicial=?,
                incremento_franja=?,
                no_generar_franjas=?
            WHERE id=?
        ''', (
            nombre,
            data.get('descripcion', ''),
            subtotal,
            iva,
            impuestos,
            total,
            1 if config_franjas.get('calculo_automatico') else 0,
            config_franjas.get('franja_inicial', 1),
            config_franjas.get('numero_franjas', 50),
            config_franjas.get('ancho_franja', 10),
            config_franjas.get('descuento_inicial', 5.0),
            config_franjas.get('incremento_franja', 5.0),
            no_generar_franjas_val,
            id_producto
        ))
        
        conn.commit()

        # Gestionar franjas según configuración
        try:
            config_franjas = data.get('config_franjas', {})
            
            # Verificar que hay configuración de franjas
            if config_franjas:
                # Si está marcado "no generar franjas", eliminar todas las franjas existentes
                if config_franjas.get('no_generar_franjas', 0):
                    eliminar_todas_franjas_producto(id_producto)
                    logger.info(f"Eliminadas todas las franjas del producto {id_producto}")
                else:
                    # Verificar si el producto ya tiene franjas
                    cursor.execute('SELECT COUNT(*) as total FROM descuento_producto_franja WHERE producto_id = ?', (id_producto,))
                    tiene_franjas = cursor.fetchone()['total'] > 0
                    
                    # Solo generar franjas si NO tiene franjas y el check está activo
                    if not tiene_franjas and config_franjas.get('calculo_automatico'):
                        franjas_cfg = {
                            'franja_inicio': config_franjas.get('franja_inicial', 1),
                            'bandas': config_franjas.get('numero_franjas', 50),
                            'ancho': config_franjas.get('ancho_franja', 10),
                            'descuento_inicial': config_franjas.get('descuento_inicial', 5.0),
                            'incremento': config_franjas.get('incremento_franja', 5.0)
                        }
                        
                        regenerar_franjas_producto(id_producto, franjas_cfg)
                        logger.info(f"Franjas generadas para producto {id_producto} (no tenía franjas)")
                    else:
                        logger.debug(f"Producto {id_producto} ya tiene franjas o check desactivado - NO se regeneran")
        except Exception as e_fr:
            # No fallar la actualización del producto si las franjas fallan, solo registrar
            logger.warning(f"Advertencia al gestionar franjas automáticas para producto {id_producto}: {e_fr}")

        return {
            "success": True,
            "message": "Producto actualizado exitosamente."
        }
        
    except sqlite3.Error as e:
        logger.error(f"Error de base de datos al actualizar producto {id_producto}: {str(e)}", exc_info=True)
        return {"success": False, "message": f"Error de base de datos: {str(e)}"}
    except Exception as e:
        logger.error(f"Error inesperado al actualizar producto {id_producto}: {str(e)}", exc_info=True)
        return {"success": False, "message": f"Error inesperado: {str(e)}"}
    finally:
        if 'conn' in locals():
            conn.close()


def eliminar_producto(id_producto):
    """
    Elimina un producto por su ID.
    
    Args:
        id_producto (int): ID del producto a eliminar
        
    Returns:
        dict: Resultado de la operación con mensaje de éxito/error
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si existe el producto
        cursor.execute('SELECT id FROM productos WHERE id = ?', (id_producto,))
        producto = cursor.fetchone()
        if not producto:
            return {
                "success": False,
                "message": f"No existe un producto con el ID {id_producto}."
            }
        
        # Verificar si el producto está siendo utilizado en detalle_tickets
        cursor.execute('SELECT COUNT(*) FROM detalle_tickets WHERE productoId = ?', (id_producto,))
        count_tickets = cursor.fetchone()[0]
        
        # Verificar si el producto está siendo utilizado en detalle_factura
        cursor.execute('SELECT COUNT(*) FROM detalle_factura WHERE productoId = ?', (id_producto,))
        count_factura = cursor.fetchone()[0]
        
        # Verificar si el producto está siendo utilizado en detalle_proforma
        cursor.execute('SELECT COUNT(*) FROM detalle_proforma WHERE productoId = ?', (id_producto,))
        count_proforma = cursor.fetchone()[0]
        
        # Si el producto está siendo utilizado, no permitir eliminación
        if count_tickets > 0 or count_factura > 0 or count_proforma > 0:
            return {
                "success": False,
                "message": "No se puede eliminar el producto porque está siendo utilizado en tickets, facturas o proformas."
            }
        
        # Eliminar franjas asociadas y el producto dentro de una transacción
        try:
            conn.execute('BEGIN IMMEDIATE')
            cursor.execute('DELETE FROM descuento_producto_franja WHERE producto_id = ?', (id_producto,))
            cursor.execute('DELETE FROM productos WHERE id = ?', (id_producto,))
            conn.commit()
        except Exception as e_tr:
            if 'conn' in locals():
                conn.rollback()
            raise e_tr
        
        return {
            "success": True,
            "message": "Producto eliminado exitosamente."
        }
        
    except sqlite3.Error as e:
        logger.error(f"Error de base de datos al eliminar producto {id_producto}: {str(e)}", exc_info=True)
        return {"success": False, "message": f"Error de base de datos: {str(e)}"}
    except Exception as e:
        logger.error(f"Error inesperado al eliminar producto {id_producto}: {str(e)}", exc_info=True)
        return {"success": False, "message": f"Error inesperado: {str(e)}"}
    finally:
        if 'conn' in locals():
            conn.close()

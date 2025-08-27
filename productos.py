import sqlite3
from functools import lru_cache

from constantes import *
from db_utils import get_db_connection, redondear_importe
from flask import jsonify, request


def obtener_productos():
    """
    Obtiene todos los productos ordenados por nombre.
    
    Returns:
        list: Lista de diccionarios con los datos de los productos.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM productos ORDER BY nombre ASC')
        productos = cursor.fetchall()
        
        return [dict(producto) for producto in productos]
        
    except sqlite3.Error as e:
        print(f"Error de base de datos: {str(e)}")
        raise Exception("Error al obtener los productos de la base de datos")
    except Exception as e:
        print(f"Error inesperado: {str(e)}")
        raise Exception("Error inesperado al obtener los productos")
    finally:
        if 'conn' in locals():
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
        conn.commit()
    except Exception as e:
        print(f"[DESCUENTOS] Error creando tabla de franjas: {e}")
        raise
    finally:
        try:
            conn.close()
        except:
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
                'min': int(row['min_cantidad']),
                'max': int(row['max_cantidad']),
                'descuento': float(row['porcentaje_descuento'])
            }
            for row in filas
        ]
    except Exception as e:
        print(f"[DESCUENTOS] Error consultando franjas de producto {producto_id}: {e}")
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
            desc = float(fr.get('descuento', 0))
            if min_c <= 0 or max_c <= 0 or max_c < min_c:
                raise ValueError(f"Franja inválida: {fr}")
            if desc < 0:
                desc = 0.0
            cur.execute(
                'INSERT INTO descuento_producto_franja (producto_id, min_cantidad, max_cantidad, porcentaje_descuento) VALUES (?,?,?,?)',
                (producto_id, min_c, max_c, desc)
            )
        conn.commit()
        return True
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        print(f"[DESCUENTOS] Error reemplazando franjas del producto {producto_id}: {e}")
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
        print(f"Error de base de datos en obtener_productos_paginados: {str(e)}")
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
        
        # Buscar el producto específico
        query = 'SELECT * FROM productos WHERE id = ?'
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
                print(f"Error: impuestos no es un valor numérico: {filtros['impuestos']}")
                # Si no es convertible, ignoramos este filtro
        
        # Ordenar y limitar
        sql += ' ORDER BY nombre ASC LIMIT 100'
        
        # Ejecutar la consulta
        cursor.execute(sql, params)
        productos = cursor.fetchall()
        
        return [dict(producto) for producto in productos]
        
    except sqlite3.Error as e:
        print(f"Error de base de datos en buscar_productos: {str(e)}")
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
        
        # Redondear valores
        subtotal = redondear_importe(subtotal)
        iva = redondear_importe(iva)
        total = redondear_importe(total)
        
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
        
        # Insertar el nuevo producto
        cursor.execute('''
            INSERT INTO productos (nombre, descripcion, subtotal, iva, impuestos, total)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            nombre,
            data.get('descripcion', ''),
            subtotal,
            iva,
            impuestos,
            total
        ))
        
        conn.commit()
        last_id = cursor.lastrowid
        
        return {
            "success": True,
            "message": "Producto creado exitosamente.",
            "id": last_id
        }
        
    except sqlite3.Error as e:
        print(f"Error de base de datos: {str(e)}")
        return {"success": False, "message": f"Error de base de datos: {str(e)}"}
    except Exception as e:
        print(f"Error inesperado: {str(e)}")
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
        
        # Redondear valores
        subtotal = redondear_importe(subtotal)
        iva = redondear_importe(iva)
        total = redondear_importe(total)
        
        # Actualizar el producto
        cursor.execute('''
            UPDATE productos
            SET nombre=?,
                descripcion=?,
                subtotal=?,
                iva=?,
                impuestos=?,
                total=?
            WHERE id=?
        ''', (
            nombre,
            data.get('descripcion', ''),
            subtotal,
            iva,
            impuestos,
            total,
            id_producto
        ))
        
        conn.commit()
        
        return {
            "success": True,
            "message": "Producto actualizado exitosamente."
        }
        
    except sqlite3.Error as e:
        print(f"Error de base de datos: {str(e)}")
        return {"success": False, "message": f"Error de base de datos: {str(e)}"}
    except Exception as e:
        print(f"Error inesperado: {str(e)}")
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
        
        # Eliminar el producto
        cursor.execute('DELETE FROM productos WHERE id = ?', (id_producto,))
        conn.commit()
        
        return {
            "success": True,
            "message": "Producto eliminado exitosamente."
        }
        
    except sqlite3.Error as e:
        print(f"Error de base de datos: {str(e)}")
        return {"success": False, "message": f"Error de base de datos: {str(e)}"}
    except Exception as e:
        print(f"Error inesperado: {str(e)}")
        return {"success": False, "message": f"Error inesperado: {str(e)}"}
    finally:
        if 'conn' in locals():
            conn.close()

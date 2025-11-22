import sqlite3
from db_utils import get_db_connection
from functools import lru_cache

from constantes import *
from logger_config import get_logger

# Inicializar logger
logger = get_logger(__name__)



def obtener_sugerencias_carrer(query):
    """
    Obtiene sugerencias de dirección (carrer) basadas en una consulta de búsqueda.
    La caché se aplica a las búsquedas más frecuentes.

    Args:
        query (str): Texto de búsqueda ingresado por el usuario.

    Returns:
        list: Lista de diccionarios con 'carrer' y 'cp'.
    """
    # Normalizar la query para mejorar el hit ratio de la caché
    query = query.lower().strip()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = """
            SELECT carrer, cp
            FROM codipostal
            WHERE LOWER(carrer) LIKE ?
            ORDER BY 
                CASE 
                    WHEN LOWER(carrer) LIKE ? THEN 1  -- Coincidencia exacta al inicio
                    WHEN LOWER(carrer) LIKE ? THEN 2  -- Coincidencia al inicio
                    ELSE 3                            -- Otras coincidencias
                END,
                carrer
            LIMIT 10
        """
        like_query = f"%{query}%"
        exact_start = f"{query}%"
        cursor.execute(sql, (like_query, exact_start, exact_start))
        rows = cursor.fetchall()
        
        return [{'carrer': row[0], 'cp': row[1]} for row in rows]
    except sqlite3.Error:
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def buscar_codigos_postales(prefijo):
    """Devuelve lista de CP que empiezan por *prefijo* (máx 20)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT cp, poblacio, provincia
            FROM codipostal
            WHERE cp LIKE ? || '%'
            ORDER BY cp
            LIMIT 20
            """,
            (prefijo,)
        )
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error:
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def obtener_datos_cp(cp):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT cp, poblacio, provincia
            FROM codipostal
            WHERE cp = ?
            LIMIT 1
        """

        cursor.execute(query, (cp,))
        resultado = cursor.fetchone()

        if resultado:
            return [dict(resultado)]  # Devuelve un array con un único resultado
        return []  # Si no hay resultados, devuelve un array vacío

    except sqlite3.DatabaseError:
        return {"error": "Error de base de datos al procesar la solicitud"}
    except Exception:
        return {"error": "Error inesperado al procesar la solicitud"}
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def obtener_contactos():
    """Devuelve todos los contactos ordenados por razón social."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener todos los contactos con información de proformas abiertas
        cursor.execute('''
            SELECT 
                c.idContacto,
                c.razonsocial,
                c.identificador,
                c.mail,
                c.telf1,
                c.telf2,
                c.direccion,
                c.localidad,
                c.cp,
                c.provincia,
                c.tipo,
                c.dir3_oficina,
                c.dir3_organo,
                c.dir3_unidad,
                c.face_presentacion,
                c.idContacto as id,
                p.numero as numero_proforma_abierta
            FROM contactos c
            LEFT JOIN (
                SELECT idcontacto, numero
                FROM proforma
                WHERE estado = 'A'
                GROUP BY idcontacto
                HAVING MAX(fecha)
            ) p ON p.idcontacto = c.idContacto
            ORDER BY c.razonsocial ASC 
            LIMIT 10
        ''')
        contactos = cursor.fetchall()
        
        # Convertir a lista de diccionarios y asegurar que id e idContacto estén presentes
        return [dict(c) for c in contactos]
        
    except sqlite3.Error as e:
        logger.error(f"Error de base de datos: {str(e)}", exc_info=True)
        raise Exception("Error al obtener los contactos de la base de datos")
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}", exc_info=True)
        raise Exception("Error inesperado al obtener los contactos")
    finally:
        if 'conn' in locals():
            conn.close()


def obtener_contactos_paginados(filtros, page=1, page_size=10, sort='razonsocial', order='ASC'):
    """
    Obtiene contactos con paginación y filtros opcionales.

    Args:
        filtros (dict): { 'razonSocial': str, 'nif': str }
        page (int): Número de página (1-indexado)
        page_size (int): Tamaño de página (máx 100)
        sort (str): Campo de ordenación ('razonsocial', 'identificador', 'localidad', 'provincia')
        order (str): 'ASC' o 'DESC'

    Returns:
        dict: {
            'items': [ {contacto...} ],
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
                page_size = 10
            page_size = min(page_size, 100)
        except Exception:
            page_size = 10

        allowed_sort = {
            'razonsocial': 'c.razonsocial',
            'identificador': 'c.identificador',
            'localidad': 'c.localidad',
            'provincia': 'c.provincia'
        }
        sort_column = allowed_sort.get(str(sort).lower(), 'c.razonsocial')
        order = 'DESC' if str(order).upper() == 'DESC' else 'ASC'

        conn = get_db_connection()
        cursor = conn.cursor()

        where_sql = 'WHERE 1=1 AND COALESCE(TRIM(c.identificador), "") <> ""'
        params = []

        if filtros.get('razonsocial'):
            where_sql += ' AND LOWER(c.razonsocial) LIKE LOWER(?)'
            params.append(f"%{filtros['razonsocial']}%")
        if filtros.get('nif'):
            where_sql += ' AND LOWER(c.identificador) LIKE LOWER(?)'
            params.append(f"%{filtros['nif']}%")

        # Conteo total
        count_sql = f'SELECT COUNT(*) as total FROM contactos c {where_sql}'
        cursor.execute(count_sql, params)
        row = cursor.fetchone()
        total = row['total'] if isinstance(row, sqlite3.Row) else (row[0] if row else 0)

        offset = (page - 1) * page_size
        sql = f'''
            SELECT 
                c.idContacto,
                c.razonsocial,
                c.identificador,
                c.mail,
                c.telf1,
                c.telf2,
                c.direccion,
                c.localidad,
                c.cp,
                c.provincia,
                c.tipo,
                c.dir3_oficina,
                c.dir3_organo,
                c.dir3_unidad,
                c.face_presentacion,
                c.idContacto as id,
                (
                    SELECT p.numero 
                    FROM proforma p 
                    WHERE p.idcontacto = c.idContacto 
                    AND p.estado = 'A'
                    ORDER BY p.fecha DESC, p.id DESC
                    LIMIT 1
                ) as numero_proforma_abierta
            FROM contactos c
            {where_sql}
            ORDER BY {sort_column} {order}
            LIMIT ? OFFSET ?
        '''
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
        logger.error(f"Error de base de datos en obtener_contactos_paginados: {str(e)}", exc_info=True)
        raise Exception(f"Error al obtener contactos paginados: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

def obtener_contacto(idContacto):
    """
    Devuelve un contacto específico por su ID.
    
    Args:
        idContacto (int): ID del contacto a buscar
        
    Returns:
        dict: Datos del contacto si se encuentra
        None: Si no se encuentra el contacto
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si la tabla existe y tiene registros
        cursor.execute("SELECT COUNT(*) FROM contactos")
        total_contactos = cursor.fetchone()[0]
        
        # Verificar el máximo ID en la tabla
        cursor.execute("SELECT MAX(idContacto) FROM contactos")
        max_id = cursor.fetchone()[0]
        
        # Buscar el contacto específico
        query = 'SELECT * FROM contactos WHERE idContacto = ?'
        cursor.execute(query, (idContacto,))
        contacto = cursor.fetchone()
        
        if contacto:
            resultado = dict(contacto)
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

def crear_contacto(data):
    """
    Crea un nuevo contacto.
    `data` es un diccionario con las llaves:
    razonsocial, identificador, mail, telf1, telf2, direccion, localidad, cp, provincia, tipo
    """
    
    identificador = data.get('identificador')
        
    if not identificador:
        return {"success": False, "message": "El campo 'identificador' es obligatorio."}
        
    if not es_identificador_unico(identificador):
        return {"success": False, "message": "El identificador ya está registrado. Por favor introduce uno diferente o edita el contacto existente."}
        
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO contactos (
            razonsocial, identificador, mail, telf1, telf2, direccion,
            localidad, cp, provincia, tipo,
            dir3_oficina, dir3_organo, dir3_unidad, facturacion_automatica
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('razonsocial'),
        data.get('identificador'),
        data.get('mail'),
        data.get('telf1'),
        data.get('telf2'),
        data.get('direccion'),
        data.get('localidad'),
        data.get('cp'),
        data.get('provincia'),
        data.get('tipo'),
        data.get('dir3_oficina'),
        data.get('dir3_organo'),
        data.get('dir3_unidad'),
        1 if data.get('facturacion_automatica') else 0
    ))
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return {
        "success": True,
        "message": "Contacto creado exitosamente.",
        "id": last_id
     }


def es_identificador_unico(identificador, idContacto=None):
    """
    Verifica si un identificador es único en la base de datos.
    
    Parámetros:
        identificador (str): El identificador a verificar.
        idContacto (int, opcional): ID del contacto a excluir de la verificación (usado en actualizaciones).
    
    Retorna:
        bool: True si el identificador es único, False de lo contrario.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if idContacto:
                cursor.execute('''
                    SELECT idContacto FROM contactos
                    WHERE identificador = ?
                    AND idContacto != ?
                ''', (identificador, idContacto))
            else:
                cursor.execute('''
                    SELECT idContacto FROM contactos
                    WHERE identificador = ?
                ''', (identificador,))
            
            resultado = cursor.fetchone()
            return resultado is None
    except sqlite3.Error:
        return False


def actualizar_contacto(idContacto, data):
    """
    Actualiza un contacto existente por su idContacto.
    `data` es un diccionario con las llaves:
    razonsocial, identificador, mail, telf1, telf2, direccion, localidad, cp, provincia, tipo
    """
     
    identificador = data.get('identificador')

        
    if not es_identificador_unico(identificador, idContacto):
            return {"success": False, "message": "El identificador ya está registrado. Por favor introduce uno diferente o edita el contacto existente."}
    
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        UPDATE contactos
        SET
            razonsocial=?,
            identificador=?,
            mail=?,
            telf1=?,
            telf2=?,
            direccion=?,
            localidad=?,
            cp=?,
            provincia=?,
            tipo=?,
            dir3_oficina=?,
            dir3_organo=?,
            dir3_unidad=?,
            facturacion_automatica=?
        WHERE idContacto=?
    ''', (
        data.get('razonsocial'),
        data.get('identificador'),
        data.get('mail'),
        data.get('telf1'),
        data.get('telf2'),
        data.get('direccion'),
        data.get('localidad'),
        data.get('cp'),
        data.get('provincia'),
        data.get('tipo'),
        data.get('dir3_oficina'),
        data.get('dir3_organo'),
        data.get('dir3_unidad'),
        1 if data.get('facturacion_automatica') else 0,
        idContacto
    ))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Contacto actualizado exitosamente."}

def delete_contacto(idContacto):
    """Elimina un contacto por su idContacto."""
    conn = get_db_connection()
    conn.execute('DELETE FROM contactos WHERE idContacto=?', (idContacto,))
    conn.commit()
    conn.close()
    return True

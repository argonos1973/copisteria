"""
Módulo de gestión de facturas de proveedores
Incluye funciones para CRUD de proveedores y facturas recibidas
"""

import sqlite3
import os
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import json
from logger_config import get_logger
from db_utils import get_db_connection

logger = get_logger(__name__)

FACTURAS_DIR = '/var/www/html/facturas_proveedores'


# ============================================================================
# FUNCIONES DE UTILIDAD
# ============================================================================

def obtener_trimestre_actual():
    """
    Retorna el trimestre actual y fechas de inicio/fin
    
    Returns:
        tuple: (trimestre, año, fecha_inicio, fecha_fin)
    """
    hoy = datetime.now()
    mes = hoy.month
    año = hoy.year
    
    if mes <= 3:  # Q1
        trimestre = 'Q1'
        inicio = datetime(año, 1, 1)
        fin = datetime(año, 3, 31, 23, 59, 59)
    elif mes <= 6:  # Q2
        trimestre = 'Q2'
        inicio = datetime(año, 4, 1)
        fin = datetime(año, 6, 30, 23, 59, 59)
    elif mes <= 9:  # Q3
        trimestre = 'Q3'
        inicio = datetime(año, 7, 1)
        fin = datetime(año, 9, 30, 23, 59, 59)
    else:  # Q4
        trimestre = 'Q4'
        inicio = datetime(año, 10, 1)
        fin = datetime(año, 12, 31, 23, 59, 59)
    
    return trimestre, año, inicio, fin


def obtener_directorio_facturas(empresa_codigo, año=None, trimestre=None):
    """
    Obtiene el directorio para guardar facturas
    
    Args:
        empresa_codigo: Código de la empresa
        año: Año (opcional)
        trimestre: Trimestre Q1-Q4 (opcional)
    
    Returns:
        Path: Ruta del directorio
    """
    base = Path(FACTURAS_DIR)
    
    if not año or not trimestre:
        return base / empresa_codigo
    
    dir_trimestre = base / empresa_codigo / str(año) / trimestre / 'originales'
    dir_trimestre.mkdir(parents=True, exist_ok=True)
    
    return dir_trimestre


def calcular_hash_pdf(pdf_bytes):
    """Calcula hash MD5 del PDF para detectar duplicados"""
    return hashlib.md5(pdf_bytes).hexdigest()


def validar_nif(nif):
    """
    Valida formato de NIF/CIF español
    
    Args:
        nif: NIF/CIF a validar
    
    Returns:
        bool: True si es válido
    """
    if not nif or len(nif) < 9:
        return False
    
    nif = nif.upper().strip()
    
    # Validación básica de formato
    if len(nif) == 9:
        # Puede ser NIF (8 dígitos + letra) o CIF (letra + 7 dígitos + letra/dígito)
        return True
    
    return False


# ============================================================================
# GESTIÓN DE PROVEEDORES
# ============================================================================

def obtener_proveedores(empresa_id, activos_solo=True):
    """
    Obtiene lista de proveedores de una empresa
    
    Args:
        empresa_id: ID de la empresa
        activos_solo: Si True, solo devuelve activos
    
    Returns:
        list: Lista de proveedores
    """
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = """
        SELECT 
            id, nombre, nif, direccion, cp, poblacion, provincia,
            email, email_facturacion, telefono, iban,
            forma_pago, dias_pago, activo,
            creado_automaticamente, requiere_revision,
            fecha_alta, notas
        FROM proveedores
        WHERE empresa_id = ?
    """
    
    params = [empresa_id]
    
    if activos_solo:
        query += " AND activo = 1"
    
    query += " ORDER BY nombre"
    
    cursor.execute(query, params)
    proveedores = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return proveedores


def obtener_proveedor_por_id(proveedor_id, empresa_id):
    """Obtiene un proveedor por su ID"""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM proveedores
        WHERE id = ? AND empresa_id = ?
    """, (proveedor_id, empresa_id))
    
    proveedor = cursor.fetchone()
    conn.close()
    
    return dict(proveedor) if proveedor else None


def normalizar_nif(nif):
    """
    Normaliza un NIF eliminando guiones, espacios y puntos
    y convirtiéndolo a mayúsculas para comparación
    
    Args:
        nif: NIF a normalizar
    
    Returns:
        str: NIF normalizado (sin guiones, espacios, puntos, en mayúsculas)
    """
    if not nif:
        return ''
    
    # Eliminar guiones, espacios, puntos y convertir a mayúsculas
    nif_normalizado = nif.upper().strip()
    nif_normalizado = nif_normalizado.replace('-', '')
    nif_normalizado = nif_normalizado.replace(' ', '')
    nif_normalizado = nif_normalizado.replace('.', '')
    
    return nif_normalizado


def obtener_proveedor_por_nif(nif, empresa_id):
    """
    Obtiene un proveedor por su NIF
    Busca tanto por NIF exacto como por NIF normalizado para evitar duplicados
    """
    if not nif:
        return None
    
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Normalizar el NIF de búsqueda
    nif_normalizado = normalizar_nif(nif)
    
    # Buscar por NIF exacto primero
    cursor.execute("""
        SELECT * FROM proveedores
        WHERE nif = ? AND empresa_id = ?
    """, (nif.upper().strip(), empresa_id))
    
    proveedor = cursor.fetchone()
    
    # Si no se encuentra, buscar por NIF normalizado
    if not proveedor and nif_normalizado:
        cursor.execute("""
            SELECT * FROM proveedores
            WHERE REPLACE(REPLACE(REPLACE(UPPER(nif), '-', ''), ' ', ''), '.', '') = ? 
            AND empresa_id = ?
        """, (nif_normalizado, empresa_id))
        
        proveedor = cursor.fetchone()
        
        if proveedor:
            logger.info(f"✓ Proveedor encontrado por NIF normalizado: {dict(proveedor)['nombre']} (NIF original: {dict(proveedor)['nif']}, buscado: {nif})")
    
    conn.close()
    
    return dict(proveedor) if proveedor else None


def obtener_proveedor_por_nombre(nombre, empresa_id):
    """
    Obtiene un proveedor por su nombre (búsqueda exacta, case-insensitive)
    """
    if not nombre:
        return None
    
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Buscar por nombre exacto (case-insensitive)
    cursor.execute("""
        SELECT * FROM proveedores
        WHERE LOWER(TRIM(nombre)) = LOWER(TRIM(?)) AND empresa_id = ?
    """, (nombre, empresa_id))
    
    proveedor = cursor.fetchone()
    conn.close()
    
    return dict(proveedor) if proveedor else None


def crear_proveedor(empresa_id, datos, usuario='sistema'):
    """
    Crea un nuevo proveedor
    
    Args:
        empresa_id: ID de la empresa
        datos: Diccionario con datos del proveedor
        usuario: Usuario que crea el proveedor
    
    Returns:
        int: ID del proveedor creado
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Transformar datos a mayúsculas y normalizar NIF
        nombre = datos.get('nombre', '').upper().strip()
        nif = datos.get('nif', '')
        if nif:
            nif = normalizar_nif(nif)  # Guardar siempre normalizado
            
        direccion = datos.get('direccion', '').upper().strip() if datos.get('direccion') else ''
        poblacion = datos.get('poblacion', '').upper().strip() if datos.get('poblacion') else ''
        provincia = datos.get('provincia', '').upper().strip() if datos.get('provincia') else ''
        
        # Validar nombre obligatorio
        if not nombre:
            raise Exception("El nombre del proveedor es obligatorio")

        # Verificar duplicado por nombre (evitar duplicados visuales)
        proveedor_existente_nombre = obtener_proveedor_por_nombre(nombre, empresa_id)
        if proveedor_existente_nombre:
            logger.warning(f"Intento de crear proveedor duplicado por nombre: {nombre}")
            # Si estamos en modo automático (usuario='sistema_auto'), devolvemos el existente
            if usuario == 'sistema_auto':
                return proveedor_existente_nombre['id']
            # Si es manual, lanzamos error
            raise Exception(f"Ya existe un proveedor con el nombre '{nombre}'")
            
        # Verificar duplicado por NIF (si se proporciona)
        if nif:
            proveedor_existente_nif = obtener_proveedor_por_nif(nif, empresa_id)
            if proveedor_existente_nif:
                 # Si coincide nombre y NIF, es claramente el mismo
                if proveedor_existente_nif['nombre'].upper() == nombre:
                    if usuario == 'sistema_auto':
                        return proveedor_existente_nif['id']
                    raise Exception(f"Ya existe este proveedor con NIF {nif}")
                else:
                    # Mismo NIF pero nombre diferente? (Raro pero posible si cambió de nombre)
                    logger.warning(f"Proveedor con mismo NIF {nif} pero distinto nombre: {proveedor_existente_nif['nombre']} vs {nombre}")
                    if usuario == 'sistema_auto':
                        return proveedor_existente_nif['id']
                    raise Exception(f"Ya existe un proveedor con el NIF {nif} ({proveedor_existente_nif['nombre']})")

        # Si el NIF está vacío, permitirlo (para proveedores sin NIF o cuando coincide con empresa)
        if not nif:
            logger.info(f"Creando proveedor sin NIF: {nombre}")
        
        cursor.execute("""
            INSERT INTO proveedores (
                empresa_id, nombre, nif, direccion, cp, poblacion, provincia,
                email, email_facturacion, telefono, iban,
                forma_pago, dias_pago, activo,
                creado_automaticamente, requiere_revision, notas
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            empresa_id,
            nombre,
            nif,
            direccion,
            datos.get('cp'),
            poblacion,
            provincia,
            datos.get('email'),
            datos.get('email_facturacion'),
            datos.get('telefono'),
            datos.get('iban'),
            datos.get('forma_pago', 'transferencia'),
            datos.get('dias_pago', 30),
            datos.get('activo', 1),
            datos.get('creado_automaticamente', 0),
            datos.get('requiere_revision', 0),
            datos.get('notas')
        ))
        
        proveedor_id = cursor.lastrowid
        conn.commit()
        
        nif_info = f"NIF: {nif}" if nif else "sin NIF"
        logger.info(f"✓ Proveedor creado: {datos.get('nombre')} ({nif_info}, ID: {proveedor_id}) por {usuario}")
        
        return proveedor_id
        
    except sqlite3.IntegrityError as e:
        conn.rollback()
        error_msg = str(e).lower()
        if 'unique' in error_msg and 'nif' in error_msg:
            # Buscar el proveedor existente y devolverlo
            logger.warning(f"Proveedor con NIF {nif} ya existe, buscando...")
            proveedor_existente = obtener_proveedor_por_nif(nif, empresa_id)
            if proveedor_existente:
                logger.info(f"✓ Proveedor existente encontrado: {proveedor_existente['nombre']} (ID: {proveedor_existente['id']})")
                return proveedor_existente['id']
            else:
                logger.error(f"Error: Proveedor con NIF {nif} existe pero no se pudo recuperar")
                raise Exception(f"Error de consistencia: proveedor existe pero no se pudo recuperar")
        else:
            logger.error(f"Error de integridad creando proveedor: {e}")
            raise Exception(f"Error de integridad en la base de datos: {str(e)}")
    finally:
        conn.close()


def actualizar_proveedor(proveedor_id, empresa_id, datos, usuario='sistema'):
    """
    Actualiza los datos de un proveedor existente
    
    Args:
        proveedor_id: ID del proveedor
        empresa_id: ID de la empresa (para validar pertenencia)
        datos: Diccionario con datos del proveedor a actualizar
        usuario: Usuario que actualiza el proveedor
    
    Returns:
        bool: True si se actualizó correctamente
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar que el proveedor pertenece a la empresa
        cursor.execute('SELECT id FROM proveedores WHERE id = ? AND empresa_id = ?', 
                      (proveedor_id, empresa_id))
        if not cursor.fetchone():
            raise Exception('Proveedor no encontrado o no pertenece a esta empresa')
        
        # Construir campos a actualizar
        campos = []
        valores = []
        
        if 'nombre' in datos:
            campos.append('nombre = ?')
            valores.append(datos['nombre'].upper().strip())
        
        if 'nif' in datos:
            campos.append('nif = ?')
            # Normalizar NIF al actualizar también
            nif_norm = normalizar_nif(datos['nif'])
            valores.append(nif_norm)
        
        if 'email' in datos:
            campos.append('email = ?')
            valores.append(datos['email'])
        
        if 'telefono' in datos:
            campos.append('telefono = ?')
            valores.append(datos['telefono'])
        
        if 'direccion' in datos:
            campos.append('direccion = ?')
            valores.append(datos['direccion'].upper().strip() if datos['direccion'] else '')
        
        if 'notas' in datos:
            campos.append('notas = ?')
            valores.append(datos['notas'])
        
        if not campos:
            return True  # No hay nada que actualizar
        
        # Agregar ID al final
        valores.append(proveedor_id)
        
        query = f"UPDATE proveedores SET {', '.join(campos)} WHERE id = ?"
        cursor.execute(query, valores)
        conn.commit()
        
        logger.info(f"✓ Proveedor actualizado: ID {proveedor_id} por {usuario}")
        return True
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error actualizando proveedor {proveedor_id}: {e}")
        raise
    finally:
        conn.close()


def eliminar_proveedor(proveedor_id, empresa_id, usuario='sistema'):
    """
    Elimina un proveedor (solo si no tiene facturas asociadas)
    
    Args:
        proveedor_id: ID del proveedor
        empresa_id: ID de la empresa (para validar pertenencia)
        usuario: Usuario que elimina el proveedor
    
    Returns:
        bool: True si se eliminó correctamente
    
    Raises:
        Exception: Si el proveedor tiene facturas asociadas
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar que el proveedor pertenece a la empresa
        cursor.execute('SELECT nombre FROM proveedores WHERE id = ? AND empresa_id = ?', 
                      (proveedor_id, empresa_id))
        proveedor = cursor.fetchone()
        
        if not proveedor:
            raise Exception('Proveedor no encontrado o no pertenece a esta empresa')
        
        nombre_proveedor = proveedor['nombre']
        
        # Verificar si tiene facturas asociadas
        cursor.execute('SELECT COUNT(*) as total FROM facturas_proveedores WHERE proveedor_id = ?', 
                      (proveedor_id,))
        total_facturas = cursor.fetchone()['total']
        
        if total_facturas > 0:
            raise Exception(f'No se puede eliminar el proveedor porque tiene {total_facturas} facturas asociadas')
        
        # Eliminar el proveedor
        cursor.execute('DELETE FROM proveedores WHERE id = ?', (proveedor_id,))
        conn.commit()
        
        logger.info(f"✓ Proveedor eliminado: {nombre_proveedor} (ID: {proveedor_id}) por {usuario}")
        return True
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error eliminando proveedor {proveedor_id}: {e}")
        raise
    finally:
        conn.close()


def obtener_o_crear_proveedor(nif, nombre, empresa_id, datos_adicionales=None, email_origen=None):
    """
    Busca un proveedor por NIF y nombre, si no existe lo crea automáticamente
    Previene duplicados buscando por NIF normalizado y nombre similar
    
    Args:
        nif: NIF del proveedor
        nombre: Nombre del proveedor
        empresa_id: ID de la empresa
        datos_adicionales: Datos extra de la factura
        email_origen: Email del que proviene
    
    Returns:
        int: ID del proveedor
    """
    # 1. Buscar por NIF (con normalización)
    if nif:
        proveedor = obtener_proveedor_por_nif(nif, empresa_id)
        if proveedor:
            logger.info(f"✓ Proveedor encontrado por NIF: {proveedor['nombre']} (ID: {proveedor['id']})")
            return proveedor['id']
    
    # 2. Buscar por nombre exacto (si no se encontró por NIF)
    if nombre:
        proveedor = obtener_proveedor_por_nombre(nombre, empresa_id)
        if proveedor:
            logger.warning(f"⚠️ Proveedor encontrado por nombre (NIF diferente): {proveedor['nombre']} (ID: {proveedor['id']}, NIF: {proveedor.get('nif')} vs {nif})")
            # Actualizar NIF si el proveedor no tenía NIF o era diferente
            if not proveedor.get('nif') and nif:
                logger.info(f"Actualizando NIF del proveedor {proveedor['id']}: {nif}")
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE proveedores SET nif = ? WHERE id = ?", (nif, proveedor['id']))
                conn.commit()
                conn.close()
            return proveedor['id']
    
    # 3. No existe, crear nuevo
    logger.info(f"⚠️ Proveedor no encontrado, creando automáticamente: {nombre} ({nif})")
    
    datos = {
        'nombre': nombre,
        'nif': nif,
        'email_facturacion': email_origen,
        'creado_automaticamente': 1,
        'requiere_revision': 1,  # Marcar para revisión manual
        'activo': 1
    }
    
    # Agregar datos adicionales si existen
    if datos_adicionales:
        if datos_adicionales.get('proveedor_direccion'):
            datos['direccion'] = datos_adicionales['proveedor_direccion']
        if datos_adicionales.get('proveedor_cp'):
            datos['cp'] = datos_adicionales['proveedor_cp']
        if datos_adicionales.get('proveedor_poblacion'):
            datos['poblacion'] = datos_adicionales['proveedor_poblacion']
        if datos_adicionales.get('proveedor_provincia'):
            datos['provincia'] = datos_adicionales['proveedor_provincia']
    
    proveedor_id = crear_proveedor(empresa_id, datos, usuario='sistema_auto')
    
    return proveedor_id


# ============================================================================
# GESTIÓN DE FACTURAS
# ============================================================================

def consultar_facturas_recibidas(empresa_id, filtros=None):
    """
    Consulta facturas recibidas con filtros
    
    Args:
        empresa_id: ID de la empresa
        filtros: Diccionario con filtros opcionales
    
    Returns:
        dict: Facturas y resúmenes
    """
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    filtros = filtros or {}
    
    # Query base
    query = """
        SELECT 
            f.id,
            f.numero_factura,
            f.fecha_emision,
            f.fecha_vencimiento,
            f.base_imponible,
            f.iva_porcentaje,
            f.iva_importe,
            f.total,
            f.estado,
            f.fecha_pago,
            f.metodo_pago,
            f.ruta_archivo,
            f.metodo_extraccion,
            f.confianza_extraccion,
            f.revisado,
            f.concepto,
            p.id as proveedor_id,
            p.nombre as proveedor_nombre,
            p.nif as proveedor_nif,
            CASE 
                WHEN f.estado = 'pagada' THEN '🟢'
                WHEN f.fecha_vencimiento < date('now') AND f.estado != 'pagada' THEN '🔴'
                WHEN f.revisado = 0 THEN '⚠️'
                ELSE '🟡'
            END as icono_estado
        FROM facturas_proveedores f
        INNER JOIN proveedores p ON f.proveedor_id = p.id
        WHERE f.empresa_id = ?
    """
    
    params = [empresa_id]
    
    # Aplicar filtros
    if filtros.get('proveedor_id'):
        query += " AND f.proveedor_id = ?"
        params.append(filtros['proveedor_id'])
    
    if filtros.get('estado') and filtros['estado'] != 'todos':
        if filtros['estado'] == 'vencida':
            query += " AND f.fecha_vencimiento < date('now') AND f.estado != 'pagada'"
        else:
            query += " AND f.estado = ?"
            params.append(filtros['estado'])
    
    if filtros.get('fecha_desde'):
        query += " AND f.fecha_emision >= ?"
        params.append(filtros['fecha_desde'])
    
    if filtros.get('fecha_hasta'):
        query += " AND f.fecha_emision <= ?"
        params.append(filtros['fecha_hasta'])
    
    if filtros.get('trimestre') and filtros['trimestre'] != 'todos':
        if filtros['trimestre'] == 'actual':
            trimestre, año, _, _ = obtener_trimestre_actual()
            query += " AND f.trimestre = ? AND f.año = ?"
            params.extend([trimestre, año])
        else:
            query += " AND f.trimestre = ?"
            params.append(filtros['trimestre'])
    
    if filtros.get('busqueda'):
        query += """ AND (
            f.numero_factura LIKE ? OR
            p.nombre LIKE ? OR
            f.concepto LIKE ?
        )"""
        busqueda = f"%{filtros['busqueda']}%"
        params.extend([busqueda, busqueda, busqueda])
    
    # Contar total CON LOS MISMOS FILTROS (antes de ordenar y paginar)
    query_count = """
        SELECT COUNT(*) as total
        FROM facturas_proveedores f
        INNER JOIN proveedores p ON f.proveedor_id = p.id
        WHERE f.empresa_id = ?
    """
    
    params_count = [empresa_id]
    
    # Aplicar los mismos filtros al conteo
    if filtros.get('proveedor_id'):
        query_count += " AND f.proveedor_id = ?"
        params_count.append(filtros['proveedor_id'])
    
    if filtros.get('estado') and filtros['estado'] != 'todos':
        if filtros['estado'] == 'vencida':
            query_count += " AND f.fecha_vencimiento < date('now') AND f.estado != 'pagada'"
        else:
            query_count += " AND f.estado = ?"
            params_count.append(filtros['estado'])
    
    if filtros.get('fecha_desde'):
        query_count += " AND f.fecha_emision >= ?"
        params_count.append(filtros['fecha_desde'])
    
    if filtros.get('fecha_hasta'):
        query_count += " AND f.fecha_emision <= ?"
        params_count.append(filtros['fecha_hasta'])
    
    if filtros.get('trimestre') and filtros['trimestre'] != 'todos':
        if filtros['trimestre'] == 'actual':
            trimestre, año, _, _ = obtener_trimestre_actual()
            query_count += " AND f.trimestre = ? AND f.año = ?"
            params_count.extend([trimestre, año])
        else:
            query_count += " AND f.trimestre = ?"
            params_count.append(filtros['trimestre'])
    
    if filtros.get('busqueda'):
        query_count += """ AND (
            f.numero_factura LIKE ? OR
            p.nombre LIKE ? OR
            f.concepto LIKE ?
        )"""
        busqueda = f"%{filtros['busqueda']}%"
        params_count.extend([busqueda, busqueda, busqueda])
    
    cursor.execute(query_count, params_count)
    total = cursor.fetchone()['total']
    
    # Ordenamiento
    orden_campo = filtros.get('orden_campo', 'fecha_emision')
    orden_dir = filtros.get('orden_direccion', 'DESC')
    query += f" ORDER BY f.{orden_campo} {orden_dir}"
    
    # Paginación
    pagina = filtros.get('pagina', 1)
    por_pagina = filtros.get('por_pagina', 20)
    offset = (pagina - 1) * por_pagina
    
    query += " LIMIT ? OFFSET ?"
    params.extend([por_pagina, offset])
    
    # Ejecutar consulta de facturas
    cursor.execute(query, params)
    facturas = [dict(row) for row in cursor.fetchall()]
    
    # Calcular resúmenes CON LOS MISMOS FILTROS
    query_resumen = """
        SELECT 
            COALESCE(SUM(f.base_imponible), 0) as total_base,
            COALESCE(SUM(f.iva_importe), 0) as total_iva,
            COALESCE(SUM(f.total), 0) as total_general,
            COALESCE(SUM(CASE WHEN f.estado = 'pendiente' THEN f.total ELSE 0 END), 0) as total_pendiente,
            COALESCE(SUM(CASE WHEN f.estado = 'pagada' THEN f.total ELSE 0 END), 0) as total_pagado,
            COALESCE(SUM(CASE WHEN f.fecha_vencimiento < date('now') AND f.estado != 'pagada' THEN f.total ELSE 0 END), 0) as total_vencido
        FROM facturas_proveedores f
        INNER JOIN proveedores p ON f.proveedor_id = p.id
        WHERE f.empresa_id = ?
    """
    
    params_resumen = [empresa_id]
    
    # Aplicar los mismos filtros que a la consulta principal
    if filtros.get('proveedor_id'):
        query_resumen += " AND f.proveedor_id = ?"
        params_resumen.append(filtros['proveedor_id'])
    
    if filtros.get('estado') and filtros['estado'] != 'todos':
        if filtros['estado'] == 'vencida':
            query_resumen += " AND f.fecha_vencimiento < date('now') AND f.estado != 'pagada'"
        else:
            query_resumen += " AND f.estado = ?"
            params_resumen.append(filtros['estado'])
    
    if filtros.get('fecha_desde'):
        query_resumen += " AND f.fecha_emision >= ?"
        params_resumen.append(filtros['fecha_desde'])
    
    if filtros.get('fecha_hasta'):
        query_resumen += " AND f.fecha_emision <= ?"
        params_resumen.append(filtros['fecha_hasta'])
    
    if filtros.get('trimestre') and filtros['trimestre'] != 'todos':
        if filtros['trimestre'] == 'actual':
            trimestre, año, _, _ = obtener_trimestre_actual()
            query_resumen += " AND f.trimestre = ? AND f.año = ?"
            params_resumen.extend([trimestre, año])
        else:
            query_resumen += " AND f.trimestre = ?"
            params_resumen.append(filtros['trimestre'])
    
    if filtros.get('busqueda'):
        query_resumen += """ AND (
            f.numero_factura LIKE ? OR
            p.nombre LIKE ? OR
            f.concepto LIKE ?
        )"""
        busqueda = f"%{filtros['busqueda']}%"
        params_resumen.extend([busqueda, busqueda, busqueda])
    
    cursor.execute(query_resumen, params_resumen)
    resumen = dict(cursor.fetchone())
    
    conn.close()
    
    return {
        'facturas': facturas,
        'total': total,
        'pagina': pagina,
        'total_paginas': (total + por_pagina - 1) // por_pagina,
        **resumen
    }


def guardar_factura_bd(empresa_id, proveedor_id, datos_factura, ruta_pdf, pdf_hash, email_origen=None, usuario='sistema'):
    """
    Guarda una factura en la base de datos
    
    Args:
        empresa_id: ID de la empresa
        proveedor_id: ID del proveedor
        datos_factura: Diccionario con datos de la factura
        ruta_pdf: Ruta del archivo PDF
        pdf_hash: Hash MD5 del PDF
        email_origen: Email de origen (opcional)
        usuario: Usuario que crea la factura
    
    Returns:
        int: ID de la factura creada
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Calcular trimestre y año
        fecha_emision = datos_factura.get('fecha_emision')
        if fecha_emision:
            fecha_obj = datetime.strptime(fecha_emision, '%Y-%m-%d')
            mes = fecha_obj.month
            año = fecha_obj.year
            trimestre = f"Q{(mes - 1) // 3 + 1}"
        else:
            trimestre, año, _, _ = obtener_trimestre_actual()
        
        # Calcular fecha de vencimiento si no viene
        fecha_vencimiento = datos_factura.get('fecha_vencimiento')
        if not fecha_vencimiento and fecha_emision:
            # Obtener días de pago del proveedor
            cursor.execute("SELECT dias_pago FROM proveedores WHERE id = ?", (proveedor_id,))
            prov = cursor.fetchone()
            dias_pago = prov['dias_pago'] if prov else 30
            
            fecha_obj = datetime.strptime(fecha_emision, '%Y-%m-%d')
            fecha_venc_obj = fecha_obj + timedelta(days=dias_pago)
            fecha_vencimiento = fecha_venc_obj.strftime('%Y-%m-%d')
        
        # Calcular IVA si no viene
        iva_importe = datos_factura.get('iva_importe')
        if not iva_importe:
            base = datos_factura.get('base_imponible', 0)
            iva_pct = datos_factura.get('iva_porcentaje', 21)
            iva_importe = round(base * iva_pct / 100, 2)
        
        # Marcar como pagada automáticamente con fecha de emisión como fecha de pago
        fecha_pago = fecha_emision if fecha_emision else datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute("""
            INSERT INTO facturas_proveedores (
                empresa_id, proveedor_id, numero_factura,
                fecha_emision, fecha_vencimiento,
                base_imponible, iva_porcentaje, iva_importe, total,
                estado, fecha_pago, metodo_pago,
                ruta_archivo, pdf_hash, email_origen,
                trimestre, año,
                metodo_extraccion, confianza_extraccion, revisado,
                usuario_alta, concepto, notas
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            empresa_id,
            proveedor_id,
            datos_factura.get('numero_factura'),
            fecha_emision,
            fecha_vencimiento,
            datos_factura.get('base_imponible'),
            datos_factura.get('iva_porcentaje', 21),
            iva_importe,
            datos_factura.get('total'),
            'pagada',  # Marcar como pagada automáticamente
            fecha_pago,  # Fecha de pago = fecha de emisión
            'transferencia',  # Método de pago por defecto
            ruta_pdf,
            pdf_hash,
            email_origen,
            trimestre,
            año,
            datos_factura.get('metodo_extraccion'),
            datos_factura.get('confianza_extraccion'),
            0,  # Requiere revisión
            usuario,
            datos_factura.get('concepto'),
            datos_factura.get('notas')
        ))
        
        factura_id = cursor.lastrowid
        conn.commit()
        
        logger.info(f"✓ Factura guardada: {datos_factura.get('numero_factura')} (ID: {factura_id})")
        
        return factura_id
        
    except sqlite3.IntegrityError as e:
        conn.rollback()
        if 'UNIQUE constraint failed' in str(e):
            if 'pdf_hash' in str(e):
                raise Exception("Esta factura ya fue procesada anteriormente (PDF duplicado)")
            else:
                raise Exception("Ya existe una factura con ese número para este proveedor")
        raise Exception(f"Error guardando factura: {e}")
    finally:
        conn.close()


def factura_ya_procesada(pdf_hash, empresa_id):
    """Verifica si una factura ya fue procesada por su hash"""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id FROM facturas_proveedores
        WHERE pdf_hash = ? AND empresa_id = ?
    """, (pdf_hash, empresa_id))
    
    existe = cursor.fetchone() is not None
    conn.close()
    
    return existe



def obtener_factura_por_id(factura_id, empresa_id):
    """Obtiene una factura por su ID"""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Obtener datos principales
    cursor.execute("""
        SELECT 
            f.*,
            p.nombre as proveedor_nombre,
            p.nif as proveedor_nif,
            p.direccion as proveedor_direccion,
            p.telefono as proveedor_telefono,
            CASE 
                WHEN f.estado = 'pagada' THEN '🟢'
                WHEN f.fecha_vencimiento < date('now') AND f.estado != 'pagada' THEN '🔴'
                WHEN f.revisado = 0 THEN '⚠️'
                ELSE '🟡'
            END as icono_estado
        FROM facturas_proveedores f
        INNER JOIN proveedores p ON f.proveedor_id = p.id
        WHERE f.id = ? AND f.empresa_id = ?
    """, (factura_id, empresa_id))
    
    factura = cursor.fetchone()
    
    if not factura:
        conn.close()
        return None
    
    factura_dict = dict(factura)
    
    # Obtener líneas
    cursor.execute("""
        SELECT * FROM lineas_factura_proveedor
        WHERE factura_id = ?
    """, (factura_id,))
    factura_dict['lineas'] = [dict(row) for row in cursor.fetchall()]
    
    # Obtener historial
    cursor.execute("""
        SELECT * FROM historial_facturas_proveedores
        WHERE factura_id = ?
        ORDER BY fecha DESC
    """, (factura_id,))
    factura_dict['historial'] = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return factura_dict


def actualizar_factura_proveedor(factura_id, empresa_id, datos, usuario='sistema'):
    """Actualiza una factura existente"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar existencia y obtener datos anteriores
        cursor.execute("SELECT * FROM facturas_proveedores WHERE id = ? AND empresa_id = ?", 
                      (factura_id, empresa_id))
        factura_anterior = cursor.fetchone()
        
        if not factura_anterior:
            raise Exception("Factura no encontrada")
            
        # Campos permitidos para actualizar
        campos_permitidos = [
            'numero_factura', 'fecha_emision', 'fecha_vencimiento',
            'base_imponible', 'iva_porcentaje', 'iva_importe', 'total',
            'concepto', 'notas', 'revisado', 'estado'
        ]
        
        campos_update = []
        valores = []
        
        for campo in campos_permitidos:
            if campo in datos:
                campos_update.append(f"{campo} = ?")
                valores.append(datos[campo])
        
        if not campos_update:
            return True
            
        # Recalcular trimestre y año si cambia la fecha
        if 'fecha_emision' in datos:
            fecha_obj = datetime.strptime(datos['fecha_emision'], '%Y-%m-%d')
            mes = fecha_obj.month
            año = fecha_obj.year
            trimestre = f"Q{(mes - 1) // 3 + 1}"
            
            campos_update.append("trimestre = ?")
            valores.append(trimestre)
            campos_update.append("año = ?")
            valores.append(año)
        
        valores.append(factura_id)
        
        query = f"UPDATE facturas_proveedores SET {', '.join(campos_update)} WHERE id = ?"
        cursor.execute(query, valores)
        
        conn.commit()
        
        # Registrar en historial
        registrar_historial(factura_id, 'actualizacion', usuario, 
                           datos_anteriores=dict(factura_anterior), 
                           datos_nuevos=datos)
        
        return True
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error actualizando factura {factura_id}: {e}")
        raise
    finally:
        conn.close()


def eliminar_factura(factura_id, empresa_id, usuario='sistema'):
    """Elimina una factura y sus archivos asociados"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Obtener datos para borrar archivo
        cursor.execute("SELECT ruta_archivo FROM facturas_proveedores WHERE id = ? AND empresa_id = ?", 
                      (factura_id, empresa_id))
        factura = cursor.fetchone()
        
        if not factura:
            raise Exception("Factura no encontrada")
            
        # Eliminar de BD (cascade eliminará líneas e historial si está configurado, sino hacerlo manual)
        cursor.execute("DELETE FROM facturas_proveedores WHERE id = ?", (factura_id,))
        conn.commit()
        
        # Eliminar archivo físico si existe
        ruta_archivo = factura['ruta_archivo']
        if ruta_archivo and os.path.exists(ruta_archivo):
            try:
                os.remove(ruta_archivo)
                logger.info(f"Archivo eliminado: {ruta_archivo}")
            except Exception as e:
                logger.error(f"Error eliminando archivo {ruta_archivo}: {e}")
        
        logger.info(f"✓ Factura eliminada: ID {factura_id} por {usuario}")
        return True
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error eliminando factura {factura_id}: {e}")
        raise
    finally:
        conn.close()


def registrar_pago_factura(factura_id, empresa_id, datos_pago, usuario='sistema'):
    """Registra el pago de una factura"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM facturas_proveedores WHERE id = ? AND empresa_id = ?", 
                      (factura_id, empresa_id))
        factura = cursor.fetchone()
        
        if not factura:
            raise Exception("Factura no encontrada")
            
        cursor.execute("""
            UPDATE facturas_proveedores 
            SET estado = 'pagada', 
                fecha_pago = ?, 
                metodo_pago = ?,
                referencia_pago = ?
            WHERE id = ?
        """, (
            datos_pago.get('fecha_pago'),
            datos_pago.get('metodo_pago'),
            datos_pago.get('referencia_pago'),
            factura_id
        ))
        
        conn.commit()
        
        registrar_historial(factura_id, 'pago_registrado', usuario, 
                           datos_nuevos=datos_pago)
        
        return True
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error registrando pago factura {factura_id}: {e}")
        raise
    finally:
        conn.close()


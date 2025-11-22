"""
Servicios comunes y utilidades para la aplicación
"""

from decimal import Decimal
from datetime import datetime
from logger_config import get_logger
from db_utils import get_db_connection

logger = get_logger('aleph70.common_services')

def _to_decimal(val, default='0'):
    """Convierte un valor a Decimal de forma segura"""
    try:
        return Decimal(str(val).replace(',', '.'))
    except Exception:
        return Decimal(default)


def format_date(date_value):
    """Función auxiliar para formatear fechas en formato DD/MM/AAAA"""
    if date_value is None:
        return None
    
    if isinstance(date_value, str):
        try:
            # Intentar parsear si es string
            date_obj = datetime.strptime(date_value, '%Y-%m-%d')
            return date_obj.strftime('%d/%m/%Y')
        except ValueError:
            try:
                date_obj = datetime.strptime(date_value, '%Y-%m-%d %H:%M:%S')
                return date_obj.strftime('%d/%m/%Y')
            except ValueError:
                return date_value
    
    if hasattr(date_value, 'strftime'):
        return date_value.strftime('%d/%m/%Y')
    
    return str(date_value)


def validate_required_fields(data, required_fields):
    """
    Valida que los campos requeridos estén presentes en los datos
    
    Args:
        data (dict): Diccionario con los datos
        required_fields (list): Lista de campos requeridos
        
    Returns:
        dict: {'valid': bool, 'errors': [str]}
    """
    errors = []
    
    if not isinstance(data, dict):
        return {'valid': False, 'errors': ['Los datos deben ser un diccionario']}
    
    for field in required_fields:
        if field not in data or data[field] is None or str(data[field]).strip() == '':
            errors.append(f'El campo {field} es requerido')
    
    return {'valid': len(errors) == 0, 'errors': errors}


def sanitize_sql_params(params):
    """
    Sanitiza parámetros para consultas SQL
    
    Args:
        params (dict): Parámetros a sanitizar
        
    Returns:
        dict: Parámetros sanitizados
    """
    sanitized = {}
    
    for key, value in params.items():
        if value is None:
            sanitized[key] = None
        elif isinstance(value, str):
            # Limitar longitud y escapar caracteres peligrosos
            sanitized[key] = value.strip()[:1000]  # Limitar a 1000 chars
        elif isinstance(value, (int, float, Decimal)):
            sanitized[key] = value
        else:
            # Convertir a string y sanitizar
            sanitized[key] = str(value).strip()[:1000]
    
    return sanitized


def build_pagination_response(data, page, page_size, total_count, extra_data=None):
    """
    Construye respuesta estándar de paginación
    
    Args:
        data (list): Datos de la página
        page (int): Página actual
        page_size (int): Tamaño de página
        total_count (int): Total de registros
        extra_data (dict): Datos adicionales
        
    Returns:
        dict: Respuesta de paginación estandarizada
    """
    total_pages = (total_count + page_size - 1) // page_size
    
    response = {
        'success': True,
        'data': data,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total_count': total_count,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
    }
    
    if extra_data:
        response.update(extra_data)
    
    return response


def execute_query_with_pagination(query, params, page=1, page_size=25, count_query=None):
    """
    Ejecuta una consulta con paginación
    
    Args:
        query (str): Consulta SQL principal
        params (tuple): Parámetros para la consulta
        page (int): Página a obtener
        page_size (int): Tamaño de página
        count_query (str): Consulta para contar total (opcional)
        
    Returns:
        dict: Resultado con datos y paginación
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener total de registros
        if count_query:
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()[0]
        else:
            # Crear query de conteo automática
            count_query_auto = f"SELECT COUNT(*) FROM ({query})"
            cursor.execute(count_query_auto, params)
            total_count = cursor.fetchone()[0]
        
        # Calcular offset
        offset = (page - 1) * page_size
        
        # Ejecutar consulta con paginación
        paginated_query = f"{query} LIMIT {page_size} OFFSET {offset}"
        cursor.execute(paginated_query, params)
        data = cursor.fetchall()
        
        return {
            'success': True,
            'data': data,
            'total_count': total_count,
            'page': page,
            'page_size': page_size
        }
        
    except Exception as e:
        logger.error(f"Error ejecutando consulta paginada: {e}")
        return {
            'success': False,
            'error': str(e),
            'data': [],
            'total_count': 0
        }
    finally:
        if 'conn' in locals():
            conn.close()


def log_user_action(user_id, action, resource_type, resource_id=None, details=None):
    """
    Registra acciones de usuario para auditoría
    
    Args:
        user_id (int): ID del usuario
        action (str): Acción realizada (create, update, delete, view, etc.)
        resource_type (str): Tipo de recurso (factura, contacto, etc.)
        resource_id (int): ID del recurso afectado
        details (dict): Detalles adicionales
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insertar log de auditoría
        cursor.execute('''
            INSERT INTO auditoria_usuarios 
            (user_id, action, resource_type, resource_id, details, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            action,
            resource_type,
            resource_id,
            str(details) if details else None,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        
    except Exception as e:
        logger.error(f"Error registrando acción de usuario: {e}")
        # No fallar la operación principal por error de logging
    finally:
        if 'conn' in locals():
            conn.close()


def calculate_totals(lines, tax_rate=0.21):
    """
    Calcula totales de una lista de líneas
    
    Args:
        lines (list): Lista de líneas con cantidad, precio, descuento
        tax_rate (float): Tasa de impuesto (por defecto 21%)
        
    Returns:
        dict: Diccionario con subtotal, descuentos, impuestos, total
    """
    subtotal = Decimal('0')
    total_descuento = Decimal('0')
    
    for line in lines:
        cantidad = _to_decimal(line.get('cantidad', 0))
        precio = _to_decimal(line.get('precio', 0))
        descuento_pct = _to_decimal(line.get('descuento', 0))
        
        # Calcular subtotal de línea
        subtotal_linea = cantidad * precio
        descuento_linea = subtotal_linea * (descuento_pct / 100)
        subtotal_linea_final = subtotal_linea - descuento_linea
        
        subtotal += subtotal_linea_final
        total_descuento += descuento_linea
    
    # Calcular impuestos
    impuestos = subtotal * _to_decimal(tax_rate)
    
    # Total final
    total = subtotal + impuestos
    
    return {
        'subtotal': float(subtotal),
        'descuentos': float(total_descuento),
        'impuestos': float(impuestos),
        'total': float(total),
        'tax_rate': tax_rate
    }


def generate_next_number(table_name, field_name, prefix='', year_based=True):
    """
    Genera el siguiente número correlativo para una tabla
    
    Args:
        table_name (str): Nombre de la tabla
        field_name (str): Campo que contiene el número
        prefix (str): Prefijo del número
        year_based (bool): Si el numerador se reinicia cada año
        
    Returns:
        str: Siguiente número generado
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if year_based:
            current_year = datetime.now().year
            # Buscar el último número del año actual
            cursor.execute(f'''
                SELECT MAX(CAST(SUBSTR({field_name}, LENGTH(?) + 1) AS INTEGER))
                FROM {table_name}
                WHERE {field_name} LIKE ? || ?
            ''', (prefix, prefix, f'{current_year}%'))
        else:
            # Buscar el último número global
            cursor.execute(f'''
                SELECT MAX(CAST(SUBSTR({field_name}, LENGTH(?) + 1) AS INTEGER))
                FROM {table_name}
                WHERE {field_name} LIKE ? || '%'
            ''', (prefix, prefix))
        
        result = cursor.fetchone()
        last_number = result[0] if result and result[0] else 0
        
        next_number = last_number + 1
        
        if year_based:
            return f"{prefix}{current_year}{next_number:04d}"
        else:
            return f"{prefix}{next_number:06d}"
            
    except Exception as e:
        logger.error(f"Error generando siguiente número: {e}")
        # Fallback: usar timestamp
        timestamp = int(datetime.now().timestamp())
        return f"{prefix}{timestamp}"
    finally:
        if 'conn' in locals():
            conn.close()

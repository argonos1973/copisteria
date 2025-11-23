"""
Rutas relacionadas con productos y franjas de descuento
"""

from flask import Blueprint, jsonify, request
from auth_middleware import login_required
import productos
import productos_franjas_utils
from logger_config import get_logger
from db_utils import get_db_connection

logger = get_logger('aleph70.productos_routes')

# Blueprint para las rutas de productos
productos_bp = Blueprint('productos', __name__)

@productos_bp.route('/api/productos', methods=['GET'])
@login_required
def obtener_todos_productos():
    """Obtiene todos los productos"""
    try:
        lista_productos = productos.obtener_productos()
        return jsonify(lista_productos)
    except Exception as e:
        logger.error(f"Error obteniendo productos: {e}")
        return jsonify({'error': str(e)}), 500

@productos_bp.route('/api/productos/paginado', methods=['GET'])
@login_required
def obtener_productos_paginado_route():
    """Obtiene productos paginados"""
    try:
        page = request.args.get('page', 1)
        page_size = request.args.get('page_size', 20)
        sort_by = request.args.get('sort', 'nombre')
        order = request.args.get('order', 'ASC')
        
        # El frontend envía 'nombre' como término de búsqueda, lo mapeamos a search_term
        search_term = request.args.get('search') or request.args.get('nombre')
        
        resultado = productos.obtener_productos_paginado(
            page=page, 
            page_size=page_size, 
            sort_by=sort_by, 
            order=order, 
            search_term=search_term
        )
        return jsonify(resultado)
    except Exception as e:
        logger.error(f"Error en endpoint productos paginado: {e}")
        return jsonify({'error': str(e)}), 500

@productos_bp.route('/api/productos/aplicar_franjas', methods=['POST'])
def api_aplicar_franjas_todos():
    try:
        # Permitir parámetros por query o body JSON
        args = request.get_json(silent=True) or {}
        
        porcentaje_base = args.get('porcentaje_base', request.args.get('porcentaje_base', 10))
        incremento = args.get('incremento', request.args.get('incremento', 5))
        num_franjas = args.get('num_franjas', request.args.get('num_franjas', 5))
        
        try:
            porcentaje_base = float(porcentaje_base)
            incremento = float(incremento)
            num_franjas = int(num_franjas)
        except ValueError as e:
            return jsonify({'error': f'Parámetros inválidos: {e}'}), 400
        
        # Aplicar franjas a todos los productos
        resultado = productos_franjas_utils.aplicar_franjas_automaticas_todos(
            porcentaje_base, incremento, num_franjas
        )
        
        return jsonify({
            'success': True, 
            'mensaje': f'Franjas aplicadas a {resultado} productos'
        })
        
    except Exception as e:
        logger.error(f"Error aplicando franjas: {e}")
        return jsonify({'error': str(e)}), 500


@productos_bp.route('/api/debug/schema_productos', methods=['GET'])
def debug_schema_productos():
    try:
        with get_db_connection() as conn:
            if not conn:
                return jsonify({'error': 'No se pudo conectar a la base de datos'}), 500
            
            cursor = conn.cursor()
            
            # Obtener esquema de la tabla productos
            cursor.execute("PRAGMA table_info(productos)")
            schema = cursor.fetchall()
            
            # Formatear resultado
            columnas = []
            for col in schema:
                columnas.append({
                    'cid': col[0],
                    'name': col[1],
                    'type': col[2],
                    'notnull': col[3],
                    'default_value': col[4],
                    'pk': col[5]
                })
            
            # Obtener algunos registros de ejemplo
            cursor.execute("SELECT * FROM productos LIMIT 5")
            ejemplos = cursor.fetchall()
            
            return jsonify({
                'success': True,
                'schema': columnas,
                'ejemplos': ejemplos,
                'total_columnas': len(columnas)
            })
        
    except Exception as e:
        logger.error(f"Error obteniendo schema productos: {e}")
        return jsonify({'error': str(e)}), 500


@productos_bp.route('/api/productos/<int:producto_id>', methods=['GET'])
@login_required
def obtener_producto_individual(producto_id):
    try:
        producto = productos.obtener_producto(producto_id)
        if producto:
            return jsonify(producto)
        else:
            return jsonify({'error': 'Producto no encontrado'}), 404
    except Exception as e:
        logger.error(f"Error obteniendo producto {producto_id}: {e}")
        return jsonify({'error': str(e)}), 500


@productos_bp.route('/api/productos/<int:producto_id>', methods=['DELETE'])
@login_required
def eliminar_producto_route(producto_id):
    try:
        resultado = productos.eliminar_producto(producto_id)
        return jsonify(resultado)
    except Exception as e:
        logger.error(f"Error eliminando producto {producto_id}: {e}")
        return jsonify({'error': str(e)}), 500


@productos_bp.route('/api/productos/<int:producto_id>', methods=['PUT'])
@login_required
def actualizar_producto_rest(producto_id):
    try:
        data = request.get_json()
        # Asegurar que el ID del payload coincide
        data['id'] = producto_id
        return jsonify(productos.actualizar_producto(producto_id, data))
    except Exception as e:
        logger.error(f"Error actualizando producto {producto_id}: {e}")
        return jsonify({'error': str(e)}), 500


@productos_bp.route('/api/productos', methods=['POST'])
@login_required
def crear_producto_rest():
    try:
        data = request.get_json()
        return jsonify(productos.crear_producto(data))
    except Exception as e:
        logger.error(f"Error creando producto: {e}")
        return jsonify({'error': str(e)}), 500


@productos_bp.route('/api/productos/<int:producto_id>/franjas_descuento', methods=['GET'])
@productos_bp.route('/productos/<int:producto_id>/franjas_descuento', methods=['GET'])
def api_get_franjas_descuento_producto(producto_id):
    try:
        franjas = productos.obtener_franjas_descuento_por_producto(producto_id)
        try:
            return jsonify({'success': True, 'franjas': franjas})
        except Exception as json_e:
            logger.error(f"Error serializando franjas: {json_e}")
            return jsonify({'error': f'Error procesando datos: {json_e}'}), 500
    except Exception as e:
        logger.error(f"Error obteniendo franjas: {e}")
        return jsonify({'error': str(e)}), 500


@productos_bp.route('/api/productos/<int:producto_id>/franjas_descuento', methods=['POST', 'PUT'])
@productos_bp.route('/productos/<int:producto_id>/franjas_descuento', methods=['POST', 'PUT'])
def api_set_franjas_descuento_producto(producto_id):
    try:
        body = request.get_json() or {}
        try:
            franjas_data = body.get('franjas', [])
            if not isinstance(franjas_data, list):
                return jsonify({'error': 'Las franjas deben ser una lista'}), 400
                
            # Guardar franjas
            resultado = productos.guardar_franjas_descuento_producto(producto_id, franjas_data)
            return jsonify({'success': True, 'mensaje': 'Franjas guardadas correctamente'})
            
        except Exception as save_e:
            logger.error(f"Error guardando franjas: {save_e}")
            return jsonify({'error': f'Error guardando: {save_e}'}), 500
            
    except Exception as e:
        logger.error(f"Error procesando franjas: {e}")
        return jsonify({'error': str(e)}), 500


@productos_bp.route('/api/productos/<int:producto_id>/franjas_config', methods=['GET'])
def api_get_franjas_config_producto(producto_id):
    """Obtiene la configuración de franjas automáticas de un producto"""
    try:
        config = productos_franjas_utils.obtener_configuracion_franjas_producto(producto_id)
        return jsonify({'success': True, 'config': config})
    except Exception as e:
        logger.error(f"Error obteniendo config franjas: {e}")
        return jsonify({'error': str(e)}), 500


@productos_bp.route('/api/productos/<int:producto_id>/franjas_config', methods=['POST', 'PUT'])
def api_set_franjas_config_producto(producto_id):
    """Actualiza la configuración de franjas automáticas de un producto"""
    try:
        config = request.get_json() or {}
        resultado = productos_franjas_utils.guardar_configuracion_franjas_producto(producto_id, config)
        return jsonify({'success': True, 'mensaje': 'Configuración guardada'})
    except Exception as e:
        logger.error(f"Error guardando config franjas: {e}")
        return jsonify({'error': str(e)}), 500


@productos_bp.route('/api/productos/<int:producto_id>/generar_franjas_automaticas', methods=['POST'])
def api_generar_franjas_automaticas(producto_id):
    """Genera franjas automáticas basadas en la configuración del producto"""
    try:
        # Obtener configuración actual
        config = productos_franjas_utils.obtener_configuracion_franjas_producto(producto_id)
        
        if not config:
            return jsonify({'error': 'No hay configuración de franjas para este producto'}), 400
        
        # Generar franjas automáticas
        franjas_generadas = productos_franjas_utils.generar_franjas_automaticas_producto(
            producto_id, config
        )
        
        return jsonify({
            'success': True, 
            'franjas_generadas': len(franjas_generadas),
            'franjas': franjas_generadas
        })
        
    except Exception as e:
        logger.error(f"Error generando franjas automáticas: {e}")
        return jsonify({'error': str(e)}), 500


@productos_bp.route('/api/productos/guardar', methods=['POST'])
@login_required
def guardar_producto_legacy():
    """Endpoint de compatibilidad para guardar/actualizar productos"""
    try:
        data = request.get_json()
        if data and data.get('id'):
            return jsonify(productos.actualizar_producto(data['id'], data))
        else:
            return jsonify(productos.crear_producto(data))
    except Exception as e:
        logger.error(f"Error en guardar_producto_legacy: {e}")
        return jsonify({'error': str(e)}), 500


@productos_bp.route('/api/productos/actualizar', methods=['POST', 'PUT'])
@login_required
def actualizar_producto_legacy():
    """Endpoint de compatibilidad para actualizar productos"""
    try:
        data = request.get_json()
        if not data or not data.get('id'):
            return jsonify({'error': 'ID de producto requerido'}), 400
        return jsonify(productos.actualizar_producto(data['id'], data))
    except Exception as e:
        logger.error(f"Error en actualizar_producto_legacy: {e}")
        return jsonify({'error': str(e)}), 500

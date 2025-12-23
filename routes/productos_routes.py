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
        
        # Validación de seguridad: body debe ser un diccionario
        if not isinstance(body, dict):
            # Si es una lista, quizás enviaron las franjas directamente
            if isinstance(body, list):
                logger.warning(f"Recibida lista directa de franjas para producto {producto_id}, adaptando...")
                body = {'franjas': body}
            else:
                return jsonify({'error': 'Formato JSON inválido: se esperaba un objeto'}), 400

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


@productos_bp.route('/api/productos/importar-csv', methods=['POST'])
@login_required
def importar_productos_csv():
    """
    Importa productos desde un archivo CSV.
    Formato CSV (separador ;):
    nombre;subtotal;iva%;descripcion
    
    Ejemplo:
    XAPA 25MM;0.70;21;
    Las franjas se generan automáticamente.
    """
    import csv
    import io
    
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No se envió ningún archivo'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nombre de archivo vacío'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'El archivo debe ser CSV'}), 400
        
        # Leer contenido del archivo
        content = file.read().decode('utf-8-sig')  # utf-8-sig para manejar BOM
        reader = csv.reader(io.StringIO(content), delimiter=';')
        
        productos_creados = 0
        productos_actualizados = 0
        errores = []
        
        # Configuración por defecto para franjas
        default_config = {
            'franja_inicial': 1,
            'numero_franjas': 50,
            'ancho_franja': 10,
            'descuento_inicial': 5.0,
            'incremento_franja': 5.0
        }
        
        logger.info(f"[CSV] Iniciando procesamiento de CSV")
        
        for i, row in enumerate(reader, 1):
            logger.info(f"[CSV] Fila {i}: {row}")
            
            # Saltar cabecera si existe
            if i == 1 and row and row[0].lower() in ['nombre', 'producto', 'name']:
                logger.info(f"[CSV] Saltando cabecera")
                continue
            
            if not row or len(row) < 2:
                logger.info(f"[CSV] Fila vacía o insuficiente, saltando")
                continue
            
            try:
                nombre = row[0].strip().upper()
                if not nombre:
                    logger.info(f"[CSV] Nombre vacío, saltando")
                    continue
                
                subtotal = float(row[1].replace(',', '.')) if row[1] else 0.0
                logger.info(f"[CSV] Procesando: {nombre}, subtotal={subtotal}")
                iva_porcentaje = int(row[2]) if len(row) > 2 and row[2] else 21
                descripcion = row[3].strip() if len(row) > 3 else ''
                
                # Calcular IVA y total
                iva_importe = round(subtotal * iva_porcentaje / 100, 2)
                total = round(subtotal + iva_importe, 2)
                
                # Verificar si el producto ya existe
                producto_id = None
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM productos WHERE UPPER(nombre) = ?", (nombre,))
                    existing = cursor.fetchone()
                    
                    if existing:
                        # Actualizar producto existente
                        producto_id = existing[0]
                        cursor.execute("""
                            UPDATE productos 
                            SET subtotal=?, iva=?, impuestos=?, total=?, descripcion=?, no_generar_franjas=0, calculo_automatico=1
                            WHERE id=?
                        """, (subtotal, iva_importe, iva_porcentaje, total, descripcion, producto_id))
                        productos_actualizados += 1
                    else:
                        # Crear nuevo producto (incluir ejercicio actual)
                        from datetime import datetime
                        ejercicio_actual = datetime.now().year
                        cursor.execute("""
                            INSERT INTO productos (nombre, descripcion, subtotal, iva, impuestos, total, calculo_automatico, no_generar_franjas, ejercicio)
                            VALUES (?, ?, ?, ?, ?, ?, 1, 0, ?)
                        """, (nombre, descripcion, subtotal, iva_importe, iva_porcentaje, total, ejercicio_actual))
                        producto_id = cursor.lastrowid
                        productos_creados += 1
                    
                    conn.commit()
                
                # Generar y guardar franjas automáticas (fuera del with para evitar lock)
                if producto_id:
                    try:
                        franjas = productos_franjas_utils.generar_franjas_automaticas(producto_id, default_config)
                        productos.reemplazar_franjas_descuento_producto(producto_id, franjas)
                    except Exception as fe:
                        logger.warning(f"Error generando franjas para producto {producto_id}: {fe}")
                    
            except Exception as row_e:
                errores.append(f"Fila {i}: {str(row_e)}")
                logger.warning(f"Error en fila {i}: {row_e}")
        
        return jsonify({
            'success': True,
            'productos_creados': productos_creados,
            'productos_actualizados': productos_actualizados,
            'errores': errores[:10]  # Limitar errores mostrados
        })
        
    except Exception as e:
        logger.error(f"Error importando CSV: {e}")
        return jsonify({'error': str(e)}), 500


@productos_bp.route('/api/productos/plantilla-csv', methods=['GET'])
@login_required
def descargar_plantilla_csv():
    """Descarga una plantilla CSV de ejemplo para importación"""
    from flask import Response
    
    plantilla = """nombre;subtotal;iva%;descripcion
PRODUCTO EJEMPLO;10.00;21;Descripción opcional
XAPA 25MM;0.70;21;
"""
    
    return Response(
        plantilla,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=plantilla_productos.csv'}
    )

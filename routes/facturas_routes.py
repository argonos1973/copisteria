"""
Rutas relacionadas con facturas y facturación
"""

from flask import Blueprint, jsonify, request
from auth_middleware import login_required
import factura
from logger_config import get_logger

logger = get_logger('aleph70.facturas_routes')

# Blueprint para las rutas de facturas
facturas_bp = Blueprint('facturas', __name__)

@login_required
@facturas_bp.route('/api/facturas/paginado', methods=['GET'])
@login_required
def api_facturas_paginado():
    return facturas_paginado()


@facturas_bp.route('/facturas/paginado', methods=['GET'])
@login_required
def facturas_paginado():
    try:
        # Filtros de consulta
        fecha_inicio = request.args.get('fecha_inicio', '')
        fecha_fin = request.args.get('fecha_fin', '')
        numero_factura = request.args.get('numero_factura', '')
        cliente = request.args.get('cliente', '')
        estado = request.args.get('estado', '')
        
        # Parámetros de paginación
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('pageSize', 25))
        sort = request.args.get('sort', 'fecha')
        order = request.args.get('order', 'DESC')
        
        # Construir filtros
        filtros = {}
        if fecha_inicio:
            filtros['fecha_inicio'] = fecha_inicio
        if fecha_fin:
            filtros['fecha_fin'] = fecha_fin
        if numero_factura:
            filtros['numero_factura'] = numero_factura
        if cliente:
            filtros['cliente'] = cliente
        if estado:
            filtros['estado'] = estado
        
        # Obtener facturas paginadas
        resultado = factura.obtener_facturas_paginadas(filtros, page, page_size, sort, order)
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error en facturas paginado: {e}")
        return jsonify({'error': str(e)}), 500


@facturas_bp.route('/api/facturas/<int:factura_id>', methods=['GET'])
@login_required
def obtener_factura_detalle(factura_id):
    """Obtiene el detalle de una factura específica"""
    try:
        factura_data = factura.obtener_factura_completa(factura_id)
        if factura_data:
            return jsonify({
                'success': True,
                'factura': factura_data
            })
        else:
            return jsonify({'error': 'Factura no encontrada'}), 404
            
    except Exception as e:
        logger.error(f"Error obteniendo factura {factura_id}: {e}")
        return jsonify({'error': str(e)}), 500


@facturas_bp.route('/api/facturas', methods=['POST'])
@login_required
def crear_factura():
    """Crea una nueva factura"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
        
        # Validar datos requeridos
        if not data.get('idcontacto'):
            return jsonify({'error': 'ID de contacto es requerido'}), 400
        
        if not data.get('lineas') or len(data.get('lineas', [])) == 0:
            return jsonify({'error': 'La factura debe tener al menos una línea'}), 400
        
        # Crear factura
        resultado = factura.crear_factura(data)
        
        if resultado['success']:
            return jsonify(resultado), 201
        else:
            return jsonify(resultado), 400
            
    except Exception as e:
        logger.error(f"Error creando factura: {e}")
        return jsonify({'error': str(e)}), 500


@facturas_bp.route('/api/facturas/<int:factura_id>', methods=['PUT'])
@login_required
def actualizar_factura(factura_id):
    """Actualiza una factura existente"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
        
        # Verificar que la factura existe
        factura_existente = factura.obtener_factura(factura_id)
        if not factura_existente:
            return jsonify({'error': 'Factura no encontrada'}), 404
        
        # Actualizar factura
        resultado = factura.actualizar_factura(factura_id, data)
        
        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 400
            
    except Exception as e:
        logger.error(f"Error actualizando factura {factura_id}: {e}")
        return jsonify({'error': str(e)}), 500


@facturas_bp.route('/api/facturas/<int:factura_id>', methods=['DELETE'])
@login_required
def eliminar_factura(factura_id):
    """Elimina una factura"""
    try:
        # Verificar que la factura existe
        factura_existente = factura.obtener_factura(factura_id)
        if not factura_existente:
            return jsonify({'error': 'Factura no encontrada'}), 404
        
        # Verificar si se puede eliminar (ej: no esté cobrada)
        if factura_existente.get('estado') == 'cobrada':
            return jsonify({'error': 'No se puede eliminar una factura cobrada'}), 400
        
        # Eliminar factura
        resultado = factura.eliminar_factura(factura_id)
        
        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 400
            
    except Exception as e:
        logger.error(f"Error eliminando factura {factura_id}: {e}")
        return jsonify({'error': str(e)}), 500


@facturas_bp.route('/api/facturas/<int:factura_id>/pdf', methods=['GET'])
@login_required
def generar_pdf_factura(factura_id):
    """Genera PDF de una factura"""
    try:
        # Verificar que la factura existe
        factura_data = factura.obtener_factura_completa(factura_id)
        if not factura_data:
            return jsonify({'error': 'Factura no encontrada'}), 404
        
        # Generar PDF
        resultado = factura.generar_pdf_factura(factura_id)
        
        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 500
            
    except Exception as e:
        logger.error(f"Error generando PDF factura {factura_id}: {e}")
        return jsonify({'error': str(e)}), 500


@facturas_bp.route('/api/facturas/<int:factura_id>/enviar', methods=['POST'])
@login_required
def enviar_factura_email(factura_id):
    """Envía factura por email"""
    try:
        data = request.get_json() or {}
        
        # Verificar que la factura existe
        factura_data = factura.obtener_factura_completa(factura_id)
        if not factura_data:
            return jsonify({'error': 'Factura no encontrada'}), 404
        
        email_destino = data.get('email') or factura_data.get('email_contacto')
        if not email_destino:
            return jsonify({'error': 'Email de destino requerido'}), 400
        
        # Enviar email
        resultado = factura.enviar_factura_email(factura_id, email_destino, data.get('mensaje', ''))
        
        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 500
            
    except Exception as e:
        logger.error(f"Error enviando factura {factura_id}: {e}")
        return jsonify({'error': str(e)}), 500


@facturas_bp.route('/api/facturas/estadisticas', methods=['GET'])
@login_required
def obtener_estadisticas_facturas():
    """Obtiene estadísticas de facturación"""
    try:
        # Parámetros de filtro
        fecha_inicio = request.args.get('fecha_inicio', '')
        fecha_fin = request.args.get('fecha_fin', '')
        
        # Obtener estadísticas
        estadisticas = factura.obtener_estadisticas_facturacion(fecha_inicio, fecha_fin)
        
        return jsonify({
            'success': True,
            'estadisticas': estadisticas
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas facturas: {e}")
        return jsonify({'error': str(e)}), 500

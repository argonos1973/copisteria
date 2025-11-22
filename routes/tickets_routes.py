"""
Rutas relacionadas con tickets
"""

from flask import Blueprint, jsonify, request
from auth_middleware import login_required
import tickets
from logger_config import get_logger

logger = get_logger('aleph70.tickets_routes')

# Blueprint para las rutas de tickets
tickets_bp = Blueprint('tickets', __name__)

@login_required
@tickets_bp.route('/tickets/paginado', methods=['GET'])
def tickets_paginado_route():
    return tickets.tickets_paginado()

@login_required
@tickets_bp.route('/api/tickets/paginado', methods=['GET'])
def api_tickets_paginado():
    return tickets.tickets_paginado()


@tickets_bp.route('/api/tickets/<int:ticket_id>', methods=['GET'])
@login_required
def obtener_ticket_detalle(ticket_id):
    """Obtiene el detalle de un ticket específico"""
    try:
        ticket_data = tickets.obtener_ticket_completo(ticket_id)
        if ticket_data:
            return jsonify({
                'success': True,
                'ticket': ticket_data
            })
        else:
            return jsonify({'error': 'Ticket no encontrado'}), 404
            
    except Exception as e:
        logger.error(f"Error obteniendo ticket {ticket_id}: {e}")
        return jsonify({'error': str(e)}), 500


@tickets_bp.route('/api/tickets', methods=['POST'])
@login_required
def crear_ticket():
    """Crea un nuevo ticket"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
        
        # Validar datos requeridos
        if not data.get('lineas') or len(data.get('lineas', [])) == 0:
            return jsonify({'error': 'El ticket debe tener al menos una línea'}), 400
        
        # Crear ticket
        resultado = tickets.crear_ticket(data)
        
        if resultado['success']:
            return jsonify(resultado), 201
        else:
            return jsonify(resultado), 400
            
    except Exception as e:
        logger.error(f"Error creando ticket: {e}")
        return jsonify({'error': str(e)}), 500


@tickets_bp.route('/api/tickets/<int:ticket_id>', methods=['PUT'])
@login_required
def actualizar_ticket(ticket_id):
    """Actualiza un ticket existente"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
        
        # Verificar que el ticket existe
        ticket_existente = tickets.obtener_ticket(ticket_id)
        if not ticket_existente:
            return jsonify({'error': 'Ticket no encontrado'}), 404
        
        # Actualizar ticket
        resultado = tickets.actualizar_ticket(ticket_id, data)
        
        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 400
            
    except Exception as e:
        logger.error(f"Error actualizando ticket {ticket_id}: {e}")
        return jsonify({'error': str(e)}), 500


@tickets_bp.route('/api/tickets/<int:ticket_id>', methods=['DELETE'])
@login_required
def eliminar_ticket(ticket_id):
    """Elimina un ticket"""
    try:
        # Verificar que el ticket existe
        ticket_existente = tickets.obtener_ticket(ticket_id)
        if not ticket_existente:
            return jsonify({'error': 'Ticket no encontrado'}), 404
        
        # Eliminar ticket
        resultado = tickets.eliminar_ticket(ticket_id)
        
        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 400
            
    except Exception as e:
        logger.error(f"Error eliminando ticket {ticket_id}: {e}")
        return jsonify({'error': str(e)}), 500


@tickets_bp.route('/api/tickets/<int:ticket_id>/imprimir', methods=['GET'])
@login_required
def imprimir_ticket(ticket_id):
    """Genera formato de impresión para un ticket"""
    try:
        # Verificar que el ticket existe
        ticket_data = tickets.obtener_ticket_completo(ticket_id)
        if not ticket_data:
            return jsonify({'error': 'Ticket no encontrado'}), 404
        
        # Generar formato de impresión
        resultado = tickets.generar_formato_impresion(ticket_id)
        
        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 500
            
    except Exception as e:
        logger.error(f"Error imprimiendo ticket {ticket_id}: {e}")
        return jsonify({'error': str(e)}), 500


@tickets_bp.route('/api/tickets/estadisticas', methods=['GET'])
@login_required
def obtener_estadisticas_tickets():
    """Obtiene estadísticas de tickets"""
    try:
        # Parámetros de filtro
        fecha_inicio = request.args.get('fecha_inicio', '')
        fecha_fin = request.args.get('fecha_fin', '')
        
        # Obtener estadísticas
        estadisticas = tickets.obtener_estadisticas_tickets(fecha_inicio, fecha_fin)
        
        return jsonify({
            'success': True,
            'estadisticas': estadisticas
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas tickets: {e}")
        return jsonify({'error': str(e)}), 500

"""
Rutas relacionadas con tickets
"""

from flask import Blueprint, jsonify, request
from auth_middleware import login_required
import tickets
from logger_config import get_logger
from db_utils import obtener_numerador

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
        return tickets.obtener_ticket_con_detalles(ticket_id)
            
    except Exception as e:
        logger.error(f"Error obteniendo ticket {ticket_id}: {e}")
        return jsonify({'error': str(e)}), 500


@tickets_bp.route('/api/tickets/obtenerTicket/<int:ticket_id>', methods=['GET'])
@login_required
def obtener_ticket_detalle_legacy(ticket_id):
    """Endpoint legacy para obtener ticket"""
    return obtener_ticket_detalle(ticket_id)


@tickets_bp.route('/api/tickets', methods=['POST'])
@login_required
def crear_ticket():
    """Crea un nuevo ticket"""
    try:
        data = request.get_json()
        logger.info(f"DEBUG TICKETS: Payload recibido: {data}")
        
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
        
        # Validar datos requeridos
        detalles = data.get('detalles') or data.get('lineas') or []
        logger.info(f"DEBUG TICKETS: Detalles extraídos: {detalles}, Tipo: {type(detalles)}")
        
        if not detalles or len(detalles) == 0:
            logger.error(f"DEBUG TICKETS: Validación fallida. Detalles vacíos.")
            return jsonify({'error': 'El ticket debe tener al menos una línea'}), 400
        
        # Asegurar que 'detalles' está presente en data para tickets.guardar_ticket
        if 'detalles' not in data and 'lineas' in data:
            data['detalles'] = data['lineas']
        
        # Crear ticket (usando guardar_ticket que es la función correcta)
        return tickets.guardar_ticket(data)
            
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
        return tickets.actualizar_ticket(ticket_id, data)
            
    except Exception as e:
        logger.error(f"Error actualizando ticket {ticket_id}: {e}")
        return jsonify({'error': str(e)}), 500


@tickets_bp.route('/api/tickets/anular/<int:ticket_id>', methods=['POST'])
@login_required
def anular_ticket(ticket_id):
    """Anula un ticket y crea uno rectificativo"""
    return tickets.anular_ticket(ticket_id)


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
        return tickets.eliminar_ticket(ticket_id)
            
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


@tickets_bp.route('/api/tickets/obtener_numerador/<serie>', methods=['GET'])
@login_required
def obtener_siguiente_numero(serie):
    """Obtiene el siguiente número para la serie indicada"""
    try:
        # obtener_numerador devuelve el último número usado
        numerador, _ = obtener_numerador(serie)
        
        # Si no existe registro, asumimos que el último fue 0, así que el siguiente es 1
        ultimo = numerador if numerador is not None else 0
        siguiente = ultimo + 1
        
        return jsonify({
            'numerador': siguiente,
            'serie': serie,
            'success': True
        })
    except Exception as e:
        logger.error(f"Error obteniendo numerador {serie}: {e}")
        return jsonify({'error': str(e)}), 500


@tickets_bp.route('/api/ticket/numero', methods=['GET'])
@login_required
def obtener_numero_ticket_legacy():
    """Endpoint legacy para obtener siguiente número de ticket (asume serie T)"""
    return obtener_siguiente_numero('T')


@tickets_bp.route('/api/tickets/guardar', methods=['POST'])
@login_required
def guardar_ticket_legacy():
    """Endpoint de compatibilidad para guardar tickets"""
    return tickets.guardar_ticket()


@tickets_bp.route('/api/tickets/actualizar', methods=['POST', 'PUT'])
@login_required
def actualizar_ticket_legacy():
    """Endpoint de compatibilidad para actualizar tickets"""
    return tickets.actualizar_ticket()

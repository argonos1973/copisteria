from flask import Blueprint, request, jsonify
from auth_middleware import login_required
import presupuesto
from logger_config import get_logger
from db_utils import obtener_numerador

logger = get_logger('aleph70.presupuestos_routes')

presupuestos_bp = Blueprint('presupuestos', __name__)

@presupuestos_bp.route('/api/presupuestos', methods=['GET'])
@login_required
def consultar_presupuestos():
    return presupuesto.consultar_presupuestos()

@presupuestos_bp.route('/api/presupuestos/<int:id>', methods=['GET'])
@login_required
def obtener_presupuesto(id):
    return presupuesto.obtener_presupuesto(id)

@presupuestos_bp.route('/api/presupuestos', methods=['POST'])
@login_required
def crear_presupuesto():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
            
        # Normalizaciones
        if 'idContacto' in data and 'idcontacto' not in data:
            data['idcontacto'] = data['idContacto']
        
        detalles = data.get('detalles') or data.get('lineas')
        if detalles:
            data['detalles'] = detalles
            
        return presupuesto.crear_presupuesto(data)
    except Exception as e:
        logger.error(f"Error creando presupuesto: {e}")
        return jsonify({'error': str(e)}), 500

@presupuestos_bp.route('/api/presupuestos/<int:id>', methods=['PUT'])
@login_required
def actualizar_presupuesto(id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
            
        # Normalizaciones
        if 'idContacto' in data and 'idcontacto' not in data:
            data['idcontacto'] = data['idContacto']
        
        detalles = data.get('detalles') or data.get('lineas')
        if detalles:
            data['detalles'] = detalles
            
        return presupuesto.actualizar_presupuesto(id, data)
    except Exception as e:
        logger.error(f"Error actualizando presupuesto {id}: {e}")
        return jsonify({'error': str(e)}), 500

@presupuestos_bp.route('/api/presupuestos/<int:id>/convertir-factura', methods=['POST'])
@login_required
def convertir_a_factura(id):
    return presupuesto.convertir_presupuesto_a_factura(id)

@presupuestos_bp.route('/api/presupuestos/<int:id>/convertir-ticket', methods=['POST'])
@login_required
def convertir_a_ticket(id):
    return presupuesto.convertir_presupuesto_a_ticket(id)

# Endpoints de compatibilidad (Legacy)
@presupuestos_bp.route('/api/presupuestos/guardar', methods=['POST'])
@login_required
def guardar_presupuesto_legacy():
    """Endpoint de compatibilidad para guardar/actualizar presupuestos"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
            
        # Normalizaciones
        if 'idContacto' in data and 'idcontacto' not in data:
            data['idcontacto'] = data['idContacto']
        
        detalles = data.get('detalles') or data.get('lineas')
        if detalles:
            data['detalles'] = detalles

        if data.get('id'):
            return presupuesto.actualizar_presupuesto(data['id'], data)
        else:
            return presupuesto.crear_presupuesto(data)
    except Exception as e:
        logger.error(f"Error en guardar_presupuesto_legacy: {e}")
        return jsonify({'error': str(e)}), 500

@presupuestos_bp.route('/api/presupuestos/actualizar', methods=['POST', 'PUT'])
@login_required
def actualizar_presupuesto_legacy():
    """Endpoint de compatibilidad para actualizar presupuestos"""
    try:
        data = request.get_json()
        if not data or not data.get('id'):
            return jsonify({'error': 'ID requerido'}), 400
            
        # Normalizaciones
        if 'idContacto' in data and 'idcontacto' not in data:
            data['idcontacto'] = data['idContacto']
        
        detalles = data.get('detalles') or data.get('lineas')
        if detalles:
            data['detalles'] = detalles
            
        return presupuesto.actualizar_presupuesto(data['id'], data)
    except Exception as e:
        logger.error(f"Error en actualizar_presupuesto_legacy: {e}")
        return jsonify({'error': str(e)}), 500

@presupuestos_bp.route('/api/presupuestos/obtener_numerador', methods=['GET'])
@login_required
def obtener_numerador_presupuesto():
    """Obtiene el siguiente número de presupuesto"""
    try:
        # Serie O para presupuestos según lógica interna
        num, _ = obtener_numerador('O') 
        siguiente = (num or 0) + 1
        return jsonify({'numerador': siguiente, 'serie': 'O', 'success': True})
    except Exception as e:
        logger.error(f"Error obteniendo numerador presupuesto: {e}")
        return jsonify({'error': str(e)}), 500

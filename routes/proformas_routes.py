from flask import Blueprint, request, jsonify
from auth_middleware import login_required
import proforma
from logger_config import get_logger
from db_utils import obtener_numerador

logger = get_logger('aleph70.proformas_routes')

proformas_bp = Blueprint('proformas', __name__)

@proformas_bp.route('/api/proformas', methods=['GET'])
@login_required
def consultar_proformas():
    return proforma.consultar_proformas()

@proformas_bp.route('/api/proformas/<int:id>', methods=['GET'])
@login_required
def obtener_proforma(id):
    return proforma.obtener_proforma(id)

@proformas_bp.route('/api/proformas', methods=['POST'])
@login_required
def crear_proforma():
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
            
        return proforma.crear_proforma(data)
    except Exception as e:
        logger.error(f"Error creando proforma: {e}")
        return jsonify({'error': str(e)}), 500

@proformas_bp.route('/api/proformas/actualizar', methods=['POST', 'PATCH'])
@login_required
def actualizar_proforma_endpoint():
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
            
        id_proforma = data.get('id')
        if not id_proforma:
            return jsonify({'error': 'ID de proforma requerido para actualizar'}), 400
            
        return proforma.actualizar_proforma(id_proforma, data)
    except Exception as e:
        logger.error(f"Error actualizando proforma endpoint: {e}")
        return jsonify({'error': str(e)}), 500

@proformas_bp.route('/api/proformas/<int:id>/convertir-factura', methods=['POST'])
@login_required
def convertir_a_factura(id):
    return proforma.convertir_proforma_a_factura(id)

# Endpoints de compatibilidad (Legacy)
@proformas_bp.route('/api/proformas/guardar', methods=['POST'])
@login_required
def guardar_proforma_legacy():
    """Endpoint de compatibilidad para guardar proformas"""
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
            
        # Nota: proforma.crear_proforma maneja la lógica de inserción.
        # Si se requiere actualización, debería implementarse en proforma.py primero.
        return proforma.crear_proforma(data)
    except Exception as e:
        logger.error(f"Error en guardar_proforma_legacy: {e}")
        return jsonify({'error': str(e)}), 500

@proformas_bp.route('/api/proformas/obtener_numerador', methods=['GET'])
@login_required
def obtener_numerador_proforma():
    """Obtiene el siguiente número de proforma"""
    try:
        # Serie P para proformas
        num, _ = obtener_numerador('P') 
        siguiente = (num or 0) + 1
        return jsonify({'numerador': siguiente, 'serie': 'P', 'success': True})
    except Exception as e:
        logger.error(f"Error obteniendo numerador proforma: {e}")
        return jsonify({'error': str(e)}), 500

@proformas_bp.route('/api/proforma/abierta/<int:idContacto>', methods=['GET'])
@login_required
def obtener_proforma_abierta_endpoint(idContacto):
    """Obtiene la última proforma abierta de un contacto o devuelve datos para nueva"""
    return proforma.obtener_proforma_abierta(idContacto)

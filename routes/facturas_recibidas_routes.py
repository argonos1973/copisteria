import traceback
from flask import Blueprint, request, jsonify, session
from facturas_proveedores import obtener_proveedores, consultar_facturas_recibidas
from auth_middleware import login_required
from logger_config import get_logger

logger = get_logger(__name__)

facturas_recibidas_bp = Blueprint('facturas_recibidas', __name__, url_prefix='/api')

@facturas_recibidas_bp.route('/proveedores/listar', methods=['GET'])
@login_required
def listar_proveedores():
    try:
        empresa_id = session.get('empresa_id')
        if not empresa_id:
            return jsonify({'error': 'No hay empresa seleccionada'}), 400
            
        activos = request.args.get('activos') == 'true'
        proveedores = obtener_proveedores(empresa_id, activos_solo=activos)
        return jsonify({'success': True, 'proveedores': proveedores})
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Error al listar proveedores: {str(e)}\n{tb}")
        return jsonify({'error': f"{str(e)}\n{tb}", 'success': False}), 500

@facturas_recibidas_bp.route('/facturas-proveedores/consultar', methods=['POST'])
@login_required
def consultar_facturas():
    try:
        empresa_id = session.get('empresa_id')
        if not empresa_id:
            return jsonify({'error': 'No hay empresa seleccionada'}), 400
            
        # Obtener filtros del body (JSON)
        filtros = request.json or {}
        
        # Mapear filtros si es necesario
        
        resultado = consultar_facturas_recibidas(empresa_id, filtros)
        return jsonify({'success': True, **resultado})
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Error al consultar facturas recibidas: {str(e)}\n{tb}")
        return jsonify({'error': f"{str(e)}\n{tb}", 'success': False}), 500

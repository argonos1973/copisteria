"""
Rutas relacionadas con contactos y búsquedas
"""

from flask import Blueprint, jsonify, request
from auth_middleware import login_required
import contactos
from logger_config import get_logger
from db_utils import get_db_connection

logger = get_logger('aleph70.contactos_routes')

# Blueprint para las rutas de contactos
contactos_bp = Blueprint('contactos', __name__)

@contactos_bp.route('/api/contactos/paginado', methods=['GET'])
def api_contactos_paginado():
    return contactos_paginado()

@contactos_bp.route('/contactos/paginado', methods=['GET'])
def contactos_paginado():
    try:
        # Parámetros de filtros
        razon_social = request.args.get('razonSocial', '')
        nif = request.args.get('nif', '')
        poblacion = request.args.get('poblacion', '')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('pageSize', 25))
        
        # Construir filtros
        filtros = {}
        if razon_social:
            filtros['razonsocial'] = razon_social
        if nif:
            filtros['nif'] = nif
        if poblacion:
            filtros['poblacion'] = poblacion
        
        resultado = contactos.obtener_contactos_paginados(filtros, page, page_size)
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error en contactos paginado: {e}")
        return jsonify({'error': str(e)}), 500


@contactos_bp.route('/contactos', methods=['GET'])
def listar_contactos():
    try:
        return jsonify(contactos.obtener_contactos())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@contactos_bp.route('/contactos/buscar', methods=['GET'])
def filtrar_contactos():
    try:
        # Parámetros de filtrado
        razon_social = request.args.get('razonSocial', '').strip()
        nif = request.args.get('nif', '').strip()
        poblacion = request.args.get('poblacion', '').strip()
        
        # Construir consulta dinámica
        condiciones = []
        parametros = []
        
        if razon_social:
            condiciones.append("razonsocial LIKE ?")
            parametros.append(f'%{razon_social}%')
            
        if nif:
            condiciones.append("nif LIKE ?")
            parametros.append(f'%{nif}%')
            
        if poblacion:
            condiciones.append("poblacion LIKE ?")
            parametros.append(f'%{poblacion}%')
        
        # Construir query final
        query_base = '''
            SELECT idContacto, razonsocial, nif, direccion, 
                   cp, poblacion, provincia, telefono, email
            FROM contactos 
        '''
        
        if condiciones:
            query_final = query_base + ' WHERE ' + ' AND '.join(condiciones)
        else:
            query_final = query_base
            
        query_final += ' ORDER BY razonsocial LIMIT 100'
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query_final, parametros)
            resultados = cursor.fetchall()
            
            # Formatear resultados
            contactos_lista = []
            for row in resultados:
                contactos_lista.append({
                    'idContacto': row[0],
                    'razonsocial': row[1],
                    'nif': row[2],
                    'direccion': row[3],
                    'cp': row[4],
                    'poblacion': row[5],
                    'provincia': row[6],
                    'telefono': row[7],
                    'email': row[8]
                })
        
        return jsonify(contactos_lista)
        
    except Exception as e:
        logger.error(f"Error filtrando contactos: {e}")
        return jsonify({'error': str(e)}), 500


@contactos_bp.route('/api/contactos/search', methods=['GET'])
def search_contactos():
    """Endpoint para búsqueda de contactos por razón social"""
    query = request.args.get('query', '').strip()
    sort = request.args.get('sort', 'razonsocial')
    order = request.args.get('order', 'ASC')
    
    if not query:
        return jsonify([])
    
    try:
        # Validar campo de ordenamiento
        campos_validos = ['razonsocial', 'nif', 'poblacion', 'idContacto']
        if sort not in campos_validos:
            sort = 'razonsocial'
            
        # Validar orden
        if order.upper() not in ['ASC', 'DESC']:
            order = 'ASC'
        
        sql_query = f'''
            SELECT idContacto, razonsocial, nif, direccion, 
                   cp, poblacion, provincia, telefono, email
            FROM contactos 
            WHERE razonsocial LIKE ? 
            ORDER BY {sort} {order}
            LIMIT 50
        '''
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql_query, (f'%{query}%',))
            resultados = cursor.fetchall()
            
            contactos_lista = []
            for row in resultados:
                contactos_lista.append({
                    'idContacto': row[0],
                    'razonsocial': row[1],
                    'nif': row[2],
                    'direccion': row[3],
                    'cp': row[4],
                    'poblacion': row[5],
                    'provincia': row[6],
                    'telefono': row[7],
                    'email': row[8]
                })
        
        return jsonify(contactos_lista)
        
    except Exception as e:
        logger.error(f"Error buscando contactos: {e}")
        return jsonify({'error': str(e)}), 500


@contactos_bp.route('/api/contactos/searchCarrer', methods=['GET'])
def search_carrer():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify([])
    
    try:
        return jsonify(contactos.obtener_sugerencias_carrer(query))
    except Exception as e:
        logger.error(f"Error buscando direcciones: {e}")
        return jsonify({'error': str(e)}), 500


@contactos_bp.route('/api/contactos/search_cp', methods=['GET'])
def search_cp():
    term = request.args.get('term', '').strip()[:5]
    if not term:
        return jsonify([])
    
    try:
        return jsonify(contactos.buscar_codigos_postales(term))
    except Exception as e:
        logger.error(f"Error buscando CP: {e}")
        return jsonify({'error': str(e)}), 500


@contactos_bp.route('/api/contactos/get_cp', methods=['GET'])
def get_cp():
    cp = request.args.get('cp', '').strip()
    if not cp:
        return jsonify([])
    
    try:
        return jsonify(contactos.obtener_datos_cp(cp))
    except Exception as e:
        logger.error(f"Error obteniendo datos CP: {e}")
        return jsonify({'error': str(e)}), 500


@contactos_bp.route('/api/contactos/get_contacto/<int:idContacto>', methods=['GET'])
def get_contacto_endpoint(idContacto):
    try:
        contacto = contactos.obtener_contacto(idContacto)
        if contacto:
            return jsonify(contacto)
        else:
            return jsonify({'error': 'Contacto no encontrado'}), 404
    except Exception as e:
        logger.error(f"Error obteniendo contacto: {e}")
        return jsonify({'error': str(e)}), 500


@contactos_bp.route('/api/contactos/create_contacto', methods=['POST'])
def crear():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
        
        # Validar campos requeridos
        if not data.get('razonsocial'):
            return jsonify({'error': 'La razón social es requerida'}), 400
            
        resultado = contactos.crear_contacto(data)
        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 400
            
    except Exception as e:
        logger.error(f"Error creando contacto: {e}")
        return jsonify({'error': str(e)}), 500


@contactos_bp.route('/api/contactos/update_contacto/<int:idContacto>', methods=['PUT'])
def actualizar(idContacto):
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
        
        # Validar campos requeridos
        if not data.get('razonsocial'):
            return jsonify({'error': 'La razón social es requerida'}), 400
            
        resultado = contactos.actualizar_contacto(idContacto, data)
        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 400
            
    except Exception as e:
        logger.error(f"Error actualizando contacto: {e}")
        return jsonify({'error': str(e)}), 500


@contactos_bp.route('/api/contactos/eliminar_contacto/<int:idContacto>', methods=['DELETE'])
def eliminar(idContacto):
    try:
        if contactos.delete_contacto(idContacto):
            return jsonify({'mensaje': 'Contacto eliminado exitosamente'})
        return jsonify({'error': 'No se pudo eliminar el contacto'}), 400
    except Exception as e:
        logger.error(f"Error eliminando contacto: {e}")
        return jsonify({'error': str(e)}), 500


@contactos_bp.route('/api/contactos/ocr', methods=['POST'])
def procesar_ocr_contacto():
    """
    Procesa un contacto mediante OCR
    """
    try:
        # Verificar si se subió un archivo
        if 'file' not in request.files:
            return jsonify({'error': 'No se encontró archivo'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No se seleccionó archivo'}), 400
        
        # Procesar OCR (implementar según necesidades)
        resultado = contactos.procesar_ocr_contacto(file)
        
        return jsonify({
            'success': True,
            'data': resultado,
            'mensaje': 'OCR procesado correctamente'
        })
        
    except Exception as e:
        logger.error(f"Error procesando OCR contacto: {e}")
        return jsonify({'error': str(e)}), 500


@contactos_bp.route('/api/contactos/guardar', methods=['POST'])
@login_required
def guardar_contacto_legacy():
    """Endpoint de compatibilidad para guardar/actualizar contactos"""
    try:
        data = request.get_json()
        if data and data.get('idContacto'):
            return jsonify(contactos.actualizar_contacto(data['idContacto'], data))
        else:
            return jsonify(contactos.crear_contacto(data))
    except Exception as e:
        logger.error(f"Error en guardar_contacto_legacy: {e}")
        return jsonify({'error': str(e)}), 500


@contactos_bp.route('/api/contactos/actualizar', methods=['POST', 'PUT'])
@login_required
def actualizar_contacto_legacy():
    """Endpoint de compatibilidad para actualizar contactos"""
    try:
        data = request.get_json()
        if not data or not data.get('idContacto'):
            return jsonify({'error': 'ID de contacto requerido'}), 400
        return jsonify(contactos.actualizar_contacto(data['idContacto'], data))
    except Exception as e:
        logger.error(f"Error en actualizar_contacto_legacy: {e}")
        return jsonify({'error': str(e)}), 500

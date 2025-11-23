"""
Rutas relacionadas con facturas y facturación
"""

from flask import Blueprint, jsonify, request
from auth_middleware import login_required
import factura
import anulacion
from logger_config import get_logger
from db_utils import get_db_connection, obtener_numerador

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


@facturas_bp.route('/api/facturas/consulta/<int:factura_id>', methods=['GET'])
@login_required
def obtener_factura_detalle_legacy(factura_id):
    """Endpoint legacy para obtener detalle de factura con estructura para impresión"""
    try:
        factura_data = factura.obtener_factura_completa(factura_id)
        if factura_data:
            # Reestructurar para impresión (espera objeto contacto anidado)
            factura_data['contacto'] = {
                'razonsocial': factura_data.get('razonsocial'),
                'direccion': factura_data.get('direccion'),
                'cp': factura_data.get('cp'),
                'localidad': factura_data.get('localidad'),
                'provincia': factura_data.get('provincia'),
                'identificador': factura_data.get('nif'),
                'nif': factura_data.get('nif')
            }
            
            # Flag de configuración Veri*Factu
            verifactu_enabled_val = False
            try:
                from config_loader import get as get_config
                verifactu_enabled_val = bool(get_config("verifactu_enabled", False))
            except:
                pass
            
            # También lo metemos dentro de factura por si acaso otro frontend lo busca ahí
            factura_data['verifactu_enabled'] = verifactu_enabled_val

            return jsonify({
                'success': True,
                'factura': factura_data,
                'verifactu_enabled': verifactu_enabled_val
            })
        else:
            return jsonify({'error': 'Factura no encontrada'}), 404
            
    except Exception as e:
        logger.error(f"Error obteniendo factura legacy {factura_id}: {e}")
        return jsonify({'error': str(e)}), 500


@facturas_bp.route('/api/facturas', methods=['POST'])
@login_required
def crear_factura():
    """Crea una nueva factura"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
        
        # Normalizar idContacto -> idcontacto
        if 'idContacto' in data and 'idcontacto' not in data:
            data['idcontacto'] = data['idContacto']
        
        # Validar datos requeridos
        if not data.get('idcontacto'):
            return jsonify({'error': 'ID de contacto es requerido'}), 400
        
        # Normalizar lineas/detalles
        detalles = data.get('detalles') or data.get('lineas') or []
        if len(detalles) == 0:
            return jsonify({'error': 'La factura debe tener al menos una línea'}), 400
        data['detalles'] = detalles
        
        # Crear factura
        return factura.crear_factura(data)
            
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
        return factura.actualizar_factura(factura_id, data)
            
    except Exception as e:
        logger.error(f"Error actualizando factura {factura_id}: {e}")
        return jsonify({'error': str(e)}), 500


@facturas_bp.route('/api/facturas/anular/<int:factura_id>', methods=['POST'])
@login_required
def anular_factura_endpoint(factura_id):
    """Anula una factura"""
    return anulacion.anular_factura(factura_id)


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
        return factura.eliminar_factura(factura_id)
            
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


@facturas_bp.route('/api/facturas/<int:factura_id>/aeat', methods=['GET'])
@login_required
def obtener_info_aeat_factura(factura_id):
    """Obtiene información AEAT de una factura"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Consultar registro_facturacion, no factura
            cursor.execute('''
                SELECT estado_envio, csv, id_envio_aeat, fecha_envio, codigo_qr 
                FROM registro_facturacion WHERE factura_id = ? AND ticket_id IS NULL
            ''', (factura_id,))
            row = cursor.fetchone()
            
            if row:
                # Convertir QR a base64 si es necesario
                qr_val = row['codigo_qr']
                qr_b64 = None
                if qr_val and isinstance(qr_val, (bytes, bytearray)):
                    import base64
                    qr_b64 = base64.b64encode(qr_val).decode('utf-8')
                elif qr_val:
                    qr_b64 = qr_val # Si ya es string

                return jsonify({
                    'estado_envio': row['estado_envio'],
                    'csv': row['csv'],
                    'id_envio_aeat': row['id_envio_aeat'],
                    'fecha_envio': row['fecha_envio'],
                    'codigo_qr': qr_b64
                })
            
            # Si no hay registro, devolver vacío o pendiente en lugar de 404 para no romper frontend
            return jsonify({
                'estado_envio': 'NO_ENVIADO',
                'csv': None,
                'id_envio_aeat': None,
                'fecha_envio': None,
                'codigo_qr': None
            })
            
    except Exception as e:
        logger.error(f"Error obteniendo info AEAT factura {factura_id}: {e}")
        return jsonify({'error': str(e)}), 500


@facturas_bp.route('/api/facturas/guardar', methods=['POST'])
@login_required
def guardar_factura_legacy():
    """Endpoint de compatibilidad para guardar/actualizar facturas"""
    data = request.get_json()
    # Normalizar idContacto -> idcontacto
    if data and 'idContacto' in data and 'idcontacto' not in data:
        data['idcontacto'] = data['idContacto']

    # Normalizar lineas/detalles
    if data:
        detalles = data.get('detalles') or data.get('lineas') or []
        data['detalles'] = detalles

    if data and data.get('id'):
        # Si el frontend envía un ID, asumimos que es una actualización
        return factura.actualizar_factura(data['id'], data)
    else:
        # Si no hay ID, es una nueva factura
        return factura.crear_factura(data)


@facturas_bp.route('/api/facturas/actualizar', methods=['POST', 'PUT', 'PATCH'])
@login_required
def actualizar_factura_legacy():
    """Endpoint de compatibilidad para actualizar facturas"""
    data = request.get_json()
    if not data or not data.get('id'):
        return jsonify({'error': 'ID de factura requerido para actualizar'}), 400
    
    # Normalizar idContacto -> idcontacto
    if 'idContacto' in data and 'idcontacto' not in data:
        data['idcontacto'] = data['idContacto']
    
    # Normalizar lineas/detalles
    if data:
        detalles = data.get('detalles') or data.get('lineas')
        if detalles is not None:
            data['detalles'] = detalles
        
    return factura.actualizar_factura(data['id'], data)


@facturas_bp.route('/api/facturas/obtener_numerador/<serie>', methods=['GET'])
@login_required
def obtener_numerador_factura(serie):
    """Obtiene el siguiente número de factura para la serie dada"""
    try:
        if serie == 'F':
            # obtener_numerador devuelve el último número usado
            num, _ = obtener_numerador('F')
            # Siguiente número
            siguiente = (num or 0) + 1
            return jsonify({'numerador': siguiente, 'serie': 'F', 'success': True})
        else:
            return jsonify({'error': 'Serie desconocida'}), 400
    except Exception as e:
        logger.error(f"Error obteniendo numerador factura serie {serie}: {e}")
        return jsonify({'error': str(e)}), 500


@facturas_bp.route('/api/factura/numero', methods=['GET'])
@login_required
def obtener_numero_factura_legacy():
    """Endpoint legacy para obtener siguiente número de factura (asume serie F)"""
    return obtener_numerador_factura('F')


@facturas_bp.route('/api/facturas/obtener_contacto/<int:factura_id>', methods=['GET'])
@login_required
def obtener_contacto_factura(factura_id):
    """Obtiene el idContacto asociado a una factura"""
    try:
        # Usar obtener_factura_completa que solo requiere el ID
        factura_data = factura.obtener_factura_completa(factura_id)
        
        # Intentar obtener con mayúscula o minúscula por seguridad
        id_contacto = None
        if factura_data:
            id_contacto = factura_data.get('idContacto') or factura_data.get('idcontacto')
            
        if id_contacto:
             return jsonify({'idContacto': id_contacto, 'success': True})
        return jsonify({'error': 'Contacto no encontrado en factura'}), 404
    except Exception as e:
        logger.error(f"Error obteniendo contacto de factura {factura_id}: {e}")
        return jsonify({'error': str(e)}), 500


@facturas_bp.route('/api/factura/abierta/<int:idContacto>/<int:idFactura>', methods=['GET'])
@login_required
def obtener_factura_abierta_legacy(idContacto, idFactura):
    """Endpoint legacy para obtener factura abierta (edición) con estructura específica"""
    try:
        factura_data = factura.obtener_factura_completa(idFactura)
        if factura_data:
            # Reestructurar para el frontend (espera objeto contacto anidado)
            respuesta = factura_data.copy()
            respuesta['contacto'] = {
                'idContacto': factura_data.get('idContacto'),
                'razonsocial': factura_data.get('razonsocial'),
                'identificador': factura_data.get('nif'),
                'nif': factura_data.get('nif'),
                'direccion': factura_data.get('direccion'),
                'cp': factura_data.get('cp'),
                'localidad': factura_data.get('localidad'),
                'provincia': factura_data.get('provincia'),
                'email': factura_data.get('email_contacto')
            }
            respuesta['modo'] = 'edicion'
            return jsonify(respuesta)
        else:
            return jsonify({'error': 'Factura no encontrada'}), 404
    except Exception as e:
        logger.error(f"Error obteniendo factura abierta {idFactura}: {e}")
        return jsonify({'error': str(e)}), 500

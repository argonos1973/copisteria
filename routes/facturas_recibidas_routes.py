import traceback
import os
from flask import Blueprint, request, jsonify, session, send_file
from werkzeug.utils import secure_filename
from facturas_proveedores import (
    obtener_proveedores, consultar_facturas_recibidas, crear_proveedor, 
    actualizar_proveedor, eliminar_proveedor, obtener_factura_por_id, 
    actualizar_factura_proveedor, eliminar_factura, registrar_pago_factura,
    guardar_factura_bd, calcular_hash_pdf, factura_ya_procesada,
    obtener_o_crear_proveedor  # Importar la función inteligente
)
from factura_ocr import procesar_imagen_factura
from auth_middleware import login_required
from logger_config import get_logger
from multiempresa_config import DB_USUARIOS_PATH
from database_pool import get_database_pool
import sqlite3

logger = get_logger(__name__)

facturas_recibidas_bp = Blueprint('facturas_recibidas', __name__, url_prefix='/api')

@facturas_recibidas_bp.route('/facturas-proveedores/ocr', methods=['POST'])
@login_required
def procesar_ocr_factura():
    """Procesa una factura con OCR (OpenAI Vision)"""
    try:
        if 'archivo' not in request.files:
            return jsonify({'error': 'No se envió archivo para OCR'}), 400
            
        archivo = request.files['archivo']
        if archivo.filename == '':
            return jsonify({'error': 'Nombre de archivo vacío'}), 400
            
        # Leer bytes del archivo
        imagen_bytes = archivo.read()
        
        # Procesar con OCR
        datos = procesar_imagen_factura(imagen_bytes)
        
        # VALIDACIÓN: El NIF del proveedor no puede ser el de la propia empresa
        empresa_id = session.get('empresa_id')
        if empresa_id:
            try:
                with get_database_pool(DB_USUARIOS_PATH).get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT cif FROM empresas WHERE id = ?", (empresa_id,))
                    res = cursor.fetchone()
                    
                    if res and res[0]:
                        cif_empresa = res[0].upper().replace('-', '').replace(' ', '').strip()
                        nif_proveedor = datos.get('proveedor', {}).get('nif', '').upper().replace('-', '').replace(' ', '').strip()
                        
                        if cif_empresa and nif_proveedor and cif_empresa == nif_proveedor:
                            logger.warning(f"⚠️ OCR detectó el NIF de la propia empresa ({nif_proveedor}) como proveedor. Borrando dato incorrecto.")
                            datos['proveedor']['nif'] = ''
                            datos['proveedor']['advertencia'] = 'El NIF detectado coincidía con su empresa y ha sido eliminado.'
            except Exception as e:
                logger.error(f"Error validando NIF empresa vs proveedor: {e}")
        
        return jsonify({'success': True, 'datos': datos})
        
    except Exception as e:
        logger.error(f"Error en OCR: {e}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500

@facturas_recibidas_bp.route('/facturas-proveedores/subir', methods=['POST'])
@login_required
def subir_factura_endpoint():
    """Guarda una factura subida manualmente o via OCR"""
    try:
        empresa_id = session.get('empresa_id')
        usuario = session.get('usuario_id', 'sistema')
        if not empresa_id:
            return jsonify({'error': 'No hay empresa seleccionada'}), 400
            
        # Obtener datos del form
        proveedor_id = request.form.get('proveedor_id')
        if not proveedor_id:
            return jsonify({'error': 'Falta proveedor_id'}), 400
            
        # Archivo
        if 'archivos' not in request.files:
            return jsonify({'error': 'No se envió archivo PDF'}), 400
            
        archivo = request.files['archivos']
        if archivo.filename == '':
            return jsonify({'error': 'Nombre de archivo vacío'}), 400
            
        # Calcular hash para duplicados
        archivo.seek(0)
        pdf_bytes = archivo.read()
        pdf_hash = calcular_hash_pdf(pdf_bytes)
        archivo.seek(0) # Resetear puntero
        
        # Verificar si ya existe
        if factura_ya_procesada(pdf_hash, empresa_id):
             return jsonify({
                'success': False, 
                'duplicada': True, 
                'mensaje': 'Esta factura ya ha sido procesada anteriormente',
                'info': 'Duplicada'
            })

        # Guardar archivo en disco
        # Estándar multiempresa: facturas_proveedores/empresa_codigo/anio/filename
        empresa_codigo = session.get('empresa_codigo')
        if not empresa_codigo:
            # Fallback: Obtener código desde DB si no está en sesión
            try:
                with get_database_pool(DB_USUARIOS_PATH).get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT codigo FROM empresas WHERE id = ?", (empresa_id,))
                    res = cursor.fetchone()
                    if res:
                        empresa_codigo = res[0]
            except Exception as e:
                logger.error(f"Error obteniendo código empresa: {e}")
        
        # Si falla todo, usar ID como fallback temporal (no ideal pero evita crash)
        carpeta_empresa = empresa_codigo if empresa_codigo else str(empresa_id)
        
        from datetime import datetime
        anio = datetime.now().year
        upload_folder = f"/var/www/html/facturas_proveedores/{carpeta_empresa}/{anio}"
        os.makedirs(upload_folder, exist_ok=True)
        
        filename = secure_filename(archivo.filename)
        ruta_destino = os.path.join(upload_folder, filename)
        archivo.save(ruta_destino)
        
        # Datos factura dictionary
        datos_factura = {
            'numero_factura': request.form.get('numero_factura'),
            'fecha_emision': request.form.get('fecha_emision'),
            'fecha_vencimiento': request.form.get('fecha_vencimiento'),
            'base_imponible': float(request.form.get('base_imponible') or 0),
            'iva_porcentaje': 21, # Default o calcular
            'iva_importe': float(request.form.get('iva') or 0), 
            'total': float(request.form.get('total') or 0),
            'concepto': request.form.get('concepto'),
            'notas': request.form.get('notas', '')
        }
        
        factura_id = guardar_factura_bd(
            empresa_id, 
            proveedor_id, 
            datos_factura, 
            ruta_destino, 
            pdf_hash, 
            usuario=usuario
        )
        
        return jsonify({'success': True, 'id': factura_id, 'message': 'Factura guardada correctamente'})
        
    except Exception as e:
        error_msg = str(e)
        # Detectar error de duplicado por número de factura (lanzado por guardar_factura_bd)
        if "Ya existe una factura con ese número" in error_msg or "duplicada" in error_msg.lower():
            logger.warning(f"Intento de subir factura duplicada (número): {error_msg}")
            return jsonify({
                'success': False, 
                'duplicada': True, 
                'mensaje': 'Ya existe una factura con este número para este proveedor',
                'info': 'Duplicada'
            }), 200 # Retornar 200 para que el frontend lo procese como warning, no error 500
            
        logger.error(f"Error al subir factura: {e}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500

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

@facturas_recibidas_bp.route('/proveedores/crear', methods=['POST'])
@login_required
def crear_nuevo_proveedor():
    try:
        empresa_id = session.get('empresa_id')
        usuario = session.get('usuario_id', 'sistema')
        if not empresa_id:
            return jsonify({'error': 'No hay empresa seleccionada'}), 400
            
        datos = request.json
        if not datos:
            return jsonify({'error': 'No se enviaron datos'}), 400
            
        # Usar la función inteligente obtener_o_crear_proveedor para evitar duplicados
        # Extraer datos clave
        nif = datos.get('nif')
        nombre = datos.get('nombre')
        
        # Mapear campos para datos_adicionales (para que coincidan con lo que espera la función)
        # La función espera 'proveedor_telefono' o 'telefono', 'proveedor_direccion' o 'direccion'
        datos_adicionales = datos.copy()
        
        # Si el request viene del OCR masivo, los campos ya son 'telefono', 'direccion', etc.
        # Si viene de otra fuente, aseguramos compatibilidad
        
        proveedor_id = obtener_o_crear_proveedor(
            nif, 
            nombre, 
            empresa_id, 
            datos_adicionales=datos_adicionales,
            email_origen=datos.get('email')
        )
        
        # Verificar si se creó uno nuevo o se devolvió uno existente
        # obtener_o_crear_proveedor devuelve solo el ID
        
        return jsonify({
            'success': True, 
            'id': proveedor_id, 
            'message': 'Proveedor procesado correctamente',
            # Intentamos devolver el objeto proveedor completo si es posible
            'proveedor': {'id': proveedor_id, 'nombre': nombre, 'nif': nif} 
        })
        
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Error al crear proveedor: {str(e)}\n{tb}")
        return jsonify({'error': str(e), 'success': False}), 500

@facturas_recibidas_bp.route('/proveedores/<int:proveedor_id>', methods=['PUT'])
@login_required
def actualizar_proveedor_existente(proveedor_id):
    try:
        empresa_id = session.get('empresa_id')
        usuario = session.get('usuario_id', 'sistema')
        if not empresa_id:
            return jsonify({'error': 'No hay empresa seleccionada'}), 400
            
        datos = request.json
        if not datos:
            return jsonify({'error': 'No se enviaron datos'}), 400
            
        actualizar_proveedor(proveedor_id, empresa_id, datos, usuario=usuario)
        return jsonify({'success': True, 'message': 'Proveedor actualizado correctamente'})
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Error al actualizar proveedor: {str(e)}\n{tb}")
        return jsonify({'error': str(e), 'success': False}), 500

@facturas_recibidas_bp.route('/proveedores/<int:proveedor_id>', methods=['DELETE'])
@login_required
def eliminar_proveedor_existente(proveedor_id):
    try:
        empresa_id = session.get('empresa_id')
        usuario = session.get('usuario_id', 'sistema')
        if not empresa_id:
            return jsonify({'error': 'No hay empresa seleccionada'}), 400
            
        eliminar_proveedor(proveedor_id, empresa_id, usuario=usuario)
        return jsonify({'success': True, 'message': 'Proveedor eliminado correctamente'})
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Error al eliminar proveedor: {str(e)}\n{tb}")
        return jsonify({'error': str(e), 'success': False}), 500

@facturas_recibidas_bp.route('/facturas-proveedores/consultar', methods=['POST'])
@login_required
def consultar_facturas():
    try:
        empresa_id = session.get('empresa_id')
        if not empresa_id:
            return jsonify({'error': 'No hay empresa seleccionada'}), 400
            
        # Obtener filtros del body (JSON)
        filtros = request.json or {}
        
        resultado = consultar_facturas_recibidas(empresa_id, filtros)
        return jsonify({'success': True, **resultado})
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Error al consultar facturas recibidas: {str(e)}\n{tb}")
        return jsonify({'error': f"{str(e)}\n{tb}", 'success': False}), 500


@facturas_recibidas_bp.route('/facturas-proveedores/<int:factura_id>', methods=['GET'])
@login_required
def obtener_factura(factura_id):
    try:
        empresa_id = session.get('empresa_id')
        if not empresa_id:
            return jsonify({'error': 'No hay empresa seleccionada'}), 400
            
        factura = obtener_factura_por_id(factura_id, empresa_id)
        if not factura:
            return jsonify({'error': 'Factura no encontrada'}), 404
            
        return jsonify({'success': True, 'factura': factura})
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Error al obtener factura {factura_id}: {str(e)}\n{tb}")
        return jsonify({'error': str(e), 'success': False}), 500


@facturas_recibidas_bp.route('/facturas-proveedores/<int:factura_id>', methods=['PUT'])
@login_required
def actualizar_factura_endpoint(factura_id):
    try:
        empresa_id = session.get('empresa_id')
        usuario = session.get('usuario_id', 'sistema')
        if not empresa_id:
            return jsonify({'error': 'No hay empresa seleccionada'}), 400
            
        datos = request.json
        if not datos:
            return jsonify({'error': 'No se enviaron datos'}), 400
            
        actualizar_factura_proveedor(factura_id, empresa_id, datos, usuario=usuario)
        return jsonify({'success': True, 'message': 'Factura actualizada correctamente'})
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Error al actualizar factura {factura_id}: {str(e)}\n{tb}")
        return jsonify({'error': str(e), 'success': False}), 500


@facturas_recibidas_bp.route('/facturas-proveedores/<int:factura_id>', methods=['DELETE'])
@login_required
def eliminar_factura_endpoint(factura_id):
    try:
        empresa_id = session.get('empresa_id')
        usuario = session.get('usuario_id', 'sistema')
        if not empresa_id:
            return jsonify({'error': 'No hay empresa seleccionada'}), 400
            
        eliminar_factura(factura_id, empresa_id, usuario=usuario)
        return jsonify({'success': True, 'message': 'Factura eliminada correctamente'})
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Error al eliminar factura {factura_id}: {str(e)}\n{tb}")
        return jsonify({'error': str(e), 'success': False}), 500


@facturas_recibidas_bp.route('/facturas-proveedores/<int:factura_id>/pagar', methods=['PUT'])
@login_required
def registrar_pago_endpoint(factura_id):
    try:
        empresa_id = session.get('empresa_id')
        usuario = session.get('usuario_id', 'sistema')
        if not empresa_id:
            return jsonify({'error': 'No hay empresa seleccionada'}), 400
            
        datos = request.json
        if not datos:
            return jsonify({'error': 'No se enviaron datos de pago'}), 400
            
        registrar_pago_factura(factura_id, empresa_id, datos, usuario=usuario)
        return jsonify({'success': True, 'message': 'Pago registrado correctamente'})
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Error al registrar pago factura {factura_id}: {str(e)}\n{tb}")
        return jsonify({'error': str(e), 'success': False}), 500


@facturas_recibidas_bp.route('/facturas-proveedores/<int:factura_id>/pdf', methods=['GET'])
@login_required
def descargar_pdf_factura(factura_id):
    try:
        empresa_id = session.get('empresa_id')
        if not empresa_id:
            return jsonify({'error': 'No hay empresa seleccionada'}), 400
            
        factura = obtener_factura_por_id(factura_id, empresa_id)
        if not factura or not factura.get('ruta_archivo'):
            return jsonify({'error': 'Factura o archivo no encontrado'}), 404
            
        ruta_archivo = factura['ruta_archivo']
        if not os.path.exists(ruta_archivo):
             return jsonify({'error': 'El archivo físico no existe en el servidor'}), 404
             
        return send_file(ruta_archivo)
    except Exception as e:
        logger.error(f"Error sirviendo PDF factura {factura_id}: {e}")
        return jsonify({'error': str(e)}), 500

import traceback
import os
import uuid
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


def _normalizar_estado_factura(valor):
    if valor is None:
        return None
    v = str(valor).strip()
    if not v:
        return None
    u = v.upper()
    if u in ('P', 'PAGADA', 'PAGADO'):
        return 'pagada'
    return v


@facturas_recibidas_bp.route('/facturas-proveedores/inbox/upload-zip', methods=['POST'])
@login_required
def upload_zip_facturas_proveedores_inbox():
    try:
        empresa_id = session.get('empresa_id')
        if not empresa_id:
            return jsonify({'error': 'No hay empresa seleccionada'}), 400

        files = request.files.getlist('archivo')
        if not files:
            files = request.files.getlist('archivos')
        if not files:
            return jsonify({'error': 'No se envió archivo ZIP'}), 400

        empresa_codigo = session.get('empresa_codigo')
        if not empresa_codigo:
            try:
                with get_database_pool(DB_USUARIOS_PATH).get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT codigo FROM empresas WHERE id = ?", (empresa_id,))
                    res = cursor.fetchone()
                    if res:
                        empresa_codigo = res[0]
            except Exception as e:
                logger.error(f"Error obteniendo código empresa: {e}")

        carpeta_empresa = empresa_codigo if empresa_codigo else str(empresa_id)
        inbox_dir = os.path.join('/var/www/html/facturas_proveedores', str(carpeta_empresa), 'inbox')
        os.makedirs(inbox_dir, exist_ok=True)

        saved_files = []
        for archivo in files:
            if not archivo or not archivo.filename:
                return jsonify({'error': 'Nombre de archivo vacío'}), 400

            original_name = secure_filename(archivo.filename)
            if not original_name or not original_name.lower().endswith('.zip'):
                return jsonify({'error': 'El archivo debe ser .zip'}), 400

            saved_name = original_name
            dest_path = os.path.join(inbox_dir, saved_name)
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(saved_name)
                saved_name = f"{base}_{uuid.uuid4().hex}{ext}"
                dest_path = os.path.join(inbox_dir, saved_name)

            archivo.save(dest_path)
            saved_files.append({
                'saved_name': saved_name,
                'original_name': original_name,
            })

        first = saved_files[0] if saved_files else {}
        return jsonify({
            'success': True,
            'inbox_dir': inbox_dir,
            'saved_name': first.get('saved_name'),
            'original_name': first.get('original_name'),
            'files': saved_files,
        })
    except Exception as e:
        logger.error(f"Error subiendo ZIP a inbox: {e}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500


@facturas_recibidas_bp.route('/facturas-proveedores/crear', methods=['POST'])
@login_required
def crear_factura_manual():
    """Crea una factura recibida manualmente (sin PDF)."""
    try:
        empresa_id = session.get('empresa_id')
        usuario = session.get('usuario_id', 'sistema')
        if not empresa_id:
            return jsonify({'error': 'No hay empresa seleccionada'}), 400

        payload = request.json or {}
        proveedor_id = payload.get('proveedor_id')
        proveedor_data = payload.get('proveedor') or {}
        factura_data = payload.get('factura') or {}

        # Resolver proveedor
        if proveedor_id:
            proveedor_id = int(proveedor_id)
        else:
            nombre = (proveedor_data.get('nombre') or '').strip()
            nif = (proveedor_data.get('nif') or '').strip()
            if not nombre:
                return jsonify({'error': 'Falta proveedor (selecciona uno o indica nombre)'}), 400

            proveedor_id = obtener_o_crear_proveedor(
                nif,
                nombre,
                empresa_id,
                datos_adicionales=proveedor_data,
                email_origen=proveedor_data.get('email')
            )

        # Datos de factura
        datos_factura = {
            'numero_factura': factura_data.get('numero_factura'),
            'fecha_emision': factura_data.get('fecha_emision'),
            'fecha_vencimiento': factura_data.get('fecha_vencimiento'),
            'base_imponible': float(factura_data.get('base_imponible') or 0),
            'iva_porcentaje': float(factura_data.get('iva_porcentaje') or 0),
            'iva_importe': float(factura_data.get('iva_importe') or 0),
            'total': float(factura_data.get('total') or 0),
            'concepto': factura_data.get('concepto'),
            'notas': factura_data.get('notas', ''),
            'estado': _normalizar_estado_factura(factura_data.get('estado')) or 'pagada'
        }

        # Hash manual para evitar colisiones y que factura_ya_procesada no bloquee
        pdf_hash = f"MANUAL-{uuid.uuid4().hex.upper()}"

        factura_id = guardar_factura_bd(
            empresa_id,
            proveedor_id,
            datos_factura,
            None,
            pdf_hash,
            usuario=usuario
        )

        return jsonify({'success': True, 'id': factura_id})

    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Error creando factura manual: {str(e)}\n{tb}")
        return jsonify({'error': str(e), 'success': False}), 500

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

        empresa_id = session.get('empresa_id')
        if not empresa_id:
            return jsonify({'error': 'No hay empresa seleccionada'}), 400

        empresa_codigo = session.get('empresa_codigo')
        if not empresa_codigo:
            try:
                with get_database_pool(DB_USUARIOS_PATH).get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT codigo FROM empresas WHERE id = ?", (empresa_id,))
                    res = cursor.fetchone()
                    if res:
                        empresa_codigo = res[0]
            except Exception as e:
                logger.error(f"Error obteniendo código empresa: {e}")

        carpeta_empresa = empresa_codigo if empresa_codigo else str(empresa_id)

        from datetime import datetime
        anio = datetime.now().year
        upload_folder = f"/var/www/html/facturas_proveedores/{carpeta_empresa}/{anio}"
        os.makedirs(upload_folder, exist_ok=True)

        original_name = secure_filename(archivo.filename) or 'factura'
        _, ext = os.path.splitext(original_name)
        ext = (ext or '').lower()
        if not ext:
            if imagen_bytes.startswith(b'%PDF'):
                ext = '.pdf'
            else:
                ext = '.jpg'

        saved_name = f"OCR_{uuid.uuid4().hex}{ext}"
        ruta_destino = os.path.join(upload_folder, saved_name)
        with open(ruta_destino, 'wb') as f:
            f.write(imagen_bytes)
        
        # Obtener NIF de la empresa activa para ignorarlo en el OCR
        nif_cliente = None
        try:
            with get_database_pool(DB_USUARIOS_PATH).get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT cif FROM empresas WHERE id = ?", (empresa_id,))
                res = cursor.fetchone()
                if res and res[0]:
                    nif_cliente = res[0].upper().strip()
        except Exception as e:
            logger.error(f"Error obteniendo NIF empresa para OCR: {e}")

        # Procesar con OCR
        datos = procesar_imagen_factura(imagen_bytes, nif_cliente)
        
        # VALIDACIÓN: El NIF del proveedor no puede ser el de la propia empresa
        if nif_cliente:
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
        
        preview_url = f"/api/facturas-proveedores/ocr-preview/{anio}/{saved_name}"
        return jsonify({
            'success': True,
            'datos': datos,
            'archivo_guardado': True,
            'preview_url': preview_url,
            'preview_filename': saved_name,
            'preview_year': anio
        })
        
    except Exception as e:
        logger.error(f"Error en OCR: {e}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500


@facturas_recibidas_bp.route('/facturas-proveedores/ocr-preview/<int:anio>/<path:filename>', methods=['GET'])
@login_required
def ocr_preview_factura(anio, filename):
    try:
        empresa_id = session.get('empresa_id')
        if not empresa_id:
            return jsonify({'error': 'No hay empresa seleccionada'}), 400

        empresa_codigo = session.get('empresa_codigo')
        if not empresa_codigo:
            try:
                with get_database_pool(DB_USUARIOS_PATH).get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT codigo FROM empresas WHERE id = ?", (empresa_id,))
                    res = cursor.fetchone()
                    if res:
                        empresa_codigo = res[0]
            except Exception as e:
                logger.error(f"Error obteniendo código empresa: {e}")

        carpeta_empresa = empresa_codigo if empresa_codigo else str(empresa_id)

        safe_name = secure_filename(os.path.basename(filename))
        if not safe_name:
            return jsonify({'error': 'Nombre de archivo no válido'}), 400

        ruta = os.path.join('/var/www/html/facturas_proveedores', carpeta_empresa, str(anio), safe_name)
        if not os.path.exists(ruta):
            return jsonify({'error': 'Archivo no encontrado'}), 404

        return send_file(ruta)
    except Exception as e:
        logger.error(f"Error sirviendo preview OCR: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

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
            
        # Archivo: puede venir como archivo nuevo o como ruta OCR ya guardada
        ruta_ocr = request.form.get('ruta_archivo_ocr', '').strip()
        ruta_destino = None
        pdf_hash = None

        if ruta_ocr:
            # Reutilizar archivo que ya guardó el OCR
            empresa_codigo = session.get('empresa_codigo')
            if not empresa_codigo:
                try:
                    with get_database_pool(DB_USUARIOS_PATH).get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT codigo FROM empresas WHERE id = ?", (empresa_id,))
                        res = cursor.fetchone()
                        if res:
                            empresa_codigo = res[0]
                except Exception as e:
                    logger.error(f"Error obteniendo código empresa: {e}")
            carpeta_empresa = empresa_codigo if empresa_codigo else str(empresa_id)
            ruta_destino = os.path.join('/var/www/html/facturas_proveedores', carpeta_empresa, str(datetime.now().year), secure_filename(os.path.basename(ruta_ocr)))
            if not os.path.exists(ruta_destino):
                return jsonify({'error': 'No se encuentra el archivo OCR indicado'}), 400
            pdf_hash = calcular_hash_pdf(open(ruta_destino, 'rb').read())
        else:
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
            'iva_porcentaje': float(request.form.get('iva_porcentaje') or 21),
            'iva_importe': float(request.form.get('iva') or 0), 
            'total': float(request.form.get('total') or 0),
            'concepto': request.form.get('concepto'),
            'notas': request.form.get('notas', ''),
            'estado': _normalizar_estado_factura(request.form.get('estado')) or 'pagada'
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
        empresa_db = session.get('empresa_db', 'NO DEFINIDA')
        logger.info(f"[GET FACTURA] ID={factura_id}, empresa_id={empresa_id}, empresa_db={empresa_db}")
        
        if not empresa_id:
            return jsonify({'error': 'No hay empresa seleccionada'}), 400
            
        factura = obtener_factura_por_id(factura_id, empresa_id)
        if not factura:
            logger.warning(f"[GET FACTURA] Factura {factura_id} no encontrada para empresa {empresa_id}")
            return jsonify({'error': 'Factura no encontrada'}), 404
            
        return jsonify({'success': True, 'factura': factura})
    except Exception as e:
        tb = traceback.format_exc()
        error_info = f"Error obteniendo factura {factura_id}:\nempresa_id={session.get('empresa_id')}\nempresa_db={session.get('empresa_db')}\nError: {str(e)}\n\nTraceback:\n{tb}"
        try:
            with open('/var/www/html/error_debug_factura.log', 'w') as f:
                f.write(error_info)
        except:
            pass
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
        logger.info(f"[PUT FACTURA] ID={factura_id}, datos recibidos: {datos}")
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

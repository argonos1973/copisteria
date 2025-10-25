import os
import sqlite3
import shutil
import json
from flask import Blueprint, request, jsonify, session
from werkzeug.utils import secure_filename
from auth_middleware import login_required, superadmin_required
from logger_config import get_logger
from color_generator import generate_palette

logger = get_logger(__name__)

empresas_bp = Blueprint('empresas', __name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_USUARIOS_PATH = os.path.join(BASE_DIR, 'db', 'usuarios_sistema.db')
DB_DIR = os.path.join(BASE_DIR, 'db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'logos')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}

# Crear directorio de logos si no existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generar_codigo_empresa(nombre):
    """Genera código de empresa: primeros 5 caracteres sin espacios"""
    codigo = nombre.replace(' ', '').lower()[:5]
    return codigo

def clonar_estructura_bd(bd_origen, bd_destino):
    """
    Clona la estructura (schema) de una BD SQLite sin copiar datos
    """
    try:
        # Conectar a BD origen
        conn_origen = sqlite3.connect(bd_origen)
        cursor_origen = conn_origen.cursor()
        
        # Obtener el schema completo
        cursor_origen.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tablas_sql = cursor_origen.fetchall()
        
        cursor_origen.execute("SELECT sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL")
        indices_sql = cursor_origen.fetchall()
        
        cursor_origen.execute("SELECT sql FROM sqlite_master WHERE type='trigger'")
        triggers_sql = cursor_origen.fetchall()
        
        conn_origen.close()
        
        # Crear nueva BD con el schema
        conn_destino = sqlite3.connect(bd_destino)
        cursor_destino = conn_destino.cursor()
        
        # Crear tablas
        for (sql,) in tablas_sql:
            if sql:
                cursor_destino.execute(sql)
        
        # Crear índices
        for (sql,) in indices_sql:
            if sql:
                cursor_destino.execute(sql)
        
        # Crear triggers
        for (sql,) in triggers_sql:
            if sql:
                cursor_destino.execute(sql)
        
        conn_destino.commit()
        conn_destino.close()
        
        logger.info(f"Estructura de BD clonada correctamente: {bd_destino}")
        return True
        
    except Exception as e:
        logger.error(f"Error clonando estructura de BD: {e}", exc_info=True)
        return False

@empresas_bp.route('/api/empresas', methods=['GET'])
@superadmin_required
def listar_empresas():
    """Lista todas las empresas del sistema"""
    try:
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, codigo, nombre, cif, direccion, telefono, email, web,
                   logo_header, logo_factura, color_primario, color_secundario,
                   color_success, color_warning, color_danger, color_info,
                   color_button, color_button_hover, activa, fecha_alta
            FROM empresas
            ORDER BY nombre
        ''')
        
        empresas = []
        for row in cursor.fetchall():
            empresas.append({
                'id': row[0],
                'codigo': row[1],
                'nombre': row[2],
                'cif': row[3],
                'direccion': row[4],
                'telefono': row[5],
                'email': row[6],
                'web': row[7],
                'logo_header': row[8],
                'logo_factura': row[9],
                'color_primario': row[10],
                'color_secundario': row[11],
                'color_success': row[12],
                'color_warning': row[13],
                'color_danger': row[14],
                'color_info': row[15],
                'color_button': row[16],
                'color_button_hover': row[17],
                'activa': row[18],
                'fecha_alta': row[19]
            })
        
        conn.close()
        return jsonify(empresas), 200
        
    except Exception as e:
        logger.error(f"Error listando empresas: {e}", exc_info=True)
        return jsonify({'error': 'Error listando empresas'}), 500

@empresas_bp.route('/api/empresas', methods=['POST'])
@superadmin_required
def crear_empresa():
    """
    Crea una nueva empresa con su BD independiente
    """
    try:
        # Obtener datos del formulario
        nombre = request.form.get('nombre')
        cif = request.form.get('cif', '')
        razon_social = request.form.get('razon_social', nombre)  # Si no se proporciona, usa nombre
        direccion = request.form.get('direccion', '')
        codigo_postal = request.form.get('codigo_postal', '')
        ciudad = request.form.get('ciudad', '')
        provincia = request.form.get('provincia', '')
        telefono = request.form.get('telefono', '')
        email = request.form.get('email', '')
        web = request.form.get('web', '')
        color_primario = request.form.get('color_primario', '#2c3e50')
        color_secundario = request.form.get('color_secundario', '#3498db')
        
        if not nombre:
            return jsonify({'error': 'El nombre de la empresa es obligatorio'}), 400
        
        # Generar código de empresa
        codigo = generar_codigo_empresa(nombre)
        
        # Verificar que no exista otra empresa con ese código
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM empresas WHERE codigo = ?', (codigo,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': f'Ya existe una empresa con código "{codigo}"'}), 400
        
        # Procesar logo si se subió
        logo_filename = None
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Renombrar con código de empresa
                ext = filename.rsplit('.', 1)[1].lower()
                logo_filename = f"{codigo}_logo.{ext}"
                file.save(os.path.join(UPLOAD_FOLDER, logo_filename))
                logger.info(f"Logo guardado: {logo_filename}")
        
        # Crear BD de la empresa
        bd_origen = os.path.join(DB_DIR, 'aleph70.db')
        bd_destino = os.path.join(DB_DIR, f'{codigo}.db')
        
        if not os.path.exists(bd_origen):
            conn.close()
            return jsonify({'error': 'BD de origen (aleph70.db) no encontrada'}), 500
        
        # Clonar estructura
        if not clonar_estructura_bd(bd_origen, bd_destino):
            conn.close()
            return jsonify({'error': 'Error clonando estructura de BD'}), 500
        
        
        # Establecer permisos correctos en la BD recién creada
        import subprocess
        try:
            # Cambiar propietario a www-data:www-data usando sudo
            subprocess.run(['sudo', 'chown', 'www-data:www-data', bd_destino], check=True)
            # Establecer permisos 664 (rw-rw-r--)
            subprocess.run(['sudo', 'chmod', '664', bd_destino], check=True)
            logger.info(f"Permisos establecidos correctamente para BD: {bd_destino}")
        except Exception as perm_error:
            logger.warning(f"No se pudieron establecer permisos automáticamente: {perm_error}")
            logger.warning(f"Por favor, ejecute manualmente: sudo chown www-data:www-data {bd_destino} && sudo chmod 664 {bd_destino}")
        
        # Insertar empresa en BD de usuarios
        cursor.execute('''
            INSERT INTO empresas (
                codigo, nombre, razon_social, cif, direccion, codigo_postal, ciudad, provincia,
                telefono, email, web,
                logo_header, logo_factura, color_primario, color_secundario,
                db_path, activa, fecha_alta
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'))
        ''', (
            codigo, nombre, razon_social, cif, direccion, codigo_postal, ciudad, provincia,
            telefono, email, web,
            logo_filename or 'default_header.png', logo_filename or 'default_header.png', 
            color_primario, color_secundario,
            bd_destino
        ))
        empresa_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        
        # Crear archivo emisor.json para la empresa
        import json
        emisor_data = {
            "nombre": razon_social or nombre,
            "nif": cif or "",
            "direccion": direccion or "",
            "cp": codigo_postal or "",
            "ciudad": ciudad or "",
            "provincia": provincia or "",
            "telefono": telefono or "",
            "email": email or "",
            "web": web or ""
        }
        
        emisor_path = os.path.join(BASE_DIR, 'emisores', f'{codigo}_emisor.json')
        os.makedirs(os.path.dirname(emisor_path), exist_ok=True)
        
        with open(emisor_path, 'w', encoding='utf-8') as f:
            json.dump(emisor_data, f, ensure_ascii=False, indent=4)
        
        logger.info(f"Emisor JSON creado: {emisor_path}")
        logger.info(f"Empresa creada: {nombre} ({codigo}) - BD: {bd_destino}")
        
        return jsonify({
            'success': True,
            'empresa_id': empresa_id,
            'codigo': codigo,
            'nombre': nombre,
            'db_path': bd_destino,
            'mensaje': f'Empresa "{nombre}" creada exitosamente'
        }), 201
        
    except Exception as e:
        logger.error(f"Error creando empresa: {e}", exc_info=True)
        # Limpiar archivos si hubo error
        if logo_filename and os.path.exists(os.path.join(UPLOAD_FOLDER, logo_filename)):
            os.remove(os.path.join(UPLOAD_FOLDER, logo_filename))
        if bd_destino and os.path.exists(bd_destino):
            os.remove(bd_destino)
        return jsonify({'error': 'Error creando empresa'}), 500


@empresas_bp.route('/api/empresas/<int:empresa_id>', methods=['GET'])
@superadmin_required
def obtener_empresa(empresa_id):
    """Obtiene los datos de una empresa específica para edición"""
    try:
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, codigo, nombre, cif, direccion, telefono, email, web,
                   logo_header, logo_factura,
                   color_primario, color_secundario, color_success, color_warning, color_danger, color_info,
                   color_button, color_button_hover, color_button_text,
                   color_app_bg, color_header_bg, color_header_text,
                   color_grid_header, color_grid_hover, color_grid_bg, color_grid_text,
                   color_input_bg, color_input_text, color_input_border,
                   color_select_bg, color_select_text, color_select_border,
                   color_submenu_bg, color_submenu_text, color_submenu_hover,
                   color_icon,
                   color_disabled_bg, color_disabled_text,
                   activa, db_path
            FROM empresas
            WHERE id = ?
        ''', (empresa_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'error': 'Empresa no encontrada'}), 404
        
        return jsonify({
            'id': row[0],
            'codigo': row[1],
            'nombre': row[2],
            'cif': row[3],
            'direccion': row[4],
            'telefono': row[5],
            'email': row[6],
            'web': row[7],
            'logo_header': row[8],
            'logo_factura': row[9],
            'color_primario': row[10],
            'color_secundario': row[11],
            'color_success': row[12],
            'color_warning': row[13],
            'color_danger': row[14],
            'color_info': row[15],
            'color_button': row[16],
            'color_button_hover': row[17],
            'color_button_text': row[18],
            'color_app_bg': row[19],
            'color_header_bg': row[20],
            'color_header_text': row[21],
            'color_grid_header': row[22],
            'color_grid_hover': row[23],
            'color_grid_bg': row[24],
            'color_grid_text': row[25],
            'color_input_bg': row[26],
            'color_input_text': row[27],
            'color_input_border': row[28],
            'color_select_bg': row[29],
            'color_select_text': row[30],
            'color_select_border': row[31],
            'color_submenu_bg': row[32],
            'color_submenu_text': row[33],
            'color_submenu_hover': row[34],
            'color_icon': row[35],
            'color_disabled_bg': row[36],
            'color_disabled_text': row[37],
            'activa': row[38],
            'db_path': row[39]
        }), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo empresa: {e}", exc_info=True)
        return jsonify({'error': 'Error obteniendo empresa'}), 500
@empresas_bp.route('/api/empresas/<int:empresa_id>', methods=['PUT'])
@superadmin_required
def actualizar_empresa(empresa_id):
    """Actualiza datos de una empresa, incluyendo logo"""
    try:
        # Detectar si es FormData (con archivo) o JSON
        content_type = request.content_type
        
        if 'multipart/form-data' in content_type:
            # Viene con archivo (FormData)
            data = request.form.to_dict()
            logo_file = request.files.get('logo')
        else:
            # JSON puro
            data = request.get_json()
            logo_file = None
        
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        # Construir UPDATE dinámicamente
        campos_permitidos = ['nombre', 'cif', 'direccion', 'telefono', 'email', 'web', 
                            'color_primario', 'color_secundario', 'color_success', 'color_warning',
                            'color_danger', 'color_info', 'color_button', 'color_button_hover',
                            'color_button_text', 'color_app_bg',
                            'color_header_bg', 'color_header_text', 'color_grid_header', 'color_grid_hover',
                            'color_input_bg', 'color_input_text', 'color_input_border',
                            'color_submenu_bg', 'color_submenu_text', 'color_submenu_hover',
                            'color_icon', 'color_grid_bg', 'color_grid_text',
                            'color_select_bg', 'color_select_text', 'color_select_border',
                            'color_disabled_bg', 'color_disabled_text',
                            'activa']
        
        campos_update = []
        valores = []
        
        for campo in campos_permitidos:
            if campo in data:
                campos_update.append(f"{campo} = ?")
                # Convertir el campo 'activa' a INTEGER
                if campo == 'activa':
                    # Convertir 'on', 'true', '1', True a 1; cualquier otra cosa a 0
                    valor = data[campo]
                    if valor in ('on', 'true', '1', True, 1):
                        valores.append(1)
                    else:
                        valores.append(0)
                else:
                    valores.append(data[campo])
        
        # Procesar logo si viene archivo
        if logo_file and logo_file.filename:
            # Obtener código de la empresa para nombrar el archivo
            cursor.execute('SELECT codigo FROM empresas WHERE id = ?', (empresa_id,))
            row = cursor.fetchone()
            if row:
                codigo = row[0]
                
                # Validar archivo
                if allowed_file(logo_file.filename):
                    ext = logo_file.filename.rsplit('.', 1)[1].lower()
                    filename = f"{codigo}_logo.{ext}"
                    filepath = os.path.join(UPLOAD_FOLDER, filename)
                    
                    # Guardar archivo
                    logo_file.save(filepath)
                    logger.info(f"Logo actualizado para empresa {codigo}: {filename}")
                    
                    # Agregar logo_header al update
                    campos_update.append("logo_header = ?")
                    valores.append(filename)
                else:
                    conn.close()
                    return jsonify({'error': 'Formato de archivo no permitido'}), 400
        
        if not campos_update:
            conn.close()
            return jsonify({'error': 'No hay campos para actualizar'}), 400
        
        valores.append(empresa_id)
        sql = f"UPDATE empresas SET {', '.join(campos_update)} WHERE id = ?"
        
        logger.info(f"🔧 UPDATE SQL: {sql}")
        logger.info(f"🔧 Valores: {valores}")
        logger.info(f"🔧 Datos recibidos: {data}")
        
        cursor.execute(sql, valores)
        conn.commit()
        
        # Verificar que se guardó
        cursor.execute('SELECT color_primario, color_button, color_success FROM empresas WHERE id = ?', (empresa_id,))
        verificacion = cursor.fetchone()
        logger.info(f"✅ Colores guardados en BD: primario={verificacion[0]}, button={verificacion[1]}, success={verificacion[2]}")
        
        conn.close()
        
        logger.info(f"Empresa {empresa_id} actualizada")
        
        return jsonify({'success': True, 'mensaje': 'Empresa actualizada'}), 200
        
    except Exception as e:
        logger.error(f"Error actualizando empresa: {e}", exc_info=True)
        return jsonify({'error': 'Error actualizando empresa'}), 500

@empresas_bp.route('/api/empresas/generar-colores', methods=['POST'])
@login_required  # Cambiar temporalmente a login_required en lugar de superadmin_required
def generar_colores_automaticos():
    """Genera una paleta de colores armónica basada en el color primario"""
    try:
        data = request.get_json()
        color_primario = data.get('color_primario', '#2c3e50')
        
        # Generar paleta armónica
        palette = generate_palette(color_primario)
        
        logger.info(f"Paleta generada para color {color_primario}: {palette}")
        
        return jsonify(palette), 200
        
    except Exception as e:
        logger.error(f"Error generando colores: {e}", exc_info=True)
        return jsonify({'error': 'Error generando colores'}), 500


@empresas_bp.route('/api/empresas/<int:empresa_id>', methods=['DELETE'])
@superadmin_required
def eliminar_empresa(empresa_id):
    """
    Elimina una empresa físicamente: BD, logo y emisor.json
    """
    try:
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        # Obtener datos de la empresa antes de eliminar
        cursor.execute('SELECT codigo, db_path, logo_header FROM empresas WHERE id = ?', (empresa_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return jsonify({'error': 'Empresa no encontrada'}), 404
        
        codigo, db_path, logo_header = row
        
        # Verificar que no sea la empresa por defecto
        if codigo == 'copisteria' or empresa_id == 1:
            conn.close()
            return jsonify({'error': 'No se puede eliminar la empresa principal'}), 400
        
        # Eliminar de la BD
        cursor.execute('DELETE FROM empresas WHERE id = ?', (empresa_id,))
        
        # Eliminar permisos asociados
        cursor.execute('DELETE FROM permisos_usuario_modulo WHERE empresa_id = ?', (empresa_id,))
        
        # Eliminar asociaciones usuario-empresa
        cursor.execute('DELETE FROM usuario_empresa WHERE empresa_id = ?', (empresa_id,))
        
        conn.commit()
        conn.close()
        
        # Eliminar archivos físicos
        archivos_eliminados = []
        
        # Eliminar BD
        if db_path and os.path.exists(db_path):
            os.remove(db_path)
            archivos_eliminados.append(f'BD: {os.path.basename(db_path)}')
            logger.info(f"BD eliminada: {db_path}")
        
        # Eliminar logo
        if logo_header and not logo_header.startswith('default_'):
            logo_path = os.path.join(UPLOAD_FOLDER, logo_header)
            if os.path.exists(logo_path):
                os.remove(logo_path)
                archivos_eliminados.append(f'Logo: {logo_header}')
                logger.info(f"Logo eliminado: {logo_path}")
        
        # Eliminar emisor.json
        emisor_path = os.path.join(BASE_DIR, 'emisores', f'{codigo}_emisor.json')
        if os.path.exists(emisor_path):
            os.remove(emisor_path)
            archivos_eliminados.append(f'Emisor: {codigo}_emisor.json')
            logger.info(f"Emisor eliminado: {emisor_path}")
        
        logger.info(f"Empresa {empresa_id} ({codigo}) eliminada completamente")
        
        return jsonify({
            'success': True, 
            'mensaje': f'Empresa eliminada completamente',
            'archivos_eliminados': archivos_eliminados
        }), 200
        
    except Exception as e:
        logger.error(f"Error eliminando empresa: {e}", exc_info=True)
        return jsonify({'error': 'Error eliminando empresa'}), 500

@empresas_bp.route('/api/empresas/<int:empresa_id>/emisor', methods=['PUT'])
@superadmin_required
def actualizar_emisor(empresa_id):
    """Actualiza el archivo emisor.json de una empresa"""
    try:
        data = request.get_json()
        
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT codigo FROM empresas WHERE id = ?', (empresa_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'error': 'Empresa no encontrada'}), 404
        
        codigo = row[0]
        
        # Actualizar emisor.json
        emisor_data = {
            "nombre": data.get('razon_social', data.get('nombre', '')),
            "nif": data.get('cif', ''),
            "direccion": data.get('direccion', ''),
            "cp": data.get('codigo_postal', ''),
            "ciudad": data.get('ciudad', ''),
            "provincia": data.get('provincia', ''),
            "telefono": data.get('telefono', ''),
            "email": data.get('email', ''),
            "web": data.get('web', '')
        }
        
        emisor_path = os.path.join(BASE_DIR, 'emisores', f'{codigo}_emisor.json')
        
        with open(emisor_path, 'w', encoding='utf-8') as f:
            json.dump(emisor_data, f, ensure_ascii=False, indent=4)
        
        logger.info(f"Emisor JSON actualizado: {emisor_path}")
        
        return jsonify({'success': True, 'mensaje': 'Emisor actualizado'}), 200
        
    except Exception as e:
        logger.error(f"Error actualizando emisor: {e}", exc_info=True)
        return jsonify({'error': 'Error actualizando emisor'}), 500

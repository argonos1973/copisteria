# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify, send_file, session
from auth_middleware import superadmin_required, require_admin, login_required
import sqlite3
import os
import json
import re
import shutil
from werkzeug.utils import secure_filename
from logger_config import get_logger

logger = get_logger(__name__)


def convertir_tokens_a_legacy(theme_json):
    """Convierte formato nuevo (design tokens) a formato antiguo (color_x)"""
    
    def resolver_referencia(valor, context):
        """Resuelve referencias {palette.x} y {semantic.x}"""
        if not isinstance(valor, str):
            return valor
        
        match = re.match(r'^\{(.+)\}$', valor)
        if not match:
            return valor
        
        path = match.group(1).split('.')
        resolved = context
        for key in path:
            resolved = resolved.get(key) if isinstance(resolved, dict) else None
            if resolved is None:
                return valor
        
        # Recursivo por si la referencia apunta a otra referencia
        return resolver_referencia(resolved, context)
    
    # Mapeo de nuevo formato a antiguo
    legacy = {}
    ctx = theme_json
    
    # Mapeo directo
    mapping = {
        'color_app_bg': ['semantic', 'bg'],
        'color_primario': ['semantic', 'primary'],
        'color_secundario': ['semantic', 'bg-elevated'],
        'color_success': ['semantic', 'success'],
        'color_warning': ['semantic', 'warning'],
        'color_danger': ['semantic', 'danger'],
        'color_info': ['semantic', 'info'],
        'color_button': ['components', 'button', 'bg'],
        'color_button_hover': ['components', 'button', 'hover-bg'],
        'color_button_text': ['components', 'button', 'text'],
        'color_header_bg': ['components', 'header', 'bg'],
        'color_header_text': ['components', 'header', 'text'],
        'color_grid_header': ['components', 'table', 'header-bg'],
        'color_grid_header_text': ['components', 'table', 'header-text'],
        'color_grid_bg': ['components', 'table', 'bg'],
        'color_grid_text': ['components', 'table', 'text'],
        'color_grid_hover': ['components', 'table', 'row-hover'],
        'color_grid_border': ['components', 'table', 'border'],
        'color_input_bg': ['components', 'input', 'bg'],
        'color_input_text': ['components', 'input', 'text'],
        'color_input_border': ['components', 'input', 'border'],
        'color_select_bg': ['components', 'select', 'bg'],
        'color_select_text': ['components', 'select', 'text'],
        'color_select_border': ['components', 'select', 'border'],
        'color_modal_bg': ['components', 'modal', 'bg'],
        'color_modal_text': ['components', 'modal', 'text'],
        'color_modal_border': ['components', 'modal', 'border'],
        'color_modal_overlay': ['components', 'modal', 'overlay'],
        'color_modal_shadow': ['components', 'modal', 'shadow'],
        'color_submenu_bg': ['components', 'menu', 'bg'],
        'color_submenu_text': ['components', 'menu', 'text'],
        'color_submenu_hover': ['components', 'menu', 'hover'],
        'color_icon': ['components', 'icon', 'color'],
        'color_spinner_border': ['components', 'spinner', 'border'],
        'color_tab_active_bg': ['components', 'tab', 'active-bg'],
        'color_tab_active_text': ['components', 'tab', 'active-text'],
        'color_disabled_bg': ['components', 'disabled', 'bg'],
        'color_disabled_text': ['components', 'disabled', 'text']
    }
    
    for old_key, path in mapping.items():
        value = ctx
        for key in path:
            value = value.get(key) if isinstance(value, dict) else None
            if value is None:
                break
        
        if value is not None:
            legacy[old_key] = resolver_referencia(value, ctx)
    
    # Metadata
    if 'meta' in theme_json:
        legacy['nombre'] = theme_json.get('name', 'Custom')
        legacy['descripcion'] = theme_json['meta'].get('description', '')
        legacy['icon'] = theme_json['meta'].get('icon', '🎨')
    
    return legacy


empresas_bp = Blueprint('empresas', __name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_USUARIOS_PATH = '/var/www/html/db/usuarios_sistema.db'
DB_DIR = os.path.join(BASE_DIR, 'db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'logos')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}

def allowed_file(filename):
    """Verifica si el archivo tiene una extensión permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generar_codigo_empresa(nombre):
    """Genera código de empresa a partir del nombre (5 primeros caracteres, sin espacios)"""
    # Quitar acentos y caracteres especiales
    codigo = nombre.upper()
    codigo = re.sub(r'[ÁÀÄÂ]', 'A', codigo)
    codigo = re.sub(r'[ÉÈËÊ]', 'E', codigo)
    codigo = re.sub(r'[ÍÌÏÎ]', 'I', codigo)
    codigo = re.sub(r'[ÓÒÖÔ]', 'O', codigo)
    codigo = re.sub(r'[ÚÙÜÛ]', 'U', codigo)
    codigo = re.sub(r'[^A-Z0-9]', '', codigo)  # Solo letras y números
    return codigo[:5]  # Primeros 5 caracteres

def clonar_estructura_bd(bd_origen, bd_destino):
    """Clona la estructura de una BD sin datos"""
    try:
        # Conectar a BD origen
        conn_origen = sqlite3.connect(bd_origen)
        cursor_origen = conn_origen.cursor()
        
        # Obtener esquema completo
        cursor_origen.execute("SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL")
        tablas = cursor_origen.fetchall()
        
        # Obtener índices
        cursor_origen.execute("SELECT sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL")
        indices = cursor_origen.fetchall()
        
        conn_origen.close()
        
        # Crear BD destino
        if os.path.exists(bd_destino):
            os.remove(bd_destino)
        
        conn_destino = sqlite3.connect(bd_destino)
        cursor_destino = conn_destino.cursor()
        
        # Crear tablas
        for tabla_sql, in tablas:
            try:
                cursor_destino.execute(tabla_sql)
            except Exception as e:
                logger.warning(f"Error creando tabla: {e}")
        
        # Crear índices
        for indice_sql, in indices:
            try:
                cursor_destino.execute(indice_sql)
            except Exception as e:
                logger.warning(f"Error creando índice: {e}")
        
        conn_destino.commit()
        conn_destino.close()
        
        logger.info(f"BD clonada exitosamente: {bd_destino}")
        return True
        
    except Exception as e:
        logger.error(f"Error clonando BD: {e}", exc_info=True)
        return False

# SELECT estándar con TODAS las columnas (20 total - sin color_*)
SELECT_EMPRESAS_FULL = """
    SELECT id, codigo, nombre, razon_social, cif, direccion, telefono, email, web,
           logo_header, logo_factura,
           codigo_postal, ciudad, provincia,
           activa, fecha_alta, fecha_modificacion,
           plantilla, plantilla_personalizada,
           db_path
    FROM empresas
"""

def _row_to_dict_full(row):
    """Convierte row con 20 columnas a diccionario completo (sin color_*)"""
    if not row:
        return None
    if len(row) != 20:
        logger.error(f"Row tiene {len(row)} columnas, se esperaban 20")
        return None
    
    return {
        'id': row[0],
        'codigo': row[1],
        'nombre': row[2],
        'razon_social': row[3],
        'cif': row[4],
        'direccion': row[5],
        'telefono': row[6],
        'email': row[7],
        'web': row[8],
        'logo_header': row[9],
        'logo_factura': row[10],
        'logo_url': f'/static/logos/{row[9]}' if row[9] else '/static/img/logo.png',
        'codigo_postal': row[11],
        'ciudad': row[12],
        'provincia': row[13],
        'activa': row[14],
        'fecha_alta': row[15],
        'fecha_modificacion': row[16],
        'plantilla': row[17],
        'plantilla_personalizada': row[18],
        'db_path': row[19]
    }

@empresas_bp.route('/api/empresas', methods=['GET'])
@require_admin
def listar_empresas():
    """Lista todas las empresas del sistema (requiere admin)"""
    try:
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        cursor.execute(SELECT_EMPRESAS_FULL + " ORDER BY nombre")
        
        empresas = []
        for row in cursor.fetchall():
            empresa = _row_to_dict_full(row)
            if empresa:
                empresas.append(empresa)
        
        conn.close()
        return jsonify(empresas), 200
        
    except Exception as e:
        logger.error(f"Error listando empresas: {e}", exc_info=True)
        return jsonify({'error': 'Error listando empresas'}), 500

@empresas_bp.route('/api/empresas/<int:empresa_id>', methods=['GET'])
@login_required
def obtener_empresa(empresa_id):
    """Obtiene datos de una empresa y su JSON de emisor"""
    try:
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        cursor.execute(SELECT_EMPRESAS_FULL + " WHERE id = ?", (empresa_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'error': 'Empresa no encontrada'}), 404
        
        empresa = _row_to_dict_full(row)
        if not empresa:
            return jsonify({'error': 'Error procesando datos de empresa'}), 500
        
        # Cargar datos de emisor desde JSON
        codigo_empresa = empresa.get('codigo', '')
        emisor_json_path = os.path.join(BASE_DIR, 'emisores', f'{codigo_empresa}_emisor.json')
        
        if os.path.exists(emisor_json_path):
            try:
                with open(emisor_json_path, 'r', encoding='utf-8') as f:
                    emisor_data = json.load(f)
                
                # Sobrescribir con datos del JSON (tienen prioridad)
                empresa['cif'] = emisor_data.get('nif', empresa.get('cif', ''))
                empresa['razon_social'] = emisor_data.get('nombre', empresa.get('razon_social', ''))
                empresa['direccion'] = emisor_data.get('direccion', empresa.get('direccion', ''))
                empresa['codigo_postal'] = emisor_data.get('cp', empresa.get('codigo_postal', ''))
                empresa['ciudad'] = emisor_data.get('ciudad', empresa.get('ciudad', ''))
                empresa['provincia'] = emisor_data.get('provincia', empresa.get('provincia', ''))
                empresa['email'] = emisor_data.get('email', empresa.get('email', ''))
                empresa['pais'] = emisor_data.get('pais', 'ESP')
                
                logger.info(f"Datos de emisor cargados desde {emisor_json_path}")
            except Exception as e:
                logger.error(f"Error cargando JSON de emisor: {e}")
        else:
            logger.info(f"JSON de emisor no encontrado, usando datos de BD: {emisor_json_path}")
        
        return jsonify(empresa), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo empresa: {e}", exc_info=True)
        return jsonify({'error': 'Error obteniendo empresa'}), 500

@empresas_bp.route('/api/empresas/test', methods=['GET'])
def test_empresa():
    """Ruta de prueba sin decorador"""
    print("[DEBUG TEST] Ruta de test ejecutada", flush=True)
    return jsonify({'success': True, 'message': 'Test OK'}), 200

@empresas_bp.route('/api/empresas', methods=['POST'])
@login_required
def crear_empresa():
    """
    Crea una nueva empresa con su BD independiente
    """
    conn = None  # Inicializar conn al principio
    logger.error(f"[DEBUG CRITICAL] Función crear_empresa llamada - inicio")
    try:
        # Debug: log de datos recibidos
        logger.error(f"[DEBUG] Dentro del try - Iniciando crear_empresa")
        logger.info(f"[CREAR EMPRESA] Form data recibido: {dict(request.form)}")
        logger.info(f"[CREAR EMPRESA] Files recibidos: {list(request.files.keys())}")
        logger.error(f"[DEBUG] Datos recibidos OK")
        
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
        
        logger.info(f"[CREAR EMPRESA] Nombre recibido: '{nombre}'")
        
        if not nombre:
            logger.warning(f"[CREAR EMPRESA] Nombre vacío o None")
            return jsonify({'error': 'El nombre de la empresa es obligatorio'}), 400
        
        # Generar código de empresa
        codigo = generar_codigo_empresa(nombre)
        print(f"[DEBUG] Código generado: {codigo}", flush=True)
        
        # Verificar que no exista otra empresa con ese código
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM empresas WHERE codigo = ?', (codigo,))
        if cursor.fetchone():
            conn.close()
            print(f"[DEBUG] Empresa {codigo} ya existe", flush=True)
            return jsonify({'error': f'Ya existe una empresa con código "{codigo}"'}), 400
        
        print(f"[DEBUG] Empresa {codigo} no existe, continuando...", flush=True)
        
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
        
        # Crear directorio para la empresa
        empresa_dir = os.path.join(DB_DIR, codigo)
        print(f"[DEBUG] Creando directorio: {empresa_dir}", flush=True)
        os.makedirs(empresa_dir, exist_ok=True)
        # Establecer permisos inmediatamente después de crear el directorio
        os.chmod(empresa_dir, 0o775)
        logger.info(f"Directorio creado para empresa: {empresa_dir}")
        print(f"[DEBUG] Directorio creado OK", flush=True)
        
        # Crear BD de la empresa dentro del subdirectorio
        bd_origen = os.path.join(DB_DIR, 'plantilla.db')
        bd_destino = os.path.join(empresa_dir, f'{codigo}.db')
        
        print(f"[DEBUG] BD origen: {bd_origen}, existe: {os.path.exists(bd_origen)}", flush=True)
        print(f"[DEBUG] BD destino: {bd_destino}", flush=True)
        
        if not os.path.exists(bd_origen):
            conn.close()
            print(f"[DEBUG ERROR] Plantilla no encontrada", flush=True)
            return jsonify({'error': 'BD plantilla (plantilla.db) no encontrada'}), 500
        
        # Clonar estructura
        print(f"[DEBUG] Iniciando clonación de BD...", flush=True)
        if not clonar_estructura_bd(bd_origen, bd_destino):
            conn.close()
            print(f"[DEBUG ERROR] Error clonando BD", flush=True)
            return jsonify({'error': 'Error clonando estructura de BD'}), 500
        
        print(f"[DEBUG] BD clonada exitosamente", flush=True)
        
        
        # Establecer permisos correctos en directorio y BD
        import subprocess
        try:
            # Cambiar propietario del directorio a www-data:www-data
            subprocess.run(['sudo', 'chown', '-R', 'www-data:www-data', empresa_dir], check=True)
            # Establecer permisos 775 al directorio (rwxrwxr-x)
            subprocess.run(['sudo', 'chmod', '775', empresa_dir], check=True)
            # Establecer permisos 664 a la BD (rw-rw-r--)
            subprocess.run(['sudo', 'chmod', '664', bd_destino], check=True)
            logger.info(f"Permisos establecidos correctamente para directorio: {empresa_dir}")
            logger.info(f"Permisos establecidos correctamente para BD: {bd_destino}")
        except Exception as perm_error:
            logger.warning(f"No se pudieron establecer permisos automáticamente: {perm_error}")
            logger.warning(f"Por favor, ejecute manualmente: sudo chown -R www-data:www-data {empresa_dir} && sudo chmod 775 {empresa_dir} && sudo chmod 664 {bd_destino}")
        
        # Insertar empresa en BD de usuarios (SIN COMMIT todavía)
        cursor.execute('''
            INSERT INTO empresas (
                codigo, nombre, razon_social, cif, direccion, codigo_postal, ciudad, provincia,
                telefono, email, web,
                logo_header, logo_factura,
                db_path, activa, fecha_alta
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'))
        ''', (
            codigo, nombre, razon_social, cif, direccion, codigo_postal, ciudad, provincia,
            telefono, email, web,
            logo_filename or 'default_header.png', logo_filename or 'default_header.png',
            bd_destino
        ))
        empresa_id = cursor.lastrowid
        # NO cerrar conexión todavía, la necesitamos para crear el usuario admin
        
        
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
            "web": web or "",
            "db_path": bd_destino,
            "codigo": codigo
        }
        
        emisor_path = os.path.join(BASE_DIR, 'emisores', f'{codigo}_emisor.json')
        os.makedirs(os.path.dirname(emisor_path), exist_ok=True)
        
        with open(emisor_path, 'w', encoding='utf-8') as f:
            json.dump(emisor_data, f, ensure_ascii=False, indent=4)
        
        logger.info(f"Emisor JSON creado: {emisor_path}")
        
        # Crear usuario admin automático para la empresa
        import hashlib
        username_admin = f'admin_{codigo.lower()}'
        password_admin = codigo.lower()  # Contraseña inicial = código de empresa
        password_hash = hashlib.sha256(password_admin.encode('utf-8')).hexdigest()
        
        # Usar la misma conexión que ya tenemos abierta
        try:
            # Crear usuario admin (es_superadmin = 0, ya no hay superadmins)
            cursor.execute('''
                INSERT INTO usuarios (username, password_hash, nombre_completo, email, es_superadmin, activo)
                VALUES (?, ?, ?, ?, 0, 1)
            ''', (username_admin, password_hash, f'Administrador {nombre}', email or ''))
            
            usuario_admin_id = cursor.lastrowid
            
            # Asignar empresa al usuario admin
            cursor.execute('''
                INSERT INTO usuario_empresa (usuario_id, empresa_id, rol, es_admin_empresa)
                VALUES (?, ?, 'admin', 1)
            ''', (usuario_admin_id, empresa_id))
            
            # También asignar empresa al usuario actual si no tiene empresa
            usuario_actual_id = session.get('user_id')
            empresa_actual = session.get('empresa_id')
            if usuario_actual_id and not empresa_actual:
                # Asignar la nueva empresa al usuario actual como admin
                cursor.execute('''
                    INSERT INTO usuario_empresa (usuario_id, empresa_id, rol, es_admin_empresa)
                    VALUES (?, ?, 'admin', 1)
                ''', (usuario_actual_id, empresa_id))
                logger.info(f"Empresa {codigo} asignada al usuario actual {session.get('username')}")
            
            # Asignar TODOS los permisos al admin
            modulos = ['facturas', 'tickets', 'proformas', 'productos', 'contactos', 'presupuestos']
            permisos_completos = ['ver', 'crear', 'editar', 'eliminar', 'anular', 'exportar']
            
            for modulo in modulos:
                # Crear permisos completos para cada módulo
                permisos_dict = {permiso: 1 for permiso in permisos_completos}
                cursor.execute('''
                    INSERT INTO permisos_usuario_modulo 
                    (usuario_id, empresa_id, modulo_codigo, ver, crear, editar, eliminar, anular, exportar)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (usuario_admin_id, empresa_id, modulo,
                      permisos_dict.get('ver', 1),
                      permisos_dict.get('crear', 1),
                      permisos_dict.get('editar', 1),
                      permisos_dict.get('eliminar', 1),
                      permisos_dict.get('anular', 1),
                      permisos_dict.get('exportar', 1)))
            
            conn.commit()
            logger.info(f"Usuario admin creado: {username_admin} para empresa {codigo}")
            logger.info(f"Contraseña inicial: {password_admin}")
            
        except sqlite3.IntegrityError:
            logger.warning(f"Usuario {username_admin} ya existe, saltando creación")
        finally:
            conn.close()
        
        logger.info(f"Empresa creada: {nombre} ({codigo}) - BD: {bd_destino}")
        
        return jsonify({
            'success': True,
            'empresa_id': empresa_id,
            'codigo': codigo,
            'nombre': nombre,
            'db_path': bd_destino,
            'usuario_admin': username_admin,
            'password_admin': password_admin,
            'mensaje': f'Empresa "{nombre}" creada exitosamente. Usuario admin: {username_admin} / {password_admin}'
        }), 201
        
    except Exception as e:
        print(f"[DEBUG ERROR] {type(e).__name__}: {e}", flush=True)
        import traceback
        traceback.print_exc()
        logger.error(f"Error creando empresa: {e}", exc_info=True)
        # Hacer rollback de la transacción si hay error
        try:
            if 'conn' in locals() and conn:
                conn.rollback()
                conn.close()
                logger.info("Rollback de transacción realizado")
        except:
            pass
        # Limpiar archivos si hubo error
        if 'logo_filename' in locals() and logo_filename and os.path.exists(os.path.join(UPLOAD_FOLDER, logo_filename)):
            os.remove(os.path.join(UPLOAD_FOLDER, logo_filename))
        if 'bd_destino' in locals() and bd_destino and os.path.exists(bd_destino):
            os.remove(bd_destino)
        if 'empresa_dir' in locals() and empresa_dir and os.path.exists(empresa_dir):
            import shutil
            shutil.rmtree(empresa_dir)
        if 'emisor_path' in locals() and emisor_path and os.path.exists(emisor_path):
            os.remove(emisor_path)
        return jsonify({'error': f'Error creando empresa: {str(e)}'}), 500


@empresas_bp.route('/api/empresas/<int:empresa_id>', methods=['PUT'])
@login_required
def actualizar_empresa(empresa_id):
    """Actualiza datos de empresa y guarda datos de emisor en JSON"""
    try:
        # SEGURIDAD: Verificar permisos
        es_superadmin = session.get('es_superadmin', False)
        empresa_id_usuario = session.get('empresa_id')
        user_id = session.get('user_id')
        
        # Solo superadmin puede editar cualquier empresa
        # Admin de empresa solo puede editar su propia empresa
        if not es_superadmin:
            if empresa_id != empresa_id_usuario:
                logger.warning(f"Usuario {session.get('username')} intentó modificar empresa {empresa_id} sin permisos")
                return jsonify({'error': 'No tienes permisos para modificar esta empresa'}), 403
        
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
        
        # Obtener código, nombre y db_path de empresa para el archivo JSON
        cursor.execute('SELECT codigo, nombre, db_path FROM empresas WHERE id = ?', (empresa_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({'error': 'Empresa no encontrada'}), 404
        
        codigo_empresa = row[0]
        nombre_empresa = row[1]
        db_path_empresa = row[2]
        
        # Construir datos de emisor para JSON
        emisor_data = {
            'nif': data.get('cif', ''),
            'nombre': data.get('razon_social', data.get('nombre', '')),
            'direccion': data.get('direccion', ''),
            'cp': data.get('codigo_postal', ''),
            'ciudad': data.get('ciudad', ''),
            'provincia': data.get('provincia', ''),
            'pais': 'ESP',
            'email': data.get('email', ''),
            'db_path': db_path_empresa,
            'codigo': codigo_empresa
        }
        
        # Guardar JSON de emisor
        emisor_json_path = os.path.join(BASE_DIR, 'emisores', f'{codigo_empresa}_emisor.json')
        try:
            with open(emisor_json_path, 'w', encoding='utf-8') as f:
                json.dump(emisor_data, f, indent=4, ensure_ascii=False)
            logger.info(f"Datos de emisor guardados en {emisor_json_path}")
        except Exception as e:
            logger.error(f"Error guardando JSON de emisor: {e}")
            conn.close()
            return jsonify({'error': f'Error guardando datos de emisor: {str(e)}'}), 500
        
        # Actualizar solo nombre y logo en BD (lo esencial para la app)
        campos_update = []
        valores = []
        
        # Solo guardar nombre y activa en BD
        if 'nombre' in data:
            campos_update.append("nombre = ?")
            valores.append(data['nombre'])
        
        if 'activa' in data:
            campos_update.append("activa = ?")
            valor = data['activa']
            if valor in ('on', 'true', '1', True, 1):
                valores.append(1)
            else:
                valores.append(0)
        
        # Procesar logo si viene archivo
        if logo_file and logo_file.filename:
            # Validar archivo
            if allowed_file(logo_file.filename):
                ext = logo_file.filename.rsplit('.', 1)[1].lower()
                filename = f"{codigo_empresa}_logo.{ext}"
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                
                # Guardar archivo
                logo_file.save(filepath)
                logger.info(f"Logo actualizado para empresa {codigo_empresa}: {filename}")
                
                # Agregar logo_header al update
                campos_update.append("logo_header = ?")
                valores.append(filename)
            else:
                conn.close()
                return jsonify({'error': 'Formato de archivo no permitido'}), 400
        
        # Ejecutar UPDATE solo si hay campos para actualizar
        if campos_update:
            query = f"UPDATE empresas SET {', '.join(campos_update)} WHERE id = ?"
            valores.append(empresa_id)
            cursor.execute(query, valores)
            logger.info(f"Empresa {empresa_id} actualizada en BD")
        
        conn.commit()
        conn.close()
        
        logger.info(f"Empresa {empresa_id} y datos de emisor actualizados correctamente")
        
        return jsonify({
            'success': True, 
            'mensaje': 'Datos de empresa guardados correctamente',
            'emisor_json': f'{codigo_empresa}_emisor.json'
        }), 200
        
    except Exception as e:
        logger.error(f"Error actualizando empresa: {e}", exc_info=True)
        logger.error(f"Datos recibidos: empresa_id={empresa_id}, user_id={session.get('user_id')}, es_superadmin={session.get('es_superadmin')}")
        return jsonify({'error': f'Error actualizando empresa: {str(e)}'}), 500


@empresas_bp.route('/api/empresas/generar-colores', methods=['POST'])
@login_required
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
@login_required
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
        
        # Eliminar directorio completo de la empresa (incluye BD y otros archivos)
        empresa_dir = os.path.join(DB_DIR, codigo)
        if os.path.exists(empresa_dir) and os.path.isdir(empresa_dir):
            shutil.rmtree(empresa_dir)
            archivos_eliminados.append(f'Directorio: {codigo}/')
            logger.info(f"Directorio de empresa eliminado: {empresa_dir}")
        elif db_path and os.path.exists(db_path):
            # Fallback: si no existe el directorio pero existe la BD antigua (migración)
            os.remove(db_path)
            archivos_eliminados.append(f'BD: {os.path.basename(db_path)}')
            logger.info(f"BD eliminada (antigua estructura): {db_path}")
        
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

# ENDPOINT /colores ELIMINADO - Ya no se usan colores en BD, solo plantillas JSON

@empresas_bp.route('/api/empresas/<int:empresa_id>/emisor', methods=['PUT'])
@login_required
def actualizar_emisor(empresa_id):
    """Actualiza el archivo emisor.json de una empresa"""
    try:
        data = request.get_json()
        
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT codigo, db_path FROM empresas WHERE id = ?', (empresa_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'error': 'Empresa no encontrada'}), 404
        
        codigo = row[0]
        db_path = row[1]
        
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
            "web": data.get('web', ''),
            "db_path": db_path,
            "codigo": codigo
        }
        
        emisor_path = os.path.join(BASE_DIR, 'emisores', f'{codigo}_emisor.json')
        
        with open(emisor_path, 'w', encoding='utf-8') as f:
            json.dump(emisor_data, f, ensure_ascii=False, indent=4)
        
        logger.info(f"Emisor JSON actualizado: {emisor_path}")
        
        return jsonify({'success': True, 'mensaje': 'Emisor actualizado'}), 200
        
    except Exception as e:
        logger.error(f"Error actualizando emisor: {e}", exc_info=True)
        return jsonify({'error': 'Error actualizando emisor'}), 500

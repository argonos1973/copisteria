# -*- coding: utf-8 -*-
"""
============================================================================
RUTAS DE AUTENTICACIÓN
============================================================================
Archivo: auth_routes.py
Descripción: Endpoints para login, logout y gestión de sesiones
Fecha: 2025-10-21
============================================================================
"""

import os
import io
import base64
import uuid
import secrets
import requests
import pyotp
import qrcode
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from flask import Blueprint, request, jsonify, session, render_template_string, Response, make_response
from logger_config import get_logger
from auth_middleware import (
    autenticar_usuario, cerrar_sesion, obtener_empresas_usuario,
    login_required, registrar_auditoria
)
import sqlite3
from multiempresa_config import DB_USUARIOS_PATH, GOOGLE_AUTH_CONFIG, obtener_db_empresa
from database_pool import get_database_pool
from email_utils import enviar_email_recuperacion_password

# Configuración de avatares
AVATAR_FOLDER = 'static/avatars'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

logger = get_logger(__name__)

# Crear blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# ============================================================================
# ENDPOINTS DE AUTENTICACIÓN
# ============================================================================

@auth_bp.route('/config', methods=['GET'])
def get_auth_config():
    """Retorna configuración pública de autenticación"""
    return jsonify({
        'google_client_id': GOOGLE_AUTH_CONFIG.get('CLIENT_ID')
    })

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Endpoint de login
    
    Body JSON:
    {
        "username": "admin",
        "password": "admin123",
        "empresa": "copisteria"
    }
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({'error': 'Datos incompletos'}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        empresa_codigo = data.get('empresa', '').strip() if data.get('empresa') else None
        
        if not username or not password:
            return jsonify({'error': 'Usuario y contraseña son requeridos'}), 400
        
        logger.info(f"Intento de login: {username} → {empresa_codigo}")
        
        # Autenticar
        resultado = autenticar_usuario(username, password, empresa_codigo)
        
        if resultado is None:
            return jsonify({'error': 'Usuario o contraseña incorrectos'}), 401
        
        if 'error' in resultado:
            return jsonify(resultado), 401
        
        # IMPORTANTE: Usar make_response para asegurar que la cookie se envíe
        response = make_response(jsonify(resultado), 200)
        
        # Forzar que Flask guarde la sesión
        session.permanent = True
        session.modified = True
        
        # Agregar headers CORS para cookies
        origin = request.headers.get('Origin')
        if origin and 'trycloudflare.com' in origin:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
        
        return response
        
    except Exception as e:
        logger.error(f"Error en endpoint login: {e}", exc_info=True)
        return jsonify({'error': 'Error en el servidor'}), 500

@auth_bp.route('/google', methods=['POST'])
def google_auth():
    """
    Autenticación/Registro con Google
    Recibe un JWT credential del frontend.
    """
    try:
        data = request.json
        token = data.get('token')
        
        if not token:
            return jsonify({'error': 'Token no proporcionado'}), 400
            
        # Verificar token con Google
        google_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"
        res = requests.get(google_url)
        
        if res.status_code != 200:
            logger.error(f"Token Google inválido: {res.text}")
            return jsonify({'error': 'Token de Google inválido'}), 401
            
        google_data = res.json()
        
        email = google_data.get('email')
        name = google_data.get('name')
        picture = google_data.get('picture')
        
        if not email:
            return jsonify({'error': 'Google no proporcionó email'}), 400
            
        # Buscar usuario en BD
        with get_database_pool(DB_USUARIOS_PATH).get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
            usuario = cursor.fetchone()
            
            user_id = None
            username = ""
            rol = "consultor"
            
            if usuario:
                # Usuario existe
                user_id = usuario['id']
                username = usuario['username']
                rol = usuario['rol']
                logger.info(f"Login Google: Usuario existente {email}")
                
                # Actualizar avatar si no tiene
                if picture and not usuario['avatar']:
                    cursor.execute("UPDATE usuarios SET avatar = ? WHERE id = ?", (picture, user_id))
                    conn.commit()
            else:
                # Usuario no existe, CREARLO con periodo de prueba de 14 días
                logger.info(f"Login Google: Creando nuevo usuario {email} con periodo de prueba")
                
                # Generar username único
                username_base = email.split('@')[0]
                username = username_base
                counter = 1
                while True:
                    cursor.execute("SELECT 1 FROM usuarios WHERE username = ?", (username,))
                    if not cursor.fetchone():
                        break
                    username = f"{username_base}{counter}"
                    counter += 1
                
                # Password aleatoria
                password_random = secrets.token_urlsafe(16)
                password_hash = generate_password_hash(password_random)
                
                # Crear usuario con rol admin para su empresa de prueba
                cursor.execute("""
                    INSERT INTO usuarios (username, password_hash, email, nombre_completo, avatar, rol, activo, fecha_creacion)
                    VALUES (?, ?, ?, ?, ?, 'admin', 1, CURRENT_TIMESTAMP)
                """, (username, password_hash, email, name, picture))
                
                user_id = cursor.lastrowid
                rol = 'admin'
                
                # Crear empresa de prueba para el nuevo usuario
                from datetime import timedelta
                import os
                import shutil
                
                fecha_fin_prueba = datetime.now() + timedelta(days=14)
                empresa_codigo = f"trial_{username}_{user_id}"
                empresa_nombre = f"Empresa de prueba - {name or username}"
                
                # Crear directorio y BD para la empresa de prueba
                db_dir = f"/var/www/html/db/{empresa_codigo}"
                db_path = f"{db_dir}/{empresa_codigo}.db"
                
                os.makedirs(db_dir, exist_ok=True)
                
                # Copiar BD plantilla si existe, sino crear vacía
                plantilla_db = "/var/www/html/db/plantilla/plantilla.db"
                if os.path.exists(plantilla_db):
                    shutil.copy2(plantilla_db, db_path)
                    logger.info(f"BD de prueba creada desde plantilla: {db_path}")
                else:
                    # Crear BD vacía básica
                    import sqlite3 as sqlite3_local
                    conn_trial = sqlite3_local.connect(db_path)
                    conn_trial.close()
                    logger.info(f"BD de prueba creada vacía: {db_path}")
                
                # Insertar empresa en tabla empresas
                cursor.execute("""
                    INSERT INTO empresas (codigo, nombre, db_path, fecha_fin_prueba, activa)
                    VALUES (?, ?, ?, ?, 1)
                """, (empresa_codigo, empresa_nombre, db_path, fecha_fin_prueba.strftime('%Y-%m-%d %H:%M:%S')))
                
                empresa_id = cursor.lastrowid
                
                # Asignar usuario a la empresa con rol admin
                cursor.execute("""
                    INSERT INTO usuarios_empresas (usuario_id, empresa_id, rol, activo)
                    VALUES (?, ?, 'admin', 1)
                """, (user_id, empresa_id))
                
                conn.commit()
                logger.info(f"Empresa de prueba creada: {empresa_codigo} (válida hasta {fecha_fin_prueba})")
        
        # Iniciar sesión
        session.clear()
        session['user_id'] = user_id
        session['username'] = username
        session['email'] = email
        session['rol'] = rol
        session['nombre_completo'] = name
        session['ultimo_acceso'] = datetime.now().isoformat()
        
        # Intentar auto-seleccionar empresa si tiene una sola
        empresas = obtener_empresas_usuario(username)
        if len(empresas) == 1:
            emp = empresas[0]
            session['empresa_id'] = emp['id']
            session['empresa_nombre'] = emp['nombre']
            session['empresa_codigo'] = emp['codigo']
            session['empresa_logo'] = emp['logo']
            
            # Obtener y establecer la BD de la empresa
            db_path = obtener_db_empresa(emp['id'])
            if db_path:
                session['empresa_db'] = db_path
                logger.info(f"Login Google: BD establecida para {username}: {db_path}")
            else:
                logger.error(f"Login Google: No se pudo obtener BD para empresa {emp['id']}")
            
            # Verificar rol específico en esa empresa
            with get_database_pool(DB_USUARIOS_PATH).get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT es_admin_empresa FROM usuario_empresa WHERE usuario_id=? AND empresa_id=?", (user_id, emp['id']))
                row = cursor.fetchone()
                if row and row[0]:
                    session['es_admin_empresa'] = True
        
        # Registrar auditoría
        registrar_auditoria('login_google', f"Login vía Google: {email}")
        
        # Respuesta exitosa
        response = make_response(jsonify({
            'success': True,
            'usuario': name,
            'redirect': '/api/auth/app'
        }), 200)
        
        session.permanent = True
        session.modified = True
        
        return response

    except Exception as e:
        logger.error(f"Error en auth google: {e}", exc_info=True)
        # DEBUG: Retornar el error específico para depuración
        return jsonify({'error': f'Error interno: {str(e)}'}), 500

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """
    Endpoint de logout
    """
    try:
        cerrar_sesion()
        return jsonify({'success': True, 'mensaje': 'Sesión cerrada'}), 200
    except Exception as e:
        logger.error(f"Error en logout: {e}", exc_info=True)
        return jsonify({'error': 'Error cerrando sesión'}), 500

# ============================================================================
# PREFERENCIAS DEL USUARIO
# ============================================================================

@auth_bp.route('/preferencias', methods=['GET'])
@login_required
def obtener_preferencias():
    """Obtiene las preferencias del usuario actual"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'No autenticado'}), 401
        
        import json
        with get_database_pool(DB_USUARIOS_PATH).get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT preferencias FROM usuarios WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            
            if row and row['preferencias']:
                try:
                    prefs = json.loads(row['preferencias'])
                except:
                    prefs = {}
            else:
                prefs = {}
        
        return jsonify(prefs), 200
    except Exception as e:
        logger.error(f"Error obteniendo preferencias: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/preferencias', methods=['POST'])
@login_required
def guardar_preferencias():
    """Guarda las preferencias del usuario actual"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'No autenticado'}), 401
        
        import json
        data = request.get_json() or {}
        
        with get_database_pool(DB_USUARIOS_PATH).get_db_connection() as conn:
            cursor = conn.cursor()
            # Obtener preferencias actuales
            cursor.execute("SELECT preferencias FROM usuarios WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            
            if row and row['preferencias']:
                try:
                    prefs = json.loads(row['preferencias'])
                except:
                    prefs = {}
            else:
                prefs = {}
            
            # Merge con nuevas preferencias
            prefs.update(data)
            
            # Guardar
            cursor.execute("UPDATE usuarios SET preferencias = ? WHERE id = ?", 
                          (json.dumps(prefs), user_id))
            conn.commit()
        
        return jsonify({'success': True}), 200
    except Exception as e:
        logger.error(f"Error guardando preferencias: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/empresas/<username>', methods=['GET'])
def obtener_empresas(username):
    """
    Obtiene las empresas disponibles para un usuario
    
    Endpoint: GET /api/auth/empresas/admin
    """
    try:
        # Decodificar y limpiar username por si acaso
        username = username.strip()
        logger.info(f"Solicitando empresas para usuario: '{username}'")
        
        empresas = obtener_empresas_usuario(username)
        return jsonify(empresas), 200
    except Exception as e:
        logger.error(f"Error obteniendo empresas para '{username}': {e}", exc_info=True)
        return jsonify({'error': 'Error obteniendo empresas'}), 500

@auth_bp.route('/verify-session', methods=['GET', 'POST'])
@login_required
def verificar_sesion():
    """Verifica si la sesión actual es válida"""
    try:
        return jsonify({
            'valid': True,
            'usuario': session.get('nombre_completo'),
            'username': session.get('username'),
            'empresa': session.get('empresa_nombre')
        }), 200
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)}), 401

@auth_bp.route('/session', methods=['GET'])
@login_required
def obtener_sesion():
    """
    Obtiene información de la sesión actual
    """
    try:
        user_id = session.get('user_id')
        empresa_id = session.get('empresa_id')
        
        # Valores por defecto de sesión
        avatar = None
        email = None
        telefono = None
        rol = session.get('rol')
        es_admin_empresa = session.get('es_admin_empresa', False)
        es_superadmin = session.get('es_superadmin', False)
        
        if user_id:
            with get_database_pool(DB_USUARIOS_PATH).get_db_connection() as conn:
                cursor = conn.cursor()
                # Leer datos actualizados del usuario incluyendo rol
                cursor.execute('SELECT avatar, email, telefono, rol, es_superadmin FROM usuarios WHERE id = ?', (user_id,))
                result = cursor.fetchone()
                if result:
                    avatar = result[0] if result[0] else None
                    email = result[1] if result[1] else None
                    telefono = result[2] if result[2] else None
                    rol = result[3] # Actualizar rol
                    es_superadmin = bool(result[4]) if result[4] is not None else False
                    
                    # Actualizar sesión con datos frescos
                    session['rol'] = rol
                    session['es_superadmin'] = es_superadmin
                
                # Si hay empresa, verificar permiso de admin actualizado
                if empresa_id:
                    cursor.execute("SELECT es_admin_empresa FROM usuario_empresa WHERE usuario_id=? AND empresa_id=?", (user_id, empresa_id))
                    row_emp = cursor.fetchone()
                    if row_emp:
                        es_admin_empresa = bool(row_emp[0])
                        session['es_admin_empresa'] = es_admin_empresa

        return jsonify({
            'usuario': session.get('nombre_completo'),
            'username': session.get('username'),
            'email': email,
            'telefono': telefono,
            'empresa': session.get('empresa_nombre'),
            'empresa_id': session.get('empresa_id'),
            'empresa_codigo': session.get('empresa_codigo'),
            'logo': session.get('empresa_logo') or '/public/assets/logo.svg',
            'avatar': avatar,
            'rol': rol,
            'es_admin': es_admin_empresa or es_superadmin,
            'es_admin_empresa': es_admin_empresa,
            'es_superadmin': es_superadmin,
            'ultimo_acceso': session.get('ultimo_acceso')
        }), 200
    except Exception as e:
        logger.error(f"Error obteniendo sesión: {e}", exc_info=True)
        return jsonify({'error': 'Error obteniendo sesión'}), 500

@auth_bp.route('/menu', methods=['GET'])
@login_required
def obtener_menu():
    """
    Retorna el menú según permisos del usuario logueado
    """
    try:
        user_id = session.get('user_id')
        empresa_id = session.get('empresa_id')
        es_superadmin = session.get('es_superadmin')
        es_admin_empresa = session.get('es_admin_empresa', False)
        
        logger.info(f"[MENU] user_id={user_id}, empresa_id={empresa_id}, es_superadmin={es_superadmin}, es_admin_empresa={es_admin_empresa}")
        
        # Si el usuario no tiene empresa asignada, solo mostrar menú de gestión
        if not empresa_id:
            logger.info(f"[MENU] Usuario sin empresa - mostrando menú de gestión inicial")
            menu_limitado = [{
                'codigo': 'gestion',
                'nombre': 'Mi Empresa',
                'icono': 'fas fa-building',
                'ruta': '/bienvenida.html',  # Página de inicio por defecto
                'submenu': [
                    {'nombre': 'Crear Mi Empresa', 'icono': 'fas fa-plus-circle', 'ruta': '/crear_empresa'},
                    {'nombre': 'Mi Perfil', 'icono': 'fas fa-user', 'ruta': '/perfil'},
                    {'nombre': 'Cambiar Contraseña', 'icono': 'fas fa-key', 'ruta': '/cambiar_password'}
                ]
            }]
            return jsonify(menu_limitado), 200
        
        rows = []
        permisos_usuario = {}
        
        with get_database_pool(DB_USUARIOS_PATH).get_db_connection() as conn:
            cursor = conn.cursor()
            
            if es_admin_empresa:
                # Admin de empresa ve todos los módulos de su empresa
                cursor.execute('''
                    SELECT codigo, nombre, ruta, icono, orden
                    FROM modulos
                    WHERE activo = 1
                    ORDER BY orden
                ''')
            else:
                # Usuario normal según permisos
                # Obtener TODOS los módulos con Ver=1 primero
                sql = '''
                    SELECT 
                        m.codigo,
                        m.nombre,
                        m.ruta,
                        m.icono,
                        m.orden,
                        p.puede_ver,
                        p.puede_crear,
                        p.puede_editar,
                        p.puede_eliminar,
                        p.puede_anular,
                        p.puede_exportar
                    FROM modulos m
                    JOIN permisos_usuario_modulo p ON m.codigo = p.modulo_codigo
                    WHERE p.usuario_id = ? 
                    AND p.empresa_id = ?
                    AND p.puede_ver = 1
                    AND m.activo = 1
                    ORDER BY m.orden
                '''
                logger.info(f"[MENU] Ejecutando query con user_id={user_id}, empresa_id={empresa_id}")
                cursor.execute(sql, (user_id, empresa_id))
            
            rows = cursor.fetchall()
            logger.info(f"[MENU] Encontrados {len(rows)} módulos")
            
            # Obtener todos los permisos del usuario para filtrar submenús
            if not es_admin_empresa:
                cursor.execute('''
                    SELECT modulo_codigo, puede_ver, puede_crear, puede_editar, 
                           puede_eliminar, puede_anular, puede_exportar
                    FROM permisos_usuario_modulo
                    WHERE usuario_id = ? AND empresa_id = ?
                ''', (user_id, empresa_id))
                for perm_row in cursor.fetchall():
                    permisos_usuario[perm_row[0]] = {
                        'puede_ver': perm_row[1],
                        'puede_crear': perm_row[2],
                        'puede_editar': perm_row[3],
                        'puede_eliminar': perm_row[4],
                        'puede_anular': perm_row[5],
                        'puede_exportar': perm_row[6]
                    }
        
        # Definir submódulos fuera del loop
        submenu_map = {
            'facturas_emitidas': [
                {
                    'codigo': 'tickets',
                    'nombre': 'Tickets',
                    'icono': 'fas fa-receipt',
                    'ruta': '#',
                    'submenu': [
                        {'nombre': 'Consultar', 'icono': 'fas fa-search', 'ruta': '/CONSULTA_TICKETS.html'},
                        {'nombre': 'Nuevo', 'icono': 'fas fa-plus', 'ruta': '/GESTION_TICKETS.html'}
                    ]
                },
                {
                    'codigo': 'facturas',
                    'nombre': 'Facturas',
                    'icono': 'fas fa-file-invoice',
                    'ruta': '#',
                    'submenu': [
                        {'nombre': 'Consultar', 'icono': 'fas fa-search', 'ruta': '/CONSULTA_FACTURAS.html'}
                    ]
                },
                {
                    'codigo': 'proformas',
                    'nombre': 'Proformas',
                    'icono': 'fas fa-file-contract',
                    'ruta': '#',
                    'submenu': [
                        {'nombre': 'Consultar', 'icono': 'fas fa-search', 'ruta': '/CONSULTA_PROFORMAS.html'}
                    ]
                }
            ],
            'presupuestos': [
                {'nombre': 'Consultar', 'icono': 'fas fa-search', 'ruta': '/CONSULTA_PRESUPUESTOS.html'},
                {'nombre': 'Nuevo', 'icono': 'fas fa-plus', 'ruta': '/GESTION_PRESUPUESTOS.html'}
            ],
            'productos': [
                {'nombre': 'Consultar', 'icono': 'fas fa-search', 'ruta': '/CONSULTA_PRODUCTOS.html'},
                {'nombre': 'Franjas', 'icono': 'fas fa-percentage', 'ruta': '/FRANJAS_DESCUENTO.html'}
            ],
            'contactos': [
                {'nombre': 'Consultar', 'icono': 'fas fa-search', 'ruta': '/CONSULTA_CONTACTOS.html'},
                {'nombre': 'Nuevo', 'icono': 'fas fa-plus', 'ruta': '/GESTION_CONTACTOS.html'}
            ],
            'gastos': [
                {'nombre': 'Consultar Gastos', 'icono': 'fas fa-search', 'ruta': '/CONSULTA_GASTOS.html'},
                {'nombre': 'Conciliación', 'icono': 'fas fa-exchange-alt', 'ruta': '/CONCILIACION_GASTOS.html'}
            ],
            'facturas_recibidas': [
                {'nombre': 'Consultar', 'icono': 'fas fa-search', 'ruta': '/CONSULTA_FACTURAS_RECIBIDAS.html'},
                {'nombre': 'Nueva', 'icono': 'fas fa-plus', 'ruta': '/CONSULTA_FACTURAS_RECIBIDAS.html?nueva=1'},
                {'nombre': 'Subir Factura', 'icono': 'fas fa-file-upload', 'ruta': '/SUBIR_FACTURAS_MASIVO.html'},
                {'nombre': 'Proveedores', 'icono': 'fas fa-users', 'ruta': '/GESTION_PROVEEDORES.html'}
            ]  # Submenu de facturas de proveedores
        }
        
        # Módulos que ya están incluidos en submenus (no deben aparecer como items independientes)
        modulos_en_submenu = ['facturas', 'tickets', 'proformas', 'admin_empresas']
        
        menu = []
        for row in rows:
            logger.info(f"[MENU] Procesando módulo: {row[0]} - {row[1]}")
            item = {
                'codigo': row[0],
                'nombre': row[1],
                'ruta': row[2],
                'icono': row[3],
                'orden': row[4]
            }
            
            # Añadir permisos si no es superadmin
            if not es_superadmin and len(row) > 5:
                item['permisos'] = {
                    'ver': row[5],
                    'crear': row[6],
                    'editar': row[7],
                    'eliminar': row[8],
                    'anular': row[9],
                    'exportar': row[10]
                }
            else:
                # Superadmin tiene todos los permisos
                item['permisos'] = {
                    'ver': 1,
                    'crear': 1,
                    'editar': 1,
                    'eliminar': 1,
                    'anular': 1,
                    'exportar': 1
                }
            
            # Ajustar permisos según rol del usuario
            rol_usuario = session.get('rol', 'admin')
            if rol_usuario == 'consultor':
                # Consultor solo puede ver, no puede crear/editar/eliminar
                item['permisos']['crear'] = 0
                item['permisos']['editar'] = 0
                item['permisos']['eliminar'] = 0
                item['permisos']['anular'] = 0
                item['permisos']['exportar'] = 0
            
            # Agregar submódulos según el código del módulo
            codigo_modulo = item['codigo']
            if codigo_modulo in submenu_map:
                # Filtrar submenús según permisos del usuario
                submenu_completo = submenu_map[codigo_modulo]
                
                if es_admin_empresa:
                    # Admin ve todo, pero necesitamos agregar permisos a submódulos para el frontend
                    submenu_con_permisos = []
                    rol_usuario = session.get('rol', 'admin')
                    
                    for submenu_item in submenu_completo:
                        submenu_item_copia = submenu_item.copy()
                        
                        # Si el submódulo tiene código (tickets, facturas, proformas), agregar permisos
                        if 'codigo' in submenu_item:
                            if rol_usuario == 'consultor':
                                # Consultor solo puede ver
                                submenu_item_copia['permisos'] = {
                                    'ver': 1,
                                    'crear': 0,
                                    'editar': 0,
                                    'eliminar': 0,
                                    'anular': 0,
                                    'exportar': 0
                                }
                            else:
                                # Admin y editor tienen todos los permisos
                                submenu_item_copia['permisos'] = {
                                    'ver': 1,
                                    'crear': 1,
                                    'editar': 1,
                                    'eliminar': 1,
                                    'anular': 1,
                                    'exportar': 1
                                }
                        
                        submenu_con_permisos.append(submenu_item_copia)
                    
                    item['submenu'] = submenu_con_permisos
                else:
                    # Filtrar según permisos
                    submenu_filtrado = []
                    
                    for submenu_item in submenu_completo:
                        # Mapeo de nombres de submenús a códigos de módulo (para facturas_emitidas)
                        nombre_modulo_map = {
                            'Tickets': 'tickets',
                            'Facturas': 'facturas',
                            'Proformas': 'proformas',
                            'Exportar': 'exportar'
                        }
                        
                        nombre_sub = submenu_item.get('nombre', '')
                        modulo_codigo_sub = nombre_modulo_map.get(nombre_sub)
                        
                        # Si es un submódulo de facturas_emitidas (tiene mapeo)
                        if modulo_codigo_sub:
                            # Verificar permiso de ver para este submódulo
                            if permisos_usuario.get(modulo_codigo_sub, {}).get('puede_ver', 0) == 1:
                                # Crear copia del submódulo y agregar permisos
                                submenu_item_copia = submenu_item.copy()
                                perms = permisos_usuario.get(modulo_codigo_sub, {})
                                submenu_item_copia['permisos'] = {
                                    'ver': perms.get('puede_ver', 0),
                                    'crear': perms.get('puede_crear', 0),
                                    'editar': perms.get('puede_editar', 0),
                                    'eliminar': perms.get('puede_eliminar', 0),
                                    'anular': perms.get('puede_anular', 0),
                                    'exportar': perms.get('puede_exportar', 0)
                                }
                                
                                # Filtrar sub-submenús si existen
                                if 'submenu' in submenu_item:
                                    submenu_interno = submenu_item['submenu']
                                    submenu_interno_filtrado = []
                                    
                                    for subsub in submenu_interno:
                                        nombre_subsub = subsub.get('nombre', '')
                                        # Filtrar "Nuevo" si no tiene permiso de crear
                                        if nombre_subsub == 'Nuevo':
                                            if permisos_usuario.get(modulo_codigo_sub, {}).get('puede_crear', 0) == 1:
                                                submenu_interno_filtrado.append(subsub)
                                        else:
                                            # Consultar y otros siempre se muestran si tiene ver
                                            submenu_interno_filtrado.append(subsub)
                                    
                                    if submenu_interno_filtrado:
                                        submenu_item_copia['submenu'] = submenu_interno_filtrado
                                        submenu_filtrado.append(submenu_item_copia)
                                else:
                                    submenu_filtrado.append(submenu_item_copia)
                        else:
                            # Para módulos simples (productos, contactos, presupuestos)
                            # Usar el código del módulo padre
                            nombre_subsub = submenu_item.get('nombre', '')
                            
                            # Filtrar "Nuevo" si no tiene permiso de crear en el módulo padre
                            if nombre_subsub in ('Nuevo', 'Nueva'):
                                if permisos_usuario.get(codigo_modulo, {}).get('puede_crear', 0) == 1:
                                    submenu_filtrado.append(submenu_item)
                            else:
                                # Consultar, Franjas, etc. - siempre incluir si tiene ver
                                submenu_filtrado.append(submenu_item)
                    
                    item['submenu'] = submenu_filtrado
                
                logger.info(f"[MENU] Submódulos agregados a {codigo_modulo}: {len(item.get('submenu', []))} items")
            
            # Decidir si incluir el módulo en el menú
            incluir_modulo = False
            
            # FILTRO ESPECIAL: Eliminar Banco del menú
            if codigo_modulo == 'banco' or item['nombre'] == 'Banco':
                logger.info(f"[MENU] Item omitido (filtro banco): {item['nombre']}")
                incluir_modulo = False
            elif codigo_modulo in modulos_en_submenu:
                # Módulos que están dentro de otros (nunca se muestran independientemente)
                logger.info(f"[MENU] Item omitido (está en submenu): {item['nombre']}")
                incluir_modulo = False
            elif codigo_modulo == 'estadisticas' and not es_admin_empresa:
                # Estadísticas solo para administradores
                logger.info(f"[MENU] Item omitido (solo para admins): {item['nombre']}")
                incluir_modulo = False
            elif es_admin_empresa:
                # Admin ve todo
                incluir_modulo = True
            else:
                # Usuario normal - verificar permisos
                permisos = item.get('permisos', {})
                tiene_accion = (permisos.get('crear', 0) == 1 or 
                               permisos.get('editar', 0) == 1 or 
                               permisos.get('eliminar', 0) == 1 or 
                               permisos.get('anular', 0) == 1 or 
                               permisos.get('exportar', 0) == 1)
                
                # CAMBIO: Incluir módulos aunque solo tengan permiso de Ver
                # Los usuarios de solo consulta también deben ver el menú
                incluir_modulo = True
                logger.info(f"[MENU] Item incluido (tiene permiso de Ver): {item['nombre']}")
            
            if incluir_modulo:
                menu.append(item)
                logger.info(f"[MENU] ✓ Item agregado al menú: {item['nombre']}")
        
        logger.info(f"[MENU] Total items en menú: {len(menu)}")
        
        # Obtener rol del usuario
        rol_usuario = session.get('rol', 'consultor')
        logger.info(f"[MENU] Usuario: {session.get('username')} - Rol sesión: {rol_usuario} - Es Admin Empresa: {es_admin_empresa}")
        
        # Agregar opciones de administración si es admin de empresa o superadmin
        if es_admin_empresa or es_superadmin:
            submenu_admin = [
                {
                    'nombre': 'Gestión',
                    'icono': 'fas fa-users-cog',
                    'ruta': '/ADMIN_PERMISOS.html'
                },
                {
                    'nombre': 'Procesos',
                    'icono': 'fas fa-clock',
                    'ruta': '/ADMIN_BATCH.html'
                }
            ]
            
            menu.append({
                'codigo': 'admin',
                'nombre': 'Administración',
                'ruta': '#',
                'icono': 'fas fa-user-shield',
                'orden': 999,
                'permisos': {
                    'ver': 1,
                    'crear': 1,
                    'editar': 1,
                    'eliminar': 1,
                    'anular': 1,
                    'exportar': 1
                },
                'submenu': submenu_admin
            })
            logger.info("[MENU] Opciones de administración agregadas")
        
        conn.close()
        
        registrar_auditoria('menu_cargado')
        
        return jsonify(menu), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo menú: {e}", exc_info=True)
        return jsonify({'error': 'Error obteniendo menú'}), 500

@auth_bp.route('/app', methods=['GET'])
@login_required
def servir_aplicacion():
    """Sirve la aplicación principal (requiere autenticación)"""
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        
        # Detección básica de dispositivo móvil/tablet
        user_agent = request.headers.get('User-Agent', '').lower()
        is_mobile = 'mobile' in user_agent or 'android' in user_agent or 'iphone' in user_agent
        is_tablet = 'ipad' in user_agent or 'tablet' in user_agent
        
        # Definir ruta por defecto (Escritorio)
        app_path = os.path.join(BASE_DIR, 'frontend', '_app_private.html')
        
        # Si es móvil o tablet, intentar servir la versión móvil
        if is_mobile or is_tablet:
            mobile_path = os.path.join(BASE_DIR, 'frontend', 'mobile', 'index.html')
            if os.path.exists(mobile_path):
                app_path = mobile_path
                logger.info(f"Sirviendo versión móvil para UA: {user_agent[:30]}...")
            
        with open(app_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Si es móvil y NO tiene empresa, inyectar CSS para ocultar elementos
        empresa_codigo = session.get('empresa_codigo')
        if (is_mobile or is_tablet) and not empresa_codigo:
            logger.info(f"[MOBILE] Usuario sin empresa - inyectando CSS para ocultar elementos")
            # Inyectar CSS y JS antes del </head>
            hide_css = """
<style id="no-empresa-style">
    .bottom-nav { display: none !important; }
    .summary-card { display: none !important; }
    .quick-actions { display: none !important; }
    .section-title { display: none !important; }
    #ultimos-tickets-list { display: none !important; }
</style>
<script>
    window._sinEmpresa = true;
    document.addEventListener('DOMContentLoaded', function() {
        var dashboard = document.querySelector('.dashboard-mobile');
        if (dashboard) {
            dashboard.innerHTML = '<div style="text-align:center; padding: 60px 20px;"><i class="fas fa-building" style="font-size: 64px; color: #ccc; margin-bottom: 24px; display: block;"></i><h2 style="margin-bottom: 12px; color: #333;">Bienvenido</h2><p style="color:#666; margin-bottom: 24px; font-size: 16px;">No tienes ninguna empresa asociada.</p><p style="color:#888; margin-bottom: 32px; font-size: 14px;">Contacta con tu administrador para que te asigne una empresa.</p><button onclick="location.href=\\'/crear_empresa\\'" style="background: #e74c3c; color: white; padding: 14px 28px; border: none; border-radius: 8px; font-size: 16px; cursor: pointer;">+ Crear Empresa</button></div>';
        }
    });
</script>
"""
            content = content.replace('</head>', hide_css + '</head>')
        
        return Response(content, mimetype='text/html')
    except Exception as e:
        logger.error(f"Error sirviendo aplicación: {e}", exc_info=True)
        return jsonify({'error': 'Error sirviendo aplicación'}), 500

@auth_bp.route('/mobile/tickets', methods=['GET'])
@login_required
def servir_mobile_tickets():
    """Sirve la vista móvil de tickets"""
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        app_path = os.path.join(BASE_DIR, 'frontend', 'mobile', 'tickets.html')
        
        if not os.path.exists(app_path):
             return jsonify({'error': 'Vista no disponible'}), 404

        with open(app_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, mimetype='text/html')
    except Exception as e:
        logger.error(f"Error sirviendo tickets mobile: {e}", exc_info=True)
        return jsonify({'error': 'Error interno'}), 500

@auth_bp.route('/mobile/tickets/gestion', methods=['GET'])
@login_required
def servir_mobile_tickets_gestion():
    """Sirve la vista móvil de gestión de tickets (crear/editar)"""
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        app_path = os.path.join(BASE_DIR, 'frontend', 'mobile', 'gestion_tickets.html')
        
        if not os.path.exists(app_path):
             return jsonify({'error': 'Vista no disponible'}), 404

        with open(app_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, mimetype='text/html')
    except Exception as e:
        logger.error(f"Error sirviendo gestion tickets mobile: {e}", exc_info=True)
        return jsonify({'error': 'Error interno'}), 500

@auth_bp.route('/mobile/facturas', methods=['GET'])
@login_required
def servir_mobile_facturas():
    """Sirve la vista móvil de facturas"""
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        app_path = os.path.join(BASE_DIR, 'frontend', 'mobile', 'facturas.html')
        
        if not os.path.exists(app_path):
             return jsonify({'error': 'Vista no disponible'}), 404

        with open(app_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, mimetype='text/html')
    except Exception as e:
        logger.error(f"Error sirviendo facturas mobile: {e}", exc_info=True)
        return jsonify({'error': 'Error interno'}), 500

@auth_bp.route('/mobile/facturas/gestion', methods=['GET'])
@login_required
def servir_mobile_facturas_gestion():
    """Sirve la vista móvil de gestión de facturas"""
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        app_path = os.path.join(BASE_DIR, 'frontend', 'mobile', 'gestion_facturas.html')
        
        if not os.path.exists(app_path):
             return jsonify({'error': 'Vista no disponible'}), 404

        with open(app_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, mimetype='text/html')
    except Exception as e:
        logger.error(f"Error sirviendo gestion facturas mobile: {e}", exc_info=True)
        return jsonify({'error': 'Error interno'}), 500

@auth_bp.route('/mobile/gastos', methods=['GET'])
@login_required
def servir_mobile_gastos():
    """Sirve la vista móvil de gastos"""
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        app_path = os.path.join(BASE_DIR, 'frontend', 'mobile', 'gastos.html')
        
        if not os.path.exists(app_path):
             return jsonify({'error': 'Vista no disponible'}), 404
        with open(app_path, 'r', encoding='utf-8') as f: content = f.read()
        return Response(content, mimetype='text/html')
    except Exception as e:
        logger.error(f"Error sirviendo gastos mobile: {e}", exc_info=True)
        return jsonify({'error': 'Error interno'}), 500

@auth_bp.route('/mobile/contactos', methods=['GET'])
@login_required
def servir_mobile_contactos():
    """Sirve la vista móvil de contactos"""
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        app_path = os.path.join(BASE_DIR, 'frontend', 'mobile', 'contactos.html')
        if not os.path.exists(app_path): return jsonify({'error': 'Vista no disponible'}), 404
        with open(app_path, 'r', encoding='utf-8') as f: content = f.read()
        return Response(content, mimetype='text/html')
    except Exception as e:
        logger.error(f"Error sirviendo contactos mobile: {e}", exc_info=True)
        return jsonify({'error': 'Error interno'}), 500

@auth_bp.route('/mobile/contactos/gestion', methods=['GET'])
@login_required
def servir_mobile_contactos_gestion():
    """Sirve la vista móvil de gestión de contactos"""
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        app_path = os.path.join(BASE_DIR, 'frontend', 'mobile', 'gestion_contactos.html')
        if not os.path.exists(app_path): return jsonify({'error': 'Vista no disponible'}), 404
        with open(app_path, 'r', encoding='utf-8') as f: content = f.read()
        return Response(content, mimetype='text/html')
    except Exception as e:
        logger.error(f"Error sirviendo gestion contactos mobile: {e}", exc_info=True)
        return jsonify({'error': 'Error interno'}), 500

@auth_bp.route('/mobile/productos', methods=['GET'])
@login_required
def servir_mobile_productos():
    """Sirve la vista móvil de productos"""
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        app_path = os.path.join(BASE_DIR, 'frontend', 'mobile', 'productos.html')
        if not os.path.exists(app_path): return jsonify({'error': 'Vista no disponible'}), 404
        with open(app_path, 'r', encoding='utf-8') as f: content = f.read()
        return Response(content, mimetype='text/html')
    except Exception as e:
        logger.error(f"Error sirviendo productos mobile: {e}", exc_info=True)
        return jsonify({'error': 'Error interno'}), 500

@auth_bp.route('/mobile/productos/gestion', methods=['GET'])
@login_required
def servir_mobile_productos_gestion():
    """Sirve la vista móvil de gestión de productos"""
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        app_path = os.path.join(BASE_DIR, 'frontend', 'mobile', 'gestion_productos.html')
        if not os.path.exists(app_path): return jsonify({'error': 'Vista no disponible'}), 404
        with open(app_path, 'r', encoding='utf-8') as f: content = f.read()
        return Response(content, mimetype='text/html')
    except Exception as e:
        logger.error(f"Error sirviendo gestion productos mobile: {e}", exc_info=True)
        return jsonify({'error': 'Error interno'}), 500

@auth_bp.route('/mobile/presupuestos', methods=['GET'])
@login_required
def servir_mobile_presupuestos():
    """Sirve la vista móvil de presupuestos"""
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        app_path = os.path.join(BASE_DIR, 'frontend', 'mobile', 'presupuestos.html')
        if not os.path.exists(app_path): return jsonify({'error': 'Vista no disponible'}), 404
        with open(app_path, 'r', encoding='utf-8') as f: content = f.read()
        return Response(content, mimetype='text/html')
    except Exception as e:
        logger.error(f"Error sirviendo presupuestos mobile: {e}", exc_info=True)
        return jsonify({'error': 'Error interno'}), 500

@auth_bp.route('/mobile/presupuestos/gestion', methods=['GET'])
@login_required
def servir_mobile_presupuestos_gestion():
    """Sirve la vista móvil de gestión de presupuestos"""
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        app_path = os.path.join(BASE_DIR, 'frontend', 'mobile', 'gestion_presupuestos.html')
        if not os.path.exists(app_path): return jsonify({'error': 'Vista no disponible'}), 404
        with open(app_path, 'r', encoding='utf-8') as f: content = f.read()
        return Response(content, mimetype='text/html')
    except Exception as e:
        logger.error(f"Error sirviendo gestion presupuestos mobile: {e}", exc_info=True)
        return jsonify({'error': 'Error interno'}), 500

@auth_bp.route('/mobile/proformas', methods=['GET'])
@login_required
def servir_mobile_proformas():
    """Sirve la vista móvil de proformas"""
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        app_path = os.path.join(BASE_DIR, 'frontend', 'mobile', 'proformas.html')
        if not os.path.exists(app_path): return jsonify({'error': 'Vista no disponible'}), 404
        with open(app_path, 'r', encoding='utf-8') as f: content = f.read()
        return Response(content, mimetype='text/html')
    except Exception as e:
        logger.error(f"Error sirviendo proformas mobile: {e}", exc_info=True)
        return jsonify({'error': 'Error interno'}), 500

@auth_bp.route('/mobile/proformas/gestion', methods=['GET'])
@login_required
def servir_mobile_proformas_gestion():
    """Sirve la vista móvil de gestión de proformas"""
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        app_path = os.path.join(BASE_DIR, 'frontend', 'mobile', 'gestion_proformas.html')
        if not os.path.exists(app_path): return jsonify({'error': 'Vista no disponible'}), 404
        with open(app_path, 'r', encoding='utf-8') as f: content = f.read()
        return Response(content, mimetype='text/html')
    except Exception as e:
        logger.error(f"Error sirviendo gestion proformas mobile: {e}", exc_info=True)
        return jsonify({'error': 'Error interno'}), 500

@auth_bp.route('/branding-preview/<empresa_codigo>', methods=['GET'])
def obtener_branding_preview(empresa_codigo):
    """
    Retorna configuración visual de una empresa por su código (sin autenticación, solo para preview en login)
    """
    try:
        with get_database_pool(DB_USUARIOS_PATH).get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    logo_header, logo_factura,
                    color_primario, color_secundario, color_success, color_warning, 
                    color_danger, color_info, color_button, color_button_hover,
                    color_button_text, color_app_bg,
                    color_header_bg, color_header_text, color_grid_header, color_grid_hover,
                    color_input_bg, color_input_text, color_input_border,
                    color_submenu_bg, color_submenu_text, color_submenu_hover,
                    color_icon, color_grid_bg, color_grid_text,
                    color_select_bg, color_select_text, color_select_border,
                    color_disabled_bg, color_disabled_text,
                    nombre
                FROM empresas
                WHERE codigo = ?
            ''', (empresa_codigo,))
            
            empresa = cursor.fetchone()
        
        if not empresa:
            return jsonify({'error': 'Empresa no encontrada'}), 404
        
        return jsonify({
            'logo_header': empresa[0],
            'logo_factura': empresa[1],
            'colores': {
                'primario': empresa[2],
                'secundario': empresa[3],
                'success': empresa[4],
                'warning': empresa[5],
                'danger': empresa[6],
                'info': empresa[7],
                'button': empresa[8],
                'button_hover': empresa[9],
                'button_text': empresa[10],
                'app_bg': empresa[11],
                'header_bg': empresa[12],
                'header_text': empresa[13],
                'grid_header': empresa[14],
                'grid_hover': empresa[15],
                'input_bg': empresa[16],
                'input_text': empresa[17],
                'input_border': empresa[18],
                'submenu_bg': empresa[19],
                'submenu_text': empresa[20],
                'submenu_hover': empresa[21],
                'icon': empresa[22],
                'grid_bg': empresa[23],
                'grid_text': empresa[24],
                'select_bg': empresa[25],
                'select_text': empresa[26],
                'select_border': empresa[27],
                'disabled_bg': empresa[28],
                'disabled_text': empresa[29]
            },
            'nombre': empresa[30]
        }), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo branding preview: {e}", exc_info=True)
        return jsonify({'error': 'Error obteniendo branding'}), 500

@auth_bp.route('/branding', methods=['GET'])
@login_required
def obtener_branding():
    """
    Retorna SOLO el nombre de la plantilla y datos de empresa.
    El frontend carga el JSON directamente.
    """
    try:
        empresa_id = session.get('empresa_id')
        user_id = session.get('user_id')
        
        with get_database_pool(DB_USUARIOS_PATH).get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Obtener datos de empresa (logos, datos) y plantilla del usuario
            cursor.execute('''
                SELECT e.logo_header, e.logo_factura, ue.plantilla, e.plantilla_personalizada,
                       e.nombre, e.cif, e.direccion, e.telefono, e.email, e.web
                FROM empresas e
                JOIN usuario_empresa ue ON ue.empresa_id = e.id
                WHERE e.id = ? AND ue.usuario_id = ?
            ''', (empresa_id, user_id))
            
            empresa = cursor.fetchone()
        
        if not empresa:
            # Si no tiene empresa, devolver configuración por defecto (Minimal)
            logger.info("[BRANDING] Usuario sin empresa - devolviendo tema minimal por defecto")
            return jsonify({
                'empresa_id': None,
                'logo_header': '/public/assets/logo.svg',
                'logo_factura': '/public/assets/logo.svg',
                'plantilla': 'minimal',
                'datos': {
                    'nombre': 'Mi Empresa',
                    'cif': '',
                    'direccion': '',
                    'telefono': '',
                    'email': '',
                    'web': ''
                }
            }), 200
        
        # Usar directamente el campo plantilla (minimal, dark, eink)
        plantilla_base = empresa['plantilla'] or 'dark'  # default dark
        plantilla_nombre = empresa['plantilla_personalizada'] or plantilla_base.capitalize()
        
        logger.info(f"[BRANDING] Plantilla: {plantilla_base} ('{plantilla_nombre}')")
        
        return jsonify({
            'empresa_id': empresa_id,  # ← Agregar empresa_id
            'logo_header': empresa['logo_header'] or '/public/assets/logo.svg',
            'logo_factura': empresa['logo_factura'] or '/public/assets/logo.svg',
            'plantilla': plantilla_base,  # ← Solo nombre de plantilla
            'datos': {
                'nombre': empresa['nombre'],
                'cif': empresa['cif'],
                'direccion': empresa['direccion'],
                'telefono': empresa['telefono'],
                'email': empresa['email'],
                'web': empresa['web']
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo branding: {e}", exc_info=True)
        return jsonify({'error': 'Error obteniendo branding'}), 500

@auth_bp.route('/emisor', methods=['GET'])
@login_required
def obtener_datos_emisor():
    """
    Retorna los datos completos del emisor desde el JSON de la empresa.
    Usado para impresión de facturas, tickets, etc.
    """
    try:
        from utils_emisor import cargar_datos_emisor
        emisor = cargar_datos_emisor()
        
        logger.info(f"[EMISOR] Datos cargados: {emisor.get('nombre')} - {emisor.get('nif')}")
        
        return jsonify({
            'success': True,
            'emisor': emisor
        }), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo datos del emisor: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Error obteniendo datos del emisor'
        }), 500

@auth_bp.route('/cambiar-password', methods=['POST'])
@auth_bp.route('/change-password', methods=['POST'])
@login_required
def cambiar_password():
    """
    Permite al usuario cambiar su contraseña
    """
    try:
        data = request.json
        # Aceptar ambos formatos
        password_actual = data.get('password_actual') or data.get('current_password')
        password_nueva = data.get('password_nueva') or data.get('new_password')
        
        if not password_actual or not password_nueva:
            return jsonify({'error': 'Contraseñas requeridas'}), 400
        
        user_id = session.get('user_id')
        
        from auth_middleware import verificar_password, hash_password
        
        # Verificar password actual
        with get_database_pool(DB_USUARIOS_PATH).get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT password_hash FROM usuarios WHERE id = ?', (user_id,))
            result = cursor.fetchone()
            
            if not result:
                return jsonify({'error': 'Usuario no encontrado'}), 404
                
            actual_hash = result[0]
            
            if not verificar_password(password_actual, actual_hash):
                return jsonify({'error': 'Contraseña actual incorrecta'}), 401
            
            # Actualizar password
            nuevo_hash = hash_password(password_nueva)
            cursor.execute('UPDATE usuarios SET password_hash = ? WHERE id = ?', (nuevo_hash, user_id))
            conn.commit()
        
        registrar_auditoria('cambio_password', descripcion='Usuario cambió su contraseña')
        
        logger.info(f"Usuario {session.get('username')} cambió su contraseña")
        
        return jsonify({'success': True, 'mensaje': 'Contraseña actualizada'}), 200
        
    except Exception as e:
        logger.error(f"Error cambiando contraseña: {e}", exc_info=True)
        return jsonify({'error': 'Error cambiando contraseña'}), 500


@auth_bp.route('/upload-avatar', methods=['POST'])
@login_required
def upload_avatar():
    """Subir avatar de usuario"""
    try:
        user_id = session.get('user_id')
        
        if 'avatar' not in request.files:
            return jsonify({'error': 'No se envió ningún archivo'}), 400
        
        file = request.files['avatar']
        
        if file.filename == '':
            return jsonify({'error': 'No se seleccionó ningún archivo'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Tipo de archivo no permitido. Use: PNG, JPG, JPEG, GIF, WEBP'}), 400
        
        # Generar nombre único para el archivo
        extension = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{user_id}_{uuid.uuid4().hex[:8]}.{extension}"
        filepath = os.path.join(AVATAR_FOLDER, filename)
        
        # Guardar archivo
        file.save(filepath)
        
        # Actualizar base de datos
        avatar_url = f"/static/avatars/{filename}"
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        cursor.execute('UPDATE usuarios SET avatar = ? WHERE id = ?', (avatar_url, user_id))
        conn.commit()
        conn.close()
        
        logger.info(f"Usuario {session.get('username')} actualizó su avatar")
        
        return jsonify({'success': True, 'avatar_url': avatar_url}), 200
        
    except Exception as e:
        logger.error(f"Error subiendo avatar: {e}", exc_info=True)
        return jsonify({'error': 'Error al subir avatar'}), 500

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """
    Solicitar recuperación de contraseña - envía email con token
    """
    try:
        data = request.get_json()
        username_or_email = data.get('username', '').strip()
        
        if not username_or_email:
            return jsonify({'error': 'Usuario o email requerido'}), 400
        
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Buscar usuario por username o email
        cursor.execute('''
            SELECT id, username, nombre_completo, email 
            FROM usuarios 
            WHERE username = ? OR email = ?
        ''', (username_or_email, username_or_email))
        
        usuario = cursor.fetchone()
        
        if not usuario:
            # Por seguridad, no revelar si el usuario existe
            logger.warning(f"Intento de recuperación para usuario inexistente: {username_or_email}")
            return jsonify({'success': True, 'message': 'Si el usuario existe, recibirás un email'}), 200
        
        if not usuario['email']:
            logger.warning(f"Usuario {usuario['username']} no tiene email configurado")
            return jsonify({'error': 'Usuario sin email configurado. Contacta al administrador'}), 400
        
        # Generar token único
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=1)
        
        # Guardar token en BD
        cursor.execute('''
            INSERT INTO password_reset_tokens (usuario_id, token, email, expires_at)
            VALUES (?, ?, ?, ?)
        ''', (usuario['id'], token, usuario['email'], expires_at))
        
        conn.commit()
        conn.close()
        
        # Obtener URL base - priorizar variable de entorno, luego headers de proxy
        base_url = os.environ.get('APP_URL')
        if not base_url:
            # Usar X-Forwarded-Host si está detrás de proxy
            forwarded_host = request.headers.get('X-Forwarded-Host')
            forwarded_proto = request.headers.get('X-Forwarded-Proto', 'https')
            if forwarded_host:
                base_url = f"{forwarded_proto}://{forwarded_host}"
            else:
                base_url = request.host_url.rstrip('/')
        
        # Enviar email
        success, message = enviar_email_recuperacion_password(
            usuario['email'],
            usuario['nombre_completo'] or usuario['username'],
            token,
            base_url
        )
        
        if success:
            logger.info(f"Email de recuperación enviado a {usuario['email']}")
            return jsonify({
                'success': True, 
                'message': 'Email de recuperación enviado. Revisa tu bandeja de entrada.'
            }), 200
        else:
            logger.error(f"Error enviando email de recuperación: {message}")
            return jsonify({'error': 'Error enviando email. Intenta más tarde'}), 500
        
    except Exception as e:
        logger.error(f"Error en forgot_password: {e}", exc_info=True)
        return jsonify({'error': 'Error procesando solicitud'}), 500

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """
    Restablecer contraseña usando token
    """
    try:
        data = request.get_json()
        token = data.get('token', '').strip()
        new_password = data.get('password', '').strip()
        
        if not token or not new_password:
            return jsonify({'error': 'Token y contraseña requeridos'}), 400
        
        if len(new_password) < 6:
            return jsonify({'error': 'La contraseña debe tener al menos 6 caracteres'}), 400
        
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Buscar token válido
        cursor.execute('''
            SELECT t.id, t.usuario_id, t.used, t.expires_at, u.username
            FROM password_reset_tokens t
            JOIN usuarios u ON t.usuario_id = u.id
            WHERE t.token = ?
        ''', (token,))
        
        token_data = cursor.fetchone()
        
        if not token_data:
            conn.close()
            return jsonify({'error': 'Token inválido'}), 400
        
        # Verificar si ya fue usado
        if token_data['used']:
            conn.close()
            return jsonify({'error': 'Este enlace ya fue utilizado'}), 400
        
        # Verificar si expiró
        expires_at = datetime.fromisoformat(token_data['expires_at'])
        if datetime.now() > expires_at:
            conn.close()
            return jsonify({'error': 'Este enlace ha expirado. Solicita uno nuevo'}), 400
        
        # Actualizar contraseña
        hashed_password = generate_password_hash(new_password)
        cursor.execute('UPDATE usuarios SET password_hash = ? WHERE id = ?', 
                      (hashed_password, token_data['usuario_id']))
        
        # Marcar token como usado
        cursor.execute('UPDATE password_reset_tokens SET used = 1 WHERE id = ?', 
                      (token_data['id'],))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Contraseña restablecida para usuario {token_data['username']}")
        
        return jsonify({
            'success': True,
            'message': 'Contraseña actualizada correctamente. Ya puedes iniciar sesión.'
        }), 200
        
    except Exception as e:
        logger.error(f"Error en reset_password: {e}", exc_info=True)
        return jsonify({'error': 'Error procesando solicitud'}), 500

@auth_bp.route('/validate-reset-token', methods=['GET'])
def validate_reset_token():
    """
    Validar si un token de recuperación es válido
    """
    try:
        token = request.args.get('token', '').strip()
        
        if not token:
            return jsonify({'valid': False, 'error': 'Token requerido'}), 400
        
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT used, expires_at, u.username, u.nombre_completo
            FROM password_reset_tokens t
            JOIN usuarios u ON t.usuario_id = u.id
            WHERE t.token = ?
        ''', (token,))
        
        token_data = cursor.fetchone()
        conn.close()
        
        if not token_data:
            return jsonify({'valid': False, 'error': 'Token inválido'}), 200
        
        if token_data['used']:
            return jsonify({'valid': False, 'error': 'Este enlace ya fue utilizado'}), 200
        
        expires_at = datetime.fromisoformat(token_data['expires_at'])
        if datetime.now() > expires_at:
            return jsonify({'valid': False, 'error': 'Este enlace ha expirado'}), 200
        
        return jsonify({
            'valid': True,
            'username': token_data['username'],
            'nombre': token_data['nombre_completo']
        }), 200
        
    except Exception as e:
        logger.error(f"Error validando token: {e}", exc_info=True)
        return jsonify({'valid': False, 'error': 'Error validando token'}), 500

@auth_bp.route('/permisos', methods=['GET'])
@login_required
def obtener_permisos():
    """
    Retorna los permisos detallados del usuario logueado para control de UI
    """
    try:
        user_id = session.get('user_id')
        empresa_id = session.get('empresa_id')
        es_superadmin = session.get('es_superadmin')
        es_admin_empresa = session.get('es_admin_empresa', False)
        
        # Si es superadmin o admin de empresa, tiene todos los permisos
        if es_superadmin or es_admin_empresa:
            return jsonify({
                '_todos': True,
                '_es_admin': True
            }), 200
        
        if not empresa_id:
            return jsonify({}), 200
        
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                modulo_codigo,
                puede_ver,
                puede_crear,
                puede_editar,
                puede_eliminar,
                puede_anular,
                puede_exportar
            FROM permisos_usuario_modulo
            WHERE usuario_id = ? AND empresa_id = ?
        ''', (user_id, empresa_id))
        
        permisos = {}
        for row in cursor.fetchall():
            permisos[row[0]] = {
                'puede_ver': row[1],
                'puede_crear': row[2],
                'puede_editar': row[3],
                'puede_eliminar': row[4],
                'puede_anular': row[5],
                'puede_exportar': row[6]
            }
        
        conn.close()
        
        logger.info(f"[PERMISOS] Usuario {user_id} tiene permisos en {len(permisos)} módulos")
        return jsonify(permisos), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo permisos: {e}", exc_info=True)
        return jsonify({'error': 'Error obteniendo permisos'}), 500

@auth_bp.route('/mobile/facturas_recibidas', methods=['GET'])
@login_required
def servir_mobile_facturas_recibidas():
    """Sirve la vista móvil de facturas recibidas"""
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        app_path = os.path.join(BASE_DIR, 'frontend', 'mobile', 'facturas_recibidas.html')
        if not os.path.exists(app_path): return jsonify({'error': 'Vista no disponible'}), 404
        with open(app_path, 'r', encoding='utf-8') as f: content = f.read()
        return Response(content, mimetype='text/html')
    except Exception as e:
        logger.error(f"Error sirviendo facturas recibidas mobile: {e}", exc_info=True)
        return jsonify({'error': 'Error interno'}), 500

@auth_bp.route('/mobile/facturas_recibidas/gestion', methods=['GET'])
@login_required
def servir_mobile_facturas_recibidas_gestion():
    """Sirve la vista móvil de gestión de facturas recibidas"""
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        app_path = os.path.join(BASE_DIR, 'frontend', 'mobile', 'gestion_facturas_recibidas.html')
        if not os.path.exists(app_path): return jsonify({'error': 'Vista no disponible'}), 404
        with open(app_path, 'r', encoding='utf-8') as f: content = f.read()
        return Response(content, mimetype='text/html')
    except Exception as e:
        logger.error(f"Error sirviendo gestion facturas recibidas mobile: {e}", exc_info=True)
        return jsonify({'error': 'Error interno'}), 500

# ============================================================================
# ENDPOINTS 2FA (Doble Factor de Autenticación)
# ============================================================================

def _ensure_2fa_columns():
    """Asegura que existan las columnas de 2FA en la tabla usuarios"""
    try:
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        # Verificar si existen las columnas
        cursor.execute("PRAGMA table_info(usuarios)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'totp_secret' not in columns:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN totp_secret TEXT")
            logger.info("Columna totp_secret añadida a usuarios")
        
        if 'totp_enabled' not in columns:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN totp_enabled INTEGER DEFAULT 0")
            logger.info("Columna totp_enabled añadida a usuarios")
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error asegurando columnas 2FA: {e}")

@auth_bp.route('/2fa/status', methods=['GET'])
@login_required
def get_2fa_status():
    """Obtiene el estado de 2FA del usuario actual"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'No autenticado'}), 401
        
        _ensure_2fa_columns()
        
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT totp_enabled FROM usuarios WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        enabled = bool(result[0]) if result and result[0] else False
        
        return jsonify({
            'enabled': enabled
        }), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo estado 2FA: {e}", exc_info=True)
        return jsonify({'error': 'Error obteniendo estado 2FA'}), 500

@auth_bp.route('/2fa/setup', methods=['POST'])
@login_required
def setup_2fa():
    """
    Inicia la configuración de 2FA.
    Genera un secreto TOTP y devuelve el código QR para escanear.
    """
    try:
        user_id = session.get('user_id')
        username = session.get('username')
        
        if not user_id:
            return jsonify({'error': 'No autenticado'}), 401
        
        _ensure_2fa_columns()
        
        # Generar secreto TOTP
        secret = pyotp.random_base32()
        
        # Guardar secreto temporalmente (no activado aún)
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE usuarios SET totp_secret = ? WHERE id = ?",
            (secret, user_id)
        )
        conn.commit()
        conn.close()
        
        # Crear URI para el QR
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(name=username, issuer_name="Aleph70")
        
        # Generar imagen QR
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convertir a base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        logger.info(f"2FA setup iniciado para usuario {username}")
        
        return jsonify({
            'success': True,
            'qr_code': f"data:image/png;base64,{qr_base64}",
            'secret': secret,  # Para entrada manual si no pueden escanear QR
            'message': 'Escanea el código QR con tu app de autenticación'
        }), 200
        
    except Exception as e:
        logger.error(f"Error en setup 2FA: {e}", exc_info=True)
        return jsonify({'error': 'Error configurando 2FA'}), 500

@auth_bp.route('/2fa/verify', methods=['POST'])
@login_required
def verify_2fa():
    """
    Verifica el código TOTP y activa 2FA si es correcto.
    Se usa durante la configuración inicial.
    """
    try:
        user_id = session.get('user_id')
        username = session.get('username')
        data = request.json or {}
        code = data.get('code', '').strip()
        
        if not user_id:
            return jsonify({'error': 'No autenticado'}), 401
        
        if not code or len(code) != 6:
            return jsonify({'error': 'Código inválido. Debe ser de 6 dígitos'}), 400
        
        # Obtener secreto del usuario
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT totp_secret FROM usuarios WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result or not result[0]:
            conn.close()
            return jsonify({'error': 'No hay configuración 2FA pendiente'}), 400
        
        secret = result[0]
        
        # Verificar código
        totp = pyotp.TOTP(secret)
        if not totp.verify(code, valid_window=1):  # Permite 30 segundos de margen
            conn.close()
            logger.warning(f"Código 2FA incorrecto para usuario {username}")
            return jsonify({'error': 'Código incorrecto. Inténtalo de nuevo'}), 400
        
        # Activar 2FA
        cursor.execute(
            "UPDATE usuarios SET totp_enabled = 1 WHERE id = ?",
            (user_id,)
        )
        conn.commit()
        conn.close()
        
        registrar_auditoria('2fa_activado', descripcion=f'2FA activado para {username}')
        logger.info(f"2FA activado exitosamente para usuario {username}")
        
        return jsonify({
            'success': True,
            'message': 'Autenticación de doble factor activada correctamente'
        }), 200
        
    except Exception as e:
        logger.error(f"Error verificando 2FA: {e}", exc_info=True)
        return jsonify({'error': 'Error verificando código'}), 500

@auth_bp.route('/2fa/disable', methods=['POST'])
@login_required
def disable_2fa():
    """
    Desactiva 2FA para el usuario actual.
    Requiere verificar la contraseña actual.
    """
    try:
        user_id = session.get('user_id')
        username = session.get('username')
        data = request.json or {}
        password = data.get('password', '')
        
        if not user_id:
            return jsonify({'error': 'No autenticado'}), 401
        
        if not password:
            return jsonify({'error': 'Se requiere la contraseña actual'}), 400
        
        # Verificar contraseña
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM usuarios WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        # Usar verificar_password que soporta SHA256 legacy y PBKDF2
        from auth_middleware import verificar_password
        if not verificar_password(password, result[0], user_id):
            conn.close()
            logger.warning(f"Intento de desactivar 2FA con contraseña incorrecta: {username}")
            return jsonify({'error': 'Contraseña incorrecta'}), 401
        
        # Desactivar 2FA
        cursor.execute(
            "UPDATE usuarios SET totp_enabled = 0, totp_secret = NULL WHERE id = ?",
            (user_id,)
        )
        conn.commit()
        conn.close()
        
        registrar_auditoria('2fa_desactivado', descripcion=f'2FA desactivado para {username}')
        logger.info(f"2FA desactivado para usuario {username}")
        
        return jsonify({
            'success': True,
            'message': 'Autenticación de doble factor desactivada'
        }), 200
        
    except Exception as e:
        logger.error(f"Error desactivando 2FA: {e}", exc_info=True)
        return jsonify({'error': 'Error desactivando 2FA'}), 500

@auth_bp.route('/2fa/validate', methods=['POST'])
def validate_2fa_login():
    """
    Valida el código 2FA durante el proceso de login.
    Se llama después de verificar usuario/contraseña si 2FA está activo.
    Nota: No depende de pending_2fa_session para compatibilidad con Cloudflare.
    """
    try:
        data = request.json or {}
        user_id = data.get('user_id')
        code = data.get('code', '').strip()
        logger.info(f"2FA validate request: user_id={user_id}, code_len={len(code) if code else 0}")
        
        if not user_id:
            return jsonify({'error': 'Sesión inválida'}), 400
        
        if not code or len(code) != 6:
            return jsonify({'error': 'Código inválido'}), 400
        
        # Obtener datos completos del usuario para establecer sesión
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, username, nombre_completo, totp_secret, es_superadmin, rol
            FROM usuarios WHERE id = ? AND activo = 1 AND totp_enabled = 1
        ''', (user_id,))
        usuario = cursor.fetchone()
        
        if not usuario or not usuario['totp_secret']:
            conn.close()
            return jsonify({'error': 'Usuario no válido o 2FA no configurado'}), 400
        
        # Verificar código TOTP (ventana ampliada para tolerancia de tiempo)
        totp = pyotp.TOTP(usuario['totp_secret'])
        if not totp.verify(code, valid_window=2):
            logger.warning(f"Código 2FA login incorrecto para {usuario['username']}")
            conn.close()
            return jsonify({'error': 'Código incorrecto'}), 401
        
        # Código correcto - obtener empresa del usuario para establecer sesión
        cursor.execute('''
            SELECT ue.empresa_id, ue.es_admin_empresa, e.codigo, e.nombre, e.db_path, e.logo_header
            FROM usuario_empresa ue
            JOIN empresas e ON ue.empresa_id = e.id
            WHERE ue.usuario_id = ?
            ORDER BY ue.es_admin_empresa DESC
            LIMIT 1
        ''', (user_id,))
        empresa_row = cursor.fetchone()
        conn.close()
        
        # Preparar datos de sesión
        empresa_id = empresa_row['empresa_id'] if empresa_row else None
        empresa_codigo = empresa_row['codigo'] if empresa_row else None
        empresa_nombre = empresa_row['nombre'] if empresa_row else 'Sin empresa'
        db_path = empresa_row['db_path'] if empresa_row else None
        logo_header = (empresa_row['logo_header'] or '/public/assets/logo.svg') if empresa_row else '/public/assets/logo.svg'
        es_admin_empresa = empresa_row['es_admin_empresa'] if empresa_row else 0
        
        # Establecer sesión completa
        session.permanent = True
        session['user_id'] = usuario['id']
        session['username'] = usuario['username']
        session['nombre_completo'] = usuario['nombre_completo']
        session['empresa_id'] = empresa_id
        session['empresa_codigo'] = empresa_codigo
        session['empresa_nombre'] = empresa_nombre
        session['empresa_db'] = db_path
        session['empresa_logo'] = logo_header
        session['rol'] = usuario['rol']
        session['es_admin_empresa'] = es_admin_empresa
        session['es_superadmin'] = usuario['es_superadmin']
        session.modified = True
        
        logger.info(f"Login 2FA completado para {usuario['username']}")
        registrar_auditoria('login_2fa', descripcion=f'Login con 2FA exitoso')
        
        return jsonify({
            'success': True,
            'usuario': usuario['nombre_completo'],
            'empresa': empresa_nombre,
            'rol': usuario['rol'],
            'es_admin': es_admin_empresa or usuario['es_superadmin'],
            'message': 'Autenticación completada'
        }), 200
        
    except Exception as e:
        logger.error(f"Error validando 2FA login: {e}", exc_info=True)
        return jsonify({'error': 'Error validando código'}), 500

# ============================================================================
# REGISTRO PÚBLICO (sin autenticación)
# ============================================================================

@auth_bp.route('/registro', methods=['POST'])
def registro_publico():
    """
    Registro público: crea usuario + empresa + activa trial de 15 días.
    No requiere autenticación.
    """
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Datos incompletos'}), 400
        
        # Datos del usuario
        nombre_completo = data.get('nombre_completo', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        # Datos de la empresa
        nombre_empresa = data.get('nombre_empresa', '').strip()
        nif = data.get('nif', '').strip().upper()
        
        # Validaciones
        if not nombre_completo or not email or not password:
            return jsonify({'error': 'Nombre, email y contraseña son obligatorios'}), 400
        
        if not nombre_empresa:
            return jsonify({'error': 'El nombre de la empresa es obligatorio'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'La contraseña debe tener al menos 6 caracteres'}), 400
        
        # Generar username desde email
        username = email.split('@')[0].lower().replace('.', '_')[:20]
        
        # Generar código de empresa (5 letras del nombre)
        codigo_empresa = ''.join(c for c in nombre_empresa.upper() if c.isalnum())[:5]
        if len(codigo_empresa) < 3:
            codigo_empresa = codigo_empresa + 'EMP'
        
        with get_database_pool(DB_USUARIOS_PATH).get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Verificar si el email ya existe
            cursor.execute("SELECT id FROM usuarios WHERE email = ?", (email,))
            if cursor.fetchone():
                return jsonify({'error': 'Ya existe una cuenta con este email'}), 400
            
            # Verificar si el username ya existe
            cursor.execute("SELECT id FROM usuarios WHERE username = ?", (username,))
            if cursor.fetchone():
                # Añadir número aleatorio
                username = username + str(secrets.randbelow(1000))
            
            # Verificar si el código de empresa ya existe
            cursor.execute("SELECT id FROM empresas WHERE codigo = ?", (codigo_empresa,))
            if cursor.fetchone():
                codigo_empresa = codigo_empresa + str(secrets.randbelow(100))
            
            # 1. Crear usuario
            password_hash = generate_password_hash(password)
            cursor.execute('''
                INSERT INTO usuarios (username, password_hash, nombre_completo, email, rol, activo, es_superadmin)
                VALUES (?, ?, ?, ?, 'admin', 1, 0)
            ''', (username, password_hash, nombre_completo, email))
            user_id = cursor.lastrowid
            
            # 2. Crear empresa (copiar desde plantilla.db)
            import shutil
            plantilla_path = '/var/www/html/db/plantilla.db'
            empresa_db_dir = f'/var/www/html/db/{codigo_empresa}'
            empresa_db_path = f'{empresa_db_dir}/{codigo_empresa}.db'
            
            os.makedirs(empresa_db_dir, exist_ok=True)
            if os.path.exists(plantilla_path):
                shutil.copy2(plantilla_path, empresa_db_path)
                os.chmod(empresa_db_path, 0o664)
                try:
                    import pwd
                    import grp
                    uid = pwd.getpwnam('www-data').pw_uid
                    gid = grp.getgrnam('www-data').gr_gid
                    os.chown(empresa_db_path, uid, gid)
                    os.chown(empresa_db_dir, uid, gid)
                except:
                    pass
            
            cursor.execute('''
                INSERT INTO empresas (codigo, nombre, cif, db_path, activa, logo_header, logo_factura)
                VALUES (?, ?, ?, ?, 1, '/public/assets/logo.svg', '/public/assets/logo.svg')
            ''', (codigo_empresa, nombre_empresa, nif, empresa_db_path))
            empresa_id = cursor.lastrowid
            
            # 3. Asignar usuario a empresa como admin
            cursor.execute('''
                INSERT INTO usuario_empresa (usuario_id, empresa_id, es_admin_empresa, fecha_asignacion)
                VALUES (?, ?, 1, datetime('now'))
            ''', (user_id, empresa_id))
            
            conn.commit()
        
        # 4. Activar trial de 15 días
        try:
            from subscription_routes import get_subscription_db
            from datetime import datetime, timedelta
            
            trial_start = datetime.now()
            trial_end = trial_start + timedelta(days=15)
            
            sub_conn = get_subscription_db()
            sub_cursor = sub_conn.cursor()
            sub_cursor.execute('''
                INSERT INTO subscriptions (
                    empresa_id, status, plan, current_period_start, current_period_end
                ) VALUES (?, 'free_trial', 'trial', ?, ?)
            ''', (str(empresa_id), trial_start.isoformat(), trial_end.isoformat()))
            sub_conn.commit()
            sub_conn.close()
            
            logger.info(f"Trial de 15 días activado para empresa {codigo_empresa}")
        except Exception as trial_error:
            logger.error(f"Error activando trial: {trial_error}")
        
        logger.info(f"Registro exitoso: {email} → empresa {codigo_empresa}")
        
        return jsonify({
            'success': True,
            'mensaje': '¡Registro completado! Ya puedes iniciar sesión.',
            'username': username,
            'empresa': nombre_empresa,
            'codigo': codigo_empresa,
            'trial_dias': 15
        }), 201
        
    except Exception as e:
        logger.error(f"Error en registro público: {e}", exc_info=True)
        return jsonify({'error': 'Error al procesar el registro'}), 500

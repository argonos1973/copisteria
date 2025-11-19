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
import uuid
import secrets
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
from multiempresa_config import DB_USUARIOS_PATH
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

@auth_bp.route('/empresas/<username>', methods=['GET'])
def obtener_empresas(username):
    """
    Obtiene las empresas disponibles para un usuario
    
    Endpoint: GET /api/auth/empresas/admin
    """
    try:
        empresas = obtener_empresas_usuario(username)
        return jsonify(empresas), 200
    except Exception as e:
        logger.error(f"Error obteniendo empresas: {e}", exc_info=True)
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
        
        # Obtener avatar, email y teléfono de la base de datos
        avatar = None
        email = None
        telefono = None
        if user_id:
            conn = sqlite3.connect(DB_USUARIOS_PATH)
            cursor = conn.cursor()
            cursor.execute('SELECT avatar, email, telefono FROM usuarios WHERE id = ?', (user_id,))
            result = cursor.fetchone()
            if result:
                avatar = result[0] if result[0] else None
                email = result[1] if result[1] else None
                telefono = result[2] if result[2] else None
            conn.close()
        
        return jsonify({
            'usuario': session.get('nombre_completo'),
            'username': session.get('username'),
            'email': email,
            'telefono': telefono,
            'empresa': session.get('empresa_nombre'),
            'empresa_codigo': session.get('empresa_codigo'),
            'logo': f"/static/logos/{session.get('empresa_logo', 'default_header.png')}",
            'avatar': avatar,
            'rol': session.get('rol'),
            'es_admin': session.get('es_admin_empresa') or session.get('es_superadmin'),
            'es_admin_empresa': session.get('es_admin_empresa', False),
            'es_superadmin': session.get('es_superadmin'),
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
        
        conn = sqlite3.connect(DB_USUARIOS_PATH)
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
        permisos_usuario = {}
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
                },
                {
                    'nombre': 'Exportar',
                    'icono': 'fas fa-download',
                    'ruta': '/EXPORTAR.html'
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
                {'nombre': 'Conciliación', 'icono': 'fas fa-exchange-alt', 'ruta': '/CONCILIACION_GASTOS.html'},
                {'nombre': 'Extracto Bancario', 'icono': 'fas fa-file-invoice-dollar', 'ruta': '/extracto_bancario'},
                {'nombre': 'Conectar Banco', 'icono': 'fas fa-university', 'ruta': '/conectar_banco'}
            ],
            'facturas_recibidas': [
                {'nombre': 'Consultar Facturas', 'icono': 'fas fa-search', 'ruta': '/CONSULTA_FACTURAS_RECIBIDAS.html'},
                {'nombre': 'Subir Factura', 'icono': 'fas fa-file-upload', 'ruta': '/SUBIR_FACTURAS_MASIVO.html'},
                {'nombre': 'Gestión Proveedores', 'icono': 'fas fa-users', 'ruta': '/GESTION_PROVEEDORES.html'}
            ]  # Submenu de facturas de proveedores
        }
        
        # Módulos que ya están incluidos en submenus (no deben aparecer como items independientes)
        modulos_en_submenu = ['facturas', 'tickets', 'proformas', 'exportar', 'admin_empresas']
        
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
                            if nombre_subsub == 'Nuevo':
                                if permisos_usuario.get(codigo_modulo, {}).get('puede_crear', 0) == 1:
                                    submenu_filtrado.append(submenu_item)
                            else:
                                # Consultar, Franjas, etc. - siempre incluir si tiene ver
                                submenu_filtrado.append(submenu_item)
                    
                    item['submenu'] = submenu_filtrado
                
                logger.info(f"[MENU] Submódulos agregados a {codigo_modulo}: {len(item.get('submenu', []))} items")
            
            # Decidir si incluir el módulo en el menú
            incluir_modulo = False
            
            if codigo_modulo in modulos_en_submenu:
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
        logger.info(f"[MENU] Rol del usuario: {rol_usuario}")
        
        # Agregar opciones de administración solo si es admin de empresa Y tiene rol 'admin'
        if es_admin_empresa and rol_usuario == 'admin':
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
                'submenu': [
                    {
                        'nombre': 'Permisos',
                        'icono': 'fas fa-cog',
                        'ruta': '/ADMIN_PERMISOS.html'
                    }
                ]
            })
            logger.info("[MENU] Opciones de administración agregadas para admin de empresa")
        
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
        app_path = os.path.join(BASE_DIR, 'frontend', '_app_private.html')
        with open(app_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, mimetype='text/html')
    except Exception as e:
        logger.error(f"Error sirviendo aplicación: {e}", exc_info=True)
        return jsonify({'error': 'Error sirviendo aplicación'}), 500

@auth_bp.route('/branding-preview/<empresa_codigo>', methods=['GET'])
def obtener_branding_preview(empresa_codigo):
    """
    Retorna configuración visual de una empresa por su código (sin autenticación, solo para preview en login)
    """
    try:
        conn = sqlite3.connect(DB_USUARIOS_PATH)
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
        conn.close()
        
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
        
        conn = sqlite3.connect(DB_USUARIOS_PATH)
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
        conn.close()
        
        if not empresa:
            return jsonify({'error': 'Empresa no encontrada'}), 404
        
        # Usar directamente el campo plantilla (minimal, dark, eink)
        plantilla_base = empresa['plantilla'] or 'dark'  # default dark
        plantilla_nombre = empresa['plantilla_personalizada'] or plantilla_base.capitalize()
        
        logger.info(f"[BRANDING] Plantilla: {plantilla_base} ('{plantilla_nombre}')")
        
        return jsonify({
            'empresa_id': empresa_id,  # ← Agregar empresa_id
            'logo_header': empresa['logo_header'],
            'logo_factura': empresa['logo_factura'],
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
        
        # Verificar password actual
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT password_hash FROM usuarios WHERE id = ?', (user_id,))
        actual_hash = cursor.fetchone()[0]
        
        from auth_middleware import verificar_password, hash_password
        
        if not verificar_password(password_actual, actual_hash):
            conn.close()
            return jsonify({'error': 'Contraseña actual incorrecta'}), 401
        
        # Actualizar password
        nuevo_hash = hash_password(password_nueva)
        cursor.execute('UPDATE usuarios SET password_hash = ? WHERE id = ?', (nuevo_hash, user_id))
        conn.commit()
        conn.close()
        
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
        
        # Obtener URL base del request
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
        cursor.execute('UPDATE usuarios SET password = ? WHERE id = ?', 
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

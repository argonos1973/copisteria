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
from flask import Blueprint, request, jsonify, session, render_template_string, Response, make_response
from logger_config import get_logger
from auth_middleware import (
    autenticar_usuario, cerrar_sesion, obtener_empresas_usuario,
    login_required, registrar_auditoria
)
import sqlite3
from multiempresa_config import DB_USUARIOS_PATH

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
        empresa_codigo = data.get('empresa', '').strip()
        
        if not username or not password or not empresa_codigo:
            return jsonify({'error': 'Usuario, contraseña y empresa son requeridos'}), 400
        
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
        session.modified = True
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

@auth_bp.route('/session', methods=['GET'])
@login_required
def obtener_sesion():
    """
    Obtiene información de la sesión actual
    """
    try:
        return jsonify({
            'usuario': session.get('nombre_completo'),
            'username': session.get('username'),
            'empresa': session.get('empresa_nombre'),
            'empresa_codigo': session.get('empresa_codigo'),
            'logo': f"/static/logos/{session.get('empresa_logo', 'default_header.png')}",
            'rol': session.get('rol'),
            'es_admin': session.get('es_admin_empresa') or session.get('es_superadmin'),
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
                SELECT modulo_codigo, puede_ver, puede_crear
                FROM permisos_usuario_modulo
                WHERE usuario_id = ? AND empresa_id = ?
            ''', (user_id, empresa_id))
            for perm_row in cursor.fetchall():
                permisos_usuario[perm_row[0]] = {
                    'puede_ver': perm_row[1],
                    'puede_crear': perm_row[2]
                }
        
        # Definir submódulos fuera del loop
        submenu_map = {
            'facturas_emitidas': [
                {
                    'nombre': 'Tickets',
                    'icono': 'fas fa-receipt',
                    'ruta': '#',
                    'submenu': [
                        {'nombre': 'Consultar', 'icono': 'fas fa-search', 'ruta': '/CONSULTA_TICKETS.html'},
                        {'nombre': 'Nuevo', 'icono': 'fas fa-plus', 'ruta': '/GESTION_TICKETS.html'}
                    ]
                },
                {
                    'nombre': 'Facturas',
                    'icono': 'fas fa-file-invoice',
                    'ruta': '#',
                    'submenu': [
                        {'nombre': 'Consultar', 'icono': 'fas fa-search', 'ruta': '/CONSULTA_FACTURAS.html'}
                    ]
                },
                {
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
                {'nombre': 'Conciliación', 'icono': 'fas fa-exchange-alt', 'ruta': '/CONCILIACION_GASTOS.html'}
            ]
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
            
            # Agregar submódulos según el código del módulo
            codigo_modulo = item['codigo']
            if codigo_modulo in submenu_map:
                # Filtrar submenús según permisos del usuario
                submenu_completo = submenu_map[codigo_modulo]
                
                if es_admin_empresa:
                    # Admin ve todo
                    item['submenu'] = submenu_completo
                else:
                    # Filtrar según permisos
                    submenu_filtrado = []
                    for submenu_item in submenu_completo:
                        # Mapeo de nombres a códigos de módulo
                        nombre_modulo_map = {
                            'Tickets': 'tickets',
                            'Facturas': 'facturas',
                            'Proformas': 'proformas',
                            'Exportar': 'exportar'
                        }
                        
                        nombre_sub = submenu_item.get('nombre', '')
                        modulo_codigo_sub = nombre_modulo_map.get(nombre_sub)
                        
                        # Si no tiene mapeo o si tiene permiso de ver, incluir
                        if not modulo_codigo_sub or permisos_usuario.get(modulo_codigo_sub, {}).get('puede_ver', 0) == 1:
                            # Filtrar sub-submenús si existen
                            if 'submenu' in submenu_item and modulo_codigo_sub:
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
                                    submenu_item_copia = submenu_item.copy()
                                    submenu_item_copia['submenu'] = submenu_interno_filtrado
                                    submenu_filtrado.append(submenu_item_copia)
                            else:
                                submenu_filtrado.append(submenu_item)
                    
                    item['submenu'] = submenu_filtrado
                
                logger.info(f"[MENU] Submódulos agregados a {codigo_modulo}: {len(item.get('submenu', []))} items")
            
            # Solo agregar si NO está en un submenu
            if codigo_modulo not in modulos_en_submenu:
                menu.append(item)
                logger.info(f"[MENU] Item agregado al menú: {item['nombre']}")
            else:
                logger.info(f"[MENU] Item omitido (está en submenu): {item['nombre']}")
        
        logger.info(f"[MENU] Total items en menú: {len(menu)}")
        
        # Agregar opciones de administración si es admin de empresa
        if es_admin_empresa:
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
                        'nombre': 'Gestión',
                        'icono': 'fas fa-cog',
                        'ruta': '/ADMIN_PERMISOS.html'
                    },
                    {
                        'nombre': 'Nueva Empresa',
                        'icono': 'fas fa-plus-circle',
                        'ruta': '/NUEVA_EMPRESA.html'
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

@auth_bp.route('/cambiar-password', methods=['POST'])
@login_required
def cambiar_password():
    """
    Permite al usuario cambiar su contraseña
    """
    try:
        data = request.json
        password_actual = data.get('password_actual')
        password_nueva = data.get('password_nueva')
        
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

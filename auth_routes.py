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

from flask import Blueprint, request, jsonify, session, render_template_string
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
        
        return jsonify(resultado), 200
        
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
            'rol': session.get('rol'),
            'es_admin': session.get('es_admin_empresa') or session.get('es_superadmin'),
            'es_superadmin': session.get('es_superadmin')
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
        
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        if es_superadmin:
            # Superadmin ve todos los módulos
            cursor.execute('''
                SELECT codigo, nombre, ruta, icono, orden
                FROM modulos
                WHERE activo = 1
                ORDER BY orden
            ''')
        else:
            # Usuario normal según permisos
            cursor.execute('''
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
            ''', (user_id, empresa_id))
        
        menu = []
        for row in cursor.fetchall():
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
            
            menu.append(item)
        
        conn.close()
        
        registrar_auditoria('menu_cargado')
        
        return jsonify(menu), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo menú: {e}", exc_info=True)
        return jsonify({'error': 'Error obteniendo menú'}), 500

@auth_bp.route('/branding', methods=['GET'])
@login_required
def obtener_branding():
    """
    Retorna configuración visual de la empresa activa
    """
    try:
        empresa_id = session.get('empresa_id')
        
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                logo_header, logo_factura,
                color_primario, color_secundario,
                nombre, cif, direccion, telefono, email, web
            FROM empresas
            WHERE id = ?
        ''', (empresa_id,))
        
        empresa = cursor.fetchone()
        conn.close()
        
        if not empresa:
            return jsonify({'error': 'Empresa no encontrada'}), 404
        
        return jsonify({
            'logo_header': empresa[0],
            'logo_factura': empresa[1],
            'colores': {
                'primario': empresa[2],
                'secundario': empresa[3]
            },
            'datos': {
                'nombre': empresa[4],
                'cif': empresa[5],
                'direccion': empresa[6],
                'telefono': empresa[7],
                'email': empresa[8],
                'web': empresa[9]
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

# -*- coding: utf-8 -*-
"""
============================================================================
MIDDLEWARE DE AUTENTICACIÓN MULTIEMPRESA
============================================================================
Archivo: auth_middleware.py
Descripción: Sistema de autenticación y control de permisos
Fecha: 2025-10-21
============================================================================
"""

import sqlite3
import hashlib
from functools import wraps
from flask import session, request, jsonify, redirect
from logger_config import get_logger
from multiempresa_config import (
    DB_USUARIOS_PATH, PUBLIC_ROUTES, ADMIN_ROUTES,
    SECURITY_CONFIG, obtener_db_empresa
)

logger = get_logger(__name__)

# ============================================================================
# FUNCIONES DE UTILIDAD
# ============================================================================

def hash_password(password):
    """
    Genera hash SHA256 de una contraseña
    """
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verificar_password(password, password_hash):
    """
    Verifica una contraseña contra su hash
    Soporta tanto SHA256 (legacy) como Werkzeug scrypt (nuevo)
    """
    # Si el hash empieza con scrypt: es un hash de Werkzeug
    if password_hash.startswith('scrypt:') or password_hash.startswith('pbkdf2:'):
        from werkzeug.security import check_password_hash
        return check_password_hash(password_hash, password)
    # Si no, es el hash SHA256 legacy
    return hash_password(password) == password_hash

def es_ruta_publica(ruta):
    """
    Verifica si una ruta es pública (no requiere autenticación)
    """
    for public_route in PUBLIC_ROUTES:
        if ruta.startswith(public_route):
            return True
    return False

def es_ruta_admin(ruta):
    """
    Verifica si una ruta requiere permisos de administrador
    """
    for admin_route in ADMIN_ROUTES:
        if ruta.startswith(admin_route):
            return True
    return False

def registrar_auditoria(accion, modulo=None, descripcion=None):
    """
    Registra una acción en el log de auditoría
    """
    try:
        usuario_id = session.get('user_id')
        empresa_id = session.get('empresa_id')
        
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO auditoria 
            (usuario_id, empresa_id, accion, modulo, descripcion, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            usuario_id,
            empresa_id,
            accion,
            modulo,
            descripcion,
            request.remote_addr,
            request.headers.get('User-Agent', '')[:200]
        ))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error registrando auditoría: {e}", exc_info=True)

# ============================================================================
# DECORADORES DE AUTENTICACIÓN
# ============================================================================

def login_required(f):
    """
    Decorador para rutas que requieren autenticación
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # DEBUG: Ver contenido de la sesión
        session_data = dict(session)
        logger.debug(f"Verificando sesión para {request.path}: {list(session_data.keys())}")
        
        if 'user_id' not in session:
            logger.warning(f"Acceso no autenticado a: {request.path} - Sesión: {list(session_data.keys())}")
            
            # Si es petición AJAX, retornar JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'No autenticado', 'redirect': '/LOGIN.html'}), 401
            
            # Si es petición normal, redirigir a login
            return redirect('/LOGIN.html')
        
        logger.debug(f"Sesión válida para user_id={session.get('user_id')}")
        return f(*args, **kwargs)
    
    return decorated_function

def require_admin(f):
    """
    Decorador para rutas que requieren permisos de administrador Y empresa asignada
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'No autenticado'}), 401
        
        # Verificar si tiene empresa asignada
        empresa_id = session.get('empresa_id')
        if not empresa_id:
            logger.warning(f"Acceso denegado (sin empresa) para usuario {session.get('username')} a: {request.path}")
            registrar_auditoria('acceso_denegado_sin_empresa', descripcion=f'Intento acceso a {request.path} sin empresa')
            return redirect('/bienvenida.html')
        
        # Verificar si es superadmin o admin de empresa
        es_admin_empresa = session.get('es_admin_empresa', False)
        es_superadmin = session.get('es_superadmin', False)
        
        if not (es_admin_empresa or es_superadmin):
            logger.warning(f"Acceso denegado (admin) para usuario {session.get('username')} a: {request.path}")
            registrar_auditoria('acceso_denegado_admin', descripcion=f'Intento acceso a {request.path}')
            return jsonify({'error': 'Acceso denegado. Se requieren permisos de administrador'}), 403
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_permission(modulo, accion):
    """
    Decorador para verificar permisos específicos sobre un módulo
    
    Uso:
        @require_permission('facturas', 'crear')
        def crear_factura():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'error': 'No autenticado'}), 401
            
            # Superadmin tiene todos los permisos
            if session.get('es_superadmin'):
                return f(*args, **kwargs)
            
            usuario_id = session.get('user_id')
            empresa_id = session.get('empresa_id')
            
            if not usuario_id or not empresa_id:
                return jsonify({'error': 'Sesión inválida'}), 401
            
            try:
                conn = sqlite3.connect(DB_USUARIOS_PATH)
                cursor = conn.cursor()
                
                campo_permiso = f'puede_{accion}'
                cursor.execute(f'''
                    SELECT {campo_permiso}
                    FROM permisos_usuario_modulo
                    WHERE usuario_id = ? 
                    AND empresa_id = ?
                    AND modulo_codigo = ?
                ''', (usuario_id, empresa_id, modulo))
                
                resultado = cursor.fetchone()
                conn.close()
                
                if not resultado or not resultado[0]:
                    logger.warning(
                        f"Permiso denegado: usuario={session.get('username')}, "
                        f"modulo={modulo}, accion={accion}"
                    )
                    registrar_auditoria(
                        'permiso_denegado',
                        modulo=modulo,
                        descripcion=f'Intento {accion} sin permisos'
                    )
                    return jsonify({
                        'error': f'No tienes permisos para {accion} en {modulo}'
                    }), 403
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Error verificando permisos: {e}", exc_info=True)
                return jsonify({'error': 'Error verificando permisos'}), 500
        
        return decorated_function
    return decorator

# ============================================================================
# FUNCIONES DE AUTENTICACIÓN
# ============================================================================

def autenticar_usuario(username, password, empresa_codigo):
    """
    Autentica un usuario contra la base de datos
    
    Retorna: dict con información del usuario o None si falla
    """
    try:
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        # Verificar usuario
        cursor.execute('''
            SELECT id, password_hash, nombre_completo, activo, es_superadmin, intentos_fallidos
            FROM usuarios
            WHERE username = ?
        ''', (username,))
        
        usuario = cursor.fetchone()
        
        if not usuario:
            logger.warning(f"Intento de login con usuario inexistente: {username}")
            return None
        
        user_id, password_hash, nombre_completo, activo, es_superadmin, intentos_fallidos = usuario
        
        # Verificar si está bloqueado
        if intentos_fallidos >= SECURITY_CONFIG['MAX_LOGIN_ATTEMPTS']:
            logger.warning(f"Usuario bloqueado por intentos fallidos: {username}")
            return {'error': 'Usuario bloqueado por múltiples intentos fallidos'}
        
        # Verificar si está activo
        if not activo:
            logger.warning(f"Intento de login con usuario inactivo: {username}")
            return {'error': 'Usuario inactivo'}
        
        # Verificar contraseña
        if not verificar_password(password, password_hash):
            # Incrementar intentos fallidos
            cursor.execute('''
                UPDATE usuarios 
                SET intentos_fallidos = intentos_fallidos + 1
                WHERE id = ?
            ''', (user_id,))
            conn.commit()
            logger.warning(f"Contraseña incorrecta para usuario: {username}")
            conn.close()
            return None
        
        # Si empresa_codigo es None o vacío, permitir login sin empresa
        if not empresa_codigo:
            logger.info(f"Usuario {username} ingresando sin empresa asignada")
            # Usuario sin empresa - acceso limitado
            rol = 'usuario'
            es_admin_empresa = True  # Usuario sin empresa es admin para poder crear su empresa
            empresa_id = None
            empresa_nombre = 'Sin Empresa'
            db_path = None
            logo_header = 'aleph_completo.png'  # Logo completo de Aleph70
        else:
            # Verificar acceso a empresa
            cursor.execute('''
                SELECT u.rol, ue.es_admin_empresa, e.id, e.nombre, e.db_path, e.logo_header
                FROM usuario_empresa ue
                JOIN empresas e ON ue.empresa_id = e.id
                JOIN usuarios u ON ue.usuario_id = u.id
                WHERE ue.usuario_id = ? 
                AND e.codigo = ?
                AND e.activa = 1
            ''', (user_id, empresa_codigo))
            
            empresa = cursor.fetchone()
            
            if not empresa:
                logger.warning(f"Usuario {username} sin acceso a empresa {empresa_codigo}")
                conn.close()
                return {'error': 'No tienes acceso a esta empresa'}
            
            rol, es_admin_empresa, empresa_id, empresa_nombre, db_path, logo_header = empresa
        
        # Obtener último acceso ANTES de actualizarlo
        cursor.execute('SELECT ultimo_acceso FROM usuarios WHERE id = ?', (user_id,))
        ultimo_acceso_row = cursor.fetchone()
        ultimo_acceso_anterior = ultimo_acceso_row[0] if ultimo_acceso_row and ultimo_acceso_row[0] else None
        
        # Reset intentos fallidos y actualizar último acceso
        cursor.execute('''
            UPDATE usuarios 
            SET intentos_fallidos = 0,
                ultimo_acceso = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (user_id,))
        
        conn.commit()
        conn.close()
        
        # Registrar login exitoso
        # NO usar session.clear() porque borra metadatos de Flask-Session
        session.permanent = True  # Hacer que la sesión persista según PERMANENT_SESSION_LIFETIME
        session['user_id'] = user_id
        session['username'] = username
        session['nombre_completo'] = nombre_completo
        session['empresa_id'] = empresa_id
        session['empresa_codigo'] = empresa_codigo
        session['empresa_nombre'] = empresa_nombre
        session['empresa_db'] = db_path  # IMPORTANTE: BD de la empresa para conexiones
        session['empresa_logo'] = logo_header  # Guardar logo en sesión
        session['rol'] = rol
        session['es_admin_empresa'] = es_admin_empresa
        session['es_superadmin'] = es_superadmin
        session['ultimo_acceso'] = ultimo_acceso_anterior
        
        logger.info(f"Login exitoso: {username} → {empresa_nombre} (BD: {db_path})")
        
        return {
            'success': True,
            'usuario': nombre_completo,
            'empresa': empresa_nombre,
            'rol': rol,
            'es_admin': es_admin_empresa or es_superadmin
        }
        
    except Exception as e:
        logger.error(f"Error en autenticación: {e}", exc_info=True)
        return {'error': 'Error en el sistema de autenticación'}

def cerrar_sesion():
    """
    Cierra la sesión del usuario actual
    """
    username = session.get('username', 'Desconocido')
    empresa = session.get('empresa_nombre', 'Desconocida')
    
    registrar_auditoria('logout', descripcion=f'Logout de {empresa}')
    
    logger.info(f"Logout: {username} de {empresa}")
    session.clear()

def obtener_empresas_usuario(username):
    """
    Obtiene la lista de empresas a las que tiene acceso un usuario
    """
    try:
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT e.codigo, e.nombre, e.logo_header
            FROM empresas e
            JOIN usuario_empresa ue ON e.id = ue.empresa_id
            JOIN usuarios u ON ue.usuario_id = u.id
            WHERE u.username = ? AND e.activa = 1
            ORDER BY e.nombre
        ''', (username,))
        
        empresas = []
        for row in cursor.fetchall():
            empresas.append({
                'codigo': row[0],
                'nombre': row[1],
                'logo': row[2]
            })
        
        conn.close()
        return empresas
        
    except Exception as e:
        logger.error(f"Error obteniendo empresas de usuario: {e}", exc_info=True)
        return []

def get_db_empresa():
    """
    Retorna la ruta de la BD de la empresa actual según sesión
    MULTIEMPRESA: Ya NO usa BD por defecto hardcodeada
    """
    if 'empresa_db' not in session:
        logger.error("[MULTIEMPRESA] get_db_empresa(): session['empresa_db'] no definida")
        raise RuntimeError("BD de empresa no definida en sesión. Usuario debe iniciar sesión.")
    return session.get('empresa_db')

def superadmin_required(f):
    """
    Decorador que verifica que el usuario sea superadministrador
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            logger.warning(f"Acceso no autenticado a: {request.path}")
            # Si es una petición API, devolver JSON en lugar de redirect
            if request.path.startswith('/api/'):
                return jsonify({'error': 'No autenticado'}), 401
            return redirect(url_for('auth.login'))
        
        if not session.get('es_superadmin'):
            logger.warning(f"Acceso denegado (no superadmin): user_id={session.get('user_id')} a {request.path}")
            return jsonify({'error': 'Acceso denegado - Se requieren permisos de superadministrador'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

# -*- coding: utf-8 -*-
"""
============================================================================
RUTAS DE ADMINISTRACIÓN
============================================================================
Endpoints para gestión de usuarios, permisos, empresas y módulos
Requiere permisos de superadmin o admin_empresa
============================================================================
"""

import sqlite3
import hashlib
from flask import Blueprint, jsonify, request, session
from auth_middleware import login_required, require_admin
from multiempresa_config import DB_USUARIOS_PATH
from logger_config import get_logger

logger = get_logger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

def hash_password(password):
    """Genera hash SHA256 de una contraseña"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

# ============================================================================
# USUARIOS
# ============================================================================

@admin_bp.route('/usuarios', methods=['GET'])
@login_required
@require_admin
def listar_usuarios():
    """Lista solo usuarios de la empresa del admin"""
    try:
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        empresa_id_admin = session.get('empresa_id')
        
        # Admin de empresa: solo usuarios de su empresa
        cursor.execute('''
            SELECT 
                u.id, u.username, u.nombre_completo, u.email, u.telefono,
                u.activo, u.fecha_alta, u.ultimo_acceso,
                ue.rol, ue.es_admin_empresa,
                GROUP_CONCAT(DISTINCT e.nombre) as empresas,
                GROUP_CONCAT(DISTINCT e.codigo) as empresas_codigos
            FROM usuarios u
            INNER JOIN usuario_empresa ue ON u.id = ue.usuario_id
            INNER JOIN empresas e ON ue.empresa_id = e.id
            WHERE ue.empresa_id = ?
            GROUP BY u.id
            ORDER BY u.username
        ''', (empresa_id_admin,))
        
        usuarios = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(usuarios), 200
        
    except Exception as e:
        logger.error(f"Error listando usuarios: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/usuarios', methods=['POST'])
@admin_bp.route('/usuarios/crear', methods=['POST'])
@login_required
@require_admin
def crear_usuario():
    """Crea un nuevo usuario (admin de empresa solo puede crear usuarios de su empresa)"""
    try:
        data = request.json
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        nombre_completo = data.get('nombre_completo', '').strip()
        email = data.get('email', '').strip()
        telefono = data.get('telefono', '').strip()
        
        if not username or not password or not nombre_completo:
            return jsonify({'error': 'Faltan campos requeridos'}), 400
        
        # Verificar que el creador tenga empresa asignada
        empresa_id_creador = session.get('empresa_id')
        
        # Permitir crear usuarios sin empresa si así se especifica
        asignar_empresa = data.get('asignar_empresa', True)  # Por defecto asigna empresa
        
        if not empresa_id_creador and asignar_empresa:
            return jsonify({'error': 'Tu cuenta no tiene empresa asignada'}), 403
        
        password_hash = hash_password(password)
        
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        # es_superadmin siempre 0 (ya no hay superadmins)
        cursor.execute('''
            INSERT INTO usuarios (username, password_hash, nombre_completo, email, telefono, es_superadmin, activo)
            VALUES (?, ?, ?, ?, ?, 0, 1)
        ''', (username, password_hash, nombre_completo, email, telefono))
        
        usuario_id = cursor.lastrowid
        
        # Asignar a empresa solo si se especifica y hay empresa
        if asignar_empresa and empresa_id_creador:
            cursor.execute('''
                INSERT INTO usuario_empresa (usuario_id, empresa_id, rol, es_admin_empresa)
                VALUES (?, ?, 'usuario', 0)
            ''', (usuario_id, empresa_id_creador))
            logger.info(f"Usuario {username} asignado automáticamente a empresa ID {empresa_id_creador}")
        else:
            logger.info(f"Usuario {username} creado sin empresa asignada")
        
        conn.commit()
        conn.close()
        
        logger.info(f"Usuario creado: {username} (ID: {usuario_id})")
        
        return jsonify({'success': True, 'id': usuario_id, 'mensaje': f'Usuario {username} creado correctamente'}), 201
        
    except sqlite3.IntegrityError:
        return jsonify({'error': 'El nombre de usuario ya existe'}), 400
    except Exception as e:
        logger.error(f"Error creando usuario: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/usuarios/<int:usuario_id>', methods=['PUT'])
@login_required
@require_admin
def actualizar_usuario(usuario_id):
    """Actualiza un usuario existente (admin de empresa solo puede modificar usuarios de su empresa)"""
    try:
        data = request.json
        
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        # Verificar que el usuario pertenece a la empresa del admin
        empresa_id_editor = session.get('empresa_id')
        
        cursor.execute('''
            SELECT COUNT(*) FROM usuario_empresa 
            WHERE usuario_id = ? AND empresa_id = ?
        ''', (usuario_id, empresa_id_editor))
        
        if cursor.fetchone()[0] == 0:
            conn.close()
            return jsonify({'error': 'No tienes permisos para modificar este usuario'}), 403
        
        # Construir query dinámicamente
        campos = []
        valores = []
        
        if 'nombre_completo' in data:
            campos.append('nombre_completo = ?')
            valores.append(data['nombre_completo'])
        
        if 'email' in data:
            campos.append('email = ?')
            valores.append(data['email'])
        
        if 'telefono' in data:
            campos.append('telefono = ?')
            valores.append(data['telefono'])
        
        if 'activo' in data:
            campos.append('activo = ?')
            valores.append(data['activo'])
        
        if 'password' in data and data['password']:
            campos.append('password_hash = ?')
            valores.append(hash_password(data['password']))
        
        if not campos:
            conn.close()
            return jsonify({'error': 'No hay campos para actualizar'}), 400
        
        valores.append(usuario_id)
        
        query = f"UPDATE usuarios SET {', '.join(campos)} WHERE id = ?"
        cursor.execute(query, valores)
        
        conn.commit()
        conn.close()
        
        logger.info(f"Usuario actualizado: ID {usuario_id}")
        
        return jsonify({'success': True, 'mensaje': 'Usuario actualizado correctamente'}), 200
        
    except Exception as e:
        logger.error(f"Error actualizando usuario: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/usuarios/<int:usuario_id>', methods=['DELETE'])
@login_required
@require_admin
def eliminar_usuario(usuario_id):
    """Elimina un usuario (admin de empresa solo puede eliminar usuarios de su empresa)"""
    try:
        # No permitir eliminar el propio usuario
        if usuario_id == session.get('user_id'):
            return jsonify({'error': 'No puedes eliminar tu propio usuario'}), 400
        
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        # Verificar que el usuario pertenece a la empresa del admin
        empresa_id_eliminador = session.get('empresa_id')
        
        cursor.execute('''
            SELECT COUNT(*) FROM usuario_empresa 
            WHERE usuario_id = ? AND empresa_id = ?
        ''', (usuario_id, empresa_id_eliminador))
        
        if cursor.fetchone()[0] == 0:
            conn.close()
            return jsonify({'error': 'No tienes permisos para eliminar este usuario'}), 403
        
        cursor.execute('DELETE FROM usuarios WHERE id = ?', (usuario_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        conn.commit()
        conn.close()
        
        logger.info(f"Usuario eliminado: ID {usuario_id}")
        
        return jsonify({'success': True, 'mensaje': 'Usuario eliminado correctamente'}), 200
        
    except Exception as e:
        logger.error(f"Error eliminando usuario: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# ============================================================================
# EMPRESAS
# ============================================================================

@admin_bp.route('/empresas', methods=['GET'])
@login_required
@require_admin
def listar_empresas():
    """Lista todas las empresas"""
    try:
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                e.*,
                COUNT(DISTINCT ue.usuario_id) as total_usuarios
            FROM empresas e
            LEFT JOIN usuario_empresa ue ON e.id = ue.empresa_id
            GROUP BY e.id
            ORDER BY e.nombre
        ''')
        
        empresas = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(empresas), 200
        
    except Exception as e:
        logger.error(f"Error listando empresas: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# ============================================================================
# MÓDULOS
# ============================================================================

@admin_bp.route('/modulos', methods=['GET'])
@login_required
@require_admin
def listar_modulos():
    """Lista todos los módulos"""
    try:
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM modulos ORDER BY orden, nombre')
        
        modulos = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(modulos), 200
        
    except Exception as e:
        logger.error(f"Error listando módulos: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# ============================================================================
# PERMISOS
# ============================================================================

@admin_bp.route('/usuarios/<int:usuario_id>/empresas', methods=['GET'])
@login_required
@require_admin
def obtener_empresas_usuario(usuario_id):
    """Obtiene las empresas asignadas a un usuario"""
    try:
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                e.id, e.codigo, e.nombre,
                ue.rol, ue.es_admin_empresa
            FROM usuario_empresa ue
            JOIN empresas e ON ue.empresa_id = e.id
            WHERE ue.usuario_id = ?
        ''', (usuario_id,))
        
        empresas = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(empresas), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo empresas del usuario: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/usuarios/<int:usuario_id>/empresas', methods=['POST'])
@login_required
@require_admin
def asignar_empresa_usuario(usuario_id):
    """Asigna una empresa a un usuario"""
    try:
        data = request.json
        empresa_id = data.get('empresa_id')
        rol = data.get('rol', 'usuario')
        es_admin_empresa = data.get('es_admin_empresa', 0)
        
        if not empresa_id:
            return jsonify({'error': 'empresa_id es requerido'}), 400
        
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO usuario_empresa (usuario_id, empresa_id, rol, es_admin_empresa)
            VALUES (?, ?, ?, ?)
        ''', (usuario_id, empresa_id, rol, es_admin_empresa))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Empresa {empresa_id} asignada a usuario {usuario_id}")
        
        return jsonify({'success': True, 'mensaje': 'Empresa asignada correctamente'}), 201
        
    except sqlite3.IntegrityError:
        return jsonify({'error': 'El usuario ya tiene asignada esta empresa'}), 400
    except Exception as e:
        logger.error(f"Error asignando empresa: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/usuarios/<int:usuario_id>/empresas/<int:empresa_id>', methods=['DELETE'])
@login_required
@require_admin
def desasignar_empresa_usuario(usuario_id, empresa_id):
    """Desasigna una empresa de un usuario"""
    try:
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM usuario_empresa WHERE usuario_id = ? AND empresa_id = ?', (usuario_id, empresa_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Empresa {empresa_id} desasignada del usuario {usuario_id}")
        
        return jsonify({'success': True, 'mensaje': 'Empresa desasignada correctamente'}), 200
        
    except Exception as e:
        logger.error(f"Error desasignando empresa: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/usuarios/<int:usuario_id>/permisos', methods=['GET'])
@login_required
@require_admin
def obtener_permisos_usuario(usuario_id):
    """Obtiene todos los permisos de un usuario en todas sus empresas"""
    try:
        empresa_id = request.args.get('empresa_id')
        
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if empresa_id:
            cursor.execute('''
                SELECT p.*, m.nombre as modulo_nombre
                FROM permisos_usuario_modulo p
                JOIN modulos m ON p.modulo_codigo = m.codigo
                WHERE p.usuario_id = ? AND p.empresa_id = ?
                ORDER BY m.orden, m.nombre
            ''', (usuario_id, empresa_id))
        else:
            cursor.execute('''
                SELECT p.*, m.nombre as modulo_nombre, e.nombre as empresa_nombre
                FROM permisos_usuario_modulo p
                JOIN modulos m ON p.modulo_codigo = m.codigo
                JOIN empresas e ON p.empresa_id = e.id
                WHERE p.usuario_id = ?
                ORDER BY e.nombre, m.orden, m.nombre
            ''', (usuario_id,))
        
        permisos = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(permisos), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo permisos: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/usuarios/<int:usuario_id>/permisos', methods=['POST'])
@login_required
@require_admin
def actualizar_permisos_usuario(usuario_id):
    """Actualiza permisos de un usuario en un módulo"""
    try:
        data = request.json
        
        empresa_id = data.get('empresa_id')
        modulo_codigo = data.get('modulo_codigo')
        puede_ver = data.get('puede_ver', 0)
        puede_crear = data.get('puede_crear', 0)
        puede_editar = data.get('puede_editar', 0)
        puede_eliminar = data.get('puede_eliminar', 0)
        puede_anular = data.get('puede_anular', 0)
        puede_exportar = data.get('puede_exportar', 0)
        
        if not empresa_id or not modulo_codigo:
            return jsonify({'error': 'empresa_id y modulo_codigo son requeridos'}), 400
        
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO permisos_usuario_modulo 
            (usuario_id, empresa_id, modulo_codigo, puede_ver, puede_crear, puede_editar, puede_eliminar, puede_anular, puede_exportar)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (usuario_id, empresa_id, modulo_codigo, puede_ver, puede_crear, puede_editar, puede_eliminar, puede_anular, puede_exportar))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Permisos actualizados: usuario {usuario_id}, empresa {empresa_id}, módulo {modulo_codigo}")
        
        return jsonify({'success': True, 'mensaje': 'Permisos actualizados correctamente'}), 200
        
    except Exception as e:
        logger.error(f"Error actualizando permisos: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# ============================================================================
# ESTADÍSTICAS
# ============================================================================

@admin_bp.route('/stats', methods=['GET'])
@login_required
@require_admin
def obtener_estadisticas():
    """Obtiene estadísticas del sistema"""
    try:
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        # Total usuarios
        cursor.execute('SELECT COUNT(*) FROM usuarios WHERE activo = 1')
        total_usuarios = cursor.fetchone()[0]
        
        # Total empresas
        cursor.execute('SELECT COUNT(*) FROM empresas WHERE activa = 1')
        total_empresas = cursor.fetchone()[0]
        
        # Total módulos
        cursor.execute('SELECT COUNT(*) FROM modulos WHERE activo = 1')
        total_modulos = cursor.fetchone()[0]
        
        # Total permisos configurados
        cursor.execute('SELECT COUNT(*) FROM permisos_usuario_modulo')
        total_permisos = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'total_usuarios': total_usuarios,
            'total_empresas': total_empresas,
            'total_modulos': total_modulos,
            'total_permisos': total_permisos
        }), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

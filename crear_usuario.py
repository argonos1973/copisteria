#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para crear usuarios en el sistema multiempresa Aleph70
Uso: python3 crear_usuario.py
"""

import sqlite3
import hashlib
from datetime import datetime

DB_PATH = '/var/www/html/db/usuarios_sistema.db'

def hash_password(password):
    """Genera hash SHA256 de una contraseña"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def crear_usuario(username, password, nombre_completo, email='', es_admin=False):
    """
    Crea un nuevo usuario en el sistema
    
    Args:
        username: Nombre de usuario (único)
        password: Contraseña en texto plano
        nombre_completo: Nombre completo del usuario
        email: Email (opcional)
        es_admin: Si es superadmin (acceso a todo)
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        password_hash = hash_password(password)
        
        cursor.execute('''
            INSERT INTO usuarios (username, password_hash, nombre_completo, email, es_superadmin, activo)
            VALUES (?, ?, ?, ?, ?, 1)
        ''', (username, password_hash, nombre_completo, email, 1 if es_admin else 0))
        
        usuario_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"✅ Usuario '{username}' creado correctamente (ID: {usuario_id})")
        return usuario_id
        
    except sqlite3.IntegrityError:
        print(f"❌ Error: El usuario '{username}' ya existe")
        return None
    except Exception as e:
        print(f"❌ Error creando usuario: {e}")
        return None

def asignar_empresa(usuario_id, empresa_codigo, rol='usuario', es_admin_empresa=False):
    """
    Asigna un usuario a una empresa
    
    Args:
        usuario_id: ID del usuario
        empresa_codigo: Código de la empresa (ej: 'copisteria')
        rol: Rol en la empresa ('admin', 'usuario', 'lectura')
        es_admin_empresa: Si es administrador de esta empresa específica
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Obtener ID de empresa
        cursor.execute('SELECT id FROM empresas WHERE codigo = ?', (empresa_codigo,))
        result = cursor.fetchone()
        
        if not result:
            print(f"❌ Error: Empresa '{empresa_codigo}' no encontrada")
            conn.close()
            return False
        
        empresa_id = result[0]
        
        cursor.execute('''
            INSERT INTO usuario_empresa (usuario_id, empresa_id, rol, es_admin_empresa)
            VALUES (?, ?, ?, ?)
        ''', (usuario_id, empresa_id, rol, 1 if es_admin_empresa else 0))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Usuario asignado a empresa '{empresa_codigo}' como {rol}")
        return True
        
    except sqlite3.IntegrityError:
        print(f"❌ El usuario ya está asignado a esta empresa")
        return False
    except Exception as e:
        print(f"❌ Error asignando empresa: {e}")
        return False

def asignar_permisos_completos(usuario_id, empresa_codigo):
    """
    Asigna permisos completos a un usuario en todos los módulos de una empresa
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Obtener ID de empresa
        cursor.execute('SELECT id FROM empresas WHERE codigo = ?', (empresa_codigo,))
        result = cursor.fetchone()
        
        if not result:
            print(f"❌ Error: Empresa '{empresa_codigo}' no encontrada")
            conn.close()
            return False
        
        empresa_id = result[0]
        
        # Obtener todos los módulos activos
        cursor.execute('SELECT codigo FROM modulos WHERE activo = 1')
        modulos = cursor.fetchall()
        
        for (modulo_codigo,) in modulos:
            cursor.execute('''
                INSERT OR REPLACE INTO permisos_usuario_modulo 
                (usuario_id, empresa_id, modulo_codigo, puede_ver, puede_crear, puede_editar, puede_eliminar, puede_anular, puede_exportar)
                VALUES (?, ?, ?, 1, 1, 1, 1, 1, 1)
            ''', (usuario_id, empresa_id, modulo_codigo))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Permisos completos asignados ({len(modulos)} módulos)")
        return True
        
    except Exception as e:
        print(f"❌ Error asignando permisos: {e}")
        return False

def listar_usuarios():
    """Lista todos los usuarios del sistema"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.id, u.username, u.nombre_completo, u.email, u.activo, u.es_superadmin,
                   GROUP_CONCAT(e.codigo, ', ') as empresas
            FROM usuarios u
            LEFT JOIN usuario_empresa ue ON u.id = ue.usuario_id
            LEFT JOIN empresas e ON ue.empresa_id = e.id
            GROUP BY u.id
        ''')
        
        usuarios = cursor.fetchall()
        conn.close()
        
        print("\n" + "="*80)
        print("USUARIOS DEL SISTEMA")
        print("="*80)
        
        for usuario in usuarios:
            id, username, nombre, email, activo, superadmin, empresas = usuario
            estado = "✅ Activo" if activo else "❌ Inactivo"
            admin = "🔑 Superadmin" if superadmin else ""
            empresas_str = empresas if empresas else "Sin empresas"
            
            print(f"\nID: {id}")
            print(f"  Usuario: {username}")
            print(f"  Nombre: {nombre}")
            print(f"  Email: {email}")
            print(f"  Estado: {estado} {admin}")
            print(f"  Empresas: {empresas_str}")
        
        print("\n" + "="*80)
        
    except Exception as e:
        print(f"❌ Error listando usuarios: {e}")

# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == '__main__':
    print("\n🔐 GESTOR DE USUARIOS - ALEPH70\n")
    print("="*80)
    
    # Ejemplo: Crear un usuario nuevo
    print("\n1️⃣ CREAR USUARIO NUEVO:\n")
    
    usuario_id = crear_usuario(
        username='juan',
        password='juan123',
        nombre_completo='Juan García',
        email='juan@empresa.com',
        es_admin=False  # False = usuario normal, True = superadmin
    )
    
    if usuario_id:
        # Asignar a empresa
        print("\n2️⃣ ASIGNAR A EMPRESA:\n")
        asignar_empresa(
            usuario_id=usuario_id,
            empresa_codigo='copisteria',
            rol='usuario',  # 'admin', 'usuario', 'lectura'
            es_admin_empresa=False
        )
        
        # Asignar permisos
        print("\n3️⃣ ASIGNAR PERMISOS:\n")
        asignar_permisos_completos(usuario_id, 'copisteria')
    
    # Listar todos los usuarios
    print("\n4️⃣ USUARIOS ACTUALES:\n")
    listar_usuarios()
    
    print("\n✅ Proceso completado\n")

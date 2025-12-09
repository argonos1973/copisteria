# -*- coding: utf-8 -*-
"""
============================================================================
CONFIGURACIÓN SISTEMA MULTIEMPRESA
============================================================================
Archivo: multiempresa_config.py
Descripción: Configuración central para sistema multiempresa
Fecha: 2025-10-21
============================================================================
"""

import os
from logger_config import get_logger

logger = get_logger(__name__)

# Ruta base de la aplicación
BASE_DIR = '/var/www/html'

# Base de datos central de usuarios y configuración
DB_USUARIOS_PATH = os.path.join(BASE_DIR, 'db', 'usuarios_sistema.db')

# Configuración de sesiones
SESSION_CONFIG = {
    'SECRET_KEY': 'e296f3311294d608621f62570ebb03ffc6036e9d4eb21854f7c878994236516e',  # Clave segura generada
    'PERMANENT_SESSION_LIFETIME': 3600 * 8,  # 8 horas
    'SESSION_COOKIE_NAME': 'aleph70_session',
    'SESSION_COOKIE_HTTPONLY': True,
    'SESSION_COOKIE_SAMESITE': 'Lax',
    'SESSION_COOKIE_PATH': '/',  # Cookies disponibles en todas las rutas
    'SESSION_COOKIE_SECURE': False  # True solo si usas HTTPS
}

# Configuración de seguridad
SECURITY_CONFIG = {
    'MAX_LOGIN_ATTEMPTS': 5,
    'LOCKOUT_DURATION': 900,  # 15 minutos en segundos
    'PASSWORD_MIN_LENGTH': 8,
    'REQUIRE_PASSWORD_CHANGE_DAYS': 90,
    'SESSION_TIMEOUT_WARNING': 300  # 5 minutos antes de expirar
}

# Rutas públicas (no requieren autenticación)
PUBLIC_ROUTES = [
    '/login',
    '/LOGIN.html',
    '/api/auth/login',
    '/api/auth/logout',
    '/static/',
    '/favicon.ico'
]

# Rutas de administración (solo superadmin)
ADMIN_ROUTES = [
    '/api/admin/',
    '/ADMIN_PERMISOS.html',
    '/ADMIN_CONFIG_EMPRESA.html'
]

# Logos por defecto
DEFAULT_LOGOS = {
    'header': '/static/logos/default_header.png',
    'factura': '/static/logos/default_factura.png'
}

# Configuración de branding por defecto
DEFAULT_BRANDING = {
    'color_primario': '#2c3e50',
    'color_secundario': '#3498db',
    'logo_header': DEFAULT_LOGOS['header'],
    'logo_factura': DEFAULT_LOGOS['factura']
}

# Configuración de Google Auth
GOOGLE_AUTH_CONFIG = {
    'CLIENT_ID': 'YOUR_GOOGLE_CLIENT_ID' # REEMPLAZAR CON ID REAL DE GOOGLE CLOUD CONSOLE
}

# Módulos del sistema con configuración
MODULOS_SISTEMA = {
    'facturas': {
        'nombre': 'Facturas',
        'ruta': '/GESTION_FACTURAS.html',
        'icono': '📋',
        'permisos_disponibles': ['ver', 'crear', 'editar', 'eliminar', 'anular', 'exportar']
    },
    'tickets': {
        'nombre': 'Tickets',
        'ruta': '/GESTION_TICKETS.html',
        'icono': '🧾',
        'permisos_disponibles': ['ver', 'crear', 'editar', 'eliminar', 'exportar']
    },
    'proformas': {
        'nombre': 'Proformas',
        'ruta': '/GESTION_PROFORMAS.html',
        'icono': '📄',
        'permisos_disponibles': ['ver', 'crear', 'editar', 'eliminar', 'exportar']
    },
    'productos': {
        'nombre': 'Productos',
        'ruta': '/GESTION_PRODUCTOS.html',
        'icono': '📦',
        'permisos_disponibles': ['ver', 'crear', 'editar', 'eliminar']
    },
    'contactos': {
        'nombre': 'Contactos',
        'ruta': '/GESTION_CONTACTOS.html',
        'icono': '👥',
        'permisos_disponibles': ['ver', 'crear', 'editar', 'eliminar', 'exportar']
    },
    'gastos': {
        'nombre': 'Gastos',
        'ruta': '/CONSULTA_GASTOS.html',
        'icono': '💳',
        'permisos_disponibles': ['ver', 'crear', 'editar', 'eliminar', 'exportar']
    },
    'conciliacion': {
        'nombre': 'Conciliación',
        'ruta': '/conciliacion.html',
        'icono': '✅',
        'permisos_disponibles': ['ver', 'crear', 'editar']
    },
    'estadisticas': {
        'nombre': 'Estadísticas',
        'ruta': '/estadisticas.html',
        'icono': '📊',
        'permisos_disponibles': ['ver', 'exportar']
    }
}

# Plantillas de permisos predefinidas
PLANTILLAS_PERMISOS = {
    'admin': {
        'nombre': 'Administrador Total',
        'descripcion': 'Acceso completo a todos los módulos',
        'permisos': {
            'ver': True,
            'crear': True,
            'editar': True,
            'eliminar': True,
            'anular': True,
            'exportar': True
        }
    },
    'usuario': {
        'nombre': 'Usuario Normal',
        'descripcion': 'Acceso estándar sin eliminaciones',
        'permisos': {
            'ver': True,
            'crear': True,
            'editar': True,
            'eliminar': False,
            'anular': False,
            'exportar': True
        }
    },
    'lectura': {
        'nombre': 'Solo Lectura',
        'descripcion': 'Solo puede consultar información',
        'permisos': {
            'ver': True,
            'crear': False,
            'editar': False,
            'eliminar': False,
            'anular': False,
            'exportar': True
        }
    },
    'contabilidad': {
        'nombre': 'Contabilidad',
        'descripcion': 'Acceso a módulos financieros',
        'modulos_permitidos': ['facturas', 'gastos', 'estadisticas', 'conciliacion'],
        'permisos': {
            'ver': True,
            'crear': False,
            'editar': False,
            'eliminar': False,
            'anular': False,
            'exportar': True
        }
    }
}

def obtener_db_empresa(empresa_id=None):
    """
    Obtiene la ruta de la BD de una empresa desde el emisor.json
    Si no existe, hace fallback a la tabla empresas (compatibilidad)
    """
    import sqlite3
    import json
    from flask import session
    
    if empresa_id is None:
        empresa_id = session.get('empresa_id')
    
    if not empresa_id:
        logger.warning("No se especificó empresa_id y no hay sesión activa")
        return None
    
    try:
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT codigo, db_path FROM empresas WHERE id = ? AND activa = 1', (empresa_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            logger.error(f"No se encontró empresa con id={empresa_id}")
            return None
        
        codigo = result[0]
        db_path_tabla = result[1]
        
        # Intentar leer db_path desde emisor.json (método principal)
        emisor_path = os.path.join(BASE_DIR, 'static', 'emisores', f'{codigo}_emisor.json')
        
        if os.path.exists(emisor_path):
            try:
                with open(emisor_path, 'r', encoding='utf-8') as f:
                    emisor_data = json.load(f)
                    db_path_json = emisor_data.get('db_path')
                    
                    if db_path_json and os.path.exists(db_path_json):
                        logger.debug(f"BD obtenida desde emisor.json: {db_path_json}")
                        return db_path_json
                    else:
                        logger.warning(f"db_path en emisor.json no existe o es inválido, usando fallback")
            except Exception as e:
                logger.warning(f"Error leyendo emisor.json: {e}, usando fallback")
        
        # Fallback: usar db_path de la tabla (compatibilidad con estructura antigua)
        if db_path_tabla and os.path.exists(db_path_tabla):
            logger.debug(f"BD obtenida desde tabla (fallback): {db_path_tabla}")
            return db_path_tabla
        
        logger.error(f"No se encontró BD válida para empresa {codigo} (id={empresa_id})")
        return None
        
    except Exception as e:
        logger.error(f"Error obteniendo BD de empresa: {e}", exc_info=True)
        return None

def inicializar_bd_usuarios():
    """
    Inicializa la base de datos de usuarios si no existe
    """
    import sqlite3
    
    if os.path.exists(DB_USUARIOS_PATH):
        logger.info("Base de datos de usuarios ya existe")
        return True
    
    try:
        logger.info("Creando base de datos de usuarios...")
        
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(DB_USUARIOS_PATH), exist_ok=True)
        
        # Leer y ejecutar script SQL
        script_path = os.path.join(BASE_DIR, 'db', 'init_multiempresa.sql')
        with open(script_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        cursor.executescript(sql_script)
        conn.commit()
        conn.close()
        
        logger.info("✅ Base de datos de usuarios creada exitosamente")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creando BD de usuarios: {e}", exc_info=True)
        return False

# Inicializar BD al importar el módulo
if not os.path.exists(DB_USUARIOS_PATH):
    logger.info("Detectada primera ejecución del sistema multiempresa")
    inicializar_bd_usuarios()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Aplicación Flask refactorizada - Aleph70
Sistema de facturación y gestión empresarial

Versión refactorizada con arquitectura modular basada en Blueprints
"""

import os
from dotenv import load_dotenv
# Cargar variables de entorno desde .env
load_dotenv()

from flask import Flask, request, make_response, session, send_from_directory
from flask_cors import CORS
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge
from werkzeug.middleware.proxy_fix import ProxyFix
import logging
from logger_config import get_logger

# Sistema Multiempresa
from multiempresa_config import SESSION_CONFIG, inicializar_bd_usuarios

# Importar todos los blueprints
from auth_routes import auth_bp
from empresas_api import empresas_bp
from admin_routes import admin_bp
from plantillas_routes import plantillas_bp
from usuario_api import usuario_bp
from avatares_api import avatares_bp
from dashboard_routes import dashboard_bp
from gastos import gastos_bp
from estadisticas_gastos_routes import estadisticas_gastos_bp
from conciliacion import conciliacion_bp

# Nuevos blueprints refactorizados
from routes.productos_routes import productos_bp
from routes.contactos_routes import contactos_bp
from routes.facturas_routes import facturas_bp
from routes.tickets_routes import tickets_bp
from routes.system_routes import system_bp
from routes.presupuestos_routes import presupuestos_bp
from routes.proformas_routes import proformas_bp
from routes.facturas_recibidas_routes import facturas_recibidas_bp
from routes.batch_routes import batch_bp
from public_routes import public_bp

# Middlewares
from auth_middleware import login_required, require_admin, require_permission

logger = get_logger('aleph70.app')

# Versión de la aplicación
APP_VERSION = '1.3.1-legacy-support'

# =====================================
# CONFIGURACIÓN DE LA APLICACIÓN
# =====================================

def create_app():
    """Factory function para crear la aplicación Flask"""
    
    # Crear instancia de Flask
    application = Flask(__name__, 
                       template_folder='templates',
                       static_folder='static')
    
    # Configuración CORS
    CORS(application, supports_credentials=True, 
         origins=['https://*.trycloudflare.com', 'http://localhost:*', 'http://192.168.*:*'])
    
    # Configurar para proxy reverso (Cloudflare, nginx, etc)
    application.wsgi_app = ProxyFix(application.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    # Configuración de sesiones
    application.config.update(SESSION_CONFIG)
    
    # Configuración de límite de carga (20MB)
    max_upload_mb = int(os.getenv('MAX_CONTENT_LENGTH_MB', '200'))
    application.config['MAX_CONTENT_LENGTH'] = max_upload_mb * 1024 * 1024
    
    # Inicializar base de datos de usuarios
    inicializar_bd_usuarios()
    
    # Configurar logging
    setup_logging()
    
    # Registrar middlewares
    register_middlewares(application)
    
    @application.route('/favicon.ico')
    def favicon():
        """Ruta para el favicon"""
        return send_from_directory(os.path.join(application.root_path, 'static'),
                                   'favicon.ico', mimetype='image/vnd.microsoft.icon')

    # Registrar blueprints
    register_blueprints(application)
    
    # Configurar manejo de errores
    setup_error_handlers(application)
    
    logger.info(f"🚀 Aplicación Flask inicializada - Versión {APP_VERSION}")
    
    return application


def setup_logging():
    """Configura el sistema de logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )


def register_middlewares(app):
    """Registra middlewares de la aplicación"""
    
    @app.before_request
    def before_request():
        """Middleware ejecutado antes de cada request"""
        # Log de requests para depuración
        logger.info(f"REQUEST INCOMING: {request.method} {request.path}")
        
        # Headers para permitir cookies cross-origin (preflight)
        if request.method == "OPTIONS":
            response = make_response()
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add('Access-Control-Allow-Headers', "*")
            response.headers.add('Access-Control-Allow-Methods', "*")
            response.headers.add('Access-Control-Allow-Credentials', "true")
            return response
        
        # Log de requests (solo en desarrollo)
        if os.getenv('FLASK_ENV') == 'development':
            logger.debug(f"Request: {request.method} {request.path}")

    @app.after_request
    def after_request(response):
        """Middleware ejecutado después de cada request"""
        # Detectar el origen de la petición
        origin = request.headers.get('Origin', '')
        
        # Lista de dominios permitidos
        allowed_origins = [
            'https://127.0.0.1',
            'http://127.0.0.1',
            'https://localhost',
            'http://localhost'
        ]
        
        # Permitir cualquier subdominio de trycloudflare.com
        if '.trycloudflare.com' in origin:
            allowed_origins.append(origin)
        
        # Permitir IPs locales
        if '192.168.' in origin or '10.' in origin or '172.' in origin:
            allowed_origins.append(origin)
        
        # Configurar headers CORS
        if origin in allowed_origins or any(allowed in origin for allowed in ['.trycloudflare.com', 'localhost', '127.0.0.1']):
            response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
            response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        
        # Headers de seguridad
        response.headers.add('X-Content-Type-Options', 'nosniff')
        response.headers.add('X-Frame-Options', 'SAMEORIGIN')
        response.headers.add('X-XSS-Protection', '1; mode=block')
        
        # Cache control para recursos estáticos
        if request.path.startswith('/static/'):
            response.headers.add('Cache-Control', 'public, max-age=3600')
        
        return response


def register_blueprints(app):
    """Registra todos los blueprints de la aplicación"""
    
    # Blueprints existentes del sistema multiempresa
    app.register_blueprint(auth_bp)  # Sistema de autenticación
    app.register_blueprint(empresas_bp)  # Gestión de empresas
    app.register_blueprint(admin_bp)  # Sistema de administración
    app.register_blueprint(plantillas_bp)  # Plantillas personalizadas
    app.register_blueprint(usuario_bp)
    app.register_blueprint(avatares_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(gastos_bp)
    app.register_blueprint(estadisticas_gastos_bp)
    app.register_blueprint(conciliacion_bp)
    
    # Nuevos blueprints refactorizados
    app.register_blueprint(public_bp)          # Rutas públicas (landing page, registro)
    app.register_blueprint(system_bp)          # Rutas de sistema (/config.json, /api/version, etc.)
    app.register_blueprint(productos_bp)       # Rutas de productos y franjas
    app.register_blueprint(contactos_bp)       # Rutas de contactos
    app.register_blueprint(facturas_bp)        # Rutas de facturas
    app.register_blueprint(tickets_bp)         # Rutas de tickets
    app.register_blueprint(presupuestos_bp)    # Rutas de presupuestos
    app.register_blueprint(proformas_bp)       # Rutas de proformas
    app.register_blueprint(facturas_recibidas_bp) # Rutas de facturas recibidas y proveedores
    app.register_blueprint(batch_bp)           # Rutas de procesos batch (admin)
    
    logger.info("✅ Todos los blueprints registrados correctamente")


def setup_error_handlers(app):
    """Configura manejadores de errores globales"""
    
    @app.errorhandler(RequestEntityTooLarge)
    def request_entity_too_large(error):
        return {'error': 'Archivo demasiado grande', 'status': 413}, 413

    @app.errorhandler(404)
    def not_found_error(error):
        return {'error': 'Recurso no encontrado', 'status': 404}, 404
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return {'error': 'Acceso denegado', 'status': 403}, 403
    
    @app.errorhandler(401)
    def unauthorized_error(error):
        return {'error': 'No autorizado', 'status': 401}, 401
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Error interno del servidor: {error}")
        return {'error': 'Error interno del servidor', 'status': 500}, 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        if isinstance(error, HTTPException):
            code = getattr(error, 'code', 500) or 500
            description = getattr(error, 'description', None)
            message = description if description else 'Error HTTP'
            return {'error': message, 'status': code}, code
        logger.error(f"Excepción no manejada: {error}", exc_info=True)
        return {'error': 'Error inesperado', 'details': str(error), 'status': 500}, 500


# =====================================
# INICIALIZACIÓN DE LA APLICACIÓN
# =====================================

# Crear la aplicación
application = create_app()
app = application

logger.info("📦 Aplicación refactorizada lista para producción")

if __name__ == '__main__':
    # Solo para desarrollo local
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_ENV') == 'development'
    )

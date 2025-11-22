#!/usr/bin/env python3
"""
Configuración de Rate Limiting para las APIs
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import request
import os

def get_real_ip():
    """Obtener la IP real del cliente (considerando proxies)"""
    # Verificar headers de proxy en orden de prioridad
    headers_to_check = [
        'X-Real-IP',
        'X-Forwarded-For',
        'X-Client-IP',
        'CF-Connecting-IP',  # Cloudflare
        'True-Client-IP'      # Cloudflare Enterprise
    ]
    
    for header in headers_to_check:
        ip = request.headers.get(header)
        if ip:
            # X-Forwarded-For puede contener múltiples IPs
            if ',' in ip:
                return ip.split(',')[0].strip()
            return ip.strip()
    
    # Fallback a IP directa
    return request.remote_addr or '127.0.0.1'

def create_limiter(app):
    """Crear y configurar el limiter para la aplicación Flask"""
    
    # Configuración base
    limiter = Limiter(
        app=app,
        key_func=get_real_ip,
        default_limits=["1000 per hour", "100 per minute"],  # Límites globales
        storage_uri=os.environ.get('REDIS_URL', 'memory://'),  # Usar Redis si disponible
        strategy="fixed-window",
        headers_enabled=True,  # Incluir headers de rate limit en respuesta
    )
    
    # Configurar mensajes de error personalizados
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return {
            'success': False,
            'error': 'Demasiadas peticiones. Por favor, intente más tarde.',
            'retry_after': e.description
        }, 429
    
    return limiter

# Decoradores específicos para diferentes tipos de endpoints
class RateLimits:
    """Límites predefinidos para diferentes tipos de operaciones"""
    
    # APIs de solo lectura - más permisivas
    READ = "100 per minute"
    
    # APIs de escritura - más restrictivas
    WRITE = "30 per minute"
    
    # APIs de autenticación - muy restrictivas
    AUTH = "5 per minute"
    
    # APIs de búsqueda/consulta - moderadas
    SEARCH = "60 per minute"
    
    # APIs de reportes/exportación - limitadas
    EXPORT = "10 per minute"
    
    # APIs críticas/costosas - muy limitadas
    CRITICAL = "5 per minute"
    
    # APIs públicas (sin auth) - estrictas
    PUBLIC = "20 per minute"

# Función helper para aplicar rate limiting condicional
def apply_rate_limit(limit_type=None, override=None):
    """
    Aplicar rate limiting basado en el tipo de operación
    
    Args:
        limit_type: Tipo de límite de RateLimits
        override: String de límite personalizado (ej: "10 per minute")
    """
    if override:
        return override
    
    if limit_type:
        return getattr(RateLimits, limit_type, RateLimits.READ)
    
    return RateLimits.READ

# Ejemplo de uso con decoradores
"""
from rate_limiter import create_limiter, RateLimits

# En app.py:
limiter = create_limiter(app)

# En las rutas:
@app.route('/api/login', methods=['POST'])
@limiter.limit(RateLimits.AUTH)
def login():
    pass

@app.route('/api/export/pdf')
@limiter.limit(RateLimits.EXPORT)
def export_pdf():
    pass

@app.route('/api/productos')
@limiter.limit(RateLimits.READ)
def get_productos():
    pass
"""

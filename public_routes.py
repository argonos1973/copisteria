"""
Routes para servir el sitio web público (landing page)
"""

from flask import Blueprint, send_from_directory, redirect, url_for
import os

# Crear blueprint para las rutas públicas
public_bp = Blueprint('public', __name__)

# Directorio público
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), 'public')

@public_bp.route('/')
def home():
    """Redirigir al index de la landing page"""
    return send_from_directory(PUBLIC_DIR, 'index.html')

@public_bp.route('/landing')
def landing():
    """Página de inicio pública"""
    return send_from_directory(PUBLIC_DIR, 'index.html')

@public_bp.route('/public/<path:filename>')
def serve_public(filename):
    """Servir archivos estáticos del sitio público"""
    return send_from_directory(PUBLIC_DIR, filename)

# Para archivos CSS, JS e imágenes con rutas directas
@public_bp.route('/css/<path:filename>')
def serve_css(filename):
    """Servir archivos CSS"""
    return send_from_directory(os.path.join(PUBLIC_DIR, 'css'), filename)

@public_bp.route('/js/<path:filename>')
def serve_js(filename):
    """Servir archivos JavaScript"""
    return send_from_directory(os.path.join(PUBLIC_DIR, 'js'), filename)

@public_bp.route('/images/<path:filename>')
def serve_images(filename):
    """Servir imágenes"""
    # Si no existe la imagen, usar placeholder
    image_path = os.path.join(PUBLIC_DIR, 'images', filename)
    if not os.path.exists(image_path):
        # Devolver una imagen placeholder SVG
        return '''
        <svg width="800" height="600" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" style="stop-color:#667eea;stop-opacity:1" />
                    <stop offset="100%" style="stop-color:#764ba2;stop-opacity:1" />
                </linearGradient>
            </defs>
            <rect width="800" height="600" fill="url(#bg)"/>
            <text x="400" y="280" font-family="Arial" font-size="24" fill="white" text-anchor="middle">
                Aleph70 - Captura de Pantalla
            </text>
            <text x="400" y="320" font-family="Arial" font-size="16" fill="white" opacity="0.8" text-anchor="middle">
                Sistema de Gestión Empresarial
            </text>
        </svg>
        ''', 200, {'Content-Type': 'image/svg+xml'}
    return send_from_directory(os.path.join(PUBLIC_DIR, 'images'), filename)

@public_bp.route('/assets/<path:filename>')
def serve_assets(filename):
    """Servir assets (logos, favicon, etc)"""
    assets_path = os.path.join(PUBLIC_DIR, 'assets', filename)
    
    # Si es logo.png y no existe, usar el SVG
    if filename == 'logo.png' and not os.path.exists(assets_path):
        return redirect('/assets/logo.svg')
    
    # Si es favicon.png y no existe, crear uno simple
    if filename == 'favicon.png' and not os.path.exists(assets_path):
        return '''
        <svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <linearGradient id="fav" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" style="stop-color:#667eea;stop-opacity:1" />
                    <stop offset="100%" style="stop-color:#764ba2;stop-opacity:1" />
                </linearGradient>
            </defs>
            <rect width="32" height="32" rx="6" fill="url(#fav)"/>
            <text x="16" y="22" font-family="Arial" font-size="18" font-weight="bold" fill="white" text-anchor="middle">A</text>
        </svg>
        ''', 200, {'Content-Type': 'image/svg+xml'}
    
    return send_from_directory(os.path.join(PUBLIC_DIR, 'assets'), filename)

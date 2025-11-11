"""
Routes para servir el sitio web público (landing page)
"""

from flask import Blueprint, send_from_directory, redirect, url_for, request, jsonify
import os
import sqlite3
import secrets
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from auth_middleware import hash_password
from dotenv import load_dotenv
import logging

# Cargar variables de entorno
load_dotenv()

logger = logging.getLogger(__name__)

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


# Configuración de email (usando las mismas variables que email_utils.py)
EMAIL_CONFIG = {
    'smtp_server': os.getenv('SMTP_SERVER', 'smtp.ionos.es'),
    'smtp_port': int(os.getenv('SMTP_PORT', '465')),
    'smtp_username': os.getenv('SMTP_USERNAME', 'info@aleph70.com'),
    'smtp_password': os.getenv('SMTP_PASSWORD', ''),
    'sender_email': os.getenv('SMTP_FROM', 'info@aleph70.com'),
    'enabled': os.getenv('EMAIL_ENABLED', 'true').lower() == 'true',
    'use_ssl': True  # IONOS usa SSL en puerto 465
}

DB_USUARIOS_PATH = 'db/usuarios_sistema.db'


def enviar_email_verificacion(email, nombre, token):
    """Enviar email de verificación al usuario"""
    if not EMAIL_CONFIG['enabled']:
        logger.info(f"Email deshabilitado. Token de verificación para {email}: {token}")
        return True
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Verifica tu cuenta en Aleph70'
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = email
        
        # URL de verificación
        verify_url = f"http://localhost:5002/api/public/verify-email?token={token}"
        
        # HTML del email
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
              <h2 style="color: #667eea;">¡Bienvenido a Aleph70, {nombre}!</h2>
              <p>Gracias por registrarte en nuestro sistema de gestión empresarial.</p>
              <p>Para activar tu cuenta, por favor haz clic en el siguiente enlace:</p>
              <p style="text-align: center; margin: 30px 0;">
                <a href="{verify_url}" 
                   style="background-color: #667eea; color: white; padding: 12px 30px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                  Verificar mi cuenta
                </a>
              </p>
              <p style="color: #666; font-size: 14px;">
                Si no puedes hacer clic en el botón, copia y pega este enlace en tu navegador:<br>
                <a href="{verify_url}">{verify_url}</a>
              </p>
              <p style="color: #666; font-size: 14px;">
                Este enlace expirará en 24 horas.
              </p>
              <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
              <p style="color: #999; font-size: 12px;">
                Si no solicitaste esta cuenta, puedes ignorar este email.
              </p>
            </div>
          </body>
        </html>
        """
        
        part = MIMEText(html, 'html')
        msg.attach(part)
        
        # Enviar email usando SSL (como email_utils.py)
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'], context=context) as server:
            server.login(EMAIL_CONFIG['smtp_username'], EMAIL_CONFIG['smtp_password'])
            server.send_message(msg)
        
        logger.info(f"Email de verificación enviado a {email}")
        return True
        
    except Exception as e:
        logger.error(f"Error enviando email a {email}: {e}")
        return False


@public_bp.route('/api/public/register', methods=['POST'])
def register_user():
    """
    Endpoint público para registro de nuevos usuarios
    Crea usuario admin sin empresa asignada
    """
    try:
        data = request.json
        
        # Validar datos requeridos
        required_fields = ['nombre', 'apellidos', 'email', 'telefono', 'password', 'password_confirm']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'El campo {field} es requerido'}), 400
        
        # Validar que las contraseñas coincidan
        if data['password'] != data['password_confirm']:
            return jsonify({'error': 'Las contraseñas no coinciden'}), 400
        
        # Validar longitud de contraseña
        if len(data['password']) < 6:
            return jsonify({'error': 'La contraseña debe tener al menos 6 caracteres'}), 400
        
        nombre_completo = f"{data['nombre']} {data['apellidos']}"
        email = data['email'].lower().strip()
        telefono = data['telefono'].strip()
        password = data['password']
        
        # Generar username único basado en el email
        username = email.split('@')[0]
        
        # Conectar a la base de datos
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        # Verificar si el email ya existe
        cursor.execute('SELECT id FROM usuarios WHERE email = ?', (email,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Este email ya está registrado'}), 400
        
        # Verificar si el username ya existe, si es así, agregar número
        base_username = username
        counter = 1
        while True:
            cursor.execute('SELECT id FROM usuarios WHERE username = ?', (username,))
            if not cursor.fetchone():
                break
            username = f"{base_username}{counter}"
            counter += 1
        
        # Generar token de verificación
        verification_token = secrets.token_urlsafe(32)
        token_expiry = datetime.now() + timedelta(hours=24)
        
        # Hash de la contraseña
        password_hash = hash_password(password)
        
        # Insertar usuario
        cursor.execute('''
            INSERT INTO usuarios (
                username, password_hash, nombre_completo, email, telefono,
                activo, es_superadmin, verification_token, token_expiry,
                fecha_creacion
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            username,
            password_hash,
            nombre_completo,
            email,
            telefono,
            0,  # Inactivo hasta verificar email
            0,  # No es superadmin
            verification_token,
            token_expiry.isoformat()
        ))
        
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        
        # Enviar email de verificación
        email_sent = enviar_email_verificacion(email, data['nombre'], verification_token)
        
        logger.info(f"Usuario registrado: {username} ({email}) - ID: {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Usuario registrado correctamente. Por favor verifica tu email.',
            'username': username,
            'email_sent': email_sent,
            'verification_required': True
        }), 201
        
    except Exception as e:
        logger.error(f"Error en registro de usuario: {e}", exc_info=True)
        return jsonify({'error': 'Error al registrar usuario'}), 500


@public_bp.route('/api/public/verify-email', methods=['GET'])
def verify_email():
    """Verificar email del usuario mediante token"""
    try:
        token = request.args.get('token')
        
        if not token:
            return jsonify({'error': 'Token no proporcionado'}), 400
        
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        # Buscar usuario por token
        cursor.execute('''
            SELECT id, username, email, token_expiry
            FROM usuarios
            WHERE verification_token = ? AND activo = 0
        ''', (token,))
        
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({'error': 'Token inválido o usuario ya verificado'}), 400
        
        user_id, username, email, token_expiry = user
        
        # Verificar si el token ha expirado
        if datetime.now() > datetime.fromisoformat(token_expiry):
            conn.close()
            return jsonify({'error': 'El token ha expirado. Solicita un nuevo enlace de verificación'}), 400
        
        # Activar usuario
        cursor.execute('''
            UPDATE usuarios
            SET activo = 1, verification_token = NULL, token_expiry = NULL
            WHERE id = ?
        ''', (user_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Usuario verificado: {username} ({email})")
        
        # Redirigir al login con mensaje de éxito
        return redirect('/LOGIN.html?verified=true')
        
    except Exception as e:
        logger.error(f"Error verificando email: {e}", exc_info=True)
        return jsonify({'error': 'Error al verificar email'}), 500

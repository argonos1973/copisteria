#!/usr/bin/env python3
"""
Utilidades de seguridad para Aleph70
- Protección CSRF
- Sanitización XSS
"""

import bleach
from flask_wtf.csrf import CSRFProtect, generate_csrf
from markupsafe import Markup
import re

# Inicializar CSRF
csrf = CSRFProtect()

# ============================================================================
# CONFIGURACIÓN DE SANITIZACIÓN XSS
# ============================================================================

# Tags HTML permitidos (whitelist)
ALLOWED_TAGS = [
    'a', 'abbr', 'acronym', 'b', 'blockquote', 'br', 'code', 'em', 
    'i', 'li', 'ol', 'p', 'strong', 'ul', 'span', 'div', 'h1', 'h2', 
    'h3', 'h4', 'h5', 'h6', 'table', 'thead', 'tbody', 'tr', 'th', 'td'
]

# Atributos permitidos por tag
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target'],
    'abbr': ['title'],
    'acronym': ['title'],
    'span': ['class', 'style'],
    'div': ['class', 'style'],
    'table': ['class', 'border'],
    'th': ['colspan', 'rowspan'],
    'td': ['colspan', 'rowspan']
}

# Protocolos permitidos en URLs
ALLOWED_PROTOCOLS = ['http', 'https', 'mailto', 'tel']

# ============================================================================
# FUNCIONES DE SANITIZACIÓN
# ============================================================================

def sanitize_html(text, allow_html=False):
    """
    Sanitiza texto para prevenir XSS.
    
    Args:
        text: Texto a sanitizar
        allow_html: Si True, permite tags HTML seguros. Si False, escapa todo.
    
    Returns:
        Texto sanitizado
    """
    if text is None:
        return None
    
    if not isinstance(text, str):
        text = str(text)
    
    if allow_html:
        # Permitir HTML seguro
        return bleach.clean(
            text,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            protocols=ALLOWED_PROTOCOLS,
            strip=True
        )
    else:
        # Escapar todo HTML
        return bleach.clean(text, tags=[], attributes={}, strip=True)


def sanitize_input(text):
    """
    Sanitiza input de usuario básico (sin HTML).
    Elimina caracteres peligrosos y limpia espacios.
    """
    if text is None:
        return None
    
    if not isinstance(text, str):
        text = str(text)
    
    # Eliminar tags HTML
    text = bleach.clean(text, tags=[], attributes={}, strip=True)
    
    # Limpiar espacios múltiples
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def sanitize_filename(filename):
    """
    Sanitiza nombre de archivo para prevenir path traversal.
    """
    if filename is None:
        return None
    
    # Eliminar caracteres peligrosos
    filename = re.sub(r'[^\w\s\-\.]', '', filename)
    # Eliminar path traversal
    filename = filename.replace('..', '')
    # Limpiar espacios
    filename = filename.strip()
    
    return filename


def sanitize_dict(data, fields_to_sanitize=None):
    """
    Sanitiza campos específicos de un diccionario.
    
    Args:
        data: Diccionario con datos
        fields_to_sanitize: Lista de campos a sanitizar (None = todos los strings)
    
    Returns:
        Diccionario con campos sanitizados
    """
    if not isinstance(data, dict):
        return data
    
    sanitized = {}
    for key, value in data.items():
        if fields_to_sanitize is None or key in fields_to_sanitize:
            if isinstance(value, str):
                sanitized[key] = sanitize_input(value)
            elif isinstance(value, dict):
                sanitized[key] = sanitize_dict(value, fields_to_sanitize)
            else:
                sanitized[key] = value
        else:
            sanitized[key] = value
    
    return sanitized


# ============================================================================
# MIDDLEWARE PARA SANITIZACIÓN AUTOMÁTICA
# ============================================================================

def sanitize_request_data(app):
    """
    Middleware que sanitiza automáticamente los datos de request.
    Aplicar con: sanitize_request_data(app)
    """
    @app.before_request
    def _sanitize_request():
        from flask import request, g
        
        # Sanitizar form data
        if request.form:
            g.sanitized_form = sanitize_dict(dict(request.form))
        
        # Sanitizar JSON data
        if request.is_json:
            try:
                json_data = request.get_json(silent=True)
                if json_data:
                    g.sanitized_json = sanitize_dict(json_data)
            except:
                pass


# ============================================================================
# FUNCIONES AUXILIARES PARA TEMPLATES
# ============================================================================

def init_security(app):
    """
    Inicializa todas las protecciones de seguridad en la app Flask.
    
    Uso:
        from security_utils import init_security
        init_security(app)
    """
    # Inicializar CSRF
    csrf.init_app(app)
    
    # Añadir función csrf_token a templates
    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf)
    
    # Aplicar sanitización automática en requests
    @app.before_request
    def auto_sanitize_request():
        from flask import request, g
        
        # Sanitizar parámetros GET
        if request.args:
            g.safe_args = {}
            for key, value in request.args.items():
                if isinstance(value, str):
                    g.safe_args[key] = sanitize_input(value)
                else:
                    g.safe_args[key] = value
        
        # Sanitizar JSON body
        if request.is_json:
            try:
                json_data = request.get_json(silent=True)
                if json_data and isinstance(json_data, dict):
                    g.safe_json = sanitize_dict(json_data)
            except:
                pass
    
    app.logger.info("✅ Seguridad inicializada: CSRF + Sanitización XSS automática")
    
    return csrf

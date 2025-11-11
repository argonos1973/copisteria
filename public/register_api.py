#!/usr/bin/env python3
"""
API endpoints para el registro de nuevos usuarios desde la landing page
"""

from flask import Blueprint, request, jsonify
import sqlite3
import hashlib
import secrets
from datetime import datetime
import re
import os

# Blueprint para las rutas de registro
register_bp = Blueprint('register', __name__)

# Configuración de base de datos
DB_PATH = '/var/www/html/db/usuarios.db'

def init_db():
    """Inicializar tablas para registro de usuarios"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Tabla de registros pendientes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registros_pendientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            apellidos TEXT NOT NULL,
            empresa TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            telefono TEXT,
            password_hash TEXT NOT NULL,
            token_confirmacion TEXT,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            confirmado BOOLEAN DEFAULT 0,
            plan TEXT DEFAULT 'profesional',
            activo BOOLEAN DEFAULT 0
        )
    ''')
    
    # Tabla de contactos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contactos_web (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT NOT NULL,
            mensaje TEXT NOT NULL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atendido BOOLEAN DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()

def hash_password(password):
    """Hashear contraseña con SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def validate_email(email):
    """Validar formato de email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def generate_token():
    """Generar token único para confirmación"""
    return secrets.token_urlsafe(32)

@register_bp.route('/api/register', methods=['POST'])
def register_user():
    """Endpoint para registro de nuevos usuarios"""
    try:
        data = request.get_json()
        
        # Validar campos requeridos
        required_fields = ['name', 'surname', 'company', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'El campo {field} es requerido'}), 400
        
        # Validar email
        if not validate_email(data['email']):
            return jsonify({'error': 'Email inválido'}), 400
        
        # Validar contraseña
        if len(data['password']) < 6:
            return jsonify({'error': 'La contraseña debe tener al menos 6 caracteres'}), 400
        
        # Conectar a base de datos
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verificar si el email ya existe
        cursor.execute('SELECT id FROM registros_pendientes WHERE email = ?', (data['email'],))
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Este email ya está registrado'}), 409
        
        # Generar token de confirmación
        token = generate_token()
        
        # Insertar nuevo registro
        cursor.execute('''
            INSERT INTO registros_pendientes 
            (nombre, apellidos, empresa, email, telefono, password_hash, token_confirmacion, plan)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['name'],
            data['surname'],
            data['company'],
            data['email'],
            data.get('phone', ''),
            hash_password(data['password']),
            token,
            'profesional'  # Plan por defecto
        ))
        
        conn.commit()
        registro_id = cursor.lastrowid
        conn.close()
        
        # TODO: Enviar email de confirmación
        # send_confirmation_email(data['email'], token)
        
        return jsonify({
            'success': True,
            'message': 'Registro exitoso. Revisa tu email para confirmar tu cuenta.',
            'id': registro_id
        }), 201
        
    except Exception as e:
        print(f"Error en registro: {e}")
        return jsonify({'error': 'Error al procesar el registro'}), 500

@register_bp.route('/api/contact', methods=['POST'])
def contact_form():
    """Endpoint para formulario de contacto"""
    try:
        data = request.form
        
        # Validar campos
        if not data.get('name') or not data.get('email') or not data.get('message'):
            return jsonify({'error': 'Todos los campos son requeridos'}), 400
        
        # Guardar en base de datos
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO contactos_web (nombre, email, mensaje)
            VALUES (?, ?, ?)
        ''', (
            data['name'],
            data['email'],
            data['message']
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Mensaje recibido correctamente'
        }), 200
        
    except Exception as e:
        print(f"Error en contacto: {e}")
        return jsonify({'error': 'Error al enviar el mensaje'}), 500

@register_bp.route('/api/confirm/<token>', methods=['GET'])
def confirm_email(token):
    """Confirmar email con token"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Buscar registro por token
        cursor.execute('''
            SELECT id, email FROM registros_pendientes 
            WHERE token_confirmacion = ? AND confirmado = 0
        ''', (token,))
        
        registro = cursor.fetchone()
        
        if not registro:
            conn.close()
            return jsonify({'error': 'Token inválido o ya confirmado'}), 400
        
        # Marcar como confirmado
        cursor.execute('''
            UPDATE registros_pendientes 
            SET confirmado = 1, token_confirmacion = NULL
            WHERE id = ?
        ''', (registro[0],))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Email confirmado exitosamente',
            'email': registro[1]
        }), 200
        
    except Exception as e:
        print(f"Error en confirmación: {e}")
        return jsonify({'error': 'Error al confirmar email'}), 500

@register_bp.route('/api/plans', methods=['GET'])
def get_plans():
    """Obtener información de planes disponibles"""
    plans = [
        {
            'id': 'basico',
            'name': 'Básico',
            'price': 29,
            'features': [
                'Hasta 100 tickets/mes',
                '1 usuario',
                'Soporte por email',
                'Backup diario'
            ]
        },
        {
            'id': 'profesional',
            'name': 'Profesional',
            'price': 59,
            'features': [
                'Tickets ilimitados',
                '5 usuarios',
                'Soporte prioritario',
                'Backup cada hora',
                'Facturación electrónica',
                'Integraciones'
            ],
            'popular': True
        },
        {
            'id': 'empresa',
            'name': 'Empresa',
            'price': 99,
            'features': [
                'Todo ilimitado',
                'Usuarios ilimitados',
                'Soporte 24/7',
                'Backup continuo',
                'Multi-empresa',
                'Personalización'
            ]
        }
    ]
    
    return jsonify({'plans': plans}), 200

# Inicializar base de datos al importar
if __name__ == '__main__':
    init_db()
    print("Base de datos de registro inicializada")

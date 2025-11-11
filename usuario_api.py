# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify, session
import sqlite3
import os
import json

from logger_config import get_logger
from auth_middleware import login_required
from multiempresa_config import DB_USUARIOS_PATH

logger = get_logger(__name__)

usuario_bp = Blueprint('usuario', __name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@usuario_bp.route('/api/usuario/perfil', methods=['PUT'])
@login_required
def actualizar_perfil():
    """Actualiza datos del perfil del usuario (email, teléfono)"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        email = data.get('email')
        telefono = data.get('telefono')
        
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        # Actualizar datos del usuario
        cursor.execute('''
            UPDATE usuarios 
            SET email = ?, telefono = ?
            WHERE id = ?
        ''', (email, telefono, user_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Perfil actualizado para usuario {user_id}")
        
        return jsonify({
            'success': True,
            'mensaje': 'Perfil actualizado correctamente'
        }), 200
        
    except Exception as e:
        logger.error(f"Error actualizando perfil: {e}", exc_info=True)
        return jsonify({'error': f'Error actualizando perfil: {str(e)}'}), 500


@usuario_bp.route('/api/usuario/plantilla', methods=['PUT'])
@login_required
def cambiar_plantilla_usuario():
    """Cambia la plantilla del usuario en usuario_empresa"""
    try:
        user_id = session.get('user_id')
        empresa_id = session.get('empresa_id')
        data = request.get_json()
        
        plantilla = data.get('plantilla')
        
        if not plantilla:
            return jsonify({'error': 'Plantilla requerida'}), 400
        
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        # Actualizar plantilla del usuario
        cursor.execute('''
            UPDATE usuario_empresa 
            SET plantilla = ? 
            WHERE usuario_id = ? AND empresa_id = ?
        ''', (plantilla, user_id, empresa_id))
        
        conn.commit()
        conn.close()
        
        # Cargar y devolver el JSON del tema
        tema_json = None
        try:
            import json as json_module
            plantilla_path = os.path.join(BASE_DIR, 'static', 'plantillas', f'{plantilla}.json')
            if os.path.exists(plantilla_path):
                with open(plantilla_path, 'r', encoding='utf-8') as f:
                    tema_json = json_module.load(f)
                logger.info(f"Plantilla {plantilla} cargada para usuario {user_id}")
        except Exception as e:
            logger.error(f"Error cargando plantilla {plantilla}: {e}")
        
        logger.info(f"Plantilla de usuario {user_id} cambiada a: {plantilla}")
        
        response_data = {
            'success': True,
            'mensaje': 'Plantilla cambiada correctamente',
            'plantilla': plantilla
        }
        
        if tema_json:
            response_data['colores'] = tema_json
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error cambiando plantilla: {e}", exc_info=True)
        return jsonify({'error': f'Error cambiando plantilla: {str(e)}'}), 500


@usuario_bp.route('/api/usuario/plantillas', methods=['GET'])
@login_required
def obtener_plantillas_disponibles():
    """Obtiene la lista de plantillas disponibles leyendo el directorio"""
    try:
        plantillas_dir = os.path.join(BASE_DIR, 'static', 'plantillas')
        plantillas = []
        
        # Leer todos los archivos .json del directorio
        if os.path.exists(plantillas_dir):
            for filename in os.listdir(plantillas_dir):
                if filename.endswith('.json'):
                    plantilla_id = filename[:-5]  # Quitar extensión .json
                    plantilla_path = os.path.join(plantillas_dir, filename)
                    
                    try:
                        with open(plantilla_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            
                            # Extraer información del JSON
                            nombre = data.get('name', plantilla_id.replace('_', ' ').title())
                            icono = data.get('meta', {}).get('icon', '🎨')
                            
                            # Función para resolver referencias
                            def resolver_referencia(valor, data):
                                if isinstance(valor, str) and valor.startswith('{') and valor.endswith('}'):
                                    # Quitar llaves y obtener la ruta
                                    path = valor[1:-1].split('.')
                                    
                                    # Navegar por el objeto para obtener el valor
                                    resultado = data
                                    for parte in path:
                                        if isinstance(resultado, dict) and parte in resultado:
                                            resultado = resultado[parte]
                                        else:
                                            return valor  # Devolver como está si no se puede resolver
                                    
                                    # Resolver recursivamente si el resultado es otra referencia
                                    if isinstance(resultado, str) and resultado.startswith('{'):
                                        return resolver_referencia(resultado, data)
                                    
                                    return resultado
                                return valor
                            
                            # Extraer colores para preview
                            colores_preview = {}
                            if 'semantic' in data:
                                semantic = data['semantic']
                                colores_preview['background'] = resolver_referencia(semantic.get('bg', '#ffffff'), data)
                                colores_preview['text'] = resolver_referencia(semantic.get('text', '#000000'), data)
                                colores_preview['primary'] = resolver_referencia(semantic.get('primary', '#3498db'), data)
                                colores_preview['border'] = resolver_referencia(semantic.get('border', '#ddd'), data)
                            else:
                                # Valores por defecto para plantillas sin estructura semantic
                                colores_preview = {
                                    'background': '#ffffff',
                                    'text': '#000000',
                                    'primary': '#3498db',
                                    'border': '#ddd'
                                }
                            
                            plantillas.append({
                                'id': plantilla_id,
                                'nombre': nombre,
                                'icono': icono,
                                'colores': colores_preview
                            })
                    except Exception as e:
                        logger.warning(f"Error leyendo plantilla {filename}: {e}")
                        continue
        
        # Ordenar alfabéticamente por nombre
        plantillas.sort(key=lambda x: x['nombre'])
        
        logger.info(f"Plantillas disponibles: {len(plantillas)}")
        
        return jsonify({
            'success': True,
            'plantillas': plantillas
        }), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo plantillas: {e}", exc_info=True)
        return jsonify({'error': f'Error obteniendo plantillas: {str(e)}'}), 500

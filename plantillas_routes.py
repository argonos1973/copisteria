"""
Rutas API para gestión de plantillas personalizadas de colores
"""
from flask import Blueprint, request, jsonify
from functools import wraps
import sqlite3
import os
import json
from logger_config import get_logger

logger = get_logger(__name__)

plantillas_bp = Blueprint('plantillas', __name__, url_prefix='/api/plantillas')

DB_PATH = '/var/www/html/db/usuarios_sistema.db'

def login_required(f):
    """Decorador simplificado para requerir login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Por ahora, permitir acceso sin validación estricta
        # TODO: Implementar validación de sesión real
        return f(*args, **kwargs)
    return decorated_function

@plantillas_bp.route('/personalizadas', methods=['GET'])
def obtener_plantillas_personalizadas():
    """
    Obtener todas las plantillas personalizadas
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM plantillas_personalizadas
            ORDER BY fecha_creacion DESC
        ''')
        
        rows = cursor.fetchall()
        plantillas = []
        
        for row in rows:
            plantilla = {
                'id': row['id'],
                'nombre': row['nombre'],
                'descripcion': row['descripcion'],
                'plantilla_base': row['plantilla_base'],
                'color_primario': row['color_primario'],
                'color_secundario': row['color_secundario'],
                'color_success': row['color_success'],
                'color_warning': row['color_warning'],
                'color_danger': row['color_danger'],
                'color_info': row['color_info'],
                'color_button': row['color_button'],
                'color_button_hover': row['color_button_hover'],
                'color_button_text': row['color_button_text'],
                'color_app_bg': row['color_app_bg'],
                'color_header_bg': row['color_header_bg'],
                'color_header_text': row['color_header_text'],
                'color_grid_header': row['color_grid_header'],
                'color_grid_hover': row['color_grid_hover'],
                'color_input_bg': row['color_input_bg'],
                'color_input_text': row['color_input_text'],
                'color_input_border': row['color_input_border'],
                'color_select_bg': row['color_select_bg'],
                'color_select_text': row['color_select_text'],
                'color_select_border': row['color_select_border'],
                'color_disabled_bg': row['color_disabled_bg'],
                'color_disabled_text': row['color_disabled_text'],
                'color_submenu_bg': row['color_submenu_bg'],
                'color_submenu_text': row['color_submenu_text'],
                'color_submenu_hover': row['color_submenu_hover'],
                'color_grid_bg': row['color_grid_bg'],
                'color_grid_text': row['color_grid_text'],
                'color_icon': row['color_icon'],
                'fecha_creacion': row['fecha_creacion']
            }
            plantillas.append(plantilla)
        
        conn.close()
        
        logger.info(f"Plantillas personalizadas obtenidas: {len(plantillas)}")
        return jsonify({'success': True, 'plantillas': plantillas})
        
    except Exception as e:
        logger.error(f"Error obteniendo plantillas personalizadas: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@plantillas_bp.route('/personalizadas', methods=['POST'])
def guardar_plantilla_personalizada():
    """
    Guardar una nueva plantilla personalizada
    """
    try:
        data = request.json
        
        # Validar datos requeridos
        if not data.get('nombre'):
            return jsonify({'success': False, 'error': 'Nombre requerido'}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verificar si ya existe una plantilla con ese nombre
        cursor.execute('SELECT id FROM plantillas_personalizadas WHERE nombre = ?', (data['nombre'],))
        existe = cursor.fetchone()
        
        if existe:
            # Actualizar plantilla existente
            cursor.execute('''
                UPDATE plantillas_personalizadas SET
                    descripcion = ?,
                    plantilla_base = ?,
                    color_primario = ?,
                    color_secundario = ?,
                    color_success = ?,
                    color_warning = ?,
                    color_danger = ?,
                    color_info = ?,
                    color_button = ?,
                    color_button_hover = ?,
                    color_button_text = ?,
                    color_app_bg = ?,
                    color_header_bg = ?,
                    color_header_text = ?,
                    color_grid_header = ?,
                    color_grid_hover = ?,
                    color_input_bg = ?,
                    color_input_text = ?,
                    color_input_border = ?,
                    color_select_bg = ?,
                    color_select_text = ?,
                    color_select_border = ?,
                    color_disabled_bg = ?,
                    color_disabled_text = ?,
                    color_submenu_bg = ?,
                    color_submenu_text = ?,
                    color_submenu_hover = ?,
                    color_grid_bg = ?,
                    color_grid_text = ?,
                    color_icon = ?
                WHERE nombre = ?
            ''', (
                data.get('descripcion', ''),
                data.get('plantilla_base', ''),
                data.get('color_primario'),
                data.get('color_secundario'),
                data.get('color_success'),
                data.get('color_warning'),
                data.get('color_danger'),
                data.get('color_info'),
                data.get('color_button'),
                data.get('color_button_hover'),
                data.get('color_button_text'),
                data.get('color_app_bg'),
                data.get('color_header_bg'),
                data.get('color_header_text'),
                data.get('color_grid_header'),
                data.get('color_grid_hover'),
                data.get('color_input_bg'),
                data.get('color_input_text'),
                data.get('color_input_border'),
                data.get('color_select_bg'),
                data.get('color_select_text'),
                data.get('color_select_border'),
                data.get('color_disabled_bg'),
                data.get('color_disabled_text'),
                data.get('color_submenu_bg'),
                data.get('color_submenu_text'),
                data.get('color_submenu_hover'),
                data.get('color_grid_bg'),
                data.get('color_grid_text'),
                data.get('color_icon'),
                data['nombre']
            ))
            
            logger.info(f"Plantilla personalizada actualizada: {data['nombre']}")
        else:
            # Insertar nueva plantilla
            cursor.execute('''
                INSERT INTO plantillas_personalizadas (
                    nombre, descripcion, plantilla_base,
                    color_primario, color_secundario, color_success, color_warning,
                    color_danger, color_info, color_button, color_button_hover,
                    color_button_text, color_app_bg, color_header_bg, color_header_text,
                    color_grid_header, color_grid_hover, color_input_bg, color_input_text,
                    color_input_border, color_select_bg, color_select_text, color_select_border,
                    color_disabled_bg, color_disabled_text, color_submenu_bg, color_submenu_text,
                    color_submenu_hover, color_grid_bg, color_grid_text, color_icon
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['nombre'],
                data.get('descripcion', ''),
                data.get('plantilla_base', ''),
                data.get('color_primario'),
                data.get('color_secundario'),
                data.get('color_success'),
                data.get('color_warning'),
                data.get('color_danger'),
                data.get('color_info'),
                data.get('color_button'),
                data.get('color_button_hover'),
                data.get('color_button_text'),
                data.get('color_app_bg'),
                data.get('color_header_bg'),
                data.get('color_header_text'),
                data.get('color_grid_header'),
                data.get('color_grid_hover'),
                data.get('color_input_bg'),
                data.get('color_input_text'),
                data.get('color_input_border'),
                data.get('color_select_bg'),
                data.get('color_select_text'),
                data.get('color_select_border'),
                data.get('color_disabled_bg'),
                data.get('color_disabled_text'),
                data.get('color_submenu_bg'),
                data.get('color_submenu_text'),
                data.get('color_submenu_hover'),
                data.get('color_grid_bg'),
                data.get('color_grid_text'),
                data.get('color_icon')
            ))
            
            logger.info(f"Nueva plantilla personalizada creada: {data['nombre']}")
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Plantilla guardada correctamente'})
        
    except Exception as e:
        logger.error(f"Error guardando plantilla personalizada: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@plantillas_bp.route('/personalizadas/<int:plantilla_id>', methods=['DELETE'])
def eliminar_plantilla_personalizada(plantilla_id):
    """
    Eliminar una plantilla personalizada
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM plantillas_personalizadas WHERE id = ?', (plantilla_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Plantilla no encontrada'}), 404
        
        conn.commit()
        conn.close()
        
        logger.info(f"Plantilla personalizada eliminada: ID {plantilla_id}")
        return jsonify({'success': True, 'message': 'Plantilla eliminada'})
        
    except Exception as e:
        logger.error(f"Error eliminando plantilla personalizada: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@plantillas_bp.route('/listar', methods=['GET'])
def listar_todas_plantillas():
    """
    Lista todas las plantillas (predefinidas JSON + personalizadas BD)
    """
    try:
        import os
        import json
        
        plantillas = []
        
        # 1. Cargar plantillas predefinidas desde archivos JSON
        ruta_plantillas = '/var/www/html/static/plantillas'
        if os.path.exists(ruta_plantillas):
            for archivo in os.listdir(ruta_plantillas):
                if archivo.endswith('.json'):
                    try:
                        ruta_completa = os.path.join(ruta_plantillas, archivo)
                        with open(ruta_completa, 'r', encoding='utf-8') as f:
                            plantilla_data = json.load(f)
                            plantillas.append({
                                'archivo': archivo.replace('.json', ''),
                                'nombre': plantilla_data.get('nombre', archivo.replace('.json', '')),
                                'descripcion': plantilla_data.get('descripcion', ''),
                                'icon': plantilla_data.get('icon', '📄'),
                                'personalizada': plantilla_data.get('personalizada', False),
                                'basada_en': plantilla_data.get('basada_en', '')
                            })
                    except Exception as e:
                        logger.error(f"Error cargando plantilla {archivo}: {e}")
        
        # 2. Cargar plantillas personalizadas desde BD
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT nombre, descripcion, plantilla_base, fecha_creacion
                FROM plantillas_personalizadas
                ORDER BY fecha_creacion DESC
            ''')
            
            rows = cursor.fetchall()
            for row in rows:
                plantillas.append({
                    'archivo': f"custom_{row['nombre'].replace(' ', '_')}",
                    'nombre': row['nombre'],
                    'descripcion': row['descripcion'] or f"Basada en {row['plantilla_base']}",
                    'icon': '🎨',
                    'personalizada': True,
                    'basada_en': row['plantilla_base']
                })
            
            conn.close()
        except Exception as e:
            logger.error(f"Error cargando plantillas personalizadas de BD: {e}")
        
        logger.info(f"Total plantillas listadas: {len(plantillas)}")
        return jsonify({'plantillas': plantillas})
        
    except Exception as e:
        logger.error(f"Error listando plantillas: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


"""
API para gestión de avatares predefinidos
"""

from flask import Blueprint, jsonify
import os
import logging

logger = logging.getLogger(__name__)

# Crear blueprint
avatares_bp = Blueprint('avatares', __name__)

# Directorio de avatares predefinidos
AVATARES_DIR = os.path.join(os.path.dirname(__file__), 'static', 'avatares')

@avatares_bp.route('/api/avatares/listar', methods=['GET'])
def listar_avatares():
    """
    Lista todos los avatares predefinidos disponibles
    """
    try:
        # Crear directorio si no existe
        if not os.path.exists(AVATARES_DIR):
            os.makedirs(AVATARES_DIR)
            logger.info(f"Directorio de avatares creado: {AVATARES_DIR}")
            return jsonify([]), 200
        
        # Listar archivos de imagen
        avatares = []
        extensiones_validas = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp')
        
        for archivo in os.listdir(AVATARES_DIR):
            if archivo.lower().endswith(extensiones_validas):
                avatares.append(archivo)
        
        avatares.sort()  # Ordenar alfabéticamente
        
        logger.info(f"Avatares disponibles: {len(avatares)}")
        return jsonify(avatares), 200
        
    except Exception as e:
        logger.error(f"Error listando avatares: {e}", exc_info=True)
        return jsonify({'error': 'Error al listar avatares'}), 500

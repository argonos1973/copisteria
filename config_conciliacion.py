"""
Módulo independiente para gestión de configuración de conciliación.
No depende de Flask ni otros módulos web, puede usarse desde scripts cron.
"""

import json
import os
from datetime import datetime

CONFIG_FILE = '/var/www/html/config/conciliacion_config.json'

def inicializar_config_conciliacion():
    """Crear archivo de configuración si no existe con valores por defecto"""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    
    config_default = {
        "tolerancia_euros": 3.0,
        "descripcion": "Tolerancia máxima en euros para conciliación automática",
        "fecha_modificacion": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_default, f, indent=4, ensure_ascii=False)

def get_tolerancia_conciliacion():
    """Obtener tolerancia de conciliación desde archivo JSON"""
    try:
        if not os.path.exists(CONFIG_FILE):
            inicializar_config_conciliacion()
        
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        return config.get('tolerancia_euros', 3.0)
    except Exception as e:
        # Si hay error, usar valor por defecto
        print(f"Error obteniendo tolerancia: {e}")
        return 3.0  # Valor por defecto en caso de error

def set_tolerancia_conciliacion(nueva_tolerancia):
    """Actualizar tolerancia de conciliación en archivo JSON"""
    try:
        if not os.path.exists(CONFIG_FILE):
            inicializar_config_conciliacion()
        
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        config['tolerancia_euros'] = nueva_tolerancia
        config['fecha_modificacion'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error actualizando tolerancia: {e}")
        raise

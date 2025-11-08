import json
import os
import sqlite3
from flask import session


def cargar_datos_emisor(codigo_empresa=None):
    """
    Carga los datos del emisor desde el archivo JSON de la empresa.
    
    Args:
        codigo_empresa: Código de la empresa. Si no se proporciona, se obtiene de la sesión.
        
    Returns:
        dict: Diccionario con los datos del emisor.
    """
    # Si no se proporciona código, intentar obtenerlo de la sesión
    if codigo_empresa is None:
        codigo_empresa = session.get('codigo_empresa', '')
        
    if not codigo_empresa:
        # Fallback: intentar obtener de empresa_id
        empresa_id = session.get('empresa_id')
        if empresa_id:
            try:
                from multiempresa_config import DB_USUARIOS_PATH
                conn = sqlite3.connect(DB_USUARIOS_PATH)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT codigo FROM empresas WHERE id = ?', (empresa_id,))
                row = cursor.fetchone()
                conn.close()
                if row:
                    codigo_empresa = row['codigo']
            except Exception:
                pass
    
    # Construir ruta al archivo JSON del emisor
    base_dir = os.path.dirname(os.path.abspath(__file__))
    emisor_path = os.path.join(base_dir, 'static', 'emisores', f'{codigo_empresa}_emisor.json')
    
    if os.path.exists(emisor_path):
        with open(emisor_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # Si no existe el archivo JSON, retornar datos vacíos
    return {
        'nombre': '',
        'nif': '',
        'direccion': '',
        'cp': '',
        'ciudad': '',
        'provincia': '',
        'pais': 'ESP',
        'email': '',
        'telefono': ''
    }

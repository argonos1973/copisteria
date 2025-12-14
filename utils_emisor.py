import json
import os
import sqlite3
from flask import session

# Caché global para datos de emisores: {codigo_empresa: {'data': dict, 'mtime': float}}
_EMISOR_CACHE = {}


def resetear_cache_emisor(codigo_empresa=None):
    """
    Resetea la caché del emisor.
    
    Args:
        codigo_empresa: Código de la empresa a resetear. Si es None, resetea todo.
    """
    global _EMISOR_CACHE
    if codigo_empresa:
        if codigo_empresa in _EMISOR_CACHE:
            del _EMISOR_CACHE[codigo_empresa]
    else:
        _EMISOR_CACHE = {}


def cargar_datos_emisor(codigo_empresa=None):
    """
    Carga los datos del emisor desde el archivo JSON de la empresa.
    Usa caché en memoria con invalidación por mtime (fecha modificación archivo).
    
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
    emisor_path = os.path.join(base_dir, 'emisores', f'{codigo_empresa}_emisor.json')
    
    if os.path.exists(emisor_path):
        try:
            # Obtener tiempo de modificación actual
            current_mtime = os.path.getmtime(emisor_path)
            
            # Verificar si tenemos datos en caché y si el archivo no ha cambiado
            if codigo_empresa in _EMISOR_CACHE:
                cached = _EMISOR_CACHE[codigo_empresa]
                if cached['mtime'] == current_mtime:
                    # Retornar copia para evitar modificaciones accidentales del caché
                    return cached['data'].copy()
            
            # Si no está en caché o cambió el archivo, cargar de disco
            with open(emisor_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Actualizar caché
                _EMISOR_CACHE[codigo_empresa] = {
                    'data': data,
                    'mtime': current_mtime
                }
                return data.copy()
                
        except Exception as e:
            # En caso de error (lectura, json inválido), loggear y retornar vacío o caché previo
            print(f"Error cargando emisor {codigo_empresa}: {e}")
            if codigo_empresa in _EMISOR_CACHE:
                return _EMISOR_CACHE[codigo_empresa]['data'].copy()
    
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

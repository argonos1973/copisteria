import json
import os
import subprocess
from datetime import datetime

from flask import Blueprint, jsonify

# Crear blueprint para las rutas de scraping
scraping_bp = Blueprint('scraping', __name__)

@scraping_bp.route('/ejecutar_scrapeo', methods=['POST'])
def ejecutar_scrapeo():
    """
    Endpoint para ejecutar el script de scraping de forma asíncrona
    """
    try:
        # Ejecutar el script de scraping en un subproceso
        # Usar python3 con el entorno virtual adecuado
        python_path = '/var/www/html/venv/bin/python'
        script_path = '/var/www/html/scrapeo.py'
        
        # Verificar que los archivos existen
        if not os.path.exists(python_path):
            return jsonify({'exito': False, 'error': f'No se encontró Python en {python_path}'}), 500
        
        if not os.path.exists(script_path):
            return jsonify({'exito': False, 'error': f'No se encontró el script en {script_path}'}), 500
        
        # Ejecutar el script usando xvfb-run y redirigir el log a /tmp/scrapeo.log
        cmd = f"/usr/bin/xvfb-run -s '-screen 0 1920x1080x24' {python_path} {script_path} >> /tmp/scrapeo.log 2>&1"
        try:
            proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as sub_err:
            return jsonify({'exito': False, 'error': f'Error lanzando el proceso: {str(sub_err)}'}), 500

        
        # Registrar el inicio del proceso
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open('/var/www/html/log_scraping.txt', 'a') as f:
            f.write(f"[{timestamp}] Iniciado proceso de scraping\n")
            
        return jsonify({
            'exito': True, 
            'mensaje': 'Proceso de actualización bancaria iniciado correctamente'
        })
        
    except Exception as e:
        # Registrar el error
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open('/var/www/html/log_scraping.txt', 'a') as f:
            f.write(f"[{timestamp}] Error al iniciar el scraping: {str(e)}\n")
            
        return jsonify({
            'exito': False,
            'error': f'Error al ejecutar el script: {str(e)}'
        }), 500

@scraping_bp.route('/estado_scraping', methods=['GET'])
def estado_scraping():
    """
    Endpoint para verificar si el proceso de scraping está en ejecución
    """
    try:
        # Verificar si hay algún proceso de python ejecutando scrapeo.py
        resultado = subprocess.run(
            ["pgrep", "-f", "scrapeo.py"], 
            capture_output=True, 
            text=True
        )
        
        # Si hay salida, significa que el proceso está en ejecución
        en_ejecucion = bool(resultado.stdout.strip())
        
        return jsonify({
            'exito': True,
            'en_ejecucion': en_ejecucion
        })
        
    except Exception as e:
        return jsonify({
            'exito': False,
            'error': f'Error al verificar el estado: {str(e)}'
        }), 500

import sys
from flask import Flask, session
import logging

sys.path.append('/var/www/html')
logging.basicConfig(level=logging.DEBUG)

from app import create_app
import tickets
from db_utils import get_db_connection

app = create_app()
app.config['SECRET_KEY'] = 'test'

with app.app_context():
    # Simular sesión apuntando a la BD correcta (caca.db según logs)
    # Hack para db_utils: si no hay request context o session, usa default o variable entorno
    import os
    os.environ['EMPRESA_DB_PATH'] = '/var/www/html/db/caca/caca.db'
    
    print("--- Probando consulta de ticket 8170 ---")
    try:
        # Llamar a la función directamente
        response = tickets.obtener_ticket_con_detalles(8170)
        
        # response es un objeto Response de Flask (jsonify)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Datos (parcial):", str(response.json)[:200])
        else:
            print("Error:", response.json)
            
    except Exception as e:
        print(f"Excepción: {e}")
        import traceback
        traceback.print_exc()

#!/home/sami/santander/venv/bin/python

# Resto del script original...
# Solo modificamos la parte final que llama a scrapeo.py

import logging
import re
import os
import time
import sys
import json

# El resto del contenido original se mantiene igual
# ...

# Modificamos solo la parte final que ejecuta scrapeo.py
    # Cerrar navegador y finalizar
    try:
        context.close()
    except Exception:
        try:
            browser.close()
        except Exception:
            pass
    print("Navegador cerrado. Script finalizado.")
    
    # Llamar al script scrapeo.py al finalizar
    try:
        import subprocess
        print("Ejecutando scrapeo.py...")
        subprocess.call(["/home/sami/santander/venv/bin/python", "/home/sami/santander/scrapeo.py"])
    except Exception as e:
        print(f"Error al ejecutar scrapeo.py: {e}")

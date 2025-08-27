#!/bin/bash

# Modificar únicamente la llamada a scrapeo.py al final del archivo
sed -i 's|subprocess.call.*|        subprocess.call(["/home/sami/santander/venv/bin/python", "/home/sami/santander/scrapeo.py"])|' /home/sami/santander/api_scraping.py

echo "Corrección completada"

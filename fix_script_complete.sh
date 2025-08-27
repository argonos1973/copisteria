#!/bin/bash
# Script para corregir completamente el archivo

# Crear una copia de respaldo
cp /home/sami/santander/api_scraping.py /home/sami/santander/api_scraping.py.bak

# Corregir la línea del intérprete
sed -i '1s|^.*$|#!/home/sami/santander/venv/bin/python|' /home/sami/santander/api_scraping.py

# Corregir las líneas problemáticas con comillas para las cadenas
sed -i 's|os\.execl(/home/sami/santander/venv/bin/python|os.execl(sys.executable, sys.executable|g' /home/sami/santander/api_scraping.py
sed -i 's|/home/sami/santander/venv/bin/python = sys\.executable|python_exe = sys.executable|g' /home/sami/santander/api_scraping.py

# Corregir la llamada a scrapeo.py
sed -i 's|subprocess\.call\(\[.*\]\)|subprocess.call(["/home/sami/santander/venv/bin/python", "/home/sami/santander/scrapeo.py"])|' /home/sami/santander/api_scraping.py

echo "Script corregido completamente"

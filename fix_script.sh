#!/bin/bash
# Script para corregir solo la parte específica del archivo que necesita cambiar

# Crear una copia de respaldo
cp /home/sami/santander/api_scraping.py /home/sami/santander/api_scraping.py.bak

# Corregir solo la línea específica que llama a scrapeo.py
sed -i '1s|#!/var/www/html/venv/bin//home/sami/santander/venv/bin/python|#!/home/sami/santander/venv/bin/python|' /home/sami/santander/api_scraping.py
sed -i 's|subprocess\.call\(\[.\+\]\)|subprocess.call(["/home/sami/santander/venv/bin/python", "/home/sami/santander/scrapeo.py"])|' /home/sami/santander/api_scraping.py
sed -i 's|^        /home/sami/santander/venv/bin/python = sys\.executable|        python_exe = sys.executable|g' /home/sami/santander/api_scraping.py
sed -i 's|        os\.execl(/home/sami/santander/venv/bin/python,|        os.execl(python_exe, python_exe,|g' /home/sami/santander/api_scraping.py

echo "Script corregido correctamente"

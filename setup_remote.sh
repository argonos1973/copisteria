#!/bin/bash

# Script para configurar el entorno y cron en el servidor remoto
# Debe ejecutarse después de copiar api_scraping.py y scrapeo.py a /tmp/

# Crear directorio de producción
mkdir -p /opt/santander

# Mover los scripts a su ubicación
mv /tmp/api_scraping.py /tmp/scrapeo.py /opt/santander/

# Crear entorno virtual e instalar dependencias
python3 -m venv /opt/santander/venv
/opt/santander/venv/bin/pip install playwright
/opt/santander/venv/bin/playwright install

# Crear crontab para ejecución a las 15:00 y 20:00
cat > /tmp/santander_cron << EOF
0 15,20 * * * sami cd /opt/santander && /opt/santander/venv/bin/python /opt/santander/api_scraping.py > /tmp/santander_descarga_\$(date +\%Y\%m\%d_\%H\%M\%S).log 2>&1
EOF

sudo mv /tmp/santander_cron /etc/cron.d/santander_produccion
sudo chmod 644 /etc/cron.d/santander_produccion

echo "Configuración completada. Ahora ejecutando el script..."

# Ejecutar el script
cd /opt/santander
/opt/santander/venv/bin/python /opt/santander/api_scraping.py

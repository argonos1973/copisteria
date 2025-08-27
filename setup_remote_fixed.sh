#!/bin/bash

# Script para configurar el entorno y cron en el servidor remoto usando el directorio home
# Debe ejecutarse después de copiar api_scraping.py y scrapeo.py a /tmp/

# Crear directorio de santander en el home de sami
mkdir -p ~/santander

# Mover los scripts a su ubicación
mv /tmp/api_scraping.py /tmp/scrapeo.py ~/santander/

# Crear entorno virtual e instalar dependencias
python3 -m venv ~/santander/venv
~/santander/venv/bin/pip install playwright
~/santander/venv/bin/playwright install

# Crear archivo temporal para el crontab
cat > /tmp/santander_cron << EOF
0 15,20 * * * sami cd \$HOME/santander && \$HOME/santander/venv/bin/python \$HOME/santander/api_scraping.py > /tmp/santander_descarga_\$(date +\%Y\%m\%d_\%H\%M\%S).log 2>&1
EOF

# Solicitar al usuario que use sudo para mover el archivo cron
echo "Por favor, ejecuta el siguiente comando como sudo para configurar el crontab:"
echo "sudo mv /tmp/santander_cron /etc/cron.d/santander_produccion && sudo chmod 644 /etc/cron.d/santander_produccion"

echo "Configuración completada. Ahora ejecutando el script..."

# Ejecutar el script
cd ~/santander
~/santander/venv/bin/python ~/santander/api_scraping.py

#!/bin/bash
# Script para reiniciar Gunicorn después de cambios en el código

echo "🔄 Reiniciando Gunicorn..."

# Matar todos los procesos de Gunicorn
sudo killall -9 gunicorn 2>/dev/null

# Esperar 2 segundos
sleep 2

# Iniciar Gunicorn en background
cd /var/www/html
nohup /var/www/html/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:5002 \
    --timeout 120 \
    --access-logfile /var/www/html/logs/gunicorn-access.log \
    --error-logfile /var/www/html/logs/gunicorn-error.log \
    app:app > /dev/null 2>&1 &

# Esperar 2 segundos
sleep 2

# Verificar que está corriendo
if pgrep -f "gunicorn.*app:app" > /dev/null; then
    echo "✅ Gunicorn reiniciado correctamente"
    echo "📊 Procesos activos:"
    ps aux | grep gunicorn | grep -v grep | wc -l
else
    echo "❌ Error: Gunicorn no está corriendo"
    exit 1
fi

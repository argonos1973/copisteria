#!/bin/bash
# Script para iniciar Gunicorn
# Uso: ./start_gunicorn.sh

cd /var/www/html

# Matar procesos Gunicorn previos
pkill -f gunicorn

# Activar entorno virtual
source venv/bin/activate

# Verificar permisos de logs
mkdir -p logs
chmod 775 logs
chown sami:www-data logs

echo "🚀 Iniciando Gunicorn..."

# Iniciar Gunicorn en background con logs
nohup gunicorn -w 2 -b 0.0.0.0:5000 app:app \
    --timeout 300 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --preload \
    --log-level info \
    --access-logfile logs/gunicorn_access.log \
    --error-logfile logs/gunicorn_error.log \
    --capture-output \
    --pid gunicorn.pid > /dev/null 2>&1 &

sleep 3

# Verificar que se inició correctamente
if pgrep -f gunicorn > /dev/null; then
    echo "✅ Gunicorn iniciado correctamente"
    echo "   PID: $(cat gunicorn.pid 2>/dev/null || echo 'N/A')"
    echo "   Puerto: 5000"
    echo "   Workers: 2"
    echo "   URL: http://localhost:5000"
    
    # Test de conectividad
    if curl -s -o /dev/null http://localhost:5000; then
        echo "   🌐 Servicio respondiendo correctamente"
    else
        echo "   ⚠️  Servicio iniciado pero no responde aún"
    fi
else
    echo "❌ Error iniciando Gunicorn"
    echo "   Ver logs en: logs/gunicorn_error.log"
fi

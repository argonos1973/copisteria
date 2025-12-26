#!/bin/bash
# Script para reiniciar Gunicorn - PRODUCCIÓN
# Solo usa systemctl, nunca nohup

echo "🔄 Reiniciando Gunicorn..."
sudo systemctl restart gunicorn
sleep 2

if systemctl is-active --quiet gunicorn; then
    echo "✅ Gunicorn reiniciado correctamente"
    echo "📊 Procesos activos:"
    ps aux | grep gunicorn | grep -v grep | wc -l
else
    echo "❌ Error: Gunicorn no está corriendo"
    sudo systemctl status gunicorn --no-pager
    exit 1
fi

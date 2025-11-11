#!/bin/bash
# Script para ver la URL de acceso actual

echo "==========================================="
echo "   🌐 URL DE ACCESO A TU SISTEMA"
echo "==========================================="
echo ""

# Obtener la URL del log
URL=$(grep "https://" /tmp/cloudflared_output.log 2>/dev/null | tail -1 | grep -oE "https://[a-zA-Z0-9\.\-]+\.trycloudflare\.com")

if [ -z "$URL" ]; then
    echo "❌ El tunnel no está activo"
    echo ""
    echo "Iniciando tunnel..."
    pkill -f cloudflared 2>/dev/null
    nohup cloudflared tunnel --url http://localhost:5002 > /tmp/cloudflared_output.log 2>&1 &
    sleep 5
    URL=$(grep "https://" /tmp/cloudflared_output.log | tail -1 | grep -oE "https://[a-zA-Z0-9\.\-]+\.trycloudflare\.com")
fi

if [ ! -z "$URL" ]; then
    echo "✅ TU SISTEMA ESTÁ ONLINE"
    echo ""
    echo "📱 Landing Page:"
    echo "   $URL/"
    echo ""
    echo "🔐 Login Sistema:"
    echo "   $URL/frontend/LOGIN.html"
    echo ""
    echo "👤 Credenciales:"
    echo "   Usuario: admin"
    echo "   Clave:   admin123"
    echo ""
    echo "==========================================="
    echo "💡 Copia la URL y ábrela en tu navegador"
    echo "==========================================="
else
    echo "❌ Error al obtener la URL"
    echo "Intenta ejecutar manualmente:"
    echo "cloudflared tunnel --url http://localhost:5002"
fi

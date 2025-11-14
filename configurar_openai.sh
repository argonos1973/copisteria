#!/bin/bash
#
# Script para configurar OpenAI API Key
# Uso: ./configurar_openai.sh
#

echo "╔════════════════════════════════════════════════════════╗"
echo "║  Configuración de OpenAI GPT-4 Vision para OCR        ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Verificar si ya existe una API key
if [ -f /var/www/html/.env ]; then
    if grep -q "OPENAI_API_KEY" /var/www/html/.env; then
        echo "⚠️  Ya existe una API key configurada en .env"
        echo ""
        read -p "¿Deseas reemplazarla? (s/n): " replace
        if [[ ! $replace =~ ^[Ss]$ ]]; then
            echo "❌ Operación cancelada"
            exit 0
        fi
    fi
fi

echo ""
echo "Para obtener una API key:"
echo "1. Ve a: https://platform.openai.com/api-keys"
echo "2. Inicia sesión o crea una cuenta"
echo "3. Click en 'Create new secret key'"
echo "4. Copia la key (empieza con sk-proj-...)"
echo ""

read -sp "Ingresa tu OpenAI API Key: " api_key
echo ""

# Validar formato básico
if [[ ! $api_key =~ ^sk-proj- ]] && [[ ! $api_key =~ ^sk- ]]; then
    echo "❌ Error: La API key no parece válida (debe empezar con 'sk-' o 'sk-proj-')"
    exit 1
fi

# Crear o actualizar .env
if [ -f /var/www/html/.env ]; then
    # Actualizar existente
    if grep -q "OPENAI_API_KEY" /var/www/html/.env; then
        sed -i "s|OPENAI_API_KEY=.*|OPENAI_API_KEY=$api_key|" /var/www/html/.env
    else
        echo "OPENAI_API_KEY=$api_key" >> /var/www/html/.env
    fi
else
    # Crear nuevo
    echo "OPENAI_API_KEY=$api_key" > /var/www/html/.env
fi

# Establecer permisos correctos
sudo chown www-data:www-data /var/www/html/.env
sudo chmod 640 /var/www/html/.env

echo "✅ API Key guardada en /var/www/html/.env"
echo ""

# Exportar para la sesión actual
export OPENAI_API_KEY=$api_key

# Verificar instalación de OpenAI
echo "🔍 Verificando instalación de OpenAI..."
cd /var/www/html
source venv/bin/activate

if python3 -c "import openai" 2>/dev/null; then
    echo "✅ Librería OpenAI instalada correctamente"
else
    echo "❌ Error: Librería OpenAI no encontrada"
    echo "   Instalando..."
    pip install openai
fi

# Probar conexión
echo ""
echo "🧪 Probando conexión con OpenAI API..."

python3 << 'PYTHON_SCRIPT'
import os
try:
    from openai import OpenAI
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ Error: API Key no cargada en entorno")
        exit(1)
    
    client = OpenAI(api_key=api_key)
    # Hacer una llamada simple para verificar
    response = client.models.list()
    print("✅ Conexión exitosa con OpenAI API")
    print(f"   Modelos disponibles: {len(list(response))}")
    
except Exception as e:
    print(f"❌ Error al conectar con OpenAI: {e}")
    exit(1)
PYTHON_SCRIPT

if [ $? -eq 0 ]; then
    echo ""
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║  ✅ CONFIGURACIÓN COMPLETADA EXITOSAMENTE             ║"
    echo "╚════════════════════════════════════════════════════════╝"
    echo ""
    echo "Próximos pasos:"
    echo "1. Reiniciar servicios:"
    echo "   sudo systemctl restart apache2"
    echo "   sudo kill -HUP \$(ps aux | grep gunicorn | grep 'bin/gunicorn' | head -1 | awk '{print \$2}')"
    echo ""
    echo "2. Probar con una imagen:"
    echo "   python3 test_ocr.py /ruta/a/imagen.jpg"
    echo ""
    echo "3. Usar desde la web:"
    echo "   - Ve a Gestión de Contactos"
    echo "   - Click en 'Escanear Datos'"
    echo "   - Sube una tarjeta de visita"
    echo ""
    echo "💰 Costo aproximado: ~$0.01 por imagen"
    echo "📊 Monitorea tu uso en: https://platform.openai.com/usage"
else
    echo ""
    echo "❌ Hubo un error en la configuración"
    echo "   Revisa que la API key sea correcta"
    echo "   y que tengas créditos disponibles en tu cuenta OpenAI"
fi

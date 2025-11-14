#!/bin/bash
#
# Script para configurar procesamiento automático de emails
# Uso: ./configurar_email.sh
#

echo "╔════════════════════════════════════════════════════════╗"
echo "║  Configuración de Procesamiento Automático de Emails  ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Verificar si ya existe configuración
if [ -f /var/www/html/.env ]; then
    if grep -q "EMAIL_USER" /var/www/html/.env; then
        echo "⚠️  Ya existe configuración de email en .env"
        echo ""
        read -p "¿Deseas reemplazarla? (s/n): " replace
        if [[ ! $replace =~ ^[Ss]$ ]]; then
            echo "❌ Operación cancelada"
            exit 0
        fi
    fi
fi

echo ""
echo "Este sistema permite procesar automáticamente contactos"
echo "enviados por email con foto adjunta."
echo ""
echo "Flujo:"
echo "  1. Haces foto de tarjeta con el móvil"
echo "  2. Envías email con asunto 'NUEVO CONTACTO'"
echo "  3. Sistema procesa cada 2 minutos automáticamente"
echo "  4. Contacto creado en base de datos"
echo "  5. Recibes confirmación por email"
echo ""

# Seleccionar proveedor
echo "Selecciona tu proveedor de email:"
echo "  1) Gmail (recomendado)"
echo "  2) Outlook/Hotmail"
echo "  3) Yahoo"
echo "  4) Otro (configuración manual)"
echo ""
read -p "Opción (1-4): " provider

case $provider in
    1)
        IMAP_HOST="imap.gmail.com"
        IMAP_PORT="993"
        SMTP_HOST="smtp.gmail.com"
        SMTP_PORT="587"
        echo ""
        echo "📧 Gmail seleccionado"
        echo ""
        echo "⚠️  IMPORTANTE: Para Gmail necesitas crear una 'App Password'"
        echo ""
        echo "Pasos:"
        echo "  1. Ve a: https://myaccount.google.com/security"
        echo "  2. Habilita 'Verificación en 2 pasos'"
        echo "  3. Ve a: https://myaccount.google.com/apppasswords"
        echo "  4. Selecciona 'Correo' y 'Otro dispositivo'"
        echo "  5. Copia la contraseña de 16 caracteres"
        echo ""
        ;;
    2)
        IMAP_HOST="outlook.office365.com"
        IMAP_PORT="993"
        SMTP_HOST="smtp.office365.com"
        SMTP_PORT="587"
        echo "📧 Outlook/Hotmail seleccionado"
        ;;
    3)
        IMAP_HOST="imap.mail.yahoo.com"
        IMAP_PORT="993"
        SMTP_HOST="smtp.mail.yahoo.com"
        SMTP_PORT="587"
        echo "📧 Yahoo seleccionado"
        ;;
    4)
        echo ""
        read -p "IMAP Host (ej: imap.ejemplo.com): " IMAP_HOST
        read -p "IMAP Port (normalmente 993): " IMAP_PORT
        read -p "SMTP Host (ej: smtp.ejemplo.com): " SMTP_HOST
        read -p "SMTP Port (normalmente 587): " SMTP_PORT
        ;;
    *)
        echo "❌ Opción inválida"
        exit 1
        ;;
esac

# Solicitar credenciales
echo ""
read -p "Email completo (ej: contactos@empresa.com): " email_user
echo ""

if [ "$provider" = "1" ]; then
    read -sp "App Password de Gmail (16 caracteres sin espacios): " email_pass
else
    read -sp "Contraseña del email: " email_pass
fi

echo ""
echo ""

# Asunto a buscar
echo "¿Qué asunto debe tener el email para procesarlo?"
read -p "Asunto (por defecto 'NUEVO CONTACTO'): " asunto
asunto=${asunto:-"NUEVO CONTACTO"}

echo ""
echo "Guardando configuración..."

# Actualizar o agregar al .env
if [ -f /var/www/html/.env ]; then
    # Eliminar configuraciones antiguas si existen
    sed -i '/^EMAIL_USER=/d' /var/www/html/.env
    sed -i '/^EMAIL_PASSWORD=/d' /var/www/html/.env
    sed -i '/^EMAIL_IMAP_HOST=/d' /var/www/html/.env
    sed -i '/^EMAIL_IMAP_PORT=/d' /var/www/html/.env
    sed -i '/^EMAIL_SMTP_HOST=/d' /var/www/html/.env
    sed -i '/^EMAIL_SMTP_PORT=/d' /var/www/html/.env
    sed -i '/^EMAIL_ASUNTO_CONTACTO=/d' /var/www/html/.env
fi

# Agregar nuevas configuraciones
cat >> /var/www/html/.env << EOF

# Configuración de procesamiento automático de emails
EMAIL_USER=$email_user
EMAIL_PASSWORD=$email_pass
EMAIL_IMAP_HOST=$IMAP_HOST
EMAIL_IMAP_PORT=$IMAP_PORT
EMAIL_SMTP_HOST=$SMTP_HOST
EMAIL_SMTP_PORT=$SMTP_PORT
EMAIL_ASUNTO_CONTACTO=$asunto
EOF

sudo chown www-data:www-data /var/www/html/.env
sudo chmod 640 /var/www/html/.env

echo "✅ Configuración guardada en .env"
echo ""

# Probar conexión
echo "🧪 Probando conexión..."
cd /var/www/html
source venv/bin/activate
export EMAIL_USER=$email_user
export EMAIL_PASSWORD=$email_pass
export EMAIL_IMAP_HOST=$IMAP_HOST
export EMAIL_IMAP_PORT=$IMAP_PORT

python3 << PYTHON_SCRIPT
import imaplib
import os

try:
    host = os.getenv('EMAIL_IMAP_HOST')
    port = int(os.getenv('EMAIL_IMAP_PORT'))
    user = os.getenv('EMAIL_USER')
    password = os.getenv('EMAIL_PASSWORD')
    
    print(f"Conectando a {host}:{port}...")
    mail = imaplib.IMAP4_SSL(host, port)
    mail.login(user, password)
    mail.select('INBOX')
    
    # Contar emails
    status, messages = mail.search(None, 'ALL')
    email_ids = messages[0].split()
    
    print(f"✅ Conexión exitosa!")
    print(f"   Emails en bandeja: {len(email_ids)}")
    
    mail.close()
    mail.logout()
    
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
PYTHON_SCRIPT

if [ $? -eq 0 ]; then
    echo ""
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║  ✅ CONFIGURACIÓN COMPLETADA EXITOSAMENTE             ║"
    echo "╚════════════════════════════════════════════════════════╝"
    echo ""
    echo "Próximos pasos:"
    echo ""
    echo "1. Configurar Cron Job (procesamiento automático cada 2 min):"
    echo "   crontab -e"
    echo ""
    echo "   Agrega esta línea:"
    echo "   */2 * * * * cd /var/www/html && /var/www/html/venv/bin/python3 /var/www/html/procesar_emails_contactos.py >> /var/www/html/logs/email_processor.log 2>&1"
    echo ""
    echo "2. Crear directorio de logs:"
    echo "   mkdir -p /var/www/html/logs"
    echo ""
    echo "3. Probar manualmente:"
    echo "   cd /var/www/html"
    echo "   source venv/bin/activate"
    echo "   source .env"
    echo "   python3 procesar_emails_contactos.py"
    echo ""
    echo "4. Enviar email de prueba:"
    echo "   Para: $email_user"
    echo "   Asunto: $asunto"
    echo "   Adjunto: foto_tarjeta.jpg"
    echo ""
    echo "5. Ver logs:"
    echo "   tail -f /var/www/html/logs/email_processor.log"
    echo ""
    echo "📧 Email configurado: $email_user"
    echo "🔍 Busca emails con asunto: '$asunto'"
    echo ""
else
    echo ""
    echo "❌ Hubo un error en la configuración"
    echo "   Verifica las credenciales y vuelve a intentar"
fi

#!/bin/bash
# fix_security.sh - Correcciones de seguridad inmediatas
# Ejecutar como: sudo bash fix_security.sh

set -e

echo "🔐 Aplicando correcciones de seguridad..."

# 1. Bloquear acceso a .env
echo "1️⃣ Bloqueando acceso a .env..."
cat > /etc/apache2/conf-available/block-sensitive.conf << 'EOF'
# Bloquear archivos sensibles
<FilesMatch "^\.env$|^\.git|\.db$|\.sqlite$">
    Require all denied
</FilesMatch>

# Bloquear directorio db
<Directory "/var/www/html/db">
    Require all denied
</Directory>

# Bloquear directorio flask_session
<Directory "/var/www/html/flask_session">
    Require all denied
</Directory>
EOF

a2enconf block-sensitive 2>/dev/null || true
echo "   ✅ Configuración Apache creada"

# 2. Añadir headers de seguridad adicionales
echo "2️⃣ Configurando headers de seguridad..."
cat > /etc/apache2/conf-available/security-headers.conf << 'EOF'
# Headers de seguridad adicionales
<IfModule mod_headers.c>
    Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains" env=HTTPS
    Header always set Referrer-Policy "strict-origin-when-cross-origin"
    Header always set Permissions-Policy "geolocation=(), microphone=(), camera=()"
</IfModule>
EOF

a2enconf security-headers 2>/dev/null || true
a2enmod headers 2>/dev/null || true
echo "   ✅ Headers configurados"

# 3. Verificar permisos de archivos sensibles
echo "3️⃣ Ajustando permisos..."
chmod 600 /var/www/html/.env 2>/dev/null || true
chmod 750 /var/www/html/db 2>/dev/null || true
chown -R www-data:www-data /var/www/html/db 2>/dev/null || true
echo "   ✅ Permisos ajustados"

# 4. Reiniciar Apache
echo "4️⃣ Reiniciando Apache..."
systemctl reload apache2
echo "   ✅ Apache reiniciado"

# 5. Verificación
echo ""
echo "🔍 Verificando correcciones..."
echo ""

# Test .env
HTTP_ENV=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/.env 2>/dev/null || echo "000")
if [ "$HTTP_ENV" = "403" ] || [ "$HTTP_ENV" = "404" ]; then
    echo "   ✅ .env bloqueado (HTTP $HTTP_ENV)"
else
    echo "   ⚠️ .env puede estar accesible (HTTP $HTTP_ENV)"
fi

# Test db
HTTP_DB=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/db/usuarios_sistema.db 2>/dev/null || echo "000")
if [ "$HTTP_DB" = "403" ] || [ "$HTTP_DB" = "404" ]; then
    echo "   ✅ /db/ bloqueado (HTTP $HTTP_DB)"
else
    echo "   ⚠️ /db/ puede estar accesible (HTTP $HTTP_DB)"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ Correcciones inmediatas aplicadas"
echo ""
echo "⚠️  ACCIONES MANUALES PENDIENTES:"
echo "   1. Rotar OPENAI_API_KEY en https://platform.openai.com"
echo "   2. Cambiar SMTP_PASSWORD en el proveedor de email"
echo "   3. Regenerar SECRET_KEY:"
echo "      python3 -c \"import secrets; print(secrets.token_hex(32))\""
echo "   4. Actualizar .env con las nuevas credenciales"
echo "   5. Reiniciar gunicorn: pkill -f gunicorn && ..."
echo "═══════════════════════════════════════════════════════════"

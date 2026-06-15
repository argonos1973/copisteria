#!/bin/bash

# =============================================================================
# CONFIGURACIÓN DEL DESPLIEGUE
# =============================================================================
REMOTE_HOST="192.168.1.55"
REMOTE_USER="sami"
REMOTE_PASS="sami"
REMOTE_DIR="/var/www/html"
VENV_DIR="$REMOTE_DIR/venv"
LOCAL_DIR="/var/www/html"

# Colores para logs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[DEPLOY]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# =============================================================================
# 1. VERIFICACIONES PREVIAS
# =============================================================================
log "Iniciando despliegue a $REMOTE_USER@$REMOTE_HOST..."

# Verificar si sshpass está instalado
if ! command -v sshpass &> /dev/null; then
    warn "sshpass no encontrado. Instalando..."
    sudo apt-get update && sudo apt-get install -y sshpass
fi

# Función wrapper para ejecutar comandos remotos con contraseña
remote_exec() {
    sshpass -p "$REMOTE_PASS" ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" "$1"
}

# Verificar conexión
log "Verificando conexión SSH..."
if remote_exec "echo 'Conexión exitosa'" > /dev/null; then
    log "Conexión establecida correctamente."
else
    error "No se pudo conectar a $REMOTE_HOST. Verifica IP y credenciales."
    exit 1
fi

# =============================================================================
# 2. PREPARACIÓN DEL SERVIDOR REMOTO
# =============================================================================
log "Preparando servidor remoto..."

# Instalar dependencias del sistema
log "Instalando dependencias del sistema (Python, Apache, etc.)..."
# Nota: Se asume que el usuario remoto tiene permisos sudo sin password o usa la misma password
remote_exec "echo '$REMOTE_PASS' | sudo -S apt-get update"
remote_exec "echo '$REMOTE_PASS' | sudo -S apt-get install -y python3 python3-pip python3-venv python3-dev apache2 libapache2-mod-wsgi-py3 rsync poppler-utils tesseract-ocr curl"

# Instalar Cloudflare (cloudflared)
log "Instalando servicio Cloudflare..."
remote_exec "
    if ! command -v cloudflared &> /dev/null; then
        echo 'Descargando cloudflared...'
        curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
        echo '$REMOTE_PASS' | sudo -S dpkg -i cloudflared.deb
        rm cloudflared.deb
        echo '✅ Cloudflare instalado exitosamente'
    else
        echo 'ℹ️ Cloudflare ya está instalado'
    fi
    cloudflared --version
"

# Configurar Túnel Cloudflare automáticamente si existe token
if [ -f "$LOCAL_DIR/.env" ]; then
    CF_TOKEN=$(grep "CLOUDFLARE_TUNNEL_TOKEN" "$LOCAL_DIR/.env" | cut -d '=' -f2 | tr -d '"' | tr -d "'")
    
    if [ ! -z "$CF_TOKEN" ]; then
        log "Configurando túnel Cloudflare..."
        remote_exec "
            echo 'Configurando servicio Cloudflare Tunnel...'
            # Limpiar instalación previa si existe
            echo '$REMOTE_PASS' | sudo -S cloudflared service uninstall 2>/dev/null || true
            
            # Instalar nuevo servicio
            echo '$REMOTE_PASS' | sudo -S cloudflared service install $CF_TOKEN
            
            # Verificar estado
            if systemctl is-active --quiet cloudflared; then
                echo '✅ Túnel Cloudflare configurado y activo'
            else
                echo '⚠️ Túnel instalado pero no activo. Verificando...'
                echo '$REMOTE_PASS' | sudo -S systemctl start cloudflared
            fi
        "
    else
        warn "CLOUDFLARE_TUNNEL_TOKEN no encontrado en .env. El túnel no se configurará automáticamente."
    fi
fi

# Crear directorio destino si no existe
remote_exec "echo '$REMOTE_PASS' | sudo -S mkdir -p $REMOTE_DIR"
remote_exec "echo '$REMOTE_PASS' | sudo -S chown -R $REMOTE_USER:$REMOTE_USER $REMOTE_DIR"

# =============================================================================
# 3. TRANSFERENCIA DE ARCHIVOS
# =============================================================================
log "Transfiriendo archivos..."

# Excluir archivos innecesarios y DATOS (para no sobrescribir producción)
sshpass -p "$REMOTE_PASS" rsync -avz --delete \
    --exclude 'venv' \
    --exclude '__pycache__' \
    --exclude '.git' \
    --exclude '*.log' \
    --exclude 'logs/*' \
    --exclude '.env' \
    --exclude '*.db' \
    --exclude '*.sqlite' \
    --exclude 'db/*' \
    "$LOCAL_DIR/" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/"

# Transferir explícitamente el script de inicialización SQL (estaba excluido por db/*)
sshpass -p "$REMOTE_PASS" scp "$LOCAL_DIR/db/init_multiempresa.sql" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/db/init_multiempresa.sql"

# Transferir .env manualmente si es necesario (o crear uno nuevo)
if [ -f "$LOCAL_DIR/.env" ]; then
    # Verificar que OPENAI_API_KEY existe en el .env local antes de enviar
    if grep -q "OPENAI_API_KEY" "$LOCAL_DIR/.env"; then
        log "✅ Clave GPT-4 Vision detectada en .env"
    else
        warn "⚠️ OPENAI_API_KEY no encontrada en .env local. El OCR podría no funcionar."
    fi

    log "Transfiriendo archivo .env (Credenciales GPT-4)..."
    sshpass -p "$REMOTE_PASS" scp "$LOCAL_DIR/.env" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/.env"
else
    warn "No se encontró archivo .env local. Asegúrate de configurarlo en el servidor remoto."
fi

# Transferir configuración de Apache
log "Transfiriendo configuración de Apache..."
if [ -f "/etc/apache2/sites-enabled/aleph70-proxy.conf" ]; then
    # Crear archivo de config temporal con la IP correcta
    sed 's/192.168.1.23/192.168.1.55/g' /etc/apache2/sites-enabled/aleph70-proxy.conf > aleph70-proxy-remote.conf
    sshpass -p "$REMOTE_PASS" scp aleph70-proxy-remote.conf "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/aleph70-proxy.conf"
    rm aleph70-proxy-remote.conf

    # Configurar Apache remoto
    log "Configurando Apache remoto..."
    remote_exec "
        echo '$REMOTE_PASS' | sudo -S cp $REMOTE_DIR/aleph70-proxy.conf /etc/apache2/sites-available/aleph70-proxy.conf
        echo '$REMOTE_PASS' | sudo -S a2enmod proxy proxy_http headers deflate
        echo '$REMOTE_PASS' | sudo -S a2dissite 000-default.conf
        echo '$REMOTE_PASS' | sudo -S a2ensite aleph70-proxy.conf
        echo '$REMOTE_PASS' | sudo -S systemctl restart apache2
    "
else
    warn "No se encontró configuración local de Apache (/etc/apache2/sites-enabled/aleph70-proxy.conf). Saltando configuración de Apache."
fi

# =============================================================================
# 4. CONFIGURACIÓN DEL ENTORNO VIRTUAL
# =============================================================================
log "Configurando entorno virtual remoto..."

remote_exec "
    cd $REMOTE_DIR
    if [ ! -d 'venv' ]; then
        echo 'Creando virtualenv...'
        python3 -m venv venv
    fi
    
    echo 'Instalando dependencias Python...'
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
"

# =============================================================================
# 5. CONFIGURACIÓN DE PERMISOS Y DIRECTORIOS
# =============================================================================
log "Ajustando permisos y directorios..."

remote_exec "
    cd $REMOTE_DIR
    mkdir -p logs db facturas_proveedores factura_e
    # El servicio systemd 'gunicorn' corre como www-data: dar propiedad de grupo
    # y escritura de grupo para que pueda escribir logs/db sin PermissionError.
    echo '$REMOTE_PASS' | sudo -S chown -R $REMOTE_USER:www-data logs db facturas_proveedores factura_e
    echo '$REMOTE_PASS' | sudo -S chmod -R g+rwX logs db facturas_proveedores factura_e
    echo '$REMOTE_PASS' | sudo -S find logs db facturas_proveedores factura_e -type d -exec chmod g+s {} +
    
    # NO BORRAR la BD de usuarios: contiene los usuarios/empresas de produccion.
    # Solo se inicializa si NO existe (inicializar_bd_usuarios ya hace ese chequeo).
    # Hacer copia de seguridad por si acaso antes de cualquier operacion.
    if [ -f 'db/usuarios_sistema.db' ]; then
        echo 'BD de usuarios existente: se conserva (backup de seguridad).' 
        cp -f db/usuarios_sistema.db db/usuarios_sistema.db.bak_\$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
    else
        echo 'No existe BD de usuarios: inicializando por primera vez...'
        venv/bin/python3 -c 'import sys; sys.path.append(\".\"); from multiempresa_config import inicializar_bd_usuarios; inicializar_bd_usuarios()'
    fi
"

# =============================================================================
# 6. CONFIGURACIÓN DE SERVICIOS (GUNICORN)
# =============================================================================
log "Reiniciando servicios..."

# El servidor usa el servicio systemd 'gunicorn' (www-data, bind 127.0.0.1:5001)
# detras de nginx. NO arrancar gunicorn manualmente con nohup ni en otro puerto,
# ya que nginx hace proxy_pass a 127.0.0.1:5001.
log "Reiniciando servicio systemd gunicorn..."
remote_exec "
    # Matar cualquier gunicorn huerfano que no sea el del servicio systemd
    echo '$REMOTE_PASS' | sudo -S pkill -f 'bind 0.0.0.0:5002' 2>/dev/null || true
    sleep 2
    echo '$REMOTE_PASS' | sudo -S systemctl restart gunicorn.service
    sleep 3
    systemctl is-active gunicorn.service
"

# =============================================================================
# 7. VERIFICACIÓN FINAL
# =============================================================================
log "Verificando despliegue..."

sleep 5
if remote_exec "systemctl is-active --quiet gunicorn.service && curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5001/ | grep -qE '200|30[0-9]'"; then
    log "✅ Despliegue completado exitosamente!"
    echo "La aplicación está corriendo (gunicorn :5001 detrás de nginx). Accede en http://$REMOTE_HOST/"
else
    error "Gunicorn (servicio systemd) no responde correctamente. Revisa el estado y los logs."
    remote_exec "echo '$REMOTE_PASS' | sudo -S journalctl -u gunicorn.service -n 30 --no-pager"
fi

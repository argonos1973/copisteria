#!/bin/bash
# Backup de facturas_proveedores: sincroniza .55 -> .18
# Uso: ejecutar desde .55 o desde local
# Cron recomendado: cada 30 minutos

set -e

REMOTE_18="192.168.1.18"
REMOTE_USER="sami"
REMOTE_PASS="sami"
SRC_DIR="/var/www/html/facturas_proveedores"
DST_DIR="/var/www/html/facturas_proveedores"
LOG_FILE="/var/www/html/logs/backup_facturas.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

mkdir -p "$(dirname "$LOG_FILE")"

echo "[$TIMESTAMP] Iniciando backup facturas_proveedores -> .18" >> "$LOG_FILE"

# Sincronizar .55 -> .18 (no borrar en destino, solo copiar nuevos/actualizados)
sshpass -p "$REMOTE_PASS" rsync -avz \
    --no-perms \
    --omit-dir-times \
    "$SRC_DIR/" "$REMOTE_USER@$REMOTE_18:$DST_DIR/" \
    >> "$LOG_FILE" 2>&1

RESULT=$?
TIMESTAMP_END=$(date '+%Y-%m-%d %H:%M:%S')

if [ $RESULT -eq 0 ]; then
    echo "[$TIMESTAMP_END] Backup completado OK" >> "$LOG_FILE"
else
    echo "[$TIMESTAMP_END] ERROR en backup (codigo $RESULT)" >> "$LOG_FILE"
fi

exit $RESULT

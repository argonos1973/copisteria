#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# --- Config ---
SSH_KEY="${SSH_KEY:-/home/sami/.ssh/id_rsa}"
USER="sami"

# Origen ahora es 192.168.1.18
SRC_HOST="192.168.1.18"
SRC_DB_DIR="/var/www/html/db"
SRC_DB="$SRC_DB_DIR/aleph70.db"
SRC_TMP="/tmp/aleph70_copy.db"
SRC_CARTAS="/var/www/html/cartas_reclamacion"

# Destino ahora es 192.168.1.55
DST_HOST="192.168.1.55"
DST_DIR="/var/www/html/db/aleph70"
DST_DB="$DST_DIR/aleph70.db"
DST_WORK_DIR="/home/sami/bd_update_work"
DST_TMP="$DST_WORK_DIR/aleph70_incoming.db"

LOCAL_TMP="/tmp/aleph70_copy_from_src.db"
LOCAL_CARTAS_DIR="/tmp/cartas_reclamacion"

ssh_src() { ssh -i "$SSH_KEY" -o BatchMode=yes "$USER@$SRC_HOST" "$@"; }
ssh_dst() { ssh -i "$SSH_KEY" -o BatchMode=yes "$USER@$DST_HOST" "$@"; }

echo "📁 Asegurando carpetas en destino ($DST_HOST)..."
ssh_dst "sudo mkdir -p '$DST_DIR' && sudo chown sami:www-data '$DST_DIR' && sudo chmod 775 '$DST_DIR'"
ssh_dst "sudo mkdir -p '/var/www/html/cartas_reclamacion' && sudo chown sami:www-data '/var/www/html/cartas_reclamacion' && sudo chmod 775 '/var/www/html/cartas_reclamacion'"
ssh_dst "mkdir -p '$DST_WORK_DIR'"

echo "🛑 Parando servicios en destino ($DST_HOST)..."
ssh_dst "sudo systemctl stop apache2 && sudo systemctl stop aleph70-flask || true"

cleanup() {
  echo "🧯 Recuperación: arrancando servicios en destino..."
  ssh_dst "sudo systemctl start apache2 && sudo systemctl start aleph70-flask || true"
  rm -f "$LOCAL_TMP" 2>/dev/null || true
  rm -rf "$LOCAL_CARTAS_DIR" 2>/dev/null || true
}
trap cleanup ERR

# --- BASE DE DATOS ---
echo "🔁 Generando copia segura en origen ($SRC_HOST) con .backup..."
ssh_src "sqlite3 '$SRC_DB' \".backup '$SRC_TMP'\""

echo "⬇️  Descargando copia DB a local..."
rsync -avz -e "ssh -i $SSH_KEY -o BatchMode=yes" "$USER@$SRC_HOST:$SRC_TMP" "$LOCAL_TMP"

echo "🧹 Limpiando copia temporal en origen..."
ssh_src "rm -f '$SRC_TMP' || true"

echo "⬆️  Subiendo copia DB al destino..."
rsync -avz -e "ssh -i $SSH_KEY -o BatchMode=yes" "$LOCAL_TMP" "$USER@$DST_HOST:$DST_TMP"

echo "🗑️  Limpiando temporal local DB..."
rm -f "$LOCAL_TMP" || true

# --- CARTAS DE RECLAMACIÓN ---
echo "⬇️  Sincronizando cartas de reclamación desde origen..."
# Rsync directo de origen a local
mkdir -p "$LOCAL_CARTAS_DIR"
# Usamos || true porque si no existe el directorio en origen podría fallar, pero queremos continuar
rsync -avz -e "ssh -i $SSH_KEY -o BatchMode=yes" "$USER@$SRC_HOST:$SRC_CARTAS/" "$LOCAL_CARTAS_DIR/" || echo "⚠️ Advertencia: No se pudieron descargar cartas o no existen."

echo "⬆️  Subiendo cartas al destino..."
rsync -avz -e "ssh -i $SSH_KEY -o BatchMode=yes" "$LOCAL_CARTAS_DIR/" "$USER@$DST_HOST:/tmp/cartas_reclamacion_sync/"

echo "📦 Moviendo cartas a ubicación final en destino..."
ssh_dst "sudo rsync -av /tmp/cartas_reclamacion_sync/ /var/www/html/cartas_reclamacion/ && sudo chown -R www-data:www-data /var/www/html/cartas_reclamacion && sudo chmod -R 775 /var/www/html/cartas_reclamacion"
ssh_dst "rm -rf /tmp/cartas_reclamacion_sync"

echo "🗑️  Limpiando temporal local cartas..."
rm -rf "$LOCAL_CARTAS_DIR"

# --- ACTUALIZACIÓN DE SCHEMA Y FINALIZACIÓN ---
echo "🛠️  Actualizando esquema de base de datos en destino..."
ssh_dst "sudo python3 /var/www/html/actualizar_bd_schema.py '$DST_TMP'"

echo "🧹 Vaciando tabla de gastos en destino..."
ssh_dst "sudo sqlite3 '$DST_TMP' 'DELETE FROM gastos;' 2>/dev/null || echo '⚠️  Advertencia: No se pudo vaciar tabla gastos (quizás no existe)'"

echo "🔍 Verificando integridad en destino..."
INTEGRIDAD=$(ssh_dst "sqlite3 '$DST_TMP' 'PRAGMA integrity_check;'")
if [[ "$INTEGRIDAD" != "ok" ]]; then
  echo "❌ Integridad fallida en destino: $INTEGRIDAD"
  ssh_dst "rm -f '$DST_TMP' || true"
  exit 1
fi

echo "🧽 Eliminando WAL/SHM antiguos en destino..."
ssh_dst "sudo rm -f '${DST_DB}-wal' '${DST_DB}-shm' || true"

echo "💾 Sustituyendo base de datos en destino..."
ssh_dst "sudo mv -f '$DST_TMP' '$DST_DB' && sudo chown sami:www-data '$DST_DB' && sudo chmod 664 '$DST_DB'"

echo "🚀 Arrancando servicios en destino..."
ssh_dst "sudo systemctl start apache2 && sudo systemctl start aleph70-flask"

trap - ERR
echo "✅ Listo: Sincronización completa (BD + Cartas Reclamación)."

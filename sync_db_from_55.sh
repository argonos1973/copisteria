#!/bin/bash
# =============================================================================
# sync_db_from_55.sh
# Sincronización diaria de la BD de producción (.55) -> desarrollo (.23)
#
# Pasos:
#   1. Backup consistente en .55 con sqlite3 .backup (seguro con BD en uso)
#   2. Copia a .23 vía scp
#   3. Restore con sqlite3 .restore (evita problemas de -shm/-wal obsoletos)
#   4. Integrity check
#   5. Commit + push (solo si la BD cambió)
#
# Cron (.23): 0 22 * * * /var/www/html/sync_db_from_55.sh
# =============================================================================

set -euo pipefail

REMOTE_HOST="192.168.1.55"
REMOTE_USER="sami"
REMOTE_PASS="sami"
REMOTE_DB="/var/www/html/db/aleph70/aleph70.db"
REMOTE_TMP="/tmp/aleph70_backup.db"
LOCAL_DB="/var/www/html/db/aleph70/aleph70.db"
LOCAL_TMP="/tmp/aleph70_from_55.db"
LOG="/var/www/html/logs/sync_db.log"
REPO="/var/www/html"

TS() { date '+%Y-%m-%d %H:%M:%S'; }

mkdir -p "$(dirname "$LOG")"
echo "[$(TS)] === Inicio sync BD .55 -> .23 ===" >> "$LOG"

# 1. Backup consistente en .55
sshpass -p "$REMOTE_PASS" ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" \
    "sqlite3 '$REMOTE_DB' '.backup $REMOTE_TMP'" >> "$LOG" 2>&1
echo "[$(TS)] Backup en .55 OK" >> "$LOG"

# 2. Copiar a .23
sshpass -p "$REMOTE_PASS" scp -o StrictHostKeyChecking=no \
    "$REMOTE_USER@$REMOTE_HOST:$REMOTE_TMP" "$LOCAL_TMP" >> "$LOG" 2>&1
echo "[$(TS)] Copia a .23 OK ($(du -h "$LOCAL_TMP" | cut -f1))" >> "$LOG"

# 3. Restore en la BD local (mantiene inodo/permisos, gestiona WAL correctamente)
sqlite3 "$LOCAL_DB" ".restore '$LOCAL_TMP'" >> "$LOG" 2>&1
chown sami:www-data "$LOCAL_DB"
chmod 664 "$LOCAL_DB"
rm -f "$LOCAL_TMP"

# 4. Integrity check
INTEGRITY=$(sqlite3 "$LOCAL_DB" "PRAGMA integrity_check;" | head -1)
if [ "$INTEGRITY" != "ok" ]; then
    echo "[$(TS)] ERROR: integrity_check fallo -> $INTEGRITY" >> "$LOG"
    exit 1
fi
echo "[$(TS)] Integrity check OK" >> "$LOG"

# 5. Commit + push solo si la BD cambió
cd "$REPO"
git add -f db/aleph70/aleph70.db >> "$LOG" 2>&1
if git diff --cached --quiet -- db/aleph70/aleph70.db; then
    echo "[$(TS)] Sin cambios en BD, no se hace commit" >> "$LOG"
else
    git commit -m "chore: sync diaria BD aleph70 desde .55 ($(date +%F))" >> "$LOG" 2>&1
    if git push >> "$LOG" 2>&1; then
        echo "[$(TS)] Commit + push OK" >> "$LOG"
    else
        echo "[$(TS)] WARNING: commit hecho pero push fallo" >> "$LOG"
    fi
fi

echo "[$(TS)] === Sync completado ===" >> "$LOG"

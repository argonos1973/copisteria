#!/bin/bash
set -eo pipefail

# Sincroniza BD de .55 -> .18 cada noche
# Usa sqlite3 .dump para evitar corrupcion por transferencia binaria

LOG="/var/www/html/logs/sync_db_to_18.log"
SRC_DB="/var/www/html/db/aleph70/aleph70.db"
DST_HOST="192.168.1.18"
DST_DB="/var/www/html/db/aleph70/aleph70.db"
SSH_KEY="/home/sami/.ssh/id_rsa"
TS=$(date "+%Y-%m-%d %H:%M:%S")

echo "[$TS] Iniciando sincronizacion .55 -> .18" >> "$LOG"

# 1. Verificar integridad en origen
INTEGRIDAD=$(sqlite3 "$SRC_DB" "PRAGMA integrity_check;" 2>&1)
if [[ "$INTEGRIDAD" != "ok" ]]; then
  echo "[$TS] ERROR: Integridad fallida en origen: $INTEGRIDAD" >> "$LOG"
  exit 1
fi

# 2. Detener gunicorn en destino para liberar la BD
echo "[$TS] Deteniendo gunicorn en .18..." >> "$LOG"
ssh -i "$SSH_KEY" -o BatchMode=yes sami@"$DST_HOST" \
  "echo sami | sudo -S systemctl stop gunicorn 2>/dev/null; echo gunicorn_stopped" >> "$LOG" 2>&1 || true

# 3. Dump local a archivo, scp a .18 y restaurar
DUMP_FILE="/tmp/aleph70_dump.sql"

echo "[$TS] Volcando BD a archivo local..." >> "$LOG"
if ! sqlite3 "$SRC_DB" .dump > "$DUMP_FILE"; then
  echo "[$TS] ERROR: Fallo al volcar BD de .55" >> "$LOG"
  ssh -i "$SSH_KEY" -o BatchMode=yes sami@"$DST_HOST" \
    "echo sami | sudo -S systemctl start gunicorn 2>/dev/null; echo gunicorn_started" >> "$LOG" 2>&1 || true
  exit 1
fi
SIZE=$(ls -la "$DUMP_FILE" | awk '{print $5}')
echo "[$TS] Archivo dump generado: $SIZE bytes" >> "$LOG"

echo "[$TS] Copiando dump a .18..." >> "$LOG"
if ! scp -i "$SSH_KEY" -o BatchMode=yes "$DUMP_FILE" sami@"$DST_HOST":/tmp/aleph70_dump.sql; then
  echo "[$TS] ERROR: Fallo al copiar a .18" >> "$LOG"
  ssh -i "$SSH_KEY" -o BatchMode=yes sami@"$DST_HOST" \
    "echo sami | sudo -S systemctl start gunicorn 2>/dev/null; echo gunicorn_started" >> "$LOG" 2>&1 || true
  exit 1
fi

echo "[$TS] Restaurando BD en .18..." >> "$LOG"
if ! ssh -i "$SSH_KEY" -o BatchMode=yes sami@"$DST_HOST" \
  "rm -f /tmp/aleph70_incoming.db /tmp/aleph70_incoming.db-shm /tmp/aleph70_incoming.db-wal && \
   sqlite3 /tmp/aleph70_incoming.db < /tmp/aleph70_dump.sql && \
   sqlite3 /tmp/aleph70_incoming.db 'PRAGMA integrity_check;' && \
   rm -f '$DST_DB-shm' '$DST_DB-wal' && \
   mv -f /tmp/aleph70_incoming.db '$DST_DB' && \
   chmod 664 '$DST_DB' && \
   chgrp www-data '$DST_DB' && \
   rm -f /tmp/aleph70_dump.sql && \
   echo DB_REPLACED" >> "$LOG" 2>&1; then
  echo "[$TS] ERROR: Fallo al restaurar BD en .18" >> "$LOG"
  ssh -i "$SSH_KEY" -o BatchMode=yes sami@"$DST_HOST" \
    "echo sami | sudo -S systemctl start gunicorn 2>/dev/null; echo gunicorn_started" >> "$LOG" 2>&1 || true
  rm -f "$DUMP_FILE"
  exit 1
fi

rm -f "$DUMP_FILE"

# 4. Verificar resultado en destino
ULTIMA=$(ssh -i "$SSH_KEY" -o BatchMode=yes sami@"$DST_HOST" \
  "sqlite3 '$DST_DB' 'SELECT MAX(fecha) FROM tickets;' 2>&1")
echo "[$TS] Sincronizacion completada. Ultima fecha en .18: $ULTIMA" >> "$LOG"

# 5. Reiniciar gunicorn en destino
echo "[$TS] Reiniciando gunicorn en .18..." >> "$LOG"
ssh -i "$SSH_KEY" -o BatchMode=yes sami@"$DST_HOST" \
  "echo sami | sudo -S systemctl start gunicorn 2>/dev/null; echo gunicorn_started" >> "$LOG" 2>&1 || true

echo "[$TS] Fin de sincronizacion" >> "$LOG"

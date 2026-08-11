#!/bin/bash
set -euo pipefail

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

# 2. Dump -> pipe SSH -> sqlite3 en destino (evita corrupcion binaria)
echo "[$TS] Volcando y restaurando BD via dump..." >> "$LOG"
sqlite3 "$SRC_DB" .dump | ssh -i "$SSH_KEY" -o BatchMode=yes sami@"$DST_HOST" \
  "rm -f /tmp/aleph70_incoming.db && sqlite3 /tmp/aleph70_incoming.db && \
   sqlite3 /tmp/aleph70_incoming.db 'PRAGMA integrity_check;' && \
   mv -f /tmp/aleph70_incoming.db '$DST_DB' && \
   echo OK" >> "$LOG" 2>&1

if [[ $? -ne 0 ]]; then
  echo "[$TS] ERROR: Fallo en la transferencia" >> "$LOG"
  exit 1
fi

# 3. Verificar resultado en destino
ULTIMA=$(ssh -i "$SSH_KEY" -o BatchMode=yes sami@"$DST_HOST" \
  "sqlite3 '$DST_DB' 'SELECT MAX(fecha) FROM tickets;' 2>&1")
echo "[$TS] Sincronizacion completada. Ultima fecha en .18: $ULTIMA" >> "$LOG"

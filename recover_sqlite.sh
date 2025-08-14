#!/usr/bin/env bash
# recover_sqlite.sh - Recupera una base de datos SQLite dañada usando la orden .recover
#
# Uso:
#   ./recover_sqlite.sh ruta/a/aleph70.db            # recupera BD completa
#   ./recover_sqlite.sh ruta/a/aleph70.db gastos      # recupera solo la tabla gastos
#
# Requisitos:
#   - sqlite3 v3.29 o superior (necesario para la orden .recover)
#
# Pasos que realiza:
#   1) Crea una copia de seguridad del fichero original.
#   2) Ejecuta `.recover` volcando las sentencias INSERT en un SQL intermedio.
#   3) Genera una BD nueva a partir del volcado.
#   4) Ejecuta `PRAGMA integrity_check` y `VACUUM`.
#   5) Informa de la ruta de la BD recuperada para que el usuario la reemplace manualmente.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Uso: $0 <ruta_db> [tabla1 tabla2 ...]" >&2
  exit 1
fi

DB_PATH=$1; shift
TABLES=("$@")

if [[ ! -f "$DB_PATH" ]]; then
  echo "El fichero $DB_PATH no existe" >&2
  exit 1
fi

# Detener Apache antes de operar
echo "🛑 Parando Apache..."
APACHE_SERVICE="apache2"
# Intentamos detener usando systemctl y, si falla, service
sudo systemctl stop "$APACHE_SERVICE" 2>/dev/null || sudo service "$APACHE_SERVICE" stop 2>/dev/null || true

# Al finalizar el script, volver a arrancar Apache esté como esté (éxito o error)
trap 'echo "🚀 Arrancando Apache..."; sudo systemctl start "$APACHE_SERVICE" 2>/dev/null || sudo service "$APACHE_SERVICE" start 2>/dev/null || true' EXIT

# Verificar versión de sqlite3
REQ_VER=3.29
SQLITE_VER=$(sqlite3 -version | awk '{print $1}')
if [[ $(printf '%s\n' "$REQ_VER" "$SQLITE_VER" | sort -V | head -n1) != "$REQ_VER" ]]; then
  echo "sqlite3 ≥ $REQ_VER es necesario (version actual $SQLITE_VER)" >&2
  exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="${DB_PATH%.db}_backup_${TIMESTAMP}.db"
DUMP_SQL="dump_recover_${TIMESTAMP}.sql"
NEW_DB="${DB_PATH%.db}_recovered_${TIMESTAMP}.db"

echo "📦  Copiando BD original a $BACKUP_PATH..."
cp "$DB_PATH" "$BACKUP_PATH"

# Recuperación: ruta completa o por tablas
if [[ ${#TABLES[@]} -eq 0 ]]; then
  echo "🔧 Ejecutando .recover completo... (esto puede tardar)"
# SQLite .recover no admite nombres de tabla (los interpreta como opciones).
# Por ello siempre recuperamos todo. Si el usuario solicitó tablas específicas,
# más adelante extraeremos solo esas tablas.
  sqlite3 "$BACKUP_PATH" <<EOF
.mode insert
.output $DUMP_SQL
.recover
EOF

  echo "🗄️  Creando nueva BD en $NEW_DB..."
  sqlite3 "$NEW_DB" < "$DUMP_SQL"

  echo "🩺 Verificando integridad..."
INTEGRITY=$(  INTEGRITY=$(sqlite3 "$NEW_DB" "PRAGMA integrity_check;"))
if [[ "$INTEGRITY" != "ok" ]]; then
  echo "❌ La nueva BD sigue corrupta: $INTEGRITY" >&2
  exit 1
fi

# Optimizar
  sqlite3 "$NEW_DB" "VACUUM;"
else
  echo "🔧 Recuperación de tablas específicas: ${TABLES[*]} (sin .recover)"
  echo "🗄️  Copiando base original a $NEW_DB..."
  cp "$BACKUP_PATH" "$NEW_DB"

  for tbl in "${TABLES[@]}"; do
    echo "🔄 Reemplazando tabla $tbl..."
    # Extraer estructura y datos de la tabla desde copia de seguridad
    sqlite3 "$BACKUP_PATH" ".dump $tbl" > "$tbl.sql" || {
      echo "❌ Error al volcar tabla $tbl" >&2; exit 1;
    }
    # Eliminar tabla corrupta y cargar la versión exportada
    sqlite3 "$NEW_DB" "DROP TABLE IF EXISTS $tbl;"
    sqlite3 "$NEW_DB" < "$tbl.sql"
    rm -f "$tbl.sql"
  done

  echo "🩺 Verificando integridad..."
  INTEGRITY=$(sqlite3 "$NEW_DB" "PRAGMA integrity_check;")
  if [[ "$INTEGRITY" != "ok" ]]; then
    echo "❌ La BD reparada tiene problemas: $INTEGRITY" >&2
    exit 1
  fi

  sqlite3 "$NEW_DB" "VACUUM;"
fi

echo "✅ Recuperación finalizada con éxito. Fichero generado: $NEW_DB"
echo "   Reemplaza manualmente la BD antigua cuando no esté en uso:"
echo "   mv $NEW_DB $DB_PATH"

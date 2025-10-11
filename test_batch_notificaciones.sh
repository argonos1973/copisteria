#!/bin/bash
cd /var/www/html

echo "🗑️  Eliminando notificaciones existentes..."
sqlite3 db/aleph70.db "DELETE FROM notificaciones;"
echo "✅ Notificaciones eliminadas"

echo "📝 Cambiando factura F250313 a estado Pendiente..."
sqlite3 db/aleph70.db "UPDATE factura SET estado = 'P' WHERE numero = 'F250313';"
echo "✅ Factura actualizada"

echo "🚀 Ejecutando batch de facturas vencidas..."
source venv/bin/activate
python3 batchFacturasVencidas.py

echo ""
echo "📊 Verificando notificaciones generadas..."
sqlite3 db/aleph70.db "SELECT COUNT(*) as total FROM notificaciones;"
echo ""
echo "📄 Últimas notificaciones:"
sqlite3 db/aleph70.db "SELECT tipo, mensaje FROM notificaciones ORDER BY id DESC LIMIT 3;"

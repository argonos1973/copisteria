#!/bin/bash
# Script para instalar la tarea cron de conciliación automática

CRON_SCRIPT="/var/www/html/scripts/ejecutar_conciliacion_automatica.py"
PYTHON_BIN="/usr/bin/python3"

# Verificar que el script existe
if [ ! -f "$CRON_SCRIPT" ]; then
    echo "❌ Error: Script $CRON_SCRIPT no encontrado"
    exit 1
fi

# Hacer el script ejecutable
chmod +x "$CRON_SCRIPT"

# Crear entrada de crontab
# Ejecutar cada hora de 8:00 a 20:00 de lunes a viernes
CRON_ENTRY="0 8-20 * * 1-5 $PYTHON_BIN $CRON_SCRIPT >> /var/www/html/logs/conciliacion_cron.log 2>&1"

# Verificar si ya existe la entrada
if crontab -l 2>/dev/null | grep -q "$CRON_SCRIPT"; then
    echo "⚠️  La tarea cron ya existe. Actualizando..."
    # Eliminar entrada existente
    crontab -l 2>/dev/null | grep -v "$CRON_SCRIPT" | crontab -
fi

# Añadir nueva entrada
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo "✅ Tarea cron instalada correctamente"
echo ""
echo "📋 Configuración:"
echo "   - Script: $CRON_SCRIPT"
echo "   - Horario: Cada hora de 8:00 a 20:00 (lunes a viernes)"
echo "   - Log: /var/www/html/logs/conciliacion_cron.log"
echo ""
echo "Para ver las tareas cron actuales:"
echo "   crontab -l"
echo ""
echo "Para ver el log en tiempo real:"
echo "   tail -f /var/www/html/logs/conciliacion_cron.log"

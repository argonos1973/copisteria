#!/bin/bash
# scraping_y_conciliacion.sh
# Script que ejecuta el scraping bancario y luego la conciliación automática

SCRIPT_DIR="/var/www/html"
VENV_PYTHON="/var/www/html/venv/bin/python"
LOG_FILE="/var/www/html/logs/conciliacion_auto.log"

# Crear directorio de logs si no existe
mkdir -p /var/www/html/logs

echo "========================================" >> "$LOG_FILE"
echo "Inicio: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# 1. Ejecutar scraping bancario
echo "[1/2] Ejecutando scraping bancario..." >> "$LOG_FILE"
cd "$SCRIPT_DIR"
$VENV_PYTHON scrapeo.py >> "$LOG_FILE" 2>&1
SCRAPING_EXIT=$?

if [ $SCRAPING_EXIT -eq 0 ]; then
    echo "✓ Scraping completado exitosamente" >> "$LOG_FILE"
    
    # 2. Ejecutar conciliación automática
    echo "[2/2] Ejecutando conciliación automática..." >> "$LOG_FILE"
    $VENV_PYTHON conciliacion_auto.py 90 >> "$LOG_FILE" 2>&1
    CONCILIACION_EXIT=$?
    
    if [ $CONCILIACION_EXIT -eq 0 ]; then
        echo "✓ Conciliación completada exitosamente" >> "$LOG_FILE"
    else
        echo "✗ Error en conciliación (exit code: $CONCILIACION_EXIT)" >> "$LOG_FILE"
    fi
else
    echo "✗ Error en scraping (exit code: $SCRAPING_EXIT)" >> "$LOG_FILE"
    echo "No se ejecuta conciliación debido al error en scraping" >> "$LOG_FILE"
fi

echo "Fin: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

#!/bin/bash

echo "🔧 Moviendo auto_branding.js al inicio del <head> en todas las páginas..."
echo ""

TOTAL=0
MOVIDOS=0

for archivo in /var/www/html/frontend/*.html; do
    nombre=$(basename "$archivo")
    
    # Saltar archivos sin auto_branding
    if ! grep -q "auto_branding.js" "$archivo"; then
        continue
    fi
    
    TOTAL=$((TOTAL + 1))
    
    # Obtener línea actual
    LINEA=$(grep -n "auto_branding" "$archivo" | cut -d: -f1 | head -1)
    
    # Si está después de línea 20, moverlo
    if [ "$LINEA" -gt 20 ]; then
        echo "📝 $nombre (línea $LINEA) → Moviendo al inicio..."
        
        # 1. Eliminar la línea actual
        sudo sed -i "${LINEA}d" "$archivo"
        
        # 2. Encontrar línea de <title> y añadir después
        TITLE_LINE=$(grep -n "<title>" "$archivo" | cut -d: -f1 | head -1)
        if [ -n "$TITLE_LINE" ]; then
            sudo sed -i "${TITLE_LINE}a\    <script src=\"/static/auto_branding.js?v=2\"></script>" "$archivo"
            echo "   ✅ Movido después de <title>"
        else
            echo "   ⚠️  No se encontró <title>, dejando como estaba"
        fi
        
        MOVIDOS=$((MOVIDOS + 1))
    else
        echo "✅ $nombre (línea $LINEA) → Ya está al inicio"
    fi
done

echo ""
echo "=========================================="
echo "  RESUMEN"
echo "=========================================="
echo "Total archivos procesados: $TOTAL"
echo "Archivos movidos:          $MOVIDOS"
echo "=========================================="
echo ""
echo "✅ Proceso completado"
echo ""
echo "Reinicia Apache:"
echo "  sudo systemctl restart apache2"

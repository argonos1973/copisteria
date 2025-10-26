#!/bin/bash
# Script para añadir auto_branding.js a todos los HTML del frontend

echo "🎨 Aplicando auto-branding a todas las páginas HTML..."
echo ""

# Archivos a excluir (sin sesión o contenedores)
EXCLUIR=(
    "LOGIN.html"
    "_app_private.html"
    "index.html"
)

# Contador
TOTAL=0
MODIFICADOS=0
YA_TIENEN=0

# Buscar todos los .html en frontend
for archivo in /var/www/html/frontend/*.html; do
    nombre=$(basename "$archivo")
    TOTAL=$((TOTAL + 1))
    
    # Verificar si está en la lista de exclusión
    EXCLUIR_ESTE=false
    for excluido in "${EXCLUIR[@]}"; do
        if [ "$nombre" = "$excluido" ]; then
            EXCLUIR_ESTE=true
            echo "⏭️  Saltando: $nombre (en lista de exclusión)"
            break
        fi
    done
    
    if [ "$EXCLUIR_ESTE" = true ]; then
        continue
    fi
    
    # Verificar si ya tiene el script
    if grep -q "auto_branding.js" "$archivo"; then
        echo "✅ Ya tiene: $nombre"
        YA_TIENEN=$((YA_TIENEN + 1))
    else
        # Añadir antes del </head>
        sudo sed -i '/<\/head>/i \    <script src="/static/auto_branding.js"><\/script>' "$archivo"
        echo "➕ Añadido:  $nombre"
        MODIFICADOS=$((MODIFICADOS + 1))
    fi
done

echo ""
echo "=========================================="
echo "  RESUMEN"
echo "=========================================="
echo "Total archivos procesados: $TOTAL"
echo "Ya tenían el script:       $YA_TIENEN"
echo "Modificados ahora:         $MODIFICADOS"
echo "=========================================="
echo ""
echo "✅ Proceso completado"
echo ""
echo "Ahora reinicia Apache:"
echo "  sudo systemctl restart apache2"

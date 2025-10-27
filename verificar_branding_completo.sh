#!/bin/bash

echo "======================================"
echo "VERIFICACIÓN COMPLETA DE AUTO-BRANDING"
echo "======================================"
echo ""

FRONTEND_DIR="/var/www/html/frontend"
TOTAL=0
CON_BRANDING=0
SIN_BRANDING=0
PROBLEMAS=0

echo "📋 ANALIZANDO ARCHIVOS HTML..."
echo ""

for file in "$FRONTEND_DIR"/*.html; do
    filename=$(basename "$file")
    
    # Excluir archivos de admin, login e impresión
    if [[ "$filename" =~ ^(ADMIN_|EDITAR_EMPRESA_COLORES|LOGIN|index|IMPRIMIR_|imprimir-|_app_private) ]]; then
        continue
    fi
    
    TOTAL=$((TOTAL + 1))
    
    # Verificar si tiene auto_branding.js
    if grep -q "auto_branding.js" "$file"; then
        CON_BRANDING=$((CON_BRANDING + 1))
        
        # Verificar que sea el primer script
        first_script_line=$(grep -n "<script" "$file" | head -1 | cut -d: -f1)
        auto_brand_line=$(grep -n "auto_branding.js" "$file" | cut -d: -f1)
        
        if [ "$first_script_line" == "$auto_brand_line" ]; then
            echo "✅ $filename - Branding OK (línea $auto_brand_line)"
        else
            echo "⚠️  $filename - Branding NO es el primer script (línea $auto_brand_line, primer script: $first_script_line)"
            PROBLEMAS=$((PROBLEMAS + 1))
        fi
        
        # Verificar estilos inline problemáticos
        white_styles=$(grep -i 'style.*background.*white\|style.*background.*#fff' "$file" | wc -l)
        if [ "$white_styles" -gt 0 ]; then
            echo "   ⚠️  Tiene $white_styles estilos inline con fondo blanco"
            PROBLEMAS=$((PROBLEMAS + 1))
        fi
        
    else
        echo "❌ $filename - SIN auto_branding.js"
        SIN_BRANDING=$((SIN_BRANDING + 1))
        PROBLEMAS=$((PROBLEMAS + 1))
    fi
done

echo ""
echo "======================================"
echo "RESUMEN"
echo "======================================"
echo "Total archivos analizados: $TOTAL"
echo "Con auto_branding.js: $CON_BRANDING"
echo "Sin auto_branding.js: $SIN_BRANDING"
echo "Problemas detectados: $PROBLEMAS"
echo ""

if [ "$PROBLEMAS" -eq 0 ]; then
    echo "✅ TODO CORRECTO - Todos los archivos tienen branding"
else
    echo "⚠️  HAY PROBLEMAS - Revisar advertencias arriba"
fi

echo ""
echo "======================================"
echo "VERIFICACIÓN DE auto_branding.js"
echo "======================================"

if [ -f "/var/www/html/static/auto_branding.js" ]; then
    size=$(du -h /var/www/html/static/auto_branding.js | cut -f1)
    version=$(grep -o "v[0-9.]*" /var/www/html/static/auto_branding.js | head -1)
    echo "✅ Archivo existe: $size"
    echo "✅ Versión: $version"
    
    # Verificar que tiene las secciones clave
    echo ""
    echo "Secciones encontradas:"
    grep -q "IMPORTES" /var/www/html/static/auto_branding.js && echo "  ✅ Importes positivos/negativos"
    grep -q "NOTIFICACIONES" /var/www/html/static/auto_branding.js && echo "  ✅ Notificaciones y alertas"
    grep -q "MODALES" /var/www/html/static/auto_branding.js && echo "  ✅ Modales y diálogos"
    grep -q "TABS" /var/www/html/static/auto_branding.js && echo "  ✅ Tabs y pestañas"
    grep -q "grid_cell_borders" /var/www/html/static/auto_branding.js && echo "  ✅ Bordes de tabla configurables"
    grep -q "paginasExcluidas" /var/www/html/static/auto_branding.js && echo "  ✅ Exclusión de páginas admin"
else
    echo "❌ Archivo NO EXISTE"
fi

echo ""
echo "======================================"
echo "LISTADO DE PÁGINAS NO-ADMIN"
echo "======================================"
echo ""
for file in "$FRONTEND_DIR"/*.html; do
    filename=$(basename "$file")
    if [[ ! "$filename" =~ ^(ADMIN_|EDITAR_EMPRESA_COLORES|LOGIN|index|IMPRIMIR_|imprimir-|_app_private) ]]; then
        echo "  • $filename"
    fi
done

echo ""
echo "✅ Verificación completa finalizada"

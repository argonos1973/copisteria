#!/bin/bash

echo "======================================"
echo "  🔍 VERIFICACIÓN DE ESTILOS"
echo "======================================"
echo ""

# 1. Verificar archivo
echo "1️⃣  Verificando auto_branding.js..."
if [ -f "/var/www/html/static/auto_branding.js" ]; then
    VERSION=$(head -5 /var/www/html/static/auto_branding.js | grep -o "Versión:.*")
    echo "   ✅ Archivo existe"
    echo "   📦 $VERSION"
else
    echo "   ❌ Archivo NO existe"
fi
echo ""

# 2. Verificar colores en BD
echo "2️⃣  Verificando colores en Base de Datos..."
COLORES=$(sqlite3 /var/www/html/db/usuarios_sistema.db \
  "SELECT color_primario, color_header_text, color_secundario, color_grid_text, color_button 
   FROM empresas WHERE codigo = 'copisteria'")

IFS='|' read -r PRIMARIO TEXTO_MENU SECUNDARIO TEXTO_CARD BOTON <<< "$COLORES"

echo "   🎨 Menú lateral (primario):   $PRIMARIO"
echo "   📝 Texto menú:                $TEXTO_MENU"
echo "   🔲 Tarjetas (secundario):     $SECUNDARIO"
echo "   ✏️  Texto tarjetas:            $TEXTO_CARD"
echo "   🔘 Botones:                   $BOTON"
echo ""

# 3. Verificar páginas actualizadas
echo "3️⃣  Verificando páginas con auto_branding..."
PAGINAS_V2=$(grep -l "auto_branding.js?v=2" /var/www/html/frontend/*.html 2>/dev/null | wc -l)
PAGINAS_TOTAL=$(grep -l "auto_branding.js" /var/www/html/frontend/*.html 2>/dev/null | wc -l)

echo "   📄 Páginas con v=2:  $PAGINAS_V2"
echo "   📄 Páginas total:    $PAGINAS_TOTAL"

if [ "$PAGINAS_V2" -eq "$PAGINAS_TOTAL" ]; then
    echo "   ✅ Todas actualizadas"
else
    echo "   ⚠️  Algunas páginas sin versionar"
fi
echo ""

# 4. Verificar Apache
echo "4️⃣  Verificando Apache..."
if systemctl is-active --quiet apache2; then
    echo "   ✅ Apache corriendo"
    PORT_5001=$(sudo lsof -i :5001 2>/dev/null | grep apache | wc -l)
    if [ "$PORT_5001" -gt 0 ]; then
        echo "   ✅ Escuchando en puerto 5001"
    else
        echo "   ⚠️  NO escuchando en 5001"
    fi
else
    echo "   ❌ Apache NO está corriendo"
fi
echo ""

# 5. Validaciones
echo "5️⃣  Validaciones..."
ERRORES=0

# Validar Minimal: menú blanco
if [ "$PRIMARIO" = "#ffffff" ] || [ "$PRIMARIO" = "#FFFFFF" ]; then
    echo "   ✅ Menú lateral blanco (Minimal)"
else
    echo "   ❌ Menú lateral NO es blanco: $PRIMARIO"
    ERRORES=$((ERRORES + 1))
fi

# Validar Minimal: texto negro
if [ "$TEXTO_MENU" = "#000000" ]; then
    echo "   ✅ Texto menú negro (Minimal)"
else
    echo "   ❌ Texto menú NO es negro: $TEXTO_MENU"
    ERRORES=$((ERRORES + 1))
fi

# Validar contraste tarjetas
if [ "$TEXTO_CARD" = "#000000" ]; then
    echo "   ✅ Texto tarjetas negro (buen contraste)"
else
    echo "   ⚠️  Texto tarjetas: $TEXTO_CARD"
fi

echo ""

# Resumen
echo "======================================"
if [ $ERRORES -eq 0 ]; then
    echo "  ✅ TODO CORRECTO"
    echo "======================================"
    echo ""
    echo "🎯 Instrucciones para el navegador:"
    echo "   1. Presiona Ctrl + Shift + R para forzar recarga"
    echo "   2. Abre DevTools (F12)"
    echo "   3. Ve a la pestaña Console"
    echo "   4. Deberías ver logs: [AUTO-BRANDING v2.0]"
    echo "   5. Navega entre páginas y verifica que"
    echo "      los estilos se mantienen"
else
    echo "  ⚠️  $ERRORES ERRORES ENCONTRADOS"
    echo "======================================"
    echo ""
    echo "🔧 Ejecuta este comando para corregir:"
    echo ""
    echo "sqlite3 /var/www/html/db/usuarios_sistema.db \\"
    echo "  \"UPDATE empresas SET \\"
    echo "    color_primario = '#ffffff', \\"
    echo "    color_header_text = '#000000', \\"
    echo "    color_secundario = '#f5f5f5', \\"
    echo "    color_grid_text = '#000000', \\"
    echo "    color_button = '#000000' \\"
    echo "  WHERE codigo = 'copisteria'\""
    echo ""
    echo "sudo systemctl restart apache2"
fi
echo ""

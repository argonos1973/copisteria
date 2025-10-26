#!/bin/bash
# Script para limpiar cache y verificar

echo "🧹 Limpiando cache..."

# Limpiar cache de Apache
sudo rm -rf /var/cache/apache2/*

# Reiniciar Apache
sudo systemctl restart apache2

echo "✅ Cache limpiada y Apache reiniciado"
echo ""
echo "Ahora recarga la página con:"
echo "  Ctrl + Shift + R (Chrome/Firefox)"
echo "  o"
echo "  Ctrl + F5 (cualquier navegador)"

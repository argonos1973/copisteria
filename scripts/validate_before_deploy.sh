#!/bin/bash
#
# Script de Validación Pre-Deployment
# Ejecutar SIEMPRE antes de desplegar a producción
#
# Uso: ./scripts/validate_before_deploy.sh [archivos...]
#       Si no se especifican archivos, valida todos los .py del proyecto
#

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  🛡️  VALIDACIÓN PRE-DEPLOYMENT - SEGURIDAD DE PRODUCCIÓN${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Determinar archivos a validar
if [ $# -eq 0 ]; then
    echo -e "${BLUE}📂 Modo: Validación completa del proyecto${NC}"
    FILES=$(find /var/www/html -name "*.py" -not -path "*/venv/*" -not -path "*/.git/*" -not -path "*/tests/*" -not -path "*/__pycache__/*")
else
    echo -e "${BLUE}📂 Modo: Validación de archivos específicos${NC}"
    FILES="$@"
fi

echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  FASE 1: VALIDACIÓN DE SINTAXIS PYTHON${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo ""

SYNTAX_ERRORS=0
SYNTAX_ERROR_FILES=""

while IFS= read -r file; do
    if [ -f "$file" ]; then
        BASENAME=$(basename "$file")
        OUTPUT=$(python3 -m py_compile "$file" 2>&1)
        
        if [ $? -ne 0 ]; then
            echo -e "${RED}✗ $BASENAME - ERROR DE SINTAXIS${NC}"
            echo "$OUTPUT" | head -3 | sed 's/^/    /'
            echo ""
            SYNTAX_ERRORS=$((SYNTAX_ERRORS + 1))
            SYNTAX_ERROR_FILES="${SYNTAX_ERROR_FILES}\n    ❌ $BASENAME"
        else
            echo -e "${GREEN}✓${NC} $BASENAME"
        fi
    fi
done <<< "$FILES"

echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  FASE 2: VALIDACIÓN DE IMPORTS${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo ""

IMPORT_ERRORS=0
IMPORT_ERROR_FILES=""

# Validar imports críticos
CORE_FILES="/var/www/html/app.py /var/www/html/factura.py /var/www/html/tickets.py /var/www/html/productos.py /var/www/html/conciliacion.py"

for file in $CORE_FILES; do
    if [ -f "$file" ]; then
        BASENAME=$(basename "$file")
        
        # Intentar importar el módulo
        MODULE_NAME=$(basename "$file" .py)
        OUTPUT=$(cd /var/www/html && python3 -c "import sys; sys.path.insert(0, '.'); import $MODULE_NAME" 2>&1)
        
        if [ $? -ne 0 ]; then
            echo -e "${RED}✗ $BASENAME - ERROR DE IMPORT${NC}"
            echo "$OUTPUT" | grep -E "(ImportError|ModuleNotFoundError|Error)" | head -2 | sed 's/^/    /'
            echo ""
            IMPORT_ERRORS=$((IMPORT_ERRORS + 1))
            IMPORT_ERROR_FILES="${IMPORT_ERROR_FILES}\n    ❌ $BASENAME"
        else
            echo -e "${GREEN}✓${NC} $BASENAME - Imports OK"
        fi
    fi
done

echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  FASE 3: VALIDACIÓN DE PATTERNS PROBLEMÁTICOS${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo ""

PATTERN_WARNINGS=0
PATTERN_WARNING_FILES=""

# Buscar f-strings mal formateados (el problema que tuvimos)
echo -e "${BLUE}🔎 Buscando f-strings potencialmente mal formateados...${NC}"

PROBLEMATIC_FSTRINGS=$(grep -rn 'logger.*f".*'"'" /var/www/html --include="*.py" --exclude-dir=venv --exclude-dir=.git --exclude-dir=tests 2>/dev/null || true)

if [ ! -z "$PROBLEMATIC_FSTRINGS" ]; then
    echo -e "${YELLOW}⚠️  Encontrados f-strings con comillas sospechosas:${NC}"
    echo "$PROBLEMATIC_FSTRINGS" | head -5 | sed 's/^/    /'
    PATTERN_WARNINGS=$((PATTERN_WARNINGS + 1))
else
    echo -e "${GREEN}✓${NC} No se encontraron f-strings problemáticos"
fi

echo ""

# Buscar paréntesis desbalanceados en logger
echo -e "${BLUE}🔎 Buscando paréntesis desbalanceados en logger...${NC}"

UNBALANCED=$(grep -rn 'logger\.' /var/www/html --include="*.py" --exclude-dir=venv --exclude-dir=.git --exclude-dir=tests | \
             awk -F: '{print $1":"$2":"$3}' | \
             while read line; do
                 CODE=$(echo "$line" | cut -d: -f3-)
                 OPEN=$(echo "$CODE" | tr -cd '(' | wc -c)
                 CLOSE=$(echo "$CODE" | tr -cd ')' | wc -c)
                 if [ $OPEN -ne $CLOSE ]; then
                     echo "$line"
                 fi
             done 2>/dev/null || true)

if [ ! -z "$UNBALANCED" ]; then
    echo -e "${YELLOW}⚠️  Encontradas líneas con paréntesis desbalanceados:${NC}"
    echo "$UNBALANCED" | head -5 | sed 's/^/    /'
    PATTERN_WARNINGS=$((PATTERN_WARNINGS + 1))
else
    echo -e "${GREEN}✓${NC} No se encontraron paréntesis desbalanceados"
fi

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  📊 RESUMEN DE VALIDACIÓN${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""

TOTAL_ERRORS=$((SYNTAX_ERRORS + IMPORT_ERRORS))

echo -e "  Errores de sintaxis:     ${RED}$SYNTAX_ERRORS${NC}"
echo -e "  Errores de imports:      ${RED}$IMPORT_ERRORS${NC}"
echo -e "  Warnings de patterns:    ${YELLOW}$PATTERN_WARNINGS${NC}"
echo ""

if [ $TOTAL_ERRORS -gt 0 ]; then
    echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ❌ VALIDACIÓN FALLIDA - NO DESPLEGAR A PRODUCCIÓN        ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    if [ $SYNTAX_ERRORS -gt 0 ]; then
        echo -e "${RED}Archivos con errores de sintaxis:${NC}"
        echo -e "$SYNTAX_ERROR_FILES"
        echo ""
    fi
    
    if [ $IMPORT_ERRORS -gt 0 ]; then
        echo -e "${RED}Archivos con errores de imports:${NC}"
        echo -e "$IMPORT_ERROR_FILES"
        echo ""
    fi
    
    echo -e "${YELLOW}⚠️  Por favor, corrige los errores antes de desplegar.${NC}"
    echo ""
    exit 1
elif [ $PATTERN_WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║  ⚠️  VALIDACIÓN CON WARNINGS - REVISAR ANTES DE DEPLOY   ║${NC}"
    echo -e "${YELLOW}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Se encontraron patterns sospechosos. Revisa antes de continuar.${NC}"
    echo ""
    read -p "¿Deseas continuar de todas formas? [y/N] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}❌ Deployment cancelado por el usuario${NC}"
        exit 1
    fi
    exit 0
else
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ VALIDACIÓN EXITOSA - SEGURO PARA DEPLOYMENT          ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}✓ Todos los archivos pasaron la validación${NC}"
    echo -e "${GREEN}✓ Es seguro desplegar a producción${NC}"
    echo ""
    exit 0
fi

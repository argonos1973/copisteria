#!/bin/bash

# Script de configuración de CI/CD para Aleph70
# Ejecutar: chmod +x setup_ci.sh && ./setup_ci.sh

set -e

echo "🚀 Configurando CI/CD para Aleph70..."
echo ""

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar Python
echo -e "${BLUE}📦 Verificando Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}⚠️  Python 3 no encontrado. Por favor instala Python 3.11 o superior.${NC}"
    exit 1
fi

python_version=$(python3 --version | awk '{print $2}')
echo -e "${GREEN}✓ Python $python_version encontrado${NC}"
echo ""

# Actualizar pip
echo -e "${BLUE}📦 Actualizando pip...${NC}"
python3 -m pip install --upgrade pip --quiet
echo -e "${GREEN}✓ pip actualizado${NC}"
echo ""

# Instalar dependencias de desarrollo
echo -e "${BLUE}📦 Instalando dependencias de desarrollo...${NC}"
pip install pre-commit pytest pytest-cov pytest-xdist flake8 black isort mypy bandit safety --quiet
echo -e "${GREEN}✓ Dependencias instaladas${NC}"
echo ""

# Configurar pre-commit
echo -e "${BLUE}🔧 Configurando pre-commit hooks...${NC}"
pre-commit install
pre-commit install --hook-type commit-msg
echo -e "${GREEN}✓ Pre-commit hooks instalados${NC}"
echo ""

# Ejecutar pre-commit en todos los archivos (primera vez)
echo -e "${BLUE}🔄 Ejecutando pre-commit en todos los archivos (esto puede tardar)...${NC}"
pre-commit run --all-files || true
echo -e "${GREEN}✓ Pre-commit ejecutado${NC}"
echo ""

# Ejecutar tests
echo -e "${BLUE}🧪 Ejecutando tests...${NC}"
pytest tests/ -v --maxfail=3 || true
echo -e "${GREEN}✓ Tests ejecutados${NC}"
echo ""

# Generar reporte de cobertura
echo -e "${BLUE}📊 Generando reporte de cobertura...${NC}"
pytest tests/ --cov=. --cov-report=html --cov-report=term-missing --quiet || true
echo -e "${GREEN}✓ Reporte generado en htmlcov/index.html${NC}"
echo ""

# Verificar que no hay prints
echo -e "${BLUE}🔍 Verificando print statements...${NC}"
print_count=$(grep -rn "print(" --include="*.py" --exclude-dir=venv --exclude-dir=.venv --exclude-dir=tests --exclude=logger_config.py . | wc -l || echo "0")
if [ "$print_count" -eq "0" ]; then
    echo -e "${GREEN}✓ No se encontraron print statements en producción${NC}"
else
    echo -e "${YELLOW}⚠️  Se encontraron $print_count print statements. Considera migrarlos a logger.${NC}"
fi
echo ""

# Resumen
echo "═══════════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ CI/CD configurado exitosamente!${NC}"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "📚 Comandos disponibles:"
echo ""
echo "  make help          - Ver todos los comandos"
echo "  make test          - Ejecutar tests"
echo "  make coverage      - Generar reporte de cobertura"
echo "  make format        - Formatear código"
echo "  make lint          - Ejecutar linters"
echo "  make ci-local      - Simular CI localmente"
echo ""
echo "📖 Documentación: CI_CD.md"
echo ""
echo "🎯 Próximos pasos:"
echo "  1. Revisar CI_CD.md para más información"
echo "  2. Ejecutar 'make test' para verificar tests"
echo "  3. Ejecutar 'make coverage' para ver cobertura"
echo "  4. Hacer un commit para probar pre-commit hooks"
echo ""
echo -e "${BLUE}Happy coding! 🚀${NC}"

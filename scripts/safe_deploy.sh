#!/bin/bash
#
# Script de Deployment Seguro a Producción
# Valida SIEMPRE antes de desplegar
#
# Uso: ./scripts/safe_deploy.sh archivo1.py archivo2.py ...
#

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                               ║"
echo "║      🛡️  DEPLOYMENT SEGURO A PRODUCCIÓN                      ║"
echo "║      Validación automática integrada                          ║"
echo "║                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# Verificar que se proporcionaron archivos
if [ $# -eq 0 ]; then
    echo -e "${RED}❌ Error: Debes especificar los archivos a desplegar${NC}"
    echo ""
    echo "Uso: $0 archivo1.py archivo2.py ..."
    echo ""
    echo "Ejemplo:"
    echo "  $0 factura.py tickets.py productos.py"
    echo ""
    exit 1
fi

FILES="$@"

echo -e "${BLUE}📂 Archivos a desplegar:${NC}"
for file in $FILES; do
    echo "  • $file"
done
echo ""

# FASE 1: VALIDACIÓN
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  FASE 1: VALIDACIÓN DE SEGURIDAD${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo ""

if ! /var/www/html/scripts/validate_before_deploy.sh $FILES; then
    echo ""
    echo -e "${RED}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ❌ DEPLOYMENT ABORTADO - ERRORES EN VALIDACIÓN              ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Los archivos contienen errores. Corrígelos antes de desplegar.${NC}"
    echo ""
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Validación exitosa - Procediendo con el deployment${NC}"
echo ""
sleep 2

# FASE 2: DEPLOYMENT
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  FASE 2: DEPLOYMENT A SERVIDORES DE PRODUCCIÓN${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo ""

SERVERS=("192.168.1.55" "192.168.1.18")

for SERVER in "${SERVERS[@]}"; do
    echo -e "${BLUE}📡 Desplegando a servidor: $SERVER${NC}"
    
    for FILE in $FILES; do
        BASENAME=$(basename "$FILE")
        echo -e "  📄 Desplegando: $BASENAME"
        
        # SCP con verificación
        if sshpass -p 'sami' scp -o StrictHostKeyChecking=no "$FILE" "sami@$SERVER:/tmp/$BASENAME.new" 2>&1 | grep -v "Warning"; then
            # Copiar con sudo
            if sshpass -p 'sami' ssh -o StrictHostKeyChecking=no "sami@$SERVER" "echo 'sami' | sudo -S cp /tmp/$BASENAME.new /var/www/html/$BASENAME" 2>&1 | grep -v "password"; then
                echo -e "  ${GREEN}✓${NC} $BASENAME desplegado en $SERVER"
            else
                echo -e "  ${RED}✗${NC} Error al copiar $BASENAME en $SERVER"
                exit 1
            fi
        else
            echo -e "  ${RED}✗${NC} Error al transferir $BASENAME a $SERVER"
            exit 1
        fi
    done
    
    # Reiniciar Apache
    echo -e "  🔄 Reiniciando Apache..."
    if sshpass -p 'sami' ssh -o StrictHostKeyChecking=no "sami@$SERVER" "echo 'sami' | sudo -S systemctl restart apache2" 2>&1 | grep -v "password"; then
        echo -e "  ${GREEN}✓${NC} Apache reiniciado en $SERVER"
    else
        echo -e "  ${RED}✗${NC} Error al reiniciar Apache en $SERVER"
        exit 1
    fi
    
    echo -e "  ${GREEN}✅ $SERVER completado${NC}"
    echo ""
done

# FASE 3: VERIFICACIÓN POST-DEPLOYMENT
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  FASE 3: VERIFICACIÓN POST-DEPLOYMENT${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
echo ""

echo "⏱  Esperando 5 segundos para que Apache recargue..."
sleep 5
echo ""

# Verificar endpoints críticos
ENDPOINTS=(
    "conciliacion/notificaciones"
    "facturas/paginado?page=1&page_size=1"
    "ingresos_gastos_totales?anio=2025&mes=10"
)

echo -e "${BLUE}🔍 Verificando endpoints en 192.168.1.18:${NC}"
FAILED=0

for ENDPOINT in "${ENDPOINTS[@]}"; do
    HTTP_CODE=$(sshpass -p 'sami' ssh -o StrictHostKeyChecking=no sami@192.168.1.18 \
                "curl -s -o /dev/null -w '%{http_code}' http://localhost:5001/api/$ENDPOINT" 2>&1)
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "  ${GREEN}✓${NC} /api/$ENDPOINT → HTTP $HTTP_CODE"
    else
        echo -e "  ${RED}✗${NC} /api/$ENDPOINT → HTTP $HTTP_CODE"
        FAILED=$((FAILED + 1))
    fi
done

echo ""

if [ $FAILED -gt 0 ]; then
    echo -e "${RED}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ⚠️  DEPLOYMENT COMPLETADO CON WARNINGS                      ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Archivos desplegados, pero algunos endpoints no responden correctamente.${NC}"
    echo -e "${YELLOW}Revisa los logs de Apache:${NC}"
    echo ""
    echo "  sshpass -p 'sami' ssh sami@192.168.1.18 \"sudo tail -50 /var/log/apache2/error.log\""
    echo ""
    exit 1
else
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ DEPLOYMENT COMPLETADO EXITOSAMENTE                       ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}✓ Archivos desplegados en ambos servidores${NC}"
    echo -e "${GREEN}✓ Apache reiniciado correctamente${NC}"
    echo -e "${GREEN}✓ Todos los endpoints verificados (HTTP 200)${NC}"
    echo ""
    echo -e "${CYAN}🎉 Producción actualizada y funcionando correctamente${NC}"
    echo ""
fi

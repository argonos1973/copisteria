#!/bin/bash
# =====================================================
# SCRIPT PARA APLICAR ÍNDICES A TODAS LAS BDs
# Fecha: 2025-11-21
# =====================================================

set -e  # Salir si hay errores

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===== OPTIMIZANDO ÍNDICES EN TODAS LAS BDs =====${NC}"
echo ""

# Directorio de trabajo
SCRIPT_DIR="/var/www/html/scripts"
DB_DIR="/var/www/html/db"
BACKUP_SUFFIX="_backup_$(date +%Y%m%d_%H%M%S)"

# Contador
TOTAL_DBS=0
SUCCESS_DBS=0
FAILED_DBS=0

# Buscar todas las bases de datos
echo -e "${YELLOW}Buscando bases de datos...${NC}"
DBS=$(find "$DB_DIR" -name "*.db" -type f | grep -v backup)

for db_path in $DBS; do
    db_name=$(basename "$db_path")
    db_dir=$(dirname "$db_path")
    
    echo ""
    echo -e "${BLUE}=================================================${NC}"
    echo -e "${BLUE}Procesando: ${YELLOW}$db_name${NC}"
    echo -e "${BLUE}Ruta: ${db_path}${NC}"
    echo -e "${BLUE}=================================================${NC}"
    
    TOTAL_DBS=$((TOTAL_DBS + 1))
    
    # Crear backup
    echo -e "${YELLOW}📋 Creando backup...${NC}"
    cp "$db_path" "${db_path}${BACKUP_SUFFIX}"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Backup creado: ${db_name}${BACKUP_SUFFIX}${NC}"
    else
        echo -e "${RED}❌ Error creando backup de $db_name${NC}"
        FAILED_DBS=$((FAILED_DBS + 1))
        continue
    fi
    
    # Verificar si la BD es válida
    echo -e "${YELLOW}🔍 Verificando integridad de la BD...${NC}"
    sqlite3 "$db_path" "PRAGMA integrity_check;" > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ BD corrupta o inválida: $db_name - SALTANDO${NC}"
        FAILED_DBS=$((FAILED_DBS + 1))
        continue
    fi
    
    # Verificar si tiene las tablas principales
    echo -e "${YELLOW}📊 Verificando estructura de tablas...${NC}"
    TABLES=$(sqlite3 "$db_path" "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name IN ('gastos', 'factura', 'tickets', 'contactos');" 2>/dev/null)
    
    if [ -z "$TABLES" ] || [ "$TABLES" -eq 0 ]; then
        echo -e "${YELLOW}⚠️  BD sin tablas principales (usuarios/sistema): $db_name - SALTANDO${NC}"
        rm "${db_path}${BACKUP_SUFFIX}"  # Eliminar backup innecesario
        continue
    fi
    
    echo -e "${GREEN}✅ BD válida con $TABLES tablas principales${NC}"
    
    # Mostrar índices antes
    echo -e "${YELLOW}📋 Índices antes:${NC}"
    INDICES_ANTES=$(sqlite3 "$db_path" "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%';" 2>/dev/null)
    echo -e "${BLUE}   Índices idx_*: $INDICES_ANTES${NC}"
    
    # Aplicar fix de contactos (más seguro)
    echo -e "${YELLOW}🔧 Aplicando índices optimizados...${NC}"
    if sqlite3 "$db_path" < "$SCRIPT_DIR/fix_contactos_indices.sql" 2>/dev/null; then
        echo -e "${GREEN}✅ Índices aplicados correctamente${NC}"
        
        # Mostrar índices después
        INDICES_DESPUES=$(sqlite3 "$db_path" "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%';" 2>/dev/null)
        NUEVOS_INDICES=$((INDICES_DESPUES - INDICES_ANTES))
        
        echo -e "${GREEN}📈 Resultado:${NC}"
        echo -e "${BLUE}   Índices antes: $INDICES_ANTES${NC}"
        echo -e "${BLUE}   Índices después: $INDICES_DESPUES${NC}"
        echo -e "${GREEN}   Nuevos índices: $NUEVOS_INDICES${NC}"
        
        SUCCESS_DBS=$((SUCCESS_DBS + 1))
        
        # Verificar integridad post-optimización
        sqlite3 "$db_path" "PRAGMA integrity_check;" > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Integridad verificada post-optimización${NC}"
        else
            echo -e "${RED}❌ Error de integridad post-optimización - RESTAURANDO BACKUP${NC}"
            cp "${db_path}${BACKUP_SUFFIX}" "$db_path"
            FAILED_DBS=$((FAILED_DBS + 1))
            SUCCESS_DBS=$((SUCCESS_DBS - 1))
        fi
        
    else
        echo -e "${RED}❌ Error aplicando índices a $db_name${NC}"
        echo -e "${YELLOW}🔄 Restaurando desde backup...${NC}"
        cp "${db_path}${BACKUP_SUFFIX}" "$db_path"
        FAILED_DBS=$((FAILED_DBS + 1))
    fi
done

echo ""
echo -e "${BLUE}===== RESUMEN FINAL =====${NC}"
echo -e "${BLUE}Total BDs procesadas: $TOTAL_DBS${NC}"
echo -e "${GREEN}Exitosas: $SUCCESS_DBS${NC}"
echo -e "${RED}Fallidas: $FAILED_DBS${NC}"

if [ $SUCCESS_DBS -gt 0 ]; then
    echo ""
    echo -e "${GREEN}🎉 OPTIMIZACIÓN COMPLETADA${NC}"
    echo -e "${YELLOW}📋 Backups creados con sufijo: ${BACKUP_SUFFIX}${NC}"
    echo ""
    echo -e "${BLUE}Resumen por BD:${NC}"
    for db_path in $DBS; do
        db_name=$(basename "$db_path")
        if [ -f "$db_path" ]; then
            INDICES=$(sqlite3 "$db_path" "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%';" 2>/dev/null || echo "ERROR")
            echo -e "${BLUE}  $db_name: $INDICES índices idx_*${NC}"
        fi
    done
fi

echo ""
echo -e "${BLUE}Para limpiar backups antiguos:${NC}"
echo -e "${YELLOW}find /var/www/html/db -name '*_backup_*' -type f -mtime +7 -delete${NC}"

-- =====================================================
-- SCRIPT DE ROLLBACK - ÍNDICES OPTIMIZADOS V2
-- Fecha: 2025-11-21
-- Descripción: Elimina los índices creados por indices_optimizados_v2.sql
-- =====================================================

-- =====================================================
-- VERIFICACIÓN INICIAL
-- =====================================================

.echo on
.headers on
SELECT '===== INICIANDO ROLLBACK DE ÍNDICES =====' as INFO;
SELECT COUNT(*) as Indices_Antes FROM sqlite_master WHERE type = 'index';

-- =====================================================
-- ELIMINAR ÍNDICES DE TABLA GASTOS
-- =====================================================

DROP INDEX IF EXISTS idx_gastos_fecha_operacion_importe;
DROP INDEX IF EXISTS idx_gastos_importe_signo;
DROP INDEX IF EXISTS idx_gastos_fecha_valor_optimized;
DROP INDEX IF EXISTS idx_gastos_conciliacion;
DROP INDEX IF EXISTS idx_gastos_fecha_operacion_iso;
DROP INDEX IF EXISTS idx_gastos_año_mes;

-- Restaurar índice anterior si fue eliminado
CREATE INDEX IF NOT EXISTS idx_gastos_fecha_valor_iso
ON gastos (date(substr(fecha_valor,7,4)||'-'||substr(fecha_valor,4,2)||'-'||substr(fecha_valor,1,2)));

-- =====================================================
-- ELIMINAR ÍNDICES DE TABLA FACTURA
-- =====================================================

DROP INDEX IF EXISTS idx_factura_numero_estado;
DROP INDEX IF EXISTS idx_factura_fechaCobro;
DROP INDEX IF EXISTS idx_factura_estado_total;
DROP INDEX IF EXISTS idx_factura_verifactu;
DROP INDEX IF EXISTS idx_factura_año;
DROP INDEX IF EXISTS idx_factura_join_contacto;

-- =====================================================
-- ELIMINAR ÍNDICES DE TABLA TICKETS
-- =====================================================

DROP INDEX IF EXISTS idx_tickets_fecha_formaPago_estado;
DROP INDEX IF EXISTS idx_tickets_tpv;
DROP INDEX IF EXISTS idx_tickets_efectivo;
DROP INDEX IF EXISTS idx_tickets_cobrados;
DROP INDEX IF EXISTS idx_tickets_año_mes;

-- =====================================================
-- ELIMINAR ÍNDICES DE TABLA CONTACTOS
-- =====================================================

DROP INDEX IF EXISTS idx_contactos_id_razon;
DROP INDEX IF EXISTS idx_contactos_nif;
DROP INDEX IF EXISTS idx_contactos_busqueda;

-- =====================================================
-- ELIMINAR ÍNDICES DE TABLA CONCILIACION_GASTOS
-- =====================================================

DROP INDEX IF EXISTS idx_conciliacion_gastos_gasto_estado;
DROP INDEX IF EXISTS idx_conciliacion_fecha;

-- Nota: NO eliminamos estos índices porque pueden ser del sistema original
-- idx_conciliacion_gasto
-- idx_conciliacion_estado
-- idx_conciliacion_documento
-- idx_conciliacion_notificado

-- =====================================================
-- ELIMINAR ÍNDICES DE PROVEEDORES
-- =====================================================

DROP INDEX IF EXISTS idx_proveedores_busqueda;
DROP INDEX IF EXISTS idx_facturas_proveedores_fecha_estado;

-- =====================================================
-- ELIMINAR ÍNDICES DE JOINS
-- =====================================================

DROP INDEX IF EXISTS idx_detalle_factura_join;
DROP INDEX IF EXISTS idx_detalle_tickets_join;

-- =====================================================
-- VERIFICACIÓN FINAL
-- =====================================================

SELECT '===== ROLLBACK COMPLETADO =====' as INFO;
SELECT COUNT(*) as Indices_Despues FROM sqlite_master WHERE type = 'index';

-- Mostrar índices restantes en tablas principales
SELECT '===== ÍNDICES RESTANTES =====' as INFO;
SELECT 
    tbl_name as Tabla,
    COUNT(*) as Num_Indices
FROM sqlite_master 
WHERE type = 'index' 
AND tbl_name IN ('gastos', 'factura', 'tickets', 'contactos', 'conciliacion_gastos')
GROUP BY tbl_name
ORDER BY tbl_name;

-- Listar índices específicos que permanecen
SELECT name, tbl_name 
FROM sqlite_master 
WHERE type = 'index' 
AND tbl_name IN ('gastos', 'factura', 'tickets', 'contactos', 'conciliacion_gastos')
ORDER BY tbl_name, name;

-- =====================================================
-- LIMPIEZA Y OPTIMIZACIÓN POST-ROLLBACK
-- =====================================================

-- Analizar tablas para actualizar estadísticas después del rollback
ANALYZE gastos;
ANALYZE factura;
ANALYZE tickets;
ANALYZE contactos;
ANALYZE conciliacion_gastos;

-- =====================================================
-- NOTAS DE ROLLBACK
-- =====================================================

/*
IMPORTANTE:
- Este script elimina SOLO los índices creados por indices_optimizados_v2.sql
- Los índices del sistema original se mantienen intactos
- Se restaura idx_gastos_fecha_valor_iso si fue modificado

EJECUCIÓN:
sqlite3 /var/www/html/db/plantilla.db < rollback_indices_v2.sql

VERIFICACIÓN POST-ROLLBACK:
1. Verificar que las consultas siguen funcionando
2. Confirmar que los índices esenciales permanecen
3. Monitorear rendimiento para detectar degradación

Si hay problemas después del rollback:
- Ejecutar: sqlite3 /var/www/html/db/plantilla.db < /var/www/html/scripts/optimizar_indices_database.sql
- Esto restaurará los índices básicos necesarios
*/

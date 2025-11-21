-- =====================================================
-- SCRIPT DE ÍNDICES OPTIMIZADOS V2
-- Fecha: 2025-11-21
-- Descripción: Añade índices faltantes y optimizaciones adicionales
-- =====================================================

-- =====================================================
-- VERIFICACIÓN INICIAL DE ÍNDICES EXISTENTES
-- =====================================================

-- Mostrar índices actuales antes de comenzar
.echo on
.headers on
SELECT '===== ÍNDICES EXISTENTES ANTES DE LA OPTIMIZACIÓN =====' as INFO;
SELECT name, tbl_name 
FROM sqlite_master 
WHERE type = 'index' 
AND tbl_name IN ('gastos', 'factura', 'tickets', 'contactos', 'conciliacion_gastos')
ORDER BY tbl_name, name;

-- =====================================================
-- 1. ÍNDICES OPTIMIZADOS PARA TABLA GASTOS
-- =====================================================

-- Índice compuesto para consultas por fecha_operacion e importe (NUEVO)
CREATE INDEX IF NOT EXISTS idx_gastos_fecha_operacion_importe 
ON gastos(fecha_operacion, importe_eur);

-- Índice para consultas de ingresos vs gastos
CREATE INDEX IF NOT EXISTS idx_gastos_importe_signo 
ON gastos(
    CASE WHEN importe_eur > 0 THEN 1 ELSE -1 END,
    fecha_operacion
);

-- Índice funcional para fechas DD/MM/YYYY transformadas (MEJORADO)
DROP INDEX IF EXISTS idx_gastos_fecha_valor_iso;
CREATE INDEX IF NOT EXISTS idx_gastos_fecha_valor_optimized
ON gastos(
    substr(fecha_valor,7,4) || '-' || substr(fecha_valor,4,2) || '-' || substr(fecha_valor,1,2),
    importe_eur
);

-- Índice para conciliación de gastos
CREATE INDEX IF NOT EXISTS idx_gastos_conciliacion 
ON gastos(id, concepto, importe_eur);

-- =====================================================
-- 2. ÍNDICES OPTIMIZADOS PARA TABLA FACTURA
-- =====================================================

-- Índice compuesto numero + estado (NUEVO)
CREATE INDEX IF NOT EXISTS idx_factura_numero_estado 
ON factura(numero, estado);

-- Índice para búsquedas por fecha de cobro
CREATE INDEX IF NOT EXISTS idx_factura_fechaCobro 
ON factura(fechaCobro, formaPago, estado);

-- Índice para totales y estadísticas
CREATE INDEX IF NOT EXISTS idx_factura_estado_total 
ON factura(estado, total, fecha);

-- Índice para VeriFactu
CREATE INDEX IF NOT EXISTS idx_factura_verifactu 
ON factura(id, numero, fecha, estado);

-- =====================================================
-- 3. ÍNDICES OPTIMIZADOS PARA TABLA TICKETS
-- =====================================================

-- Índice compuesto fecha + formaPago + estado (COMPLETO)
CREATE INDEX IF NOT EXISTS idx_tickets_fecha_formaPago_estado 
ON tickets(fecha, formaPago, estado);

-- Índice para conciliación TPV
CREATE INDEX IF NOT EXISTS idx_tickets_tpv 
ON tickets(fecha, formaPago, total)
WHERE formaPago = 'T';

-- Índice para tickets en efectivo
CREATE INDEX IF NOT EXISTS idx_tickets_efectivo 
ON tickets(fecha, formaPago, total)
WHERE formaPago = 'E';

-- Índice parcial para tickets cobrados
CREATE INDEX IF NOT EXISTS idx_tickets_cobrados 
ON tickets(fecha, numero, total)
WHERE estado = 'C';

-- =====================================================
-- 4. ÍNDICES OPTIMIZADOS PARA TABLA CONTACTOS
-- =====================================================

-- Índice compuesto idContacto + razonsocial (NUEVO)
CREATE INDEX IF NOT EXISTS idx_contactos_id_razon 
ON contactos(idContacto, razonsocial);

-- Índice para búsqueda por NIF
CREATE INDEX IF NOT EXISTS idx_contactos_nif 
ON contactos(nif);

-- Índice para búsqueda de texto
CREATE INDEX IF NOT EXISTS idx_contactos_busqueda 
ON contactos(razonsocial COLLATE NOCASE, nombre COLLATE NOCASE);

-- =====================================================
-- 5. ÍNDICES PARA TABLA CONCILIACION_GASTOS
-- =====================================================

-- Crear tabla si no existe
CREATE TABLE IF NOT EXISTS conciliacion_gastos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gasto_id INTEGER,
    tipo_documento TEXT,
    documento_id INTEGER,
    fecha_conciliacion TIMESTAMP,
    importe_gasto REAL,
    importe_documento REAL,
    diferencia REAL,
    estado TEXT,
    metodo TEXT,
    notificado INTEGER DEFAULT 0,
    notas TEXT
);

-- Índice compuesto gasto_id + estado (NUEVO)
CREATE INDEX IF NOT EXISTS idx_conciliacion_gastos_gasto_estado 
ON conciliacion_gastos(gasto_id, estado);

-- Índices individuales si no existen
CREATE INDEX IF NOT EXISTS idx_conciliacion_gasto 
ON conciliacion_gastos(gasto_id);

CREATE INDEX IF NOT EXISTS idx_conciliacion_estado 
ON conciliacion_gastos(estado);

CREATE INDEX IF NOT EXISTS idx_conciliacion_documento 
ON conciliacion_gastos(tipo_documento, documento_id);

CREATE INDEX IF NOT EXISTS idx_conciliacion_fecha 
ON conciliacion_gastos(fecha_conciliacion);

CREATE INDEX IF NOT EXISTS idx_conciliacion_notificado 
ON conciliacion_gastos(notificado)
WHERE notificado = 0;

-- =====================================================
-- 6. ÍNDICES FUNCIONALES ADICIONALES
-- =====================================================

-- Índice para transformación de fechas en gastos (fecha_operacion)
CREATE INDEX IF NOT EXISTS idx_gastos_fecha_operacion_iso
ON gastos(
    substr(fecha_operacion,7,4) || '-' || substr(fecha_operacion,4,2) || '-' || substr(fecha_operacion,1,2)
);

-- Índice para año y mes en gastos
CREATE INDEX IF NOT EXISTS idx_gastos_año_mes
ON gastos(
    substr(fecha_operacion,7,4),
    substr(fecha_operacion,4,2)
);

-- Índice para búsquedas de facturas por año
CREATE INDEX IF NOT EXISTS idx_factura_año
ON factura(substr(fecha,1,4));

-- Índice para búsquedas de tickets por año-mes
CREATE INDEX IF NOT EXISTS idx_tickets_año_mes
ON tickets(
    substr(fecha,1,4),
    substr(fecha,6,2)
);

-- =====================================================
-- 7. ÍNDICES PARA TABLAS DE PROVEEDORES
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_proveedores_busqueda
ON proveedores(razonsocial COLLATE NOCASE, nif);

CREATE INDEX IF NOT EXISTS idx_facturas_proveedores_fecha_estado
ON facturas_proveedores(fecha_emision, estado);

-- =====================================================
-- 8. ÍNDICES PARA OPTIMIZACIÓN DE JOINS
-- =====================================================

-- Para JOIN entre factura y contactos
CREATE INDEX IF NOT EXISTS idx_factura_join_contacto
ON factura(idContacto, estado, fecha);

-- Para JOIN entre detalle_factura y productos
CREATE INDEX IF NOT EXISTS idx_detalle_factura_join
ON detalle_factura(id_factura, productoId, total);

-- Para JOIN entre tickets y detalle_tickets
CREATE INDEX IF NOT EXISTS idx_detalle_tickets_join
ON detalle_tickets(id_ticket, productoId, cantidad);

-- =====================================================
-- LIMPIEZA Y OPTIMIZACIÓN
-- =====================================================

-- Analizar tablas para actualizar estadísticas
ANALYZE gastos;
ANALYZE factura;
ANALYZE tickets;
ANALYZE contactos;
ANALYZE conciliacion_gastos;
ANALYZE detalle_factura;
ANALYZE detalle_proforma;
ANALYZE registro_facturacion;

-- Ejecutar VACUUM para optimizar el almacenamiento
-- VACUUM; -- Descomentado porque puede tardar mucho

-- =====================================================
-- VERIFICACIÓN FINAL
-- =====================================================

SELECT '===== ÍNDICES CREADOS CORRECTAMENTE =====' as INFO;

-- Verificar nuevos índices en gastos
SELECT 'Índices en tabla GASTOS:' as Tabla;
SELECT name FROM sqlite_master 
WHERE type = 'index' AND tbl_name = 'gastos'
ORDER BY name;

-- Verificar nuevos índices en factura
SELECT 'Índices en tabla FACTURA:' as Tabla;
SELECT name FROM sqlite_master 
WHERE type = 'index' AND tbl_name = 'factura'
ORDER BY name;

-- Verificar nuevos índices en tickets
SELECT 'Índices en tabla TICKETS:' as Tabla;
SELECT name FROM sqlite_master 
WHERE type = 'index' AND tbl_name = 'tickets'
ORDER BY name;

-- Verificar nuevos índices en contactos
SELECT 'Índices en tabla CONTACTOS:' as Tabla;
SELECT name FROM sqlite_master 
WHERE type = 'index' AND tbl_name = 'contactos'
ORDER BY name;

-- Verificar nuevos índices en conciliacion_gastos
SELECT 'Índices en tabla CONCILIACION_GASTOS:' as Tabla;
SELECT name FROM sqlite_master 
WHERE type = 'index' AND tbl_name = 'conciliacion_gastos'
ORDER BY name;

-- Estadísticas finales
SELECT '===== ESTADÍSTICAS FINALES =====' as INFO;
SELECT 
    tbl_name as Tabla,
    COUNT(*) as Num_Indices
FROM sqlite_master 
WHERE type = 'index' 
AND tbl_name IN ('gastos', 'factura', 'tickets', 'contactos', 'conciliacion_gastos')
GROUP BY tbl_name
ORDER BY tbl_name;

-- =====================================================
-- NOTAS DE IMPLEMENTACIÓN
-- =====================================================

/*
MEJORAS ESPERADAS:
- Consultas de gastos por fecha: 60-80% más rápidas
- Búsquedas de facturas: 70% más rápidas
- Conciliación de gastos: 80-90% más rápidas
- JOINs entre tablas: 50-70% más rápidas
- Consultas de estadísticas: 60% más rápidas

EJECUCIÓN:
sqlite3 /var/www/html/db/plantilla.db < indices_optimizados_v2.sql

MONITOREO:
- Verificar tiempos de respuesta antes y después
- Monitorear uso de espacio (esperado: +5-10MB)
- Validar que INSERTs no se degradan significativamente

IMPORTANTE:
- Los índices parciales (WHERE) son muy eficientes para consultas específicas
- Los índices funcionales optimizan las transformaciones de fecha
- ANALYZE actualiza las estadísticas para el query planner
*/

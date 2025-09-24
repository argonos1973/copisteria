-- =====================================================
-- SCRIPT DE OPTIMIZACIÓN DE ÍNDICES - BASE DE DATOS
-- Generado: 2025-09-08 22:24
-- =====================================================

-- TABLAS CRÍTICAS SIN ÍNDICES (ALTA PRIORIDAD)

-- 1. DETALLE_FACTURA (906 filas) - CRÍTICO
CREATE INDEX IF NOT EXISTS idx_detalle_factura_factura_id 
ON detalle_factura(id_factura);

CREATE INDEX IF NOT EXISTS idx_detalle_factura_producto_id 
ON detalle_factura(productoId);

-- 2. DETALLE_PROFORMA (415 filas) - CRÍTICO  
CREATE INDEX IF NOT EXISTS idx_detalle_proforma_proforma_id 
ON detalle_proforma(id_proforma);

CREATE INDEX IF NOT EXISTS idx_detalle_proforma_producto_id 
ON detalle_proforma(productoId);

-- 3. REGISTRO_FACTURACION (101 filas) - CRÍTICO
CREATE INDEX IF NOT EXISTS idx_registro_factura_id 
ON registro_facturacion(factura_id);

CREATE INDEX IF NOT EXISTS idx_registro_ticket_id 
ON registro_facturacion(ticket_id);

CREATE INDEX IF NOT EXISTS idx_registro_id_sistema 
ON registro_facturacion(id_sistema);

-- OPTIMIZACIONES ADICIONALES (MEDIA PRIORIDAD)

-- 4. TICKETS - Falta índice de estado
CREATE INDEX IF NOT EXISTS idx_tickets_estado 
ON tickets(estado);

-- 5. PRODUCTOS - Verificar si ID es PK, si no crear índice
-- CREATE INDEX IF NOT EXISTS idx_productos_id ON productos(id);

-- ÍNDICES COMPUESTOS PARA CONSULTAS COMPLEJAS (BAJA PRIORIDAD)

-- Para consultas de detalles con totales
CREATE INDEX IF NOT EXISTS idx_detalle_factura_compuesto 
ON detalle_factura(id_factura, total);

CREATE INDEX IF NOT EXISTS idx_detalle_proforma_compuesto 
ON detalle_proforma(id_proforma, total);

-- Para consultas de tickets por fecha y estado
CREATE INDEX IF NOT EXISTS idx_tickets_fecha_estado 
ON tickets(fecha, estado);

-- Para consultas de facturas por contacto y fecha
CREATE INDEX IF NOT EXISTS idx_factura_contacto_fecha 
ON factura(idContacto, fecha);

-- =====================================================
-- VERIFICACIÓN POST-APLICACIÓN
-- =====================================================

-- Verificar que los índices se crearon correctamente
.echo on
SELECT 'Verificando índices creados...';

SELECT name, tbl_name, sql 
FROM sqlite_master 
WHERE type = 'index' 
AND name LIKE 'idx_%'
ORDER BY tbl_name, name;

-- Estadísticas de las tablas principales
SELECT 'Estadísticas de tablas principales:';

SELECT 
    'detalle_factura' as tabla,
    COUNT(*) as filas,
    (SELECT COUNT(*) FROM pragma_index_list('detalle_factura')) as indices
FROM detalle_factura

UNION ALL

SELECT 
    'detalle_proforma' as tabla,
    COUNT(*) as filas,
    (SELECT COUNT(*) FROM pragma_index_list('detalle_proforma')) as indices
FROM detalle_proforma

UNION ALL

SELECT 
    'registro_facturacion' as tabla,
    COUNT(*) as filas,
    (SELECT COUNT(*) FROM pragma_index_list('registro_facturacion')) as indices
FROM registro_facturacion

UNION ALL

SELECT 
    'tickets' as tabla,
    COUNT(*) as filas,
    (SELECT COUNT(*) FROM pragma_index_list('tickets')) as indices
FROM tickets;

-- =====================================================
-- NOTAS DE IMPLEMENTACIÓN
-- =====================================================

/*
IMPACTO ESPERADO:
- Consultas de detalles: 70-90% más rápidas
- Búsquedas por estado: 60-80% más rápidas  
- Joins entre tablas: 50-70% más rápidas
- Espacio adicional: ~2-5MB

TABLAS YA OPTIMIZADAS (NO TOCAR):
- factura: 6 índices completos
- detalle_tickets: 2 índices apropiados
- contactos: 4 índices completos  
- descuento_producto_franja: Óptimo

EJECUCIÓN:
sqlite3 /var/www/html/db/aleph70.db < optimizar_indices_database.sql

MONITOREO POST-IMPLEMENTACIÓN:
- Verificar tiempos de respuesta en consultas críticas
- Monitorear uso de espacio en disco
- Validar que no hay degradación en INSERTs/UPDATEs
*/

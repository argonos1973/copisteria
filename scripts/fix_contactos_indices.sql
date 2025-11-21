-- =====================================================
-- FIX: ÍNDICES CORREGIDOS PARA TABLA CONTACTOS
-- Fecha: 2025-11-21
-- =====================================================

.echo on

SELECT '===== CORRIGIENDO ÍNDICES DE CONTACTOS =====' as INFO;

-- Índice compuesto idContacto + razonsocial (CORREGIDO)
CREATE INDEX IF NOT EXISTS idx_contactos_id_razon 
ON contactos(idContacto, razonsocial);

-- Índice para búsqueda por IDENTIFICADOR (NIF/CIF)
CREATE INDEX IF NOT EXISTS idx_contactos_identificador 
ON contactos(identificador);

-- Índice para búsqueda de texto en razonsocial
CREATE INDEX IF NOT EXISTS idx_contactos_busqueda 
ON contactos(razonsocial COLLATE NOCASE);

-- Índice para búsqueda por tipo
CREATE INDEX IF NOT EXISTS idx_contactos_tipo 
ON contactos(tipo);

-- Índice compuesto para optimizar JOINs con factura
CREATE INDEX IF NOT EXISTS idx_contactos_join 
ON contactos(idContacto, razonsocial, identificador);

-- =====================================================
-- COMPLETAR ÍNDICES QUE FALTARON
-- =====================================================

-- Índice compuesto gasto_id + estado para conciliacion_gastos
CREATE INDEX IF NOT EXISTS idx_conciliacion_gastos_gasto_estado 
ON conciliacion_gastos(gasto_id, estado);

-- Índice para fecha de conciliación
CREATE INDEX IF NOT EXISTS idx_conciliacion_fecha 
ON conciliacion_gastos(fecha_conciliacion);

-- Índice para notificados pendientes
CREATE INDEX IF NOT EXISTS idx_conciliacion_notificado 
ON conciliacion_gastos(notificado)
WHERE notificado = 0;

-- =====================================================
-- ÍNDICES FUNCIONALES ADICIONALES
-- =====================================================

-- Índice para transformación de fechas en gastos
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
-- ÍNDICES PARA PROVEEDORES (SI EXISTEN)
-- =====================================================

-- Solo crear si la tabla existe
CREATE INDEX IF NOT EXISTS idx_proveedores_busqueda
ON proveedores(razonsocial COLLATE NOCASE, nif)
WHERE EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='proveedores');

CREATE INDEX IF NOT EXISTS idx_facturas_proveedores_fecha_estado
ON facturas_proveedores(fecha_emision, estado)
WHERE EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='facturas_proveedores');

-- =====================================================
-- ÍNDICES PARA OPTIMIZACIÓN DE JOINS
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
-- ANÁLISIS Y OPTIMIZACIÓN
-- =====================================================

-- Actualizar estadísticas
ANALYZE gastos;
ANALYZE factura;
ANALYZE tickets;
ANALYZE contactos;
ANALYZE conciliacion_gastos;

-- =====================================================
-- VERIFICACIÓN FINAL
-- =====================================================

SELECT '===== ÍNDICES CORREGIDOS Y COMPLETADOS =====' as INFO;

-- Contar índices en contactos
SELECT 'Índices en CONTACTOS: ' || COUNT(*) as Info
FROM sqlite_master 
WHERE type = 'index' AND tbl_name = 'contactos';

-- Contar todos los índices nuevos
SELECT 'Total índices con prefijo idx_: ' || COUNT(*) as Info
FROM sqlite_master 
WHERE type = 'index' AND name LIKE 'idx_%';

-- Mostrar índices de contactos
SELECT name as Indices_Contactos
FROM sqlite_master 
WHERE type = 'index' AND tbl_name = 'contactos'
ORDER BY name;

.echo off

/*
CORRECCIONES APLICADAS:
- identificador en lugar de nif
- Sin columna nombre (solo razonsocial)
- Añadidos índices funcionales faltantes
- Completados índices de conciliación
*/

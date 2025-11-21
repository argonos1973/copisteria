-- =====================================================
-- SCRIPT DE PRUEBA DE RENDIMIENTO - ÍNDICES
-- Fecha: 2025-11-21
-- Descripción: Prueba el rendimiento antes y después de aplicar índices
-- =====================================================

.echo on
.headers on
.timer on

-- =====================================================
-- CONFIGURACIÓN INICIAL
-- =====================================================

-- Activar el query planner para ver qué índices se usan
.eqp on

SELECT '===== PRUEBAS DE RENDIMIENTO - INICIO =====' as INFO;

-- =====================================================
-- TEST 1: GASTOS POR FECHA E IMPORTE
-- =====================================================

SELECT '--- TEST 1: Gastos por fecha e importe ---' as Test;
EXPLAIN QUERY PLAN
SELECT fecha_operacion, concepto, importe_eur
FROM gastos
WHERE fecha_operacion BETWEEN '01/01/2025' AND '31/01/2025'
  AND importe_eur < 0
ORDER BY fecha_operacion, importe_eur
LIMIT 10;

SELECT COUNT(*) as Total_Gastos_Enero
FROM gastos
WHERE fecha_operacion BETWEEN '01/01/2025' AND '31/01/2025'
  AND importe_eur < 0;

-- =====================================================
-- TEST 2: FACTURAS POR NÚMERO Y ESTADO
-- =====================================================

SELECT '--- TEST 2: Facturas por número y estado ---' as Test;
EXPLAIN QUERY PLAN
SELECT numero, fecha, total
FROM factura
WHERE numero LIKE 'F250%'
  AND estado = 'C'
ORDER BY numero;

SELECT COUNT(*) as Facturas_Cobradas_2025
FROM factura
WHERE numero LIKE 'F250%'
  AND estado = 'C';

-- =====================================================
-- TEST 3: TICKETS CON FORMA DE PAGO
-- =====================================================

SELECT '--- TEST 3: Tickets por fecha, forma pago y estado ---' as Test;
EXPLAIN QUERY PLAN
SELECT fecha, numero, total
FROM tickets
WHERE fecha BETWEEN '2025-01-01' AND '2025-01-31'
  AND formaPago = 'T'
  AND estado = 'C'
ORDER BY fecha;

SELECT 
    formaPago,
    COUNT(*) as cantidad,
    SUM(total) as total_importe
FROM tickets
WHERE fecha BETWEEN '2025-01-01' AND '2025-01-31'
  AND estado = 'C'
GROUP BY formaPago;

-- =====================================================
-- TEST 4: JOIN FACTURA-CONTACTOS
-- =====================================================

SELECT '--- TEST 4: Join factura-contactos ---' as Test;
EXPLAIN QUERY PLAN
SELECT f.numero, f.fecha, f.total, c.razonsocial
FROM factura f
INNER JOIN contactos c ON f.idContacto = c.idContacto
WHERE f.estado = 'C'
  AND f.fecha BETWEEN '2025-01-01' AND '2025-01-31'
ORDER BY f.fecha
LIMIT 10;

-- =====================================================
-- TEST 5: CONCILIACIÓN DE GASTOS
-- =====================================================

SELECT '--- TEST 5: Conciliación de gastos ---' as Test;
EXPLAIN QUERY PLAN
SELECT g.fecha_operacion, g.concepto, g.importe_eur, cg.estado
FROM gastos g
LEFT JOIN conciliacion_gastos cg ON g.id = cg.gasto_id
WHERE cg.estado = 'conciliado'
   OR cg.estado IS NULL
ORDER BY g.fecha_operacion DESC
LIMIT 10;

-- =====================================================
-- TEST 6: TRANSFORMACIÓN DE FECHAS
-- =====================================================

SELECT '--- TEST 6: Fechas transformadas ---' as Test;
EXPLAIN QUERY PLAN
SELECT fecha_valor, concepto, importe_eur
FROM gastos
WHERE date(substr(fecha_valor,7,4)||'-'||substr(fecha_valor,4,2)||'-'||substr(fecha_valor,1,2)) 
      BETWEEN '2025-01-01' AND '2025-01-31'
ORDER BY date(substr(fecha_valor,7,4)||'-'||substr(fecha_valor,4,2)||'-'||substr(fecha_valor,1,2))
LIMIT 10;

-- =====================================================
-- TEST 7: ESTADÍSTICAS POR MES
-- =====================================================

SELECT '--- TEST 7: Estadísticas mensuales ---' as Test;
EXPLAIN QUERY PLAN
SELECT 
    substr(fecha_operacion,7,4) as año,
    substr(fecha_operacion,4,2) as mes,
    COUNT(*) as num_movimientos,
    SUM(CASE WHEN importe_eur > 0 THEN importe_eur ELSE 0 END) as ingresos,
    SUM(CASE WHEN importe_eur < 0 THEN ABS(importe_eur) ELSE 0 END) as gastos
FROM gastos
WHERE substr(fecha_operacion,7,4) = '2025'
GROUP BY substr(fecha_operacion,7,4), substr(fecha_operacion,4,2)
ORDER BY año, mes;

-- =====================================================
-- TEST 8: BÚSQUEDA DE CONTACTOS
-- =====================================================

SELECT '--- TEST 8: Búsqueda de contactos ---' as Test;
EXPLAIN QUERY PLAN
SELECT idContacto, razonsocial, nif
FROM contactos
WHERE razonsocial LIKE '%TEST%'
   OR nif LIKE 'A%'
ORDER BY razonsocial
LIMIT 10;

-- =====================================================
-- TEST 9: LIQUIDACIONES TPV
-- =====================================================

SELECT '--- TEST 9: Tickets TPV por fecha ---' as Test;
EXPLAIN QUERY PLAN
SELECT fecha, COUNT(*) as num_tickets, SUM(total) as total
FROM tickets
WHERE fecha BETWEEN '2025-01-01' AND '2025-01-31'
  AND formaPago = 'T'
  AND estado = 'C'
GROUP BY fecha
ORDER BY fecha;

-- =====================================================
-- TEST 10: ANÁLISIS DE USO DE ÍNDICES
-- =====================================================

SELECT '--- TEST 10: Análisis de uso de índices ---' as Test;

-- Mostrar estadísticas de las tablas
SELECT '===== ESTADÍSTICAS DE TABLAS =====' as INFO;
SELECT 
    name as Tabla,
    (SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND tbl_name=m.name) as Num_Indices
FROM sqlite_master m
WHERE type = 'table'
AND name IN ('gastos', 'factura', 'tickets', 'contactos', 'conciliacion_gastos')
ORDER BY name;

-- =====================================================
-- RESUMEN FINAL
-- =====================================================

.timer off
.eqp off

SELECT '===== PRUEBAS DE RENDIMIENTO - FIN =====' as INFO;

/*
INTERPRETACIÓN DE RESULTADOS:
- Si aparece "SCAN TABLE": la consulta no usa índices (LENTO)
- Si aparece "SEARCH TABLE ... USING INDEX": la consulta usa índices (RÁPIDO)
- Si aparece "USING COVERING INDEX": óptimo, todos los datos están en el índice

EJECUTAR ANTES Y DESPUÉS:
1. Antes: sqlite3 /var/www/html/db/plantilla.db < test_indices_performance.sql > antes.txt
2. Aplicar índices: sqlite3 /var/www/html/db/plantilla.db < indices_optimizados_v2.sql
3. Después: sqlite3 /var/www/html/db/plantilla.db < test_indices_performance.sql > despues.txt
4. Comparar: diff antes.txt despues.txt

MÉTRICAS A OBSERVAR:
- Tiempo de ejecución de cada query (Run Time)
- Plan de ejecución (SCAN vs SEARCH)
- Número de filas procesadas
*/

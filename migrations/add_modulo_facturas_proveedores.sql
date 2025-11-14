-- ============================================================================
-- AGREGAR MÓDULO DE FACTURAS RECIBIDAS AL SISTEMA
-- ============================================================================
-- Fecha: 2025-11-14
-- Descripción: Agrega el módulo de facturas de proveedores al menú
-- Base de datos: usuarios_sistema.db

-- Insertar módulo de facturas recibidas
INSERT OR IGNORE INTO modulos (codigo, nombre, ruta, icono, orden, activo) 
VALUES ('facturas_recibidas', 'Facturas Recibidas', '/CONSULTA_FACTURAS_RECIBIDAS.html', '📥', 10, 1);

-- Verificar inserción
SELECT 'Módulo insertado:' as resultado;
SELECT codigo, nombre, ruta, icono, orden FROM modulos WHERE codigo = 'facturas_recibidas';

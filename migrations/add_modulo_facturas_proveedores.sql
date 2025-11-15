-- ============================================================================
-- AGREGAR MÓDULO DE FACTURAS RECIBIDAS AL SISTEMA
-- ============================================================================
-- Fecha: 2025-11-14
-- Descripción: Agrega el módulo de facturas de proveedores al menú
-- Base de datos: usuarios_sistema.db

-- Insertar módulo de facturas recibidas (justo después de Facturas Emitidas)
INSERT OR IGNORE INTO modulos (codigo, nombre, ruta, icono, orden, activo) 
VALUES ('facturas_recibidas', 'Facturas Recibidas', '/CONSULTA_FACTURAS_RECIBIDAS.html', 'fas fa-file-invoice-dollar', 2, 1);

-- Actualizar si ya existe
UPDATE modulos 
SET icono = 'fas fa-file-invoice-dollar', 
    orden = 2
WHERE codigo = 'facturas_recibidas';

-- Reordenar otros módulos para mantener consistencia
UPDATE modulos SET orden = 3 WHERE codigo = 'presupuestos';
UPDATE modulos SET orden = 4 WHERE codigo = 'productos';
UPDATE modulos SET orden = 5 WHERE codigo = 'contactos';
UPDATE modulos SET orden = 6 WHERE codigo = 'gastos';

-- Verificar inserción
SELECT 'Módulo insertado:' as resultado;
SELECT codigo, nombre, ruta, icono, orden FROM modulos WHERE codigo = 'facturas_recibidas';

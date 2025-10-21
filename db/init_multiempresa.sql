-- ============================================================================
-- SISTEMA MULTIEMPRESA - BASE DE DATOS CENTRAL
-- ============================================================================
-- Archivo: db/init_multiempresa.sql
-- Descripción: Crea estructura de BD para sistema multiempresa con autenticación
-- Fecha: 2025-10-21
-- ============================================================================

-- Tabla de empresas
CREATE TABLE IF NOT EXISTS empresas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT UNIQUE NOT NULL,
    nombre TEXT NOT NULL,
    db_path TEXT NOT NULL,
    
    -- Branding
    logo_header TEXT DEFAULT '/static/logos/default_header.png',
    logo_factura TEXT DEFAULT '/static/logos/default_factura.png',
    color_primario TEXT DEFAULT '#2c3e50',
    color_secundario TEXT DEFAULT '#3498db',
    
    -- Datos empresa
    cif TEXT,
    direccion TEXT,
    telefono TEXT,
    email TEXT,
    web TEXT,
    
    -- Control
    activa INTEGER DEFAULT 1,
    fecha_alta DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de usuarios
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    nombre_completo TEXT NOT NULL,
    email TEXT,
    telefono TEXT,
    
    -- Control
    activo INTEGER DEFAULT 1,
    es_superadmin INTEGER DEFAULT 0,
    fecha_alta DATETIME DEFAULT CURRENT_TIMESTAMP,
    ultimo_acceso DATETIME,
    intentos_fallidos INTEGER DEFAULT 0
);

-- Relación usuarios-empresas
CREATE TABLE IF NOT EXISTS usuario_empresa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    empresa_id INTEGER NOT NULL,
    rol TEXT DEFAULT 'usuario', -- 'admin', 'usuario', 'lectura'
    es_admin_empresa INTEGER DEFAULT 0,
    fecha_asignacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
    UNIQUE(usuario_id, empresa_id)
);

-- Tabla de módulos del sistema
CREATE TABLE IF NOT EXISTS modulos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT UNIQUE NOT NULL,
    nombre TEXT NOT NULL,
    ruta TEXT NOT NULL,
    icono TEXT,
    descripcion TEXT,
    orden INTEGER DEFAULT 999,
    activo INTEGER DEFAULT 1
);

-- Permisos de usuarios por módulo y empresa
CREATE TABLE IF NOT EXISTS permisos_usuario_modulo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    empresa_id INTEGER NOT NULL,
    modulo_codigo TEXT NOT NULL,
    
    -- Permisos granulares
    puede_ver INTEGER DEFAULT 0,
    puede_crear INTEGER DEFAULT 0,
    puede_editar INTEGER DEFAULT 0,
    puede_eliminar INTEGER DEFAULT 0,
    puede_anular INTEGER DEFAULT 0,
    puede_exportar INTEGER DEFAULT 0,
    
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
    FOREIGN KEY (modulo_codigo) REFERENCES modulos(codigo) ON DELETE CASCADE,
    UNIQUE(usuario_id, empresa_id, modulo_codigo)
);

-- Configuración flexible por empresa
CREATE TABLE IF NOT EXISTS configuracion_empresa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    categoria TEXT NOT NULL, -- 'estadisticas', 'layout', 'widgets', 'general'
    clave TEXT NOT NULL,
    valor TEXT, -- Formato JSON para datos complejos
    tipo TEXT DEFAULT 'text', -- 'json', 'text', 'boolean', 'number', 'color'
    descripcion TEXT,
    orden INTEGER DEFAULT 999,
    activo INTEGER DEFAULT 1,
    FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
    UNIQUE(empresa_id, categoria, clave)
);

-- Log de auditoría
CREATE TABLE IF NOT EXISTS auditoria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    empresa_id INTEGER,
    accion TEXT NOT NULL,
    modulo TEXT,
    descripcion TEXT,
    ip_address TEXT,
    user_agent TEXT,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    FOREIGN KEY (empresa_id) REFERENCES empresas(id)
);

-- ============================================================================
-- DATOS INICIALES
-- ============================================================================

-- Módulos del sistema
INSERT OR IGNORE INTO modulos (codigo, nombre, ruta, icono, orden) VALUES
('facturas', 'Facturas', '/GESTION_FACTURAS.html', '📋', 1),
('tickets', 'Tickets', '/GESTION_TICKETS.html', '🧾', 2),
('proformas', 'Proformas', '/GESTION_PROFORMAS.html', '📄', 3),
('presupuestos', 'Presupuestos', '/GESTION_PRESUPUESTOS.html', '📝', 4),
('productos', 'Productos', '/GESTION_PRODUCTOS.html', '📦', 5),
('contactos', 'Contactos', '/GESTION_CONTACTOS.html', '👥', 6),
('gastos', 'Gastos', '/CONSULTA_GASTOS.html', '💳', 7),
('conciliacion', 'Conciliación', '/conciliacion.html', '✅', 8),
('estadisticas', 'Estadísticas', '/estadisticas.html', '📊', 9);

-- Empresa por defecto (Copistería)
INSERT OR IGNORE INTO empresas (
    codigo, nombre, db_path,
    color_primario, color_secundario,
    cif, direccion, telefono, email
) VALUES (
    'copisteria',
    'Copistería Aleph70',
    '/var/www/html/db/aleph70.db',
    '#2c3e50',
    '#3498db',
    'B12345678',
    'Calle Principal 123',
    '912345678',
    'info@copisteria.com'
);

-- Usuario admin por defecto
-- Password: admin123 (cambiar en producción)
-- Hash SHA256 de "admin123"
INSERT OR IGNORE INTO usuarios (
    username, password_hash, nombre_completo, 
    activo, es_superadmin
) VALUES (
    'admin',
    '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9',
    'Administrador Sistema',
    1,
    1
);

-- Asignar admin a copistería como admin de empresa
INSERT OR IGNORE INTO usuario_empresa (usuario_id, empresa_id, rol, es_admin_empresa)
SELECT u.id, e.id, 'admin', 1
FROM usuarios u, empresas e
WHERE u.username = 'admin' AND e.codigo = 'copisteria';

-- Permisos totales para admin en todos los módulos
INSERT OR IGNORE INTO permisos_usuario_modulo (
    usuario_id, empresa_id, modulo_codigo,
    puede_ver, puede_crear, puede_editar, puede_eliminar, puede_anular, puede_exportar
)
SELECT 
    u.id, e.id, m.codigo,
    1, 1, 1, 1, 1, 1
FROM usuarios u
CROSS JOIN empresas e
CROSS JOIN modulos m
WHERE u.username = 'admin' AND e.codigo = 'copisteria';

-- Configuración por defecto para copistería
INSERT OR IGNORE INTO configuracion_empresa (empresa_id, categoria, clave, valor, tipo) 
SELECT e.id, 'estadisticas', 'tarjetas', 
    '{"ventas":true,"gastos":true,"balance":true,"clientes":true}',
    'json'
FROM empresas e WHERE e.codigo = 'copisteria';

INSERT OR IGNORE INTO configuracion_empresa (empresa_id, categoria, clave, valor, tipo)
SELECT e.id, 'estadisticas', 'orden_tarjetas',
    '["ventas","gastos","balance","clientes"]',
    'json'
FROM empresas e WHERE e.codigo = 'copisteria';

INSERT OR IGNORE INTO configuracion_empresa (empresa_id, categoria, clave, valor, tipo)
SELECT e.id, 'estadisticas', 'mostrar_proyecciones', 'true', 'boolean'
FROM empresas e WHERE e.codigo = 'copisteria';

-- ============================================================================
-- ÍNDICES PARA OPTIMIZACIÓN
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_usuarios_username ON usuarios(username);
CREATE INDEX IF NOT EXISTS idx_usuarios_activo ON usuarios(activo);
CREATE INDEX IF NOT EXISTS idx_empresas_codigo ON empresas(codigo);
CREATE INDEX IF NOT EXISTS idx_empresas_activa ON empresas(activa);
CREATE INDEX IF NOT EXISTS idx_usuario_empresa_usuario ON usuario_empresa(usuario_id);
CREATE INDEX IF NOT EXISTS idx_usuario_empresa_empresa ON usuario_empresa(empresa_id);
CREATE INDEX IF NOT EXISTS idx_permisos_usuario ON permisos_usuario_modulo(usuario_id, empresa_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_usuario ON auditoria(usuario_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_fecha ON auditoria(fecha);

-- ============================================================================
-- FIN DE SCRIPT
-- ============================================================================

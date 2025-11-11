-- Script de inicialización de base de datos
-- Aleph70 Copistería - Sistema Multiempresa

-- Tabla de contactos
CREATE TABLE IF NOT EXISTS contacto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    email TEXT,
    telefono TEXT,
    direccion TEXT,
    cif TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de productos
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT UNIQUE NOT NULL,
    descripcion TEXT NOT NULL,
    precio REAL NOT NULL,
    iva REAL DEFAULT 21,
    stock INTEGER DEFAULT 0,
    activo INTEGER DEFAULT 1,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de tickets
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT UNIQUE NOT NULL,
    fecha DATE NOT NULL,
    cliente_id INTEGER,
    total REAL NOT NULL,
    iva REAL DEFAULT 21,
    estado TEXT DEFAULT 'pendiente',
    cobrado INTEGER DEFAULT 0,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES contacto (id)
);

-- Tabla de líneas de ticket
CREATE TABLE IF NOT EXISTS ticket_lineas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    producto_id INTEGER,
    descripcion TEXT NOT NULL,
    cantidad INTEGER NOT NULL,
    precio REAL NOT NULL,
    descuento REAL DEFAULT 0,
    iva REAL DEFAULT 21,
    total REAL NOT NULL,
    FOREIGN KEY (ticket_id) REFERENCES tickets (id),
    FOREIGN KEY (producto_id) REFERENCES productos (id)
);

-- Tabla de proformas
CREATE TABLE IF NOT EXISTS proforma (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT UNIQUE NOT NULL,
    fecha DATE NOT NULL,
    cliente_id INTEGER,
    total REAL NOT NULL,
    iva REAL DEFAULT 21,
    estado TEXT DEFAULT 'pendiente',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES contacto (id)
);

-- Tabla de facturas
CREATE TABLE IF NOT EXISTS factura (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT UNIQUE NOT NULL,
    fecha DATE NOT NULL,
    cliente_id INTEGER,
    total REAL NOT NULL,
    iva REAL DEFAULT 21,
    estado TEXT DEFAULT 'pendiente',
    cobrado INTEGER DEFAULT 0,
    fecha_vencimiento DATE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES contacto (id)
);

-- Tabla de líneas de factura
CREATE TABLE IF NOT EXISTS factura_lineas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    factura_id INTEGER NOT NULL,
    producto_id INTEGER,
    descripcion TEXT NOT NULL,
    cantidad INTEGER NOT NULL,
    precio REAL NOT NULL,
    descuento REAL DEFAULT 0,
    iva REAL DEFAULT 21,
    total REAL NOT NULL,
    FOREIGN KEY (factura_id) REFERENCES factura (id),
    FOREIGN KEY (producto_id) REFERENCES productos (id)
);

-- Tabla de presupuestos
CREATE TABLE IF NOT EXISTS presupuesto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT UNIQUE NOT NULL,
    fecha DATE NOT NULL,
    cliente_id INTEGER,
    total REAL NOT NULL,
    iva REAL DEFAULT 21,
    estado TEXT DEFAULT 'pendiente',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES contacto (id)
);

-- Tabla de gastos
CREATE TABLE IF NOT EXISTS gastos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha DATE NOT NULL,
    concepto TEXT NOT NULL,
    importe REAL NOT NULL,
    proveedor TEXT,
    categoria TEXT,
    pagado INTEGER DEFAULT 0,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de configuración
CREATE TABLE IF NOT EXISTS configuracion (
    clave TEXT PRIMARY KEY,
    valor TEXT,
    descripcion TEXT
);

-- Tabla de franjas de descuento
CREATE TABLE IF NOT EXISTS franjas_descuento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cantidad_min INTEGER NOT NULL,
    cantidad_max INTEGER,
    descuento REAL NOT NULL,
    activo INTEGER DEFAULT 1
);

-- Insertar datos de ejemplo
INSERT OR IGNORE INTO configuracion (clave, valor, descripcion) VALUES 
    ('empresa_nombre', 'ALEPH70', 'Nombre de la empresa'),
    ('empresa_cif', 'B12345678', 'CIF de la empresa'),
    ('empresa_direccion', 'Calle Principal 123', 'Dirección de la empresa'),
    ('empresa_telefono', '900123456', 'Teléfono de la empresa'),
    ('empresa_email', 'info@aleph70.com', 'Email de la empresa'),
    ('iva_defecto', '21', 'IVA por defecto'),
    ('serie_factura', 'F', 'Serie de facturas'),
    ('serie_ticket', 'T', 'Serie de tickets'),
    ('ultimo_numero_factura', '250000', 'Último número de factura'),
    ('ultimo_numero_ticket', '1000', 'Último número de ticket');

-- Insertar algunos productos de ejemplo
INSERT OR IGNORE INTO productos (codigo, descripcion, precio, iva) VALUES 
    ('001', 'Fotocopia B/N', 0.05, 21),
    ('002', 'Fotocopia Color', 0.15, 21),
    ('003', 'Encuadernación', 3.50, 21),
    ('004', 'Plastificado A4', 2.00, 21),
    ('005', 'Impresión A3', 0.50, 21);

-- Insertar algunos contactos de ejemplo
INSERT OR IGNORE INTO contacto (nombre, email, telefono, cif) VALUES 
    ('Cliente Genérico', 'cliente@example.com', '600000000', 'B87654321'),
    ('Proveedor Test', 'proveedor@example.com', '900000000', 'A12345678');

-- Crear índices para mejorar rendimiento
CREATE INDEX IF NOT EXISTS idx_factura_fecha ON factura(fecha);
CREATE INDEX IF NOT EXISTS idx_factura_cliente ON factura(cliente_id);
CREATE INDEX IF NOT EXISTS idx_tickets_fecha ON tickets(fecha);
CREATE INDEX IF NOT EXISTS idx_tickets_cliente ON tickets(cliente_id);
CREATE INDEX IF NOT EXISTS idx_gastos_fecha ON gastos(fecha);

-- Vista para facturas pendientes
CREATE VIEW IF NOT EXISTS facturas_pendientes AS
SELECT 
    f.id,
    f.numero,
    f.fecha,
    f.fecha_vencimiento,
    f.total,
    c.nombre as cliente,
    f.estado
FROM factura f
LEFT JOIN contacto c ON f.cliente_id = c.id
WHERE f.cobrado = 0
ORDER BY f.fecha_vencimiento;

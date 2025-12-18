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

-- Tabla de proveedores
CREATE TABLE IF NOT EXISTS proveedores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    nombre TEXT NOT NULL,
    nif TEXT,
    direccion TEXT,
    cp TEXT,
    poblacion TEXT,
    provincia TEXT,
    email TEXT,
    email_facturacion TEXT,
    telefono TEXT,
    iban TEXT,
    forma_pago TEXT DEFAULT 'transferencia',
    dias_pago INTEGER DEFAULT 30,
    activo INTEGER DEFAULT 1,
    creado_automaticamente INTEGER DEFAULT 0,
    requiere_revision INTEGER DEFAULT 0,
    fecha_alta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notas TEXT
);

-- Tabla de facturas de proveedores
CREATE TABLE IF NOT EXISTS facturas_proveedores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    proveedor_id INTEGER NOT NULL,
    numero_factura TEXT,
    fecha_emision DATE,
    fecha_vencimiento DATE,
    base_imponible REAL DEFAULT 0,
    iva_porcentaje REAL DEFAULT 21,
    iva_importe REAL DEFAULT 0,
    total REAL DEFAULT 0,
    estado TEXT DEFAULT 'pendiente',
    fecha_pago DATE,
    metodo_pago TEXT,
    referencia_pago TEXT,
    ruta_archivo TEXT,
    pdf_hash TEXT,
    email_origen TEXT,
    trimestre TEXT,
    año INTEGER,
    metodo_extraccion TEXT,
    confianza_extraccion REAL,
    revisado INTEGER DEFAULT 0,
    fecha_alta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    usuario_alta TEXT,
    concepto TEXT,
    notas TEXT,
    FOREIGN KEY (proveedor_id) REFERENCES proveedores(id)
);

-- Tabla de líneas de factura de proveedor
CREATE TABLE IF NOT EXISTS lineas_factura_proveedor (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    factura_id INTEGER NOT NULL,
    descripcion TEXT,
    cantidad REAL DEFAULT 1,
    precio_unitario REAL DEFAULT 0,
    subtotal REAL DEFAULT 0,
    iva_porcentaje REAL DEFAULT 21,
    iva_importe REAL DEFAULT 0,
    total REAL DEFAULT 0,
    FOREIGN KEY (factura_id) REFERENCES facturas_proveedores(id) ON DELETE CASCADE
);

-- Tabla de historial de facturas de proveedor
CREATE TABLE IF NOT EXISTS historial_facturas_proveedores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    factura_id INTEGER NOT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accion TEXT,
    usuario TEXT,
    datos_anteriores TEXT,
    datos_nuevos TEXT,
    FOREIGN KEY (factura_id) REFERENCES facturas_proveedores(id) ON DELETE CASCADE
);

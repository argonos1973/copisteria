-- SISTEMA DE GESTION DE FACTURAS DE PROVEEDORES
-- Fecha: 2025-11-14

-- TABLA: proveedores
CREATE TABLE IF NOT EXISTS proveedores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    nombre TEXT NOT NULL,
    nif TEXT NOT NULL,
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
    fecha_alta DATETIME DEFAULT CURRENT_TIMESTAMP,
    notas TEXT,
    UNIQUE(empresa_id, nif),
    FOREIGN KEY (empresa_id) REFERENCES empresas(id)
);

-- TABLA: facturas_proveedores
CREATE TABLE IF NOT EXISTS facturas_proveedores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    proveedor_id INTEGER NOT NULL,
    numero_factura TEXT NOT NULL,
    fecha_emision DATE NOT NULL,
    fecha_vencimiento DATE,
    base_imponible REAL NOT NULL,
    iva_porcentaje REAL DEFAULT 21,
    iva_importe REAL,
    total REAL NOT NULL,
    estado TEXT DEFAULT 'pendiente',
    fecha_pago DATE,
    metodo_pago TEXT,
    referencia_pago TEXT,
    ruta_archivo TEXT,
    pdf_hash TEXT UNIQUE,
    email_origen TEXT,
    trimestre TEXT,
    año INTEGER,
    metodo_extraccion TEXT,
    confianza_extraccion REAL,
    revisado INTEGER DEFAULT 0,
    fecha_alta DATETIME DEFAULT CURRENT_TIMESTAMP,
    usuario_alta TEXT,
    concepto TEXT,
    notas TEXT,
    UNIQUE(empresa_id, proveedor_id, numero_factura),
    FOREIGN KEY (empresa_id) REFERENCES empresas(id),
    FOREIGN KEY (proveedor_id) REFERENCES proveedores(id)
);

-- TABLA: lineas_factura_proveedor
CREATE TABLE IF NOT EXISTS lineas_factura_proveedor (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    factura_id INTEGER NOT NULL,
    concepto TEXT NOT NULL,
    cantidad REAL DEFAULT 1,
    precio_unitario REAL NOT NULL,
    iva_porcentaje REAL DEFAULT 21,
    total_linea REAL NOT NULL,
    FOREIGN KEY (factura_id) REFERENCES facturas_proveedores(id) ON DELETE CASCADE
);

-- TABLA: historial_facturas_proveedores
CREATE TABLE IF NOT EXISTS historial_facturas_proveedores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    factura_id INTEGER NOT NULL,
    usuario TEXT NOT NULL,
    accion TEXT NOT NULL,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    datos_anteriores TEXT,
    datos_nuevos TEXT,
    FOREIGN KEY (factura_id) REFERENCES facturas_proveedores(id)
);

-- Indices para mejorar rendimiento
CREATE INDEX IF NOT EXISTS idx_proveedores_empresa ON proveedores(empresa_id);
CREATE INDEX IF NOT EXISTS idx_proveedores_nif ON proveedores(nif);
CREATE INDEX IF NOT EXISTS idx_facturas_empresa ON facturas_proveedores(empresa_id);
CREATE INDEX IF NOT EXISTS idx_facturas_proveedor ON facturas_proveedores(proveedor_id);
CREATE INDEX IF NOT EXISTS idx_facturas_estado ON facturas_proveedores(estado);
CREATE INDEX IF NOT EXISTS idx_facturas_fecha ON facturas_proveedores(fecha_emision);
CREATE INDEX IF NOT EXISTS idx_facturas_trimestre ON facturas_proveedores(trimestre, año);
CREATE INDEX IF NOT EXISTS idx_facturas_hash ON facturas_proveedores(pdf_hash);

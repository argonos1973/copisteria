-- Migración Presupuestos: crear tablas presupuesto y detalle_presupuesto si no existen
-- Nota: ejecutar esta migración manualmente en la BD /var/www/html/db/aleph70.db

BEGIN;

-- Tabla presupuesto (similar a proforma/factura, sin claves foráneas estrictas por retrocompatibilidad)
CREATE TABLE IF NOT EXISTS presupuesto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL,
    fecha TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'A',
    idContacto INTEGER,
    nif TEXT DEFAULT '',
    total REAL NOT NULL DEFAULT 0,
    formaPago TEXT DEFAULT 'E',
    importe_bruto REAL NOT NULL DEFAULT 0,
    importe_impuestos REAL NOT NULL DEFAULT 0,
    importe_cobrado REAL NOT NULL DEFAULT 0,
    timestamp TEXT,
    tipo TEXT DEFAULT 'N'
);

-- Índices útiles
CREATE INDEX IF NOT EXISTS PRESUPUESTO_NUMERO ON presupuesto (numero);
CREATE INDEX IF NOT EXISTS PRESUPUESTO_CONTACTO ON presupuesto (idContacto);
CREATE INDEX IF NOT EXISTS PRESUPUESTO_ESTADO_FECHA ON presupuesto (estado, fecha);

-- Detalle de presupuesto
CREATE TABLE IF NOT EXISTS detalle_presupuesto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_presupuesto INTEGER NOT NULL,
    concepto TEXT NOT NULL,
    descripcion TEXT DEFAULT '',
    cantidad INTEGER NOT NULL DEFAULT 1,
    precio REAL NOT NULL DEFAULT 0,
    impuestos REAL NOT NULL DEFAULT 21,
    total REAL NOT NULL DEFAULT 0,
    formaPago TEXT DEFAULT 'E',
    productoId INTEGER,
    fechaDetalle TEXT
);

CREATE INDEX IF NOT EXISTS DET_PRESUPUESTO_FK ON detalle_presupuesto (id_presupuesto);

-- Asegurar numerador para tipo 'O' (presupuesto) del ejercicio actual
INSERT INTO numerador (tipo, ejercicio, numerador)
SELECT 'O', CAST(strftime('%Y','now') AS INTEGER), 1
WHERE NOT EXISTS (
    SELECT 1 FROM numerador WHERE tipo = 'O' AND ejercicio = CAST(strftime('%Y','now') AS INTEGER)
);

COMMIT;

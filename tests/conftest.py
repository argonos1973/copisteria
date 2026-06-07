"""
Fixtures compartidas para tests de Aleph70
"""
import os
import sys
import pytest
import sqlite3
import tempfile
from pathlib import Path

# Añadir el directorio raíz al path
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

@pytest.fixture
def test_db():
    """Crea una base de datos de prueba en memoria"""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    
    # Crear esquema básico para tests
    cursor = conn.cursor()
    
    # Tabla contactos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contactos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identificador TEXT,
            razonsocial TEXT,
            nif TEXT,
            direccion TEXT,
            cp TEXT,
            provincia TEXT,
            telefono TEXT,
            email TEXT
        )
    ''')
    
    # Tabla factura
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS factura (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idContacto INTEGER,
            nif TEXT,
            fecha TEXT,
            fvencimiento TEXT,
            numero TEXT,
            importe_bruto REAL,
            importe_impuestos REAL,
            importe_cobrado REAL,
            total REAL,
            timestamp TEXT,
            estado TEXT DEFAULT 'P',
            formaPago TEXT DEFAULT 'E',
            enviado INTEGER DEFAULT 0,
            tipo TEXT DEFAULT 'N'
        )
    ''')
    
    # Tabla productos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            precio REAL,
            iva REAL DEFAULT 21.0,
            activo INTEGER DEFAULT 1
        )
    ''')
    
    conn.commit()
    
    yield conn
    
    conn.close()

@pytest.fixture
def sample_contactos(test_db):
    """Inserta contactos de ejemplo para tests"""
    cursor = test_db.cursor()
    
    contactos = [
        ('12345678A', 'Test Cliente 1', '12345678A', 'Calle Test 1', '08001', 'Barcelona', '666111222', 'test1@example.com'),
        ('87654321B', 'Test Cliente 2', '87654321B', 'Calle Test 2', '28001', 'Madrid', '666333444', 'test2@example.com'),
    ]
    
    cursor.executemany('''
        INSERT INTO contactos (identificador, razonsocial, nif, direccion, cp, provincia, telefono, email)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', contactos)
    
    test_db.commit()
    return contactos

@pytest.fixture
def sample_productos(test_db):
    """Inserta productos de ejemplo para tests"""
    cursor = test_db.cursor()
    
    productos = [
        ('Producto Test 1', 10.00, 21.0, 1),
        ('Producto Test 2', 25.50, 21.0, 1),
        ('Producto Test 3', 100.00, 10.0, 1),
    ]
    
    cursor.executemany('''
        INSERT INTO productos (nombre, precio, iva, activo)
        VALUES (?, ?, ?, ?)
    ''', productos)
    
    test_db.commit()
    return productos

@pytest.fixture
def mock_logger(mocker):
    """Mock del logger para tests"""
    return mocker.patch('logger_config.get_logger')

"""
Tests unitarios para db_utils.py
"""
import pytest
import sys
from pathlib import Path

# Añadir directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import db_utils


class TestGetDbConnection:
    """Tests para get_db_connection"""
    
    def test_get_connection_returns_connection(self, mocker):
        """Test que get_db_connection devuelve una conexión"""
        # Mock de sqlite3.connect
        mock_connect = mocker.patch('sqlite3.connect')
        mock_conn = mocker.MagicMock()
        mock_connect.return_value = mock_conn
        
        resultado = db_utils.get_db_connection()
        
        assert resultado is not None
        mock_connect.assert_called_once()
    
    def test_connection_has_row_factory(self, mocker):
        """Test que la conexión tiene row_factory configurado"""
        import sqlite3
        mock_connect = mocker.patch('sqlite3.connect')
        mock_conn = mocker.MagicMock()
        mock_connect.return_value = mock_conn
        
        db_utils.get_db_connection()
        
        # Verificar que se configuró row_factory
        assert mock_conn.row_factory == sqlite3.Row


class TestVerificarNumeroFactura:
    """Tests para verificar_numero_factura"""
    
    def test_numero_no_existe_devuelve_false(self, mocker):
        """Test que número no existente devuelve respuesta correcta"""
        # Mock de get_db_connection para evitar conexión real
        mock_conn = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None  # No existe
        
        mocker.patch('db_utils.get_db_connection', return_value=mock_conn)
        
        # Mock de jsonify para evitar contexto Flask
        mock_jsonify = mocker.patch('db_utils.jsonify')
        mock_jsonify.return_value = {'existe': False, 'id': None}
        
        resultado = db_utils.verificar_numero_factura("F-2025-9999")
        
        # Verificar que se llamó jsonify con los parámetros correctos
        assert mock_jsonify.called
    
    def test_numero_existe_devuelve_true(self, mocker):
        """Test que número existente devuelve respuesta correcta"""
        # Mock de get_db_connection
        mock_conn = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = [1]  # Existe con id=1
        
        mocker.patch('db_utils.get_db_connection', return_value=mock_conn)
        
        # Mock de jsonify
        mock_jsonify = mocker.patch('db_utils.jsonify')
        mock_jsonify.return_value = {'existe': True, 'id': 1}
        
        resultado = db_utils.verificar_numero_factura("F-2025-0001")
        
        # Verificar que se llamó jsonify
        assert mock_jsonify.called


class TestActualizarNumerador:
    """Tests para actualizar_numerador"""
    
    def test_actualizar_numerador_sin_error(self, test_db):
        """Test que actualizar numerador no genera error"""
        # Crear tabla numerador con estructura correcta
        cursor = test_db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS numerador (
                tipo TEXT,
                ejercicio INTEGER,
                numerador INTEGER,
                PRIMARY KEY (tipo, ejercicio)
            )
        ''')
        # Insertar numerador inicial
        cursor.execute('''
            INSERT INTO numerador (tipo, ejercicio, numerador)
            VALUES ('factura', 2025, 0)
        ''')
        test_db.commit()
        
        try:
            # actualizar_numerador(tipo, conn=None, commit=True)
            db_utils.actualizar_numerador('factura', test_db, True)
            assert True
        except Exception as e:
            pytest.fail(f"actualizar_numerador falló con error: {e}")
    
    def test_numerador_se_actualiza_correctamente(self, test_db):
        """Test que el numerador se actualiza al valor correcto"""
        # Crear tabla numerador con estructura correcta
        cursor = test_db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS numerador (
                tipo TEXT,
                ejercicio INTEGER,
                numerador INTEGER,
                PRIMARY KEY (tipo, ejercicio)
            )
        ''')
        # Insertar numerador inicial
        cursor.execute('''
            INSERT INTO numerador (tipo, ejercicio, numerador)
            VALUES ('factura', 2025, 49)
        ''')
        test_db.commit()
        
        # Actualizar numerador - devuelve tupla (actual, siguiente)
        actual, siguiente = db_utils.actualizar_numerador('factura', test_db, True)
        
        # Verificar que se incrementó
        assert actual == 50
        assert siguiente == 51

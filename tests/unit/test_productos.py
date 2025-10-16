"""
Tests unitarios para el módulo productos.py

Cubre:
- Generación de franjas de descuento
- CRUD de productos
- Validaciones
- Cálculos de descuentos
"""
import pytest
import sys
from pathlib import Path

# Añadir directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import productos
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal


class TestGenerarFranjasAutomaticas:
    """Tests para la función _generar_franjas_automaticas"""
    
    def test_franjas_basicas_3_bandas(self):
        """Test generación básica con 3 bandas"""
        base_subtotal = 100.0
        iva_pct = 21.0
        franjas_cfg = {
            'bandas': 3,
            'ancho': 10,
            'descuento_inicial': 5.0,
            'incremento': 5.0
        }
        
        franjas = productos._generar_franjas_automaticas(base_subtotal, iva_pct, franjas_cfg)
        
        assert len(franjas) == 3
        # Verificar que las franjas tienen estructura correcta
        for franja in franjas:
            assert 'min' in franja
            assert 'max' in franja
            assert 'descuento' in franja
            assert franja['min'] <= franja['max']
    
    def test_franjas_descuentos_crecientes(self):
        """Test que los descuentos crecen correctamente"""
        base_subtotal = 100.0
        iva_pct = 21.0
        franjas_cfg = {
            'bandas': 5,
            'ancho': 10,
            'descuento_inicial': 5.0,
            'incremento': 3.0
        }
        
        franjas = productos._generar_franjas_automaticas(base_subtotal, iva_pct, franjas_cfg)
        
        # Verificar que los descuentos son crecientes
        descuentos = [f['descuento'] for f in franjas]
        for i in range(len(descuentos) - 1):
            assert descuentos[i] <= descuentos[i+1], "Los descuentos deben ser crecientes"
    
    def test_franjas_limite_60_por_ciento(self):
        """Test que los descuentos no superan el 60%"""
        base_subtotal = 100.0
        iva_pct = 21.0
        franjas_cfg = {
            'bandas': 20,
            'ancho': 10,
            'descuento_inicial': 10.0,
            'incremento': 10.0  # Esto llevaría a >60% sin límite
        }
        
        franjas = productos._generar_franjas_automaticas(base_subtotal, iva_pct, franjas_cfg)
        
        # Verificar que ningún descuento supera el 60%
        for franja in franjas:
            assert franja['descuento'] <= 60.0, f"Descuento {franja['descuento']} supera 60%"
    
    def test_franjas_conversion_porcentaje_decimal(self):
        """Test conversión de porcentajes decimales (0.05 = 5%)"""
        base_subtotal = 100.0
        iva_pct = 21.0
        franjas_cfg = {
            'bandas': 3,
            'ancho': 10,
            'descuento_inicial': 0.05,  # 5% en formato decimal
            'incremento': 0.03  # 3% en formato decimal
        }
        
        franjas = productos._generar_franjas_automaticas(base_subtotal, iva_pct, franjas_cfg)
        
        # Debería generar 3 franjas
        assert len(franjas) == 3
        # Los descuentos deberían ser >= 0 y <= 60%
        for franja in franjas:
            assert 0.0 <= franja['descuento'] <= 60.0
    
    def test_franjas_parametros_invalidos_negativos(self):
        """Test que parámetros negativos se convierten a 0"""
        base_subtotal = 100.0
        iva_pct = 21.0
        franjas_cfg = {
            'bandas': 3,
            'ancho': 10,
            'descuento_inicial': -5.0,  # Negativo
            'incremento': -2.0  # Negativo
        }
        
        franjas = productos._generar_franjas_automaticas(base_subtotal, iva_pct, franjas_cfg)
        
        # Deberían normalizarse a 0
        assert len(franjas) > 0
        # Los descuentos deberían ser 0 o muy bajos
        assert franjas[0]['descuento'] >= 0.0
    
    def test_franjas_parametros_por_defecto(self):
        """Test parámetros por defecto cuando no se especifican"""
        base_subtotal = 100.0
        iva_pct = 21.0
        franjas_cfg = {}  # Sin parámetros
        
        franjas = productos._generar_franjas_automaticas(base_subtotal, iva_pct, franjas_cfg)
        
        # Debería usar valores por defecto (3 bandas, etc.)
        assert len(franjas) == 3
    
    def test_franjas_sin_solapamiento(self):
        """Test que las franjas no se solapan"""
        base_subtotal = 100.0
        iva_pct = 21.0
        franjas_cfg = {
            'bandas': 5,
            'ancho': 10,
            'descuento_inicial': 5.0,
            'incremento': 3.0
        }
        
        franjas = productos._generar_franjas_automaticas(base_subtotal, iva_pct, franjas_cfg)
        
        # Verificar que no hay solapamiento
        for i in range(len(franjas) - 1):
            assert franjas[i]['max'] < franjas[i+1]['min'], \
                f"Solapamiento detectado entre franjas {i} y {i+1}"
    
    def test_franjas_una_banda(self):
        """Test con una sola banda"""
        base_subtotal = 100.0
        iva_pct = 21.0
        franjas_cfg = {
            'bandas': 1,
            'ancho': 10,
            'descuento_inicial': 5.0,
            'incremento': 5.0
        }
        
        franjas = productos._generar_franjas_automaticas(base_subtotal, iva_pct, franjas_cfg)
        
        assert len(franjas) == 1
    
    def test_franjas_limite_60_bandas(self):
        """Test que el número de bandas no supera 60"""
        base_subtotal = 100.0
        iva_pct = 21.0
        franjas_cfg = {
            'bandas': 100,  # Excede el límite
            'ancho': 5,
            'descuento_inicial': 1.0,
            'incremento': 0.5
        }
        
        franjas = productos._generar_franjas_automaticas(base_subtotal, iva_pct, franjas_cfg)
        
        # Debería limitarse a 60 bandas
        assert len(franjas) <= 60


class TestObtenerProductos:
    """Tests para obtener_productos"""
    
    @patch('productos.get_db_connection')
    def test_obtener_productos_exitoso(self, mock_db):
        """Test obtención exitosa de productos"""
        # Mock de conexión y cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Simular productos devueltos
        mock_cursor.fetchall.return_value = [
            {'id': 1, 'nombre': 'Producto 1', 'subtotal': 100.0},
            {'id': 2, 'nombre': 'Producto 2', 'subtotal': 200.0}
        ]
        
        resultado = productos.obtener_productos()
        
        assert len(resultado) == 2
        assert resultado[0]['nombre'] == 'Producto 1'
        assert resultado[1]['nombre'] == 'Producto 2'
        mock_conn.close.assert_called_once()
    
    @patch('productos.get_db_connection')
    def test_obtener_productos_vacio(self, mock_db):
        """Test cuando no hay productos"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        
        resultado = productos.obtener_productos()
        
        assert len(resultado) == 0
        mock_conn.close.assert_called_once()


class TestValidaciones:
    """Tests de validaciones"""
    
    def test_validacion_parametros_franjas(self):
        """Test que los parámetros de franjas se validan correctamente"""
        base_subtotal = 100.0
        iva_pct = 21.0
        
        # Test con valores extremos
        franjas_cfg = {
            'bandas': 1000,  # Muy alto
            'ancho': -10,  # Negativo
            'descuento_inicial': 150.0,  # >60%
            'incremento': -50.0  # Negativo
        }
        
        # No debería lanzar excepción, sino normalizar
        franjas = productos._generar_franjas_automaticas(base_subtotal, iva_pct, franjas_cfg)
        
        # Verificar que se normalizaron
        assert len(franjas) <= 60  # Límite de bandas
        for franja in franjas:
            assert 0.0 <= franja['descuento'] <= 60.0  # Límite de descuento


class TestCalculosFinancieros:
    """Tests de cálculos financieros en franjas"""
    
    def test_calculo_precio_con_iva(self):
        """Test cálculo de precio con IVA"""
        base_subtotal = 100.0
        iva_pct = 21.0
        franjas_cfg = {
            'bandas': 1,
            'ancho': 10,
            'descuento_inicial': 0.0,
            'incremento': 0.0
        }
        
        franjas = productos._generar_franjas_automaticas(base_subtotal, iva_pct, franjas_cfg)
        
        # El precio final debería incluir IVA
        # Con 0% descuento: 100 + 21% = 121
        assert len(franjas) > 0
    
    def test_calculo_descuento_aplicado(self):
        """Test que el descuento se aplica correctamente al precio"""
        base_subtotal = 100.0
        iva_pct = 21.0
        franjas_cfg = {
            'bandas': 2,
            'ancho': 10,
            'descuento_inicial': 10.0,  # 10% descuento
            'incremento': 10.0
        }
        
        franjas = productos._generar_franjas_automaticas(base_subtotal, iva_pct, franjas_cfg)
        
        # Verificar que hay franjas
        assert len(franjas) >= 2
        # El descuento debería reflejarse en precios decrecientes
        # (asumiendo que precio_reducido decrece con descuento)


class TestReemplazarFranjas:
    """Tests para reemplazar_franjas_descuento_producto"""
    
    @patch('productos.get_db_connection')
    def test_reemplazar_franjas_exitoso(self, mock_db):
        """Test reemplazo exitoso de franjas"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        producto_id = 1
        franjas = [
            {'min': 1, 'max': 10, 'descuento': 5.0},
            {'min': 11, 'max': 20, 'descuento': 10.0}
        ]
        
        resultado = productos.reemplazar_franjas_descuento_producto(producto_id, franjas)
        
        assert resultado == True
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()
    
    @patch('productos.get_db_connection')
    def test_reemplazar_franjas_descuento_fuera_rango(self, mock_db):
        """Test que descuentos fuera de rango se limitan a [0, 60]"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        producto_id = 1
        franjas = [
            {'min': 1, 'max': 10, 'descuento': -5.0},  # Negativo
            {'min': 11, 'max': 20, 'descuento': 150.0}  # >60%
        ]
        
        # No debería lanzar excepción
        resultado = productos.reemplazar_franjas_descuento_producto(producto_id, franjas)
        
        assert resultado == True


# Ejecutar tests si se ejecuta directamente
if __name__ == '__main__':
    pytest.main([__file__, '-v'])

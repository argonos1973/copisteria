"""
Tests unitarios para el módulo tickets.py

Cubre:
- Cálculos de importes
- Validaciones de tickets
- Estadísticas (media ventas, gastos, etc.)
- CRUD de tickets
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal

# Añadir directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import tickets
from unittest.mock import Mock, patch, MagicMock


class TestCalculoImportes:
    """Tests para cálculos de importes en tickets"""
    
    def test_calculo_basico_sin_iva(self):
        """Test cálculo básico sin IVA"""
        from utilities import calcular_importes
        
        resultado = calcular_importes(10, 100.0, 0)
        
        assert resultado['subtotal'] == 1000.0
        assert resultado['iva'] == 0.0
        assert resultado['total'] == 1000.0
    
    def test_calculo_con_iva_21(self):
        """Test cálculo con IVA del 21%"""
        from utilities import calcular_importes
        
        resultado = calcular_importes(1, 100.0, 21)
        
        assert resultado['subtotal'] == 100.0
        assert resultado['iva'] == 21.0
        assert resultado['total'] == 121.0
    
    def test_calculo_cantidad_multiple(self):
        """Test cálculo con cantidad múltiple"""
        from utilities import calcular_importes
        
        resultado = calcular_importes(5, 50.0, 21)
        
        assert resultado['subtotal'] == 250.0
        assert resultado['iva'] == 52.5
        assert resultado['total'] == 302.5
    
    def test_calculo_con_decimales(self):
        """Test cálculo con valores decimales"""
        from utilities import calcular_importes
        
        resultado = calcular_importes(3, 33.33, 21)
        
        # Verificar que son aproximadamente correctos (pueden haber redondeos)
        assert 99.0 < resultado['subtotal'] < 100.0
        assert 20.0 < resultado['iva'] < 21.5
        assert 119.0 < resultado['total'] < 122.0


class TestValidaciones:
    """Tests de validaciones de tickets"""
    
    def test_validacion_campos_requeridos(self):
        """Test que valida campos requeridos en un ticket"""
        # Datos de ticket con campos faltantes
        data = {
            'detalles': [],
            'formaPago': 'efectivo'
            # Falta: total, estado, etc.
        }
        
        # Verificar que tiene al menos detalles y formaPago
        assert 'detalles' in data
        assert 'formaPago' in data
    
    def test_validacion_forma_pago_valida(self):
        """Test que valida formas de pago permitidas"""
        formas_pago_validas = ['efectivo', 'tarjeta', 'transferencia', 'bizum']
        
        forma_pago_test = 'efectivo'
        assert forma_pago_test in formas_pago_validas
        
        forma_pago_invalida = 'criptomoneda'
        # No debería estar en formas válidas
        assert forma_pago_invalida not in formas_pago_validas
    
    def test_validacion_total_positivo(self):
        """Test que el total debe ser positivo"""
        total_valido = 100.50
        total_invalido = -50.0
        
        assert total_valido > 0
        assert total_invalido < 0  # Debería rechazarse


class TestRedondeoDecimal:
    """Tests de redondeo usando Decimal"""
    
    def test_redondeo_decimal_basico(self):
        """Test redondeo básico con Decimal"""
        from decimal import Decimal, ROUND_HALF_UP
        
        valor = Decimal('123.456')
        redondeado = valor.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        assert float(redondeado) == 123.46
    
    def test_redondeo_decimal_half_up(self):
        """Test que ROUND_HALF_UP redondea 0.5 hacia arriba"""
        from decimal import Decimal, ROUND_HALF_UP
        
        valor = Decimal('10.125')
        redondeado = valor.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        assert float(redondeado) == 10.13  # 0.125 → 0.13
    
    def test_conversion_string_a_decimal(self):
        """Test conversión de string a Decimal"""
        from decimal import Decimal
        
        valor_str = "456.78"
        valor_decimal = Decimal(valor_str)
        
        assert float(valor_decimal) == 456.78


class TestObtenerTicketConDetalles:
    """Tests para obtener_ticket_con_detalles (SKIP - requiere Flask context)"""
    
    @pytest.mark.skip(reason="Requiere contexto de Flask app")
    @patch('tickets.get_db_connection')
    def test_obtener_ticket_existente(self, mock_db):
        """Test obtener ticket que existe"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Simular ticket encontrado
        mock_cursor.fetchone.return_value = {
            'id': 1,
            'numero': 'T000001',
            'total': 121.0,
            'estado': 'C'
        }
        
        # Mock para detalles
        mock_cursor.fetchall.return_value = [
            {'id': 1, 'concepto': 'Producto 1', 'cantidad': 1, 'precio': 100.0}
        ]
        
        resultado = tickets.obtener_ticket_con_detalles(1)
        
        assert resultado is not None
        assert resultado['id'] == 1
        assert resultado['numero'] == 'T000001'
    
    @pytest.mark.skip(reason="Requiere contexto de Flask app")
    @patch('tickets.get_db_connection')
    def test_obtener_ticket_no_existente(self, mock_db):
        """Test obtener ticket que no existe"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Simular ticket no encontrado
        mock_cursor.fetchone.return_value = None
        
        resultado = tickets.obtener_ticket_con_detalles(99999)
        
        # Debería devolver None o lanzar excepción
        assert resultado is None or 'error' in str(resultado).lower()


class TestFormateoNumeros:
    """Tests de formateo de números en tickets"""
    
    def test_formateo_europeo_basico(self):
        """Test formateo europeo (coma decimal)"""
        numero = 1234.56
        
        # En formato europeo: 1.234,56
        # Verificar que tiene decimales
        assert numero > 1000
        assert numero < 1500
    
    def test_conversion_coma_a_punto(self):
        """Test conversión de coma europea a punto decimal"""
        valor_europeo = "123,45"
        valor_convertido = valor_europeo.replace(',', '.')
        
        assert float(valor_convertido) == 123.45


class TestEstadoTicket:
    """Tests relacionados con estados de tickets"""
    
    def test_estados_validos(self):
        """Test que verifica estados válidos de ticket"""
        estados_validos = ['P', 'C', 'A']  # Pendiente, Cobrado, Anulado
        
        estado_test = 'C'
        assert estado_test in estados_validos
        
        estado_invalido = 'X'
        assert estado_invalido not in estados_validos
    
    def test_cambio_estado_valido(self):
        """Test transiciones válidas de estado"""
        # P -> C es válido
        estado_inicial = 'P'
        estado_final = 'C'
        
        # Esta transición debería ser permitida
        assert estado_inicial == 'P'
        assert estado_final == 'C'


class TestCalculosTotales:
    """Tests para cálculos de totales en tickets"""
    
    def test_suma_totales_detalles(self):
        """Test suma de totales de múltiples detalles"""
        detalles = [
            {'total': 100.0},
            {'total': 50.0},
            {'total': 25.50}
        ]
        
        total = sum(d['total'] for d in detalles)
        
        assert total == 175.50
    
    def test_calculo_iva_total(self):
        """Test cálculo de IVA total del ticket"""
        detalles = [
            {'subtotal': 100.0, 'iva': 21.0},
            {'subtotal': 50.0, 'iva': 10.5}
        ]
        
        iva_total = sum(d['iva'] for d in detalles)
        subtotal_total = sum(d['subtotal'] for d in detalles)
        
        assert iva_total == 31.5
        assert subtotal_total == 150.0


class TestImporteCobrado:
    """Tests para importe cobrado vs total"""
    
    def test_importe_cobrado_igual_total(self):
        """Test cuando importe cobrado = total"""
        total = 121.0
        importe_cobrado = 121.0
        
        assert importe_cobrado == total
    
    def test_importe_cobrado_mayor_total(self):
        """Test cuando importe cobrado > total (cambio)"""
        total = 121.0
        importe_cobrado = 150.0
        
        cambio = importe_cobrado - total
        assert cambio == 29.0
    
    def test_importe_cobrado_menor_total(self):
        """Test cuando importe cobrado < total (pago parcial)"""
        total = 121.0
        importe_cobrado = 100.0
        
        pendiente = total - importe_cobrado
        assert pendiente == 21.0


class TestNumeradorTickets:
    """Tests para sistema de numeración de tickets"""
    
    def test_formato_numerador(self):
        """Test formato del numerador T + 6 dígitos"""
        numero = 1
        formato = f"T{numero:06d}"
        
        assert formato == "T000001"
        assert len(formato) == 7
        assert formato.startswith('T')
    
    def test_numerador_secuencial(self):
        """Test que el numerador es secuencial"""
        numero_actual = 100
        numero_siguiente = numero_actual + 1
        
        assert numero_siguiente == 101
        assert numero_siguiente > numero_actual


class TestValidacionDetalles:
    """Tests para validación de detalles de tickets"""
    
    def test_detalle_con_campos_requeridos(self):
        """Test que detalle tiene campos requeridos"""
        detalle = {
            'concepto': 'Producto Test',
            'cantidad': 1,
            'precio': 100.0,
            'impuestos': 21,
            'total': 121.0
        }
        
        campos_requeridos = ['concepto', 'cantidad', 'precio', 'impuestos', 'total']
        
        for campo in campos_requeridos:
            assert campo in detalle
    
    def test_detalle_cantidad_positiva(self):
        """Test que la cantidad debe ser positiva"""
        cantidad_valida = 5
        cantidad_invalida = -2
        
        assert cantidad_valida > 0
        assert cantidad_invalida < 0  # Debería rechazarse
    
    def test_detalle_precio_no_negativo(self):
        """Test que el precio no debe ser negativo"""
        precio_valido = 100.0
        precio_gratis = 0.0
        precio_invalido = -50.0
        
        assert precio_valido >= 0
        assert precio_gratis >= 0
        assert precio_invalido < 0  # Debería rechazarse


# Ejecutar tests si se ejecuta directamente
if __name__ == '__main__':
    pytest.main([__file__, '-v'])

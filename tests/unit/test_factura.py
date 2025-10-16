"""
Tests unitarios para factura.py
"""
import pytest
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime

# Añadir directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import factura


class TestRedondearImporte:
    """Tests para la función redondear_importe"""
    
    def test_redondear_entero(self):
        """Test redondeo de número entero"""
        resultado = factura.redondear_importe(100)
        assert resultado == 100.0
        assert isinstance(resultado, float)
    
    def test_redondear_decimal_simple(self):
        """Test redondeo de decimal con 2 decimales"""
        resultado = factura.redondear_importe(99.99)
        assert resultado == 99.99
    
    def test_redondear_decimal_muchos(self):
        """Test redondeo de decimal con muchos decimales"""
        resultado = factura.redondear_importe(123.456789)
        assert resultado == 123.46
    
    def test_redondear_decimal_round_half_up(self):
        """Test redondeo usa ROUND_HALF_UP"""
        # 12.345 debe redondear a 12.35 (no 12.34)
        resultado = factura.redondear_importe(12.345)
        assert resultado == 12.35
    
    def test_redondear_decimal_type(self):
        """Test con tipo Decimal"""
        resultado = factura.redondear_importe(Decimal("99.999"))
        assert resultado == 100.0
    
    def test_redondear_string_valido(self):
        """Test con string numérico válido (formato europeo: coma para decimales)"""
        # La función usa formato europeo: coma para decimales, punto para miles
        resultado = factura.redondear_importe("123,45")
        assert resultado == 123.45
    
    def test_redondear_none(self):
        """Test con None devuelve 0.0"""
        resultado = factura.redondear_importe(None)
        assert resultado == 0.0
    
    def test_redondear_string_vacio(self):
        """Test con string vacío devuelve 0.0"""
        resultado = factura.redondear_importe("")
        assert resultado == 0.0
    
    def test_redondear_string_invalido(self):
        """Test con string no numérico devuelve 0.0"""
        resultado = factura.redondear_importe("no es un número")
        assert resultado == 0.0
    
    def test_redondear_negativo(self):
        """Test redondeo de números negativos"""
        resultado = factura.redondear_importe(-123.456)
        assert resultado == -123.46


class TestCalculoIVA:
    """Tests para cálculos de IVA"""
    
    def test_calcular_iva_21_por_ciento(self):
        """Test cálculo de IVA al 21%"""
        base = 100.0
        iva = 21.0
        resultado = factura.redondear_importe(base * iva / 100)
        assert resultado == 21.0
    
    def test_calcular_iva_10_por_ciento(self):
        """Test cálculo de IVA al 10%"""
        base = 100.0
        iva = 10.0
        resultado = factura.redondear_importe(base * iva / 100)
        assert resultado == 10.0
    
    def test_calcular_total_con_iva(self):
        """Test cálculo de total (base + IVA)"""
        base = 100.0
        iva_porcentaje = 21.0
        iva_importe = factura.redondear_importe(base * iva_porcentaje / 100)
        total = factura.redondear_importe(base + iva_importe)
        assert total == 121.0
    
    def test_calcular_iva_con_decimales(self):
        """Test cálculo de IVA con base decimal"""
        base = 123.45
        iva = 21.0
        resultado = factura.redondear_importe(base * iva / 100)
        assert resultado == 25.92  # 123.45 * 0.21 = 25.9245 → 25.92


class TestValidacionDatos:
    """Tests para validación de datos de factura"""
    
    def test_validar_nif_formato_correcto(self):
        """Test validación de NIF con formato correcto"""
        nif = "12345678A"
        assert len(nif) == 9
        assert nif[-1].isalpha()
        assert nif[:-1].isdigit()
    
    def test_validar_email_basico(self):
        """Test validación básica de email"""
        email = "test@example.com"
        assert "@" in email
        assert "." in email.split("@")[1]
    
    def test_validar_fecha_formato_dd_mm_yyyy(self):
        """Test validación de fecha formato DD/MM/YYYY"""
        fecha = "15/10/2025"
        partes = fecha.split("/")
        assert len(partes) == 3
        dia, mes, anio = int(partes[0]), int(partes[1]), int(partes[2])
        assert 1 <= dia <= 31
        assert 1 <= mes <= 12
        assert anio >= 2000


class TestCalculoDescuentos:
    """Tests para cálculos de descuentos"""
    
    def test_aplicar_descuento_porcentaje(self):
        """Test aplicar descuento porcentual"""
        precio_original = 100.0
        descuento_porcentaje = 10.0
        descuento = factura.redondear_importe(precio_original * descuento_porcentaje / 100)
        precio_final = factura.redondear_importe(precio_original - descuento)
        
        assert descuento == 10.0
        assert precio_final == 90.0
    
    def test_aplicar_descuento_50_por_ciento(self):
        """Test aplicar 50% de descuento"""
        precio_original = 200.0
        descuento_porcentaje = 50.0
        precio_final = factura.redondear_importe(precio_original * (1 - descuento_porcentaje / 100))
        
        assert precio_final == 100.0
    
    def test_precio_con_descuento_y_iva(self):
        """Test precio con descuento y luego IVA"""
        precio_original = 100.0
        descuento_porcentaje = 10.0
        iva_porcentaje = 21.0
        
        # Aplicar descuento
        precio_con_descuento = factura.redondear_importe(
            precio_original * (1 - descuento_porcentaje / 100)
        )
        
        # Aplicar IVA sobre precio con descuento
        iva = factura.redondear_importe(precio_con_descuento * iva_porcentaje / 100)
        total = factura.redondear_importe(precio_con_descuento + iva)
        
        assert precio_con_descuento == 90.0
        assert iva == 18.9
        assert total == 108.9


class TestCalculoLineasFactura:
    """Tests para cálculos de líneas de factura"""
    
    def test_calcular_linea_simple(self):
        """Test cálculo de línea de factura simple"""
        cantidad = 2
        precio_unitario = 50.0
        iva_porcentaje = 21.0
        
        subtotal = factura.redondear_importe(cantidad * precio_unitario)
        iva = factura.redondear_importe(subtotal * iva_porcentaje / 100)
        total = factura.redondear_importe(subtotal + iva)
        
        assert subtotal == 100.0
        assert iva == 21.0
        assert total == 121.0
    
    def test_calcular_linea_con_descuento(self):
        """Test cálculo de línea con descuento"""
        cantidad = 3
        precio_unitario = 100.0
        descuento_porcentaje = 10.0
        iva_porcentaje = 21.0
        
        subtotal_bruto = factura.redondear_importe(cantidad * precio_unitario)
        descuento = factura.redondear_importe(subtotal_bruto * descuento_porcentaje / 100)
        subtotal_neto = factura.redondear_importe(subtotal_bruto - descuento)
        iva = factura.redondear_importe(subtotal_neto * iva_porcentaje / 100)
        total = factura.redondear_importe(subtotal_neto + iva)
        
        assert subtotal_bruto == 300.0
        assert descuento == 30.0
        assert subtotal_neto == 270.0
        assert iva == 56.7
        assert total == 326.7


class TestCalculoTotalesFactura:
    """Tests para cálculos de totales de factura completa"""
    
    def test_calcular_total_factura_una_linea(self):
        """Test cálculo total con una línea"""
        lineas = [
            {'cantidad': 2, 'precio': 50.0, 'iva': 21.0, 'descuento': 0.0}
        ]
        
        total_base = 0.0
        total_iva = 0.0
        
        for linea in lineas:
            base = factura.redondear_importe(linea['cantidad'] * linea['precio'])
            if linea['descuento'] > 0:
                base = factura.redondear_importe(base * (1 - linea['descuento'] / 100))
            iva = factura.redondear_importe(base * linea['iva'] / 100)
            
            total_base += base
            total_iva += iva
        
        total_factura = factura.redondear_importe(total_base + total_iva)
        
        assert total_base == 100.0
        assert total_iva == 21.0
        assert total_factura == 121.0
    
    def test_calcular_total_factura_multiples_lineas(self):
        """Test cálculo total con múltiples líneas"""
        lineas = [
            {'cantidad': 2, 'precio': 50.0, 'iva': 21.0, 'descuento': 0.0},
            {'cantidad': 1, 'precio': 100.0, 'iva': 21.0, 'descuento': 10.0},
            {'cantidad': 3, 'precio': 20.0, 'iva': 10.0, 'descuento': 0.0}
        ]
        
        total_base = 0.0
        total_iva = 0.0
        
        for linea in lineas:
            base = factura.redondear_importe(linea['cantidad'] * linea['precio'])
            if linea['descuento'] > 0:
                base = factura.redondear_importe(base * (1 - linea['descuento'] / 100))
            iva = factura.redondear_importe(base * linea['iva'] / 100)
            
            total_base += base
            total_iva += iva
        
        total_base = factura.redondear_importe(total_base)
        total_iva = factura.redondear_importe(total_iva)
        total_factura = factura.redondear_importe(total_base + total_iva)
        
        # Línea 1: 2 * 50 = 100, IVA 21% = 21
        # Línea 2: 1 * 100 - 10% = 90, IVA 21% = 18.9
        # Línea 3: 3 * 20 = 60, IVA 10% = 6
        # Total base: 100 + 90 + 60 = 250
        # Total IVA: 21 + 18.9 + 6 = 45.9
        # Total: 295.9
        
        assert total_base == 250.0
        assert total_iva == 45.9
        assert total_factura == 295.9
    
    def test_calcular_total_con_diferentes_ivas(self):
        """Test cálculo con diferentes tipos de IVA"""
        lineas = [
            {'cantidad': 1, 'precio': 100.0, 'iva': 21.0, 'descuento': 0.0},  # IVA general
            {'cantidad': 1, 'precio': 100.0, 'iva': 10.0, 'descuento': 0.0},  # IVA reducido
            {'cantidad': 1, 'precio': 100.0, 'iva': 4.0, 'descuento': 0.0}    # IVA superreducido
        ]
        
        total_base = 0.0
        total_iva = 0.0
        
        for linea in lineas:
            base = factura.redondear_importe(linea['cantidad'] * linea['precio'])
            iva = factura.redondear_importe(base * linea['iva'] / 100)
            
            total_base += base
            total_iva += iva
        
        total_base = factura.redondear_importe(total_base)
        total_iva = factura.redondear_importe(total_iva)
        total_factura = factura.redondear_importe(total_base + total_iva)
        
        assert total_base == 300.0
        assert total_iva == 35.0  # 21 + 10 + 4
        assert total_factura == 335.0


class TestFormatosNumero:
    """Tests para formatos de números en facturas"""
    
    def test_numero_factura_formato_correcto(self):
        """Test formato de número de factura"""
        numero = "F-2025-0001"
        partes = numero.split("-")
        
        assert len(partes) == 3
        assert partes[0] == "F"
        assert partes[1] == "2025"
        assert len(partes[2]) == 4
        assert partes[2].isdigit()
    
    def test_incrementar_numero_factura(self):
        """Test incremento de número de factura"""
        numero_actual = "F-2025-0001"
        partes = numero_actual.split("-")
        num = int(partes[2]) + 1
        nuevo_numero = f"{partes[0]}-{partes[1]}-{num:04d}"
        
        assert nuevo_numero == "F-2025-0002"
    
    def test_formato_importe_con_dos_decimales(self):
        """Test que importes tienen exactamente 2 decimales"""
        importe = factura.redondear_importe(123.4)
        assert importe == 123.4
        
        # Verificar que al formatear tiene 2 decimales
        importe_str = f"{importe:.2f}"
        assert importe_str == "123.40"

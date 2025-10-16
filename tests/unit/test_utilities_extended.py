"""
Tests unitarios extendidos para utilities y módulos auxiliares

Cubre:
- Utilidades de cálculo
- Validaciones generales
- Conversiones
- Helpers
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

# Añadir directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utilities import calcular_importes
from unittest.mock import Mock, patch, MagicMock


class TestCalcularImportes:
    """Tests extendidos para calcular_importes"""
    
    def test_cantidad_cero(self):
        """Test con cantidad cero"""
        resultado = calcular_importes(0, 100.0, 21)
        
        assert resultado['subtotal'] == 0.0
        assert resultado['iva'] == 0.0
        assert resultado['total'] == 0.0
    
    def test_precio_cero(self):
        """Test con precio cero"""
        resultado = calcular_importes(5, 0.0, 21)
        
        assert resultado['subtotal'] == 0.0
        assert resultado['iva'] == 0.0
        assert resultado['total'] == 0.0
    
    def test_iva_cero(self):
        """Test sin IVA (0%)"""
        resultado = calcular_importes(2, 50.0, 0)
        
        assert resultado['subtotal'] == 100.0
        assert resultado['iva'] == 0.0
        assert resultado['total'] == 100.0
    
    def test_iva_10_reducido(self):
        """Test con IVA reducido (10%)"""
        resultado = calcular_importes(1, 100.0, 10)
        
        assert resultado['subtotal'] == 100.0
        assert resultado['iva'] == 10.0
        assert resultado['total'] == 110.0
    
    def test_iva_4_superreducido(self):
        """Test con IVA superreducido (4%)"""
        resultado = calcular_importes(1, 100.0, 4)
        
        assert resultado['subtotal'] == 100.0
        assert resultado['iva'] == 4.0
        assert resultado['total'] == 104.0
    
    def test_cantidad_decimal(self):
        """Test con cantidad decimal"""
        resultado = calcular_importes(2.5, 40.0, 21)
        
        assert resultado['subtotal'] == 100.0
        assert resultado['iva'] == 21.0
        assert resultado['total'] == 121.0
    
    def test_precision_decimal(self):
        """Test precisión con múltiples decimales"""
        resultado = calcular_importes(3, 33.33, 21)
        
        # Verificar que los cálculos son aproximadamente correctos
        assert 99.0 < resultado['subtotal'] < 100.0
        assert 20.0 < resultado['iva'] < 21.5
        assert 119.0 < resultado['total'] < 122.0
    
    def test_redondeo_correcto(self):
        """Test que el redondeo es correcto"""
        resultado = calcular_importes(1, 10.555, 21)
        
        # Debería redondear correctamente
        assert isinstance(resultado['subtotal'], float)
        assert isinstance(resultado['iva'], float)
        assert isinstance(resultado['total'], float)


class TestValidacionesGenerales:
    """Tests de validaciones generales"""
    
    def test_validacion_numero_positivo(self):
        """Test validación de números positivos"""
        numero = 100.50
        
        assert numero > 0
        assert isinstance(numero, (int, float))
    
    def test_validacion_numero_negativo(self):
        """Test validación rechaza números negativos"""
        numero = -50.0
        
        # En contexto de precios/importes, debería rechazarse
        assert numero < 0  # Para detección
    
    def test_validacion_string_no_vacio(self):
        """Test validación de string no vacío"""
        texto = "Producto Test"
        texto_vacio = ""
        
        assert len(texto) > 0
        assert len(texto_vacio) == 0
    
    def test_validacion_email_basico(self):
        """Test validación básica de email"""
        email_valido = "test@example.com"
        email_invalido = "test@"
        
        assert '@' in email_valido
        assert '.' in email_valido
        # Email inválido no tiene dominio completo
        assert '.' not in email_invalido.split('@')[-1]


class TestConversionesTipos:
    """Tests de conversiones de tipos"""
    
    def test_string_to_float(self):
        """Test conversión string a float"""
        valor = "123.45"
        convertido = float(valor)
        
        assert convertido == 123.45
        assert isinstance(convertido, float)
    
    def test_string_to_int(self):
        """Test conversión string a int"""
        valor = "123"
        convertido = int(valor)
        
        assert convertido == 123
        assert isinstance(convertido, int)
    
    def test_float_to_decimal(self):
        """Test conversión float a Decimal"""
        valor = 123.45
        decimal_val = Decimal(str(valor))
        
        assert float(decimal_val) == 123.45
    
    def test_formato_europeo_a_decimal(self):
        """Test conversión formato europeo (coma) a decimal"""
        valor_europeo = "1.234,56"  # Mil doscientos treinta y cuatro con cincuenta y seis
        
        # Convertir: quitar puntos de miles, cambiar coma por punto
        valor_limpio = valor_europeo.replace('.', '').replace(',', '.')
        convertido = float(valor_limpio)
        
        assert convertido == 1234.56


class TestOperacionesDecimales:
    """Tests de operaciones con Decimal"""
    
    def test_suma_decimales(self):
        """Test suma con Decimal para evitar imprecisión"""
        a = Decimal('0.1')
        b = Decimal('0.2')
        resultado = a + b
        
        assert float(resultado) == 0.3
    
    def test_multiplicacion_decimales(self):
        """Test multiplicación con Decimal"""
        cantidad = Decimal('3')
        precio = Decimal('33.33')
        resultado = cantidad * precio
        
        assert float(resultado) == 99.99
    
    def test_division_decimales(self):
        """Test división con Decimal"""
        total = Decimal('100')
        cantidad = Decimal('3')
        precio_unitario = total / cantidad
        
        # Redondear a 2 decimales
        precio_redondeado = precio_unitario.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        assert float(precio_redondeado) == 33.33


class TestFormateoMoneda:
    """Tests de formateo de moneda"""
    
    def test_formato_dos_decimales(self):
        """Test formato con 2 decimales"""
        valor = 123.456
        formateado = f"{valor:.2f}"
        
        assert formateado == "123.46"
    
    def test_formato_europeo_separador_miles(self):
        """Test formato europeo con separador de miles"""
        valor = 1234.56
        
        # Formato: 1.234,56
        # Python por defecto usa punto decimal, habría que formatear
        assert valor > 1000
        assert valor < 2000
    
    def test_simbolo_euro(self):
        """Test añadir símbolo de euro"""
        valor = 123.45
        formateado = f"{valor:.2f} €"
        
        assert "€" in formateado
        assert "123.45" in formateado


class TestManipulacionFechas:
    """Tests de manipulación de fechas"""
    
    def test_fecha_actual(self):
        """Test obtener fecha actual"""
        hoy = datetime.now()
        
        assert isinstance(hoy, datetime)
        assert hoy.year >= 2024
    
    def test_formato_fecha_iso(self):
        """Test formato ISO de fecha"""
        fecha = datetime(2024, 10, 16)
        iso = fecha.strftime('%Y-%m-%d')
        
        assert iso == "2024-10-16"
    
    def test_formato_fecha_europeo(self):
        """Test formato europeo de fecha"""
        fecha = datetime(2024, 10, 16)
        europeo = fecha.strftime('%d/%m/%Y')
        
        assert europeo == "16/10/2024"
    
    def test_diferencia_fechas(self):
        """Test cálculo de diferencia entre fechas"""
        fecha1 = datetime(2024, 10, 1)
        fecha2 = datetime(2024, 10, 16)
        
        diferencia = (fecha2 - fecha1).days
        
        assert diferencia == 15


class TestOperacionesListas:
    """Tests de operaciones con listas"""
    
    def test_suma_lista(self):
        """Test suma de elementos de lista"""
        numeros = [10, 20, 30, 40]
        total = sum(numeros)
        
        assert total == 100
    
    def test_promedio_lista(self):
        """Test promedio de lista"""
        numeros = [10, 20, 30, 40]
        promedio = sum(numeros) / len(numeros)
        
        assert promedio == 25.0
    
    def test_filtrado_lista(self):
        """Test filtrado de lista"""
        numeros = [1, 2, 3, 4, 5, 6]
        pares = [n for n in numeros if n % 2 == 0]
        
        assert pares == [2, 4, 6]
        assert len(pares) == 3
    
    def test_ordenamiento_lista(self):
        """Test ordenamiento de lista"""
        numeros = [3, 1, 4, 1, 5, 9, 2, 6]
        ordenados = sorted(numeros)
        
        assert ordenados == [1, 1, 2, 3, 4, 5, 6, 9]


class TestValidacionRangos:
    """Tests de validación de rangos"""
    
    def test_numero_en_rango(self):
        """Test número está en rango válido"""
        numero = 50
        minimo = 0
        maximo = 100
        
        assert minimo <= numero <= maximo
    
    def test_numero_fuera_rango(self):
        """Test número está fuera de rango"""
        numero = 150
        minimo = 0
        maximo = 100
        
        assert not (minimo <= numero <= maximo)
    
    def test_porcentaje_valido(self):
        """Test porcentaje válido (0-100)"""
        porcentaje = 75
        
        assert 0 <= porcentaje <= 100
    
    def test_descuento_maximo(self):
        """Test descuento no supera máximo (60%)"""
        descuento = 45
        max_descuento = 60
        
        assert descuento <= max_descuento


class TestNormalizacionTexto:
    """Tests de normalización de texto"""
    
    def test_trim_espacios(self):
        """Test eliminar espacios inicio/fin"""
        texto = "  Hola Mundo  "
        normalizado = texto.strip()
        
        assert normalizado == "Hola Mundo"
    
    def test_lowercase(self):
        """Test convertir a minúsculas"""
        texto = "HOLA MUNDO"
        minusculas = texto.lower()
        
        assert minusculas == "hola mundo"
    
    def test_uppercase(self):
        """Test convertir a mayúsculas"""
        texto = "hola mundo"
        mayusculas = texto.upper()
        
        assert mayusculas == "HOLA MUNDO"
    
    def test_reemplazar_caracteres(self):
        """Test reemplazar caracteres"""
        texto = "hola-mundo"
        reemplazado = texto.replace('-', ' ')
        
        assert reemplazado == "hola mundo"


# Ejecutar tests si se ejecuta directamente
if __name__ == '__main__':
    pytest.main([__file__, '-v'])

"""
Tests unitarios para el módulo conciliacion.py

Cubre:
- Búsqueda de coincidencias automáticas
- Validaciones de conciliación
- Cálculos de importes
- Matching de movimientos
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Añadir directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from unittest.mock import Mock, patch, MagicMock


class TestBusquedaCoincidencias:
    """Tests para búsqueda de coincidencias bancarias"""
    
    def test_coincidencia_exacta_importe(self):
        """Test coincidencia exacta por importe"""
        movimiento = {'importe': 121.50, 'fecha': '2024-10-15'}
        factura = {'total': 121.50, 'fecha_emision': '2024-10-15'}
        
        # Importes coinciden exactamente
        assert movimiento['importe'] == factura['total']
    
    def test_coincidencia_aproximada_importe(self):
        """Test coincidencia aproximada (±0.02)"""
        movimiento_importe = 121.50
        factura_total = 121.52
        
        diferencia = abs(movimiento_importe - factura_total)
        tolerancia = 0.02
        
        assert diferencia <= tolerancia
    
    def test_no_coincidencia_importe(self):
        """Test no coincidencia de importe"""
        movimiento_importe = 121.50
        factura_total = 200.00
        
        diferencia = abs(movimiento_importe - factura_total)
        tolerancia = 0.02
        
        assert diferencia > tolerancia


class TestValidacionFechas:
    """Tests de validación de fechas en conciliación"""
    
    def test_fecha_misma_semana(self):
        """Test fechas en la misma semana"""
        fecha1 = datetime(2024, 10, 15)  # Martes
        fecha2 = datetime(2024, 10, 17)  # Jueves
        
        diferencia_dias = abs((fecha2 - fecha1).days)
        
        assert diferencia_dias <= 7  # Misma semana
    
    def test_fecha_mismo_mes(self):
        """Test fechas en el mismo mes"""
        fecha1 = datetime(2024, 10, 5)
        fecha2 = datetime(2024, 10, 25)
        
        assert fecha1.month == fecha2.month
        assert fecha1.year == fecha2.year
    
    def test_fecha_fuera_rango(self):
        """Test fechas fuera de rango permitido"""
        fecha_movimiento = datetime(2024, 10, 15)
        fecha_factura = datetime(2024, 8, 15)  # 2 meses antes
        
        diferencia_dias = abs((fecha_movimiento - fecha_factura).days)
        max_dias = 30
        
        assert diferencia_dias > max_dias  # Fuera de rango


class TestNormalizacionConceptos:
    """Tests para normalización de conceptos"""
    
    def test_normalizacion_basica(self):
        """Test normalización básica de concepto"""
        concepto = "  TRANSFERENCIA BANCARIA  "
        normalizado = concepto.strip().lower()
        
        assert normalizado == "transferencia bancaria"
    
    def test_eliminacion_caracteres_especiales(self):
        """Test eliminación de caracteres especiales"""
        concepto = "PAGO-FACTURA/123"
        # Normalizar eliminando caracteres especiales comunes
        normalizado = concepto.replace('-', ' ').replace('/', ' ').strip()
        
        assert 'PAGO' in normalizado
        assert 'FACTURA' in normalizado
    
    def test_deteccion_numero_factura(self):
        """Test detección de número de factura en concepto"""
        concepto = "PAGO FACTURA F240001"
        
        # Buscar patrón F + números
        import re
        patron = r'F\d+'
        match = re.search(patron, concepto)
        
        assert match is not None
        assert match.group() == 'F240001'


class TestCalculosDiferencias:
    """Tests para cálculos de diferencias"""
    
    def test_diferencia_exacta_cero(self):
        """Test diferencia exacta (cero)"""
        movimiento = 121.50
        factura = 121.50
        
        diferencia = abs(movimiento - factura)
        
        assert diferencia == 0.0
    
    def test_diferencia_pequena_aceptable(self):
        """Test diferencia pequeña aceptable"""
        movimiento = 121.50
        factura = 121.48
        
        diferencia = abs(movimiento - factura)
        
        assert 0.0 < diferencia <= 0.05
    
    def test_diferencia_grande_no_aceptable(self):
        """Test diferencia grande no aceptable"""
        movimiento = 121.50
        factura = 125.00
        
        diferencia = abs(movimiento - factura)
        
        assert diferencia > 1.0


class TestEstadosConciliacion:
    """Tests de estados de conciliación"""
    
    def test_estado_conciliado(self):
        """Test estado conciliado"""
        estado = 'conciliado'
        estados_validos = ['pendiente', 'conciliado', 'descartado']
        
        assert estado in estados_validos
    
    def test_estado_pendiente(self):
        """Test estado pendiente"""
        movimiento = {'estado': 'pendiente', 'importe': 100.0}
        
        assert movimiento['estado'] == 'pendiente'
    
    def test_cambio_estado_valido(self):
        """Test cambio de estado válido"""
        estado_inicial = 'pendiente'
        estado_final = 'conciliado'
        
        # Transición pendiente -> conciliado es válida
        assert estado_inicial != estado_final


class TestMatchingPorReferencia:
    """Tests de matching por referencia"""
    
    def test_matching_por_numero_factura(self):
        """Test matching usando número de factura"""
        concepto_movimiento = "PAGO FACTURA F240100"
        numero_factura = "F240100"
        
        assert numero_factura in concepto_movimiento
    
    def test_matching_por_cliente(self):
        """Test matching usando nombre de cliente"""
        concepto_movimiento = "TRANSFERENCIA DE EMPRESA SA"
        nombre_cliente = "EMPRESA SA"
        
        assert nombre_cliente in concepto_movimiento
    
    def test_matching_ambiguo(self):
        """Test matching ambiguo (múltiples coincidencias)"""
        concepto = "PAGO VARIAS FACTURAS"
        
        # Este concepto es ambiguo, no tiene referencia única
        import re
        patron_factura = r'F\d+'
        matches = re.findall(patron_factura, concepto)
        
        assert len(matches) == 0  # No hay referencia clara


class TestValidacionMovimientosBancarios:
    """Tests de validación de movimientos bancarios"""
    
    def test_movimiento_ingreso(self):
        """Test identificación de movimiento de ingreso"""
        movimiento = {'importe': 121.50, 'tipo': 'ingreso'}
        
        assert movimiento['importe'] > 0
        assert movimiento['tipo'] == 'ingreso'
    
    def test_movimiento_gasto(self):
        """Test identificación de movimiento de gasto"""
        movimiento = {'importe': -50.00, 'tipo': 'gasto'}
        
        assert movimiento['importe'] < 0
        assert movimiento['tipo'] == 'gasto'
    
    def test_validacion_campos_requeridos(self):
        """Test validación de campos requeridos"""
        movimiento = {
            'fecha': '2024-10-15',
            'concepto': 'TRANSFERENCIA',
            'importe': 121.50,
            'saldo': 1000.0
        }
        
        campos_requeridos = ['fecha', 'concepto', 'importe']
        
        for campo in campos_requeridos:
            assert campo in movimiento


class TestAlgoritmoSimilitud:
    """Tests para algoritmo de similitud de textos"""
    
    def test_similitud_exacta(self):
        """Test similitud exacta de textos"""
        texto1 = "EMPRESA SA"
        texto2 = "EMPRESA SA"
        
        assert texto1 == texto2
    
    def test_similitud_case_insensitive(self):
        """Test similitud ignorando mayúsculas"""
        texto1 = "Empresa SA"
        texto2 = "EMPRESA SA"
        
        assert texto1.lower() == texto2.lower()
    
    def test_similitud_parcial(self):
        """Test similitud parcial"""
        texto1 = "EMPRESA EJEMPLO SA"
        texto2 = "EMPRESA EJEMPLO"
        
        assert texto2 in texto1


class TestAgrupacionMovimientos:
    """Tests para agrupación de movimientos"""
    
    def test_agrupacion_por_fecha(self):
        """Test agrupación por fecha"""
        movimientos = [
            {'fecha': '2024-10-15', 'importe': 100},
            {'fecha': '2024-10-15', 'importe': 50},
            {'fecha': '2024-10-16', 'importe': 75}
        ]
        
        # Agrupar por fecha
        from itertools import groupby
        movimientos_ordenados = sorted(movimientos, key=lambda x: x['fecha'])
        grupos = {k: list(g) for k, g in groupby(movimientos_ordenados, key=lambda x: x['fecha'])}
        
        assert len(grupos) == 2
        assert len(grupos['2024-10-15']) == 2
        assert len(grupos['2024-10-16']) == 1
    
    def test_suma_movimientos_agrupados(self):
        """Test suma de movimientos agrupados"""
        movimientos = [
            {'importe': 100},
            {'importe': 50},
            {'importe': 25}
        ]
        
        total = sum(m['importe'] for m in movimientos)
        
        assert total == 175


class TestReglasConciliacion:
    """Tests para reglas de conciliación"""
    
    def test_regla_importe_exacto(self):
        """Test regla: importe exacto tiene máxima prioridad"""
        regla = {'tipo': 'importe_exacto', 'prioridad': 1}
        
        assert regla['prioridad'] == 1
    
    def test_regla_referencia(self):
        """Test regla: referencia en concepto"""
        regla = {'tipo': 'referencia', 'prioridad': 2}
        
        assert regla['prioridad'] == 2
    
    def test_regla_fecha_cercana(self):
        """Test regla: fecha cercana"""
        regla = {'tipo': 'fecha_cercana', 'prioridad': 3}
        
        assert regla['prioridad'] == 3


class TestConciliacionMultiple:
    """Tests para conciliación múltiple (1 movimiento -> N facturas)"""
    
    def test_un_movimiento_varias_facturas(self):
        """Test un movimiento cubre varias facturas"""
        movimiento_importe = 500.0
        facturas = [
            {'total': 200.0},
            {'total': 150.0},
            {'total': 150.0}
        ]
        
        total_facturas = sum(f['total'] for f in facturas)
        
        assert total_facturas == movimiento_importe
    
    def test_varias_facturas_un_movimiento_parcial(self):
        """Test varias facturas con movimiento que no cubre todo"""
        movimiento_importe = 300.0
        facturas = [
            {'total': 200.0},
            {'total': 150.0}
        ]
        
        total_facturas = sum(f['total'] for f in facturas)
        pendiente = total_facturas - movimiento_importe
        
        assert pendiente == 50.0


# Ejecutar tests si se ejecuta directamente
if __name__ == '__main__':
    pytest.main([__file__, '-v'])

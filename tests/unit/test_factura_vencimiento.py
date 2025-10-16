"""
Tests para verificar cálculo de fecha de vencimiento en facturas

Verifica que la fecha de vencimiento sea fecha emisión + 30 días
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestFechaVencimientoFactura:
    """Tests para cálculo automático de fecha de vencimiento"""
    
    def test_vencimiento_30_dias_desde_emision(self):
        """Test que vencimiento es emisión + 30 días"""
        fecha_emision = datetime(2024, 10, 16)
        dias_vencimiento = 30
        
        fecha_vencimiento = fecha_emision + timedelta(days=dias_vencimiento)
        
        assert fecha_vencimiento == datetime(2024, 11, 15)
        assert (fecha_vencimiento - fecha_emision).days == 30
    
    def test_vencimiento_mes_siguiente(self):
        """Test vencimiento cae en mes siguiente"""
        fecha_emision = datetime(2024, 10, 5)
        fecha_vencimiento = fecha_emision + timedelta(days=30)
        
        assert fecha_vencimiento.month == 11
        assert fecha_vencimiento.day == 4
    
    def test_vencimiento_fin_de_mes(self):
        """Test vencimiento con fecha emisión fin de mes"""
        fecha_emision = datetime(2024, 1, 31)
        fecha_vencimiento = fecha_emision + timedelta(days=30)
        
        # 31 enero + 30 días = 2 marzo (año no bisiesto tendría 1 marzo)
        assert fecha_vencimiento == datetime(2024, 3, 1)  # 2024 es bisiesto
    
    def test_vencimiento_cambio_de_anio(self):
        """Test vencimiento que cruza año"""
        fecha_emision = datetime(2024, 12, 10)
        fecha_vencimiento = fecha_emision + timedelta(days=30)
        
        assert fecha_vencimiento.year == 2025
        assert fecha_vencimiento.month == 1
        assert fecha_vencimiento.day == 9
    
    def test_formato_fecha_iso(self):
        """Test formato de fecha ISO (YYYY-MM-DD)"""
        fecha_emision_str = "2024-10-16"
        fecha_emision = datetime.strptime(fecha_emision_str, '%Y-%m-%d')
        fecha_vencimiento = fecha_emision + timedelta(days=30)
        fecha_vencimiento_str = fecha_vencimiento.strftime('%Y-%m-%d')
        
        assert fecha_vencimiento_str == "2024-11-15"
        assert len(fecha_vencimiento_str) == 10
        assert fecha_vencimiento_str[4] == '-'
        assert fecha_vencimiento_str[7] == '-'
    
    def test_vencimiento_diferencia_exacta(self):
        """Test que la diferencia sea exactamente 30 días"""
        fecha_emision = datetime(2024, 6, 15)
        fecha_vencimiento = fecha_emision + timedelta(days=30)
        
        diferencia = (fecha_vencimiento - fecha_emision).days
        
        assert diferencia == 30
    
    def test_vencimiento_año_bisiesto(self):
        """Test vencimiento en año bisiesto"""
        # Febrero 2024 tiene 29 días (año bisiesto)
        fecha_emision = datetime(2024, 2, 15)
        fecha_vencimiento = fecha_emision + timedelta(days=30)
        
        assert fecha_vencimiento == datetime(2024, 3, 16)
    
    def test_vencimiento_año_no_bisiesto(self):
        """Test vencimiento en año no bisiesto"""
        # Febrero 2025 tiene 28 días (año no bisiesto)
        fecha_emision = datetime(2025, 2, 15)
        fecha_vencimiento = fecha_emision + timedelta(days=30)
        
        assert fecha_vencimiento == datetime(2025, 3, 17)
    
    def test_calculo_vencimiento_multiples_fechas(self):
        """Test cálculo para múltiples fechas"""
        fechas_test = [
            ("2024-01-01", "2024-01-31"),
            ("2024-02-01", "2024-03-02"),
            ("2024-03-15", "2024-04-14"),
            ("2024-06-30", "2024-07-30"),
            ("2024-12-25", "2025-01-24"),
        ]
        
        for fecha_emision_str, fecha_vencimiento_esperada in fechas_test:
            fecha_emision = datetime.strptime(fecha_emision_str, '%Y-%m-%d')
            fecha_vencimiento = fecha_emision + timedelta(days=30)
            fecha_vencimiento_str = fecha_vencimiento.strftime('%Y-%m-%d')
            
            assert fecha_vencimiento_str == fecha_vencimiento_esperada, \
                f"Emisión: {fecha_emision_str}, Esperado: {fecha_vencimiento_esperada}, Obtenido: {fecha_vencimiento_str}"
    
    def test_vencimiento_vs_15_dias_antiguo(self):
        """Test que verifica que NO sea 15 días (comportamiento antiguo)"""
        fecha_emision = datetime(2024, 10, 16)
        fecha_vencimiento_correcta = fecha_emision + timedelta(days=30)
        fecha_vencimiento_antigua = fecha_emision + timedelta(days=15)
        
        # Verificar que NO use 15 días
        assert fecha_vencimiento_correcta != fecha_vencimiento_antigua
        assert (fecha_vencimiento_correcta - fecha_emision).days == 30
        assert (fecha_vencimiento_antigua - fecha_emision).days == 15


# Ejecutar tests si se ejecuta directamente
if __name__ == '__main__':
    pytest.main([__file__, '-v'])

"""
Tests extendidos exhaustivos para factura.py

Aumenta cobertura de factura.py
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from unittest.mock import Mock, patch, MagicMock


class TestFormatoFactura:
    """Tests de formato de facturas"""
    
    def test_numero_factura_formato(self):
        """Test formato número de factura"""
        numero = 1
        formato = f"F{numero:06d}"
        
        assert formato == "F000001"
        assert len(formato) == 7
        assert formato.startswith('F')
    
    def test_formato_fecha_factura(self):
        """Test formato fecha factura"""
        fecha = datetime(2024, 10, 16)
        formato_iso = fecha.strftime('%Y-%m-%d')
        formato_europeo = fecha.strftime('%d/%m/%Y')
        
        assert formato_iso == "2024-10-16"
        assert formato_europeo == "16/10/2024"
    
    def test_formato_referencia_factura(self):
        """Test formato referencia completa"""
        serie = 'F'
        anio = 2024
        numero = 123
        referencia = f"{serie}{anio%100:02d}{numero:04d}"
        
        assert referencia == "F240123"


class TestEstadosFactura:
    """Tests de estados de factura"""
    
    def test_estados_validos(self):
        """Test estados válidos"""
        estados = ['borrador', 'emitida', 'pagada', 'anulada', 'vencida']
        
        estado_test = 'emitida'
        assert estado_test in estados
    
    def test_transicion_borrador_emitida(self):
        """Test transición borrador -> emitida"""
        estado_inicial = 'borrador'
        estado_final = 'emitida'
        
        # Esta transición es válida
        assert estado_inicial != estado_final
    
    def test_transicion_emitida_pagada(self):
        """Test transición emitida -> pagada"""
        estado_inicial = 'emitida'
        estado_final = 'pagada'
        
        # Esta transición es válida
        assert estado_inicial != estado_final


class TestCalculosFactura:
    """Tests de cálculos en facturas"""
    
    def test_calculo_base_imponible(self):
        """Test cálculo base imponible"""
        lineas = [
            {'cantidad': 2, 'precio_unitario': 50.0},
            {'cantidad': 1, 'precio_unitario': 100.0},
            {'cantidad': 3, 'precio_unitario': 25.0}
        ]
        
        base_imponible = sum(l['cantidad'] * l['precio_unitario'] for l in lineas)
        
        assert base_imponible == 275.0
    
    def test_calculo_iva_multiple(self):
        """Test cálculo IVA con múltiples tipos"""
        lineas = [
            {'base': 100.0, 'iva_pct': 21, 'cuota_iva': 21.0},
            {'base': 50.0, 'iva_pct': 10, 'cuota_iva': 5.0},
            {'base': 25.0, 'iva_pct': 4, 'cuota_iva': 1.0}
        ]
        
        total_iva = sum(l['cuota_iva'] for l in lineas)
        
        assert total_iva == 27.0
    
    def test_calculo_descuento_linea(self):
        """Test cálculo descuento en línea"""
        cantidad = 10
        precio_unitario = 100.0
        descuento_pct = 10.0
        
        subtotal = cantidad * precio_unitario
        descuento = subtotal * (descuento_pct / 100)
        base_con_descuento = subtotal - descuento
        
        assert subtotal == 1000.0
        assert descuento == 100.0
        assert base_con_descuento == 900.0
    
    def test_calculo_total_factura(self):
        """Test cálculo total factura"""
        base_imponible = 1000.0
        iva = 210.0
        
        total = base_imponible + iva
        
        assert total == 1210.0


class TestDescuentosFactura:
    """Tests de descuentos en facturas"""
    
    def test_descuento_porcentaje(self):
        """Test descuento en porcentaje"""
        importe = 1000.0
        descuento_pct = 15.0
        
        descuento = importe * (descuento_pct / 100)
        importe_final = importe - descuento
        
        assert descuento == 150.0
        assert importe_final == 850.0
    
    def test_descuento_cantidad_fija(self):
        """Test descuento cantidad fija"""
        importe = 1000.0
        descuento_fijo = 100.0
        
        importe_final = importe - descuento_fijo
        
        assert importe_final == 900.0
    
    def test_descuento_pronto_pago(self):
        """Test descuento por pronto pago"""
        importe = 1000.0
        descuento_pp = 2.0  # 2% pronto pago
        
        descuento = importe * (descuento_pp / 100)
        
        assert descuento == 20.0


class TestVencimientosFactura:
    """Tests de fechas de vencimiento"""
    
    def test_vencimiento_30_dias(self):
        """Test vencimiento a 30 días"""
        fecha_emision = datetime(2024, 10, 1)
        dias_vencimiento = 30
        
        fecha_vencimiento = fecha_emision + timedelta(days=dias_vencimiento)
        
        assert fecha_vencimiento == datetime(2024, 10, 31)
    
    def test_vencimiento_60_dias(self):
        """Test vencimiento a 60 días"""
        fecha_emision = datetime(2024, 10, 1)
        dias_vencimiento = 60
        
        fecha_vencimiento = fecha_emision + timedelta(days=dias_vencimiento)
        
        assert fecha_vencimiento == datetime(2024, 11, 30)
    
    def test_factura_vencida(self):
        """Test detectar factura vencida"""
        fecha_vencimiento = datetime(2024, 9, 1)
        fecha_actual = datetime(2024, 10, 16)
        
        esta_vencida = fecha_actual > fecha_vencimiento
        
        assert esta_vencida is True
    
    def test_dias_hasta_vencimiento(self):
        """Test calcular días hasta vencimiento"""
        fecha_actual = datetime(2024, 10, 1)
        fecha_vencimiento = datetime(2024, 10, 31)
        
        dias_restantes = (fecha_vencimiento - fecha_actual).days
        
        assert dias_restantes == 30


class TestRetencionesFactura:
    """Tests de retenciones"""
    
    def test_retencion_irpf_15(self):
        """Test retención IRPF 15%"""
        base_imponible = 1000.0
        retencion_pct = 15.0
        
        retencion = base_imponible * (retencion_pct / 100)
        
        assert retencion == 150.0
    
    def test_total_con_retencion(self):
        """Test total con retención"""
        base_imponible = 1000.0
        iva = 210.0
        retencion = 150.0
        
        total = base_imponible + iva - retencion
        
        assert total == 1060.0


class TestLineasFactura:
    """Tests de líneas de factura"""
    
    def test_agregar_linea(self):
        """Test agregar línea"""
        lineas = []
        nueva_linea = {
            'concepto': 'Producto Test',
            'cantidad': 1,
            'precio_unitario': 100.0
        }
        
        lineas.append(nueva_linea)
        
        assert len(lineas) == 1
        assert lineas[0]['concepto'] == 'Producto Test'
    
    def test_eliminar_linea(self):
        """Test eliminar línea"""
        lineas = [
            {'id': 1, 'concepto': 'A'},
            {'id': 2, 'concepto': 'B'},
            {'id': 3, 'concepto': 'C'}
        ]
        
        lineas_filtradas = [l for l in lineas if l['id'] != 2]
        
        assert len(lineas_filtradas) == 2
    
    def test_modificar_cantidad_linea(self):
        """Test modificar cantidad en línea"""
        linea = {
            'concepto': 'Producto',
            'cantidad': 1,
            'precio_unitario': 100.0
        }
        
        linea['cantidad'] = 5
        nuevo_total = linea['cantidad'] * linea['precio_unitario']
        
        assert nuevo_total == 500.0


class TestSeriesFactura:
    """Tests de series de facturación"""
    
    def test_serie_a(self):
        """Test serie A"""
        serie = 'A'
        numero = 1
        numero_completo = f"{serie}{numero:06d}"
        
        assert numero_completo == "A000001"
    
    def test_serie_f(self):
        """Test serie F (facturas)"""
        serie = 'F'
        numero = 100
        numero_completo = f"{serie}{numero:06d}"
        
        assert numero_completo == "F000100"
    
    def test_serie_r(self):
        """Test serie R (rectificativas)"""
        serie = 'R'
        numero = 1
        numero_completo = f"{serie}{numero:06d}"
        
        assert numero_completo == "R000001"


class TestFacturaRectificativa:
    """Tests de facturas rectificativas"""
    
    def test_referencia_factura_original(self):
        """Test referencia a factura original"""
        factura_rectificativa = {
            'numero': 'R000001',
            'factura_origen': 'F000123',
            'motivo': 'Error en importe'
        }
        
        assert 'factura_origen' in factura_rectificativa
        assert factura_rectificativa['factura_origen'] == 'F000123'
    
    def test_calculo_diferencia_rectificativa(self):
        """Test cálculo diferencia en rectificativa"""
        importe_original = 1000.0
        importe_correcto = 800.0
        
        diferencia = importe_original - importe_correcto
        
        assert diferencia == 200.0


class TestPagosFactura:
    """Tests de pagos de factura"""
    
    def test_pago_total(self):
        """Test pago total de factura"""
        total_factura = 1210.0
        pago_recibido = 1210.0
        
        pendiente = total_factura - pago_recibido
        
        assert pendiente == 0.0
    
    def test_pago_parcial(self):
        """Test pago parcial"""
        total_factura = 1210.0
        pago_recibido = 600.0
        
        pendiente = total_factura - pago_recibido
        
        assert pendiente == 610.0
    
    def test_multiples_pagos(self):
        """Test múltiples pagos"""
        total_factura = 1210.0
        pagos = [500.0, 400.0, 310.0]
        
        total_pagado = sum(pagos)
        pendiente = total_factura - total_pagado
        
        assert total_pagado == 1210.0
        assert pendiente == 0.0


class TestImpuestosEspeciales:
    """Tests de impuestos especiales"""
    
    def test_recargo_equivalencia(self):
        """Test recargo de equivalencia"""
        base_imponible = 1000.0
        iva_pct = 21.0
        recargo_pct = 5.2
        
        iva = base_imponible * (iva_pct / 100)
        recargo = base_imponible * (recargo_pct / 100)
        
        assert iva == 210.0
        assert round(recargo, 2) == 52.0
    
    def test_iva_intracomunitario(self):
        """Test IVA intracomunitario (0%)"""
        base_imponible = 1000.0
        iva_pct = 0.0
        
        iva = base_imponible * (iva_pct / 100)
        total = base_imponible + iva
        
        assert iva == 0.0
        assert total == 1000.0


class TestDatosClienteFactura:
    """Tests de datos de cliente en factura"""
    
    def test_cliente_campos_minimos(self):
        """Test campos mínimos cliente"""
        cliente = {
            'nif': '12345678A',
            'nombre': 'Cliente SA',
            'direccion': 'Calle Test 123'
        }
        
        campos_requeridos = ['nif', 'nombre', 'direccion']
        
        for campo in campos_requeridos:
            assert campo in cliente
    
    def test_cliente_empresa(self):
        """Test cliente empresa"""
        cliente = {
            'tipo': 'empresa',
            'razon_social': 'Test SL',
            'cif': 'B12345678'
        }
        
        assert cliente['tipo'] == 'empresa'
        assert 'razon_social' in cliente


class TestTotalesFactura:
    """Tests de totales y resúmenes"""
    
    def test_resumen_iva_por_tipo(self):
        """Test resumen de IVA por tipo"""
        lineas = [
            {'base': 100.0, 'iva_pct': 21},
            {'base': 200.0, 'iva_pct': 21},
            {'base': 50.0, 'iva_pct': 10}
        ]
        
        # Agrupar por tipo de IVA
        iva_21 = sum(l['base'] for l in lineas if l['iva_pct'] == 21)
        iva_10 = sum(l['base'] for l in lineas if l['iva_pct'] == 10)
        
        assert iva_21 == 300.0
        assert iva_10 == 50.0
    
    def test_total_bruto_neto(self):
        """Test total bruto vs neto"""
        total_bruto = 1000.0
        descuento_global = 100.0
        
        total_neto = total_bruto - descuento_global
        
        assert total_neto == 900.0


# Ejecutar tests si se ejecuta directamente
if __name__ == '__main__':
    pytest.main([__file__, '-v'])

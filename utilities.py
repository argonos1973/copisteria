"""Funciones compartidas para cálculos financieros"""
from decimal import Decimal, ROUND_HALF_UP

def calcular_importes(cantidad, precio, impuestos):
    """
    Calcula importes con precisión decimal
    REGLA FUNDAMENTAL: IVA se calcula desde subtotal SIN redondear
    Devuelve: {'subtotal': float, 'iva': float, 'total': float}
    """
    try:
        cantidad = Decimal(str(cantidad))
        precio = Decimal(str(precio))
        impuestos = Decimal(str(impuestos))
        
        # Subtotal SIN redondear (mantener precisión completa)
        subtotal_raw = cantidad * precio
        
        # IVA se calcula desde subtotal SIN redondear, luego se redondea
        iva = (subtotal_raw * impuestos / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Total = subtotal sin redondear + IVA redondeado, luego redondear el total
        total = (subtotal_raw + iva).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Subtotal para mostrar (redondeado solo para visualización)
        subtotal = subtotal_raw.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        return {
            'subtotal': float(subtotal),
            'iva': float(iva),
            'total': float(total)
        }
    except Exception as e:
        print(f"Error en cálculo: {e}")
        return {'subtotal': 0.0, 'iva': 0.0, 'total': 0.0}

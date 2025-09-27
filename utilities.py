"""Funciones compartidas para cálculos financieros"""
from decimal import Decimal, ROUND_HALF_UP

def calcular_importes(cantidad, precio, impuestos):
    """
    Calcula importes con precisión decimal
    Devuelve: {'subtotal': float, 'iva': float, 'total': float}
    """
    try:
        cantidad = Decimal(str(cantidad))
        precio = Decimal(str(precio))
        impuestos = Decimal(str(impuestos))
        
        subtotal = (cantidad * precio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        iva = (subtotal * impuestos / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total = (subtotal + iva).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        return {
            'subtotal': float(subtotal),
            'iva': float(iva),
            'total': float(total)
        }
    except Exception as e:
        print(f"Error en cálculo: {e}")
        return {'subtotal': 0.0, 'iva': 0.0, 'total': 0.0}

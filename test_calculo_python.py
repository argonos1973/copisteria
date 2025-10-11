#!/usr/bin/env python3
"""Test de cálculo de importes en Python"""

from utilities import calcular_importes

# Test con los datos del ticket T256228
print("=" * 60)
print("TEST: Ticket T256228 - IMPRESSIO A4 COLOR")
print("=" * 60)

precio = 0.70248
cantidad = 2
iva = 21

resultado = calcular_importes(cantidad, precio, iva)

print(f"\nDatos de entrada:")
print(f"  Precio unitario: {precio}€")
print(f"  Cantidad: {cantidad}")
print(f"  IVA: {iva}%")

print(f"\nResultado:")
print(f"  Subtotal: {resultado['subtotal']}€")
print(f"  IVA: {resultado['iva']}€")
print(f"  Total: {resultado['total']}€")

print(f"\nCálculo paso a paso:")
subtotal_raw = precio * cantidad
print(f"  1. Subtotal sin redondear: {precio} × {cantidad} = {subtotal_raw}€")

iva_raw = subtotal_raw * (iva / 100)
print(f"  2. IVA sin redondear: {subtotal_raw} × {iva}% = {iva_raw}€")
print(f"     IVA redondeado: {resultado['iva']}€")

total_raw = subtotal_raw + resultado['iva']
print(f"  3. Total sin redondear: {subtotal_raw} + {resultado['iva']} = {total_raw}€")
print(f"     Total redondeado: {resultado['total']}€")

print(f"\n{'='*60}")
if resultado['total'] == 1.70:
    print("✓ CORRECTO: Total = 1,70€")
else:
    print(f"✗ INCORRECTO: Total = {resultado['total']}€ (debería ser 1,70€)")
print("=" * 60)

#!/usr/bin/env python3
"""
Script para añadir @login_required a las rutas principales de app.py
"""

# Lista de rutas a proteger (sin las de /api/auth que ya son públicas)
ROUTES_TO_PROTECT = [
    '/api/facturas/paginado',
    '/api/facturas/siguiente_numero',
    '/api/facturas/actualizar',
    '/api/facturas',
    '/api/factura/numero',
    '/api/tickets',
    '/api/productos',
    '/api/contactos',
    '/api/proformas',
    '/api/presupuestos',
    '/estadisticas.html',
]

print("Rutas principales de API que deben protegerse:")
print("\nEn app.py, añadir @login_required antes de:")
for route in ROUTES_TO_PROTECT:
    print(f"  - {route}")

print("\n✅ db_utils.py ya modificado para usar BD por empresa")
print("⏳ Siguiente: Proteger rutas manualmente o crear decorador masivo")

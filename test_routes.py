#!/usr/bin/env python3
"""Script para listar todas las rutas registradas en Flask"""

import sys
sys.path.insert(0, '/var/www/html')

# Importar la app
from app import app

print("\n=== RUTAS REGISTRADAS EN FLASK ===\n")

for rule in app.url_map.iter_rules():
    methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
    print(f"{rule.endpoint:50s} {methods:20s} {rule}")

# Buscar específicamente LOGIN.html
print("\n=== BÚSQUEDA DE LOGIN.html ===\n")
for rule in app.url_map.iter_rules():
    if 'LOGIN' in str(rule) or 'login' in str(rule):
        print(f"Encontrada: {rule} → {rule.endpoint}")

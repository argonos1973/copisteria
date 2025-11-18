#!/usr/bin/env python3
import requests
import json

# Hacer login
login_data = {
    'username': 'admi',
    'password': 'Copisteria-1973',
    'empresa': 'caca'
}

session = requests.Session()

# Login
login_resp = session.post('http://localhost:5002/api/login', json=login_data)
print(f"Login: {login_resp.status_code}")

# Obtener menú
menu_resp = session.get('http://localhost:5002/api/auth/menu')
print(f"Menú: {menu_resp.status_code}")

if menu_resp.status_code == 200:
    menu = menu_resp.json()
    
    # Buscar facturas_emitidas y sus submódulos
    for item in menu:
        if item.get('codigo') == 'facturas_emitidas':
            print("\n✅ Encontrado: facturas_emitidas")
            if 'submenu' in item:
                print(f"  Submódulos: {len(item['submenu'])}")
                for submenu in item['submenu']:
                    codigo = submenu.get('codigo', 'SIN CODIGO')
                    nombre = submenu.get('nombre', 'SIN NOMBRE')
                    tiene_permisos = 'permisos' in submenu
                    
                    if tiene_permisos:
                        permisos = submenu['permisos']
                        print(f"    ✅ {codigo} ({nombre}) - Permisos: crear={permisos.get('crear', 0)}")
                    else:
                        print(f"    ❌ {codigo} ({nombre}) - SIN PERMISOS")
                        
    # Extraer todos los módulos con permisos
    print("\n📊 Módulos con permisos en el menú:")
    
    def extraer_modulos_con_permisos(items, nivel=0):
        for item in items:
            indent = "  " * nivel
            if 'codigo' in item and 'permisos' in item:
                print(f"{indent}✅ {item['codigo']}")
            elif 'codigo' in item:
                print(f"{indent}❌ {item['codigo']} (sin permisos)")
                
            if 'submenu' in item:
                extraer_modulos_con_permisos(item['submenu'], nivel + 1)
    
    extraer_modulos_con_permisos(menu)
else:
    print(f"Error: {menu_resp.text}")

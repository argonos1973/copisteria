#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
SCRIPT DE PRUEBA - SISTEMA MULTIEMPRESA
============================================================================
Archivo: test_multiempresa.py
Descripción: Prueba el sistema multiempresa localmente
Uso: python3 test_multiempresa.py
============================================================================
"""

import sqlite3
import os

# Colores para terminal
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{text.center(70)}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✓{RESET} {text}")

def print_error(text):
    print(f"{RED}✗{RESET} {text}")

def print_warning(text):
    print(f"{YELLOW}!{RESET} {text}")

def test_bd_usuarios():
    """Verifica que la BD de usuarios existe y tiene datos"""
    print_header("TEST 1: Base de Datos de Usuarios")
    
    db_path = '/var/www/html/db/usuarios_sistema.db'
    
    if not os.path.exists(db_path):
        print_error(f"BD no existe en: {db_path}")
        return False
    
    print_success(f"BD encontrada: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tablas = [row[0] for row in cursor.fetchall()]
        
        tablas_esperadas = ['empresas', 'usuarios', 'usuario_empresa', 'modulos', 
                           'permisos_usuario_modulo', 'configuracion_empresa', 'auditoria']
        
        for tabla in tablas_esperadas:
            if tabla in tablas:
                print_success(f"Tabla '{tabla}' existe")
            else:
                print_error(f"Tabla '{tabla}' NO existe")
        
        # Verificar datos iniciales
        cursor.execute("SELECT COUNT(*) FROM empresas")
        num_empresas = cursor.fetchone()[0]
        print(f"\n  Empresas registradas: {num_empresas}")
        
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        num_usuarios = cursor.fetchone()[0]
        print(f"  Usuarios registrados: {num_usuarios}")
        
        cursor.execute("SELECT COUNT(*) FROM modulos")
        num_modulos = cursor.fetchone()[0]
        print(f"  Módulos del sistema: {num_modulos}")
        
        # Mostrar empresa por defecto
        cursor.execute("SELECT codigo, nombre FROM empresas WHERE codigo='copisteria'")
        empresa = cursor.fetchone()
        if empresa:
            print_success(f"\nEmpresa por defecto: {empresa[1]} (código: {empresa[0]})")
        
        # Mostrar usuario admin
        cursor.execute("SELECT username, nombre_completo FROM usuarios WHERE username='admin'")
        usuario = cursor.fetchone()
        if usuario:
            print_success(f"Usuario admin: {usuario[1]} (username: {usuario[0]})")
        
        conn.close()
        return True
        
    except Exception as e:
        print_error(f"Error accediendo a BD: {e}")
        return False

def test_modulos():
    """Verifica que los módulos de Python existen"""
    print_header("TEST 2: Módulos Python")
    
    modulos = [
        ('multiempresa_config.py', 'Configuración multiempresa'),
        ('auth_middleware.py', 'Middleware de autenticación'),
        ('auth_routes.py', 'Rutas de autenticación'),
        ('frontend/LOGIN.html', 'Interfaz de login')
    ]
    
    todos_ok = True
    for archivo, desc in modulos:
        path = f'/var/www/html/{archivo}'
        if os.path.exists(path):
            print_success(f"{desc}: {archivo}")
        else:
            print_error(f"{desc}: {archivo} NO EXISTE")
            todos_ok = False
    
    return todos_ok

def test_import_modulos():
    """Intenta importar los módulos de autenticación"""
    print_header("TEST 3: Importación de Módulos")
    
    try:
        import multiempresa_config
        print_success("multiempresa_config importado correctamente")
        
        import auth_middleware
        print_success("auth_middleware importado correctamente")
        
        import auth_routes
        print_success("auth_routes importado correctamente")
        
        return True
    except Exception as e:
        print_error(f"Error importando módulos: {e}")
        return False

def test_credenciales():
    """Muestra las credenciales por defecto"""
    print_header("TEST 4: Credenciales por Defecto")
    
    print(f"\n  {YELLOW}Usuario:{RESET} admin")
    print(f"  {YELLOW}Password:{RESET} admin123")
    print(f"  {YELLOW}Empresa:{RESET} copisteria")
    print(f"\n  {RED}⚠️  CAMBIAR PASSWORD EN PRODUCCIÓN{RESET}\n")

def test_directorios():
    """Verifica directorios necesarios"""
    print_header("TEST 5: Directorios")
    
    dirs = [
        '/var/www/html/static/logos',
        '/var/www/html/db',
        '/var/www/html/frontend'
    ]
    
    todos_ok = True
    for dir_path in dirs:
        if os.path.exists(dir_path):
            print_success(f"Directorio existe: {dir_path}")
        else:
            print_warning(f"Directorio NO existe: {dir_path}")
            todos_ok = False
    
    return todos_ok

def main():
    """Ejecuta todos los tests"""
    print(f"\n{BLUE}")
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║           TEST SISTEMA MULTIEMPRESA - ALEPH70                      ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print(RESET)
    
    resultados = []
    
    resultados.append(("Base de Datos", test_bd_usuarios()))
    resultados.append(("Módulos Python", test_modulos()))
    resultados.append(("Importación", test_import_modulos()))
    resultados.append(("Directorios", test_directorios()))
    
    test_credenciales()
    
    # Resumen
    print_header("RESUMEN DE TESTS")
    
    todos_ok = True
    for nombre, resultado in resultados:
        if resultado:
            print_success(f"{nombre}")
        else:
            print_error(f"{nombre}")
            todos_ok = False
    
    if todos_ok:
        print(f"\n{GREEN}✓ TODOS LOS TESTS PASARON{RESET}")
        print(f"\n{YELLOW}Siguiente paso:{RESET}")
        print(f"  1. Arrancar Flask: python3 app.py")
        print(f"  2. Acceder a: http://localhost:5001/LOGIN.html")
        print(f"  3. Login con: admin / admin123 / copisteria\n")
        return 0
    else:
        print(f"\n{RED}✗ ALGUNOS TESTS FALLARON{RESET}\n")
        return 1

if __name__ == '__main__':
    exit(main())

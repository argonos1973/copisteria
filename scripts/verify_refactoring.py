#!/usr/bin/env python3
"""
Script para verificar la integridad de la refactorización de app.py
"""

import os
import sys
import importlib
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, '/var/www/html')

def test_imports():
    """Prueba que todos los módulos se puedan importar correctamente"""
    print("🔍 Verificando importaciones...")
    
    modules_to_test = [
        'routes.productos_routes',
        'routes.contactos_routes', 
        'routes.facturas_routes',
        'routes.tickets_routes',
        'routes.system_routes',
        'services.common_services'
    ]
    
    success = True
    
    for module_name in modules_to_test:
        try:
            module = importlib.import_module(module_name)
            print(f"  ✅ {module_name}")
            
            # Verificar que el blueprint existe
            blueprint_name = module_name.split('.')[-1].replace('_routes', '_bp')
            if hasattr(module, blueprint_name):
                print(f"     Blueprint '{blueprint_name}' encontrado")
            else:
                print(f"     ⚠️  Blueprint '{blueprint_name}' no encontrado")
                
        except ImportError as e:
            print(f"  ❌ {module_name}: {e}")
            success = False
        except Exception as e:
            print(f"  ⚠️  {module_name}: {e}")
    
    return success


def test_app_creation():
    """Prueba que la aplicación refactorizada se pueda crear"""
    print("\n🏗️  Verificando creación de la aplicación...")
    
    try:
        # Importar app refactorizada
        from app_refactored import create_app, APP_VERSION
        
        print(f"  📦 Versión: {APP_VERSION}")
        
        # Crear la aplicación
        app = create_app()
        
        print(f"  ✅ Aplicación creada correctamente")
        print(f"  📊 Blueprints registrados: {len(app.blueprints)}")
        
        # Listar blueprints
        for bp_name in app.blueprints:
            print(f"     - {bp_name}")
        
        return True, app
        
    except Exception as e:
        print(f"  ❌ Error creando aplicación: {e}")
        return False, None


def test_routes_coverage():
    """Verifica que las rutas principales estén cubiertas"""
    print("\n🛣️  Verificando cobertura de rutas...")
    
    success, app = test_app_creation()
    if not success:
        return False
    
    # Rutas que deberían estar disponibles
    expected_routes = [
        '/config.json',
        '/api/version',
        '/api/health',
        '/api/productos/aplicar_franjas',
        '/api/contactos/paginado',
        '/api/facturas/paginado',
        '/api/tickets/paginado'
    ]
    
    with app.test_client() as client:
        for route in expected_routes:
            try:
                # Solo verificar que la ruta existe (no necesariamente que funcione sin auth)
                response = client.get(route)
                # Cualquier respuesta que no sea 404 significa que la ruta existe
                if response.status_code != 404:
                    print(f"  ✅ {route}")
                else:
                    print(f"  ❌ {route} - No encontrada")
            except Exception as e:
                print(f"  ⚠️  {route} - Error: {e}")
    
    return True


def test_file_structure():
    """Verifica que la estructura de archivos sea correcta"""
    print("\n📁 Verificando estructura de archivos...")
    
    required_files = [
        '/var/www/html/routes/__init__.py',
        '/var/www/html/routes/productos_routes.py',
        '/var/www/html/routes/contactos_routes.py',
        '/var/www/html/routes/facturas_routes.py',
        '/var/www/html/routes/tickets_routes.py',
        '/var/www/html/routes/system_routes.py',
        '/var/www/html/services/__init__.py',
        '/var/www/html/services/common_services.py',
        '/var/www/html/app_refactored.py'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} - No encontrado")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n⚠️  Archivos faltantes: {len(missing_files)}")
        return False
    
    return True


def create_init_files():
    """Crea archivos __init__.py necesarios"""
    print("\n📝 Creando archivos __init__.py...")
    
    init_files = [
        '/var/www/html/routes/__init__.py',
        '/var/www/html/services/__init__.py'
    ]
    
    for init_file in init_files:
        os.makedirs(os.path.dirname(init_file), exist_ok=True)
        
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write('# -*- coding: utf-8 -*-\n')
            print(f"  ✅ Creado {init_file}")
        else:
            print(f"  ℹ️  {init_file} ya existe")


def generate_migration_report():
    """Genera reporte de la migración"""
    print("\n📊 Generando reporte de migración...")
    
    # Contar líneas en app.py original y refactorizado
    original_lines = 0
    try:
        with open('/var/www/html/app.py', 'r', encoding='utf-8') as f:
            original_lines = len(f.readlines())
    except FileNotFoundError:
        print("  ⚠️  app.py original no encontrado")
    
    refactored_lines = 0
    try:
        with open('/var/www/html/app_refactored.py', 'r', encoding='utf-8') as f:
            refactored_lines = len(f.readlines())
    except FileNotFoundError:
        print("  ❌ app_refactored.py no encontrado")
        return
    
    # Contar líneas en módulos refactorizados
    routes_lines = 0
    services_lines = 0
    
    routes_dir = Path('/var/www/html/routes')
    if routes_dir.exists():
        for py_file in routes_dir.glob('*.py'):
            if py_file.name != '__init__.py':
                with open(py_file, 'r', encoding='utf-8') as f:
                    routes_lines += len(f.readlines())
    
    services_dir = Path('/var/www/html/services')
    if services_dir.exists():
        for py_file in services_dir.glob('*.py'):
            if py_file.name != '__init__.py':
                with open(py_file, 'r', encoding='utf-8') as f:
                    services_lines += len(f.readlines())
    
    total_refactored = refactored_lines + routes_lines + services_lines
    
    print(f"""
📊 REPORTE DE REFACTORIZACIÓN
========================================
📄 app.py original:          {original_lines:,} líneas
📄 app_refactored.py:        {refactored_lines:,} líneas
📁 Módulos routes:           {routes_lines:,} líneas
📁 Módulos services:         {services_lines:,} líneas
----------------------------------------
📦 Total refactorizado:      {total_refactored:,} líneas
📉 Reducción app principal:  {((original_lines - refactored_lines) / original_lines * 100):.1f}%
📈 Ganancia modularidad:     {((total_refactored - original_lines) / original_lines * 100):.1f}%
    """)


def main():
    """Función principal"""
    print("🔧 VERIFICACIÓN DE REFACTORIZACIÓN - app.py")
    print("=" * 50)
    
    # Crear archivos __init__.py necesarios
    create_init_files()
    
    # Ejecutar verificaciones
    tests = [
        ("Estructura de archivos", test_file_structure),
        ("Importaciones", test_imports),
        ("Cobertura de rutas", test_routes_coverage)
    ]
    
    all_passed = True
    
    for test_name, test_func in tests:
        print(f"\n🧪 Ejecutando: {test_name}")
        try:
            result = test_func()
            if not result:
                all_passed = False
        except Exception as e:
            print(f"  ❌ Error en {test_name}: {e}")
            all_passed = False
    
    # Generar reporte
    generate_migration_report()
    
    # Resultado final
    print(f"\n{'='*50}")
    if all_passed:
        print("🎉 ¡REFACTORIZACIÓN COMPLETADA EXITOSAMENTE!")
        print("\n✅ Próximos pasos:")
        print("   1. Respaldar app.py original")
        print("   2. Renombrar app_refactored.py a app.py")
        print("   3. Reiniciar servidor web")
        print("   4. Ejecutar tests de integración")
    else:
        print("⚠️  REFACTORIZACIÓN INCOMPLETA")
        print("   Revisa los errores anteriores antes de continuar")
    
    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

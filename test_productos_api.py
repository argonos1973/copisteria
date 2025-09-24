#!/usr/bin/env python3
"""
Juego de pruebas para el endpoint de productos - Verificación de decimales significativos
Prueba la creación y actualización de productos via API REST para confirmar
que las franjas de descuento se generan con exactamente 5 decimales significativos.
"""

import requests
import json
import sqlite3
import sys
import time
from datetime import datetime

# Configuración de servidores
SERVERS = {
    "local_55": "http://localhost:5001",
    "remote_18": "http://192.168.1.18:5001"
}

def test_crear_producto_api(server_url, test_case):
    """
    Prueba la creación de un producto via API POST /api/productos
    """
    print(f"\n=== PRUEBA: {test_case['nombre']} ===")
    print(f"Servidor: {server_url}")
    
    payload = {
        "nombre": test_case["nombre"],
        "descripcion": test_case["descripcion"],
        "subtotal": test_case["subtotal"],
        "impuestos": test_case["impuestos"],
        "total": test_case["total"],
        "config_franjas": test_case["config_franjas"]
    }
    
    try:
        # Realizar petición POST
        response = requests.post(
            f"{server_url}/api/productos",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200 or response.status_code == 201:
            result = response.json()
            print(f"Respuesta API: {result}")
            
            if result.get("success"):
                producto_id = result.get("id") or result.get("producto_id")
                if producto_id:
                    return verificar_franjas_bd(producto_id, test_case, server_url)
                else:
                    print("❌ No se pudo obtener el ID del producto creado")
                    return False
            else:
                print(f"❌ Error en API: {result.get('message', 'Error desconocido')}")
                return False
        else:
            print(f"❌ Error HTTP: {response.status_code}")
            print(f"Respuesta: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

def verificar_franjas_bd(producto_id, test_case, server_url):
    """
    Verifica las franjas generadas en la base de datos
    """
    try:
        # Determinar ruta de BD según servidor
        if "localhost" in server_url or "192.168.1.55" in server_url:
            db_path = "/var/www/html/db/aleph70.db"
        else:
            # Para servidor remoto, usar API para verificar
            return verificar_franjas_api(producto_id, test_case, server_url)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Obtener franjas del producto
        cursor.execute("""
            SELECT min_cantidad, max_cantidad, porcentaje_descuento 
            FROM descuento_producto_franja 
            WHERE producto_id = ? 
            ORDER BY min_cantidad
        """, (producto_id,))
        
        franjas = cursor.fetchall()
        conn.close()
        
        if not franjas:
            print(f"❌ No se encontraron franjas para producto {producto_id}")
            return False
        
        print(f"\n📊 Franjas generadas para producto {producto_id}:")
        
        # Verificar configuración esperada
        config = test_case["config_franjas"]
        desc_inicial = config["descuento_inicial"]
        incremento = config["incremento_franja"]
        num_franjas_esperadas = config["numero_franjas"]
        
        # Validar número de franjas
        if len(franjas) != num_franjas_esperadas:
            print(f"❌ Número de franjas incorrecto: esperado {num_franjas_esperadas}, obtenido {len(franjas)}")
            return False
        
        # Validar cada franja
        errores = []
        decimales_significativos = 0
        
        for i, (min_cant, max_cant, desc_actual) in enumerate(franjas):
            # Calcular descuento esperado
            if i == 0:
                desc_esperado = 0.0
            else:
                desc_esperado = desc_inicial + ((i - 1) * incremento)
            
            desc_esperado = min(60.0, max(0.0, desc_esperado))
            desc_esperado = round(float(desc_esperado), 5)
            
            print(f"  Franja {i+1}: {min_cant}-{max_cant} = {desc_actual:.5f}% (esperado: {desc_esperado:.5f}%)")
            
            # Verificar precisión
            if abs(desc_actual - desc_esperado) > 0.00001:
                errores.append(f"Franja {i+1}: esperado {desc_esperado:.5f}%, actual {desc_actual:.5f}%")
            
            # Contar decimales significativos
            if desc_actual > 0 and desc_actual != int(desc_actual):
                decimales_significativos += 1
        
        print(f"\n✅ Franjas con decimales significativos: {decimales_significativos}/{len(franjas)}")
        
        if errores:
            print(f"\n❌ Errores encontrados:")
            for error in errores:
                print(f"   - {error}")
            return False
        else:
            print(f"✅ Todas las franjas calculadas correctamente")
            return True
            
    except Exception as e:
        print(f"❌ Error verificando BD: {e}")
        return False

def verificar_franjas_api(producto_id, test_case, server_url):
    """
    Verifica franjas via API para servidores remotos
    """
    try:
        response = requests.get(f"{server_url}/api/productos/{producto_id}/franjas_descuento", timeout=10)
        
        if response.status_code == 200:
            franjas_data = response.json()
            print(f"✅ Franjas obtenidas via API: {len(franjas_data)} franjas")
            
            # Verificar que tienen decimales significativos
            decimales_sig = sum(1 for f in franjas_data if f.get("porcentaje_descuento", 0) > 0 and f.get("porcentaje_descuento", 0) != int(f.get("porcentaje_descuento", 0)))
            print(f"✅ Franjas con decimales significativos: {decimales_sig}/{len(franjas_data)}")
            
            return decimales_sig > 0
        else:
            print(f"❌ Error obteniendo franjas via API: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error verificando via API: {e}")
        return False

def ejecutar_juego_pruebas():
    """
    Ejecuta el juego completo de pruebas
    """
    print("🧪 JUEGO DE PRUEBAS: DECIMALES SIGNIFICATIVOS EN PRODUCTOS")
    print("=" * 60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Casos de prueba
    test_cases = [
        {
            "nombre": "TEST_DECIMALES_BASICO",
            "descripcion": "Prueba básica con decimales significativos",
            "subtotal": 15.0,
            "impuestos": 21,
            "total": 18.15,
            "config_franjas": {
                "calculo_automatico": 1,
                "numero_franjas": 4,
                "ancho_franja": 10,
                "descuento_inicial": 1.23456,
                "incremento_franja": 0.98765,
                "no_generar_franjas": 0
            }
        },
        {
            "nombre": "TEST_DECIMALES_AVANZADO",
            "descripcion": "Prueba avanzada con más franjas y decimales complejos",
            "subtotal": 30.0,
            "impuestos": 21,
            "total": 36.3,
            "config_franjas": {
                "calculo_automatico": 1,
                "numero_franjas": 6,
                "ancho_franja": 15,
                "descuento_inicial": 2.71828,
                "incremento_franja": 1.41421,
                "no_generar_franjas": 0
            }
        },
        {
            "nombre": "TEST_DECIMALES_PRECISION",
            "descripcion": "Prueba de precisión con 5 decimales exactos",
            "subtotal": 50.0,
            "impuestos": 21,
            "total": 60.5,
            "config_franjas": {
                "calculo_automatico": 1,
                "numero_franjas": 5,
                "ancho_franja": 20,
                "descuento_inicial": 3.14159,
                "incremento_franja": 2.71828,
                "no_generar_franjas": 0
            }
        }
    ]
    
    resultados = {}
    
    # Probar en servidor local (.55)
    print(f"\n🖥️  PROBANDO SERVIDOR LOCAL (.55)")
    print("-" * 40)
    
    resultados["local"] = []
    for test_case in test_cases:
        # Añadir timestamp al nombre para evitar duplicados
        test_case["nombre"] = f"{test_case['nombre']}_{int(time.time())}"
        
        resultado = test_crear_producto_api(SERVERS["local_55"], test_case)
        resultados["local"].append({
            "test": test_case["nombre"],
            "success": resultado
        })
        
        time.sleep(1)  # Pausa entre pruebas
    
    # Resumen de resultados
    print(f"\n📋 RESUMEN DE RESULTADOS")
    print("=" * 40)
    
    for server, tests in resultados.items():
        exitosos = sum(1 for t in tests if t["success"])
        total = len(tests)
        print(f"\n{server.upper()}:")
        print(f"  ✅ Exitosos: {exitosos}/{total}")
        
        for test in tests:
            status = "✅" if test["success"] else "❌"
            print(f"  {status} {test['test']}")
    
    # Resultado final
    total_exitosos = sum(len([t for t in tests if t["success"]]) for tests in resultados.values())
    total_pruebas = sum(len(tests) for tests in resultados.values())
    
    print(f"\n🎯 RESULTADO FINAL: {total_exitosos}/{total_pruebas} pruebas exitosas")
    
    if total_exitosos == total_pruebas:
        print("🎉 ¡TODAS LAS PRUEBAS PASARON! Sistema funcionando correctamente.")
        return True
    else:
        print("⚠️  Algunas pruebas fallaron. Revisar configuración.")
        return False

if __name__ == "__main__":
    success = ejecutar_juego_pruebas()
    sys.exit(0 if success else 1)

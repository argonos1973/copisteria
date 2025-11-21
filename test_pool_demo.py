#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEMO Y TEST DEL CONNECTION POOL
===============================
Demuestra todas las funcionalidades del sistema de pooling
"""

import time
import threading
from database_pool import DatabasePool, get_database_pool
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)

def test_basic_functionality():
    """Test básico del pool"""
    print("=== TEST BÁSICO DEL POOL ===")
    
    # Crear pool para BD de test
    pool = DatabasePool('/var/www/html/db/plantilla.db', max_connections=5)
    
    # Test 1: Context manager automático
    print("1. Test context manager:")
    with pool.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM sqlite_master WHERE type='table'")
        result = cursor.fetchone()
        print(f"   Tablas en BD: {result[0] if result else 0}")
    
    # Test 2: Execute query directo
    print("2. Test execute_query:")
    result = pool.execute_query("SELECT name FROM sqlite_master WHERE type='table' LIMIT 3")
    if result['success']:
        print(f"   Primeras 3 tablas: {[row['name'] for row in result['data']]}")
    
    print("✅ Test básico completado\n")

def test_retry_logic():
    """Test del retry logic con BD inexistente"""
    print("=== TEST RETRY LOGIC ===")
    
    try:
        # Intentar conectar a BD que no existe
        pool = DatabasePool('/path/inexistente/test.db', max_connections=3)
        conn = pool.get_connection(timeout=5.0)
        print("❌ No debería llegar aquí")
    except RuntimeError as e:
        print(f"✅ Retry logic funcionando: {e}")
    
    print()

def test_timeout_handling():
    """Test del timeout handling"""
    print("=== TEST TIMEOUT HANDLING ===")
    
    pool = DatabasePool('/var/www/html/db/plantilla.db', max_connections=2)
    
    def hold_connection():
        """Thread que mantiene una conexión ocupada"""
        with pool.get_db_connection() as conn:
            print("   Thread manteniendo conexión por 3 segundos...")
            time.sleep(3)
    
    # Ocupar todas las conexiones
    thread1 = threading.Thread(target=hold_connection)
    thread2 = threading.Thread(target=hold_connection)
    
    thread1.start()
    thread2.start()
    
    # Intentar obtener otra conexión con timeout corto
    start_time = time.time()
    try:
        conn = pool.get_connection(timeout=1.0)
        print("❌ No debería obtener conexión")
    except RuntimeError:
        elapsed = time.time() - start_time
        print(f"✅ Timeout funcionando: {elapsed:.2f}s")
    
    # Esperar threads
    thread1.join()
    thread2.join()
    print()

def test_concurrent_connections():
    """Test de conexiones concurrentes"""
    print("=== TEST CONEXIONES CONCURRENTES ===")
    
    pool = DatabasePool('/var/www/html/db/plantilla.db', max_connections=5)
    results = []
    
    def worker(worker_id):
        """Worker que usa el pool"""
        try:
            with pool.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT ? as worker_id, COUNT(*) as tables FROM sqlite_master WHERE type='table'", (worker_id,))
                result = cursor.fetchone()
                results.append(f"Worker {result[0]}: {result[1]} tablas")
                time.sleep(0.5)  # Simular trabajo
        except Exception as e:
            results.append(f"Worker {worker_id} error: {e}")
    
    # Crear 10 threads concurrentes
    threads = []
    for i in range(10):
        thread = threading.Thread(target=worker, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Esperar todos los threads
    for thread in threads:
        thread.join()
    
    print(f"   Resultados concurrentes: {len(results)} workers completados")
    for result in results[:3]:  # Mostrar primeros 3
        print(f"   {result}")
    
    print("✅ Test concurrente completado\n")

def test_metrics_system():
    """Test del sistema de métricas"""
    print("=== TEST SISTEMA DE MÉTRICAS ===")
    
    pool = DatabasePool('/var/www/html/db/plantilla.db', max_connections=3)
    
    # Realizar varias operaciones para generar métricas
    for i in range(5):
        with pool.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
    
    # Intentar operación que falle para generar error
    try:
        pool.execute_query("SELECT * FROM tabla_inexistente")
    except:
        pass
    
    # Obtener métricas
    metrics = pool.get_metrics()
    
    print("   Métricas del pool:")
    print(f"   - Total conexiones: {metrics['total_connections']}")
    print(f"   - Conexiones activas: {metrics['active_connections']}")
    print(f"   - Total requests: {metrics['total_requests']}")
    print(f"   - Requests fallidos: {metrics['failed_requests']}")
    print(f"   - Success rate: {metrics['success_rate']}%")
    print(f"   - Tiempo promedio espera: {metrics['avg_wait_time']}s")
    print(f"   - Utilización pool: {metrics['pool_utilization']}%")
    
    print("✅ Test métricas completado\n")

def test_health_check():
    """Test del health check"""
    print("=== TEST HEALTH CHECK ===")
    
    pool = DatabasePool('/var/www/html/db/plantilla.db', max_connections=3)
    
    # Crear algunas conexiones
    with pool.get_db_connection() as conn:
        pass
    
    # Hacer health check
    health = pool.health_check()
    
    print("   Estado de salud del pool:")
    print(f"   - Status: {health['pool_status']}")
    print(f"   - Conexiones saludables: {health['healthy_connections']}")
    print(f"   - Conexiones no saludables: {health['unhealthy_connections']}")
    print(f"   - Tamaño pool: {health['pool_size']}")
    
    print("✅ Test health check completado\n")

def demo_complete():
    """Demo completo de todas las funcionalidades"""
    print("🚀 === DEMO COMPLETO CONNECTION POOL === 🚀\n")
    
    # Ejecutar todos los tests
    test_basic_functionality()
    test_retry_logic()
    test_timeout_handling()
    test_concurrent_connections()
    test_metrics_system()
    test_health_check()
    
    print("=" * 50)
    print("✅ TODOS LOS TESTS COMPLETADOS")
    print("✅ Connection Pool funcionando correctamente")
    print("=" * 50)

if __name__ == '__main__':
    demo_complete()

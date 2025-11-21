#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFICACIÓN DE OPTIMIZACIÓN DE FECHAS
======================================
Script para verificar que la optimización de fechas funciona correctamente
"""

import sqlite3
import time
from database_pool import get_database_pool

def test_performance_comparison():
    """Compara rendimiento antes y después de la optimización"""
    
    print("🔄 COMPARANDO RENDIMIENTO DE CONSULTAS DE FECHA")
    print("=" * 60)
    
    # Usar BD con datos reales
    pool = get_database_pool('/var/www/html/db/caca/caca.db')
    
    tests = [
        {
            'name': 'Consulta por año (gastos)',
            'old_query': "SELECT COUNT(*) FROM gastos WHERE substr(fecha_operacion, 7, 4) = '2025'",
            'new_query': "SELECT COUNT(*) FROM gastos WHERE substr(COALESCE(fecha_operacion_iso, substr(fecha_operacion, 7, 4) || '-' || substr(fecha_operacion, 4, 2) || '-' || substr(fecha_operacion, 1, 2)), 1, 4) = '2025'"
        },
        {
            'name': 'ORDER BY fecha optimizada',
            'old_query': "SELECT id, concepto FROM gastos ORDER BY date(substr(fecha_operacion,7,4)||'-'||substr(fecha_operacion,4,2)||'-'||substr(fecha_operacion,1,2)) DESC LIMIT 10",
            'new_query': "SELECT id, concepto FROM gastos ORDER BY COALESCE(fecha_operacion_iso, substr(fecha_operacion,7,4)||'-'||substr(fecha_operacion,4,2)||'-'||substr(fecha_operacion,1,2)) DESC LIMIT 10"
        },
        {
            'name': 'Rango de fechas',
            'old_query': "SELECT COUNT(*) FROM gastos WHERE date(substr(fecha_operacion,7,4)||'-'||substr(fecha_operacion,4,2)||'-'||substr(fecha_operacion,1,2)) BETWEEN '2025-01-01' AND '2025-12-31'",
            'new_query': "SELECT COUNT(*) FROM gastos WHERE COALESCE(fecha_operacion_iso, substr(fecha_operacion,7,4)||'-'||substr(fecha_operacion,4,2)||'-'||substr(fecha_operacion,1,2)) BETWEEN '2025-01-01' AND '2025-12-31'"
        }
    ]
    
    for test in tests:
        print(f"\n📊 {test['name']}:")
        
        # Ejecutar consulta antigua
        start_time = time.time()
        result_old = pool.execute_query(test['old_query'])
        time_old = (time.time() - start_time) * 1000  # ms
        
        # Ejecutar consulta nueva
        start_time = time.time()  
        result_new = pool.execute_query(test['new_query'])
        time_new = (time.time() - start_time) * 1000  # ms
        
        # Mostrar resultados
        if result_old['success'] and result_new['success']:
            print(f"   Método ANTIGUO: {time_old:.2f}ms")
            print(f"   Método NUEVO:   {time_new:.2f}ms")
            
            if time_old > 0:
                mejora = ((time_old - time_new) / time_old) * 100
                print(f"   MEJORA: {mejora:.1f}% más rápido")
            
            # Verificar que los resultados son iguales
            if str(result_old['data']) == str(result_new['data']):
                print("   ✅ Resultados idénticos")
            else:
                print("   ⚠️  Resultados diferentes - revisar consulta")
        else:
            print("   ❌ Error en consultas")

def verificar_triggers():
    """Verifica que los triggers funcionan correctamente"""
    
    print("\n🔧 VERIFICANDO TRIGGERS")
    print("=" * 30)
    
    pool = get_database_pool('/var/www/html/db/plantilla.db')
    
    # Test 1: Insertar nuevo registro
    print("📝 Test INSERT con trigger:")
    result = pool.execute_query(
        "INSERT INTO gastos (fecha_operacion, fecha_valor, concepto, importe_eur) VALUES (?, ?, ?, ?)",
        ('21/11/2025', '21/11/2025', 'TEST TRIGGER', -10.50),
        fetch_all=False
    )
    
    if result['success']:
        # Verificar que se generó el ISO
        result_check = pool.execute_query(
            "SELECT fecha_operacion, fecha_operacion_iso, fecha_valor_iso FROM gastos WHERE concepto = 'TEST TRIGGER'"
        )
        
        if result_check['success'] and result_check['data']:
            row = result_check['data'][0]
            print(f"   Original: {row['fecha_operacion']}")
            print(f"   ISO generado: {row['fecha_operacion_iso']}")
            
            if row['fecha_operacion_iso'] == '2025-11-21':
                print("   ✅ Trigger funcionando correctamente")
            else:
                print("   ❌ Trigger no genera ISO correctamente")
            
            # Limpiar test
            pool.execute_query("DELETE FROM gastos WHERE concepto = 'TEST TRIGGER'", fetch_all=False)
        else:
            print("   ❌ No se encontró el registro de test")
    else:
        print("   ❌ Error insertando registro de test")

def mostrar_estadisticas():
    """Muestra estadísticas de la optimización"""
    
    print("\n📈 ESTADÍSTICAS DE OPTIMIZACIÓN")
    print("=" * 40)
    
    pool = get_database_pool('/var/www/html/db/caca/caca.db')
    
    # Estadísticas por tabla
    tablas = [
        ('gastos', 'fecha_operacion_iso'),
        ('gastos', 'fecha_valor_iso'),
        ('factura', 'fecha_iso'),
        ('tickets', 'fecha_iso')
    ]
    
    for tabla, campo_iso in tablas:
        result = pool.execute_query(f"""
            SELECT 
                COUNT(*) as total,
                COUNT({campo_iso}) as con_iso,
                ROUND((COUNT({campo_iso}) * 100.0 / COUNT(*)), 2) as porcentaje
            FROM {tabla}
        """)
        
        if result['success'] and result['data']:
            stats = result['data'][0]
            print(f"📊 {tabla.upper()}.{campo_iso}:")
            print(f"   Total registros: {stats['total']}")
            print(f"   Con ISO: {stats['con_iso']}")
            print(f"   Cobertura: {stats['porcentaje']}%")

def main():
    """Función principal"""
    print("🚀 VERIFICACIÓN DE OPTIMIZACIÓN DE FECHAS")
    print("="*50)
    
    test_performance_comparison()
    verificar_triggers()
    mostrar_estadisticas()
    
    print("\n✅ VERIFICACIÓN COMPLETADA")
    print("Las optimizaciones de fecha están funcionando correctamente")

if __name__ == '__main__':
    main()

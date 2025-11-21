#!/usr/bin/env python3
"""
Script para detectar y reportar consultas SELECT * que deberían optimizarse
"""
import os
import re
from collections import defaultdict

def analyze_select_star():
    """Analiza todos los archivos Python en busca de SELECT *"""
    
    findings = defaultdict(list)
    
    # Patrón para encontrar SELECT *
    pattern = r'SELECT\s+\*\s+FROM\s+(\w+)'
    
    for root, dirs, files in os.walk('.'):
        # Ignorar directorios no relevantes
        dirs[:] = [d for d in dirs if d not in ['venv', '.git', '__pycache__', 'logs']]
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Buscar todas las coincidencias
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    
                    for match in matches:
                        table_name = match.group(1)
                        # Encontrar el número de línea
                        line_num = content[:match.start()].count('\n') + 1
                        findings[filepath].append({
                            'line': line_num,
                            'table': table_name,
                            'query': match.group(0)
                        })
                        
                except Exception as e:
                    print(f"Error procesando {filepath}: {e}")
    
    return findings

def suggest_optimizations(findings):
    """Sugiere optimizaciones para cada tabla"""
    
    # Campos comunes por tabla (esto debería personalizarse según tu esquema)
    table_fields = {
        'facturas': 'id, numero, fecha, cliente_id, total, estado',
        'tickets': 'id, numero, fecha, total, cliente_id',
        'productos': 'id, nombre, precio, codigo, stock',
        'clientes': 'id, nombre, email, telefono, nif',
        'contactos': 'id, nombre, email, empresa',
        'gastos': 'id, fecha, concepto, importe, categoria'
    }
    
    print("\n📋 REPORTE DE OPTIMIZACIÓN DE CONSULTAS SELECT *\n")
    print("=" * 70)
    
    total_queries = 0
    
    for filepath, queries in findings.items():
        print(f"\n📄 {filepath}")
        print("-" * 50)
        
        for query_info in queries:
            total_queries += 1
            table = query_info['table'].lower()
            
            print(f"  Línea {query_info['line']}: {query_info['query']}")
            
            if table in table_fields:
                print(f"  ✅ Sugerencia: SELECT {table_fields[table]} FROM {query_info['table']}")
            else:
                print(f"  ⚠️  Revisar campos necesarios para la tabla '{query_info['table']}'")
            print()
    
    print("=" * 70)
    print(f"\n📊 RESUMEN:")
    print(f"   Total de consultas SELECT * encontradas: {total_queries}")
    print(f"   Archivos afectados: {len(findings)}")
    
    if total_queries > 0:
        print(f"\n⚠️  IMPACTO EN RENDIMIENTO:")
        print(f"   - Cada SELECT * trae datos innecesarios")
        print(f"   - Aumenta el uso de memoria y red")
        print(f"   - Dificulta el mantenimiento del código")
        print(f"\n💡 RECOMENDACIÓN:")
        print(f"   Reemplazar con campos específicos para mejorar rendimiento")
    else:
        print(f"\n✅ ¡Excelente! No se encontraron consultas SELECT *")

def main():
    findings = analyze_select_star()
    suggest_optimizations(findings)
    
    # Opcionalmente, generar un archivo con las sugerencias
    with open('select_star_report.txt', 'w') as f:
        f.write("CONSULTAS SELECT * A OPTIMIZAR\n")
        f.write("=" * 50 + "\n\n")
        
        for filepath, queries in findings.items():
            f.write(f"Archivo: {filepath}\n")
            for query in queries:
                f.write(f"  Línea {query['line']}: {query['query']}\n")
            f.write("\n")
    
    print(f"\n📄 Reporte guardado en: select_star_report.txt")

if __name__ == "__main__":
    main()

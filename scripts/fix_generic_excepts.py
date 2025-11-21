#!/usr/bin/env python3
"""
Script para migrar except: genéricos a excepciones específicas
"""
import os
import re
import ast

def analyze_except_blocks(filepath):
    """Analiza bloques except en un archivo"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Buscar patrones de except genéricos
        generic_pattern = r'(\s*)except:\s*\n'
        matches = list(re.finditer(generic_pattern, content))
        
        if not matches:
            return None, 0
        
        # Analizar el contexto para sugerir excepciones específicas
        suggestions = []
        for match in matches:
            indent = match.group(1)
            start = max(0, match.start() - 500)
            context = content[start:match.end() + 200]
            
            # Detectar operaciones comunes y sugerir excepciones
            suggested_exception = "Exception"  # Por defecto
            
            if any(keyword in context for keyword in ['open(', 'read(', 'write(']):
                suggested_exception = "(IOError, OSError)"
            elif any(keyword in context for keyword in ['json.loads', 'json.dumps', 'json.load']):
                suggested_exception = "json.JSONDecodeError"
            elif any(keyword in context for keyword in ['int(', 'float(', 'Decimal(']):
                suggested_exception = "(ValueError, TypeError)"
            elif any(keyword in context for keyword in ['cursor.execute', 'conn.execute', 'get_db_connection']):
                suggested_exception = "(sqlite3.Error, Exception)"
            elif any(keyword in context for keyword in ['import ', 'from ']):
                suggested_exception = "ImportError"
            elif any(keyword in context for keyword in ['request.', 'jsonify', 'session']):
                suggested_exception = "Exception"
            elif any(keyword in context for keyword in ['[', ']', 'get(', 'pop(']):
                suggested_exception = "(KeyError, IndexError, AttributeError)"
            else:
                suggested_exception = "Exception"
            
            suggestions.append((match.start(), match.end(), indent, suggested_exception))
        
        return suggestions, len(matches)
    
    except Exception as e:
        print(f"Error analizando {filepath}: {e}")
        return None, 0

def fix_generic_excepts(filepath, auto_fix=False):
    """Corrige except genéricos en un archivo"""
    suggestions, count = analyze_except_blocks(filepath)
    
    if not suggestions:
        return 0
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Aplicar correcciones de atrás hacia adelante para mantener índices
    for start, end, indent, exception_type in reversed(suggestions):
        old_text = content[start:end]
        new_text = f"{indent}except {exception_type}:\n"
        content = content[:start] + new_text + content[end:]
    
    if auto_fix:
        # Hacer backup
        backup_path = f"{filepath}.backup_except"
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Escribir archivo corregido
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ {filepath}: {count} except genéricos corregidos")
    
    return count

def main():
    """Procesar todos los archivos Python"""
    print("🔍 Analizando archivos Python para corregir except genéricos...\n")
    
    total_fixed = 0
    files_modified = 0
    
    # Archivos prioritarios a corregir
    priority_files = [
        'app.py',
        'db_utils.py',
        'database_pool.py',
        'factura.py',
        'gastos.py',
        'tickets.py',
        'dashboard_routes.py',
        'auth_routes.py',
        'admin_routes.py'
    ]
    
    # Primero procesar archivos prioritarios
    print("📌 Procesando archivos prioritarios...")
    for filename in priority_files:
        if os.path.exists(filename):
            count = fix_generic_excepts(filename, auto_fix=True)
            if count > 0:
                total_fixed += count
                files_modified += 1
    
    # Luego procesar el resto
    print("\n📁 Procesando otros archivos...")
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in ['venv', '.git', '__pycache__']]
        
        for file in files:
            if file.endswith('.py') and file not in priority_files:
                filepath = os.path.join(root, file)
                count = fix_generic_excepts(filepath, auto_fix=True)
                if count > 0:
                    total_fixed += count
                    files_modified += 1
    
    print(f"\n✅ RESUMEN:")
    print(f"   Total de except genéricos corregidos: {total_fixed}")
    print(f"   Archivos modificados: {files_modified}")
    print(f"\n💡 Los archivos originales se guardaron con extensión .backup_except")
    
    return total_fixed, files_modified

if __name__ == "__main__":
    main()

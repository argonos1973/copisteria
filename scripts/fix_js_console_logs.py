#!/usr/bin/env python3
"""
Script para arreglar console.logs mal comentados en archivos JS
"""
import re
import os

def fix_multiline_console_logs(filepath):
    """Arregla console.logs multilinea mal comentados"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        fixed = False
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Detectar console.log comentado que podría tener continuación
            if '// console.' in line and ('({' in line or '({' in lines[i] if i+1 < len(lines) else False):
                # Buscar el cierre del console.log
                open_count = line.count('(') - line.count(')')
                brace_count = line.count('{') - line.count('}')
                
                if open_count > 0 or brace_count > 0:
                    # Es multilinea, comentar las siguientes líneas
                    j = i + 1
                    while j < len(lines) and (open_count > 0 or brace_count > 0):
                        if not lines[j].strip().startswith('//'):
                            lines[j] = '        // ' + lines[j].lstrip()
                            fixed = True
                        
                        open_count += lines[j].count('(') - lines[j].count(')')
                        brace_count += lines[j].count('{') - lines[j].count('}')
                        j += 1
            
            i += 1
        
        if fixed:
            # Hacer backup
            backup_path = f"{filepath}.backup_consolelog"
            if not os.path.exists(backup_path):
                with open(filepath, 'r', encoding='utf-8') as f:
                    with open(backup_path, 'w', encoding='utf-8') as bf:
                        bf.write(f.read())
            
            # Guardar archivo corregido
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            return True
        return False
    
    except Exception as e:
        print(f"Error procesando {filepath}: {e}")
        return False

def main():
    """Procesar todos los archivos JS"""
    print("🔧 Arreglando console.logs mal comentados en archivos JS...\n")
    
    fixed_count = 0
    
    # Procesar archivos en static/
    for root, dirs, files in os.walk('static'):
        for file in files:
            if file.endswith('.js'):
                filepath = os.path.join(root, file)
                if fix_multiline_console_logs(filepath):
                    print(f"✓ Corregido: {filepath}")
                    fixed_count += 1
    
    # Procesar archivos en frontend/
    for root, dirs, files in os.walk('frontend'):
        for file in files:
            if file.endswith('.js'):
                filepath = os.path.join(root, file)
                if fix_multiline_console_logs(filepath):
                    print(f"✓ Corregido: {filepath}")
                    fixed_count += 1
    
    print(f"\n✅ Total archivos corregidos: {fixed_count}")
    
    if fixed_count > 0:
        print("\n💡 Archivos originales guardados con extensión .backup_consolelog")

if __name__ == "__main__":
    main()

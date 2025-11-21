#!/usr/bin/env python3
"""
Script para eliminar o comentar console.logs en producción
"""
import os
import re
import sys

def process_js_file(filepath, remove=False):
    """Procesa un archivo JS para eliminar o comentar console.logs"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Patrón para encontrar console.log, console.debug, console.info, etc.
    pattern = r'(console\.(log|debug|info|warn|error)\([^;]*\);?)'
    
    if remove:
        # Eliminar completamente
        content = re.sub(pattern, '', content)
    else:
        # Comentar
        content = re.sub(pattern, r'// \1', content)
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    """Procesar todos los archivos JS y HTML"""
    modified_count = 0
    
    # Directorios a procesar
    dirs_to_process = ['static', 'frontend']
    
    for dir_name in dirs_to_process:
        if not os.path.exists(dir_name):
            continue
            
        for root, dirs, files in os.walk(dir_name):
            # Ignorar node_modules y otros directorios de librerías
            dirs[:] = [d for d in dirs if d not in ['node_modules', 'vendor', 'libs']]
            
            for file in files:
                if file.endswith('.js') or file.endswith('.html'):
                    filepath = os.path.join(root, file)
                    
                    # No procesar archivos de librerías
                    if any(lib in filepath for lib in ['jquery', 'bootstrap', 'chart', 'popper']):
                        continue
                    
                    if process_js_file(filepath, remove=False):
                        print(f"✓ Procesado: {filepath}")
                        modified_count += 1
    
    print(f"\n✅ Total archivos modificados: {modified_count}")
    
    # Crear versión de desarrollo para restaurar
    print("\n💡 Para desarrollo, descomenta con: grep -r '// console.' --include='*.js' --include='*.html' | sed 's|// ||g'")

if __name__ == "__main__":
    main()

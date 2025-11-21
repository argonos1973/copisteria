#!/usr/bin/env python3
"""
Script específico para arreglar admin.js
"""
import re

def fix_admin_js():
    with open('static/admin.js', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Hacer backup
    with open('static/admin.js.backup_clean', 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 1. Corregir console.logs mal comentados con arrow functions
    # Ejemplo: detalles.forEach(d => // console.log(`   ${d}`));
    content = re.sub(
        r'(\w+)\.forEach\((\w+) => // console\.log\([^)]+\)\);',
        r'// \1.forEach(\2 => console.log(...));',
        content
    )
    
    # 2. Corregir comentarios de bloque mal cerrados `}); */`
    content = content.replace('}); */', '});')
    content = content.replace('); */', ');')
    
    # 3. Comentar console.logs multilínea correctamente
    # Buscar patrones como // console.log('texto', { ... });
    lines = content.split('\n')
    fixed_lines = []
    in_console = False
    brace_count = 0
    
    for i, line in enumerate(lines):
        if '// console.' in line and ('{' in line or line.strip().endswith(',')):
            # Inicio de un console.log multilínea
            in_console = True
            brace_count = line.count('{') - line.count('}')
            fixed_lines.append(line)
        elif in_console:
            # Estamos dentro de un console.log multilínea
            brace_count += line.count('{') - line.count('}')
            
            # Si la línea no está comentada, comentarla
            if line.strip() and not line.strip().startswith('//'):
                # Preservar indentación
                indent = len(line) - len(line.lstrip())
                line = ' ' * indent + '// ' + line.lstrip()
            
            fixed_lines.append(line)
            
            # Verificar si terminamos
            if ');' in line and brace_count <= 0:
                in_console = False
                brace_count = 0
        else:
            fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    
    # Guardar archivo corregido
    with open('static/admin.js', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ admin.js corregido")

if __name__ == "__main__":
    fix_admin_js()

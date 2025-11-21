#!/usr/bin/env python3
"""
Script para arreglar TODOS los console.logs mal comentados en archivos JS
"""
import re
import os

def fix_console_logs(filepath):
    """Arregla todos los console.logs mal comentados"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Patrón para encontrar console.logs mal comentados (multilínea)
        # Busca líneas que empiezan con // console. y tienen continuación sin comentar
        pattern = r'([ \t]*)// console\.(log|error|warn|debug|info)\([^)]*?\n([^/][^)]*?\n)*?[^)]*?\);'
        
        def comment_multiline(match):
            """Comenta todas las líneas de un console.log multilínea"""
            lines = match.group(0).split('\n')
            indent = match.group(1)
            result = []
            
            for i, line in enumerate(lines):
                if i == 0:
                    # Primera línea ya está comentada
                    result.append(line)
                else:
                    # Comentar las líneas siguientes
                    if line.strip() and not line.strip().startswith('//'):
                        # Mantener la indentación original
                        stripped = line.lstrip()
                        spaces = len(line) - len(stripped)
                        result.append(' ' * spaces + '// ' + stripped)
                    else:
                        result.append(line)
            
            return '\n'.join(result)
        
        # Aplicar correcciones
        content = re.sub(pattern, comment_multiline, content, flags=re.MULTILINE)
        
        # Caso especial: console.logs con objetos mal comentados
        # Buscar patrones como: // console.log('texto', { ... });
        pattern2 = r'([ \t]*)// console\.(log|error|warn|debug|info)\([^{]*\{[^}]*\n'
        
        # Encontrar todos los bloques mal comentados
        lines = content.split('\n')
        fixed_lines = []
        in_console_block = False
        console_indent = ''
        brace_count = 0
        paren_count = 0
        
        for line in lines:
            if '// console.' in line and ('{' in line or '({' in line):
                # Inicio de un console.log mal comentado
                in_console_block = True
                console_indent = len(line) - len(line.lstrip())
                brace_count = line.count('{') - line.count('}')
                paren_count = line.count('(') - line.count(')')
                fixed_lines.append(line)
            elif in_console_block:
                # Estamos dentro de un console.log multilínea
                brace_count += line.count('{') - line.count('}')
                paren_count += line.count('(') - line.count(')')
                
                if not line.strip().startswith('//'):
                    # Comentar esta línea
                    stripped = line.lstrip()
                    spaces = len(line) - len(stripped)
                    line = ' ' * spaces + '// ' + stripped
                
                fixed_lines.append(line)
                
                # Verificar si terminamos el bloque
                if brace_count <= 0 and paren_count <= 0 and ');' in line:
                    in_console_block = False
                    brace_count = 0
                    paren_count = 0
            else:
                fixed_lines.append(line)
        
        content = '\n'.join(fixed_lines)
        
        if content != original_content:
            # Hacer backup
            backup_path = f"{filepath}.backup_js"
            if not os.path.exists(backup_path):
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
            
            # Guardar archivo corregido
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
        return False
    
    except Exception as e:
        print(f"Error procesando {filepath}: {e}")
        return False

def main():
    """Procesar todos los archivos JS con errores"""
    print("🔧 Arreglando console.logs mal comentados en archivos JS...\n")
    
    # Lista de archivos con problemas conocidos
    problem_files = [
        'static/admin.js',
        'static/modal_theme.js',
        'static/branding.js',
        'static/imprimir-factura.js',
        'static/scripts.js',
        'static/consulta_proformas.js',
        'static/imprimir-ticket.js',
        'static/gestion_facturas.js'
    ]
    
    fixed_count = 0
    
    # Primero procesar archivos problemáticos conocidos
    for filepath in problem_files:
        if os.path.exists(filepath):
            if fix_console_logs(filepath):
                print(f"✓ Corregido: {filepath}")
                fixed_count += 1
    
    # Luego procesar todos los demás
    for root, dirs, files in os.walk('static'):
        for file in files:
            if file.endswith('.js'):
                filepath = os.path.join(root, file)
                if filepath not in problem_files:
                    if fix_console_logs(filepath):
                        print(f"✓ Corregido: {filepath}")
                        fixed_count += 1
    
    print(f"\n✅ Total archivos corregidos: {fixed_count}")
    
    if fixed_count > 0:
        print("\n💡 Archivos originales guardados con extensión .backup_js")

if __name__ == "__main__":
    main()

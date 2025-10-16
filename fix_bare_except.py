#!/usr/bin/env python3
"""
Script para reemplazar bare except statements por except Exception as e
Añade logging apropiado en cada caso
"""
import os
import re
from pathlib import Path

def fix_bare_except_in_file(file_path):
    """Arregla bare except en un archivo"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        lines = content.split('\n')
        modified = False
        new_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Detectar "except:" (bare except)
            if re.match(r'^(\s+)except:\s*$', line):
                indent = re.match(r'^(\s+)', line).group(1)
                
                # Reemplazar por except Exception as e:
                new_lines.append(f'{indent}except Exception as e:')
                
                # Buscar el siguiente bloque (normalmente hay un pass o logger.error)
                # Si no hay logging, lo agregamos
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    # Si la siguiente línea es solo pass, agregar logging
                    if 'pass' in next_line and 'logger' not in next_line:
                        new_lines.append(f'{indent}    logger.error(f"Error: {{e}}", exc_info=True)')
                        new_lines.append(next_line)
                        i += 1  # Skip next line
                    # Si no tiene logging, agregarlo
                    elif 'logger' not in next_line and 'print' not in next_line:
                        new_lines.append(f'{indent}    logger.error(f"Error: {{e}}", exc_info=True)')
                
                modified = True
            else:
                new_lines.append(line)
            
            i += 1
        
        if modified:
            new_content = '\n'.join(new_lines)
            
            # Verificar que el archivo tenga import de logger
            if 'from logger_config import' not in new_content and 'import logger_config' not in new_content:
                # Buscar la posición después de los imports
                import_lines = []
                code_lines = []
                in_imports = True
                
                for line in new_content.split('\n'):
                    if in_imports:
                        if line.startswith('import ') or line.startswith('from '):
                            import_lines.append(line)
                        elif line.strip() and not line.strip().startswith('#'):
                            # Fin de los imports
                            in_imports = False
                            # Agregar import de logger
                            if 'logger_config' not in '\n'.join(import_lines):
                                import_lines.append('from logger_config import get_logger')
                                import_lines.append('')
                                import_lines.append('logger = get_logger(__name__)')
                            code_lines.append(line)
                        else:
                            import_lines.append(line)
                    else:
                        code_lines.append(line)
                
                new_content = '\n'.join(import_lines + code_lines)
            
            # Escribir el archivo modificado
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return True, file_path
        
        return False, None
    
    except Exception as e:
        print(f"Error procesando {file_path}: {e}")
        return False, None

def main():
    """Procesa todos los archivos Python"""
    base_dir = '/var/www/html'
    
    # Archivos a procesar (los que tienen bare except)
    files_to_fix = [
        'analisis_cuentas.py',
        'api_scraping.py',
        'app.py',
        'batchFacturasVencidas.py',
        'captura_rapida.py',
        'conciliacion.py',
        'constantes.py',
        'dashboard_routes.py',
        'db_utils.py',
        'diagnostico_simple.py',
        'email_utils.py',
        'presupuesto.py',
        'productos.py',
        'verifactu.py'
    ]
    
    print("=" * 80)
    print("🔧 CORRIGIENDO BARE EXCEPT STATEMENTS")
    print("=" * 80)
    print()
    
    fixed_count = 0
    fixed_files = []
    
    for filename in files_to_fix:
        file_path = os.path.join(base_dir, filename)
        if os.path.exists(file_path):
            was_fixed, path = fix_bare_except_in_file(file_path)
            if was_fixed:
                fixed_count += 1
                fixed_files.append(filename)
                print(f"✅ {filename}")
            else:
                print(f"⏭️  {filename} (sin cambios)")
    
    print()
    print("=" * 80)
    print(f"✅ COMPLETADO: {fixed_count} archivos modificados")
    print("=" * 80)
    print()
    
    if fixed_files:
        print("Archivos modificados:")
        for f in fixed_files:
            print(f"  • {f}")
    
    return fixed_count

if __name__ == '__main__':
    count = main()
    exit(0 if count > 0 else 1)

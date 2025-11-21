#!/usr/bin/env python3
"""
Script para corregir f-strings mal cerrados causados por el script anterior
"""
import re
import os

def fix_fstring_errors(filepath):
    """Corrige f-strings mal cerrados en un archivo"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Patrones problemáticos comunes
        # Caso 1: f"f'texto')" -> f"texto"
        content = re.sub(r'f"f\'([^\']+)\'\)', r'f"\1"', content)
        
        # Caso 2: f'f"texto"' -> f"texto"
        content = re.sub(r"f'f\"([^\"]+)\"'", r'f"\1"', content)
        
        # Caso 3: f-strings dobles anidados f"f'...'
        content = re.sub(r'f"f\'([^\']+)\'', r'f"\1"', content)
        content = re.sub(r"f'f\"([^\"]+)\"", r'f"\1"', content)
        
        # Caso 4: f-strings con comillas sin cerrar al final
        content = re.sub(r'(f"[^"]+)\'\)$', r'\1")', content, flags=re.MULTILINE)
        content = re.sub(r"(f'[^']+)\"\)$", r"\1')", content, flags=re.MULTILINE)
        
        # Caso 5: logger con f-strings duplicados
        content = re.sub(r'logger\.\w+\(f"f\'([^\']+)\'\)', r'logger.\1(f"\2")', content)
        
        if content != original_content:
            # Hacer backup
            backup_path = f"{filepath}.backup_fstring"
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
    """Procesar archivos con errores de f-strings"""
    
    files_with_errors = [
        'analizar_factura_xsig.py',
        'batchFacturasRecibidasPDF.py', 
        'check_aigues_sept.py',
        'corregir_estados_facturas.py',
        'corregir_vencimiento_f250313.py',
        'validar_facturae.py',
        'verificar_caducidad_cloudflare.py',
        'verificar_limites_baremos.py',
        'verificar_sii.py',
        'facturas_vencidas_masivo.py',
        'importar_bd_mascotas.py',
        'importar_productos_csv.py',
        'migrar_db.py',
        'recolectar_tiempos.py',
        'scrapear_web.py'
    ]
    
    print("🔧 Reparando f-strings mal cerrados...\n")
    
    fixed_count = 0
    for filepath in files_with_errors:
        if os.path.exists(filepath):
            if fix_fstring_errors(filepath):
                print(f"✓ Reparado: {filepath}")
                fixed_count += 1
            else:
                print(f"⚠ Sin cambios: {filepath}")
    
    print(f"\n✅ Total archivos reparados: {fixed_count}")
    print("\n💡 Archivos originales guardados con extensión .backup_fstring")

if __name__ == "__main__":
    main()

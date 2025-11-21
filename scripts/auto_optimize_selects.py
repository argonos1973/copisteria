#!/usr/bin/env python3
"""
Script para optimizar automáticamente las consultas SELECT *
"""
import os
import re
import sqlite3

# Esquema de tablas y campos importantes
TABLE_SCHEMAS = {
    'facturas': ['id', 'numero', 'fecha', 'cliente_id', 'total', 'estado', 'iva', 'tipo_factura'],
    'tickets': ['id', 'numero', 'fecha', 'total', 'cliente_id', 'forma_pago', 'estado'],
    'productos': ['id', 'nombre', 'precio', 'codigo', 'stock', 'iva', 'categoria'],
    'clientes': ['id', 'nombre', 'email', 'telefono', 'nif', 'direccion'],
    'contactos': ['id', 'nombre', 'email', 'empresa', 'telefono', 'cargo'],
    'gastos': ['id', 'fecha', 'concepto', 'importe', 'categoria', 'proveedor_id'],
    'proveedores': ['id', 'nombre', 'nif', 'email', 'telefono', 'direccion'],
    'detalle_factura': ['id', 'factura_id', 'producto_id', 'cantidad', 'precio', 'descuento'],
    'detalle_ticket': ['id', 'ticket_id', 'producto_id', 'cantidad', 'precio', 'descuento'],
    'proforma': ['id', 'numero', 'fecha', 'cliente_id', 'total', 'estado'],
    'detalle_proforma': ['id', 'proforma_id', 'producto_id', 'cantidad', 'precio', 'descuento'],
    'usuarios': ['id', 'username', 'email', 'rol', 'activo', 'created_at'],
    'notificaciones': ['id', 'tipo', 'mensaje', 'timestamp', 'leida'],
    'conciliacion_gastos': ['id', 'gasto_id', 'estado', 'fecha_conciliacion', 'mensaje']
}

def optimize_select_star(filepath):
    """Optimiza los SELECT * en un archivo Python"""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Patrón para encontrar SELECT * FROM tabla
    pattern = r'(SELECT\s+\*\s+FROM\s+(\w+))'
    
    def replace_select(match):
        full_match = match.group(1)
        table_name = match.group(2).lower()
        
        # Si conocemos el esquema de la tabla, reemplazar con campos específicos
        if table_name in TABLE_SCHEMAS:
            fields = ', '.join(TABLE_SCHEMAS[table_name])
            return f"SELECT {fields} FROM {match.group(2)}"
        else:
            # Si no conocemos el esquema, dejar comentario
            return f"{full_match} -- TODO: Optimizar con campos específicos"
    
    # Reemplazar todas las ocurrencias
    content = re.sub(pattern, replace_select, content, flags=re.IGNORECASE)
    
    if content != original_content:
        # Hacer backup
        backup_path = f"{filepath}.backup_select"
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        
        # Guardar archivo optimizado
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Contar cambios
        changes = len(re.findall(pattern, original_content, re.IGNORECASE))
        return changes
    
    return 0

def main():
    """Procesar archivos Python para optimizar SELECT *"""
    print("🔍 Optimizando consultas SELECT * ...\n")
    
    total_optimized = 0
    files_modified = 0
    
    # Archivos prioritarios
    priority_files = [
        'app.py',
        'factura.py',
        'gastos.py',
        'tickets.py',
        'productos.py',
        'clientes.py',
        'proforma.py',
        'dashboard_routes.py'
    ]
    
    print("📌 Procesando archivos prioritarios...")
    for filename in priority_files:
        if os.path.exists(filename):
            changes = optimize_select_star(filename)
            if changes > 0:
                print(f"✓ {filename}: {changes} consultas optimizadas")
                total_optimized += changes
                files_modified += 1
    
    print("\n📁 Procesando otros archivos...")
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in ['venv', '.venv', '.git', '__pycache__']]
        
        for file in files:
            if file.endswith('.py') and file not in priority_files:
                filepath = os.path.join(root, file)
                changes = optimize_select_star(filepath)
                if changes > 0:
                    print(f"✓ {filepath}: {changes} consultas optimizadas")
                    total_optimized += changes
                    files_modified += 1
    
    print(f"\n✅ RESUMEN:")
    print(f"   Total SELECT * optimizados: {total_optimized}")
    print(f"   Archivos modificados: {files_modified}")
    print(f"\n💡 Archivos originales guardados con extensión .backup_select")
    print(f"   Revisar los TODO para tablas con esquema desconocido")

if __name__ == "__main__":
    main()

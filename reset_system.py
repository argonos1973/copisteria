
import sqlite3
import os
import shutil

# 1. Limpiar bases de datos
databases = [
    '/var/www/html/db/CHAPA/CHAPA.db',
    '/var/www/html/db/caca/caca.db',
    '/var/www/html/factura_e/CACA.db'
]

tables_to_clear = [
    'lineas_factura_proveedor',
    'historial_facturas_proveedores',
    'facturas_proveedores',
    'proveedores',
    'gastos'
]

print("=== LIMPIANDO BASES DE DATOS ===")
for db_path in databases:
    if not os.path.exists(db_path):
        continue
        
    print(f"Procesando: {db_path}")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA foreign_keys = OFF")
        
        for table in tables_to_clear:
            try:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                if cursor.fetchone():
                    cursor.execute(f"DELETE FROM {table}")
                    cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
                    print(f"  - Tabla vaciada: {table}")
            except Exception as e:
                print(f"  - Error en {table}: {e}")
                
        cursor.execute("PRAGMA foreign_keys = ON")
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

# 2. Limpiar archivos físicos
print("\n=== LIMPIANDO ARCHIVOS ===")
base_dir = '/var/www/html/facturas_proveedores'
if os.path.exists(base_dir):
    # Eliminar contenido pero mantener directorio
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        try:
            if os.path.isfile(item_path):
                os.unlink(item_path)
                print(f"Eliminado archivo: {item}")
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
                print(f"Eliminado directorio: {item}")
        except Exception as e:
            print(f"Error eliminando {item}: {e}")
else:
    os.makedirs(base_dir)
    print("Directorio creado")

print("\n=== PROCESO COMPLETADO ===")

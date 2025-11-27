import sqlite3
import sys
import os
import shutil
from datetime import datetime

def limpiar_bd(db_path):
    if not os.path.exists(db_path):
        print(f"Error: No existe la BD {db_path}")
        return

    # Backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}_pre_clean"
    try:
        shutil.copy2(db_path, backup_path)
        print(f"✅ Backup de seguridad creado: {backup_path}")
    except Exception as e:
        print(f"⚠️ Error creando backup: {e}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tablas = [
        'lineas_factura_proveedor',
        'historial_facturas_proveedores',
        'facturas_proveedores',
        'proveedores'
    ]

    try:
        print(f"🧹 Iniciando limpieza en {db_path}...")
        
        # Desactivar foreign keys temporalmente para evitar problemas de integridad al borrar
        cursor.execute("PRAGMA foreign_keys = OFF")

        for tabla in tablas:
            # Verificar si la tabla existe
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tabla}'")
            if cursor.fetchone():
                print(f"   - Vaciando tabla {tabla}...")
                cursor.execute(f"DELETE FROM {tabla}")
                # Resetear autoincrement
                cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{tabla}'")
            else:
                print(f"   ⚠️ Tabla {tabla} no encontrada, saltando.")
        
        conn.commit()
        print("✨ Tablas vaciadas correctamente.")
        
        # Reactivar foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Verificar conteos finales
        print("\n📊 Estado final:")
        for tabla in tablas:
            try:
                cursor.execute(f"SELECT Count(*) FROM {tabla}")
                count = cursor.fetchone()[0]
                print(f"   - {tabla}: {count} registros")
            except:
                pass

    except Exception as e:
        print(f"❌ Error crítico durante la limpieza: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 limpiar_proveedores_facturas.py <ruta_bd>")
        sys.exit(1)
    
    db_path = sys.argv[1]
    limpiar_bd(db_path)

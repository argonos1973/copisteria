#!/usr/bin/env python3
import os
import sqlite3

DB_ROOT = '/var/www/html/db'

def clean_all():
    print(f"ATENCIÓN: Iniciando ELIMINACIÓN TOTAL de documentos en {DB_ROOT}")
    
    if not os.path.exists(DB_ROOT):
        print(f"Directorio {DB_ROOT} no existe.")
        return

    for nombre_empresa in os.listdir(DB_ROOT):
        empresa_dir = os.path.join(DB_ROOT, nombre_empresa)
        if not os.path.isdir(empresa_dir): continue
            
        db_file = None
        for f in os.listdir(empresa_dir):
            if f.endswith('.db') and not f.endswith('plantilla.db'):
                db_file = os.path.join(empresa_dir, f)
                break
        
        if not db_file: continue
            
        print(f"[{nombre_empresa}] Limpiando {db_file}...")
        
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Desactivar foreign keys para permitir borrado masivo
            cursor.execute("PRAGMA foreign_keys = OFF")
            
            tables_to_clear = [
                'factura', 'detalle_factura',
                'tickets', 'detalle_tickets',
                'proforma', 'detalle_proforma',
                'presupuesto', 'detalle_presupuesto',
                'conciliacion_gastos', 'conciliacion_documentos',
                'registro_facturacion',
                'notificaciones'
            ]
            
            for table in tables_to_clear:
                try:
                    # Verificar si la tabla existe antes de borrar
                    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                    if cursor.fetchone():
                        cursor.execute(f"DELETE FROM {table}")
                        # print(f"  - Tabla {table} vaciada.")
                except Exception as e:
                    print(f"  - Error vaciando {table}: {e}")

            # Resetear numeradores
            try:
                # Verificar si tabla numerador existe
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='numerador'")
                if cursor.fetchone():
                    cursor.execute("UPDATE numerador SET numerador = 0")
                    print("  - Numeradores reseteados a 0.")
            except Exception as e:
                print(f"  - Error reseteando numeradores: {e}")

            # Resetear secuencias autoincrementales (IDs volverán a empezar en 1)
            try:
                for table in tables_to_clear:
                     cursor.execute("DELETE FROM sqlite_sequence WHERE name=?", (table,))
                print("  - Secuencias de IDs reseteadas.")
            except Exception as e:
                print(f"  - Error reseteando secuencias: {e}")
            
            conn.commit()
            conn.close()
            print("  ✓ Limpieza completada.")
            
        except Exception as e:
            print(f"  ERROR procesando {db_file}: {e}")

if __name__ == '__main__':
    clean_all()

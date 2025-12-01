import sqlite3
import sys
from datetime import datetime

DB_PATH = '/var/www/html/db/caca/caca.db'

def limpiar_duplicados():
    print(f"🔍 Analizando duplicados en {DB_PATH}...")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # 1. Identificar duplicados (misma fecha, importe y proveedor)
        # Agrupamos por fecha, importe y razon_social para encontrar los repetidos
        query = """
            SELECT 
                fecha_operacion_iso, 
                importe_eur, 
                razon_social,
                COUNT(*) as cantidad,
                GROUP_CONCAT(id) as ids_grupo
            FROM gastos 
            WHERE razon_social IS NOT NULL AND razon_social != ''
            GROUP BY fecha_operacion_iso, importe_eur, razon_social
            HAVING COUNT(*) > 1
            ORDER BY cantidad DESC
        """
        
        cursor.execute(query)
        grupos_duplicados = cursor.fetchall()
        
        total_eliminados = 0
        
        if not grupos_duplicados:
            print("✅ No se encontraron duplicados.")
            return

        print(f"⚠️ Se encontraron {len(grupos_duplicados)} grupos de duplicados.")
        
        for grupo in grupos_duplicados:
            fecha = grupo['fecha_operacion_iso']
            importe = grupo['importe_eur']
            proveedor = grupo['razon_social']
            ids = grupo['ids_grupo'].split(',')
            
            print(f"\n--- Grupo duplicado: {proveedor} | {fecha} | {importe}€ ---")
            print(f"IDs encontrados: {ids}")
            
            # Obtener detalles de cada gasto para decidir cuál conservar
            # Preferimos conservar:
            # 1. El que tenga concepto más descriptivo (más largo)
            # 2. El más antiguo (menor ID)
            cursor.execute(f"SELECT id, concepto FROM gastos WHERE id IN ({','.join(ids)})")
            detalles = cursor.fetchall()
            
            # Ordenar por longitud de concepto DESC (para quedarnos con el más detallado)
            # Si longitud igual, por ID ASC
            detalles.sort(key=lambda x: (-len(x['concepto'] or ''), x['id']))
            
            conservar = detalles[0]
            eliminar = detalles[1:]
            
            print(f"✅ CONSERVAR ID {conservar['id']}: {conservar['concepto']}")
            
            ids_a_eliminar = [str(d['id']) for d in eliminar]
            
            if ids_a_eliminar:
                placeholders = ','.join('?' * len(ids_a_eliminar))
                cursor.execute(f"DELETE FROM gastos WHERE id IN ({placeholders})", ids_a_eliminar)
                eliminados = cursor.rowcount
                print(f"🗑️ Eliminados IDs: {', '.join(ids_a_eliminar)}")
                total_eliminados += eliminados
        
        conn.commit()
        print(f"\n✨ Limpieza completada. Se eliminaron {total_eliminados} registros duplicados.")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    limpiar_duplicados()

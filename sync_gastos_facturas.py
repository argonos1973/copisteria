
import sqlite3
import os
from datetime import datetime

# Configuración
DB_PATHS = [
    '/var/www/html/db/CHAPA/CHAPA.db',
    '/var/www/html/db/caca/caca.db'
]

def sync_gastos(db_path):
    if not os.path.exists(db_path):
        print(f"⚠️  Base de datos no encontrada: {db_path}")
        return

    print(f"\n📂 Procesando: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. Verificar si existen las tablas necesarias
        tables_needed = ['gastos', 'facturas_proveedores', 'proveedores']
        for table in tables_needed:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not cursor.fetchone():
                print(f"❌ Error: Tabla '{table}' no existe en {db_path}. Saltando...")
                conn.close()
                return

        # 2. Vaciar tabla de gastos
        print("🗑️  Vaciando tabla de gastos...")
        cursor.execute("DELETE FROM gastos")
        # Resetear autoincrement
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='gastos'")
        print("✓ Tabla gastos vaciada.")

        # 3. Obtener facturas recibidas
        print("📥 Leyendo facturas recibidas...")
        cursor.execute("""
            SELECT 
                f.id,
                f.fecha_emision,
                f.concepto,
                f.total,
                f.estado,
                p.nombre as proveedor_nombre
            FROM facturas_proveedores f
            LEFT JOIN proveedores p ON f.proveedor_id = p.id
        """)
        
        facturas = cursor.fetchall()
        count = 0
        
        # 4. Insertar en gastos
        for fac in facturas:
            # Preparar datos
            fecha = fac['fecha_emision']
            # Si no hay concepto, usar "Factura Proveedor [Nombre]"
            concepto = fac['concepto']
            if not concepto:
                concepto = f"Factura {fac['proveedor_nombre'] or 'Desconocido'}"
            
            importe = fac['total']
            proveedor = fac['proveedor_nombre']
            
            # Determinar si está pagado (si no está pagada, ¿debería ir a gastos? 
            # El usuario pidió "rellenar a partir de facturas recibidas", generalmente el gasto se devenga con la factura.
            # Sin embargo, esta tabla parece de movimientos bancarios (tiene saldo, fecha_valor).
            # Si insertamos aquí, estamos simulando el movimiento bancario.
            
            # Estructura detectada:
            # 0|id|INTEGER
            # 1|fecha_operacion|TEXT
            # 2|fecha_valor|TEXT
            # 3|concepto|TEXT
            # 4|importe_eur|REAL
            # 5|saldo|REAL
            # 6|ejercicio|INTEGER
            # 7|TS|TEXT
            # 8|puntual|INTEGER
            # 9|fecha_operacion_iso|TEXT
            # 10|fecha_valor_iso|TEXT

            # Calcular ejercicio
            try:
                dt = datetime.strptime(fecha, '%Y-%m-%d')
                ejercicio = dt.year
                # Formato fecha dd/mm/yyyy para fecha_operacion (formato español habitual en bancos)
                fecha_es = dt.strftime('%d/%m/%Y')
            except:
                ejercicio = datetime.now().year
                fecha_es = fecha

            # Importe en negativo para gastos
            importe_neg = -abs(float(importe))

            # Timestamp actual
            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            cursor.execute("""
                INSERT INTO gastos (
                    fecha_operacion, fecha_valor, concepto, importe_eur, saldo, 
                    ejercicio, TS, puntual, fecha_operacion_iso, fecha_valor_iso
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fecha_es,           # fecha_operacion (dd/mm/yyyy)
                fecha_es,           # fecha_valor (igual)
                concepto,           # concepto
                importe_neg,        # importe_eur (negativo)
                0,                  # saldo (no podemos calcularlo fácilmente, ponemos 0 o NULL)
                ejercicio,          # ejercicio
                ts,                 # TS
                0,                  # puntual
                fecha,              # fecha_operacion_iso (YYYY-MM-DD)
                fecha,              # fecha_valor_iso (YYYY-MM-DD)
            ))
            
            count += 1
            
        conn.commit()
        print(f"✅ Sincronización completada: {count} gastos generados desde facturas.")
        conn.close()

    except Exception as e:
        print(f"❌ Error procesando {db_path}: {e}")

if __name__ == "__main__":
    print("=== SINCRONIZACIÓN DE GASTOS DESDE FACTURAS RECIBIDAS ===")
    for db in DB_PATHS:
        sync_gastos(db)
    print("\n=== FIN DEL PROCESO ===")

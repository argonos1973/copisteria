
import sqlite3
import os
import sys
from datetime import datetime

# Añadir directorio actual al path para importar módulos
sys.path.append('/var/www/html')

from db_utils import get_db_connection

def fix_numerador():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        ejercicio = datetime.now().year
        ejercicio_corto = ejercicio % 100
        prefijo = f"T{ejercicio_corto:02}"
        
        print(f"Buscando tickets con prefijo {prefijo}...")

        # Obtener último ticket real
        cursor.execute(f"SELECT numero FROM tickets WHERE numero LIKE '{prefijo}%' ORDER BY numero DESC LIMIT 1")
        ultimo_ticket = cursor.fetchone()
        
        if not ultimo_ticket:
            print("No se encontraron tickets.")
            return

        print(f"Último ticket encontrado: {ultimo_ticket[0]}")
        
        try:
            # Extraer los últimos 4 dígitos
            num_part = ultimo_ticket[0][-4:]
            ultimo_num_real = int(num_part)
        except ValueError:
            print("No se pudo parsear el número del ticket.")
            return
            
        # Obtener numerador actual en configuración
        cursor.execute("SELECT numerador FROM numerador WHERE tipo='T' AND ejercicio=?", (ejercicio,))
        res = cursor.fetchone()
        
        if not res:
            print("No se encontró registro en tabla numerador.")
            return
            
        numerador_db = res[0]
        print(f"Valor en tabla numerador: {numerador_db}")
        
        # Lógica de corrección:
        # El numerador debe reflejar el ÚLTIMO número usado.
        # Si numerador_db < ultimo_num_real, está desfasado y causará colisiones (si se usa lógica 'actualizar primero') o duplicados (si se usa lógica 'leer primero').
        
        if numerador_db < ultimo_num_real:
            print(f"⚠️ DESFASE DETECTADO. Actualizando numerador de {numerador_db} a {ultimo_num_real}...")
            cursor.execute("UPDATE numerador SET numerador = ? WHERE tipo='T' AND ejercicio=?", (ultimo_num_real, ejercicio))
            conn.commit()
            print("✅ Numerador corregido.")
        else:
            print("✅ El numerador parece correcto (es igual o mayor al último ticket).")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    fix_numerador()

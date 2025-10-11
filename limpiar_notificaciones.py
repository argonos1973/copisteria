#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/var/www/html/db/aleph70.db')
cursor = conn.cursor()
cursor.execute('DELETE FROM notificaciones')
conn.commit()
print(f'✅ Eliminadas {cursor.rowcount} notificaciones')
conn.close()

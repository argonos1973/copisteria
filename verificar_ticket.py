#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/var/www/html/db/aleph70.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Buscar ticket
cursor.execute('''
    SELECT t.id, t.numero, t.total, t.importe_bruto, t.importe_impuestos
    FROM tickets t 
    WHERE t.numero = 'T256228'
''')
ticket = cursor.fetchone()

if ticket:
    print(f'Ticket: {ticket["numero"]}')
    print(f'Total BD: {ticket["total"]}€')
    print(f'Bruto BD: {ticket["importe_bruto"]}€')
    print(f'IVA BD: {ticket["importe_impuestos"]}€')
    print()
    
    # Detalles
    cursor.execute('''
        SELECT concepto, cantidad, precio, impuestos, total
        FROM detalle_tickets
        WHERE id_ticket = ?
    ''', (ticket['id'],))
    
    print('Detalles:')
    total_calculado = 0
    bruto_total = 0
    iva_total = 0
    
    for det in cursor.fetchall():
        print(f'\n  Concepto: {det["concepto"]}')
        print(f'  Cantidad: {det["cantidad"]}')
        print(f'  Precio: {det["precio"]}€')
        print(f'  IVA: {det["impuestos"]}%')
        print(f'  Total BD: {det["total"]}€')
        
        # Calcular correcto
        bruto = det['cantidad'] * det['precio']
        iva = bruto * (det['impuestos'] / 100)
        total_correcto = bruto + iva
        
        print(f'  Cálculo correcto:')
        print(f'    Bruto: {det["cantidad"]} x {det["precio"]} = {bruto:.4f}€')
        print(f'    IVA: {bruto:.4f} x {det["impuestos"]}% = {iva:.4f}€')
        print(f'    Total: {bruto:.4f} + {iva:.4f} = {total_correcto:.2f}€')
        
        total_calculado += total_correcto
        bruto_total += bruto
        iva_total += iva
    
    print(f'\n=== RESUMEN ===')
    print(f'Bruto total: {bruto_total:.2f}€')
    print(f'IVA total: {iva_total:.2f}€')
    print(f'Total calculado: {total_calculado:.2f}€')
    print(f'Total en BD: {ticket["total"]}€')
    print(f'Diferencia: {abs(total_calculado - ticket["total"]):.2f}€')
else:
    print('Ticket T256228 no encontrado')

conn.close()

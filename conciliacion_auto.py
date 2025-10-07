#!/usr/bin/env python3
# conciliacion_auto.py
# Script para ejecutar conciliación automática desde cron o manualmente
# Se ejecuta después del scraping bancario para conciliar nuevos gastos

import sqlite3
import sys
from datetime import datetime, timedelta
from constantes import DB_NAME

def get_db_connection():
    """Obtener conexión a la base de datos"""
    conn = sqlite3.connect(DB_NAME, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def buscar_coincidencias_automaticas(gasto):
    """
    Buscar coincidencias automáticas para un gasto bancario
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    gasto_id = gasto['id']
    importe = abs(gasto['importe_eur'])
    fecha_gasto = datetime.strptime(gasto['fecha_operacion'], '%Y-%m-%d')
    fecha_inicio = (fecha_gasto - timedelta(days=7)).strftime('%Y-%m-%d')
    fecha_fin = (fecha_gasto + timedelta(days=7)).strftime('%Y-%m-%d')
    
    tolerancia = 0.02
    
    coincidencias = []
    
    # Buscar en facturas cobradas
    cursor.execute('''
        SELECT 
            'factura' as tipo,
            id,
            numero,
            fecha,
            total,
            estado
        FROM factura
        WHERE estado = 'C'
        AND fecha BETWEEN ? AND ?
        AND ABS(total - ?) <= ?
        AND id NOT IN (
            SELECT documento_id FROM conciliacion_gastos 
            WHERE tipo_documento = 'factura' AND estado = 'conciliado'
        )
    ''', (fecha_inicio, fecha_fin, importe, tolerancia))
    
    for row in cursor.fetchall():
        score = calcular_score(gasto, dict(row))
        coincidencias.append({
            'tipo': 'factura',
            'id': row['id'],
            'numero': row['numero'],
            'fecha': row['fecha'],
            'importe': row['total'],
            'diferencia': abs(row['total'] - importe),
            'score': score
        })
    
    # Buscar en tickets cobrados
    cursor.execute('''
        SELECT 
            'ticket' as tipo,
            id,
            numero,
            fecha,
            total,
            estado
        FROM tickets
        WHERE estado = 'C'
        AND fecha BETWEEN ? AND ?
        AND ABS(total - ?) <= ?
        AND id NOT IN (
            SELECT documento_id FROM conciliacion_gastos 
            WHERE tipo_documento = 'ticket' AND estado = 'conciliado'
        )
    ''', (fecha_inicio, fecha_fin, importe, tolerancia))
    
    for row in cursor.fetchall():
        score = calcular_score(gasto, dict(row))
        coincidencias.append({
            'tipo': 'ticket',
            'id': row['id'],
            'numero': row['numero'],
            'fecha': row['fecha'],
            'importe': row['total'],
            'diferencia': abs(row['total'] - importe),
            'score': score
        })
    
    conn.close()
    
    # Ordenar por score
    coincidencias.sort(key=lambda x: x['score'], reverse=True)
    
    return coincidencias

def calcular_score(gasto, documento):
    """Calcular score de coincidencia (0-100)"""
    score = 0
    
    # Score por diferencia de importe
    diferencia_importe = abs(abs(gasto['importe_eur']) - documento['total'])
    if diferencia_importe == 0:
        score += 50
    elif diferencia_importe <= 0.01:
        score += 45
    elif diferencia_importe <= 0.02:
        score += 40
    else:
        score += max(0, 50 - (diferencia_importe * 100))
    
    # Score por diferencia de fecha
    fecha_gasto = datetime.strptime(gasto['fecha_operacion'], '%Y-%m-%d')
    fecha_doc = datetime.strptime(documento['fecha'], '%Y-%m-%d')
    diferencia_dias = abs((fecha_gasto - fecha_doc).days)
    
    if diferencia_dias == 0:
        score += 30
    elif diferencia_dias <= 1:
        score += 25
    elif diferencia_dias <= 3:
        score += 20
    elif diferencia_dias <= 7:
        score += 10
    
    # Score por exactitud
    if diferencia_importe == 0:
        score += 20
    elif diferencia_importe <= 0.01:
        score += 15
    
    return min(100, score)

def conciliar_automaticamente(gasto_id, tipo_documento, documento_id):
    """Crear una conciliación"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Obtener datos del gasto
        cursor.execute('SELECT * FROM gastos WHERE id = ?', (gasto_id,))
        gasto = dict(cursor.fetchone())
        
        # Obtener datos del documento
        if tipo_documento == 'factura':
            cursor.execute('SELECT * FROM factura WHERE id = ?', (documento_id,))
        elif tipo_documento == 'ticket':
            cursor.execute('SELECT * FROM tickets WHERE id = ?', (documento_id,))
        else:
            return False, f'Tipo de documento no válido: {tipo_documento}'
        
        documento = dict(cursor.fetchone())
        
        # Calcular diferencia
        diferencia = abs(gasto['importe_eur']) - documento['total']
        
        # Insertar conciliación
        cursor.execute('''
            INSERT INTO conciliacion_gastos 
            (gasto_id, tipo_documento, documento_id, fecha_conciliacion, 
             importe_gasto, importe_documento, diferencia, estado, metodo)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'conciliado', 'automatico')
        ''', (
            gasto_id,
            tipo_documento,
            documento_id,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            gasto['importe_eur'],
            documento['total'],
            diferencia
        ))
        
        conn.commit()
        return True, 'OK'
        
    except sqlite3.IntegrityError:
        return False, 'Ya existe'
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()

def ejecutar_conciliacion_automatica(umbral_score=90, verbose=True):
    """
    Ejecutar proceso de conciliación automática
    """
    if verbose:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iniciando conciliación automática...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obtener gastos pendientes
    cursor.execute('''
        SELECT * FROM gastos
        WHERE id NOT IN (
            SELECT gasto_id FROM conciliacion_gastos WHERE estado = 'conciliado'
        )
        AND importe_eur > 0
        ORDER BY fecha_operacion DESC
    ''')
    
    gastos_pendientes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    if verbose:
        print(f"Gastos pendientes encontrados: {len(gastos_pendientes)}")
    
    procesados = 0
    conciliados = 0
    
    for gasto in gastos_pendientes:
        procesados += 1
        
        # Buscar coincidencias
        coincidencias = buscar_coincidencias_automaticas(gasto)
        
        if coincidencias and coincidencias[0]['score'] >= umbral_score:
            mejor = coincidencias[0]
            success, message = conciliar_automaticamente(
                gasto['id'],
                mejor['tipo'],
                mejor['id']
            )
            
            if success:
                conciliados += 1
                if verbose:
                    print(f"  ✓ Gasto {gasto['id']} ({gasto['fecha_operacion']}, {gasto['importe_eur']}€) → {mejor['tipo'].upper()} {mejor['numero']} (score: {mejor['score']}%)")
            else:
                if verbose and message != 'Ya existe':
                    print(f"  ✗ Error en gasto {gasto['id']}: {message}")
    
    if verbose:
        print(f"\nResumen:")
        print(f"  - Procesados: {procesados}")
        print(f"  - Conciliados: {conciliados}")
        print(f"  - Pendientes: {procesados - conciliados}")
    
    return {
        'procesados': procesados,
        'conciliados': conciliados,
        'pendientes': procesados - conciliados
    }

if __name__ == '__main__':
    # Permitir pasar umbral como argumento
    umbral = 90
    if len(sys.argv) > 1:
        try:
            umbral = int(sys.argv[1])
        except ValueError:
            print(f"Umbral inválido: {sys.argv[1]}. Usando 90 por defecto.")
    
    try:
        resultado = ejecutar_conciliacion_automatica(umbral_score=umbral, verbose=True)
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

#!/usr/bin/env python3
"""
Script para encontrar y eliminar gastos duplicados en la base de datos
"""
import sqlite3
import re
from collections import defaultdict
from logger_config import get_logger

# Inicializar logger
logger = get_logger(__name__)

DB_PATH = '/var/www/html/db/aleph70.db'

def normalizar_concepto(concepto):
    """Normaliza un concepto para detectar duplicados"""
    # Eliminar números de recibo, referencias, códigos
    concepto = re.sub(r'N[ºo°]\s*Recibo[:\s]+[\d\s]+', '', concepto, flags=re.IGNORECASE)
    concepto = re.sub(r'Nº\s*[\d\s]+', '', concepto)
    concepto = re.sub(r'Ref[:\.\s]+.*?Mandato[:\s]+[\w\d\-]+', '', concepto, flags=re.IGNORECASE)
    concepto = re.sub(r'Ref[:\.\s]+[\w\d\-]+', '', concepto, flags=re.IGNORECASE)
    concepto = re.sub(r'Mandato[:\s]+[\w\d\-]+', '', concepto, flags=re.IGNORECASE)
    concepto = re.sub(r'Factura[:\s]+[\d\-\/]+', '', concepto, flags=re.IGNORECASE)
    concepto = re.sub(r'Contracte?\s+(Num\.?|N[ºo°])?\s*[\d\s]*', '', concepto, flags=re.IGNORECASE)
    concepto = re.sub(r'\d{2}\/\d{2}\/\d{4}', '', concepto)
    concepto = re.sub(r'\d{4}-\d{2}-\d{2}', '', concepto)
    concepto = re.sub(r'\bBb[a-z]{5}\b', '', concepto, flags=re.IGNORECASE)
    
    # Normalizar "Concepto:" variaciones
    concepto = re.sub(r'Concepto:\s*', '', concepto, flags=re.IGNORECASE)
    concepto = re.sub(r'\bConcepto\s+', '', concepto, flags=re.IGNORECASE)
    
    # Limpiar espacios múltiples
    concepto = re.sub(r'\s+', ' ', concepto).strip()
    
    return concepto.lower()

def encontrar_duplicados():
    """Encuentra gastos duplicados por fecha, importe y concepto normalizado"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Obtener todos los gastos
    cursor.execute('''
        SELECT id, concepto, fecha_operacion, importe_eur 
        FROM gastos 
        WHERE importe_eur < 0
        ORDER BY id
    ''')
    
    # Agrupar por clave única: fecha + importe + concepto_normalizado
    grupos = defaultdict(list)
    
    for row in cursor.fetchall():
        concepto_norm = normalizar_concepto(row['concepto'])
        clave = (row['fecha_operacion'], row['importe_eur'], concepto_norm)
        grupos[clave].append(dict(row))
    
    # Encontrar grupos con duplicados (más de 1 registro)
    duplicados = []
    for clave, registros in grupos.items():
        if len(registros) > 1:
            duplicados.append({
                'clave': clave,
                'registros': registros,
                'cantidad': len(registros)
            })
    
    conn.close()
    return duplicados

def eliminar_duplicados(duplicados, ejecutar=False):
    """Elimina duplicados dejando solo el registro con ID más bajo"""
    if not duplicados:
        logger.info("✅ No se encontraron duplicados")
        return
    
    logger.info(f"\n{'='*80}")
    logger.info(f"ENCONTRADOS {len(duplicados)} GRUPOS DE DUPLICADOS")
    logger.info(f"{'='*80}\n")
    
    ids_a_eliminar = []
    total_registros_duplicados = 0
    
    for i, dup in enumerate(duplicados, 1):
        registros = dup['registros']
        # Ordenar por ID para mantener el más antiguo
        registros_ordenados = sorted(registros, key=lambda x: x['id'])
        mantener = registros_ordenados[0]
        eliminar = registros_ordenados[1:]
        
        logger.info(f"Grupo {i}: {dup['cantidad']} registros duplicados")
        logger.info(f"  Fecha: {dup['clave'][0]}")
        logger.info(f"  Importe: {dup['clave'][1]}€")
        logger.info(f"  ✅ MANTENER ID {mantener['id']}: {mantener['concepto'][:70]}")
        
        for reg in eliminar:
            logger.info(f"  ❌ ELIMINAR ID {reg['id']}: {reg['concepto'][:70]}")
            ids_a_eliminar.append(reg['id'])
            total_registros_duplicados += 1
        
        logger.info(f")
    
    logger.info(f"{'='*80}")
    logger.info(f"RESUMEN:")
    logger.info(f"  - Grupos de duplicados: {len(duplicados)}")
    logger.info(f"  - Registros a MANTENER: {len(duplicados)}")
    logger.info(f"  - Registros a ELIMINAR: {total_registros_duplicados}")
    logger.info(f"{'='*80}\n")
    
    if ejecutar:
        if not ids_a_eliminar:
            logger.info("✅ No hay registros para eliminar")
            return
        
        logger.info(f"🗑️  ELIMINANDO {len(ids_a_eliminar)} REGISTROS DUPLICADOS...")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Eliminar en lotes
        placeholders = ' '.join('?' * len(ids_a_eliminar"))
        cursor.execute(f'DELETE FROM gastos WHERE id IN ({placeholders})', ids_a_eliminar)
        
        conn.commit()
        eliminados = cursor.rowcount
        conn.close()
        
        logger.info(f"✅ {eliminados} registros duplicados eliminados correctamente")
        logger.info(f"\nIDs eliminados: {ids_a_eliminar}")
    else:
        logger.info("ℹ️  MODO SIMULACIÓN - No se eliminó nada")
        logger.info("   Ejecuta con --ejecutar para eliminar realmente")

def main():
    import sys
    
    ejecutar = '--ejecutar' in sys.argv or '-e' in sys.argv
    
    logger.info(f""\n" + "="*80)
    logger.info("BUSCADOR Y ELIMINADOR DE GASTOS DUPLICADOS")
    print("="*80)
    logger.info(f"Base de datos: {DB_PATH}")
    logger.info(f"Modo: {'EJECUCIÓN' if ejecutar else 'SIMULACIÓN'}")
    print("="*80 + "\n")
    
    logger.info("🔍 Buscando duplicados...")
    duplicados = encontrar_duplicados()
    
    eliminar_duplicados(duplicados ejecutar=ejecutar")
    
    logger.info("\n✅ Proceso completado\n")

if __name__ == '__main__':
    main()

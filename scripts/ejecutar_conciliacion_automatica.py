#!/usr/bin/env python3
"""
Script para ejecutar conciliación automática desde cron
Procesa todos los gastos pendientes y los concilia automáticamente
"""

import sys
import os
import sqlite3
import requests
from datetime import datetime

# Añadir directorio padre al path para importar constantes
sys.path.insert(0, '/var/www/html')
from constantes import DB_NAME, IP_SERVIDOR

# Configuración
API_URL = f"http://{IP_SERVIDOR}:5001"
LOG_FILE = "/var/www/html/logs/conciliacion_cron.log"

def log(mensaje):
    """Escribir mensaje en log con timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {mensaje}"
    print(log_msg)
    
    # Crear directorio de logs si no existe
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(log_msg + '\n')
    except Exception as e:
        print(f"Error escribiendo log: {e}")

def obtener_gastos_pendientes():
    """Obtener gastos pendientes de conciliación"""
    try:
        response = requests.get(f"{API_URL}/api/conciliacion/gastos-pendientes", timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data.get('gastos', [])
        return []
    except Exception as e:
        log(f"❌ Error obteniendo gastos pendientes: {e}")
        return []

def buscar_coincidencias(gasto_id):
    """Buscar coincidencias para un gasto"""
    try:
        response = requests.get(f"{API_URL}/api/conciliacion/buscar/{gasto_id}", timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data.get('coincidencias', [])
        return []
    except Exception as e:
        log(f"❌ Error buscando coincidencias para gasto {gasto_id}: {e}")
        return []

def conciliar(gasto_id, tipo_documento, documento_id):
    """Conciliar un gasto con un documento"""
    try:
        payload = {
            'gasto_id': gasto_id,
            'tipo_documento': tipo_documento,
            'documento_id': documento_id,
            'metodo': 'automatico_cron'
        }
        response = requests.post(f"{API_URL}/api/conciliacion/conciliar", json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data.get('success', False)
        return False
    except Exception as e:
        log(f"❌ Error conciliando gasto {gasto_id}: {e}")
        return False

def encontrar_mejor_combinacion(documentos, objetivo, tolerancia=1.0):
    """
    Algoritmo de varita mágica para encontrar la mejor combinación de documentos
    que sumen el importe objetivo
    """
    if not documentos:
        return []
    
    # Ordenar por score descendente
    documentos_ordenados = sorted(documentos, key=lambda x: x.get('score', 0), reverse=True)
    
    # Intentar encontrar combinación exacta o muy cercana
    mejor_combinacion = []
    mejor_diferencia = float('inf')
    
    # Probar combinaciones simples primero (1, 2, 3 documentos)
    for i in range(len(documentos_ordenados)):
        # Combinación de 1 documento
        doc = documentos_ordenados[i]
        diferencia = abs(objetivo - doc['importe'])
        if diferencia < mejor_diferencia:
            mejor_diferencia = diferencia
            mejor_combinacion = [doc]
            if diferencia < 0.01:  # Coincidencia exacta
                return mejor_combinacion
        
        # Combinación de 2 documentos
        for j in range(i + 1, len(documentos_ordenados)):
            total = doc['importe'] + documentos_ordenados[j]['importe']
            diferencia = abs(objetivo - total)
            if diferencia < mejor_diferencia:
                mejor_diferencia = diferencia
                mejor_combinacion = [doc, documentos_ordenados[j]]
                if diferencia < 0.01:
                    return mejor_combinacion
        
        # Combinación de 3 documentos
        for j in range(i + 1, len(documentos_ordenados)):
            for k in range(j + 1, len(documentos_ordenados)):
                total = doc['importe'] + documentos_ordenados[j]['importe'] + documentos_ordenados[k]['importe']
                diferencia = abs(objetivo - total)
                if diferencia < mejor_diferencia:
                    mejor_diferencia = diferencia
                    mejor_combinacion = [doc, documentos_ordenados[j], documentos_ordenados[k]]
                    if diferencia < 0.01:
                        return mejor_combinacion
    
    # Retornar mejor combinación solo si está dentro de la tolerancia
    if mejor_diferencia <= tolerancia:
        return mejor_combinacion
    
    return []

def procesar_conciliacion_automatica():
    """Proceso principal de conciliación automática"""
    log("=" * 80)
    log("🚀 INICIANDO CONCILIACIÓN AUTOMÁTICA")
    log("=" * 80)
    
    total_conciliados = 0
    total_procesados = 0
    
    # 1. Obtener gastos pendientes
    gastos = obtener_gastos_pendientes()
    log(f"📋 Gastos pendientes encontrados: {len(gastos)}")
    
    if not gastos:
        log("ℹ️ No hay gastos pendientes para conciliar")
        return
    
    # 2. Filtrar solo transferencias e ingresos con importe positivo
    gastos_procesar = [g for g in gastos if g.get('importe_eur', 0) > 0]
    log(f"📊 Gastos a procesar (importe > 0): {len(gastos_procesar)}")
    
    # 3. Procesar cada gasto
    for gasto in gastos_procesar:
        total_procesados += 1
        gasto_id = gasto['id']
        importe = gasto['importe_eur']
        concepto = gasto.get('concepto', '')[:60]
        
        log(f"\n--- Procesando gasto {gasto_id} ({importe}€) ---")
        log(f"    Concepto: {concepto}...")
        
        # Buscar coincidencias
        coincidencias = buscar_coincidencias(gasto_id)
        
        if not coincidencias:
            log(f"    ⊗ Sin coincidencias")
            continue
        
        log(f"    ✓ {len(coincidencias)} coincidencias encontradas")
        
        # Buscar coincidencia exacta (diferencia < 0.01€)
        coincidencia_exacta = next((c for c in coincidencias if abs(c.get('diferencia', 999)) < 0.01), None)
        
        if coincidencia_exacta:
            # Conciliar con coincidencia exacta
            tipo = coincidencia_exacta['tipo']
            doc_id = coincidencia_exacta['id']
            numero = coincidencia_exacta.get('numero', 'N/A')
            
            if conciliar(gasto_id, tipo, doc_id):
                total_conciliados += 1
                log(f"    ✅ CONCILIADO con {tipo} {numero} (diferencia: 0.00€)")
            else:
                log(f"    ❌ Error al conciliar con {tipo} {numero}")
        else:
            # Intentar encontrar combinación de documentos
            mejor_combinacion = encontrar_mejor_combinacion(coincidencias, importe, tolerancia=1.0)
            
            if mejor_combinacion:
                diferencia_total = abs(importe - sum(d['importe'] for d in mejor_combinacion))
                
                if diferencia_total < 1.0:
                    # Conciliar con cada documento de la combinación
                    exito = True
                    for doc in mejor_combinacion:
                        if not conciliar(gasto_id, doc['tipo'], doc['id']):
                            exito = False
                            break
                    
                    if exito:
                        total_conciliados += 1
                        docs_str = ', '.join([f"{d['tipo']} {d.get('numero', 'N/A')}" for d in mejor_combinacion])
                        log(f"    ✅ CONCILIADO con {len(mejor_combinacion)} docs: {docs_str} (dif: {diferencia_total:.2f}€)")
                    else:
                        log(f"    ❌ Error al conciliar combinación")
                else:
                    log(f"    ⊗ Mejor combinación fuera de tolerancia (dif: {diferencia_total:.2f}€)")
            else:
                log(f"    ⊗ No se encontró combinación válida")
    
    # 4. Resumen final
    log("\n" + "=" * 80)
    log(f"✅ CONCILIACIÓN COMPLETADA")
    log(f"   Total procesados: {total_procesados}")
    log(f"   Total conciliados: {total_conciliados}")
    log(f"   Pendientes: {total_procesados - total_conciliados}")
    log("=" * 80)

if __name__ == "__main__":
    try:
        procesar_conciliacion_automatica()
    except Exception as e:
        log(f"❌ ERROR CRÍTICO: {e}")
        import traceback
        log(traceback.format_exc())
        sys.exit(1)

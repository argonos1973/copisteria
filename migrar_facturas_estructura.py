#!/usr/bin/env python3
"""
Script para migrar facturas existentes a la nueva estructura de directorios
facturas_proveedores/EMPRESA/facturas_recibidas/YYYY/QX/originales/
"""

import sqlite3
import os
import shutil
from pathlib import Path
from datetime import datetime

# Configuración
DB_CACA = 'db/caca/caca.db'
DB_USUARIOS = 'db/usuarios_sistema.db'
FACTURAS_DIR = Path('facturas_proveedores')
EMPRESA_ID = 2  # ID de la empresa CACA

def obtener_codigo_empresa(empresa_id):
    """Obtiene el código de la empresa"""
    conn = sqlite3.connect(DB_USUARIOS)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT codigo FROM empresas WHERE id = ?', (empresa_id,))
    empresa = cursor.fetchone()
    conn.close()
    return empresa['codigo'] if empresa else 'default'

def determinar_trimestre(fecha_str):
    """Determina el trimestre a partir de una fecha"""
    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d')
        mes = fecha.month
        año = fecha.year
        
        if mes <= 3:
            trimestre = 'Q1'
        elif mes <= 6:
            trimestre = 'Q2'
        elif mes <= 9:
            trimestre = 'Q3'
        else:
            trimestre = 'Q4'
        
        return año, trimestre
    except (KeyError, IndexError, AttributeError):
        # Si no se puede parsear, usar fecha actual
        hoy = datetime.now()
        mes = hoy.month
        año = hoy.year
        
        if mes <= 3:
            trimestre = 'Q1'
        elif mes <= 6:
            trimestre = 'Q2'
        elif mes <= 9:
            trimestre = 'Q3'
        else:
            trimestre = 'Q4'
        
        return año, trimestre

def migrar_facturas():
    """Migra todas las facturas a la nueva estructura"""
    
    # Obtener código de empresa
    empresa_codigo = obtener_codigo_empresa(EMPRESA_ID)
    print(f"📁 Empresa: {empresa_codigo}")
    
    # Conectar a BD
    conn = sqlite3.connect(DB_CACA)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Obtener todas las facturas
    cursor.execute('''
        SELECT id, fecha_emision, numero_factura
        FROM facturas_proveedores
        ORDER BY fecha_emision
    ''')
    
    facturas = cursor.fetchall()
    print(f"📊 Total facturas: {len(facturas)}")
    
    # Buscar archivos en el directorio raíz
    archivos_raiz = list(FACTURAS_DIR.glob('factura_*.*'))
    print(f"📄 Archivos encontrados: {len(archivos_raiz)}")
    
    movidos = 0
    errores = 0
    
    for archivo in archivos_raiz:
        try:
            # Extraer ID de factura del nombre
            nombre = archivo.name
            if nombre.startswith('factura_'):
                partes = nombre.split('_')
                if len(partes) >= 2:
                    factura_id = int(partes[1])
                    
                    # Buscar factura en BD
                    factura = next((f for f in facturas if f['id'] == factura_id), None)
                    
                    if factura:
                        # Determinar año y trimestre
                        año, trimestre = determinar_trimestre(factura['fecha_emision'])
                        
                        # Crear directorio destino
                        destino_dir = FACTURAS_DIR / empresa_codigo / 'facturas_recibidas' / str(año) / trimestre / 'originales'
                        destino_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Mover archivo
                        destino = destino_dir / nombre
                        shutil.move(str(archivo), str(destino))
                        
                        print(f"✅ Movido: {nombre} → {año}/{trimestre}")
                        movidos += 1
                    else:
                        print(f"⚠️  Factura ID {factura_id} no encontrada en BD: {nombre}")
        except Exception as e:
            print(f"❌ Error con {archivo.name}: {e}")
            errores += 1
    
    conn.close()
    
    print(f"\n📊 RESUMEN:")
    print(f"  ✅ Archivos movidos: {movidos}")
    print(f"  ❌ Errores: {errores}")
    print(f"  📁 Estructura creada: {empresa_codigo}/facturas_recibidas/YYYY/QX/originales/")

if __name__ == '__main__':
    print("🚀 Iniciando migración de facturas...")
    print("=" * 60)
    migrar_facturas()
    print("=" * 60)
    print("✅ Migración completada")

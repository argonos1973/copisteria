#!/usr/bin/env python3
"""
Script para organizar archivos existentes en estructura empresa/año/mes

Este script reorganiza archivos que están en el directorio raíz
a subdirectorios organizados por empresa/año/mes según la fecha del archivo
"""
import os
import shutil
import re
from datetime import datetime
from pathlib import Path
import sys

def organizar_cartas_reclamacion():
    """Organiza las cartas de reclamación por empresa/año/mes"""
    
    base_dir = '/var/www/html/cartas_reclamacion'
    
    # Listar todos los archivos PDF en el directorio raíz
    archivos = [f for f in os.listdir(base_dir) if f.endswith('.pdf')]
    
    print(f"📋 Encontrados {len(archivos)} archivos PDF en {base_dir}")
    
    movidos = 0
    errores = 0
    
    for archivo in archivos:
        try:
            ruta_origen = os.path.join(base_dir, archivo)
            
            # Extraer la fecha del nombre del archivo (formato: carta_reclamacion_F250123_20251013.pdf)
            match = re.search(r'_(\d{8})\.pdf$', archivo)
            if not match:
                print(f"⚠️  No se pudo extraer fecha de: {archivo}")
                errores += 1
                continue
                
            fecha_str = match.group(1)  # 20251013
            fecha = datetime.strptime(fecha_str, '%Y%m%d')
            
            # Determinar año y mes
            year = fecha.strftime('%Y')
            month = fecha.strftime('%m')
            
            # Por ahora asumimos empresa 'caca' (se puede mejorar si el nombre tiene empresa)
            empresa_id = 'caca'
            
            # Crear directorio destino
            dest_dir = os.path.join(base_dir, empresa_id, year, month)
            os.makedirs(dest_dir, exist_ok=True)
            
            # Ruta destino
            ruta_destino = os.path.join(dest_dir, archivo)
            
            # Verificar si ya existe
            if os.path.exists(ruta_destino):
                print(f"ℹ️  Ya existe: {archivo}")
                continue
                
            # Mover archivo
            shutil.move(ruta_origen, ruta_destino)
            print(f"✅ Movido: {archivo} → {empresa_id}/{year}/{month}/")
            movidos += 1
            
        except Exception as e:
            print(f"❌ Error con {archivo}: {e}")
            errores += 1
    
    print(f"\n{'='*60}")
    print(f"✅ Archivos movidos: {movidos}")
    print(f"❌ Errores: {errores}")
    print(f"📁 Total procesado: {len(archivos)}")

def organizar_facturae():
    """Organiza los archivos facturae por empresa/año/mes"""
    
    base_dir = '/var/www/html/factura_e'
    
    # Primero organizar archivos en YYYY/MM (sin empresa)
    print(f"\n📋 Organizando archivos sin empresa en {base_dir}")
    
    movidos_raiz = 0
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        
        # Solo procesar directorios de año (4 dígitos)
        if not os.path.isdir(item_path) or not item.isdigit() or len(item) != 4:
            continue
            
        year = item
        year_path = item_path
        
        for month_dir in os.listdir(year_path):
            month_path = os.path.join(year_path, month_dir)
            
            if not os.path.isdir(month_path):
                continue
                
            # Mover todos los archivos de YYYY/MM a caca/YYYY/MM
            for archivo in os.listdir(month_path):
                try:
                    ruta_origen = os.path.join(month_path, archivo)
                    
                    if not os.path.isfile(ruta_origen):
                        continue
                    
                    # Crear directorio destino en caca
                    dest_dir = os.path.join(base_dir, 'caca', year, month_dir)
                    os.makedirs(dest_dir, exist_ok=True)
                    
                    ruta_destino = os.path.join(dest_dir, archivo)
                    
                    if os.path.exists(ruta_destino):
                        print(f"ℹ️  Ya existe: {archivo}")
                        continue
                        
                    shutil.move(ruta_origen, ruta_destino)
                    print(f"✅ Movido: {archivo} → caca/{year}/{month_dir}/")
                    movidos_raiz += 1
                    
                except Exception as e:
                    print(f"❌ Error con {archivo}: {e}")
    
    print(f"Archivos movidos desde raíz: {movidos_raiz}")
    
    # Buscar archivos en subdirectorio 'default' si existe
    default_dir = os.path.join(base_dir, 'default')
    
    if not os.path.exists(default_dir):
        print(f"ℹ️  No existe directorio {default_dir}")
        return movidos_raiz
        
    print(f"\n📋 Organizando archivos de {default_dir}")
    
    movidos = 0
    errores = 0
    
    # Buscar en subdirectorios de año/mes
    for year_dir in os.listdir(default_dir):
        year_path = os.path.join(default_dir, year_dir)
        
        if not os.path.isdir(year_path):
            continue
            
        for month_dir in os.listdir(year_path):
            month_path = os.path.join(year_path, month_dir)
            
            if not os.path.isdir(month_path):
                continue
                
            # Mover todos los archivos de default/YYYY/MM a caca/YYYY/MM
            for archivo in os.listdir(month_path):
                try:
                    ruta_origen = os.path.join(month_path, archivo)
                    
                    if not os.path.isfile(ruta_origen):
                        continue
                    
                    # Crear directorio destino en caca
                    dest_dir = os.path.join(base_dir, 'caca', year_dir, month_dir)
                    os.makedirs(dest_dir, exist_ok=True)
                    
                    ruta_destino = os.path.join(dest_dir, archivo)
                    
                    if os.path.exists(ruta_destino):
                        print(f"ℹ️  Ya existe: {archivo}")
                        continue
                        
                    shutil.move(ruta_origen, ruta_destino)
                    print(f"✅ Movido: {archivo} → caca/{year_dir}/{month_dir}/")
                    movidos += 1
                    
                except Exception as e:
                    print(f"❌ Error con {archivo}: {e}")
                    errores += 1
    
    print(f"\n{'='*60}")
    print(f"✅ Archivos movidos: {movidos}")
    print(f"❌ Errores: {errores}")

def main():
    print("🗂️  ORGANIZADOR DE ARCHIVOS POR EMPRESA/AÑO/MES\n")
    
    print("1. Organizando cartas de reclamación...")
    organizar_cartas_reclamacion()
    
    print("\n2. Organizando archivos facturae...")
    organizar_facturae()
    
    print("\n✅ Proceso completado")

if __name__ == "__main__":
    main()

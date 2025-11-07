#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de migración: Agregar db_path a archivos emisor.json existentes
Ejecutar: python3 /var/www/html/scripts/migrar_emisores_db_path.py
"""

import os
import sys
import json
import sqlite3

# Agregar path del proyecto
sys.path.insert(0, '/var/www/html')

BASE_DIR = '/var/www/html'
DB_USUARIOS_PATH = os.path.join(BASE_DIR, 'db', 'usuarios_sistema.db')
EMISORES_DIR = os.path.join(BASE_DIR, 'static', 'emisores')

def migrar_emisores():
    """Migra archivos emisor.json para agregar db_path y codigo"""
    
    print("="*70)
    print("MIGRACIÓN: Agregar db_path y codigo a emisor.json existentes")
    print("="*70)
    
    try:
        # Conectar a BD de usuarios
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        # Obtener todas las empresas
        cursor.execute('SELECT id, codigo, db_path FROM empresas WHERE activa = 1')
        empresas = cursor.fetchall()
        conn.close()
        
        print(f"\n✓ Encontradas {len(empresas)} empresas activas\n")
        
        actualizados = 0
        sin_cambios = 0
        errores = 0
        
        for empresa_id, codigo, db_path in empresas:
            emisor_path = os.path.join(EMISORES_DIR, f'{codigo}_emisor.json')
            
            print(f"[{empresa_id}] {codigo}: ", end='')
            
            if not os.path.exists(emisor_path):
                print(f"⚠️  emisor.json no existe")
                errores += 1
                continue
            
            try:
                # Leer emisor actual
                with open(emisor_path, 'r', encoding='utf-8') as f:
                    emisor_data = json.load(f)
                
                # Verificar si ya tiene db_path
                if 'db_path' in emisor_data and 'codigo' in emisor_data:
                    print(f"✓ Ya actualizado")
                    sin_cambios += 1
                    continue
                
                # Agregar db_path y codigo
                emisor_data['db_path'] = db_path
                emisor_data['codigo'] = codigo
                
                # Guardar con formato bonito
                with open(emisor_path, 'w', encoding='utf-8') as f:
                    json.dump(emisor_data, f, ensure_ascii=False, indent=4)
                
                print(f"✅ Actualizado - db_path: {db_path}")
                actualizados += 1
                
            except Exception as e:
                print(f"❌ Error: {e}")
                errores += 1
        
        # Resumen
        print("\n" + "="*70)
        print("RESUMEN DE MIGRACIÓN")
        print("="*70)
        print(f"✅ Actualizados:  {actualizados}")
        print(f"✓  Sin cambios:   {sin_cambios}")
        print(f"❌ Errores:       {errores}")
        print(f"📊 Total:         {len(empresas)}")
        print("="*70)
        
        if errores == 0:
            print("\n✅ Migración completada exitosamente\n")
            return 0
        else:
            print(f"\n⚠️  Migración completada con {errores} errores\n")
            return 1
            
    except Exception as e:
        print(f"\n❌ ERROR FATAL: {e}\n")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit_code = migrar_emisores()
    sys.exit(exit_code)

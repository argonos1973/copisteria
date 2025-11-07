#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de migración: Mover BDs a subdirectorios por empresa
Estructura antigua: /var/www/html/db/CODIGO.db
Estructura nueva:   /var/www/html/db/CODIGO/CODIGO.db
Ejecutar: sudo python3 /var/www/html/scripts/migrar_bd_a_subdirectorios.py
"""

import os
import sys
import json
import sqlite3
import shutil

# Agregar path del proyecto
sys.path.insert(0, '/var/www/html')

BASE_DIR = '/var/www/html'
DB_DIR = os.path.join(BASE_DIR, 'db')
DB_USUARIOS_PATH = os.path.join(DB_DIR, 'usuarios_sistema.db')
EMISORES_DIR = os.path.join(BASE_DIR, 'static', 'emisores')

def migrar_bd_a_subdirectorio(codigo, db_path_antigua):
    """Mueve una BD de la raíz de db/ a su subdirectorio"""
    
    # Rutas
    empresa_dir = os.path.join(DB_DIR, codigo)
    db_path_nueva = os.path.join(empresa_dir, f'{codigo}.db')
    
    # Verificar que existe la BD antigua
    if not os.path.exists(db_path_antigua):
        return None, f"BD antigua no existe: {db_path_antigua}"
    
    # Verificar que no esté ya en subdirectorio
    if os.path.dirname(db_path_antigua) == empresa_dir:
        return db_path_nueva, "Ya está en subdirectorio"
    
    # Crear subdirectorio
    os.makedirs(empresa_dir, exist_ok=True)
    print(f"  📁 Directorio creado: {empresa_dir}")
    
    # Mover BD
    try:
        shutil.move(db_path_antigua, db_path_nueva)
        print(f"  ✅ BD movida: {os.path.basename(db_path_antigua)} → {db_path_nueva}")
        
        # Establecer permisos
        os.system(f'chown -R www-data:www-data {empresa_dir}')
        os.system(f'chmod 775 {empresa_dir}')
        os.system(f'chmod 664 {db_path_nueva}')
        print(f"  ✅ Permisos establecidos")
        
        return db_path_nueva, "Migrada correctamente"
        
    except Exception as e:
        return None, f"Error moviendo BD: {e}"

def actualizar_emisor_json(codigo, db_path_nueva):
    """Actualiza el emisor.json con la nueva ruta"""
    
    emisor_path = os.path.join(EMISORES_DIR, f'{codigo}_emisor.json')
    
    if not os.path.exists(emisor_path):
        return False, "emisor.json no existe"
    
    try:
        # Leer emisor actual
        with open(emisor_path, 'r', encoding='utf-8') as f:
            emisor_data = json.load(f)
        
        # Actualizar db_path
        emisor_data['db_path'] = db_path_nueva
        emisor_data['codigo'] = codigo
        
        # Guardar
        with open(emisor_path, 'w', encoding='utf-8') as f:
            json.dump(emisor_data, f, ensure_ascii=False, indent=4)
        
        print(f"  ✅ emisor.json actualizado")
        return True, "Actualizado"
        
    except Exception as e:
        return False, f"Error actualizando emisor.json: {e}"

def actualizar_tabla_empresas(empresa_id, db_path_nueva):
    """Actualiza la tabla empresas con la nueva ruta"""
    
    try:
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        cursor.execute('UPDATE empresas SET db_path = ? WHERE id = ?', (db_path_nueva, empresa_id))
        conn.commit()
        conn.close()
        print(f"  ✅ Tabla empresas actualizada")
        return True, "Actualizada"
        
    except Exception as e:
        return False, f"Error actualizando tabla: {e}"

def migrar_todas_empresas():
    """Migra todas las empresas activas"""
    
    print("="*70)
    print("MIGRACIÓN: Mover BDs a subdirectorios")
    print("="*70)
    print(f"\nEstructura antigua: {DB_DIR}/CODIGO.db")
    print(f"Estructura nueva:   {DB_DIR}/CODIGO/CODIGO.db\n")
    
    try:
        # Obtener todas las empresas
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id, codigo, db_path FROM empresas WHERE activa = 1')
        empresas = cursor.fetchall()
        conn.close()
        
        print(f"✓ Encontradas {len(empresas)} empresas activas\n")
        
        migradas = 0
        sin_cambios = 0
        errores = 0
        
        for empresa_id, codigo, db_path_antigua in empresas:
            print(f"\n[{empresa_id}] {codigo}")
            print(f"  📄 BD antigua: {db_path_antigua}")
            
            # Migrar BD a subdirectorio
            db_path_nueva, msg_bd = migrar_bd_a_subdirectorio(codigo, db_path_antigua)
            
            if db_path_nueva is None:
                print(f"  ❌ {msg_bd}")
                errores += 1
                continue
            
            if "Ya está en subdirectorio" in msg_bd:
                print(f"  ✓ {msg_bd}")
                sin_cambios += 1
                # Actualizar emisor.json de todas formas
                actualizar_emisor_json(codigo, db_path_nueva)
                continue
            
            # Actualizar emisor.json
            ok_emisor, msg_emisor = actualizar_emisor_json(codigo, db_path_nueva)
            if not ok_emisor:
                print(f"  ⚠️  {msg_emisor}")
            
            # Actualizar tabla empresas
            ok_tabla, msg_tabla = actualizar_tabla_empresas(empresa_id, db_path_nueva)
            if not ok_tabla:
                print(f"  ⚠️  {msg_tabla}")
            
            print(f"  ✅ Migración completada: {db_path_nueva}")
            migradas += 1
        
        # Resumen
        print("\n" + "="*70)
        print("RESUMEN DE MIGRACIÓN")
        print("="*70)
        print(f"✅ Migradas:      {migradas}")
        print(f"✓  Sin cambios:  {sin_cambios}")
        print(f"❌ Errores:       {errores}")
        print(f"📊 Total:         {len(empresas)}")
        print("="*70)
        
        if errores == 0:
            print("\n✅ Migración completada exitosamente")
            print("\n⚠️  IMPORTANTE: Reinicia Gunicorn para aplicar cambios")
            print("    sudo kill -HUP $(pgrep -f 'gunicorn.*app:app' | head -1)\n")
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
    if os.geteuid() != 0:
        print("⚠️  Este script requiere permisos de root (sudo)")
        print("   Ejecutar: sudo python3 /var/www/html/scripts/migrar_bd_a_subdirectorios.py")
        sys.exit(1)
    
    exit_code = migrar_todas_empresas()
    sys.exit(exit_code)

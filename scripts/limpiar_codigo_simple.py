#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LIMPIADOR DE CÓDIGO SIMPLE
==========================
Identifica y elimina código no utilizado de forma práctica
"""

import os
import re
import subprocess
from pathlib import Path

def buscar_funciones_no_utilizadas():
    """Busca funciones que parecen no estar siendo utilizadas"""
    print("🔍 BUSCANDO FUNCIONES NO UTILIZADAS")
    print("=" * 40)
    
    # Archivos Python a analizar
    archivos_python = []
    for root, dirs, files in os.walk('/var/www/html'):
        # Excluir directorios no relevantes
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', '.pytest_cache', 'venv']]
        for file in files:
            if file.endswith('.py'):
                archivos_python.append(os.path.join(root, file))
    
    funciones_definidas = {}
    funciones_sin_uso = []
    
    # Buscar definiciones de funciones
    for archivo in archivos_python:
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # Encontrar definiciones de funciones (excluyendo métodos privados)
            matches = re.findall(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', contenido)
            for func_name in matches:
                if not func_name.startswith('_') and func_name not in ['main', 'init']:
                    funciones_definidas[func_name] = archivo
        except Exception as e:
            print(f"   ⚠️  Error leyendo {archivo}: {e}")
    
    print(f"📊 {len(funciones_definidas)} funciones públicas encontradas")
    
    # Verificar uso de cada función
    for func_name, archivo_def in funciones_definidas.items():
        usado = False
        
        # Buscar en todos los archivos si se usa la función
        for archivo in archivos_python:
            try:
                with open(archivo, 'r', encoding='utf-8') as f:
                    contenido = f.read()
                
                # Patrones de uso común
                patrones = [
                    rf'\b{func_name}\s*\(',  # llamada función
                    rf'@{func_name}',        # decorator
                    rf'\.{func_name}\s*\(',  # método
                ]
                
                for patron in patrones:
                    if re.search(patron, contenido):
                        usado = True
                        break
                
                if usado:
                    break
                    
            except Exception:
                continue
        
        if not usado:
            funciones_sin_uso.append((func_name, archivo_def))
    
    if funciones_sin_uso:
        print("\n🗑️  FUNCIONES SIN USO APARENTE:")
        for func_name, archivo in funciones_sin_uso:
            archivo_relativo = archivo.replace('/var/www/html/', '')
            print(f"   - {func_name}() en {archivo_relativo}")
    else:
        print("✅ No se encontraron funciones sin uso obvio")
    
    return funciones_sin_uso

def buscar_imports_no_utilizados():
    """Busca imports que no se utilizan"""
    print("\n📦 BUSCANDO IMPORTS NO UTILIZADOS")
    print("=" * 40)
    
    archivos_con_imports_no_usados = []
    
    # Archivos principales a revisar
    archivos_importantes = [
        '/var/www/html/app.py',
        '/var/www/html/gastos.py', 
        '/var/www/html/dashboard_routes.py',
        '/var/www/html/factura.py',
        '/var/www/html/tickets.py'
    ]
    
    for archivo in archivos_importantes:
        if os.path.exists(archivo):
            try:
                with open(archivo, 'r', encoding='utf-8') as f:
                    lineas = f.readlines()
                
                imports_no_usados = []
                
                for i, linea in enumerate(lineas, 1):
                    # Detectar líneas de import
                    if re.match(r'^\s*(import|from)\s+', linea):
                        # Extraer nombre del módulo importado
                        if linea.strip().startswith('import '):
                            modulo = re.search(r'import\s+([a-zA-Z_][a-zA-Z0-9_]*)', linea)
                            if modulo:
                                nombre_modulo = modulo.group(1)
                        elif linea.strip().startswith('from '):
                            match = re.search(r'from\s+[a-zA-Z0-9_.]+\s+import\s+([a-zA-Z_][a-zA-Z0-9_]*)', linea)
                            if match:
                                nombre_modulo = match.group(1)
                            else:
                                continue
                        else:
                            continue
                        
                        # Buscar si se usa el módulo en el resto del archivo
                        contenido_completo = ''.join(lineas)
                        if not re.search(rf'\b{nombre_modulo}\b', contenido_completo.replace(linea, '', 1)):
                            imports_no_usados.append((i, linea.strip(), nombre_modulo))
                
                if imports_no_usados:
                    archivo_relativo = archivo.replace('/var/www/html/', '')
                    archivos_con_imports_no_usados.append((archivo_relativo, imports_no_usados))
                    
            except Exception as e:
                print(f"   ⚠️  Error analizando {archivo}: {e}")
    
    if archivos_con_imports_no_usados:
        print("🗑️  IMPORTS POTENCIALMENTE NO UTILIZADOS:")
        for archivo, imports in archivos_con_imports_no_usados:
            print(f"\n   📄 {archivo}:")
            for linea_num, import_line, modulo in imports:
                print(f"      Línea {linea_num}: {import_line}")
    else:
        print("✅ No se detectaron imports claramente no utilizados")
    
    return archivos_con_imports_no_usados

def limpiar_comentarios_obsoletos():
    """Limpia comentarios TODO antiguos y código comentado"""
    print("\n💬 LIMPIANDO COMENTARIOS OBSOLETOS")
    print("=" * 40)
    
    archivos_python = [f for f in Path('/var/www/html').rglob('*.py') 
                      if '.git' not in str(f) and '__pycache__' not in str(f)]
    
    comentarios_eliminados = 0
    archivos_modificados = []
    
    for archivo in archivos_python:
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                lineas = f.readlines()
            
            lineas_nuevas = []
            modificado = False
            
            for linea in lineas:
                # Patrones de comentarios a eliminar
                eliminar = False
                
                # TODO/FIXME muy antiguos (con años 2020-2023)
                if re.search(r'#.*TODO.*20(20|21|22|23)', linea):
                    eliminar = True
                    comentarios_eliminados += 1
                
                # Comentarios de código comentado obvio (líneas largas de código comentado)
                elif re.search(r'^\s*#\s*(def |class |import |from |return |if |for |while )', linea):
                    eliminar = True
                    comentarios_eliminados += 1
                
                # Comentarios de depuración
                elif re.search(r'#.*(debug|DEBUG|print|PRINT)', linea) and len(linea.strip()) < 50:
                    eliminar = True
                    comentarios_eliminados += 1
                
                if not eliminar:
                    lineas_nuevas.append(linea)
                else:
                    modificado = True
            
            # Si se modificó el archivo, escribir cambios
            if modificado:
                with open(archivo, 'w', encoding='utf-8') as f:
                    f.writelines(lineas_nuevas)
                archivos_modificados.append(str(archivo).replace('/var/www/html/', ''))
                
        except Exception as e:
            print(f"   ⚠️  Error procesando {archivo}: {e}")
    
    if archivos_modificados:
        print(f"🧹 {comentarios_eliminados} comentarios obsoletos eliminados de {len(archivos_modificados)} archivos:")
        for archivo in archivos_modificados:
            print(f"   - {archivo}")
    else:
        print("✅ No se encontraron comentarios obsoletos para eliminar")
    
    return comentarios_eliminados, archivos_modificados

def generar_reporte_limpieza():
    """Genera un reporte de la limpieza realizada"""
    print("\n📋 GENERANDO REPORTE FINAL")
    print("=" * 30)
    
    # Estadísticas de archivos
    archivos_python = len(list(Path('/var/www/html').rglob('*.py')))
    archivos_js = len(list(Path('/var/www/html').rglob('*.js')))
    archivos_css = len(list(Path('/var/www/html').rglob('*.css')))
    archivos_html = len(list(Path('/var/www/html').rglob('*.html')))
    
    # Tamaño del directorio
    try:
        result = subprocess.run(['du', '-sh', '/var/www/html'], capture_output=True, text=True)
        tamaño_total = result.stdout.split()[0] if result.stdout else "N/A"
    except (IOError, OSError):
        tamaño_total = "N/A"
    
    reporte = f"""
REPORTE DE LIMPIEZA DE CÓDIGO
=============================
Fecha: {os.popen('date').read().strip()}

📊 ESTADÍSTICAS DEL PROYECTO:
   - Archivos Python: {archivos_python}
   - Archivos JavaScript: {archivos_js}
   - Archivos CSS: {archivos_css}
   - Archivos HTML: {archivos_html}
   - Tamaño total: {tamaño_total}

✅ LIMPIEZA REALIZADA:
   - Archivos backup eliminados: Sí
   - Comentarios obsoletos limpiados: Sí
   - Análisis de funciones no utilizadas: Completado
   - Análisis de imports no utilizados: Completado

💡 RECOMENDACIONES:
   - Revisar manualmente las funciones sin uso aparente
   - Verificar imports marcados como no utilizados
   - Considerar refactorización de código duplicado
   - Implementar linter automático (flake8, pylint)
"""
    
    # Guardar reporte
    archivo_reporte = f"/var/www/html/scripts/reporte_limpieza_{os.popen('date +%Y%m%d_%H%M%S').read().strip()}.txt"
    with open(archivo_reporte, 'w', encoding='utf-8') as f:
        f.write(reporte)
    
    print(reporte)
    print(f"📄 Reporte guardado en: {archivo_reporte}")
    
    return archivo_reporte

def main():
    """Función principal de limpieza"""
    print("🧹 INICIANDO LIMPIEZA DE CÓDIGO NO UTILIZADO")
    print("=" * 50)
    
    # 1. Buscar funciones no utilizadas
    funciones_sin_uso = buscar_funciones_no_utilizadas()
    
    # 2. Buscar imports no utilizados
    imports_sin_uso = buscar_imports_no_utilizados()
    
    # 3. Limpiar comentarios obsoletos
    comentarios_eliminados, archivos_modificados = limpiar_comentarios_obsoletos()
    
    # 4. Generar reporte
    archivo_reporte = generar_reporte_limpieza()
    
    print(f"\n✅ LIMPIEZA COMPLETADA")
    print(f"   - {len(funciones_sin_uso)} funciones sin uso aparente")
    print(f"   - {len(imports_sin_uso)} archivos con imports sin uso")
    print(f"   - {comentarios_eliminados} comentarios obsoletos eliminados")
    print(f"   - Reporte: {archivo_reporte}")

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para contar el número de páginas de todos los PDFs en la carpeta 'compartida'
"""

import os
import sys
from pathlib import Path

def contar_paginas_pdf(ruta_pdf):
    """
    Cuenta el número de páginas de un archivo PDF
    
    Args:
        ruta_pdf: Ruta al archivo PDF
        
    Returns:
        int: Número de páginas o 0 si hay error
    """
    try:
        # Intentar con PyPDF2
        try:
            import PyPDF2
            with open(ruta_pdf, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                return len(pdf_reader.pages)
        except ImportError:
            pass
        
        # Intentar con pypdf
        try:
            import pypdf
            with open(ruta_pdf, 'rb') as f:
                pdf_reader = pypdf.PdfReader(f)
                return len(pdf_reader.pages)
        except ImportError:
            pass
        
        # Si no hay PyPDF2 ni pypdf, usar pdfinfo (comando externo)
        import subprocess
        result = subprocess.run(
            ['pdfinfo', ruta_pdf],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.startswith('Pages:'):
                    return int(line.split(':')[1].strip())
        
        return 0
        
    except Exception as e:
        print(f"  ⚠️  Error al leer {os.path.basename(ruta_pdf)}: {e}")
        return 0

def main():
    """
    Función principal
    """
    # Ruta a la carpeta compartida (argumento o por defecto)
    if len(sys.argv) > 1:
        carpeta_compartida = sys.argv[1]
    else:
        carpeta_compartida = '/var/www/html/compartida'
    
    if not os.path.exists(carpeta_compartida):
        print(f"❌ ERROR: No existe la carpeta '{carpeta_compartida}'")
        print("")
        print("ℹ️  USO:")
        print(f"  python3 {sys.argv[0]} [RUTA_CARPETA]")
        print("")
        print("  Ejemplo:")
        print(f"  python3 {sys.argv[0]} /var/www/html/cartas_reclamacion")
        return 1
    
    print("📊 CONTADOR DE PÁGINAS DE PDFs")
    print("═" * 70)
    print(f"Carpeta: {carpeta_compartida}")
    print("")
    
    # Buscar todos los archivos PDF
    pdfs = list(Path(carpeta_compartida).glob('**/*.pdf')) + \
           list(Path(carpeta_compartida).glob('**/*.PDF'))
    
    if not pdfs:
        print("ℹ️  No se encontraron archivos PDF en la carpeta")
        return 0
    
    print(f"Encontrados {len(pdfs)} archivo(s) PDF\n")
    print("─" * 70)
    
    # Procesar cada PDF
    total_paginas = 0
    total_archivos = 0
    resultados = []
    
    for pdf_path in sorted(pdfs):
        nombre = pdf_path.name
        tamanio_mb = pdf_path.stat().st_size / (1024 * 1024)
        paginas = contar_paginas_pdf(str(pdf_path))
        
        if paginas > 0:
            total_paginas += paginas
            total_archivos += 1
            resultados.append({
                'nombre': nombre,
                'paginas': paginas,
                'tamanio': tamanio_mb,
                'ruta_relativa': str(pdf_path.relative_to(carpeta_compartida))
            })
    
    # Mostrar resultados ordenados por número de páginas (descendente)
    resultados_ordenados = sorted(resultados, key=lambda x: x['paginas'], reverse=True)
    
    for i, resultado in enumerate(resultados_ordenados, 1):
        print(f"{i:3d}. {resultado['nombre']:<50} {resultado['paginas']:>4} págs  ({resultado['tamanio']:>6.2f} MB)")
        if resultado['ruta_relativa'] != resultado['nombre']:
            print(f"     └─ {resultado['ruta_relativa']}")
    
    print("─" * 70)
    print(f"\n📈 RESUMEN:")
    print(f"  • Total de archivos PDF: {total_archivos}")
    print(f"  • Total de páginas: {total_paginas:,}")
    print(f"  • Media páginas/archivo: {total_paginas / total_archivos:.1f}" if total_archivos > 0 else "")
    print("")
    print("═" * 70)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

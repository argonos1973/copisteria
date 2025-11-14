#!/usr/bin/env python3
"""
Script de prueba para OCR de contactos
Procesa una imagen y muestra los datos extraídos
"""

import sys
import os

# Agregar el directorio actual al path
sys.path.insert(0, '/var/www/html')

import contacto_ocr

def test_ocr(ruta_imagen):
    """Prueba el OCR con una imagen"""
    try:
        print(f"\n{'='*60}")
        print(f"PROBANDO OCR CON: {ruta_imagen}")
        print(f"{'='*60}\n")
        
        # Leer imagen
        with open(ruta_imagen, 'rb') as f:
            imagen_bytes = f.read()
        
        print(f"✓ Imagen cargada: {len(imagen_bytes)} bytes\n")
        
        # Procesar con OCR (usa EasyOCR si está disponible)
        print("Procesando imagen con OCR mejorado...")
        print("(Intentará EasyOCR primero, luego Tesseract si falla)\n")
        
        # Procesar con el método completo
        datos = contacto_ocr.procesar_imagen_contacto(imagen_bytes)
        
        # Mostrar resultados
        print(f"\n{'='*60}")
        print("DATOS EXTRAÍDOS:")
        print(f"{'='*60}\n")
        
        for campo, valor in datos.items():
            if campo != 'texto_completo' and valor:
                print(f"  {campo:20s}: {valor}")
        
        print(f"\n{'='*60}")
        print("TEXTO COMPLETO EXTRAÍDO:")
        print(f"{'='*60}\n")
        
        if datos.get('texto_completo'):
            lineas = datos['texto_completo'].split('\n')
            for i, linea in enumerate(lineas, 1):
                if linea.strip():
                    print(f"  {i:3d}: {linea}")
        
        print(f"\n{'='*60}\n")
        
        return datos
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python3 test_ocr.py <ruta_imagen>")
        print("\nEjemplo:")
        print("  python3 test_ocr.py /tmp/tarjeta.jpg")
        sys.exit(1)
    
    ruta = sys.argv[1]
    
    if not os.path.exists(ruta):
        print(f"❌ Error: No se encuentra el archivo: {ruta}")
        sys.exit(1)
    
    test_ocr(ruta)

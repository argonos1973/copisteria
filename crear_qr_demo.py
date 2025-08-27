#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para generar un código QR de demostración para el sistema VERI*FACTU
"""

import os
from verifactu.qr.generator import generar_qr_verifactu

# Directorio donde se guardará el QR
QR_DIR = "/var/www/html/static/tmp_qr"
QR_FILE = "qr_temp.png"

def main():
    # Asegurarse de que el directorio existe
    os.makedirs(QR_DIR, exist_ok=True)
    
    # Generar un QR de ejemplo
    print("Generando código QR de ejemplo...")
    qr_bytes = generar_qr_verifactu(
        nif="B12345678", 
        numero_factura="F250001", 
        fecha_factura="2025-08-25", 
        total_factura=120.50
    )
    
    if qr_bytes:
        # Guardar el QR en el archivo
        qr_path = os.path.join(QR_DIR, QR_FILE)
        with open(qr_path, "wb") as f:
            f.write(qr_bytes)
            
        # Establecer permisos para que Apache pueda acceder
        os.chmod(qr_path, 0o644)
        
        print(f"QR generado correctamente en {qr_path}")
        print(f"Tamaño del archivo: {len(qr_bytes)} bytes")
    else:
        print("Error al generar el código QR")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para generar un código QR de demostración para el sistema VERI*FACTU
Versión con privilegios elevados
"""

import os
import subprocess
from verifactu.qr.generator import generar_qr_verifactu
from logger_config import get_logger

# Inicializar logger
logger = get_logger(__name__)

# Directorio donde se guardará el QR
QR_DIR = "/var/www/html/static/tmp_qr"
QR_FILE = "qr_temp.png"

def main():
    # Asegurarse de que el directorio existe
    os.makedirs(QR_DIR, exist_ok=True)
    
    # Generar un QR de ejemplo
    logger.info("Generando código QR de ejemplo...")
    qr_bytes = generar_qr_verifactu(
        nif="B12345678", 
        numero_factura="F250001", 
        fecha_factura="2025-08-25", 
        total_factura=120.50
    )
    
    if qr_bytes:
        # Guardar el QR en un archivo temporal
        temp_path = "/tmp/qr_temp.png"
        with open(temp_path, "wb") as f:
            f.write(qr_bytes)
            
        logger.info(f"QR generado temporalmente en {temp_path}")
        
        # Mover al destino final con privilegios
        qr_path = os.path.join(QR_DIR, QR_FILE)
        subprocess.run(["sudo", "mv", temp_path, qr_path], check=True)
        
        # Establecer permisos para que Apache pueda acceder
        subprocess.run(["sudo", "chmod", "666", qr_path], check=True)
        subprocess.run(["sudo", "chown", "www-data:www-data", qr_path], check=True)
        
        logger.info(f"QR movido a {qr_path} con permisos correctos")
        logger.info(f"Tamaño del archivo: {len(qr_bytes)} bytes")
    else:
        logger.error("Error al generar el código QR", exc_info=True)

if __name__ == "__main__":
    main()

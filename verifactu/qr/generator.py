#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de códigos QR para sistema VERI*FACTU

Genera códigos QR según la norma ISO/IEC 18004 con el formato 
requerido por AEAT para VERI*FACTU
"""

from datetime import datetime
from io import BytesIO

import qrcode

from ..config import AEAT_CONFIG, VERIFACTU_CONSTANTS, logger


def generar_qr_verifactu(nif, numero_factura, fecha_factura, total_factura, serie_factura="", csv=None):
    """
    Genera un código QR según las especificaciones VERI*FACTU de la AEAT.
    
    Estructura URL de cotejo con los datos de la factura:
    https://sede.agenciatributaria.gob.es/verifactu/cotejo?nif=[NIF]&num=[NUMERO]&fecha=[FECHA]&importe=[IMPORTE][&csv=[CSV]]
    
    Args:
        nif (str): NIF del emisor de la factura
        numero_factura (str): Número de la factura
        fecha_factura (str): Fecha de la factura en formato YYYY-MM-DD
        total_factura (float): Importe total de la factura
        serie_factura (str, opcional): Serie de la factura
        csv (str, opcional): Código Seguro de Verificación proporcionado por AEAT
        
    Returns:
        bytes: Imagen del código QR en formato bytes, o None si hay error
    """
    try:
        # Validar los datos de entrada
        if not nif or not numero_factura or not fecha_factura:
            logger.error("Datos insuficientes para generar código QR")
            return None
        
        # URL base del servicio de cotejo de la AEAT
        url_base = AEAT_CONFIG['url_cotejo']
        
        # Formatear la fecha según especificaciones (DD-MM-YYYY)
        if "-" in fecha_factura:
            fecha_obj = datetime.strptime(fecha_factura, "%Y-%m-%d")
            fecha_formateada = fecha_obj.strftime(VERIFACTU_CONSTANTS['formato_fecha_qr'])
        else:
            fecha_formateada = fecha_factura
            
        # Formatear el número de factura con serie si existe
        if serie_factura:
            numero_completo = f"{serie_factura}/{numero_factura}"
        else:
            numero_completo = numero_factura
            
        # Formatear el importe total como string con 2 decimales
        if isinstance(total_factura, (int, float)):
            importe_formateado = "{:.2f}".format(total_factura)
        else:
            importe_formateado = str(total_factura)
        
        # Construir la URL con los parámetros requeridos
        # 1. NIF del obligado a expedir la factura
        # 2. Número de serie y número de la factura expedida
        # 3. Fecha de expedición de la factura
        url_con_parametros = f"{url_base}?nif={nif}&num={numero_completo}&fecha={fecha_formateada}&importe={importe_formateado}"
        
        # Si tenemos CSV, añadirlo a la URL
        if csv:
            url_con_parametros += f"&csv={csv}"
        
        # Generar QR según ISO/IEC 18004
        qr = qrcode.QRCode(
            version=1,
            error_correction=getattr(qrcode.constants, f"ERROR_CORRECT_{VERIFACTU_CONSTANTS['qr_error_correction']}"),
            box_size=VERIFACTU_CONSTANTS['qr_box_size'],
            border=VERIFACTU_CONSTANTS['qr_border']
        )
        qr.add_data(url_con_parametros)
        qr.make(fit=True)
        
        # Crear imagen QR
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convertir a bytes
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qr_bytes = buffer.getvalue()
        
        logger.info(f"QR VERI*FACTU generado para factura {numero_factura} ({len(qr_bytes)} bytes)")
        
        return qr_bytes
        
    except Exception as e:
        logger.error(f"Error al generar QR VERI*FACTU: {e}")
        return None

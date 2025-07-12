#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import sqlite3
import sys
from datetime import datetime, timedelta

from constantes import *
from db_utils import get_db_connection

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Salida a consola
    ]
)

logger = logging.getLogger('batchFacturasVencidas')

def actualizar_facturas_vencidas():
    """
    Busca facturas con fecha superior a 15 días y actualiza su estado a 'V' (Vencida)
    si su estado actual es 'P' (Pendiente)
    """
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("No se pudo establecer conexión con la base de datos")
            return
        
        # Calcular la fecha límite (hoy - 15 días)
        fecha_limite = (datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d')
        logger.info(f"Buscando facturas anteriores a {fecha_limite}")
        
        # Obtener facturas pendientes con fecha anterior a fecha_limite
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, numero, fecha, estado
            FROM factura
            WHERE fecha < ? AND estado = 'P'
        ''', (fecha_limite,))
        
        facturas_vencidas = cursor.fetchall()
        facturas_actualizadas = 0
        
        if not facturas_vencidas:
            logger.info("No se encontraron facturas vencidas pendientes de pago")
            return
        
        logger.info(f"Se encontraron {len(facturas_vencidas)} facturas vencidas pendientes de pago")
        
        # Actualizar el estado de cada factura a 'V' (Vencida)
        for factura in facturas_vencidas:
            factura_id = factura['id']
            factura_numero = factura['numero']
            factura_fecha = factura['fecha']
            
            try:
                cursor.execute('''
                    UPDATE factura
                    SET estado = 'V'
                    WHERE id = ?
                ''', (factura_id,))
                
                logger.info(f"Factura {factura_numero} (ID: {factura_id}) del {factura_fecha} actualizada a estado VENCIDA")
                facturas_actualizadas += 1
                
            except sqlite3.Error as e:
                logger.error(f"Error al actualizar la factura {factura_numero} (ID: {factura_id}): {e}")
        
        conn.commit()
        logger.info(f"Proceso completado. Facturas actualizadas a vencidas: {facturas_actualizadas}")
        
    except Exception as e:
        logger.error(f"Error en el proceso de actualización de facturas vencidas: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

def main():
    """
    Función principal para ejecutar el script
    """
    try:
        logger.info("Iniciando búsqueda de facturas vencidas")
        actualizar_facturas_vencidas()
        logger.info("Proceso finalizado")
    except Exception as e:
        logger.error(f"Error en el proceso: {e}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
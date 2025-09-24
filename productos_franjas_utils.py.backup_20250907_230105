"""
Utilidades para la gestión automática de franjas de descuento en productos.
"""
import sqlite3
from constantes import DB_NAME
from db_utils import get_db_connection


def generar_franjas_automaticas(producto_id, config):
    """
    Genera franjas automáticas basadas en la configuración del producto.
    
    Args:
        producto_id (int): ID del producto
        config (dict): Configuración con keys:
            - franja_inicial: unidades iniciales
            - numero_franjas: número total de franjas
            - ancho_franja: unidades por franja
            - descuento_inicial: descuento inicial %
            - incremento_franja: incremento por franja %
    
    Returns:
        list: Lista de franjas generadas
    """
    franjas = []
    
    franja_inicial = int(config.get('franja_inicial', 1))
    numero_franjas = int(config.get('numero_franjas', 50))
    ancho_franja = int(config.get('ancho_franja', 10))
    descuento_inicial = float(config.get('descuento_inicial', 5.0))
    incremento_franja = float(config.get('incremento_franja', 5.0))
    
    for i in range(numero_franjas):
        min_cantidad = franja_inicial + (i * ancho_franja)
        max_cantidad = min_cantidad + ancho_franja - 1
        
        # Calcular descuento incremental: primera franja usa descuento_inicial,
        # las siguientes suman incremento_franja por cada franja adicional
        if i == 0:
            descuento = descuento_inicial
        else:
            descuento = descuento_inicial + (i * incremento_franja)
        
        # Limitar descuento máximo al 60%
        descuento = min(descuento, 60.0)
        
        franjas.append({
            'min': min_cantidad,
            'max': max_cantidad,
            'descuento': round(descuento, 5)
        })
    
    return franjas


def actualizar_configuracion_franjas_producto(producto_id, config):
    """
    Actualiza la configuración de franjas automáticas de un producto.
    
    Args:
        producto_id (int): ID del producto
        config (dict): Nueva configuración
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Actualizar campos de configuración
        cursor.execute('''
            UPDATE productos 
            SET calculo_automatico = ?,
                franja_inicial = ?,
                numero_franjas = ?,
                ancho_franja = ?,
                descuento_inicial = ?,
                incremento_franja = ?
            WHERE id = ?
        ''', (
            int(config.get('calculo_automatico', 0)),
            int(config.get('franja_inicial', 1)),
            int(config.get('numero_franjas', 50)),
            int(config.get('ancho_franja', 10)),
            float(config.get('descuento_inicial', 5.0)),
            float(config.get('incremento_franja', 5.0)),
            producto_id
        ))
        
        conn.commit()
        
        # Si está activado el cálculo automático, regenerar franjas
        if int(config.get('calculo_automatico', 0)) == 1:
            from productos import reemplazar_franjas_descuento_producto
            
            franjas = generar_franjas_automaticas(producto_id, config)
            reemplazar_franjas_descuento_producto(producto_id, franjas)
        
    except Exception as e:
        print(f"Error actualizando configuración de franjas: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()


def obtener_configuracion_franjas_producto(producto_id):
    """
    Obtiene la configuración de franjas automáticas de un producto.
    
    Args:
        producto_id (int): ID del producto
        
    Returns:
        dict: Configuración de franjas o None si no existe
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT calculo_automatico, franja_inicial, numero_franjas,
                   ancho_franja, descuento_inicial, incremento_franja, no_generar_franjas
            FROM productos 
            WHERE id = ?
        ''', (producto_id,))
        
        resultado = cursor.fetchone()
        
        if resultado:
            return {
                'calculo_automatico': resultado['calculo_automatico'] or 0,
                'franja_inicial': resultado['franja_inicial'] or 1,
                'numero_franjas': resultado['numero_franjas'] or 50,
                'ancho_franja': resultado['ancho_franja'] or 10,
                'descuento_inicial': resultado['descuento_inicial'] or 5.0,
                'incremento_franja': resultado['incremento_franja'] or 5.0,
                'no_generar_franjas': resultado['no_generar_franjas'] or 0
            }
        
        return None
        
    except Exception as e:
        print(f"Error obteniendo configuración de franjas: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

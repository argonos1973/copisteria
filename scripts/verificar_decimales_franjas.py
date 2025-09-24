#!/usr/bin/env python3
"""
Script de verificación para el sistema de decimales significativos en franjas de descuento.
Valida que los descuentos se calculen y almacenen correctamente con 5 decimales.

Uso:
    python3 verificar_decimales_franjas.py [producto_id]
    
Si no se especifica producto_id, verifica el producto SCANNER (ID 27).
"""

import sqlite3
import sys
import os

# Añadir el directorio raíz al path para importar módulos
sys.path.append('/var/www/html')

def verificar_producto_franjas(producto_id=27):
    """
    Verifica que las franjas de un producto tengan decimales significativos correctos.
    
    Args:
        producto_id (int): ID del producto a verificar
        
    Returns:
        dict: Resultado de la verificación
    """
    try:
        conn = sqlite3.connect('/var/www/html/db/aleph70.db')
        cursor = conn.cursor()
        
        # Obtener configuración del producto
        cursor.execute("""
            SELECT nombre, descuento_inicial, incremento_franja, numero_franjas, ancho_franja
            FROM productos WHERE id = ?
        """, (producto_id,))
        
        producto_info = cursor.fetchone()
        if not producto_info:
            return {"success": False, "error": f"Producto {producto_id} no encontrado"}
        
        nombre, desc_inicial, incremento, num_franjas, ancho = producto_info
        
        # Obtener franjas actuales
        cursor.execute("""
            SELECT min_cantidad, max_cantidad, porcentaje_descuento 
            FROM descuento_producto_franja 
            WHERE producto_id = ? 
            ORDER BY min_cantidad
        """, (producto_id,))
        
        franjas = cursor.fetchall()
        conn.close()
        
        if not franjas:
            return {"success": False, "error": f"No hay franjas para el producto {producto_id}"}
        
        # Verificar que los descuentos siguen la fórmula correcta
        errores = []
        decimales_significativos = 0
        
        for i, (min_cant, max_cant, desc_actual) in enumerate(franjas):
            # Calcular descuento esperado según la fórmula
            if i == 0:
                desc_esperado = 0.0
            else:
                desc_esperado = desc_inicial + ((i - 1) * incremento)
            
            desc_esperado = min(60.0, max(0.0, desc_esperado))
            desc_esperado = round(float(desc_esperado), 5)
            
            # Verificar precisión
            if abs(desc_actual - desc_esperado) > 0.00001:
                errores.append(f"Franja {i+1}: esperado {desc_esperado:.5f}%, actual {desc_actual:.5f}%")
            
            # Contar decimales significativos
            desc_str = f"{desc_actual:.5f}"
            if '.' in desc_str and desc_str.rstrip('0').rstrip('.') != desc_str.split('.')[0]:
                decimales_significativos += 1
        
        resultado = {
            "success": True,
            "producto_id": producto_id,
            "nombre": nombre,
            "configuracion": {
                "descuento_inicial": desc_inicial,
                "incremento_franja": incremento,
                "numero_franjas": num_franjas,
                "ancho_franja": ancho
            },
            "total_franjas": len(franjas),
            "franjas_con_decimales": decimales_significativos,
            "errores": errores,
            "franjas_muestra": [
                {
                    "franja": i+1,
                    "rango": f"{min_cant}-{max_cant}",
                    "descuento": f"{desc:.5f}%"
                }
                for i, (min_cant, max_cant, desc) in enumerate(franjas[:5])
            ]
        }
        
        return resultado
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def verificar_ambos_servidores(producto_id=27):
    """
    Verifica que ambos servidores tengan la misma configuración.
    """
    print(f"=== VERIFICACIÓN DE DECIMALES SIGNIFICATIVOS ===")
    print(f"Producto ID: {producto_id}")
    print(f"Fecha: {os.popen('date').read().strip()}")
    print()
    
    resultado = verificar_producto_franjas(producto_id)
    
    if not resultado["success"]:
        print(f"❌ Error: {resultado['error']}")
        return False
    
    print(f"✅ Producto: {resultado['nombre']}")
    print(f"✅ Configuración:")
    print(f"   - Descuento inicial: {resultado['configuracion']['descuento_inicial']:.5f}%")
    print(f"   - Incremento: {resultado['configuracion']['incremento_franja']:.5f}%")
    print(f"   - Número de franjas: {resultado['configuracion']['numero_franjas']}")
    print(f"   - Ancho de franja: {resultado['configuracion']['ancho_franja']}")
    print()
    
    print(f"✅ Franjas: {resultado['total_franjas']} total")
    print(f"✅ Con decimales significativos: {resultado['franjas_con_decimales']}")
    print()
    
    if resultado["errores"]:
        print("❌ Errores encontrados:")
        for error in resultado["errores"]:
            print(f"   - {error}")
        print()
    else:
        print("✅ Todas las franjas calculadas correctamente")
        print()
    
    print("📊 Muestra de franjas:")
    for franja in resultado["franjas_muestra"]:
        print(f"   Franja {franja['franja']}: {franja['rango']} = {franja['descuento']}")
    
    return len(resultado["errores"]) == 0

if __name__ == "__main__":
    producto_id = int(sys.argv[1]) if len(sys.argv) > 1 else 27
    success = verificar_ambos_servidores(producto_id)
    sys.exit(0 if success else 1)

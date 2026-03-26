#!/usr/bin/env python3
"""
Script para duplicar facturas de proveedores marcadas como recurrentes.
Se ejecuta mensualmente vía cron para crear las facturas del mes actual.

Uso:
    python3 batch_facturas_recurrentes.py [--mes YYYY-MM] [--dry-run]

Cron sugerido (día 1 de cada mes a las 06:00):
    0 6 1 * * cd /var/www/html && ./venv/bin/python scripts/batch_facturas_recurrentes.py >> logs/facturas_recurrentes.log 2>&1
"""

import sys
import os
import argparse
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Añadir path del proyecto
sys.path.insert(0, '/var/www/html')

from db_utils import get_db_connection
from logger_config import get_logger

logger = get_logger('batch_facturas_recurrentes')


def ensure_recurrencia_columns(conn):
    """Añade columnas de recurrencia a facturas_proveedores si no existen."""
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(facturas_proveedores)")
    columnas = [col[1] for col in cursor.fetchall()]
    
    columnas_nuevas = {
        'recurrente': 'INTEGER DEFAULT 0',
        'dia_recurrencia': 'INTEGER DEFAULT 1',
        'factura_origen_id': 'INTEGER',
        'ultima_generacion': 'DATE'
    }
    
    for col, tipo in columnas_nuevas.items():
        if col not in columnas:
            try:
                cursor.execute(f"ALTER TABLE facturas_proveedores ADD COLUMN {col} {tipo}")
                logger.info(f"Columna '{col}' añadida a facturas_proveedores")
            except Exception as e:
                logger.warning(f"No se pudo añadir columna {col}: {e}")
    
    conn.commit()


def obtener_facturas_recurrentes(conn):
    """Obtiene todas las facturas marcadas como recurrentes."""
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            fp.id, fp.empresa_id, fp.proveedor_id, fp.numero_factura,
            fp.base_imponible, fp.iva_porcentaje, fp.iva_importe, fp.total,
            fp.concepto, fp.notas, fp.dia_recurrencia, fp.ultima_generacion,
            p.nombre as proveedor_nombre, p.dias_pago
        FROM facturas_proveedores fp
        LEFT JOIN proveedores p ON fp.proveedor_id = p.id
        WHERE fp.recurrente = 1
        ORDER BY fp.proveedor_id, fp.id
    """)
    
    return [dict(row) for row in cursor.fetchall()]


def factura_ya_generada_este_mes(conn, factura_origen_id, mes_objetivo, proveedor_id=None, numero_factura_esperado=None):
    """
    Verifica si ya existe una factura generada para este mes.
    Comprueba múltiples criterios para evitar duplicados.
    """
    cursor = conn.cursor()
    
    # 1. Buscar por factura_origen_id (enlace directo)
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM facturas_proveedores
        WHERE factura_origen_id = ?
        AND strftime('%Y-%m', fecha_emision) = ?
    """, (factura_origen_id, mes_objetivo))
    
    result = cursor.fetchone()
    if result['count'] > 0:
        logger.debug(f"Duplicado detectado por factura_origen_id={factura_origen_id}")
        return True
    
    # 2. Buscar por número de factura esperado (REC-xxx-MMYYYY)
    if numero_factura_esperado:
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM facturas_proveedores
            WHERE numero_factura = ?
        """, (numero_factura_esperado,))
        
        result = cursor.fetchone()
        if result['count'] > 0:
            logger.debug(f"Duplicado detectado por numero_factura={numero_factura_esperado}")
            return True
    
    # 3. Buscar por proveedor + mes (respaldo adicional)
    if proveedor_id:
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM facturas_proveedores
            WHERE proveedor_id = ?
            AND factura_origen_id = ?
            AND strftime('%Y-%m', fecha_emision) = ?
        """, (proveedor_id, factura_origen_id, mes_objetivo))
        
        result = cursor.fetchone()
        if result['count'] > 0:
            logger.debug(f"Duplicado detectado por proveedor_id={proveedor_id} + mes")
            return True
    
    return False


def generar_numero_factura(conn, factura_original, mes_objetivo):
    """Genera un número de factura para la copia."""
    fecha_obj = datetime.strptime(mes_objetivo, '%Y-%m')
    mes_str = fecha_obj.strftime('%m%Y')
    
    # Formato: REC-{num_original}-{MMYYYY}
    num_base = factura_original.get('numero_factura', 'SIN-NUM')
    # Limpiar prefijo REC si ya existe
    if num_base.startswith('REC-'):
        partes = num_base.split('-')
        if len(partes) >= 2:
            num_base = partes[1]
    
    return f"REC-{num_base}-{mes_str}"


def duplicar_factura(conn, factura_original, mes_objetivo, dry_run=False):
    """
    Duplica una factura recurrente para el mes objetivo.
    
    Args:
        conn: Conexión a BD
        factura_original: Diccionario con datos de la factura original
        mes_objetivo: Mes en formato YYYY-MM
        dry_run: Si True, no inserta, solo muestra qué haría
    
    Returns:
        int: ID de la nueva factura o None si dry_run
    """
    cursor = conn.cursor()
    
    # Calcular fechas
    fecha_obj = datetime.strptime(mes_objetivo, '%Y-%m')
    dia = factura_original.get('dia_recurrencia') or 1
    
    # Ajustar día si excede días del mes
    ultimo_dia_mes = (fecha_obj + relativedelta(months=1) - timedelta(days=1)).day
    dia = min(dia, ultimo_dia_mes)
    
    fecha_emision = fecha_obj.replace(day=dia).strftime('%Y-%m-%d')
    
    # Calcular vencimiento
    dias_pago = factura_original.get('dias_pago') or 30
    fecha_vencimiento = (datetime.strptime(fecha_emision, '%Y-%m-%d') + 
                        timedelta(days=dias_pago)).strftime('%Y-%m-%d')
    
    # Calcular trimestre
    mes = fecha_obj.month
    año = fecha_obj.year
    trimestre = f"Q{(mes - 1) // 3 + 1}"
    
    # Generar número de factura
    numero_factura = generar_numero_factura(conn, factura_original, mes_objetivo)
    
    # Concepto con indicador de recurrencia
    concepto = factura_original.get('concepto') or ''
    if not concepto:
        concepto = f"Factura recurrente - {factura_original.get('proveedor_nombre', 'Proveedor')}"
    
    if dry_run:
        logger.info(f"[DRY-RUN] Generaría factura:")
        logger.info(f"  - Proveedor: {factura_original.get('proveedor_nombre')}")
        logger.info(f"  - Número: {numero_factura}")
        logger.info(f"  - Fecha: {fecha_emision}")
        logger.info(f"  - Total: {factura_original.get('total')}€")
        return None
    
    # Insertar nueva factura
    cursor.execute("""
        INSERT INTO facturas_proveedores (
            empresa_id, proveedor_id, numero_factura,
            fecha_emision, fecha_vencimiento, fecha_pago,
            base_imponible, iva_porcentaje, iva_importe, total,
            estado, concepto, notas,
            trimestre, año,
            factura_origen_id, recurrente,
            usuario_alta
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
    """, (
        factura_original['empresa_id'],
        factura_original['proveedor_id'],
        numero_factura,
        fecha_emision,
        fecha_vencimiento,
        fecha_emision,
        factura_original['base_imponible'],
        factura_original['iva_porcentaje'],
        factura_original['iva_importe'],
        factura_original['total'],
        'pagada',
        concepto,
        factura_original.get('notas') or '',
        trimestre,
        año,
        factura_original['id'],
        'sistema_recurrente'
    ))
    
    nueva_factura_id = cursor.lastrowid
    
    # Crear gasto asociado
    cursor.execute("""
        INSERT INTO gastos (
            fecha_operacion, fecha_valor, concepto, 
            importe_eur, ejercicio, razon_social, 
            factura_proveedor_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        fecha_emision,
        fecha_emision,
        concepto,
        -abs(factura_original['total']),  # Negativo porque es gasto
        año,
        factura_original.get('proveedor_nombre', 'Proveedor'),
        nueva_factura_id
    ))
    
    logger.info(f"  └─ Gasto creado: -{factura_original['total']}€")
    
    # Actualizar última generación en factura original
    cursor.execute("""
        UPDATE facturas_proveedores 
        SET ultima_generacion = ?
        WHERE id = ?
    """, (fecha_emision, factura_original['id']))
    
    logger.info(f"✓ Factura {numero_factura} generada (ID: {nueva_factura_id}) - {factura_original.get('proveedor_nombre')} - {factura_original['total']}€")
    
    return nueva_factura_id


def procesar_facturas_recurrentes(mes_objetivo=None, dry_run=False):
    """
    Procesa todas las facturas recurrentes y genera copias para el mes objetivo.
    
    Args:
        mes_objetivo: Mes en formato YYYY-MM (default: mes actual)
        dry_run: Si True, solo muestra qué haría sin ejecutar
    
    Returns:
        dict: Resumen del proceso
    """
    if not mes_objetivo:
        # Por defecto, generar para el MES ACTUAL
        # (el proceso se ejecuta el día 1 del mes, genera facturas de ese mes)
        mes_objetivo = datetime.now().strftime('%Y-%m')
    
    logger.info(f"{'[DRY-RUN] ' if dry_run else ''}Procesando facturas recurrentes para {mes_objetivo}")
    
    conn = get_db_connection()
    
    try:
        # Asegurar que existen las columnas necesarias
        ensure_recurrencia_columns(conn)
        
        # Obtener facturas recurrentes
        facturas = obtener_facturas_recurrentes(conn)
        
        if not facturas:
            logger.info("No hay facturas marcadas como recurrentes")
            return {'procesadas': 0, 'generadas': 0, 'omitidas': 0, 'errores': 0}
        
        logger.info(f"Encontradas {len(facturas)} facturas recurrentes")
        
        resultados = {
            'procesadas': 0,
            'generadas': 0,
            'omitidas': 0,
            'errores': 0,
            'detalles': []
        }
        
        for factura in facturas:
            resultados['procesadas'] += 1
            
            try:
                # Generar número de factura esperado para verificación
                numero_esperado = generar_numero_factura(conn, factura, mes_objetivo)
                
                # Verificar si ya se generó este mes (múltiples criterios)
                if factura_ya_generada_este_mes(
                    conn, 
                    factura['id'], 
                    mes_objetivo,
                    proveedor_id=factura.get('proveedor_id'),
                    numero_factura_esperado=numero_esperado
                ):
                    logger.info(f"⏭ Factura {factura['numero_factura']} ya generada para {mes_objetivo}")
                    resultados['omitidas'] += 1
                    continue
                
                # Duplicar factura
                nueva_id = duplicar_factura(conn, factura, mes_objetivo, dry_run)
                
                if not dry_run:
                    resultados['generadas'] += 1
                    resultados['detalles'].append({
                        'origen_id': factura['id'],
                        'nueva_id': nueva_id,
                        'proveedor': factura.get('proveedor_nombre'),
                        'total': factura['total']
                    })
                else:
                    resultados['generadas'] += 1
                    
            except Exception as e:
                logger.error(f"✗ Error procesando factura {factura['id']}: {e}")
                resultados['errores'] += 1
        
        if not dry_run:
            conn.commit()
        
        logger.info(f"Resumen: {resultados['generadas']} generadas, {resultados['omitidas']} omitidas, {resultados['errores']} errores")
        
        return resultados
        
    except Exception as e:
        logger.error(f"Error en proceso de facturas recurrentes: {e}", exc_info=True)
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Genera facturas recurrentes mensuales')
    parser.add_argument('--mes', type=str, help='Mes objetivo en formato YYYY-MM (default: mes actual)')
    parser.add_argument('--dry-run', action='store_true', help='Simular sin crear facturas')
    
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"GENERACIÓN DE FACTURAS RECURRENTES")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    try:
        resultados = procesar_facturas_recurrentes(
            mes_objetivo=args.mes,
            dry_run=args.dry_run
        )
        
        print(f"\n{'='*60}")
        print(f"RESUMEN:")
        print(f"  - Facturas procesadas: {resultados['procesadas']}")
        print(f"  - Facturas generadas:  {resultados['generadas']}")
        print(f"  - Facturas omitidas:   {resultados['omitidas']}")
        print(f"  - Errores:             {resultados['errores']}")
        print(f"{'='*60}\n")
        
        return 0 if resultados['errores'] == 0 else 1
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())

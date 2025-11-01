#!/usr/bin/env python3

import os
import csv
import logging
import sqlite3
from db_utils import get_db_connection
from datetime import datetime
from pathlib import Path
from notificaciones_utils import guardar_notificacion

# Configuración
# Permitir configurar la ruta del CSV por variable de entorno para compatibilidad con www-data
# Por defecto, usar el punto de montaje CIFS
CSV_BASE_PATH = os.getenv("CSV_BASE_PATH", "/mnt/swapbatch")
ID_CONTACTO = 732
DB_NAME = "/var/www/html/db/aleph70.db"  # Ajustar según tu configuración
LOG_DIR = Path("/var/www/html/logs")
LOG_FILE = LOG_DIR / "batchPol.log"

# Configuración de tarifas
TARIFA_NORMAL = 0.22314
TARIFA_MATE = 0.7438
IVA = 21

# Configurar logging
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def redondear_importe(valor, decimales=2):
    """Redondea un valor a 2 decimales"""
    return round(float(valor), decimales)

def formatear_numero_documento(tipo, conn):
    """Genera el siguiente número de documento secuencial"""
    cursor = conn.cursor()
    cursor.execute("SELECT numerador FROM numerador WHERE tipo = ?", (tipo,))
    resultado = cursor.fetchone()
    
    if not resultado:
        raise ValueError(f"No existe numerador para el tipo {tipo}")
    
    numero_actual = resultado['numerador']
    año_actual = datetime.now().year % 100
    numero_formateado = f"{tipo}{año_actual:02}{numero_actual:04}"
    
    cursor.execute(
        "UPDATE numerador SET numerador = ? WHERE tipo = ?",
        (numero_actual + 1, tipo)
    )
    
    return numero_formateado

def procesar_csv():
    """Procesa el archivo CSV y devuelve todas las líneas válidas"""
    try:
        nombre = f"impressions_summary_{datetime.now().strftime('%m%Y')}.csv"
        candidatos = [
            Path(CSV_BASE_PATH) / nombre,                 # Ruta configurada (preferente)
            Path("/mnt/swapbatch") / nombre,              # CIFS montado
            Path("/var/www/html/descargas") / nombre,     # Copia local accesible
            Path("/home/sami/swapBatch") / nombre,        # Ruta legacy
        ]
        archivo_csv = None
        for p in candidatos:
            try:
                if p.exists():
                    archivo_csv = p
                    break
            except PermissionError:
                continue
        if archivo_csv is None:
            raise FileNotFoundError("Archivo no localizado en rutas conocidas: " + ", ".join(str(x) for x in candidatos))
        logger.info(f"Usando CSV: {archivo_csv}")
        
        lineas_validas = []
        
        with open(archivo_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, 1):
                try:
                    paper_type = row.get('Paper_Type', '').strip().upper()
                    if paper_type not in ['NORMAL', 'MATE']:
                        continue
                    
                    raw_impressions = row.get('Impressions', '0').strip()
                    impressions = int(raw_impressions) if raw_impressions.isdigit() else 0
                    if impressions <= 0:
                        continue
                    
                    lineas_validas.append({
                        'tipo': paper_type,
                        'cantidad': impressions,
                        'fecha': row.get('Date', datetime.now().strftime('%d/%m/%Y')),
                        'zip_date': row.get('Zip_Date', ''),
                        'zip_filename': row.get('Zip_Filename', '')
                    })
                    
                except Exception as e:
                    logger.warning(f"Error línea {row_num}: {str(e)} - Contenido: {dict(row)}")
                    continue
        
        return lineas_validas
    
    except Exception as e:
        logger.error(f"Error procesando CSV: {str(e)}")
        raise

def generar_detalles_proforma(lineas):
    """Genera los detalles de proforma a partir de las líneas del CSV"""
    # Diccionario para agrupar por Zip_Filename, Paper_Type y Zip_Date
    agrupado = {}
    
    # Agrupar las líneas por los campos especificados
    for linea in lineas:
        try:
            tipo = linea['tipo']
            cantidad = linea['cantidad']
            fecha = linea['fecha']
            zip_date = linea.get('zip_date', '')
            zip_filename = linea.get('zip_filename', '')
            
            # Crear clave de agrupación (zip_filename, tipo, zip_date)
            clave = (zip_filename, tipo, zip_date)
            
            # Inicializar o actualizar el grupo
            if clave not in agrupado:
                agrupado[clave] = {
                    'tipo': tipo,
                    'cantidad': cantidad,
                    'fecha': fecha,
                    'zip_date': zip_date,
                    'zip_filename': zip_filename
                }
            else:
                # Sumar la cantidad a la existente
                agrupado[clave]['cantidad'] += cantidad
        
        except Exception as e:
            logger.error(f"Error agrupando línea: {str(e)}")
            continue
    
    # Generar detalles a partir de los grupos
    detalles = []
    
    for _, grupo in agrupado.items():
        try:
            tipo = grupo['tipo']
            cantidad = grupo['cantidad']
            fecha = grupo['fecha']
            zip_date = grupo.get('zip_date', '')
            zip_filename = grupo.get('zip_filename', '')
            
            if tipo == 'NORMAL':
                tarifa = TARIFA_NORMAL
                concepto = 'IMPRESION SRA3 COLOR'
                id_producto = 221
            elif tipo == 'MATE':
                tarifa = TARIFA_MATE
                concepto = 'IMPRESION A3 MATE PLASTIFICADO'
                id_producto = 222
            else:
                continue
            
            # Cálculo correcto: IVA desde bruto sin redondear
            bruto_raw = cantidad * tarifa  # SIN redondear
            iva = redondear_importe(bruto_raw * (IVA / 100))  # Redondear IVA
            total = redondear_importe(bruto_raw + iva)  # Total desde bruto sin redondear
            
            detalles.append({
                'concepto': concepto,
                'productoId': id_producto,
                'descripcion': f" {fecha} ({zip_filename})",
                'cantidad': cantidad,
                'precio': tarifa,
                'impuestos': IVA,
                'total': total,
                'formaPago': 'R',
                'fechaDetalle': datetime.now().strftime('%Y-%m-%d')
            })
            
        except Exception as e:
            logger.error(f"Error procesando grupo: {str(e)}")
            continue
    
    return detalles

def obtener_nif_contacto(conn):
    """Obtiene el NIF del contacto desde la base de datos"""
    try:
        contacto = conn.execute(
            'SELECT identificador FROM contactos WHERE idContacto = ?',
            (ID_CONTACTO,)
        ).fetchone()
        
        if not contacto:
            raise ValueError(f"Contacto con ID {ID_CONTACTO} no encontrado")
            
        nif = contacto['identificador']
        
        if not nif:
            raise ValueError(f"El contacto {ID_CONTACTO} no tiene NIF registrado")
            
        return nif
    
    except sqlite3.Error as e:
        raise RuntimeError(f"Error de base de datos: {str(e)}")

def crear_nueva_proforma(detalles, conn):
    """Crea una nueva proforma desde cero"""
    try:
        # Obtener el NIF del contacto
        nif = obtener_nif_contacto(conn)
        
        # Generar el siguiente número de proforma
        numero_proforma = formatear_numero_documento('P', conn)
        
        # Calcular el total de la proforma
        total = sum(d['total'] for d in detalles)
        
        with conn:
            cursor = conn.execute('''
                INSERT INTO proforma (
                    numero, fecha, estado, idContacto, nif, total,
                    importe_bruto, importe_impuestos, timestamp, tipo
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                numero_proforma,
                datetime.now().strftime('%Y-%m-%d'),
                'A',
                ID_CONTACTO,
                nif,
                redondear_importe(total),
                redondear_importe(sum(d['cantidad'] * d['precio'] for d in detalles)),
                redondear_importe(total - sum(d['cantidad'] * d['precio'] for d in detalles)),
                datetime.now().isoformat(),
                'A'
            ))
            
            proforma_id = cursor.lastrowid
            
            for detalle in detalles:
                conn.execute('''
                    INSERT INTO detalle_proforma (
                        id_proforma, concepto, descripcion, cantidad,
                        precio, impuestos, total,formaPago,productoId, fechaDetalle
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    proforma_id,
                    detalle['concepto'],
                    detalle['descripcion'],
                    detalle['cantidad'],
                    detalle['precio'],
                    detalle['impuestos'],
                    detalle['total'],   
                    detalle['formaPago'],
                    detalle['productoId'],
                    detalle['fechaDetalle']
                ))
            
        logger.info(f"Nueva proforma creada: {numero_proforma} (ID: {proforma_id})")
        return True
    
    except Exception as e:
        logger.error(f"Error creando proforma: {str(e)}")
        return False

def actualizar_proforma_existente(proforma_id, detalles, conn):
    """Actualiza una proforma existente con nuevos detalles"""
    try:
        with conn:
            # Obtenemos los detalles existentes para compararlos
            detalles_existentes = conn.execute('''
                SELECT concepto, descripcion, productoId 
                FROM detalle_proforma 
                WHERE id_proforma = ?
            ''', (proforma_id,)).fetchall()
            
            # Contador de detalles añadidos
            detalles_nuevos = 0
            
            # Insertamos solo los detalles que no existen ya
            for detalle in detalles:
                # Comprobamos si este detalle ya existe en la proforma
                detalle_existe = False
                for existente in detalles_existentes:
                    # Comparamos los campos clave que determinan la unicidad del detalle
                    # Es esencial verificar tanto concepto, descripción y productoId 
                    # La descripción contiene el zip_date que los diferencia
                    if (existente['concepto'] == detalle['concepto'] and 
                        existente['descripcion'] == detalle['descripcion'] and 
                        existente['productoId'] == detalle['productoId']):
                        detalle_existe = True
                        break
                        
                # Si el detalle no existe, lo insertamos
                if not detalle_existe:
                    conn.execute('''
                        INSERT INTO detalle_proforma (
                            id_proforma, concepto, descripcion, cantidad,
                            precio, impuestos, total, formaPago, productoId, fechaDetalle 
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        proforma_id,
                        detalle['concepto'],
                        detalle['descripcion'],
                        detalle['cantidad'],
                        detalle['precio'],
                        detalle['impuestos'],
                        detalle['total'],
                        detalle['formaPago'],
                        detalle['productoId'],
                        detalle['fechaDetalle']
                    ))
                    detalles_nuevos += 1
            
            # Obtener todos los detalles para calcular los totales
            todos_detalles = conn.execute('''
                SELECT cantidad, precio, total FROM detalle_proforma 
                WHERE id_proforma = ?
            ''', (proforma_id,)).fetchall()
            
            total = sum(d['total'] for d in todos_detalles)
            importe_bruto = sum(d['cantidad'] * d['precio'] for d in todos_detalles)
            
            conn.execute('''
                UPDATE proforma SET
                    total = ?,
                    importe_bruto = ?,
                    importe_impuestos = ?,
                    timestamp = ?,
                    tipo = ?
                WHERE id = ?
            ''', (
                redondear_importe(total),
                redondear_importe(importe_bruto),
                redondear_importe(total - importe_bruto),
                datetime.now().isoformat(),
                'A',
                proforma_id
            ))
            
        logger.info(f"Proforma {proforma_id} actualizada correctamente con {detalles_nuevos} nuevos detalles de {len(detalles)} procesados")
        return True
    
    except Exception as e:
        logger.error(f"Error actualizando proforma: {str(e)}")
        return False

def main():
    """Función principal ejecutada por cron"""
    logger.info("Iniciando proceso de actualización de proforma")
    
    try:
        # Paso 1: Procesar CSV y obtener líneas válidas
        lineas_csv = procesar_csv()
        logger.info(f"Líneas CSV procesadas: {len(lineas_csv)} registros")
        
        # Paso 2: Generar detalles
        detalles = generar_detalles_proforma(lineas_csv)
        
        if not detalles:
            logger.warning("No hay detalles válidos para procesar")
            return 0
        
        logger.info(f"Detalles a insertar/actualizar: {len(detalles)} ítems")
        
        # Resto del código manteniendo la lógica de creación/actualización...
        
        # Paso 3: Procesar proforma
        with get_db_connection() as conn:
            proforma = conn.execute('''
                SELECT id, numero FROM proforma
                WHERE idContacto = ? AND estado = 'A'
                LIMIT 1
            ''', (ID_CONTACTO,)).fetchone()
            
            if proforma:
                logger.info(f"Proforma existente encontrada: {proforma['numero']}")
                if actualizar_proforma_existente(proforma['id'], detalles, conn):
                    guardar_notificacion(
                        f"Proforma {proforma['numero']} actualizada con {len(detalles)} items desde batchPol",
                        tipo='success',
                        db_path=DB_NAME
                    )
                    return 0
                return 1
            else:
                logger.info("No existe proforma activa, creando nueva")
                if crear_nueva_proforma(detalles, conn):
                    # Obtener el número de la proforma recién creada
                    nueva_proforma = conn.execute('''
                        SELECT numero FROM proforma
                        WHERE idContacto = ? AND estado = 'A'
                        ORDER BY id DESC LIMIT 1
                    ''', (ID_CONTACTO,)).fetchone()
                    if nueva_proforma:
                        guardar_notificacion(
                            f"Nueva proforma {nueva_proforma['numero']} creada con {len(detalles)} items desde batchPol",
                            tipo='success',
                            db_path=DB_NAME
                        )
                    return 0
                return 1
    
    except Exception as e:
        logger.error(f"Error crítico: {str(e)}", exc_info=True)
        return 2

if __name__ == "__main__":
    import sys
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.info("Proceso interrumpido por el usuario")
        sys.exit(3)
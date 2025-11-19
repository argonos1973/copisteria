#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo principal del sistema VERI*FACTU

Implementa la funcionalidad integrada del sistema VERI*FACTU
para generar, registrar y enviar facturas a AEAT
"""

import base64
import json
import os
from datetime import datetime

from .config import AEAT_CONFIG, VERIFACTU_CONSTANTS, logger
from .db.registro import (_ensure_column_exists, actualizar_factura_con_hash,
                          crear_registro_facturacion)
from .db.utils import get_db_connection, redondear_importe
from .hash.sha256 import generar_hash_factura, obtener_ultimo_hash
from .qr.generator import generar_qr_verifactu
from .soap.client import enviar_registro_aeat


def generar_datos_verifactu_para_factura(factura_id):
    """
    Flujo completo de VERI*FACTU para una factura:
    - Calcula hash encadenado
    - Almacena en registro de facturación
    - Genera código QR
    - Envía registro a la AEAT
    - Procesa respuesta
    
    Args:
        factura_id: ID de la factura
        
    Returns:
        dict: Datos VERI*FACTU para incluir en la factura (QR, etc)
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Obtener datos de la factura (sin dependencia de tabla empresa)
        cursor.execute('''
            SELECT f.id, f.numero, f.fecha, f.nif as nif_emisor, 
                   c.identificador as nif_receptor, 
                   f.total, f.importe_impuestos as cuota_impuestos,
                   f.hash_factura, r.id as registro_id
            FROM factura f
            LEFT JOIN contactos c ON f.idContacto = c.idContacto
            LEFT JOIN registro_facturacion r ON f.id = r.factura_id
            WHERE f.id = ?
        ''', (factura_id,))
        
        factura = cursor.fetchone()
        
        if not factura:
            logger.error(f"No se encontró la factura con ID {factura_id}")
            return {
                'success': False, 
                'mensaje': "No se encontró la factura"
            }
        
        # El NIF del emisor ahora viene directamente de la consulta a través de f.nif
        
        # 2. Calcular hash SHA-256 encadenado si no existe
        hash_factura = factura['hash_factura']
        
        if not hash_factura:
            # Obtener el hash de la factura anterior
            hash_anterior = obtener_ultimo_hash()
            
            # Generar contenido para hash (campos relevantes de la factura)
            contenido_hash = f"{factura['nif_emisor']}{factura['nif_receptor']}{factura['fecha']}{factura['numero']}{factura['total']}"
            
            # Calcular el nuevo hash
            hash_factura = generar_hash_factura(contenido_hash, hash_anterior)
            
            # Actualizar la factura con el hash calculado
            actualizar_factura_con_hash(factura_id, hash_factura)
        
        # 3. Verificar si ya existe registro de facturación
        if not factura['registro_id']:
            # Crear registro de facturación
            crear_registro_facturacion(
                factura_id=factura_id,
                nif_emisor=factura['nif_emisor'],
                nif_receptor=factura['nif_receptor'],
                fecha=factura['fecha'],
                total=factura['total'],
                hash_factura=hash_factura,
                qr_data=None,  # Se actualizará después
                numero_factura=factura['numero'],
                serie_factura="", # No hay columna serie en la tabla factura
                cuota_impuestos=factura['cuota_impuestos']
            )
        
        # 4. Inicializar variable QR (se generará después del envío a AEAT)
        qr_data = None
        csv_final = None
        
        # 6. Enviar registro a AEAT al entorno de pruebas y procesar respuesta
        logger.info(f"Enviando factura {factura_id} al web service de pruebas AEAT VERI*FACTU")
        
        # Inicializar resultado_envio para evitar UnboundLocalError
        resultado_envio = {'success': False, 'mensaje': 'No se ha realizado el envío'}
        
        try:
            resultado_envio = enviar_registro_aeat(factura_id)
            
            # Verificar si se recibió un CSV (código seguro verificación) de AEAT
            if resultado_envio.get('success'):
                logger.info(f"Factura {factura_id} enviada correctamente a AEAT")

                # --- Actualizar campos de envío en BD ---
                _ensure_column_exists('id_envio_aeat')
                _ensure_column_exists('fecha_envio')
                _ensure_column_exists('estado_envio')

                estado_envio_bd = 'ENVIADO'
                id_envio_aeat = resultado_envio.get('id_verificacion') or resultado_envio.get('id_envio_aeat')
                fecha_envio = datetime.now().isoformat()

                if True:

                    cursor.execute(
                        """
                        UPDATE registro_facturacion
                           SET estado_envio = ?,
                               id_envio_aeat = ?,
                               fecha_envio  = ?
                         WHERE factura_id  = ?
                        """,
                        (estado_envio_bd, id_envio_aeat, fecha_envio, factura_id)
                    )
                    conn.commit()
                
                # Si se recibió un CSV, actualizar el código QR para incluir el CSV en la URL de cotejo
                if resultado_envio.get('csv'):
                    csv = resultado_envio['csv']
                    logger.info(f"CSV recibido de AEAT: {csv}")
                    
                    # Formatear el total correctamente para el QR (2 decimales)
                    total_formateado = redondear_importe(factura['total'])
                    
                    # Generar nuevo código QR que incluya el CSV
                    nuevo_qr_data = generar_qr_verifactu(
                        nif=factura['nif_emisor'],
                        numero_factura=factura['numero'],
                        serie_factura="", # No hay columna serie en la tabla factura
                        fecha_factura=factura['fecha'],
                        total_factura=total_formateado,
                        csv=csv  # Añadir CSV al QR (el CSV es proporcionado por AEAT y se usa solo en el QR, no se guarda en la BD)
                    )
                    
                    if nuevo_qr_data:
                        # Actualizar QR y CSV en base de datos
                        qr_base64 = base64.b64encode(nuevo_qr_data).decode('utf-8') if nuevo_qr_data else None
                        
                        # Actualizar registro_facturacion con el nuevo QR y CSV
                        _ensure_column_exists('csv')
                        csv_final = csv
                        cursor.execute(
                            'UPDATE registro_facturacion SET codigo_qr = ?, csv = ?, estado_envio = ?, id_envio_aeat = ?, fecha_envio = ? WHERE factura_id = ?',
                            (qr_base64, csv_final, 'ENVIADO', id_envio_aeat or 'SIMULADO', datetime.now().isoformat(), factura_id)
                        )
                        conn.commit()
                        logger.info(f"Código QR actualizado con CSV para factura {factura_id}")
            else:
                # Error de AEAT - marcar como ERROR y guardar mensaje
                logger.error(f"Error al enviar factura {factura_id} a AEAT: {resultado_envio.get('mensaje')}")
                
                _ensure_column_exists('estado_envio')
                _ensure_column_exists('errores')
                _ensure_column_exists('fecha_envio')
                
                # Construir mensaje de error desde los errores devueltos
                mensaje_error = resultado_envio.get('mensaje', 'Error desconocido')
                if resultado_envio.get('errores'):
                    errores_str = ' | '.join([
                        f"{err.get('codigo', 'N/A')}: {err.get('descripcion', 'Sin descripción')}"
                        for err in resultado_envio['errores']
                    ])
                    mensaje_error = errores_str
                
                cursor.execute(
                    """
                    UPDATE registro_facturacion
                       SET estado_envio = 'ERROR',
                           errores = ?,
                           fecha_envio = ?,
                           enviado_aeat = 0
                     WHERE factura_id = ?
                    """,
                    (mensaje_error, datetime.now().isoformat(), factura_id)
                )
                conn.commit()
                logger.info(f"Estado ERROR registrado para factura {factura_id}")
                
        except Exception as e:
            logger.error(f"Error procesando respuesta AEAT: {e}")
            
            # Marcar como ERROR también en caso de excepción
            try:
                _ensure_column_exists('estado_envio')
                _ensure_column_exists('errores')
                cursor.execute(
                    """
                    UPDATE registro_facturacion
                       SET estado_envio = 'ERROR',
                           errores = ?
                     WHERE factura_id = ?
                    """,
                    (f"Excepción al procesar: {str(e)}", factura_id)
                )
                conn.commit()
            except Exception as e2:
                logger.error(f"No se pudo registrar el error: {e2}")
                        
#                         # Actualizar QR en la factura principal
#                         cursor.execute(


        # 7. Preparar respuesta con datos para mostrar en la factura
        respuesta = {
            'success': True,
            'datos': {
                'hash': hash_factura,
                'qr_data': base64.b64encode(qr_data).decode('utf-8') if qr_data else None,
                'csv': csv_final,
                'sello_tiempo': datetime.now().isoformat(),
                'leyenda': 'Factura verificable mediante código QR - VERI*FACTU',
                'url_verificacion': AEAT_CONFIG['url_cotejo'],
                'algoritmo_hash': VERIFACTU_CONSTANTS['algoritmo_hash']
            }
        }

        # Añadir información del envío a AEAT si existe
        if resultado_envio and resultado_envio.get('success'):
            respuesta['datos']['id_verificacion'] = resultado_envio.get('id_verificacion')
            respuesta['datos']['estado_envio'] = 'ENVIADO'
        else:
            respuesta['datos']['estado_envio'] = 'PENDIENTE'
            if resultado_envio:
                respuesta['datos']['mensaje_error'] = resultado_envio.get('mensaje')

        logger.info(f"Datos VERI*FACTU generados correctamente para factura ID {factura_id}")
        return respuesta

    except Exception as e:
        logger.error(f"Error al generar datos VERI*FACTU: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'mensaje': f"Error: {str(e)}"
        }
    finally:
        if conn:
            conn.close()
        
# ---------------------------------------------------------------------------

# (Función _ensure_tickets_table_exists eliminada – la tabla tickets ya existe)
    """Crea la tabla tickets si no existe.
    Solo con las columnas necesarias para el flujo VERI*FACTU de tickets.
    """
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT,
                numero TEXT,
                importe_bruto REAL,
                importe_impuestos REAL,
                importe_cobrado REAL,
                total REAL,
                timestamp TEXT,
                estado TEXT,
                formaPago TEXT
            )
        """)
        conn.commit()
    except Exception as exc:
        logger.error("No se pudo crear la tabla tickets: %s", exc)


def generar_datos_verifactu_para_ticket(ticket_id: int, push_notif=None, empresa_codigo=None):
    """Flujo VERI*FACTU adaptado a tickets.
    Genera hash encadenado, QR y crea registro en registro_facturacion con
    tipo_factura = 'F2'. Por ahora enviamos al servicio AEAT en modo test
    reutilizando la misma función enviar_registro_aeat, que aceptará ticket
    más adelante. De momento sólo generamos y guardamos los datos para poder
    imprimir el QR.
    """
    # Asegurar que EMPRESA_CODIGO esté en variables de entorno si se pasa
    if empresa_codigo:
        os.environ['EMPRESA_CODIGO'] = empresa_codigo
        logger.info(f"Estableciendo EMPRESA_CODIGO={empresa_codigo} para generación de ticket")
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener datos básicos del ticket
        cursor.execute(
            """
            SELECT id, numero, fecha, total, importe_bruto, importe_impuestos
            FROM tickets
            WHERE id = ?
            """,
            (ticket_id,)
        )
        ticket = cursor.fetchone()
        if not ticket:
            logger.error("No se encontró el ticket %s", ticket_id)
            return None

        # Cargar NIF y nombre del emisor desde configuración
        nif_emisor = ''
        nombre_emisor = ''
        try:
            from utils_emisor import cargar_datos_emisor
            datos_emisor = cargar_datos_emisor()
            nif_emisor = datos_emisor.get('nif', '')
            nombre_emisor = datos_emisor.get('nombre', '')
        except Exception as e:
            logger.warning(f"No se pudo cargar desde utils_emisor: {e}")
            # Fallback: cargar directamente desde JSON sin contexto Flask
            try:
                import json
                empresa_codigo = os.getenv('EMPRESA_CODIGO', 'default')
                emisor_path = f'/var/www/html/emisores/{empresa_codigo}_emisor.json'
                if os.path.exists(emisor_path):
                    with open(emisor_path, 'r', encoding='utf-8') as f:
                        datos_emisor = json.load(f)
                        nif_emisor = datos_emisor.get('nif', '')
                        nombre_emisor = datos_emisor.get('nombre', '')
                        logger.info(f"Datos emisor cargados desde {emisor_path}")
            except Exception as e_json:
                logger.warning(f"No se pudo cargar JSON directamente: {e_json}")

        # 1. Calcular hash encadenado (cadena común con facturas)
        hash_anterior = obtener_ultimo_hash()
        contenido_hash = f"{nif_emisor}{ticket['fecha']}{ticket['numero']}{ticket['total']}"
        hash_ticket = generar_hash_factura(contenido_hash, hash_anterior)

        # 2. Crear registro_facturacion
        crear_registro_facturacion(
            factura_id=ticket_id,
            ticket_id=ticket_id,
            nif_emisor=nif_emisor,
            nif_receptor=None,
            fecha=ticket['fecha'],
            total=ticket['total'],
            hash_factura=hash_ticket,
            qr_data=None,
            numero_factura=ticket['numero'],
            serie_factura='',
            tipo_factura='F2',
            cuota_impuestos=ticket['importe_impuestos'] or 0.0,
            estado_envio='PENDIENTE'
        )

        # 3. Enviar registro a AEAT antes de generar QR
        from verifactu.soap.ticket import enviar_registro_aeat_ticket
        resultado_envio = enviar_registro_aeat_ticket(ticket_id)
        csv_final = None
        id_envio_aeat = None

        if not resultado_envio.get('success'):
            logger.error("La AEAT devolvió error para el ticket %s: %s", ticket_id, resultado_envio.get('mensaje'))
            
            # Marcar como ERROR en la base de datos
            _ensure_column_exists('estado_envio')
            _ensure_column_exists('errores')
            _ensure_column_exists('fecha_envio')
            
            # Construir mensaje de error desde los errores devueltos
            mensaje_error = resultado_envio.get('mensaje', 'Error desconocido')
            if resultado_envio.get('errores'):
                errores_str = ' | '.join([
                    f"{err.get('codigo', 'N/A')}: {err.get('descripcion', 'Sin descripción')}"
                    for err in resultado_envio['errores']
                ])
                mensaje_error = errores_str
            
            cursor.execute(
                """
                UPDATE registro_facturacion
                   SET estado_envio = 'ERROR',
                       errores = ?,
                       fecha_envio = ?,
                       enviado_aeat = 0
                 WHERE factura_id = ?
                """,
                (mensaje_error, datetime.now().isoformat(), ticket_id)
            )
            conn.commit()
            logger.info(f"Estado ERROR registrado para ticket {ticket_id}")
            
            if push_notif:
                push_notif("Error AEAT en ticket", tipo='error', scope='ticket')
            # Devolver igualmente la respuesta para que el frontend la muestre
            return resultado_envio

        csv_final = resultado_envio.get('csv')
        id_envio_aeat = resultado_envio.get('id_verificacion') or 'SIMULADO'

        # Actualizar registro con CSV y estado enviado
        _ensure_column_exists('csv')
        _ensure_column_exists('estado_envio')
        _ensure_column_exists('id_envio_aeat')
        _ensure_column_exists('fecha_envio')
        cursor.execute(
            'UPDATE registro_facturacion SET csv = ?, estado_envio = ?, id_envio_aeat = ?, fecha_envio = ? WHERE factura_id = ?',
            (csv_final, 'ENVIADO', id_envio_aeat, datetime.now().isoformat(), ticket_id)
        )
        conn.commit()

        # 4. Generar QR con CSV recibido
        total_formateado = redondear_importe(ticket['total'])
        logger.info(f"Generando QR para ticket {ticket_id}: nif={nif_emisor}, numero={ticket['numero']}, fecha={ticket['fecha']}, total={total_formateado}, csv={csv_final}")
        qr_data = generar_qr_verifactu(
            nif=nif_emisor,
            numero_factura=ticket['numero'],
            serie_factura='',
            fecha_factura=ticket['fecha'],
            total_factura=total_formateado,
            csv=csv_final
        )
        if qr_data:
            qr_base64 = base64.b64encode(qr_data).decode('utf-8')
            _ensure_column_exists('codigo_qr', 'TEXT')
            _ensure_column_exists('estado_envio')
            _ensure_column_exists('id_envio_aeat')
            _ensure_column_exists('fecha_envio')
            cursor.execute(
                'UPDATE registro_facturacion SET codigo_qr = ?, estado_envio = ?, id_envio_aeat = ?, fecha_envio = ? WHERE factura_id = ?',
                (qr_base64, 'ENVIADO', id_envio_aeat, datetime.now().isoformat(), ticket_id)
            )
            conn.commit()

        # ------------------------------------------------------
        #  Generación de XML para tickets DESHABILITADA (requisito 2025-07)
        # ------------------------------------------------------
        if push_notif:
            push_notif("Ticket: Datos VERI*FACTU generados", scope='ticket')
        return {
            'qr_base64': qr_base64 if qr_data else None,
            'qr_data': qr_base64 if qr_data else None,
            'hash': hash_ticket
        }
        # ------------------------------------------------------
        #  **Código XML ORIGINAL (sin ejecutar por return temprano)**
        # ------------------------------------------------------
        ruta_xml_ticket = None
        try:
            from facturae.generador import \
                generar_facturae as generar_facturae_modular
            from utils_emisor import cargar_datos_emisor

            # Obtener detalles del ticket
            cursor.execute('SELECT concepto, descripcion, cantidad, precio, impuestos, total FROM detalle_tickets WHERE id_ticket = ?', (ticket_id,))
            det_rows = cursor.fetchall()
            det_cols = [d[0] for d in cursor.description]
            detalles_rows = [dict(zip(det_cols, r)) for r in det_rows]

            datos_facturae = {
                'emisor': cargar_datos_emisor(),
                'receptor': {
                    'nif': 'B00000000',
                    'nombre': 'CONSUMIDOR FINAL',
                    'direccion': '-',
                    'cp': '-',
                    'ciudad': '-',
                    'provincia': '-',
                    'pais': 'ESP'
                },
                'detalles': detalles_rows,
                'items': detalles_rows,
                'fecha': ticket['fecha'],
                'numero': ticket['numero'],
                'iva': 21.0,
                'base_amount': float(ticket['importe_bruto'] if 'importe_bruto' in ticket.keys() else 0),
                'taxes': float(ticket['importe_impuestos'] or 0),
                'total_amount': float(ticket['total'] or 0),
                'verifactu': True,
                'factura_id': ticket_id  # reuse field name even if it's ticket id
            }

            ruta_xml_ticket = generar_facturae_modular(datos_facturae)
            logger.info(f"[FACTURAE] XML generado para ticket {ticket_id}: {ruta_xml_ticket}")
        except Exception as xml_exc:
            logger.warning(f"No se pudo generar XML Facturae para ticket {ticket_id}: {xml_exc}")
            import traceback; traceback.print_exc()

        if push_notif:
            push_notif("Ticket: XML Facturae generado" if ruta_xml_ticket else "Ticket: Error al generar XML", scope='ticket')

        return {
            'qr_base64': qr_base64 if qr_data else None,
            'qr_data': qr_base64 if qr_data else None,
            'hash': hash_ticket,
                'xml_facturae': ruta_xml_ticket
        }
    except Exception as exc:
        logger.error("Error en generar_datos_verifactu_para_ticket: %s", exc)
        if push_notif:
            push_notif("Error VERI*FACTU en ticket", tipo='error', scope='ticket')
        return None
    finally:
        if conn:
            conn.close()
""" Duplicated legacy block kept for reference
#                             'UPDATE factura SET qr_code = ? WHERE id = ?',
#                             (qr_base64, csv_final, 'ENVIADO', id_envio_aeat or 'SIMULADO', datetime.now().isoformat(), factura_id)
#                         )
#                         conn.commit()
                        
                        # También actualizar QR en la respuesta
                        qr_data = nuevo_qr_data
                else:
                    # Respuesta exitosa pero sin CSV (entorno de pruebas). Simulamos un CSV con datos de la factura
                    total_formateado = redondear_importe(factura['total'])

                    csv_simulado = hashlib.sha256(
                        f"{factura['nif_emisor']}{factura['numero']}{factura['fecha']}{total_formateado}".encode('utf-8')
                    ).hexdigest()[:20].upper()
                    logger.info(f"CSV simulado generado: {csv_simulado}")

                    qr_data = generar_qr_verifactu(
                        nif=factura['nif_emisor'],
                        numero_factura=factura['numero'],
                        serie_factura="",
                        fecha_factura=factura['fecha'],
                        total_factura=total_formateado,
                        csv=csv_simulado
                    )
                    if qr_data:
                        qr_base64 = base64.b64encode(qr_data).decode('utf-8')
                        _ensure_column_exists('csv')
                        csv_final = csv_simulado
                        cursor.execute(
                            'UPDATE registro_facturacion SET codigo_qr = ?, csv = ?, estado_envio = ?, id_envio_aeat = ?, fecha_envio = ? WHERE factura_id = ?',
                            (qr_base64, csv_final, 'ENVIADO', id_envio_aeat or 'SIMULADO', datetime.now().isoformat(), factura_id)
                        )
                        conn.commit()
                        logger.info(f"Código QR generado con CSV simulado para factura {factura_id}")
                    else:
                        logger.warning(f"No se pudo generar QR con CSV simulado para factura {factura_id}")
            else:
                # Registrar estado de error en la BD
                _ensure_column_exists('estado_envio')
                _ensure_column_exists('errores')
                errores_json = json.dumps(resultado_envio.get('errores')) if resultado_envio.get('errores') else None
                cursor.execute(
                    'UPDATE registro_facturacion SET estado_envio = ?, errores = ? WHERE factura_id = ?',
                    ('ERROR', errores_json, factura_id)
                )
                conn.commit()
                logger.error(f"Error en envío a AEAT: {resultado_envio.get('errores') or resultado_envio.get('estado_envio')}")
                # Respuesta inmediata al frontend con error, sin datos VERI*FACTU
                return {
                    'success': False,
                    'errores': resultado_envio.get('errores'),
                    'estado_envio': resultado_envio.get('estado_envio') or 'ERROR',
                    'mensaje': 'Error devuelto por AEAT, la factura no es VERI*FACTU'
                }
        except Exception as e:
            logger.error(f"Error al procesar respuesta AEAT: {e}")
            # Continuar con la ejecución para al menos devolver el QR sin CSV
        
        # 7. Preparar respuesta con datos para mostrar en la factura
        respuesta = {
            'success': True,
            'datos': {
                'hash': hash_factura,
                'qr_data': base64.b64encode(qr_data).decode('utf-8') if qr_data else None,
                'csv': csv_final,
                'sello_tiempo': datetime.now().isoformat(),
                'leyenda': 'Factura verificable mediante código QR - VERI*FACTU',
                'url_verificacion': AEAT_CONFIG['url_cotejo'],
                'algoritmo_hash': VERIFACTU_CONSTANTS['algoritmo_hash']
            }
        }
        
        # Añadir información del envío a AEAT si existe
        if resultado_envio and resultado_envio.get('success'):
            respuesta['datos']['id_verificacion'] = resultado_envio.get('id_verificacion')
            respuesta['datos']['estado_envio'] = 'ENVIADO'
        else:
            respuesta['datos']['estado_envio'] = 'PENDIENTE'
            if resultado_envio:
                respuesta['datos']['mensaje_error'] = resultado_envio.get('mensaje')
        
        logger.info(f"Datos VERI*FACTU generados correctamente para factura ID {factura_id}")
        return respuesta
        
    except Exception as e:
        logger.error(f"Error al generar datos VERI*FACTU: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'mensaje': f"Error: {str(e)}"
        }
        
    finally:
        if conn:
            conn.close()



"""

def verificar_estado_registro_aeat(factura_id):
    """
    Verifica el estado de registro en AEAT para una factura.
    
    Args:
        factura_id: ID de la factura
        
    Returns:
        dict: Información sobre el estado del registro
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener estado actual
        cursor.execute('''
            SELECT estado_envio, id_envio_aeat, fecha_envio, respuesta_aeat 
            FROM registro_facturacion 
            WHERE factura_id = ?
        ''', (factura_id,))
        
        registro = cursor.fetchone()
        
        if not registro:
            return {
                'success': False,
                'mensaje': 'No existe registro de facturación para esta factura'
            }
            
        # Preparar respuesta
        datos_estado = {
            'estado': registro['estado_envio'],
            'id_verificacion': registro['id_envio_aeat'],
            'fecha_envio': registro['fecha_envio']
        }
        
        # Añadir detalles de la respuesta si existen
        if registro['respuesta_aeat']:
            try:
                datos_estado['respuesta'] = json.loads(registro['respuesta_aeat'])
            except:
                datos_estado['respuesta'] = registro['respuesta_aeat']
        
        return {
            'success': True,
            'datos': datos_estado
        }
        
    except Exception as e:
        logger.error(f"Error al verificar estado de registro: {e}")
        return {
            'success': False,
            'mensaje': f"Error: {str(e)}"
        }
        
    finally:
        if conn:
            conn.close()

#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import sqlite3
import sys
import os
from datetime import datetime, timedelta
from weasyprint import HTML

from constantes import *
from db_utils import get_db_connection
from notificaciones_utils import guardar_notificacion

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Salida a consola
    ]
)

logger = logging.getLogger('batchFacturasVencidas')

# Directorio para guardar las cartas de reclamación
CARTAS_DIR = '/var/www/html/cartas_reclamacion'

def generar_carta_reclamacion(factura_data, dias_vencidos):
    """
    Genera una carta de reclamación en PDF para una factura vencida
    
    Args:
        factura_data: Diccionario con los datos de la factura
        dias_vencidos: Número de días desde la emisión
    
    Returns:
        str: Ruta del archivo PDF generado o None si hay error
    """
    try:
        # Crear directorio si no existe
        os.makedirs(CARTAS_DIR, exist_ok=True)
        
        # Obtener datos del cliente
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.razonsocial as nombre, c.direccion, c.cp as codigoPostal, c.localidad as poblacion, c.mail as email
            FROM contactos c
            WHERE c.idContacto = ?
        ''', (factura_data['idContacto'],))
        
        cliente = cursor.fetchone()
        conn.close()
        
        if not cliente:
            logger.error(f"No se encontró el cliente para la factura {factura_data['numero']}")
            return None
        
        # Generar HTML de la carta
        html_content = f'''
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 40px;
                    line-height: 1.6;
                }}
                .header {{
                    text-align: right;
                    margin-bottom: 40px;
                }}
                .destinatario {{
                    margin-bottom: 40px;
                }}
                .contenido {{
                    text-align: justify;
                    margin-bottom: 30px;
                }}
                .firma {{
                    margin-top: 60px;
                }}
                .destacado {{
                    font-weight: bold;
                    color: #d32f2f;
                }}
                .footer {{
                    margin-top: 40px;
                    font-size: 12px;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <strong>COPISTERIA ALEPH 70</strong><br>
                C/ Aleph 70, 3<br>
                08884 - Barcelona<br>
                Fecha: {datetime.now().strftime('%d/%m/%Y')}
            </div>
            
            <div class="destinatario">
                <strong>{cliente['nombre']}</strong><br>
                {cliente['direccion'] or ''}<br>
                {cliente['codigoPostal'] or ''} {cliente['poblacion'] or ''}
            </div>
            
            <div class="contenido">
                <p><strong>Asunto: Recordatorio de pago - Factura {factura_data['numero']}</strong></p>
                
                <p>Hola,</p>
                
                <p>Te escribimos para recordarte que tenemos pendiente el pago de la factura <strong>{factura_data['numero']}</strong> 
                del <strong>{datetime.strptime(factura_data['fecha'], '%Y-%m-%d').strftime('%d/%m/%Y')}</strong>, 
                por un importe de <strong>{factura_data['total']:.2f}€</strong>.</p>
                
                <p>Han pasado ya <span class="destacado">{dias_vencidos} días</span> desde que emitimos la factura 
                y todavía no hemos recibido el pago.</p>
                
                <p>Si ya has realizado el pago, por favor ignora este mensaje. Si no es así, te agradeceríamos 
                que pudieras hacerlo lo antes posible para mantener al día tu cuenta.</p>
                
                <p>Adjuntamos de nuevo la factura para que la tengas a mano.</p>
                
                <p>Si tienes cualquier duda o necesitas hablar con nosotros, no dudes en contactarnos.</p>
                
                <p>¡Gracias!</p>
            </div>
            
            <div class="firma">
                <p>Atentamente,</p>
                <p><strong>COPISTERIA ALEPH 70</strong></p>
            </div>
            
            <div class="footer">
                <p>Este documento es una comunicación privada y confidencial dirigida exclusivamente a su destinatario.</p>
            </div>
        </body>
        </html>
        '''
        
        # Generar PDF
        pdf_filename = f"carta_reclamacion_{factura_data['numero']}_{datetime.now().strftime('%Y%m%d')}.pdf"
        pdf_path = os.path.join(CARTAS_DIR, pdf_filename)
        
        HTML(string=html_content).write_pdf(pdf_path)
        logger.info(f"Carta de reclamación generada: {pdf_path}")
        
        return pdf_path
        
    except Exception as e:
        logger.error(f"Error al generar carta de reclamación para factura {factura_data['numero']}: {e}")
        return None

def enviar_email_reclamacion(factura_id, cliente_email, factura_numero, carta_pdf_path):
    """
    Envía email con la carta de reclamación y la factura usando enviar_factura_email
    
    Args:
        factura_id: ID de la factura
        cliente_email: Email del cliente
        factura_numero: Número de factura
        carta_pdf_path: Ruta de la carta de reclamación
    
    Returns:
        bool: True si se envía correctamente
    """
    try:
        # MODO PRUEBAS: Solo enviar a elssons@gmail.com
        email_destino = 'elssons@gmail.com'
        
        logger.info(f"Enviando email a {email_destino} (original: {cliente_email})")
        logger.info(f"  - Factura ID: {factura_id}")
        logger.info(f"  - Carta de reclamación: {carta_pdf_path}")
        
        # Usar la función de factura.py para enviar el email con el PDF de la factura
        from factura import enviar_factura_email
        
        # Enviar factura al email de pruebas con carta de reclamación adjunta
        resultado = enviar_factura_email(
            factura_id, 
            email_destino_override=email_destino, 
            return_dict=True,
            adjunto_adicional=carta_pdf_path
        )
        
        # Verificar si fue exitoso
        if resultado and resultado.get('success', False):
            logger.info(f"Email de factura enviado exitosamente a {email_destino}")
            
            # Generar notificación
            notif_mensaje = f"📧 Email enviado: Recordatorio factura {factura_numero} → {email_destino} (original: {cliente_email})"
            guardar_notificacion(
                notif_mensaje,
                tipo='success',
                db_path=DB_NAME
            )
            logger.info(f"Notificación de email generada para {factura_numero}")
            return True
        else:
            logger.error(f"Error al enviar email de factura {factura_numero}")
            guardar_notificacion(
                f"❌ Error al enviar email de factura {factura_numero}",
                tipo='error',
                db_path=DB_NAME
            )
            return False
        
    except Exception as e:
        logger.error(f"Error al enviar email de reclamación: {e}")
        guardar_notificacion(
            f"❌ Error al enviar email de factura {factura_numero}: {str(e)}",
            tipo='error',
            db_path=DB_NAME
        )
        return False

def actualizar_facturas_vencidas():
    """
    Busca facturas con fecha superior a 30 días y actualiza su estado a 'V' (Vencida)
    """
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("No se pudo establecer conexión con la base de datos")
            return
        
        cursor = conn.cursor()
        
        # Añadir campo fecha_ultima_carta si no existe
        try:
            cursor.execute("ALTER TABLE factura ADD COLUMN fecha_ultima_carta TEXT")
            conn.commit()
            logger.info("Campo fecha_ultima_carta añadido a la tabla factura")
        except sqlite3.OperationalError:
            # El campo ya existe
            pass
        
        # Calcular la fecha límite (hoy - 30 días)
        fecha_limite = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        fecha_limite_carta = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        logger.info(f"Buscando facturas anteriores a {fecha_limite}")
        
        # Obtener facturas pendientes con fecha anterior a fecha_limite
        # Y que no se les haya enviado carta en los últimos 30 días
        cursor.execute('''
            SELECT id, numero, fecha, estado, idContacto, total, fecha_ultima_carta
            FROM factura
            WHERE fecha < ? 
            AND estado = 'P'
            AND (fecha_ultima_carta IS NULL OR fecha_ultima_carta < ?)
        ''', (fecha_limite, fecha_limite_carta))
        
        facturas_vencidas = cursor.fetchall()
        facturas_actualizadas = 0
        cartas_generadas = 0
        
        if not facturas_vencidas:
            logger.info("No se encontraron facturas vencidas pendientes de pago")
            return
        
        logger.info(f"Se encontraron {len(facturas_vencidas)} facturas vencidas pendientes de pago")
        
        # Actualizar el estado de cada factura a 'V' (Vencida) y generar carta de reclamación
        for factura in facturas_vencidas:
            factura_id = factura['id']
            factura_numero = factura['numero']
            factura_fecha = factura['fecha']
            
            # Calcular días transcurridos
            fecha_emision = datetime.strptime(factura_fecha, '%Y-%m-%d')
            dias_vencidos = (datetime.now() - fecha_emision).days
            
            try:
                # Actualizar estado a Vencida
                cursor.execute('''
                    UPDATE factura
                    SET estado = 'V'
                    WHERE id = ?
                ''', (factura_id,))
                
                logger.info(f"Factura {factura_numero} (ID: {factura_id}) del {factura_fecha} actualizada a estado VENCIDA ({dias_vencidos} días)")
                facturas_actualizadas += 1
                
                # Generar carta de reclamación
                factura_dict = dict(factura)
                carta_pdf = generar_carta_reclamacion(factura_dict, dias_vencidos)
                
                if carta_pdf:
                    cartas_generadas += 1
                    
                    # Obtener datos del cliente para notificación y verificar facturación automática
                    cursor.execute('SELECT razonsocial, mail as email, facturacion_automatica FROM contactos WHERE idContacto = ?', (factura['idContacto'],))
                    cliente_row = cursor.fetchone()
                    cliente = dict(cliente_row) if cliente_row else None
                    cliente_nombre = cliente['razonsocial'] if cliente else 'Cliente desconocido'
                    
                    # Hacer commit antes de crear notificación para evitar bloqueo
                    conn.commit()
                    
                    # Generar notificación individual por carta generada
                    notif_mensaje = f"📄 Carta reclamación: Factura {factura_numero} - {cliente_nombre} - {factura['total']:.2f}€ ({dias_vencidos} días)"
                    
                    guardar_notificacion(
                        notif_mensaje,
                        tipo='warning',
                        db_path=DB_NAME
                    )
                    logger.info(f"Notificación generada para carta {factura_numero}")
                    
                    # Solo enviar email si el cliente tiene email Y facturación automática activada
                    if cliente and cliente['email']:
                        if cliente.get('facturacion_automatica', 0) == 1:
                            logger.info(f"Cliente con facturación automática activada - Enviando email")
                            # Enviar email usando la función de factura.py
                            enviar_email_reclamacion(
                                factura_id,
                                cliente['email'],
                                factura_numero,
                                carta_pdf
                            )
                            
                            # Actualizar fecha_ultima_carta para evitar reenvíos en 30 días
                            cursor.execute('''
                                UPDATE factura
                                SET fecha_ultima_carta = ?
                                WHERE id = ?
                            ''', (datetime.now().strftime('%Y-%m-%d'), factura_id))
                            conn.commit()
                            logger.info(f"Fecha de última carta actualizada para factura {factura_numero}")
                        else:
                            logger.info(f"Cliente sin facturación automática - Email NO enviado para factura {factura_numero}")
                    else:
                        logger.warning(f"Cliente sin email para factura {factura_numero}")
                
            except sqlite3.Error as e:
                logger.error(f"Error al actualizar la factura {factura_numero} (ID: {factura_id}): {e}")
        
        conn.commit()
        logger.info(f"Proceso completado. Facturas actualizadas a vencidas: {facturas_actualizadas}")
        logger.info(f"Cartas de reclamación generadas: {cartas_generadas}")
        
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
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
from batch_utils import load_batch_params

# Configurar logging
from logger_config import get_logger

logger = get_logger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Salida a consola
    ]
)

logger = logging.getLogger('batchFacturasVencidas')

# Directorio base para guardar las cartas de reclamación
CARTAS_BASE_DIR = '/var/www/html/cartas_reclamacion'

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
        # Obtener empresa_id de la factura
        empresa_id = factura_data.get('empresa_id', 'default')
        if not empresa_id or empresa_id == 'default':
            env_code = os.getenv('EMPRESA_CODE')
            if env_code:
                empresa_id = env_code
            else:
                env_db = os.getenv('EMPRESA_DB_PATH')
                if env_db:
                    try:
                        empresa_id = os.path.basename(os.path.dirname(env_db)) or 'default'
                    except Exception:
                        empresa_id = 'default'
        
        # Obtener año y mes actual
        now = datetime.now()
        year = now.strftime('%Y')
        month = now.strftime('%m')
        
        # Crear directorio específico para la empresa/año/mes
        cartas_dir = os.path.join(CARTAS_BASE_DIR, str(empresa_id), year, month)
        os.makedirs(cartas_dir, exist_ok=True)
        
        # Leer datos del emisor desde JSON
        import json
        try:
            with open('/var/www/html/emisor_config.json', 'r', encoding='utf-8') as f:
                emisor = json.load(f)
        except Exception as e:
            logger.error(f"Error al leer emisor_config.json: {e}")
            emisor = {
                'nombre': 'SAMUEL RODRIGUEZ MIQUEL',
                'direccion': 'LEGALITAT, 70',
                'cp': '08024',
                'ciudad': 'BARCELONA',
                'email': 'INFO@ALEPH70.COM'
            }
        
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
                <strong>{emisor['nombre']}</strong><br>
                {emisor['direccion']}<br>
                {emisor['cp']} - {emisor['ciudad']}<br>
                Email: {emisor['email']}<br>
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
                con vencimiento el <strong>{datetime.strptime((factura_data.get('fvencimiento') or factura_data['fecha']), '%Y-%m-%d').strftime('%d/%m/%Y')}</strong>,
                por un importe de <strong>{factura_data['total']:.2f}€</strong>.</p>
                
                <p>La factura lleva <span class="destacado">{dias_vencidos} {'día' if dias_vencidos == 1 else 'días'}</span> vencida 
                y todavía no hemos recibido el pago.</p>
                
                <p>Si ya has realizado el pago, por favor ignora este mensaje. Si no es así, te agradeceríamos 
                que pudieras hacerlo lo antes posible para mantener al día tu cuenta.</p>
                
                <p>Adjuntamos de nuevo la factura para que la tengas a mano.</p>
                
                <p>Si tienes cualquier duda o necesitas hablar con nosotros, no dudes en contactarnos.</p>
                
                <p>¡Gracias!</p>
            </div>
            
            <div class="firma">
                <p>Atentamente,</p>
                <p><strong>{emisor['nombre']}</strong></p>
            </div>
            
            <div class="footer">
                <p>Este documento es una comunicación privada y confidencial dirigida exclusivamente a su destinatario.</p>
            </div>
        </body>
        </html>
        '''
        
        # Generar PDF
        pdf_filename = f"carta_reclamacion_{factura_data['numero']}_{datetime.now().strftime('%Y%m%d')}.pdf"
        pdf_path = os.path.join(cartas_dir, pdf_filename)
        
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
        notif_db_path = os.getenv('EMPRESA_DB_PATH') or DB_NAME
        params = load_batch_params()
        email_override = (
            os.getenv('BATCH_EMAIL_OVERRIDE')
            or os.getenv('BATCH_EMAIL_TO')
            or (params.get('email_override') if isinstance(params, dict) else None)
            or (params.get('email_to') if isinstance(params, dict) else None)
        )
        disable_contact_emails = bool((params.get('disable_contact_emails') if isinstance(params, dict) else False))

        email_destino = email_override or cliente_email
        if disable_contact_emails and not email_override:
            logger.info(f"Email NO enviado (disable_contact_emails=1) para factura {factura_numero}")
            return False
        
        logger.info(f"Enviando email a {email_destino}")
        logger.info(f"  - Factura ID: {factura_id}")
        logger.info(f"  - Carta de reclamación: {carta_pdf_path}")
        
        # Usar la función de factura.py para enviar el email con el PDF de la factura
        from factura import enviar_factura_email
        
        # Enviar factura al email del cliente con carta de reclamación adjunta
        resultado = enviar_factura_email(
            factura_id, 
            email_destino_override=email_destino, 
            return_dict=True,
            adjunto_adicional=carta_pdf_path
        )
        
        # Verificar si fue exitoso
        if resultado and resultado.get('success', False):
            if email_override:
                logger.info(f"Email de factura enviado exitosamente (redirigido) a {email_destino}")
            else:
                logger.info(f"Email de factura enviado exitosamente a {email_destino}")
            
            # Generar notificación
            notif_mensaje = f"📧 Email enviado: Recordatorio factura {factura_numero} → {email_destino}"
            guardar_notificacion(
                notif_mensaje,
                tipo='success',
                db_path=notif_db_path
            )
            logger.info(f"Notificación de email generada para {factura_numero}")
            return True
        else:
            logger.error(f"Error al enviar email de factura {factura_numero}")
            guardar_notificacion(
                f"❌ Error al enviar email de factura {factura_numero}",
                tipo='error',
                db_path=notif_db_path
            )
            return False
        
    except Exception as e:
        logger.error(f"Error al enviar email de reclamación: {e}")
        guardar_notificacion(
            f"❌ Error al enviar email de factura {factura_numero}: {str(e)}",
            tipo='error',
            db_path=notif_db_path
        )
        return False

def actualizar_facturas_vencidas(dias_para_vencer: int = 15, dias_para_carta: int = 15):
    """
    Busca facturas con fecha superior a N días y actualiza su estado a 'V' (Vencida)
    """
    conn = None
    try:
        params = load_batch_params()
        email_override = (
            os.getenv('BATCH_EMAIL_OVERRIDE')
            or os.getenv('BATCH_EMAIL_TO')
            or (params.get('email_override') if isinstance(params, dict) else None)
            or (params.get('email_to') if isinstance(params, dict) else None)
        )
        conn = get_db_connection()
        if not conn:
            logger.error("No se pudo establecer conexión con la base de datos")
            return

        notif_db_path = os.getenv('EMPRESA_DB_PATH') or DB_NAME
        
        cursor = conn.cursor()
        
        # Añadir campo fecha_ultima_carta si no existe
        try:
            cursor.execute("ALTER TABLE factura ADD COLUMN fecha_ultima_carta TEXT")
            conn.commit()
            logger.info("Campo fecha_ultima_carta añadido a la tabla factura")
        except sqlite3.OperationalError:
            # El campo ya existe
            pass
        
        # Añadir campo carta_enviada si no existe
        try:
            cursor.execute("ALTER TABLE factura ADD COLUMN carta_enviada INTEGER DEFAULT 0")
            conn.commit()
            logger.info("Campo carta_enviada añadido a la tabla factura")
        except sqlite3.OperationalError:
            # El campo ya existe
            pass
        
        dias_para_vencer = 15 if dias_para_vencer is None else int(dias_para_vencer)
        dias_para_carta = 15 if dias_para_carta is None else int(dias_para_carta)
        if dias_para_vencer < 0:
            dias_para_vencer = 0
        if dias_para_carta < 0:
            dias_para_carta = 0

        fecha_hoy = datetime.now().strftime('%Y-%m-%d')
        # Para cambio P→V: solo si lleva >= dias_para_vencer días vencida
        fecha_limite_vencer = (datetime.now() - timedelta(days=dias_para_vencer)).strftime('%Y-%m-%d')
        # Para cartas: solo si lleva >= dias_para_carta días vencida
        fecha_limite_carta = (datetime.now() - timedelta(days=dias_para_carta)).strftime('%Y-%m-%d')
        logger.info(f"Buscando facturas vencidas antes de {fecha_hoy} (P→V si vencida >= {dias_para_vencer}d, carta si >= {dias_para_carta}d)")
        
        # 1. Facturas PENDIENTES con vencimiento >= dias_para_vencer días atrás, sin cobro
        cursor.execute('''
            SELECT id, numero, fecha, fvencimiento, estado, idContacto, total, fecha_ultima_carta, carta_enviada
            FROM factura
            WHERE estado = 'P'
            AND fvencimiento < ?
            AND total > 0
            AND (fechaCobro IS NULL OR fechaCobro = '')
            AND (importe_cobrado IS NULL OR importe_cobrado < total)
        ''', (fecha_limite_vencer,))
        
        facturas_pendientes = cursor.fetchall()
        
        # 2. Facturas VENCIDAS que necesitan recordatorio (>= dias_para_carta días desde fvencimiento, sin cobro)
        cursor.execute('''
            SELECT id, numero, fecha, fvencimiento, estado, idContacto, total, fecha_ultima_carta, carta_enviada
            FROM factura
            WHERE estado = 'V'
            AND fvencimiento < ?
            AND (fecha_ultima_carta IS NULL OR fecha_ultima_carta < ?)
            AND total > 0
            AND (fechaCobro IS NULL OR fechaCobro = '')
            AND (importe_cobrado IS NULL OR importe_cobrado < total)
        ''', (fecha_limite_carta, fecha_limite_carta))
        
        facturas_vencidas = cursor.fetchall()
        
        # Combinar ambas listas
        todas_facturas = list(facturas_pendientes) + list(facturas_vencidas)
        facturas_actualizadas = 0
        cartas_generadas = 0
        
        if not todas_facturas:
            logger.info("No se encontraron facturas para procesar")
            return
        
        logger.info(f"Facturas pendientes a vencer: {len(facturas_pendientes)}")
        logger.info(f"Facturas vencidas a recordar: {len(facturas_vencidas)}")
        logger.info(f"Total facturas a procesar: {len(todas_facturas)}")
        
        # Procesar cada factura
        for factura_row in todas_facturas:
            factura = dict(factura_row)  # Convertir sqlite3.Row a dict para usar .get()
            factura_id = factura['id']
            factura_numero = factura['numero']
            factura_fecha = factura['fecha']
            
            # Calcular días transcurridos desde la fecha de VENCIMIENTO (no emisión)
            fecha_vencimiento_str = factura.get('fvencimiento') or factura_fecha
            try:
                fecha_vencimiento = datetime.strptime(fecha_vencimiento_str, '%Y-%m-%d')
            except (ValueError, TypeError):
                # Fallback a fecha de emisión + 30 días si fvencimiento no es válida
                fecha_vencimiento = datetime.strptime(factura_fecha, '%Y-%m-%d') + timedelta(days=30)
            dias_vencidos = (datetime.now() - fecha_vencimiento).days
            
            try:
                # Actualizar estado a Vencida solo si está en Pendiente
                if factura['estado'] == 'P':
                    cursor.execute('''
                        UPDATE factura
                        SET estado = 'V'
                        WHERE id = ?
                    ''', (factura_id,))
                    logger.info(f"Factura {factura_numero} (ID: {factura_id}) del {factura_fecha} actualizada a estado VENCIDA ({dias_vencidos} días)")
                    facturas_actualizadas += 1
                else:
                    logger.info(f"Factura {factura_numero} (ID: {factura_id}) ya está en estado {factura['estado']} - se envía carta de recordatorio")
                
                # Solo generar carta si lleva >= dias_para_carta días vencida
                debe_generar_carta = bool(fecha_vencimiento_str) and (fecha_vencimiento_str < fecha_limite_carta)
                if not debe_generar_carta:
                    logger.info(f"Factura {factura_numero}: no se genera carta (vencida hace {dias_vencidos}d, mínimo {dias_para_carta}d)")

                carta_pdf = None
                if debe_generar_carta:
                    carta_pdf = generar_carta_reclamacion(factura, dias_vencidos)
                
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
                        db_path=notif_db_path
                    )
                    logger.info(f"Notificación generada para carta {factura_numero}")
                    
                    # Actualizar fecha_ultima_carta SIEMPRE (aunque no se envíe email)
                    fecha_carta = datetime.now().strftime('%Y-%m-%d')
                    cursor.execute('''
                        UPDATE factura
                        SET fecha_ultima_carta = ?
                        WHERE id = ?
                    ''', (fecha_carta, factura_id))
                    conn.commit()
                    logger.info(f"Factura {factura_numero}: fecha_ultima_carta actualizada a {fecha_carta}")
                    
                    enviado_email = False
                    if email_override:
                        logger.info("Modo pruebas: email_override activo - Enviando email aunque el cliente no tenga facturación automática")
                        cliente_mail = (cliente.get('email') if cliente else None)
                        enviado_email = bool(enviar_email_reclamacion(
                            factura_id,
                            cliente_mail,
                            factura_numero,
                            carta_pdf
                        ))
                    else:
                        if cliente and cliente['email']:
                            if cliente.get('facturacion_automatica', 0) == 1:
                                logger.info(f"Cliente con facturación automática activada - Enviando email")
                                enviado_email = bool(enviar_email_reclamacion(
                                    factura_id,
                                    cliente['email'],
                                    factura_numero,
                                    carta_pdf
                                ))
                            else:
                                logger.info(f"Cliente sin facturación automática - Email NO enviado para factura {factura_numero}")
                        else:
                            logger.warning(f"Cliente sin email para factura {factura_numero}")

                    if enviado_email:
                        cursor.execute('''
                            UPDATE factura
                            SET carta_enviada = 1
                            WHERE id = ?
                        ''', (factura_id,))
                        conn.commit()
                
            except Exception as e:
                logger.error(f"Error al procesar la factura {factura_numero} (ID: {factura_id}): {e}")
        
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
        params = load_batch_params()
        dias_para_vencer = params.get('dias_para_vencer', 15)
        dias_para_carta = params.get('dias_para_carta', 30)
        actualizar_facturas_vencidas(dias_para_vencer=dias_para_vencer, dias_para_carta=dias_para_carta)
        logger.info("Proceso finalizado")
    except Exception as e:
        logger.error(f"Error en el proceso: {e}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
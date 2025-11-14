#!/usr/bin/env python3
"""
Sistema automático de procesamiento de contactos por email
Monitorea un buzón de correo y procesa imágenes adjuntas automáticamente

Flujo:
1. Conecta al buzón IMAP
2. Busca emails con asunto específico
3. Extrae imágenes adjuntas
4. Procesa con OCR (GPT-4 Vision)
5. Crea contacto en base de datos
6. Marca email como procesado
7. Envía confirmación
"""

import imaplib
import email
from email.header import decode_header
import os
import sys
import sqlite3
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Agregar directorio al path
sys.path.insert(0, '/var/www/html')

from logger_config import get_logger
import contacto_ocr

logger = get_logger(__name__)

# Configuración desde variables de entorno
# Usar las mismas credenciales SMTP que ya están configuradas
EMAIL_HOST = os.getenv('EMAIL_IMAP_HOST', 'imap.ionos.es')  # IONOS por defecto
EMAIL_PORT = int(os.getenv('EMAIL_IMAP_PORT', '993'))
EMAIL_USER = os.getenv('SMTP_USERNAME', os.getenv('EMAIL_USER'))
EMAIL_PASSWORD = os.getenv('SMTP_PASSWORD', os.getenv('EMAIL_PASSWORD'))
EMAIL_SMTP_HOST = os.getenv('SMTP_SERVER', os.getenv('EMAIL_SMTP_HOST', 'smtp.ionos.es'))
EMAIL_SMTP_PORT = int(os.getenv('SMTP_PORT', os.getenv('EMAIL_SMTP_PORT', '465')))

# Asunto a buscar
ASUNTO_BUSCAR = os.getenv('EMAIL_ASUNTO_CONTACTO', 'NUEVO CONTACTO')

# Base de datos
DB_PATH = '/var/www/html/gestion_copisteria.db'


def conectar_email():
    """Conecta al servidor IMAP"""
    try:
        logger.info(f"Conectando a {EMAIL_HOST}:{EMAIL_PORT}...")
        mail = imaplib.IMAP4_SSL(EMAIL_HOST, EMAIL_PORT)
        mail.login(EMAIL_USER, EMAIL_PASSWORD)
        logger.info("✓ Conexión exitosa al buzón")
        return mail
    except Exception as e:
        logger.error(f"Error conectando al email: {e}")
        return None


def buscar_emails_nuevos(mail):
    """Busca emails no leídos con el asunto específico"""
    try:
        mail.select('INBOX')
        
        # Buscar emails no leídos
        status, messages = mail.search(None, 'UNSEEN')
        
        if status != 'OK':
            logger.warning("No se pudo buscar emails")
            return []
        
        email_ids = messages[0].split()
        logger.info(f"Encontrados {len(email_ids)} emails no leídos")
        
        return email_ids
        
    except Exception as e:
        logger.error(f"Error buscando emails: {e}")
        return []


def extraer_adjuntos(msg):
    """Extrae imágenes adjuntas del email"""
    adjuntos = []
    
    try:
        for part in msg.walk():
            # Buscar adjuntos
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue
            
            filename = part.get_filename()
            
            # Verificar si es imagen
            content_type = part.get_content_type()
            if content_type and content_type.startswith('image/'):
                logger.info(f"Adjunto encontrado: {filename} ({content_type})")
                
                # Extraer bytes de la imagen
                imagen_bytes = part.get_payload(decode=True)
                adjuntos.append({
                    'filename': filename,
                    'content_type': content_type,
                    'data': imagen_bytes
                })
        
        return adjuntos
        
    except Exception as e:
        logger.error(f"Error extrayendo adjuntos: {e}")
        return []


def verificar_asunto(msg):
    """Verifica si el asunto coincide"""
    try:
        subject = msg.get('Subject', '')
        
        # Decodificar asunto si está codificado
        if subject:
            decoded = decode_header(subject)
            subject = ''
            for content, encoding in decoded:
                if isinstance(content, bytes):
                    subject += content.decode(encoding or 'utf-8', errors='ignore')
                else:
                    subject += content
        
        logger.info(f"Asunto del email: '{subject}'")
        
        # Verificar si contiene el asunto buscado
        return ASUNTO_BUSCAR.upper() in subject.upper()
        
    except Exception as e:
        logger.error(f"Error verificando asunto: {e}")
        return False


def crear_contacto_db(datos, empresa_id=1):
    """Crea el contacto en la base de datos"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Insertar contacto
        cursor.execute('''
            INSERT INTO contactos (
                empresa_id, razon_social, nif, direccion, cp, poblacion,
                telefono, email, nombre_contacto, fecha_alta, activo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ''', (
            empresa_id,
            datos.get('razon_social', ''),
            datos.get('nif', ''),
            datos.get('direccion', ''),
            datos.get('cp', ''),
            datos.get('poblacion', ''),
            datos.get('telefono', ''),
            datos.get('email', ''),
            datos.get('nombre_contacto', ''),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        contacto_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"✓ Contacto creado con ID: {contacto_id}")
        return contacto_id
        
    except Exception as e:
        logger.error(f"Error creando contacto en BD: {e}")
        return None


def enviar_confirmacion(destinatario, datos, contacto_id):
    """Envía email de confirmación al usuario"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = '✅ Contacto procesado automáticamente'
        msg['From'] = EMAIL_USER
        msg['To'] = destinatario
        
        # Crear HTML del email
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #2ecc71;">✅ Contacto procesado exitosamente</h2>
            <p>El contacto ha sido extraído y guardado automáticamente.</p>
            
            <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3>Datos extraídos:</h3>
                <table style="width: 100%;">
                    <tr><td><strong>ID:</strong></td><td>{contacto_id}</td></tr>
                    <tr><td><strong>Empresa:</strong></td><td>{datos.get('razon_social', '-')}</td></tr>
                    <tr><td><strong>NIF:</strong></td><td>{datos.get('nif', '-')}</td></tr>
                    <tr><td><strong>Contacto:</strong></td><td>{datos.get('nombre_contacto', '-')}</td></tr>
                    <tr><td><strong>Teléfono:</strong></td><td>{datos.get('telefono', '-')}</td></tr>
                    <tr><td><strong>Email:</strong></td><td>{datos.get('email', '-')}</td></tr>
                    <tr><td><strong>Dirección:</strong></td><td>{datos.get('direccion', '-')}</td></tr>
                    <tr><td><strong>CP:</strong></td><td>{datos.get('cp', '-')}</td></tr>
                    <tr><td><strong>Población:</strong></td><td>{datos.get('poblacion', '-')}</td></tr>
                    <tr><td><strong>Método:</strong></td><td>{datos.get('_metodo_ocr', 'OCR')}</td></tr>
                </table>
            </div>
            
            <p style="color: #7f8c8d; font-size: 12px;">
                <em>Procesado automáticamente por el sistema de gestión de contactos</em>
            </p>
        </body>
        </html>
        """
        
        part = MIMEText(html, 'html')
        msg.attach(part)
        
        # Enviar (usar SSL si puerto 465, STARTTLS si 587)
        import ssl
        if EMAIL_SMTP_PORT == 465:
            # Conexión SSL directa (IONOS, Gmail SSL)
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, context=context)
        else:
            # Conexión STARTTLS (Gmail, Outlook)
            server = smtplib.SMTP(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT)
            server.starttls()
        
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"✓ Email de confirmación enviado a {destinatario}")
        
    except Exception as e:
        logger.error(f"Error enviando confirmación: {e}")


def procesar_email_contacto(mail, email_id):
    """Procesa un email y crea el contacto"""
    try:
        # Obtener email
        status, msg_data = mail.fetch(email_id, '(RFC822)')
        
        if status != 'OK':
            logger.warning(f"No se pudo obtener email {email_id}")
            return False
        
        # Parsear email
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)
        
        # Verificar asunto
        if not verificar_asunto(msg):
            logger.info("Email no tiene el asunto correcto, ignorando")
            return False
        
        logger.info(f"✓ Email con asunto '{ASUNTO_BUSCAR}' encontrado")
        
        # Obtener remitente
        remitente = msg.get('From', '')
        logger.info(f"Remitente: {remitente}")
        
        # Extraer adjuntos
        adjuntos = extraer_adjuntos(msg)
        
        if not adjuntos:
            logger.warning("Email no tiene imágenes adjuntas")
            return False
        
        logger.info(f"✓ {len(adjuntos)} imagen(es) encontrada(s)")
        
        # Procesar cada imagen
        for adjunto in adjuntos:
            try:
                logger.info(f"Procesando: {adjunto['filename']}")
                
                # Procesar con OCR
                datos = contacto_ocr.procesar_imagen_contacto(adjunto['data'])
                
                # Verificar que se extrajeron datos
                if not any(v for k, v in datos.items() if k not in ['texto_completo', '_metodo_ocr']):
                    logger.warning("No se extrajeron datos útiles de la imagen")
                    continue
                
                logger.info(f"✓ Datos extraídos: {datos}")
                
                # Crear contacto en BD
                contacto_id = crear_contacto_db(datos)
                
                if contacto_id:
                    # Enviar confirmación
                    enviar_confirmacion(remitente, datos, contacto_id)
                    
                    logger.info(f"✅ Contacto procesado exitosamente (ID: {contacto_id})")
                    return True
                
            except Exception as e:
                logger.error(f"Error procesando imagen {adjunto['filename']}: {e}")
                continue
        
        return False
        
    except Exception as e:
        logger.error(f"Error procesando email {email_id}: {e}", exc_info=True)
        return False


def procesar_buzón():
    """Función principal que procesa el buzón"""
    try:
        # Verificar configuración
        if not EMAIL_USER or not EMAIL_PASSWORD:
            logger.error("Email no configurado. Configura EMAIL_USER y EMAIL_PASSWORD en .env")
            return
        
        logger.info("="*60)
        logger.info("INICIANDO PROCESAMIENTO DE EMAILS")
        logger.info(f"Buscando emails con asunto: '{ASUNTO_BUSCAR}'")
        logger.info("="*60)
        
        # Conectar
        mail = conectar_email()
        if not mail:
            return
        
        # Buscar emails nuevos
        email_ids = buscar_emails_nuevos(mail)
        
        if not email_ids:
            logger.info("No hay emails nuevos para procesar")
            mail.close()
            mail.logout()
            return
        
        # Procesar cada email
        procesados = 0
        for email_id in email_ids:
            if procesar_email_contacto(mail, email_id):
                procesados += 1
                # Marcar como leído
                mail.store(email_id, '+FLAGS', '\\Seen')
        
        logger.info(f"✅ Procesados {procesados} de {len(email_ids)} emails")
        
        # Cerrar conexión
        mail.close()
        mail.logout()
        
    except Exception as e:
        logger.error(f"Error en procesamiento de buzón: {e}", exc_info=True)


if __name__ == '__main__':
    procesar_buzón()

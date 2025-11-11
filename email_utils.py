import os
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header

from dotenv import load_dotenv
from logger_config import get_logger

# Inicializar logger
logger = get_logger(__name__)

load_dotenv()

def enviar_factura_por_email(destinatario, asunto, cuerpo, archivo_adjunto, numero_factura):
    server = None
    try:
        # Configurar el servidor SMTP
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.ionos.es')
        smtp_port = int(os.getenv('SMTP_PORT', '465'))
        smtp_username = os.getenv('SMTP_USERNAME', 'info@aleph70.com')
        smtp_password = os.getenv('SMTP_PASSWORD', 'Aleph7024*Sam')
        smtp_from = os.getenv('SMTP_FROM', 'info@aleph70.com')

        logger.info(f"Configurando servidor SMTP: {smtp_server}:{smtp_port}")
        
        # Crear el mensaje
        msg = MIMEMultipart()
        msg['From'] = smtp_from
        msg['To'] = destinatario
        # Asunto en UTF-8
        msg['Subject'] = str(Header(asunto, 'utf-8'))

        # Añadir el cuerpo del mensaje en UTF-8
        msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))

        # Adjuntar el archivo PDF
        with open(archivo_adjunto, 'rb') as f:
            pdf = MIMEApplication(f.read(), _subtype='pdf')
            pdf.add_header('Content-Disposition', 'attachment', 
                         filename=f'Factura_{numero_factura}.pdf')
            msg.attach(pdf)

        # Conectar al servidor SMTP con SSL
        logger.info("Creando conexión SMTP con SSL")
        context = ssl.create_default_context()
        server = smtplib.SMTP_SSL(smtp_server, smtp_port, context=context)

        logger.info("Iniciando sesión en el servidor SMTP")
        server.login(smtp_username, smtp_password)

        logger.info(f"Enviando correo a {destinatario}")
        # Añadir copia oculta a info@aleph70.com
        destinatarios = [destinatario, 'info@aleph70.com']  # Incluir el destinatario original y la copia oculta
        # Depuración: mostrar tipo y tamaño del mensaje
        try:
            from email import policy
            msg_bytes = msg.as_bytes(policy=policy.SMTP)
            logger.info(f"Tipo de mensaje: {type(msg_bytes)}, tamaño: {len(msg_bytes)} bytes")
            server.sendmail(smtp_from, destinatarios, msg_bytes)
        except Exception as send_err:
            logger.error(f"Error en server.sendmail: {send_err}", exc_info=True)
            raise
        
        logger.info("Cerrando conexión SMTP")
        server.quit()

        return True, "Correo enviado correctamente"
    except Exception as e:
        logger.error(f"Error al enviar correo: {str(e)}", exc_info=True)
        if server:
            try:
                server.quit()
            except Exception as e:
                logger.error(f"Error: {e}", exc_info=True)
                pass
        return False, f"Error al enviar el correo: {str(e)}"


def enviar_presupuesto_por_email(destinatario, asunto, cuerpo, archivo_adjunto, numero_presupuesto):
    """Envía un presupuesto por email con PDF adjunto"""
    server = None
    try:
        # Configurar el servidor SMTP
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.ionos.es')
        smtp_port = int(os.getenv('SMTP_PORT', '465'))
        smtp_username = os.getenv('SMTP_USERNAME', 'info@aleph70.com')
        smtp_password = os.getenv('SMTP_PASSWORD', 'Aleph7024*Sam')
        smtp_from = os.getenv('SMTP_FROM', 'info@aleph70.com')

        logger.info(f"Configurando servidor SMTP para presupuesto: {smtp_server}:{smtp_port}")
        
        # Crear el mensaje
        msg = MIMEMultipart()
        msg['From'] = smtp_from
        msg['To'] = destinatario
        msg['Subject'] = str(Header(asunto, 'utf-8'))

        # Añadir el cuerpo del mensaje en UTF-8
        msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))

        # Adjuntar el archivo PDF
        with open(archivo_adjunto, 'rb') as f:
            pdf = MIMEApplication(f.read(), _subtype='pdf')
            pdf.add_header('Content-Disposition', 'attachment', 
                         filename=f'Presupuesto_{numero_presupuesto}.pdf')
            msg.attach(pdf)

        # Conectar al servidor SMTP con SSL
        context = ssl.create_default_context()
        server = smtplib.SMTP_SSL(smtp_server, smtp_port, context=context)
        server.login(smtp_username, smtp_password)

        # Enviar email con copia oculta
        destinatarios = [destinatario, 'info@aleph70.com']
        
        from email import policy
        msg_bytes = msg.as_bytes(policy=policy.SMTP)
        server.sendmail(smtp_from, destinatarios, msg_bytes)
        server.quit()

        return True, "Presupuesto enviado correctamente por correo"
    except Exception as e:
        logger.error(f"Error al enviar presupuesto por correo: {str(e)}", exc_info=True)
        if server:
            try:
                server.quit()
            except Exception as e:
                logger.error(f"Error: {e}", exc_info=True)
                pass
        return False, f"Error al enviar el presupuesto por correo: {str(e)}"

def enviar_email_con_adjuntos(destinatario, asunto, cuerpo, archivos_adjuntos, nombres_adjuntos):
    """
    Envía un email con múltiples archivos adjuntos
    
    Args:
        destinatario: Email del destinatario
        asunto: Asunto del email
        cuerpo: Cuerpo del mensaje
        archivos_adjuntos: Lista de rutas de archivos a adjuntar
        nombres_adjuntos: Lista de nombres para los archivos adjuntos
    
    Returns:
        tuple: (bool éxito, str mensaje)
    """
    server = None
    try:
        # Configurar el servidor SMTP
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.ionos.es')
        smtp_port = int(os.getenv('SMTP_PORT', '465'))
        smtp_username = os.getenv('SMTP_USERNAME', 'info@aleph70.com')
        smtp_password = os.getenv('SMTP_PASSWORD', 'Aleph7024*Sam')
        smtp_from = os.getenv('SMTP_FROM', 'info@aleph70.com')

        logger.info(f"Configurando servidor SMTP: {smtp_server}:{smtp_port}")
        
        # Crear el mensaje
        msg = MIMEMultipart()
        msg['From'] = smtp_from
        msg['To'] = destinatario
        msg['Subject'] = str(Header(asunto, 'utf-8'))

        # Añadir el cuerpo del mensaje en UTF-8
        msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))

        # Adjuntar todos los archivos
        for archivo, nombre in zip(archivos_adjuntos, nombres_adjuntos):
            if archivo and os.path.exists(archivo):
                with open(archivo, 'rb') as f:
                    pdf = MIMEApplication(f.read(), _subtype='pdf')
                    pdf.add_header('Content-Disposition', 'attachment', filename=nombre)
                    msg.attach(pdf)

        # Conectar al servidor SMTP con SSL
        logger.info("Creando conexión SMTP con SSL")
        context = ssl.create_default_context()
        server = smtplib.SMTP_SSL(smtp_server, smtp_port, context=context)

        logger.info("Iniciando sesión en el servidor SMTP")
        server.login(smtp_username, smtp_password)

        logger.info(f"Enviando correo a {destinatario}")
        # Añadir copia oculta a info@aleph70.com
        destinatarios = [destinatario, 'info@aleph70.com']
        
        from email import policy
        msg_bytes = msg.as_bytes(policy=policy.SMTP)
        server.sendmail(smtp_from, destinatarios, msg_bytes)
        
        logger.info("Cerrando conexión SMTP")
        server.quit()

        return True, "Correo enviado correctamente"
    except Exception as e:
        logger.error(f"Error al enviar correo: {str(e)}", exc_info=True)
        if server:
            try:
                server.quit()
            except Exception as e:
                logger.error(f"Error: {e}", exc_info=True)
                pass
        return False, f"Error al enviar el correo: {str(e)}"

def enviar_email_bienvenida_empresa(destinatario, nombre_empresa, codigo_empresa, usuario_admin, password_admin):
    """
    Enviar email de bienvenida con las credenciales de acceso de la empresa creada
    """
    server = None
    try:
        # Configurar el servidor SMTP
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.ionos.es')
        smtp_port = int(os.getenv('SMTP_PORT', '465'))
        smtp_username = os.getenv('SMTP_USERNAME', 'info@aleph70.com')
        smtp_password = os.getenv('SMTP_PASSWORD', 'Aleph7024*Sam')
        smtp_from = os.getenv('SMTP_FROM', 'info@aleph70.com')

        logger.info(f"Enviando email de bienvenida a {destinatario} para empresa {nombre_empresa}")
        
        # Crear el mensaje
        msg = MIMEMultipart()
        msg['From'] = smtp_from
        msg['To'] = destinatario
        msg['Subject'] = str(Header(f'Bienvenido a {nombre_empresa} - Credenciales de Acceso', 'utf-8'))

        # Cuerpo del mensaje
        cuerpo = f"""
¡Bienvenido a {nombre_empresa}\!

Tu empresa ha sido creada exitosamente en nuestro sistema.

INFORMACIÓN DE LA EMPRESA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Nombre: {nombre_empresa}
• Código: {codigo_empresa}

CREDENCIALES DE ACCESO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Usuario: {usuario_admin}
• Contraseña: {password_admin}

IMPORTANTE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  Por seguridad, te recomendamos cambiar tu contraseña en el primer acceso.
⚠️  Guarda estas credenciales en un lugar seguro.

Puedes acceder al sistema en:
🔗 http://192.168.1.23:5001/LOGIN.html

Si tienes alguna pregunta o necesitas ayuda, no dudes en contactarnos.

¡Gracias por confiar en nosotros\!

Saludos,
El equipo de Aleph70
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        # Añadir el cuerpo del mensaje
        msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))

        # Conectar al servidor SMTP con SSL
        context = ssl.create_default_context()
        server = smtplib.SMTP_SSL(smtp_server, smtp_port, context=context)
        server.login(smtp_username, smtp_password)

        # Enviar email
        destinatarios = [destinatario, 'info@aleph70.com']  # Incluir copia a info@
        from email import policy
        msg_bytes = msg.as_bytes(policy=policy.SMTP)
        server.sendmail(smtp_from, destinatarios, msg_bytes)
        
        server.quit()
        logger.info(f"Email de bienvenida enviado correctamente a {destinatario}")
        return True, "Email enviado correctamente"
        
    except Exception as e:
        logger.error(f"Error al enviar email de bienvenida: {str(e)}", exc_info=True)
        if server:
            try:
                server.quit()
            except:
                pass
        return False, f"Error al enviar el correo: {str(e)}"

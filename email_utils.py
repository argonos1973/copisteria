import os
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header

from logger_config import get_logger

# Inicializar logger
logger = get_logger(__name__)

def _load_env_file_fallback(path: str):
    try:
        if not path or not os.path.exists(path):
            return
        with open(path, 'r', encoding='utf-8') as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass


try:
    from dotenv import load_dotenv  # type: ignore

    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        load_dotenv(dotenv_path=os.path.join(base_dir, '.env'))
    except Exception:
        pass
    try:
        load_dotenv()
    except Exception:
        pass
except Exception:
    # Sin python-dotenv: cargar .env manualmente para procesos batch
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        _load_env_file_fallback(os.path.join(base_dir, '.env'))
    except Exception:
        pass


def _get_smtp_config():
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.ionos.es')
    smtp_port = int(os.getenv('SMTP_PORT', '465'))
    smtp_username = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')
    smtp_from = os.getenv('SMTP_FROM')
    return {
        'smtp_server': smtp_server,
        'smtp_port': smtp_port,
        'smtp_username': smtp_username,
        'smtp_password': smtp_password,
        'smtp_from': smtp_from,
    }


def _build_plain_message(smtp_from, destinatario, asunto, cuerpo):
    msg = MIMEMultipart()
    msg['From'] = smtp_from
    msg['To'] = destinatario
    msg['Subject'] = str(Header(asunto, 'utf-8'))
    msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))
    return msg


def _build_alternative_message(smtp_from, destinatario, asunto):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = str(Header(asunto, 'utf-8'))
    msg['From'] = smtp_from
    msg['To'] = destinatario
    return msg


def _attach_pdf(msg, archivo_adjunto, nombre_adjunto):
    with open(archivo_adjunto, 'rb') as f:
        pdf = MIMEApplication(f.read(), _subtype='pdf')
        pdf.add_header('Content-Disposition', 'attachment', filename=nombre_adjunto)
        msg.attach(pdf)


def _send_smtp_message(cfg, msg, destinatarios):
    if not cfg.get('smtp_username') or not cfg.get('smtp_password') or not cfg.get('smtp_from'):
        raise RuntimeError('Configuración SMTP incompleta (SMTP_USERNAME/SMTP_PASSWORD/SMTP_FROM)')

    context = ssl.create_default_context()

    def _send_with(port: int, use_ssl: bool):
        server = None
        try:
            if use_ssl:
                server = smtplib.SMTP_SSL(cfg['smtp_server'], port, context=context, timeout=20)
            else:
                server = smtplib.SMTP(cfg['smtp_server'], port, timeout=20)
                server.starttls(context=context)
            server.login(cfg['smtp_username'], cfg['smtp_password'])
            from email import policy
            msg_bytes = msg.as_bytes(policy=policy.SMTP)

            redirect_to = (os.getenv('SMTP_REDIRECT_ALL_TO') or '').strip()
            if redirect_to:
                logger.warning(f"Interceptando envío a {destinatarios}. Redirigiendo a {redirect_to}")
                send_to = [redirect_to]
            else:
                send_to = destinatarios

            server.sendmail(cfg['smtp_from'], send_to, msg_bytes)
            return True
        finally:
            if server:
                try:
                    server.quit()
                except Exception:
                    pass

    try:
        smtp_port = int(cfg['smtp_port'])
    except Exception:
        smtp_port = 465

    try:
        if smtp_port == 465:
            if _send_with(465, True):
                return
        else:
            if _send_with(smtp_port, False):
                return
    except ssl.SSLError as e:
        if smtp_port == 465 and 'UNEXPECTED_EOF_WHILE_READING' in str(e):
            logger.warning(f"Fallo SMTP SSL ({cfg['smtp_server']}:{smtp_port}): {e}. Reintentando con STARTTLS en 587")
            try:
                if _send_with(587, False):
                    return
            except Exception:
                pass
        raise

def enviar_factura_por_email(destinatario, asunto, cuerpo, archivo_adjunto, numero_factura):
    # Check if email is disabled on this server
    if os.getenv('SMTP_DISABLE') == 'true' or os.getenv('EMAIL_ENABLED') == 'false':
        logger.warning(f"[EMAIL DISABLED] Envío de emails desactivado en este servidor. Factura {numero_factura} no enviada.")
        return False, "Envío de emails desactivado en este servidor"
    
    try:
        cfg = _get_smtp_config()
        logger.info(f"Configurando servidor SMTP: {cfg['smtp_server']}:{cfg['smtp_port']}")

        msg = _build_plain_message(cfg['smtp_from'], destinatario, asunto, cuerpo)
        _attach_pdf(msg, archivo_adjunto, f'Factura_{numero_factura}.pdf')

        logger.info(f"Enviando correo a {destinatario}")
        destinatarios = [destinatario, 'info@aleph70.com']
        _send_smtp_message(cfg, msg, destinatarios)
        return True, "Correo enviado correctamente"
    except Exception as e:
        logger.error(f"Error al enviar correo: {str(e)}", exc_info=True)
        return False, f"Error al enviar el correo: {str(e)}"


def enviar_email_texto(destinatarios, asunto, cuerpo, html=False):
    # Check if email is disabled on this server
    if os.getenv('SMTP_DISABLE') == 'true' or os.getenv('EMAIL_ENABLED') == 'false':
        logger.warning(f"[EMAIL DISABLED] Envío de emails desactivado en este servidor. Email '{asunto}' no enviado.")
        return False, "Envío de emails desactivado en este servidor"
    
    try:
        cfg = _get_smtp_config()

        if isinstance(destinatarios, str):
            destinatarios_list = [destinatarios]
        else:
            destinatarios_list = [d for d in (destinatarios or []) if d]

        destinatarios_list = [d.strip() for d in destinatarios_list if str(d).strip()]
        if not destinatarios_list:
            return False, 'Destinatarios vacíos'

        msg = MIMEMultipart()
        msg['From'] = cfg.get('smtp_from')
        msg['To'] = ", ".join(destinatarios_list)
        msg['Subject'] = str(Header(asunto, 'utf-8'))
        content_type = 'html' if html else 'plain'
        msg.attach(MIMEText(cuerpo or '', content_type, 'utf-8'))

        _send_smtp_message(cfg, msg, destinatarios_list)
        return True, 'Correo enviado correctamente'
    except Exception as e:
        logger.error(f"Error al enviar correo: {str(e)}", exc_info=True)
        return False, f"Error al enviar el correo: {str(e)}"


def enviar_presupuesto_por_email(destinatario, asunto, cuerpo, archivo_adjunto, numero_presupuesto):
    """Envía un presupuesto por email con PDF adjunto"""
    # Check if email is disabled on this server
    if os.getenv('SMTP_DISABLE') == 'true' or os.getenv('EMAIL_ENABLED') == 'false':
        logger.warning(f"[EMAIL DISABLED] Envío de emails desactivado en este servidor. Presupuesto {numero_presupuesto} no enviado.")
        return False, "Envío de emails desactivado en este servidor"
    
    try:
        cfg = _get_smtp_config()
        logger.info(f"Configurando servidor SMTP para presupuesto: {cfg['smtp_server']}:{cfg['smtp_port']}")

        msg = _build_plain_message(cfg['smtp_from'], destinatario, asunto, cuerpo)
        _attach_pdf(msg, archivo_adjunto, f'Presupuesto_{numero_presupuesto}.pdf')

        destinatarios = [destinatario, 'info@aleph70.com']
        _send_smtp_message(cfg, msg, destinatarios)
        return True, "Presupuesto enviado correctamente por correo"
    except Exception as e:
        logger.error(f"Error al enviar presupuesto por correo: {str(e)}", exc_info=True)
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
    try:
        cfg = _get_smtp_config()
        logger.info(f"Configurando servidor SMTP: {cfg['smtp_server']}:{cfg['smtp_port']}")

        msg = _build_plain_message(cfg['smtp_from'], destinatario, asunto, cuerpo)

        # Adjuntar todos los archivos
        for archivo, nombre in zip(archivos_adjuntos, nombres_adjuntos):
            if archivo and os.path.exists(archivo):
                _attach_pdf(msg, archivo, nombre)

        logger.info(f"Enviando correo a {destinatario}")
        destinatarios = [destinatario, 'info@aleph70.com']
        _send_smtp_message(cfg, msg, destinatarios)
        return True, "Correo enviado correctamente"
    except Exception as e:
        logger.error(f"Error al enviar correo: {str(e)}", exc_info=True)
        return False, f"Error al enviar el correo: {str(e)}"

def enviar_email_bienvenida_empresa(destinatario, nombre_empresa, codigo_empresa, usuario_admin, password_admin):
    """
    Enviar email de bienvenida con las credenciales de acceso de la empresa creada
    """
    try:
        cfg = _get_smtp_config()

        logger.info(f"Enviando email de bienvenida a {destinatario} para empresa {nombre_empresa}")
        
        # Crear el mensaje
        msg = MIMEMultipart()
        msg['From'] = cfg['smtp_from']
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

        destinatarios = [destinatario, 'info@aleph70.com']
        _send_smtp_message(cfg, msg, destinatarios)
        logger.info(f"Email de bienvenida enviado correctamente a {destinatario}")
        return True, "Email enviado correctamente"
        
    except Exception as e:
        logger.error(f"Error al enviar email de bienvenida: {str(e)}", exc_info=True)
        return False, f"Error al enviar el correo: {str(e)}"

def enviar_email_recuperacion_password(destinatario, nombre_usuario, token, base_url):
    """
    Enviar email con enlace para recuperar contraseña
    """
    try:
        cfg = _get_smtp_config()

        # Crear el mensaje
        msg = _build_alternative_message(cfg['smtp_from'], destinatario, 'Recuperación de Contraseña - Aleph70')

        # URL de recuperación
        reset_url = f"{base_url}/reset-password?token={token}"

        # Cuerpo del email en HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f9f9f9;
                }}
                .header {{
                    background-color: #000;
                    color: #fff;
                    padding: 20px;
                    text-align: center;
                }}
                .content {{
                    background-color: #fff;
                    padding: 30px;
                    border-radius: 5px;
                    margin-top: 20px;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background-color: #000;
                    color: #fff !important;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 20px;
                    font-size: 12px;
                    color: #666;
                }}
                .warning {{
                    background-color: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 10px;
                    margin: 15px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Recuperación de Contraseña</h1>
                </div>
                <div class="content">
                    <p>Hola <strong>{nombre_usuario}</strong>,</p>
                    
                    <p>Hemos recibido una solicitud para restablecer la contraseña de tu cuenta en Aleph70.</p>
                    
                    <p>Para crear una nueva contraseña, haz clic en el siguiente botón:</p>
                    
                    <div style="text-align: center;">
                        <a href="{reset_url}" class="button">Restablecer Contraseña</a>
                    </div>
                    
                    <p>O copia y pega este enlace en tu navegador:</p>
                    <p style="word-break: break-all; background-color: #f5f5f5; padding: 10px; border-radius: 3px;">
                        {reset_url}
                    </p>
                    
                    <div class="warning">
                        <strong>⚠️ Importante:</strong>
                        <ul>
                            <li>Este enlace es válido por <strong>1 hora</strong></li>
                            <li>Solo puede usarse una vez</li>
                            <li>Si no solicitaste este cambio, ignora este email</li>
                        </ul>
                    </div>
                    
                    <p>Si tienes problemas, contacta con el administrador del sistema.</p>
                    
                    <p>Saludos,<br>
                    <strong>Equipo Aleph70</strong></p>
                </div>
                <div class="footer">
                    <p>© 2025 Aleph70 - Sistema Multiempresa</p>
                    <p>Este es un email automático, por favor no respondas a este mensaje.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Adjuntar HTML
        msg.attach(MIMEText(html, 'html'))

        _send_smtp_message(cfg, msg, [destinatario])
        logger.info(f"Email de recuperación enviado correctamente a {destinatario}")
        return True, "Email enviado correctamente"
        
    except Exception as e:
        logger.error(f"Error al enviar email de recuperación: {str(e)}", exc_info=True)
        return False, f"Error al enviar el correo: {str(e)}"

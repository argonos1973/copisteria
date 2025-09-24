import os
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header

from dotenv import load_dotenv

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

        print(f"Configurando servidor SMTP: {smtp_server}:{smtp_port}")
        
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
        print("Creando conexión SMTP con SSL")
        context = ssl.create_default_context()
        server = smtplib.SMTP_SSL(smtp_server, smtp_port, context=context)

        print("Iniciando sesión en el servidor SMTP")
        server.login(smtp_username, smtp_password)

        print(f"Enviando correo a {destinatario}")
        # Añadir copia oculta a info@aleph70.com
        destinatarios = [destinatario, 'info@aleph70.com']  # Incluir el destinatario original y la copia oculta
        # Depuración: mostrar tipo y tamaño del mensaje
        try:
            from email import policy
            msg_bytes = msg.as_bytes(policy=policy.SMTP)
            print(f"Tipo de mensaje: {type(msg_bytes)}, tamaño: {len(msg_bytes)} bytes")
            server.sendmail(smtp_from, destinatarios, msg_bytes)
        except Exception as send_err:
            print(f"Error en server.sendmail: {send_err}")
            raise
        
        print("Cerrando conexión SMTP")
        server.quit()

        return True, "Correo enviado correctamente"
    except Exception as e:
        print(f"Error al enviar correo: {str(e)}")
        if server:
            try:
                server.quit()
            except:
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

        print(f"Configurando servidor SMTP para presupuesto: {smtp_server}:{smtp_port}")
        
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
        print(f"Error al enviar presupuesto por correo: {str(e)}")
        if server:
            try:
                server.quit()
            except:
                pass
        return False, f"Error al enviar el presupuesto por correo: {str(e)}"

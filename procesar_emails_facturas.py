#!/usr/bin/env python3
"""
Sistema automático de procesamiento de facturas de proveedores por email
Monitorea un buzón de correo y procesa PDFs de facturas automáticamente

Flujo:
1. Conecta al buzón IMAP
2. Busca emails del trimestre actual con asunto "FACTURA" o "F"
3. Extrae PDFs adjuntos
4. Procesa con GPT-4 Vision (extracción de datos)
5. Busca o crea proveedor automáticamente
6. Guarda factura en base de datos
7. Guarda PDF en directorio de empresa
8. Registra en historial
9. Marca email como procesado (opcional)
"""

import imaplib
import email
from email.header import decode_header
import os
import sys
import sqlite3
from datetime import datetime
from pathlib import Path
import base64
import io

# Agregar directorio al path
sys.path.insert(0, '/var/www/html')

from logger_config import get_logger
import facturas_proveedores
from factura_ocr import procesar_imagen_factura

logger = get_logger(__name__)

# Configuración desde variables de entorno
EMAIL_HOST = os.getenv('EMAIL_IMAP_HOST', 'imap.ionos.es')
EMAIL_PORT = int(os.getenv('EMAIL_IMAP_PORT', '993'))
EMAIL_USER = os.getenv('SMTP_USERNAME')
EMAIL_PASSWORD = os.getenv('SMTP_PASSWORD')

# Base de datos
DB_PATH = '/var/www/html/copisteria.db'


def _obtener_nif_cliente_empresa(empresa_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT cif FROM empresas WHERE id = ?", (empresa_id,))
        row = cursor.fetchone()
        conn.close()
        if row and row['cif']:
            return str(row['cif']).upper().strip()
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
    return None


def conectar_email():
    """Conecta al servidor IMAP"""
    try:
        logger.info(f"📧 Conectando a {EMAIL_HOST}:{EMAIL_PORT}...")
        mail = imaplib.IMAP4_SSL(EMAIL_HOST, EMAIL_PORT)
        mail.login(EMAIL_USER, EMAIL_PASSWORD)
        logger.info("✓ Conexión exitosa al buzón")
        return mail
    except Exception as e:
        logger.error(f"❌ Error conectando al email: {e}")
        return None


def obtener_empresas_activas():
    """Obtiene lista de empresas activas"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, codigo, nombre
            FROM empresas
            WHERE activo = 1
        """)
        
        empresas = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return empresas
        
    except Exception as e:
        logger.error(f"Error obteniendo empresas: {e}")
        return []


def buscar_emails_facturas(mail):
    """
    Busca emails del trimestre actual con asunto FACTURA o F
    Busca tanto leídos como no leídos
    """
    try:
        mail.select('INBOX')
        
        # Obtener fechas del trimestre actual
        trimestre, año, fecha_inicio, fecha_fin = facturas_proveedores.obtener_trimestre_actual()
        
        # Formato de fecha para IMAP: DD-MMM-YYYY
        fecha_desde = fecha_inicio.strftime('%d-%b-%Y')
        
        logger.info(f"🔍 Buscando emails del trimestre {trimestre} {año} (desde {fecha_desde})...")
        
        # Buscar emails con asunto FACTURA o F desde inicio de trimestre
        # No filtrar por UNSEEN para procesar todos los del trimestre
        criterio = f'(SINCE {fecha_desde}) (OR SUBJECT "FACTURA" SUBJECT "F")'
        
        status, messages = mail.search(None, criterio)
        
        if status != 'OK':
            logger.warning("No se pudo buscar emails")
            return []
        
        email_ids = messages[0].split() if messages[0] else []
        logger.info(f"✓ Encontrados {len(email_ids)} email(s) con facturas")
        
        return email_ids
        
    except Exception as e:
        logger.error(f"Error buscando emails: {e}")
        return []


def extraer_pdf_email(msg):
    """Extrae el PDF adjunto de un email"""
    try:
        for part in msg.walk():
            content_type = part.get_content_type()
            filename = part.get_filename()
            
            if content_type == 'application/pdf' or (filename and filename.lower().endswith('.pdf')):
                pdf_bytes = part.get_payload(decode=True)
                
                if pdf_bytes:
                    logger.info(f"✓ PDF encontrado: {filename} ({len(pdf_bytes)/1024:.1f} KB)")
                    return pdf_bytes, filename
        
        return None, None
        
    except Exception as e:
        logger.error(f"Error extrayendo PDF: {e}")
        return None, None


def extraer_datos_factura_gpt4(pdf_bytes):
    """
    Extrae datos de la factura usando el mismo OCR/prompt que la subida manual.
    Devuelve un dict plano compatible con el flujo existente de este script.
    """
    try:
        # NOTA: nif_cliente se resuelve en procesar_email_factura y se deja en un global temporal
        nif_cliente = globals().get('_NIF_CLIENTE_OCR')

        datos_ocr = procesar_imagen_factura(pdf_bytes, nif_cliente)
        proveedor = datos_ocr.get('proveedor') or {}
        factura = datos_ocr.get('factura') or {}

        datos = {
            'numero_factura': factura.get('numero'),
            'fecha_emision': factura.get('fecha_emision'),
            'fecha_vencimiento': factura.get('fecha_vencimiento'),
            'base_imponible': factura.get('base_imponible'),
            'iva_importe': factura.get('iva'),
            'total': factura.get('total'),
            'concepto': factura.get('concepto'),
            'proveedor_nombre': proveedor.get('nombre'),
            'proveedor_nif': proveedor.get('nif'),
            'proveedor_direccion': proveedor.get('direccion'),
            'proveedor_telefono': proveedor.get('telefono'),
            'proveedor_email': proveedor.get('email'),
            'proveedor_website': proveedor.get('website'),
            'metodo_extraccion': datos_ocr.get('_metodo_ocr') or 'GPT-4 Vision',
            'confianza_extraccion': 90.0,
        }

        logger.info("✓ Datos extraídos correctamente")
        logger.info(f"  - Proveedor: {datos.get('proveedor_nombre')}")
        logger.info(f"  - NIF: {datos.get('proveedor_nif')}")
        logger.info(f"  - Factura: {datos.get('numero_factura')}")
        logger.info(f"  - Total: {datos.get('total')}€")

        return datos
        
    except Exception as e:
        logger.error(f"❌ Error procesando con GPT-4: {e}", exc_info=True)
        return None


def procesar_email_factura(mail, email_id, empresa_id, empresa_codigo):
    """Procesa un email individual con factura"""
    try:
        # Obtener email
        status, msg_data = mail.fetch(email_id, '(RFC822)')
        
        if status != 'OK':
            logger.error(f"No se pudo obtener email {email_id}")
            return False
        
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)
        
        # Obtener remitente
        remitente = msg.get('From', '')
        asunto = msg.get('Subject', '')
        
        logger.info(f"\n📧 Procesando email de: {remitente}")
        logger.info(f"   Asunto: {asunto}")
        
        # Extraer PDF
        pdf_bytes, pdf_nombre = extraer_pdf_email(msg)
        
        if not pdf_bytes:
            logger.warning("⚠️ No se encontró PDF en el email")
            return False
        
        # Verificar si ya fue procesado (por hash)
        pdf_hash = facturas_proveedores.calcular_hash_pdf(pdf_bytes)
        
        if facturas_proveedores.factura_ya_procesada(pdf_hash, empresa_id):
            logger.info("⏭️ Factura ya procesada anteriormente (hash duplicado)")
            return False

        # NIF/CIF del cliente para evitar confusiones en OCR (mismo criterio que subida manual)
        globals()['_NIF_CLIENTE_OCR'] = _obtener_nif_cliente_empresa(empresa_id)
        
        # Extraer datos con GPT-4
        datos_factura = extraer_datos_factura_gpt4(pdf_bytes)
        globals()['_NIF_CLIENTE_OCR'] = None
        
        if not datos_factura:
            logger.error("❌ No se pudieron extraer datos de la factura")
            return False
        
        # Validar datos mínimos
        if not (datos_factura.get('proveedor_nif') or datos_factura.get('proveedor_nombre')):
            logger.error("❌ Falta proveedor (NIF y nombre vacíos)")
            return False

        # Buscar o crear proveedor
        logger.info("🔍 Buscando proveedor...")
        proveedor_id = facturas_proveedores.obtener_o_crear_proveedor(
            nif=datos_factura.get('proveedor_nif'),
            nombre=datos_factura.get('proveedor_nombre', 'PROVEEDOR DESCONOCIDO'),
            empresa_id=empresa_id,
            datos_adicionales=datos_factura,
            email_origen=remitente
        )
        
        # Guardar PDF en directorio
        logger.info("💾 Guardando PDF...")
        ruta_pdf = guardar_pdf_factura(
            pdf_bytes,
            empresa_codigo,
            datos_factura.get('proveedor_nombre', 'DESCONOCIDO'),
            datos_factura.get('numero_factura', 'SN')
        )
        
        # Guardar factura en BD
        logger.info("💾 Guardando factura en base de datos...")
        factura_id = facturas_proveedores.guardar_factura_bd(
            empresa_id=empresa_id,
            proveedor_id=proveedor_id,
            datos_factura=datos_factura,
            ruta_pdf=ruta_pdf,
            pdf_hash=pdf_hash,
            email_origen=remitente,
            usuario='sistema_email'
        )
        
        # Registrar en historial
        facturas_proveedores.registrar_historial(
            factura_id,
            'creada',
            'sistema_email',
            datos_nuevos=datos_factura
        )
        
        logger.info(f"🎉 Factura procesada exitosamente (ID: {factura_id})")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error procesando email: {e}", exc_info=True)
        return False


def guardar_pdf_factura(pdf_bytes, empresa_codigo, proveedor_nombre, numero_factura):
    """Guarda el PDF en el directorio correspondiente"""
    try:
        # Obtener trimestre actual
        hoy = datetime.now()
        año = hoy.year
        trimestre = f"Q{(hoy.month - 1) // 3 + 1}"
        
        # Obtener directorio
        directorio = facturas_proveedores.obtener_directorio_facturas(empresa_codigo, año, trimestre)
        
        # Sanitizar nombre de archivo
        proveedor_safe = proveedor_nombre.replace(' ', '_').replace('/', '_')[:30]
        factura_safe = numero_factura.replace('/', '_').replace(' ', '_')[:20]
        
        # Nombre del archivo: PROVEEDOR_FACTURA_TIMESTAMP.pdf
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nombre_archivo = f"{proveedor_safe}_{factura_safe}_{timestamp}.pdf"
        
        # Ruta completa
        ruta_completa = directorio / nombre_archivo
        
        # Guardar archivo
        with open(ruta_completa, 'wb') as f:
            f.write(pdf_bytes)
        
        # Retornar ruta relativa (para BD)
        ruta_relativa = str(ruta_completa).replace('/var/www/html/', '')
        
        logger.info(f"✓ PDF guardado: {ruta_relativa}")
        
        return ruta_relativa
        
    except Exception as e:
        logger.error(f"Error guardando PDF: {e}")
        raise


def procesar_facturas_email():
    """Proceso principal"""
    logger.info("=" * 70)
    logger.info("🚀 INICIANDO PROCESAMIENTO DE FACTURAS POR EMAIL")
    logger.info("=" * 70)
    logger.info(f"Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Verificar configuración
    if not EMAIL_USER or not EMAIL_PASSWORD:
        logger.error("❌ Faltan credenciales de email en variables de entorno")
        logger.error("   Configurar: SMTP_USERNAME y SMTP_PASSWORD")
        return
    
    # Conectar al email
    mail = conectar_email()
    if not mail:
        logger.error("❌ No se pudo conectar al buzón")
        return
    
    try:
        # Obtener empresas activas
        empresas = obtener_empresas_activas()
        logger.info(f"\n📊 Empresas activas: {len(empresas)}")
        
        if not empresas:
            logger.warning("⚠️ No hay empresas activas para procesar")
            return
        
        # Buscar emails con facturas
        email_ids = buscar_emails_facturas(mail)
        
        if not email_ids:
            logger.info("📭 No hay emails con facturas para procesar")
            return
        
        # Procesar cada email para cada empresa
        # (En un sistema real, deberías identificar a qué empresa pertenece cada email)
        # Por ahora, procesamos para la primera empresa activa
        empresa = empresas[0]
        empresa_id = empresa['id']
        empresa_codigo = empresa['codigo']
        
        logger.info(f"\n🏢 Procesando para empresa: {empresa['nombre']} ({empresa_codigo})")
        
        procesados = 0
        errores = 0
        
        for email_id in email_ids:
            try:
                if procesar_email_factura(mail, email_id, empresa_id, empresa_codigo):
                    procesados += 1
                else:
                    errores += 1
            except Exception as e:
                logger.error(f"Error procesando email {email_id}: {e}")
                errores += 1
        
        logger.info("\n" + "=" * 70)
        logger.info("📊 RESUMEN DEL PROCESAMIENTO")
        logger.info("=" * 70)
        logger.info(f"✅ Facturas procesadas: {procesados}")
        logger.info(f"❌ Errores: {errores}")
        logger.info(f"📧 Total emails revisados: {len(email_ids)}")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"❌ Error en el proceso: {e}", exc_info=True)
        
    finally:
        # Cerrar conexión
        try:
            mail.close()
            mail.logout()
            logger.info("✓ Conexión cerrada")
        except Exception:
            pass


if __name__ == '__main__':
    try:
        procesar_facturas_email()
    except KeyboardInterrupt:
        logger.info("\n⚠️ Proceso interrumpido por el usuario")
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}", exc_info=True)
        sys.exit(1)

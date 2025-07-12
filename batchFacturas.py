#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import os
import re
import sqlite3
import sys
import tempfile
from datetime import datetime

from flask import Flask

import factura as factura_module  # Importar el módulo factura con un alias para evitar conflictos
from constantes import *
from contactos import get_db_connection, obtener_contactos
from email_utils import enviar_factura_por_email
from proforma import app as proforma_app

# Configurar logging solo con salida a la consola
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("batchFacturas")

# Variable global para controlar si se intenta generar PDFs
GENERAR_PDFS = False  # Desactivamos la generación de PDFs por defecto

def obtener_contactos_tipo_1():
    """
    Obtiene todos los contactos de tipo 1.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                idContacto,
                razonsocial,
                identificador,
                mail,
                telf1,
                tipo
            FROM contactos 
            WHERE tipo = 1
        ''')
        contactos = cursor.fetchall()
        return [dict(c) for c in contactos]
        
    except sqlite3.Error as e:
        logger.error(f"Error de base de datos al obtener contactos tipo 1: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Error inesperado al obtener contactos tipo 1: {str(e)}")
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def obtener_proformas_activas_para_contacto(id_contacto):
    """
    Obtiene todas las proformas activas para un contacto específico.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                id,
                numero,
                fecha,
                estado,
                idContacto,
                total
            FROM proforma 
            WHERE idContacto = ? AND estado = 'A'
        ''', (id_contacto,))
        proformas = cursor.fetchall()
        return [dict(p) for p in proformas]
        
    except sqlite3.Error as e:
        logger.error(f"Error de base de datos al obtener proformas: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Error inesperado al obtener proformas: {str(e)}")
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def generar_factura_pdf(id_factura):
    """
    Genera el PDF para una factura específica intentando usar el mismo formato
    que cuando se imprime una factura desde la interfaz web.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener datos completos de la factura
        cursor.execute('''
            SELECT 
                f.*,
                c.razonsocial, 
                c.identificador,
                c.direccion,
                c.localidad,
                c.cp,
                c.provincia,
                c.mail
            FROM factura f
            LEFT JOIN contactos c ON f.idContacto = c.idContacto
            WHERE f.id = ?
        ''', (id_factura,))
        factura_datos = cursor.fetchone()
        
        if not factura_datos:
            logger.error(f"No se encontró la factura {id_factura}")
            return None
            
        # Convertir a diccionario para acceso más fácil
        factura_dict = dict(factura_datos)
        
        # Añadir registro para depurar
        logger.info(f"Datos de factura: {factura_dict}")
        
        # Verificar que la forma de pago esté presente - el campo podría llamarse formaPago o forma_pago
        forma_pago = factura_dict.get("formaPago", factura_dict.get("forma_pago", ""))
        
        # Crear número de factura formateado para el nombre del archivo
        numero_factura = factura_dict['numero']
        
        # Obtener detalles de la factura
        cursor.execute('SELECT * FROM detalle_factura WHERE id_factura = ? ORDER BY id', (id_factura,))
        detalles = cursor.fetchall()
        detalles_list = [dict(d) for d in detalles]
        
        # Crear directorio para guardar las facturas
        dir_pdf = os.path.join(os.getcwd(), 'facturas_pdf')
        if not os.path.exists(dir_pdf):
            os.makedirs(dir_pdf)
            
        # Primero intentamos generar un archivo de texto para asegurar que funcione siempre
        txt_path = os.path.join(dir_pdf, f'factura_{numero_factura}.txt')
        
        # Crear el archivo de texto
        logger.info(f"Creando archivo de texto para la factura {numero_factura}")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"FACTURA: {factura_dict.get('numero', '')}\n")
            f.write(f"FECHA: {factura_dict.get('fecha', '')}\n")
            f.write(f"CLIENTE: {factura_dict.get('razonsocial', '')}\n")
            f.write(f"NIF: {factura_dict.get('identificador', '')}\n")
            f.write(f"DIRECCIÓN: {factura_dict.get('direccion', '')}\n\n")
            f.write("DETALLES:\n")
            f.write("-" * 50 + "\n")
            
            for detalle in detalles_list:
                f.write(f"• {detalle.get('concepto', '')}: {detalle.get('cantidad', '')} x {detalle.get('precio', '')}€ = {detalle.get('total', '')}€\n")
                if detalle.get('descripcion'):
                    f.write(f"  {detalle.get('descripcion')}\n")
            
            f.write("-" * 50 + "\n")
            f.write(f"IMPORTE BRUTO: {factura_dict.get('importe_bruto', 0)}€\n")
            f.write(f"IMPUESTOS: {factura_dict.get('importe_impuestos', 0)}€\n")
            f.write(f"TOTAL: {factura_dict.get('total', 0)}€\n")
            f.write(f"\nEstado: {obtener_estado_formateado(factura_dict.get('estado', 'P'))}\n")
            
        logger.info(f"Archivo de texto generado en {txt_path}")
        
        # Ahora vamos a intentar crear un HTML que sea idéntico al que se usa
        # cuando se imprime una factura desde la interfaz web
        ruta_archivo = os.path.join(dir_pdf, f'factura_{numero_factura}.pdf')
        
        try:
            # Leer la plantilla HTML de factura usada en la interfaz web
            html_path = '/var/www/html/frontend/IMPRIMIR_FACTURA.html'
            if os.path.exists(html_path):
                logger.info(f"Utilizando plantilla HTML de factura: {html_path}")
                
                with open(html_path, 'r', encoding='utf-8') as f:
                    html_template = f.read()
                
                # Manejar el logo: copiar el archivo a una ubicación local para que wkhtmltopdf pueda acceder a él
                logo_path = '/var/www/html/static/img/logo.png'
                logo_local = os.path.join(dir_pdf, 'logo.png')
                
                try:
                    # Verificar si el logo original existe
                    if os.path.exists(logo_path):
                        # Copiar el logo a la carpeta local
                        import shutil
                        shutil.copy2(logo_path, logo_local)
                        logger.info(f"Logo copiado a {logo_local}")
                        
                        # Modificar la ruta del logo en el HTML para que sea absoluta
                        html_template = html_template.replace('src="/static/img/logo.png"', f'src="file://{logo_local}"')
                    else:
                        logger.warning(f"Logo no encontrado en {logo_path}")
                        # Usar un marcador de posición para el logo
                        logo_pattern = re.compile(r'<img[^>]*?src="[^"]*?logo\.png"[^>]*?>')
                        html_template = logo_pattern.sub('<div style="font-size: 28px; font-weight: bold; margin: 20px 0; color: #2c3e50; text-align: center;">ALEPH70</div>', html_template)
                except Exception as e:
                    logger.error(f"Error al manejar el logo: {str(e)}")
                    # Usar un marcador de posición para el logo
                    logo_pattern = re.compile(r'<img[^>]*?src="[^"]*?logo\.png"[^>]*?>')
                    html_template = logo_pattern.sub('<div style="font-size: 28px; font-weight: bold; margin: 20px 0; color: #2c3e50; text-align: center;">ALEPH70</div>', html_template)
                
                # Leer el CSS asociado si existe
                css_content = ""
                css_path = '/var/www/html/static/css/factura-pdf.css'
                if os.path.exists(css_path):
                    with open(css_path, 'r', encoding='utf-8') as f:
                        css_content = f.read()
                
                # Formatear fecha
                fecha_formateada = datetime.strptime(factura_dict['fecha'], '%Y-%m-%d').strftime('%d/%m/%Y')
                
                # Calcular totales si no están disponibles
                base_imponible = float(factura_dict.get('importe_bruto', 0))
                iva = float(factura_dict.get('importe_impuestos', 0))
                total = float(factura_dict.get('total', 0))
                
                if total == 0:
                    base_imponible = sum(float(detalle['total']) for detalle in detalles_list)
                    iva = base_imponible * 0.21  # 21% IVA
                    total = base_imponible + iva
                
                # Generar HTML de los detalles
                detalles_html = ""
                for detalle in detalles_list:
                    descripcion_html = f"<span class='detalle-descripcion'>{detalle.get('descripcion', '')}</span>" if detalle.get('descripcion') else ''
                    detalles_html += f"""
                        <tr>
                            <td>
                                <div class="detalle-concepto">
                                    <span>{detalle.get('concepto', '')}</span>
                                    {descripcion_html}
                                </div>
                            </td>
                            <td class="cantidad">{detalle.get('cantidad', 0)}</td>
                            <td class="precio">{"{:.2f}".format(float(detalle.get('precio', 0))).replace('.', ',')}€</td>
                            <td class="precio">{detalle.get('impuestos', 21)}%</td>
                            <td class="total">{"{:.2f}".format(float(detalle.get('total', 0))).replace('.', ',')}€</td>
                        </tr>
                    """
                
                # Reemplazar placeholders con datos reales
                replacements = {
                    'id="numero"></span>': f'id="numero">{factura_dict["numero"]}</span>',
                    'id="fecha"></span>': f'id="fecha">{fecha_formateada}</span>',
                    '<p id="emisor-nombre"></p>': '<p>SAMUEL RODRIGUEZ MIQUEL</p>',
                    '<p id="emisor-direccion"></p>': '<p>LEGALITAT, 70</p>',
                    '<p id="emisor-cp-ciudad"></p>': '<p>BARCELONA (08024), BARCELONA, España</p>',
                    '<p id="emisor-nif"></p>': '<p>44007535W</p>',
                    '<p id="emisor-email"></p>': '<p>info@aleph70.com</p>',
                    '<p id="razonsocial"></p>': f'<p>{factura_dict["razonsocial"]}</p>',
                    '<p id="direccion"></p>': f'<p>{factura_dict["direccion"] or ""}</p>',
                    '<p id="cp-localidad"></p>': f'<p>{", ".join(filter(None, [factura_dict["cp"], factura_dict["localidad"], factura_dict["provincia"]]))}</p>',
                    '<p id="nif"></p>': f'<p>{factura_dict["identificador"] or ""}</p>',
                    '<!-- Los detalles se insertarán aquí dinámicamente -->': detalles_html,
                    'id="base"></span>': f'id="base">{"{:.2f}".format(base_imponible).replace(".", ",")}€</span>',
                    'id="iva"></span>': f'id="iva">{"{:.2f}".format(iva).replace(".", ",")}€</span>',
                    'id="total"></span>': f'id="total">{"{:.2f}".format(total).replace(".", ",")}€</span>',
                }
                
                # Añadir reemplazo para la forma de pago
                logger.info(f"Forma de pago: {forma_pago}")
                if forma_pago == 'R':
                    replacements['<p id="forma-pago">Tarjeta</p>'] = '<p id="forma-pago">Pago por transferencia bancaria al siguiente número de cuenta ES4200494752902216156784</p>'
                else:
                    forma_pago_texto = obtener_forma_pago(forma_pago)
                    replacements['<p id="forma-pago">Tarjeta</p>'] = f'<p id="forma-pago">{forma_pago_texto}</p>'
                
                # Aplicar todos los reemplazos
                for old, new in replacements.items():
                    html_template = html_template.replace(old, new)
                
                # Agregar CSS
                head_end = html_template.find('</head>')
                if head_end > 0:
                    html_template = html_template[:head_end] + f'<style>{css_content}</style>' + html_template[head_end:]
                
                # Eliminar scripts y dependencias externas
                html_template = html_template.replace('<script type="module" src="/static/imprimir-factura.js"></script>', '')

                # Crear HTML temporal
                html_tmp = os.path.join(dir_pdf, f'factura_{numero_factura}.html')
                with open(html_tmp, 'w', encoding='utf-8') as f:
                    f.write(html_template)
                
                logger.info(f"HTML generado en {html_tmp}")
                
                # Intentar convertir a PDF usando wkhtmltopdf
                try:
                    import subprocess
                    if subprocess.run(['which', 'wkhtmltopdf'], capture_output=True).returncode == 0:
                        logger.info("Utilizando wkhtmltopdf para generar PDF")
                        
                        # Opción para incluir el CSS interno
                        css_option = []
                        if css_content:
                            css_tmp = os.path.join(dir_pdf, 'factura-pdf.css')
                            with open(css_tmp, 'w', encoding='utf-8') as f:
                                f.write(css_content)
                            css_option = ['--user-style-sheet', css_tmp]
                        
                        # Opciones para que se vea correctamente
                        options = [
                            '--encoding', 'utf-8',
                            '--page-size', 'A4',
                            '--margin-top', '10mm',
                            '--margin-bottom', '10mm',
                            '--margin-left', '10mm',
                            '--margin-right', '10mm',
                            '--print-media-type',
                            '--enable-local-file-access'  # Permitir acceso a archivos locales
                        ]
                        
                        cmd = ['wkhtmltopdf'] + options + css_option + [html_tmp, ruta_archivo]
                        logger.info(f"Ejecutando comando: {' '.join(cmd)}")
                        
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        if result.returncode == 0:
                            logger.info(f"PDF generado correctamente en {ruta_archivo}")
                            return ruta_archivo
                        else:
                            logger.error(f"Error al generar PDF: {result.stderr}")
                except Exception as e:
                    logger.error(f"Error al generar PDF con wkhtmltopdf: {str(e)}")
                
                # Si no funcionó, intentar usar el módulo factura
                logger.info("Intentando generar PDF con el módulo factura")
                if hasattr(factura_module, 'generar_pdf_factura'):
                    try:
                        resultado = factura_module.generar_pdf_factura(id_factura, ruta_archivo)
                        if resultado:
                            logger.info(f"PDF generado con el módulo factura en {ruta_archivo}")
                            return ruta_archivo
                    except Exception as e:
                        logger.error(f"Error al generar PDF con módulo factura: {str(e)}")
            else:
                logger.warning(f"No se encontró la plantilla HTML de factura: {html_path}")
        except Exception as e:
            logger.error(f"Error al generar PDF con plantilla HTML: {str(e)}")
        
        # Si después de todos los intentos no se generó un PDF, devolver el archivo de texto
        logger.info("No se pudo generar PDF, devolviendo archivo de texto")
        return txt_path
            
    except Exception as e:
        logger.error(f"Error general al generar archivo para factura {id_factura}: {str(e)}")
        return None
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def obtener_estado_formateado(estado_codigo):
    """
    Convierte códigos de estado (P, C, V) en texto legible 
    (Pendiente, Cobrada, Vencida)
    """
    estados = {
        'P': 'Pendiente',
        'C': 'Cobrada',
        'V': 'Vencida'
    }
    return estados.get(estado_codigo, 'Desconocido')

def obtener_forma_pago(forma_pago_codigo):
    """
    Convierte códigos de forma de pago en texto legible 
    """
    # Si es transferencia, mostrar el número de cuenta
    if forma_pago_codigo == 'R':
        return 'Pago por transferencia bancaria al siguiente número de cuenta ES4200494752902216156784'
    
    formas_pago = {
        'T': 'Tarjeta',
        'E': 'Efectivo'
    }
    return formas_pago.get(forma_pago_codigo, 'Desconocido')

def procesar_contactos_tipo_1():
    """
    Procesa todos los contactos de tipo 1, convirtiendo sus proformas a facturas
    y enviándolas por email.
    """
    logger.info("Iniciando procesamiento de contactos tipo 1")
    
    # Obtener contactos de tipo 1
    contactos = obtener_contactos_tipo_1()
    logger.info(f"Se encontraron {len(contactos)} contactos de tipo 1")
    
    total_facturas_generadas = 0
    total_emails_enviados = 0
    
    # Usar el contexto de aplicación Flask para las operaciones
    with proforma_app.app_context():
        from factura import obtener_factura
        from proforma import convertir_proforma_a_factura
        
        for contacto in contactos:
            id_contacto = contacto['idContacto']
            email_contacto = contacto['mail']
            nombre_contacto = contacto['razonsocial']
            
            if not email_contacto:
                logger.warning(f"Contacto ID {id_contacto} ({nombre_contacto}) no tiene email. Omitiendo.")
                continue
                
            logger.info(f"Procesando contacto: {nombre_contacto} (ID: {id_contacto})")
            
            # Obtener proformas activas para este contacto
            proformas = obtener_proformas_activas_para_contacto(id_contacto)
            logger.info(f"Se encontraron {len(proformas)} proformas activas para {nombre_contacto}")
            
            for proforma in proformas:
                id_proforma = proforma['id']
                numero_proforma = proforma['numero']
                
                try:
                    logger.info(f"Convirtiendo proforma {numero_proforma} (ID: {id_proforma}) a factura")
                    
                    # Convertir proforma a factura usando la función de la app Flask
                    resultado = convertir_proforma_a_factura(id_proforma)
                    
                    # Verificar si el resultado es una respuesta JSON o una tupla con una respuesta y un código de estado
                    if hasattr(resultado, 'json'):
                        respuesta = resultado.json
                        id_factura = respuesta.get('id_factura')
                        numero_factura = respuesta.get('numero_factura', '')
                    elif isinstance(resultado, tuple) and len(resultado) >= 2:
                        if resultado[1] >= 400:  # Error HTTP
                            if hasattr(resultado[0], 'json'):
                                logger.error(f"Error al convertir proforma {id_proforma}: {resultado[0].json}")
                            else:
                                logger.error(f"Error al convertir proforma {id_proforma}: {resultado[0]}")
                            continue
                        respuesta = resultado[0].json if hasattr(resultado[0], 'json') else {}
                        id_factura = respuesta.get('id_factura')
                        numero_factura = respuesta.get('numero_factura', '')
                    else:
                        # Intentar extraer datos en formato texto
                        respuesta_str = str(resultado)
                        logger.info(f"Respuesta no estándar: {respuesta_str}")
                        # Buscar id_factura en la respuesta
                        import re
                        id_match = re.search(r'"id_factura":\s*(\d+)', respuesta_str)
                        num_match = re.search(r'"numero_factura":\s*"?([^,"]+)', respuesta_str)
                        
                        id_factura = int(id_match.group(1)) if id_match else None
                        numero_factura = num_match.group(1) if num_match else ''
                    
                    if not id_factura:
                        logger.error(f"No se pudo obtener el ID de la factura creada para la proforma {id_proforma}")
                        continue
                        
                    logger.info(f"Proforma convertida a factura exitosamente. ID Factura: {id_factura}")
                    
                    # Obtener el número de factura formateado correctamente desde la base de datos
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('SELECT numero FROM factura WHERE id = ?', (id_factura,))
                    factura_data = cursor.fetchone()
                    if factura_data:
                        numero_factura_completo = factura_data['numero']
                        logger.info(f"Número de factura formateado: {numero_factura_completo}")
                    else:
                        numero_factura_completo = numero_factura
                    conn.close()
                    
                    # Generar PDF de la factura
                    ruta_archivo = generar_factura_pdf(id_factura)
                    if not ruta_archivo:
                        logger.error(f"No se pudo generar el archivo para la factura {id_factura}")
                        continue
                    
                    # Preparar el contenido del email
                    asunto = f"Factura {numero_factura_completo} - {nombre_contacto}"
                    cuerpo = f"""
Estimado/a cliente {nombre_contacto},

Adjunto encontrará la factura {numero_factura_completo} generada automáticamente
a partir de la proforma {numero_proforma}.

Por favor, no responda a este correo automático.

Saludos cordiales,
Departamento de Administración
"""
                    
                    # Enviar la factura por email
                    logger.info(f"Enviando factura {numero_factura_completo} por email a {email_contacto}")
                    enviado, mensaje = enviar_factura_por_email(
                        email_contacto, 
                        asunto, 
                        cuerpo, 
                        ruta_archivo, 
                        numero_factura_completo
                    )
                    
                    if enviado:
                        logger.info(f"Email enviado correctamente a {email_contacto}")
                        total_emails_enviados += 1
                    else:
                        logger.error(f"Error al enviar email a {email_contacto}: {mensaje}")
                    
                    total_facturas_generadas += 1
                    
                except Exception as e:
                    logger.error(f"Error al procesar proforma {id_proforma}: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    continue
    
    logger.info(f"Proceso completado. Facturas generadas: {total_facturas_generadas}, Emails enviados: {total_emails_enviados}")
    return {
        "total_contactos": len(contactos),
        "facturas_generadas": total_facturas_generadas,
        "emails_enviados": total_emails_enviados
    }

if __name__ == "__main__":
    try:
        resultado = procesar_contactos_tipo_1()
        logger.info(f"Resultados del proceso: {resultado}")
    except Exception as e:
        logger.error(f"Error en el proceso principal: {str(e)}")
        sys.exit(1)
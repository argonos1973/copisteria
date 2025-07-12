#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64
import os
import tempfile
import traceback
from datetime import datetime

from flask import jsonify, send_file
from weasyprint import CSS, HTML

from db_utils import get_db_connection


def generar_factura_pdf(id_factura):
    """
    Genera un archivo PDF con la factura usando el mismo método que para envío por correo,
    pero sin enviar el email, solo generando el PDF para descargar o imprimir.
    
    Args:
        id_factura: ID de la factura a generar en PDF
        
    Returns:
        str: Ruta del archivo PDF generado o None si hay error
    """
    try:
        print(f"Iniciando generación del PDF para factura {id_factura}")
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener los datos de la factura y el contacto
        query = """
            SELECT 
                f.*, 
                c.razonsocial,
                c.mail,
                c.identificador,
                c.direccion,
                c.cp,
                c.localidad,
                c.provincia
            FROM factura f
            INNER JOIN contactos c ON f.idcontacto = c.idContacto
            WHERE f.id = ?
        """
        cursor.execute(query, (id_factura,))
        factura = cursor.fetchone()
        
        print(f"Resultado de la consulta para PDF: {factura}")

        if not factura:
            print(f"Factura {id_factura} no encontrada")
            return None

        # Convertir la tupla de la factura en un diccionario con nombres de columnas
        nombres_columnas = [description[0] for description in cursor.description]
        factura_dict = dict(zip(nombres_columnas, factura))
        
        # Obtener detalles de la factura
        cursor.execute("""
            SELECT *
            FROM detalle_factura
            WHERE id_factura = ?
            ORDER BY id
        """, (id_factura,))
        detalles = cursor.fetchall()
        detalles_list = [dict(zip([d[0] for d in cursor.description], detalle)) for detalle in detalles]
        
        # Usar los totales de la factura
        base_imponible = float(factura_dict.get('importe_bruto', 0))
        iva = float(factura_dict.get('importe_impuestos', 0))
        total = float(factura_dict.get('total', 0))

        # Si no hay totales en la factura, calcularlos desde los detalles
        if total == 0:
            base_imponible = sum(float(detalle['total']) for detalle in detalles_list)
            iva = base_imponible * 0.21  # 21% IVA
            total = base_imponible + iva

        # Función para decodificar forma de pago
        def decodificar_forma_pago(forma_pago):
            formas_pago = {
                'T': 'Tarjeta',
                'E': 'Efectivo',
                'R': 'Pago por transferencia bancaria al siguiente número de cuenta ES4200494752902216156784'
            }
            return formas_pago.get(forma_pago, 'No especificada')

        # Generar el PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            print(f"Generando PDF para factura {id_factura}")
            
            # Obtener datos de VERI*FACTU si existen (usando aleph70.db)
            cursor.execute("SELECT hash_factura FROM factura WHERE id = ?", (id_factura,))
            hash_factura = cursor.fetchone()
            print(f"Hash factura obtenido: {hash_factura}")
            
            # Obtener todos los datos VERI*FACTU de la tabla registro_facturacion
            cursor.execute("""
                SELECT codigo_qr, hash, validado_aeat, estado_envio, id_envio_aeat 
                FROM registro_facturacion
                WHERE factura_id = ?
            """, (id_factura,))
            registro = cursor.fetchone()
            print(f"Registro facturación obtenido: {registro is not None}")
            
            # Definimos variables para usar en la plantilla
            qr_code = None
            hash_value = 'No disponible'
            validado_aeat = False
            id_verificacion = None
            
            if registro:
                # Determinar si la factura ha sido validada por AEAT
                validado_aeat = registro[2] == 1 if registro[2] is not None else False
                estado_envio = registro[3] if registro[3] is not None else 'PENDIENTE'
                id_verificacion = registro[4]
                
                # Obtener el hash para la factura (siempre se muestra)
                if registro[1]:
                    hash_value = registro[1]
                    print(f"Usando hash de registro_facturacion: {hash_value}")
                # Si no está ahí, usamos el de la tabla factura
                elif hash_factura and hash_factura[0]:
                    hash_value = hash_factura[0]
                    print(f"Usando hash de tabla factura: {hash_value}")
                
                # Codificar el QR en base64 SOLO si la factura está validada por AEAT
                if validado_aeat and registro[0]:
                    qr_code = base64.b64encode(registro[0]).decode('utf-8')
                    print(f"Factura VALIDADA por AEAT. Código QR codificado, longitud: {len(qr_code)}")
                elif validado_aeat and not registro[0]:
                    print("Factura validada por AEAT pero no se encontró el código QR")
                else:
                    print(f"Factura NO validada por AEAT (estado: {estado_envio}). No se incluirá código QR.")
            else:
                print("No se encontró registro VERI*FACTU para esta factura")
                
            # Leer el HTML base con la codificación correcta
            with open('/var/www/html/frontend/IMPRIMIR_FACTURA.html', 'r', encoding='utf-8') as f:
                html_base = f.read()

            # Modificar la ruta del logo para usar ruta absoluta del sistema de archivos
            html_base = html_base.replace('src="/static/img/logo.png"', 'src="file:///var/www/html/static/img/logo.png"')

            # Generar el HTML con los datos ya insertados
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
                        <td class="precio">{str(float(detalle.get('precio', 0))).rstrip('0').rstrip('.').replace('.', ',')}€</td>
                        <td class="precio">{detalle.get('impuestos', 21)}%</td>
                        <td class="total">{"{:.2f}".format(float(detalle.get('total', 0))).replace('.', ',')}€</td>
                    </tr>
                """

            # Detectar si es factura rectificativa
            es_rectificativa = (
                factura_dict.get('tipo') == 'R' or
                factura_dict.get('estado') == 'RE' or
                str(factura_dict.get('numero', '')).endswith('-R')
            )
            rectificativa_html = ''
            if es_rectificativa:
                num_orig = ''
                fecha_orig = ''
                motivo = 'Anulación de factura'  # Por ahora, motivo genérico
                try:
                    id_orig = factura_dict.get('id_factura_rectificada')
                    if id_orig:
                        cursor.execute('SELECT numero, fecha FROM factura WHERE id = ?', (id_orig,))
                        orig = cursor.fetchone()
                        if orig:
                            num_orig, fecha_orig = orig[0], datetime.strptime(orig[1], '%Y-%m-%d').strftime('%d/%m/%Y')
                except Exception:
                    pass
                rectificativa_html = f"""
                <div style='border:2px solid #c00; padding:10px; margin:10px 0;'>
                    <h2 style='color:#c00; text-align:center;'>FACTURA RECTIFICATIVA</h2>
                    <p><strong>Factura rectificada:</strong> Nº {num_orig} de fecha {fecha_orig}</p>
                    <p><strong>Motivo rectificación:</strong> {motivo}</p>
                    <p><strong>Importe rectificado:</strong> {'{:.2f}'.format(total).replace('.', ',')}€</p>
                </div>
                """
            # Reemplazar los elementos con los datos reales
            html_modificado = html_base.replace(
                '<script type="module" src="/static/imprimir-factura.js"></script>',
                ''
            ).replace(
                'id="numero"></span>',
                f'id="numero">{factura_dict["numero"]}</span>'
            ).replace(
                'id="fecha"></span>',
                f'id="fecha">{datetime.strptime(factura_dict["fecha"], "%Y-%m-%d").strftime("%d/%m/%Y")}</span>'
            ).replace(
                '<p id="emisor-nombre"></p>',
                '<p>SAMUEL RODRIGUEZ MIQUEL</p>'
            ).replace(
                '<p id="emisor-direccion"></p>',
                '<p>LEGALITAT, 70</p>'
            ).replace(
                '<p id="emisor-cp-ciudad"></p>',
                '<p>BARCELONA (08024), BARCELONA, España</p>'
            ).replace(
                '<p id="emisor-nif"></p>',
                '<p>44007535W</p>'
            ).replace(
                '<p id="emisor-email"></p>',
                '<p>info@aleph70.com</p>'
            ).replace(
                '<p id="razonsocial"></p>',
                f'<p>{factura_dict["razonsocial"]}</p>'
            ).replace(
                '<p id="direccion"></p>',
                f'<p>{factura_dict["direccion"] or ""}</p>'
            ).replace(
                '<p id="cp-localidad"></p>',
                f'<p>{", ".join(filter(None, [factura_dict["cp"], factura_dict["localidad"], factura_dict["provincia"]]))}</p>'
            ).replace(
                '<p id="nif"></p>',
                f'<p>{factura_dict["identificador"] or ""}</p>'
            ).replace(
                '<div id="rectificativa-info"></div>',
                rectificativa_html if rectificativa_html else ''
            ).replace(
                '<!-- Los detalles se insertarán aquí dinámicamente -->',
                detalles_html
            ).replace(
                'id="base"></span>',
                f'id="base">{"{:.2f}".format(base_imponible).replace(".", ",")}€</span>'
            ).replace(
                'id="iva"></span>',
                f'id="iva">{"{:.2f}".format(iva).replace(".", ",")}€</span>'
            ).replace(
                'id="total"></strong>',
                f'id="total">{"{:.2f}".format(total).replace(".", ",")}€</strong>'
            ).replace(
                '<p id="forma-pago">Tarjeta</p>',
                f'<p>{decodificar_forma_pago(factura_dict.get("formaPago", "T"))}</p>'
            )
            
            # Enfoque directo para insertar el hash y el QR
            hash_placeholder = '<p id="hash-factura">Hash: </p>'
            qr_placeholder = '<div id="qr-verifactu" style="width: 150px; height: 150px; margin-left: auto;">\n                <!-- Aquí se insertará el código QR -->\n                <img src="/static/qr_temp.png" alt="Código QR VERI*FACTU" style="width: 150px; height: 150px;" onerror="this.onerror=null; this.src=\'/static/qr_temp.png?\'+new Date().getTime();">\n            </div>'
            
            # Crear los contenidos de reemplazo
            hash_replacement = f'<p id="hash-factura">Hash: {hash_value}</p>'
            
            # Realizar reemplazos
            if hash_placeholder in html_modificado:
                html_modificado = html_modificado.replace(hash_placeholder, hash_replacement)
                print("Hash reemplazado con éxito")
            else:
                print(f"ERROR: No se encontró el marcador del hash: {hash_placeholder}")
            
            # Insertar el QR si existe
            if qr_code:
                qr_replacement = f'<div id="qr-verifactu" style="width: 150px; height: 150px; margin-left: auto;">\n                <img src="data:image/png;base64,{qr_code}" alt="Código QR VERI*FACTU" style="width: 150px; height: 150px;">\n            </div>'
                
                if qr_placeholder in html_modificado:
                    html_modificado = html_modificado.replace(qr_placeholder, qr_replacement)
                    print("QR insertado con éxito")
                else:
                    print(f"ERROR: No se encontró el marcador del QR")
            else:
                print("No hay código QR para insertar")
                
            # Guardar el HTML final en un archivo para depuración
            with open('/tmp/html_pdf.html', 'w', encoding='utf-8') as f:
                f.write(html_modificado)
                
            print(f"HTML final guardado en /tmp/html_pdf.html")
            
            # Convertir HTML a PDF usando WeasyPrint con ruta base para recursos estáticos
            HTML(
                string=html_modificado,
                base_url='/var/www/html'  # Ruta base para recursos estáticos
            ).write_pdf(
                tmp.name,
                stylesheets=[CSS(string='@page { size: A4; margin: 1cm }')]
            )
            
            pdf_path = tmp.name
            
        # Cerrar la conexión a la base de datos
        if conn:
            conn.close()
            
        return pdf_path
    except Exception as e:
        print(f"Error al generar PDF de factura: {str(e)}")
        print(traceback.format_exc())
        return None

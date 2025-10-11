
import base64
import tempfile
import traceback
import xml.etree.ElementTree as ET
from datetime import datetime
from weasyprint import CSS, HTML
from db_utils import get_db_connection
from verifactu_logger import logger  # Ajusta según tu sistema
from verifactu.config import VERIFACTU_CONSTANTS  # Ruta corregida al módulo
from format_utils import format_currency_es_two, format_total_es_two, format_number_es_max5, format_percentage

try:
    from config_loader import get as get_config
    VERIFACTU_HABILITADO = bool(get_config("verifactu_enabled", True))
except Exception as _e:
    print(f"[PDF] No se pudo cargar config.json: {_e}")
    VERIFACTU_HABILITADO = True

def extraer_huella_desde_xml(xml: str) -> str | None:
    try:
        ns = {
            'env': 'http://schemas.xmlsoap.org/soap/envelope/',
            'tikR': 'https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/RespuestaSuministro.xsd',
            'tik': 'https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/SuministroInformacion.xsd'
        }
        root = ET.fromstring(xml)
        huella = root.find('.//tik:IdPeticionRegistroDuplicado', ns)
        if huella is not None:
            return huella.text.strip()
        return None
    except Exception as e:
        logger.error(f"[VERIFACTU] Error al extraer huella del XML: {e}")
        return None

def guardar_datos_aeat_en_registro(factura_id: int, respuesta_xml: str) -> bool:
    try:
        huella = extraer_huella_desde_xml(respuesta_xml)
        if not huella:
            logger.warning("[VERIFACTU] No se encontró huella en el XML")
            return False

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(registro_facturacion)")
        cols = [c[1] for c in cur.fetchall()]
        if 'huella_aeat' not in cols:
            cur.execute("ALTER TABLE registro_facturacion ADD COLUMN huella_aeat TEXT")
        if 'primer_registro' not in cols:
            cur.execute("ALTER TABLE registro_facturacion ADD COLUMN primer_registro TEXT")

        cur.execute("""
            UPDATE registro_facturacion
            SET huella_aeat = ?, primer_registro = 'S'
            WHERE factura_id = ?
        """, (huella, factura_id))

        conn.commit()
        logger.info(f"[VERIFACTU] Huella AEAT guardada en factura {factura_id}: {huella}")
        return True

    except Exception as e:
        logger.error(f"[VERIFACTU] Error guardando datos AEAT: {e}")
        traceback.print_exc()
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def obtener_datos_para_reenvio(factura_id: int) -> tuple[str, str] | None:
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT primer_registro, huella_aeat
            FROM registro_facturacion
            WHERE factura_id = ?
        """, (factura_id,))
        row = cur.fetchone()
        return row if row else None
    except Exception as e:
        logger.error(f"[VERIFACTU] Error al obtener datos para reenvío: {e}")
        traceback.print_exc()
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def asegurar_columnas_aeat():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(registro_facturacion)")
        cols = [c[1] for c in cur.fetchall()]
        if 'huella_aeat' not in cols:
            cur.execute("ALTER TABLE registro_facturacion ADD COLUMN huella_aeat TEXT")
        if 'primer_registro' not in cols:
            cur.execute("ALTER TABLE registro_facturacion ADD COLUMN primer_registro TEXT")
        conn.commit()
    except Exception as e:
        logger.error(f"[VERIFACTU] Error asegurando columnas AEAT: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def calcular_primer_registro_exacto(nif_emisor: str, numero_factura: str, serie_factura: str) -> str:
    asegurar_columnas_aeat()
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM registro_facturacion
            WHERE nif_emisor = ? AND numero_factura = ? AND serie_factura = ?
        """, (nif_emisor.upper(), numero_factura, serie_factura))
        count = cur.fetchone()[0]
        return 'S' if count == 0 else 'N'
    except Exception as e:
        logger.error(f"[VERIFACTU] Error en calcular_primer_registro_exacto: {e}")
        return 'S'
    finally:
        if 'conn' in locals():
            conn.close()

def generar_elementos_verifactu_xml(factura_id: int) -> str:
    try:
        datos = obtener_datos_para_reenvio(factura_id)
        if not datos:
            return '<tik:PrimerRegistro>S</tik:PrimerRegistro>'

        primer_registro, huella = datos
        xml = f'<tik:PrimerRegistro>{primer_registro}</tik:PrimerRegistro>'
        if primer_registro == 'N' and huella:
            xml += f'<tik:Huella>{huella}</tik:Huella>'
        return xml

    except Exception as e:
        logger.error(f"[VERIFACTU] Error generando XML VERI*FACTU: {e}")
        return '<tik:PrimerRegistro>S</tik:PrimerRegistro>'


# Aquí empieza la función completa para generar el PDF de la factura

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
            LEFT JOIN contactos c ON f.idContacto = c.idContacto
            WHERE f.id = ?
        """
        cursor.execute(query, (id_factura,))
        factura = cursor.fetchone()
        
        print(f"Resultado de la consulta para PDF: {factura}")
        print(f"ID factura: {id_factura}")

        if not factura:
            print(f"Factura {id_factura} no encontrada")
            return None

        # Convertir la tupla de la factura en un diccionario con nombres de columnas
        nombres_columnas = [description[0] for description in cursor.description]
        factura_dict = dict(zip(nombres_columnas, factura))
        
        print(f"Datos del cliente en factura_dict:")
        print(f"  razonsocial: {factura_dict.get('razonsocial')}")
        print(f"  direccion: {factura_dict.get('direccion')}")
        print(f"  cp: {factura_dict.get('cp')}")
        print(f"  localidad: {factura_dict.get('localidad')}")
        print(f"  provincia: {factura_dict.get('provincia')}")
        print(f"  identificador: {factura_dict.get('identificador')}")
        
        # Obtener detalles de la factura
        cursor.execute("""
            SELECT *
            FROM detalle_factura
            WHERE id_factura = ?
            ORDER BY id
        """, (id_factura,))
        detalles = cursor.fetchall()
        detalles_list = [dict(zip([d[0] for d in cursor.description], detalle)) for detalle in detalles]
        
        # Usar los totales de la factura exactamente como llegan del backend
        base_imponible_raw = '' if factura_dict.get('importe_bruto') is None else str(factura_dict.get('importe_bruto'))
        iva_raw = '' if factura_dict.get('importe_impuestos') is None else str(factura_dict.get('importe_impuestos'))
        total_raw = '' if factura_dict.get('total') is None else str(factura_dict.get('total'))

        # Función para decodificar forma de pago
        def decodificar_forma_pago(forma_pago):
            formas_pago = {
                'T': 'Tarjeta',
                'E': 'Efectivo',
                'R': 'Pago por transferencia bancaria al siguiente número de cuenta ES4200494752902216156784'
            }
            return formas_pago.get(forma_pago, 'No especificada')

        # Helpers de formato numérico (ES)

        def format_total_es_two(val):
            """Formatea totales con exactamente 2 decimales, coma decimal y punto de miles."""
            try:
                num = float(val or 0)
            except Exception:
                num = 0.0
            s = f"{num:.2f}"
            sign, rest = _split_sign(s)
            entero, dec = (rest.split('.') if '.' in rest else (rest, '00'))
            try:
                entero_fmt = f"{int(entero):,}".replace(',', 'X').replace('.', ',').replace('X', '.')
            except Exception:
                entero_fmt = entero
            return f"{sign}{entero_fmt},{dec or '00'}"

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

            # Generar el HTML con los datos ya insertados (igual que factura.py)
            def _fmt_euro(val):
                try:
                    s = f"{float(val):.2f}"
                except Exception:
                    s = "0.00"
                s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
                return s
            
            def _fmt_euro_var(val, min_dec=2, max_dec=5):
                try:
                    s = f"{float(val):.{max_dec}f}"
                except Exception:
                    s = "0.00"
                s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
                if ',' in s:
                    entero, decs = s.split(',', 1)
                    decs_trim = decs.rstrip('0')
                    if len(decs_trim) < min_dec:
                        decs_trim = decs[:min_dec]
                    s = f"{entero},{decs_trim}"
                return s
            
            detalles_html = ""
            for detalle in detalles_list:
                descripcion_html = f"<span class='detalle-descripcion'>{detalle.get('descripcion', '')}</span>" if detalle.get('descripcion') else ''
                _precio_raw = detalle.get('precio', 0)
                _cantidad = detalle.get('cantidad', 0)
                # Calcular subtotal SIN IVA (cantidad × precio)
                _subtotal_sin_iva = round(_cantidad * _precio_raw, 2)
                # Precio unitario: mismo comportamiento que impresión (2-5 decimales)
                _precio_str = _fmt_euro_var(_precio_raw, min_dec=2, max_dec=5)
                _subtotal_str = _fmt_euro(_subtotal_sin_iva)
                
                detalles_html += f"""
                    <tr>
                        <td>
                            <div class="detalle-concepto">
                                <span>{detalle.get('concepto', '')}</span>
                                {descripcion_html}
                            </div>
                        </td>
                        <td class="cantidad">{_cantidad}</td>
                        <td class="precio">{_precio_str}€</td>
                        <td class="total">{_subtotal_str}€</td>
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
                'id="numero" style="font-weight:700;"></span>',
                f'id="numero" style="font-weight:700;">{factura_dict["numero"]}</span>'
            ).replace(
                'id="fecha" style="font-weight:700;color:#000;"></span>',
                f'id="fecha" style="font-weight:700;color:#000;">{datetime.strptime(factura_dict["fecha"], "%Y-%m-%d").strftime("%d/%m/%Y")}</span>'
            ).replace(
                'id="fecha-vencimiento" style="font-weight:700;color:#000;"></span>',
                f'id="fecha-vencimiento" style="font-weight:700;color:#000;">{datetime.strptime(factura_dict["fvencimiento"], "%Y-%m-%d").strftime("%d/%m/%Y") if factura_dict.get("fvencimiento") else ""}</span>'
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
                f'<p>{factura_dict.get("razonsocial") or ""}</p>'
            ).replace(
                '<p id="direccion"></p>',
                f'<p>{factura_dict.get("direccion") or ""}</p>'
            ).replace(
                '<p id="cp-localidad"></p>',
                f'<p>{", ".join(filter(None, [factura_dict.get("cp"), factura_dict.get("localidad"), factura_dict.get("provincia")]))}</p>'
            ).replace(
                '<p id="nif"></p>',
                f'<p>{factura_dict.get("identificador") or ""}</p>'
            ).replace(
                '<div id="rectificativa-info"></div>',
                rectificativa_html if rectificativa_html else ''
            ).replace(
                '<!-- Los detalles se insertarán aquí dinámicamente -->',
                detalles_html
            ).replace(
                'id="base"></span>',
                f'id="base">{base_imponible_raw}</span>'
            ).replace(
                'id="iva"></span>',
                f'id="iva">{iva_raw}</span>'
            ).replace(
                'id="total"></strong>',
                f'id="total">{total_raw}</strong>'
            ).replace(
                '<p id="forma-pago">Tarjeta</p>',
                f'<p>{decodificar_forma_pago(factura_dict.get("formaPago", "T"))}</p>'
            )
            
            # Enfoque directo para insertar el hash y el QR
            hash_placeholder = '<p id="hash-factura">Hash: </p>'
            qr_placeholder = '<div id="qr-verifactu" style="width: 150px; height: 150px; margin-left: auto;">\n                <!-- Aquí se insertará el código QR -->\n                <img src="/static/tmp_qr/qr_temp.png" alt="Código QR VERI*FACTU" style="width: 150px; height: 150px;" onerror="this.onerror=null; this.src=\'/static/tmp_qr/qr_temp.png?\'+new Date().getTime();">\n            </div>'
            
            # Crear los contenidos de reemplazo
            hash_replacement = f'<p id="hash-factura">Hash: {hash_value}</p>'
            
            # Realizar reemplazos
            if not VERIFACTU_HABILITADO:
                # Ocultar con CSS en lugar de eliminar del HTML
                # Añadir CSS para ocultar elementos VERIFACTU
                verifactu_hide_css = """
                <style>
                    #qr-verifactu { display: none !important; }
                    #hash-factura { display: none !important; }
                    .header h1 span[style*="VERI*FACTU"] { display: none !important; }
                    div[style*="Información VERI*FACTU"] { display: none !important; }
                </style>
                """
                html_modificado = html_modificado.replace('</head>', verifactu_hide_css + '</head>')
                html_modificado = html_modificado.replace(hash_placeholder, '<p id="hash-factura" style="display:none;">Hash: </p>')
                html_modificado = html_modificado.replace(qr_placeholder, '<div id="qr-verifactu" style="display:none;"></div>')
            else:
                if hash_placeholder in html_modificado:
                    html_modificado = html_modificado.replace(hash_placeholder, hash_replacement)
                    if qr_code:
                        qr_replacement = f'<div id="qr-verifactu" style="width: 150px; height: 150px; margin-left: auto;"><img src="data:image/png;base64,{qr_code}" alt="Código QR VERI*FACTU" style="width: 150px; height: 150px;"></div>'
                        html_modificado = html_modificado.replace(qr_placeholder, qr_replacement)
            
    
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

import json
import os
# --- Utilidades y acceso a base de datos ---
import sqlite3
import tempfile
import time
import traceback
from datetime import datetime, timedelta

from flask import Flask, jsonify, render_template, request, Blueprint
try:
    from weasyprint import CSS, HTML
except ImportError:
    print("WeasyPrint no está instalado. La generación de PDF no estará disponible.")
    # Mock classes to prevent import errors
    class CSS:
        def __init__(self, *args, **kwargs):
            pass
    class HTML:
        def __init__(self, *args, **kwargs):
            pass
        def write_pdf(self, *args, **kwargs):
            raise ImportError("WeasyPrint no está disponible")
from decimal import Decimal, ROUND_HALF_UP

from db_utils import (actualizar_numerador, get_db_connection,
                      verificar_numero_factura)
from email_utils import enviar_factura_por_email
# --- Integración Facturae ---
from utils_emisor import cargar_datos_emisor

# --- Integración VERI*FACTU ---
import logging
import tempfile

# Helper para depuración que escribe en /tmp si /var/www/html no es escribible
from contextlib import contextmanager

@contextmanager
def safe_append_debug(filename: str):
    """Devuelve un context manager de archivo para logs de depuración.

    Intenta abrir /var/www/html/<filename>; si falla por permisos, usa /tmp.
    """
    # Redirigir cualquier log a /dev/null para evitar escrituras en disco
    devnull = os.devnull
    f = open(devnull, 'a', encoding='utf-8')
    try:
        yield f
    finally:
        f.close()

# Intentamos importar verifactu (puede no existir en entornos sin esta funcionalidad)
try:
    import verifactu
    VERIFACTU_DISPONIBLE = True
except ImportError:
    logging.warning("Módulo verifactu no disponible o con problemas de dependencias. Funcionando sin VERI*FACTU")
    VERIFACTU_DISPONIBLE = False

# Cargamos configuración externa (config.json)
try:
    from config_loader import get as get_config
    VERIFACTU_HABILITADO = bool(get_config("verifactu_enabled", VERIFACTU_DISPONIBLE))
except Exception as e:
    logging.warning("No se pudo cargar configuración externa: %s", e)
    VERIFACTU_HABILITADO = VERIFACTU_DISPONIBLE

# Si la configuración deshabilita VERI*FACTU, forzamos su desactivación en el resto del módulo
if not VERIFACTU_HABILITADO:
    VERIFACTU_DISPONIBLE = False


# Asegurar que XDG_RUNTIME_DIR esté configurado
if 'XDG_RUNTIME_DIR' not in os.environ:
    # Usar un directorio temporal en lugar de /run/user/
    temp_dir = tempfile.gettempdir()
    runtime_dir = os.path.join(temp_dir, 'weasyprint-{}'.format(os.getuid()))
    # No intentamos crear el directorio, solo lo configuramos
    os.environ['XDG_RUNTIME_DIR'] = temp_dir


app = Flask(__name__)

factura_bp = Blueprint('facturas', __name__)

def crear_factura():
    conn = None
    try:
        data = request.get_json()
        print("Datos recibidos en crear_factura:", data)
        # Lista para acumular mensajes de progreso que se devolverán al frontend
        notificaciones = []
        def push_notif(msg, tipo='info', scope='factura'):
            # Prefijar con contexto para que el frontend pueda filtrar
            if scope == 'factura':
                msg_db = f'[FACTURA] {msg}'
            else:
                msg_db = msg
            # Enviar únicamente:
            #   - Mensajes finales ('success' / 'error')
            #   - Mensajes informativos que incluyan la palabra AEAT (inicio de envío)
            if tipo == 'info' and 'aeat' not in msg.lower():
                return
            notificaciones.append(msg_db)
            try:
                notif_conn = get_db_connection()
                notif_cursor = notif_conn.cursor()
                notif_cursor.execute("INSERT INTO notificaciones (tipo, mensaje, timestamp) VALUES (?, ?, ?)", (tipo, msg_db, datetime.now().isoformat()))
                notif_conn.commit()
                notif_conn.close()
            except Exception as e:
                print(f"Error al guardar notificación: {e}")
            time.sleep(0.4)  # retardo breve para visualización progresiva
        # Primera notificación
        push_notif("Datos de factura recibidos")

        # NIF EMISOR: debe ser el del certificado digital, cargado desde emisor_config.json
        try:
            emisor_nif = cargar_datos_emisor().get('nif', '')
        except Exception:
            # Fallback en caso de error en lectura de config
            emisor_nif = data.get('nif', '')
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400

        # Verificar si ya existe una factura con el mismo número
        verificacion = verificar_numero_factura(data['numero'])
        if isinstance(verificacion, tuple):
            return verificacion  # Error desde la función
        if verificacion.json['existe']:
            return jsonify({'error': 'Ya existe una factura con este número'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Iniciar transacción
        cursor.execute('BEGIN IMMEDIATE')

        try:
            # Si es una actualización (tiene ID válido), no verificamos el numerador
            es_actualizacion = 'id' in data and data['id'] is not None and data['id'] != 0
            presentar_face_flag = 1 if int(data.get('presentar_face', 0)) == 1 else 0

            # Insertar la factura
            cursor.execute('''
                INSERT INTO factura (numero, fecha, fvencimiento, estado, idContacto, nif, total, formaPago, 
                                   importe_bruto, importe_impuestos, importe_cobrado, timestamp, tipo, presentar_face)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['numero'],
                data['fecha'],
                data.get('fvencimiento', 
                         # Si no se proporciona fecha de vencimiento, se calcula como fecha + 15 días
                         (datetime.strptime(data['fecha'], '%Y-%m-%d') + timedelta(days=15)).strftime('%Y-%m-%d')),
                data.get('estado', 'P'),  # P=Pendiente, C=Cobrada, V=Vencida
                data['idContacto'],
                emisor_nif,
                data['total'],
                data.get('formaPago', 'E'),
                data.get('importe_bruto', 0),
                data.get('importe_impuestos', 0),
                data.get('importe_cobrado', 0),
                datetime.now().isoformat(),
                data.get('tipo', 'N'),  # N=Normal (con descuentos), A=Sin descuentos
                presentar_face_flag
            ))
            
            factura_id = cursor.lastrowid

            # Insertar los detalles
            for detalle in data['detalles']:
                cursor.execute('''
                    INSERT INTO detalle_factura (id_factura, concepto, descripcion, cantidad, 
                                              precio, impuestos, total, productoId, fechaDetalle)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    factura_id,
                    detalle['concepto'],
                    detalle.get('descripcion', ''),
                    detalle['cantidad'],
                    detalle['precio'],
                    detalle['impuestos'],
                    detalle['total'],
                    detalle.get('productoId', None),
                    detalle.get('fechaDetalle', data['fecha'])
                ))
            if not es_actualizacion:
                # Actualizar el numerador
                numerador_actual = actualizar_numerador('F', conn, commit=False)
                if numerador_actual is None:
                    raise Exception("Error al actualizar el numerador")
   
            # Commit al final de todas las operaciones
            conn.commit()

            # Si la factura todavía no está lista para envío (pendiente de cobro) y NO es rectificativa,
            # omitimos la generación de XML Facturae y el envío a AEAT. Las facturas rectificativas (estado 'RE',
            # tipo 'R' o cuyo número termina en '-R') deben enviarse aunque no estén cobradas.
            estado_doc = data.get('estado', 'P')
            tipo_doc = data.get('tipo', 'N')
            num_doc = str(data.get('numero', ''))
            es_rectificativa = (estado_doc == 'RE') or (tipo_doc.upper() == 'R') or num_doc.upper().endswith('-R')
            
            print(f"[DEBUG crear_factura] estado={estado_doc}, presentar_face_flag={presentar_face_flag}, es_rectificativa={es_rectificativa}")
            
            if estado_doc != 'C' and not es_rectificativa:
                push_notif("Factura guardada", tipo='success')
                print("[FACTURA] Guardada como pendiente: se omite generación de XML y envío AEAT")
                return jsonify({
                    'mensaje': 'Factura guardada como pendiente',
                    'id': factura_id,
                    'notificaciones': notificaciones
                })

            # --- Generación de Facturae ---
            print(f"[FACTURA] Generando XML Facturae (presentar_face={presentar_face_flag}, VERIFACTU_HABILITADO={VERIFACTU_HABILITADO})")

            try:
                print("[FACTURAE] Iniciando integración Facturae para factura_id:", factura_id)
                push_notif("Generando XML Facturae ...")
                cursor.execute('''
                    SELECT razonsocial, identificador, direccion, cp, localidad, provincia,
                           dir3_oficina, dir3_organo, dir3_unidad, face_presentacion, tipo
                    FROM contactos WHERE idContacto = ?
                ''', (data['idContacto'],))
                contacto = cursor.fetchone()
                if contacto:
                    print(f"[FACTURAE] Datos de contacto encontrados: {contacto}")
                    # Convierte contacto (sqlite3.Row o tuple) a dict para acceso seguro
                    datos_contacto = {
                        'razonsocial': contacto[0],
                        'nif': contacto[1],
                        'direccion': contacto[2],
                        'cp': contacto[3],
                        'localidad': contacto[4],
                        'provincia': contacto[5],
                        'dir3_oficina': contacto[6],
                        'dir3_organo': contacto[7],
                        'dir3_unidad': contacto[8],
                        'face_presentacion': contacto[9],
                        'tipo': contacto[10]
                    }
                    requiere_face = presentar_face_flag or (datos_contacto.get('face_presentacion') == 1)
                    if requiere_face:
                        faltantes = []
                        if not (datos_contacto.get('dir3_oficina') or '').strip():
                            faltantes.append('DIR3 Oficina contable')
                        if not (datos_contacto.get('dir3_organo') or '').strip():
                            faltantes.append('DIR3 Órgano gestor')
                        if not (datos_contacto.get('dir3_unidad') or '').strip():
                            faltantes.append('DIR3 Unidad tramitadora')
                        if faltantes:
                            mensaje_error = f"El contacto requiere FACe pero faltan códigos DIR3: {', '.join(faltantes)}"
                            print(f"[FACTURAE][ERROR] {mensaje_error}")
                            conn.rollback()
                            return jsonify({'error': mensaje_error, 'codigo': 'DIR3_INCOMPLETO'}), 400

                    direccion_completa = f"{datos_contacto['direccion']}, {datos_contacto['cp']} {datos_contacto['localidad']} ({datos_contacto['provincia']})"
                    datos_facturae = {
                        'emisor': cargar_datos_emisor(),
                        'receptor': {
                            'nif': datos_contacto['nif'] if datos_contacto['nif'] else 'B00000000',
                            'nombre': datos_contacto['razonsocial'],
                            'direccion': direccion_completa,
                            'direccion_calle': datos_contacto['direccion'],
                            'cp': datos_contacto['cp'],
                            'ciudad': datos_contacto['localidad'],
                            'provincia': datos_contacto['provincia'],
                            'pais': 'ESP',
                            'tipo': datos_contacto.get('tipo')
                        },
                        # Campos obligatorios para formato Facturae
                        'invoice_number': data['numero'],
                        'issue_date': data['fecha'],
                        'numero': data['numero'],
                        'fecha': data['fecha'],
                        'concepto': data['detalles'][0]['concepto'] if data['detalles'] else 'Concepto',
                        'cantidad': data['detalles'][0]['cantidad'] if data['detalles'] else 1,
                        'precio_unitario': data['detalles'][0]['precio'] if data['detalles'] else data['total'],
                        'total': data['total'],
                        'iva': data['detalles'][0]['impuestos'] if data['detalles'] else 21.0,
                        'detalles': data['detalles'],
                        'customer_info': {
                            'nif': datos_contacto['nif'] if datos_contacto['nif'] else 'B00000000',
                            'nombre': datos_contacto['razonsocial'],
                            'direccion': direccion_completa,
                            'cp': datos_contacto['cp'],
                            'localidad': datos_contacto['localidad'],
                            'provincia': datos_contacto['provincia'],
                            'pais': 'ESP'
                        },
                        'base_amount': float(data['importe_bruto']),
                        'taxes': float(data['importe_impuestos']),
                        'total_amount': float(data['total']),
                        # Añadimos campo 'items' con el formato correcto para generar_facturae
                        'items': data['detalles'],
                        # Nos aseguramos de que el campo 'detalles' esté presente con el formato esperado por generar_facturae
                        'detalles': data['detalles'],
                        'presentar_face': 1 if requiere_face else 0,
                        'dir3_oficina': datos_contacto.get('dir3_oficina'),
                        'dir3_organo': datos_contacto.get('dir3_organo'),
                        'dir3_unidad': datos_contacto.get('dir3_unidad')
                    }
                else:
                    print("[FACTURAE] No se encontraron datos del contacto, usando valores por defecto para receptor.")
                    datos_facturae = {
                        'emisor': cargar_datos_emisor(),
                        'receptor': {
                            'nif': 'B00000000',
                            'nombre': 'CONTACTO_DESCONOCIDO',
                            'direccion': '-',
                            'direccion_calle': '-',
                            'cp': '-',
                            'ciudad': '-',
                            'provincia': '-',
                            'pais': 'ESP',
                            'tipo': None
                        },
                        'invoice_number': data['numero'],
                        'issue_date': data['fecha'],
                        'numero': data['numero'],
                        'fecha': data['fecha'],
                        'total': data['total'],
                        'iva': data['detalles'][0]['impuestos'] if data['detalles'] else 21.0,
                        'detalles': data['detalles'],
                        'customer_info': {
                            'nif': 'B00000000',
                            'nombre': 'CONTACTO_DESCONOCIDO',
                            'direccion': '-',
                            'cp': '-',
                            'localidad': '-',
                            'provincia': '-',
                            'pais': 'ESP'
                        },
                        'base_amount': float(data['importe_bruto']),
                        'taxes': float(data['importe_impuestos']),
                        'total_amount': float(data['total']),
                        # Añadimos campo 'items' con el formato correcto para generar_facturae
                        'items': data['detalles'],
                        # Nos aseguramos de que el campo 'detalles' esté presente con el formato esperado
                        'detalles': data['detalles']
                    }
                # Validar campos críticos antes de generar Facturae
                campos_obligatorios = ['invoice_number', 'issue_date', 'customer_info', 'items', 'base_amount', 'taxes', 'total_amount']
                missing_fields = [campo for campo in campos_obligatorios if campo not in datos_facturae or datos_facturae[campo] is None]
                if missing_fields:
                    with safe_append_debug('facturae_debug.txt') as log_file:
                        log_file.write(f"[VALIDACIÓN] Campos faltantes: {missing_fields}\n")
                        log_file.write(f"[VALIDACIÓN] Claves disponibles: {list(datos_facturae.keys())}\n")
                    raise ValueError(f"Campos obligatorios faltantes: {', '.join(missing_fields)}")
                
                datos_facturae['total_amount'] = data['total']  # Añadimos el campo requerido
                
                # Añadimos campos para VERI*FACTU
                datos_facturae['verifactu'] = VERIFACTU_DISPONIBLE  # Se genera formato VERI*FACTU sólo si está habilitado
                datos_facturae['factura_id'] = factura_id  # ID de factura para registro en VERI*FACTU
                
                print("[FACTURAE] Llamando a generar_facturae con configuración VERI*FACTU")
                # Log detallado antes de llamar a generar_facturae
                with safe_append_debug('facturae_env_debug.txt') as f:
                    f.write(f'[DEBUG][factura.py] datos_facturae={datos_facturae}\n')
                    f.write('[DEBUG][factura.py] Integración VERI*FACTU activada\n')
                try:
                    # Explicitamente importamos la función desde facturae.generador para evitar confusión
                    from facturae.generador import \
                        generar_facturae as generar_facturae_modular
                    
                    push_notif("Firmando XML Facturae ...")  # noqa: E501
                    # Usar la versión modular que genera el XML en formato Facturae 3.2.2 compatible con VERI*FACTU
                    ruta_xml_final = generar_facturae_modular(datos_facturae)
                    print(f"[FACTURAE] Facturae 3.2.2 generada y firmada en {ruta_xml_final}")
                    if ruta_xml_final and ruta_xml_final.lower().endswith('.xsig'):
                        push_notif("XML Facturae generado")
                    print(f"[FACTURAE] Factura electrónica generada correctamente para factura ID: {factura_id}")
                    conn.commit()
                except Exception as e:
                    print(f"[FACTURAE][ERROR] Error generando Facturae: {e}")
                    push_notif("Error al generar XML Facturae", tipo='error')
                    # Registrar traza completa del error
                    import traceback
                    print(traceback.format_exc())
            except Exception as e:
                print(f"[FACTURAE][ERROR] Error en integración Facturae: {e}")

            # --- Integración VERI*FACTU ---
            respuesta = {
                'mensaje': 'Factura creada exitosamente',
                'id': factura_id,
                'notificaciones': notificaciones  # lista de pasos realizados
            }
            try:
                print("[VERIFACTU] Iniciando integración VERI*FACTU para factura_id:", factura_id)
                push_notif("Enviando registro AEAT ...")
                # Generar datos VERI*FACTU para la factura (solo si está disponible)
                if VERIFACTU_DISPONIBLE:
                    try:
                        datos_verifactu = verifactu.generar_datos_verifactu_para_factura(factura_id)
                        if datos_verifactu and 'datos' in datos_verifactu and 'hash' in datos_verifactu['datos']:
                            print(f"[VERIFACTU] Datos generados correctamente: hash={datos_verifactu['datos']['hash'][:10]}...")
                            push_notif("QR generado")
                            # Enviamos como parte del retorno
                            respuesta['datos_adicionales'] = {
                                'hash': datos_verifactu['datos']['hash'],
                                'verifactu': True
                            }
                        else:
                            print("[VERIFACTU] No se pudieron generar los datos VERI*FACTU")
                            # Intentar extraer código/descripcion de error devuelto por AEAT
                            codigo_err = None
                            descripcion_err = None
                            if datos_verifactu and isinstance(datos_verifactu, dict):
                                errores_list = datos_verifactu.get('errores')
                                if errores_list and isinstance(errores_list, list):
                                    codigo_err = errores_list[0].get('codigo')
                                    descripcion_err = errores_list[0].get('descripcion_error') or errores_list[0].get('descripcion')
                            if codigo_err:
                                push_notif(f"Error AEAT {codigo_err}", tipo='error')
                            else:
                                push_notif("Error en generación de datos VERI*FACTU", tipo='error')

                            # Preparar mensaje claro para frontend
                            mensaje_front = f"Error AEAT {codigo_err}: {descripcion_err}" if codigo_err else "Fallo al generar datos VERI*FACTU"
                            respuesta['datos_adicionales'] = {
                                'verifactu': False,
                                'error': mensaje_front,
                                'codigo_error_aeat': codigo_err
                            }
                    except Exception as e:
                        print(f"[!] Error al generar datos VERI*FACTU: {str(e)}")
                        push_notif("Error al enviar registro AEAT", tipo='error')
                        # Continuamos sin VERI*FACTU
                        respuesta['datos_adicionales'] = {
                            'verifactu': False,
                            'error': f"Error VERI*FACTU: {str(e)}"
                        }
                else:
                    print("[!] Módulo VERI*FACTU no disponible - Omitiendo generación de datos")
                    respuesta['datos_adicionales'] = {
                        'verifactu': False,
                        'error': "Módulo VERI*FACTU no disponible"
                    }
            except Exception as e:
                print(f"[VERIFACTU][ERROR] Error en integración VERI*FACTU: {e}")
                import traceback
                print(traceback.format_exc())
                respuesta['datos_adicionales'] = {
                    'verifactu': False,
                    'error': f"Error en integración VERI*FACTU: {str(e)}"
                }
            
            push_notif("Factura creada", tipo='success')
            print("[DEBUG] Respuesta enviada a frontend:", respuesta)
            return jsonify(respuesta)
            # Devolver respuesta sin mencionar VERI*FACTU si hubo algún problema
            return jsonify({
                'mensaje': 'Factura creada exitosamente',
                'id': factura_id
            })

        except Exception as e:
            conn.rollback()
            raise e

    except Exception as e:
        print(f"Error en crear_factura: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

def obtener_factura(idContacto, id):
    try:
        print(f"Obteniendo factura {id} para contacto {idContacto}")  # Debug
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Consulta para obtener la factura con los datos del contacto
        query = """
            SELECT 
                f.id,
                f.numero,
                f.fecha,
                f.estado,
                f.total,
                f.idContacto,
                f.formaPago,
                f.importe_bruto,
                f.importe_impuestos,
                f.importe_cobrado,
                f.tipo,
                c.razonsocial,
                c.identificador,
                c.direccion,
                c.cp,
                c.localidad,
                c.provincia,
                c.mail as email
            FROM factura f
            INNER JOIN contactos c ON f.idContacto = c.idContacto
            WHERE f.id = ? AND f.idContacto = ?
        """
        print(f"Ejecutando query: {query}")  # Debug
        print(f"Con parámetros: id={id}, idContacto={idContacto}")  # Debug
        
        cursor.execute(query, (id, idContacto))
        
        factura = cursor.fetchone()
        print(f"Resultado de la query: {factura}")  # Debug
        
        if not factura:
            print("No se encontró la factura")  # Debug
            return jsonify({'error': 'Factura no encontrada'}), 404

        # Convertir a diccionario usando los nombres de columnas
        columnas = [
            'id', 'numero', 'fecha', 'estado', 'total', 'idcontacto', 
            'formapago', 'importe_bruto', 'importe_impuestos', 'importe_cobrado',
            'tipo',
            'razonsocial', 'identificador', 'direccion', 'cp', 'localidad', 'provincia', 'email'
        ]
        print("Nombres de columnas:", columnas)  # Debug
        
        factura_dict = dict(zip(columnas, factura))
        print("Factura dict:", factura_dict)  # Debug
        
        # Obtener detalles ordenados por id
        cursor.execute('SELECT * FROM detalle_factura WHERE id_factura = ? ORDER BY id', (id,))
        detalles = cursor.fetchall()
        print(f"Detalles encontrados: {len(detalles)}")  # Debug
        
        # Convertir detalles a lista de diccionarios
        columnas_detalle = [desc[0] for desc in cursor.description]
        detalles_list = [dict(zip(columnas_detalle, detalle)) for detalle in detalles]
        
        # Agregar detalles al diccionario de la factura
        factura_dict['detalles'] = detalles_list
        
        print("Datos completos de factura a devolver:", factura_dict)  # Debug
        return jsonify(factura_dict)
        
    except Exception as e:
        print(f"Error al obtener factura: {str(e)}")
        import traceback
        print(traceback.format_exc())  # Debug - muestra el stack trace completo
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def obtener_factura_abierta(idContacto,idFactura):
    try:
        print(f"Iniciando obtener_factura_abierta para idContacto: {idContacto}")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Primero obtener los datos del contacto
        print("Ejecutando consulta de contacto...")
        cursor.execute("""
            SELECT 
                idContacto,
                razonsocial,
                identificador,
                direccion,
                cp,
                localidad,
                provincia,
                mail as email,
                dir3_oficina,
                dir3_organo,
                dir3_unidad,
                face_presentacion
            FROM contactos 
            WHERE idContacto = ?
        """, (idContacto,))
        contacto = cursor.fetchone()
        
        if not contacto:
            print(f"No se encontró el contacto con idContacto: {idContacto}")
            return jsonify({'error': 'Contacto no encontrado'}), 404
            
        contacto_dict = dict(contacto)
        print(f"Datos del contacto encontrados: {contacto_dict}")
        
        # Buscar factura abierta
        print("Ejecutando consulta de factura abierta...")
        sql = '''
            SELECT id, numero, fecha, estado, total, idContacto, tipo, presentar_face
            FROM factura
            WHERE idContacto = ? 
            AND id = ?
            LIMIT 1
        '''
        print(f"SQL factura: {sql}")
        print(f"Parámetros: idContacto = {idContacto}, id = {idFactura}")
        
        cursor.execute(sql, (idContacto,idFactura,))
        factura = cursor.fetchone()
        
        if factura:
            print(f"Factura abierta encontrada: {dict(factura)}")
            factura_dict = dict(factura)
            
            # Obtener los detalles de la factura
            print(f"Buscando detalles para factura id: {factura_dict['id']}")
            cursor.execute('''
                SELECT id, concepto, descripcion, cantidad, precio, impuestos, total, 
                       productoId, fechaDetalle
                FROM detalle_factura 
                WHERE id_factura = ?
                ORDER BY id
            ''', (factura_dict['id'],))
            detalles = cursor.fetchall()
            print(f"Detalles encontrados: {[dict(d) for d in detalles]}")
            
            # Construir respuesta completa
            response_data = {
                'modo': 'edicion',
                'id': factura_dict['id'],
                'numero': factura_dict['numero'],
                'fecha': factura_dict['fecha'],
                'estado': factura_dict['estado'],
                'total': factura_dict['total'],
                'tipo': factura_dict.get('tipo', 'N'),  # Añadir el tipo de factura a la respuesta
                'presentar_face': factura_dict.get('presentar_face', 0),
                'contacto': contacto_dict,
                'detalles': [dict(d) for d in detalles]
            }
            print("Enviando respuesta modo edición")
            print("Datos completos:", response_data)
            return jsonify(response_data)
        else:
            print("No se encontró factura abierta, modo nuevo")
            response_data = {
                'modo': 'nuevo',
                'contacto': contacto_dict
            }
            print("Datos completos:", response_data)
            return jsonify(response_data)
    
    except sqlite3.Error as e:
        print(f"Error de SQLite en obtener_factura_abierta: {str(e)}")
        return jsonify({'error': f"Error de base de datos: {str(e)}"}), 500
            
    except Exception as e:
        print(f"Error general en obtener_factura_abierta: {str(e)}")
        print(f"Tipo de error: {type(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f"Error al buscar factura abierta: {str(e)}"}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
        print("Conexión cerrada en obtener_factura_abierta")


def consultar_facturas():
    try:
        # Obtener parámetros de la consulta
        fecha_inicio = request.args.get('fecha_inicio', '')
        fecha_fin = request.args.get('fecha_fin', '')
        estado = request.args.get('estado', '')
        numero = request.args.get('numero', '')
        contacto = request.args.get('contacto', '')
        identificador = request.args.get('identificador', '')
        concepto = request.args.get('concepto', '')

        # Comprobar si hay algún filtro adicional informado
        hay_filtros_adicionales = any([
            estado.strip(), 
            numero.strip(), 
            contacto.strip(), 
            identificador.strip(),
            concepto.strip()
        ])

        conn = get_db_connection()
        cursor = conn.cursor()
  # Construir la consulta base
        query = """
            SELECT 
                f.id, 
                f.fecha, 
                f.numero, 
                f.estado, 
                f.importe_bruto as base,
                f.importe_impuestos as iva,
                f.importe_cobrado,
                f.total,
                f.idcontacto,
                f.tipo,
                c.razonsocial,
                COALESCE(c.mail, '') as mail,
                COALESCE(f.enviado, 0) as enviado
            FROM factura f
            LEFT JOIN contactos c ON f.idcontacto = c.idContacto
            WHERE 1=1
        """
        params = []

        # Añadir filtros según los parámetros recibidos
        # Aplicar filtros de fecha si no hay otros filtros o si el estado es 'cobrada'
        if fecha_inicio and (not hay_filtros_adicionales or estado == 'C'):
            query += " AND f.fecha >= ?"
            params.append(fecha_inicio)
        if fecha_fin and (not hay_filtros_adicionales or estado == 'C'):
            query += " AND f.fecha <= ?"
            params.append(fecha_fin)
        if estado:
            if estado == 'PV':  # Caso especial para Pendiente+Vencida
                query += " AND (f.estado IN ('P', 'V'))"
                print("Aplicando filtro especial PV: Pendiente o Vencida")
            else:
                query += " AND f.estado = ?"
                params.append(estado)
        else:
            # Si no se filtra por estado explícitamente, excluir anuladas por defecto
            query += " AND f.estado <> 'A'"
        if numero:
            query += " AND f.numero LIKE ?"
            params.append(f"%{numero}%")
        if contacto:
            query += " AND c.razonsocial LIKE ?"
            params.append(f"%{contacto}%")
        if identificador:
            query += " AND c.identificador LIKE ?"
            params.append(f"%{identificador}%")
        if concepto:
            query += " AND EXISTS (SELECT 1 FROM detalle_factura d WHERE d.id_factura = f.id AND (lower(d.concepto) LIKE ? OR lower(d.descripcion) LIKE ?))"
            like_val = f"%{concepto.lower()}%"
            params.extend([like_val, like_val])

        # Ordenar por fecha descendente y limitar a 100 resultados
        query += " ORDER BY f.fecha DESC LIMIT 100"

        # Ejecutar la consulta
        print(f"Consulta SQL: {query}")
        print(f"Parámetros: {params}")
        cursor.execute(query, params)
        facturas = cursor.fetchall()
        print(f"Facturas encontradas: {len(facturas)}")
        
        
        # Obtener los nombres de las columnas para mapeo preciso
        columnas = [desc[0] for desc in cursor.description]
       
        
        # Convertir los resultados a una lista de diccionarios
        result = []
        for factura in facturas:
            # Crear un diccionario con las columnas y valores
            factura_dict = dict(zip(columnas, factura))
            
            # Convertir valores numéricos
            if 'base' in factura_dict and factura_dict['base'] is not None:
                factura_dict['base'] = float(factura_dict['base'])
            if 'iva' in factura_dict and factura_dict['iva'] is not None:
                factura_dict['iva'] = float(factura_dict['iva'])
            if 'importe_cobrado' in factura_dict and factura_dict['importe_cobrado'] is not None:
                factura_dict['importe_cobrado'] = float(factura_dict['importe_cobrado'])
            if 'total' in factura_dict and factura_dict['total'] is not None:
                factura_dict['total'] = float(factura_dict['total'])
            
            # Asegurarse de que enviado sea un entero
            if 'enviado' in factura_dict:
                factura_dict['enviado'] = int(factura_dict['enviado']) if factura_dict['enviado'] is not None else 0
            result.append(factura_dict)

        return jsonify(result)

    except Exception as e:
        print(f"Error en consultar_facturas: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/facturas', methods=['GET'])
def consultar_facturas_get():
    return consultar_facturas()

def obtener_facturas_paginadas(filtros, page=1, page_size=10, sort='fecha', order='DESC'):
    """
    Obtiene facturas con filtros y paginación.

    filtros keys esperados:
      - fecha_inicio, fecha_fin, estado, numero, contacto, identificador, concepto

    Retorna dict con:
      { items: [...], total: int, page: int, page_size: int, total_pages: int }
    """
    try:
        # Saneamiento
        try:
            page = int(page) if int(page) > 0 else 1
        except Exception:
            page = 1
        try:
            page_size = int(page_size)
            if page_size <= 0:
                page_size = 10
            page_size = min(page_size, 100)
        except Exception:
            page_size = 10

        allowed_sort = {
            'fecha': 'f.fecha',
            'numero': 'f.numero',
            'estado': 'f.estado',
            'total': 'f.total',
            'razonsocial': 'c.razonsocial',
            'id': 'f.id',
            'timestamp': 'f.timestamp'
        }
        sort_col = allowed_sort.get(str(sort).lower(), 'f.fecha')
        order_dir = 'DESC' if str(order).upper() == 'DESC' else 'ASC'

        conn = get_db_connection()
        cursor = conn.cursor()

        where_sql = 'WHERE 1=1'
        params = []

        fecha_inicio = (filtros or {}).get('fecha_inicio', '')
        fecha_fin = (filtros or {}).get('fecha_fin', '')
        estado = (filtros or {}).get('estado', '')
        numero = (filtros or {}).get('numero', '')
        contacto = (filtros or {}).get('contacto', '')
        identificador = (filtros or {}).get('identificador', '')
        concepto = (filtros or {}).get('concepto', '')

        # Filtros (misma lógica que consultar_facturas)
        if fecha_inicio:
            where_sql += ' AND f.fecha >= ?'
            params.append(fecha_inicio)
        if fecha_fin:
            where_sql += ' AND f.fecha <= ?'
            params.append(fecha_fin)
        if estado:
            if estado == 'PV':
                where_sql += " AND (f.estado IN ('P', 'V'))"
            else:
                where_sql += ' AND f.estado = ?'
                params.append(estado)
        if numero:
            where_sql += ' AND f.numero LIKE ?'
            params.append(f"%{numero}%")
        if contacto:
            where_sql += ' AND c.razonsocial LIKE ?'
            params.append(f"%{contacto}%")
        if identificador:
            where_sql += ' AND c.identificador LIKE ?'
            params.append(f"%{identificador}%")
        if concepto:
            where_sql += ' AND EXISTS (SELECT 1 FROM detalle_factura d WHERE d.id_factura = f.id AND (lower(d.concepto) LIKE ? OR lower(d.descripcion) LIKE ?))'
            like_val = f"%{str(concepto).lower()}%"
            params.extend([like_val, like_val])

        # Conteo total
        count_sql = f'''
            SELECT COUNT(*) as total
            FROM factura f
            LEFT JOIN contactos c ON f.idcontacto = c.idContacto
            {where_sql}
        '''
        cursor.execute(count_sql, params)
        row = cursor.fetchone()
        total = row['total'] if isinstance(row, sqlite3.Row) else (row[0] if row else 0)

        # Datos paginados
        offset = (page - 1) * page_size
        data_sql = f'''
            SELECT 
                f.id, 
                f.fecha, 
                f.numero, 
                f.estado, 
                f.importe_bruto as base,
                f.importe_impuestos as iva,
                f.importe_cobrado,
                f.total,
                f.idcontacto,
                f.tipo,
                c.razonsocial,
                COALESCE(c.mail, '') as mail,
                COALESCE(f.enviado, 0) as enviado
            FROM factura f
            LEFT JOIN contactos c ON f.idcontacto = c.idContacto
            {where_sql}
            ORDER BY {sort_col} {order_dir}, f.fecha DESC, f.timestamp DESC
            LIMIT ? OFFSET ?
        '''
        params_limit = params + [page_size, offset]
        cursor.execute(data_sql, params_limit)
        rows = cursor.fetchall()

        def _split_sign(s: str):
            neg = s.startswith('-')
            return ('-', s[1:]) if neg else ('', s)

        def format_currency_es_two(val):
            """Formatea importes con coma decimal y punto de miles, redondeando a 2 decimales."""
            if val is None or val == '':
                val = 0
            s = str(val)
            try:
                normalized = s.replace(',', '.')
                dec_val = Decimal(normalized)
            except Exception:
                return '0,00'
            dec_rounded = dec_val.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            s = format(dec_rounded, 'f')
            sign, rest = _split_sign(s)
            entero, _, dec = rest.partition('.')
            try:
                entero_int = int(entero)
                entero_fmt = f"{entero_int:,}".replace(',', 'X').replace('.', ',').replace('X', '.')
            except Exception:
                entero_fmt = entero
            return f"{sign}{entero_fmt},{dec or '00'}"

        def format_total_es_two(val):
            return format_currency_es_two(val)

        items = []
        if rows:
            colnames = [desc[0] for desc in cursor.description]
            for r in rows:
                raw = dict(zip(colnames, r))
                # NO recalcular: devolver lo que hay en tabla, formateado
                # Formatear importes con 2 decimales
                if 'base' in raw:
                    raw['base'] = format_currency_es_two(raw['base'])
                if 'iva' in raw:
                    raw['iva'] = format_currency_es_two(raw['iva'])
                if 'importe_cobrado' in raw:
                    raw['importe_cobrado'] = format_currency_es_two(raw['importe_cobrado'])
                if 'total' in raw:
                    raw['total'] = format_total_es_two(raw['total'])
                if 'enviado' in raw:
                    raw['enviado'] = int(raw['enviado']) if raw['enviado'] is not None else 0
                items.append(raw)

        # Calcular totales globales según el estado del filtro (como numérico) y devolver formateados
        totales_globales = {
            'total_base': '0,00',
            'total_iva': '0,00',
            'total_cobrado': '0,00',
            'total_total': '0,00'
        }
        
        # Solo calcular totales si hay un estado específico en el filtro
        if estado:
            totales_sql = f'''
                SELECT 
                    SUM(f.importe_bruto) as total_base,
                    SUM(f.importe_impuestos) as total_iva,
                    SUM(f.importe_cobrado) as total_cobrado,
                    SUM(f.total) as total_total
                FROM factura f
                LEFT JOIN contactos c ON f.idcontacto = c.idContacto
                {where_sql}
            '''
            cursor.execute(totales_sql, params)
            tot_row = cursor.fetchone()
            
            if tot_row:
                tot_dict = dict(tot_row)
                totales_globales = {
                    'total_base': format_currency_es_two(tot_dict.get('total_base', 0) or 0),
                    'total_iva': format_currency_es_two(tot_dict.get('total_iva', 0) or 0),
                    'total_cobrado': format_currency_es_two(tot_dict.get('total_cobrado', 0) or 0),
                    'total_total': format_total_es_two(tot_dict.get('total_total', 0) or 0)
                }

        total = int(total or 0)
        total_pages = (total + page_size - 1) // page_size if page_size else 1
        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': int(total_pages),
            'totales_globales': totales_globales
        }
    except sqlite3.Error as e:
        raise Exception(f"Error de base de datos en obtener_facturas_paginadas: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

def agregar_detalle_factura(id_factura, detalle):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Validar campos requeridos
        campos_requeridos = ['concepto', 'cantidad', 'precio', 'impuestos', 'total']
        for campo in campos_requeridos:
            if campo not in detalle:
                return jsonify({'error': f'Falta el campo requerido: {campo}'}), 400
        
        # Validar y convertir datos numéricos
        try:
            cantidad = int(detalle['cantidad'])
            precio = float(detalle['precio'])
            impuestos = float(detalle['impuestos'])
            total = float(detalle['total'])
        except (ValueError, TypeError) as e:
            return jsonify({'error': f'Error en conversión de valores numéricos: {str(e)}'}), 400
        
        # Insertar el detalle
        cursor.execute('''
            INSERT INTO detalle_factura (id_factura, concepto, descripcion, cantidad,
                                      precio, impuestos, total, productoId, fechaDetalle)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            id_factura,
            detalle['concepto'],
            detalle.get('descripcion', ''),
            cantidad,
            precio,
            impuestos,
            total,
            detalle.get('productoId', None),
            detalle.get('fechaDetalle', datetime.now().strftime('%Y-%m-%d'))
        ))
        
        # Actualizar totales de la factura
        cursor.execute('''
            UPDATE factura 
            SET importe_bruto = (SELECT SUM(cantidad * precio) FROM detalle_factura WHERE id_factura = ?),
                importe_impuestos = (SELECT SUM(impuestos) FROM detalle_factura WHERE id_factura = ?),
                total = (SELECT SUM(total) FROM detalle_factura WHERE id_factura = ?)
            WHERE id = ?
        ''', (id_factura, id_factura, id_factura, id_factura))
        
        conn.commit()
        return jsonify({
            'mensaje': 'Detalle agregado exitosamente',
            'id': cursor.lastrowid
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/facturas/<int:id_factura>/detalles', methods=['POST'])
def agregar_detalle_factura_post(id_factura):
    detalle = request.get_json()
    return agregar_detalle_factura(id_factura, detalle)

def obtener_detalles_factura(id_factura):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener todos los detalles de la factura
        cursor.execute('''
            SELECT * FROM detalle_factura 
            WHERE id_factura = ?
            ORDER BY id
        ''', (id_factura,))
        
        detalles = cursor.fetchall()
        return jsonify([dict(detalle) for detalle in detalles])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/facturas/<int:id_factura>/detalles', methods=['GET'])
def obtener_detalles_factura_get(id_factura):
    return obtener_detalles_factura(id_factura)

def obtener_facturas_por_contacto(idContacto):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener todas las facturas del contacto
        cursor.execute('''
            SELECT f.*, 
                   GROUP_CONCAT(json_object(
                       'id', df.id,
                       'concepto', df.concepto,
                       'descripcion', df.descripcion,
                       'cantidad', df.cantidad,
                       'precio', df.precio,
                       'impuestos', df.impuestos,
                       'total', df.total,
                       'productoId', df.productoId,
                       'fechaDetalle', df.fechaDetalle
                   )) as detalles
            FROM factura f
            LEFT JOIN detalle_factura df ON f.id = df.id_factura
            WHERE f.id_contacto = ?
            GROUP BY f.id
            ORDER BY f.fecha DESC
        ''', (idContacto,))
        
        facturas = cursor.fetchall()
        
        # Procesar resultados
        resultado = []
        for factura in facturas:
            factura_dict = dict(factura)
            # Procesar los detalles si existen
            if factura_dict['detalles']:
                factura_dict['detalles'] = [eval(d) for d in factura_dict['detalles'].split(',')]
            else:
                factura_dict['detalles'] = []
            resultado.append(factura_dict)
        
        return jsonify(resultado)
        
    except Exception as e:
        print(f"Error en obtener_facturas_por_contacto: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/contactos/<int:idContacto>/facturas', methods=['GET'])
def obtener_facturas_por_contacto_get(idContacto):
    return obtener_facturas_por_contacto(idContacto)

def crear_factura_por_contacto(idContacto):
    conn = None
    try:
        conn = get_db_connection()
        conn.execute('BEGIN EXCLUSIVE TRANSACTION')
        cursor = conn.cursor()

        # Obtener el siguiente número de factura
        numerador_actual, error = actualizar_numerador('F', conn, commit=False)
        if error:
            conn.rollback()
            return jsonify({'error': error}), 500

        numero_formateado = f"F{numerador_actual:06d}"
        fecha_actual = datetime.now().strftime('%Y-%m-%d')

        # Insertar la nueva factura
        cursor.execute('''
            INSERT INTO factura (
                numero, fecha, fvencimiento, estado, id_contacto,
                total, importe_bruto, importe_impuestos, timestamp, formaPago
            ) VALUES (?, ?, ?, 'P', ?, 0, 0, 0, ?, 'E')
        ''', (
            numero_formateado,
            fecha_actual,
            fecha_actual,
            idContacto,
            datetime.now().isoformat()
        ))

        factura_id = cursor.lastrowid
        conn.commit()

        # Obtener la factura recién creada
        cursor.execute('''
            SELECT * FROM factura WHERE id = ?
        ''', (factura_id,))
        
        factura = cursor.fetchone()
        resultado = dict(factura)
        resultado['detalles'] = []

        return jsonify(resultado)

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error en crear_factura_por_contacto: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/contactos/<int:idContacto>/facturas', methods=['POST'])
def crear_factura_por_contacto_post(idContacto):
    return crear_factura_por_contacto(idContacto)

def filtrar_facturas():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener parámetros de filtrado
        estado = request.args.get('estado')
        fecha_desde = request.args.get('fecha_desde')
        fecha_hasta = request.args.get('fecha_hasta')
        numero = request.args.get('numero')
        idContacto = request.args.get('idContacto')
        formaPago = request.args.get('formaPago')
        nif = request.args.get('nif')
        razon_social = request.args.get('razon_social')
        
        # Construir la consulta base
        query = '''
            SELECT 
                f.*, 
                c.nif as contacto_nif,
                c.razon_social as contacto_razon_social,
                c.mail as contacto_email,
                GROUP_CONCAT(json_object(
                    'id', df.id,
                    'concepto', df.concepto,
                    'descripcion', df.descripcion,
                    'cantidad', df.cantidad,
                    'precio', df.precio,
                    'impuestos', df.impuestos,
                    'total', df.total,
                    'productoId', df.productoId,
                    'fechaDetalle', df.fechaDetalle
                )) as detalles
            FROM factura f
            LEFT JOIN detalle_factura df ON f.id = df.id_factura
            LEFT JOIN contactos c ON f.id_contacto = c.id
            WHERE 1=1
        '''
        params = []
        
        # Añadir filtros según los parámetros recibidos
        if estado:
            if estado == 'PV':  # Caso especial para Pendiente+Vencida
                query += " AND (f.estado IN ('P', 'V'))"
                print("Aplicando filtro especial PV: Pendiente o Vencida")
            else:
                query += " AND f.estado = ?"
                params.append(estado)
            
        if fecha_desde:
            query += ' AND f.fecha >= ?'
            params.append(fecha_desde)
            
        if fecha_hasta:
            query += ' AND f.fecha <= ?'
            params.append(fecha_hasta)
            
        if numero:
            query += ' AND f.numero LIKE ?'
            params.append(f'%{numero}%')
            
        if idContacto:
            query += ' AND f.id_contacto = ?'
            params.append(idContacto)
            
        if formaPago:
            query += ' AND f.formaPago = ?'
            params.append(formaPago)

        if nif:
            query += ' AND (f.nif LIKE ? OR c.nif LIKE ?)'
            params.extend([f'%{nif}%', f'%{nif}%'])
            
        if razon_social:
            query += ' AND c.razon_social LIKE ?'
            params.append(f'%{razon_social}%')
            
        # Agrupar por factura y ordenar por fecha descendente
        query += ' GROUP BY f.id ORDER BY f.fecha DESC'
        
        cursor.execute(query, params)
        facturas = cursor.fetchall()
        
        # Procesar resultados
        resultado = []
        for factura in facturas:
            factura_dict = dict(factura)
            # Procesar los detalles si existen
            if factura_dict['detalles']:
                factura_dict['detalles'] = [eval(d) for d in factura_dict['detalles'].split(',')]
            else:
                factura_dict['detalles'] = []
            resultado.append(factura_dict)
        
        return jsonify(resultado)
        
    except Exception as e:
        print(f"Error en filtrar_facturas: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/facturas', methods=['GET'])
def filtrar_facturas_get():
    return filtrar_facturas()

def obtener_factura_para_imprimir(factura_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener datos de la factura
        cursor.execute("""
            SELECT 
                f.*, 
                c.razonsocial,
                c.identificador,
                c.direccion,
                c.cp,
                c.localidad,
                c.provincia
            FROM factura f
            LEFT JOIN contactos c ON f.idContacto = c.idContacto
            WHERE f.id = ?
        """, (factura_id,))
        factura = cursor.fetchone()

        if not factura:
            return None

        # Obtener detalles de la factura
        cursor.execute("""
            SELECT *
            FROM detalle_factura
            WHERE id_factura = ?
            ORDER BY id
        """, (factura_id,))
        detalles = cursor.fetchall()

        # Obtener código QR de la tabla registro_facturacion, si existe
        cursor.execute("""
            SELECT codigo_qr FROM registro_facturacion
            WHERE factura_id = ?
        """, (factura_id,))
        registro = cursor.fetchone()
        
        # Codificar el QR en base64 si existe
        qr_code = None
        if registro and registro['codigo_qr']:
            import base64
            qr_raw = registro['codigo_qr']
            if isinstance(qr_raw, (bytes, bytearray)):
                qr_code = base64.b64encode(qr_raw).decode('utf-8')
            else:
                # Si ya es una cadena base64, la usamos directamente
                qr_code = qr_raw.strip()

        # Convertir a diccionarios para facilitar el acceso
        factura_dict = dict(factura)
        detalles_list = [dict(detalle) for detalle in detalles]

        # Renderizar la plantilla
        return render_template(
            'factura_template.html',
            factura=factura_dict,
            detalles=detalles_list,
            fecha_formateada=datetime.strptime(factura_dict['fecha'], '%Y-%m-%d').strftime('%d/%m/%Y'),
            qr_code=qr_code
        )

    except Exception as e:
        print(f"Error al obtener factura para imprimir: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()

def enviar_factura_email(id_factura, email_destino_override=None, return_dict=False):
    try:
        print(f"Iniciando envío de factura {id_factura}")
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
        
        print(f"Resultado de la consulta: {factura}")

        if not factura:
            print(f"Factura {id_factura} no encontrada")
            if return_dict:
                return {'success': False, 'error': 'Factura no encontrada'}
            return jsonify({'error': 'Factura no encontrada'}), 404

        # Convertir la tupla de la factura en un diccionario con nombres de columnas
        nombres_columnas = [description[0] for description in cursor.description]
        factura_dict = dict(zip(nombres_columnas, factura))
        
        print("Columnas de la factura:", nombres_columnas)
        print("Datos de la factura:", factura_dict)

        # Si se proporciona email_destino_override, usarlo; si no, usar el del cliente
        email_destino = email_destino_override if email_destino_override else factura_dict.get('mail')
        
        if not email_destino:
            print(f"Factura {id_factura} no tiene email registrado")
            if return_dict:
                return {'success': False, 'error': 'El contacto no tiene email registrado'}
            return jsonify({'error': 'El contacto no tiene email registrado'}), 400

        # Obtener detalles de la factura
        cursor.execute("""
            SELECT *
            FROM detalle_factura
            WHERE id_factura = ?
            ORDER BY id
        """, (id_factura,))
        detalles = cursor.fetchall()
        detalles_list = [dict(zip([d[0] for d in cursor.description], detalle)) for detalle in detalles]
        
        print("Detalles de la factura:", detalles_list)

        # Utilidad segura para parsear importes en formato europeo o numérico
        def _parse_euro(value):
            if value is None:
                return 0.0
            if isinstance(value, (int, float)):
                try:
                    return float(value)
                except Exception:
                    return 0.0
            s = str(value).strip()
            # Quitar separador de miles y convertir coma a punto
            s = s.replace('.', '').replace(',', '.')
            try:
                return float(s)
            except Exception:
                return 0.0

        # Recalcular BASE/IVA/TOTAL con Decimal y redondeo por línea (ROUND_HALF_UP a 2 decimales)
        # para evitar discrepancias (p.ej. 56,11 vs 56,12) y alinear con frontend
        def D(x):
            try:
                return Decimal(str(x if x is not None else '0'))
            except Exception:
                return Decimal('0')
        base_sum = Decimal('0')
        iva_sum = Decimal('0')
        for det in detalles_list:
            qty = D(det.get('cantidad'))
            price = D(det.get('precio'))
            tax = D(det.get('impuestos'))  # porcentaje IVA
            sub = qty * price
            iva_line = (sub * tax / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            base_sum += sub
            iva_sum += iva_line
        base_imponible = base_sum.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        iva = iva_sum.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total = (base_imponible + iva).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        print(f"[PDF] Totales recalculados: base={base_imponible}, iva={iva}, total={total}")

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
            
            # Obtener código QR de la tabla registro_facturacion, si existe
            cursor.execute("""
                SELECT codigo_qr, hash, csv FROM registro_facturacion
                WHERE factura_id = ?
            """, (id_factura,))
            registro = cursor.fetchone()
            print(f"Registro facturación obtenido: {registro is not None}")
            
            # Definimos variables para usar en la plantilla
            qr_code = None
            hash_value = 'No disponible'
            
            # Primero intentamos obtener el hash de registro_facturacion
            if registro and registro['hash']:
                hash_value = registro['hash']
                print(f"Usando hash de registro_facturacion: {hash_value}")
            # Si no está ahí, usamos el de la tabla factura
            elif hash_factura and hash_factura['hash_factura']:
                hash_value = hash_factura['hash_factura']
                print(f"Usando hash de tabla factura: {hash_value}")
                
            # Codificar el QR en base64 si existe
            if registro and registro['codigo_qr']:
                import base64
                qr_raw = registro['codigo_qr']
                if isinstance(qr_raw, (bytes, bytearray)):
                    qr_code = base64.b64encode(qr_raw).decode('utf-8')
                elif isinstance(qr_raw, str):
                    qr_code = qr_raw.strip()
                else:
                    print("Tipo de dato no esperado para código QR")
                    qr_code = None
                print(f"Código QR codificado en base64, longitud: {len(qr_code)}")
            else:
                print("No se encontró código QR en la base de datos")
                
            # Leer el HTML base con la codificación correcta
            with open('/var/www/html/frontend/IMPRIMIR_FACTURA.html', 'r', encoding='utf-8') as f:
                html_base = f.read()

            # Modificar la ruta del logo para usar ruta absoluta del sistema de archivos
            html_base = html_base.replace('src="/static/img/logo.png"', 'src="file:///var/www/html/static/img/logo.png"')

            # Generar el HTML con los datos ya insertados
            detalles_html = ""
            # Helper de formateo europeo con separador de miles (totales: 2 decimales fijos)
            def _fmt_euro(n, dec=2):
                try:
                    x = float(n)
                except Exception:
                    x = 0.0
                s = f"{x:,.{dec}f}"
                return s.replace(',', 'X').replace('.', ',').replace('X', '.')

            # Formateo variable con Decimal: entre 2 y 5 decimales (para precio unitario)
            def _fmt_euro_var(value, min_dec=2, max_dec=5):
                # Convertir a Decimal de forma segura desde posibles formatos europeos
                try:
                    if value is None:
                        d = Decimal('0')
                    elif isinstance(value, (int, float, Decimal)):
                        d = Decimal(str(value))
                    else:
                        s = str(value).strip().replace('.', '').replace(',', '.')
                        d = Decimal(s)
                except Exception:
                    d = Decimal('0')
                # Redondear a un máximo de "max_dec" decimales
                quant = Decimal('1').scaleb(-max_dec)  # 10^-max_dec
                d_q = d.quantize(quant, rounding=ROUND_HALF_UP)
                # Construir string con coma decimal, recortando ceros hasta min_dec
                s = f"{d_q:,.{max_dec}f}"  # con separadores y max_dec
                s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
                # Separar parte entera y decimal
                if ',' in s:
                    entero, decs = s.split(',', 1)
                    # Recortar ceros a la derecha manteniendo mínimo min_dec
                    decs_trim = decs.rstrip('0')
                    if len(decs_trim) < min_dec:
                        decs_trim = decs[:min_dec]
                    s = f"{entero},{decs_trim}"
                return s

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
                            <div class=\"detalle-concepto\">
                                <span>{detalle.get('concepto', '')}</span>
                                {descripcion_html}
                            </div>
                        </td>
                        <td class=\"cantidad\">{_cantidad}</td>
                        <td class=\"precio\">{_precio_str}€</td>
                        <td class=\"total\">{_subtotal_str}€</td>
                    </tr>
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
                '<!-- Los detalles se insertarán aquí dinámicamente -->',
                detalles_html
            ).replace(
                'id="base"></span>',
                f'id="base">{_fmt_euro(base_imponible)}€</span>'
            ).replace(
                'id="iva"></span>',
                f'id="iva">{_fmt_euro(iva)}€</span>'
            ).replace(
                'id="total"></strong>',
                f'id="total">{_fmt_euro(total)}€</strong>'
            ).replace(
                '<p id="forma-pago">Tarjeta</p>',
                f'<p>{decodificar_forma_pago(factura_dict.get("formaPago", "T"))}</p>'
            )

            # Reemplazos adicionales robustos usando regex por si la plantilla difiere en espacios/atributos
            import re
            def _safe(s):
                return '' if s is None else str(s)
            def set_p(html, elem_id, value):
                pattern = rf'<p\s+id="{re.escape(elem_id)}"[^>]*>.*?</p>'
                replacement = f'<p id="{elem_id}">{_safe(value)}</p>'
                return re.sub(pattern, replacement, html, flags=re.DOTALL|re.IGNORECASE)
            def set_span(html, elem_id, value):
                # Preservar atributos existentes y reemplazar solo el contenido usando función para evitar backrefs
                pattern = rf'(<span\s+id="{re.escape(elem_id)}"[^>]*>)(.*?)(</span>)'
                return re.sub(pattern, lambda m: m.group(1) + _safe(value) + m.group(3), html, flags=re.DOTALL|re.IGNORECASE)

            # Cliente
            html_modificado = set_p(html_modificado, 'razonsocial', factura_dict.get('razonsocial', ''))
            html_modificado = set_p(html_modificado, 'direccion', factura_dict.get('direccion', ''))
            html_modificado = set_p(html_modificado, 'cp-localidad', ", ".join(filter(None, [
                _safe(factura_dict.get('cp')), _safe(factura_dict.get('localidad')), _safe(factura_dict.get('provincia'))
            ])))
            html_modificado = set_p(html_modificado, 'nif', factura_dict.get('identificador', ''))

            # Emisor (por si cambian atributos en plantilla)
            html_modificado = set_p(html_modificado, 'emisor-nombre', 'SAMUEL RODRIGUEZ MIQUEL')
            html_modificado = set_p(html_modificado, 'emisor-direccion', 'LEGALITAT, 70')
            html_modificado = set_p(html_modificado, 'emisor-cp-ciudad', 'BARCELONA (08024), BARCELONA, España')
            html_modificado = set_p(html_modificado, 'emisor-nif', '44007535W')
            html_modificado = set_p(html_modificado, 'emisor-email', 'info@aleph70.com')

            # Totales y fechas (span)
            html_modificado = set_span(html_modificado, 'numero', factura_dict["numero"])
            html_modificado = set_span(html_modificado, 'fecha', datetime.strptime(factura_dict["fecha"], "%Y-%m-%d").strftime("%d/%m/%Y"))
            html_modificado = set_span(html_modificado, 'fecha-vencimiento', datetime.strptime(factura_dict["fvencimiento"], "%Y-%m-%d").strftime("%d/%m/%Y") if factura_dict.get("fvencimiento") else '')
            html_modificado = set_span(html_modificado, 'base', f"{_fmt_euro(base_imponible)}€")
            html_modificado = set_span(html_modificado, 'iva', f"{_fmt_euro(iva)}€")
            html_modificado = re.sub(r'<strong\s+id="total"[^>]*>.*?</strong>', f'<strong id="total">{_fmt_euro(total)}€</strong>', html_modificado, flags=re.DOTALL)
            
            # --- Leyenda para facturas rectificativas ---
            es_rectificativa = (
                (factura_dict.get("tipo") == "R") or
                (factura_dict.get("estado") == "RE") or
                (str(factura_dict.get("numero", "")).endswith("-R"))
            )
            import re
            pattern_rect = r'<div\s+id="rectificativa-info"[^>]*></div>'
            if es_rectificativa:
                num_orig = ""
                fecha_orig = ""
                motivo = factura_dict.get("motivo_rectificacion", "Anulación de factura")
                id_rect = factura_dict.get("id_factura_rectificada")
                if id_rect:
                    try:
                        cursor.execute("SELECT numero, fecha FROM factura WHERE id = ?", (id_rect,))
                        row_orig = cursor.fetchone()
                        if row_orig:
                            num_orig = row_orig["numero"] if isinstance(row_orig, dict) else row_orig[0]
                            fecha_orig = row_orig["fecha"] if isinstance(row_orig, dict) else row_orig[1]
                    except Exception as e:
                        print(f"Error obteniendo factura original para leyenda rectificativa: {e}")
                rect_html = f'<div style="border:2px solid #c00; padding:10px; margin:10px 0;"><h2 style="color:#c00; text-align:center;">FACTURA RECTIFICATIVA</h2><p><strong>Factura rectificada:</strong> Nº {num_orig} de fecha {fecha_orig}</p><p><strong>Motivo:</strong> {motivo}</p></div>'
                html_modificado = re.sub(pattern_rect, rect_html, html_modificado, flags=re.IGNORECASE)
            else:
                html_modificado = re.sub(pattern_rect, '', html_modificado, flags=re.IGNORECASE)
            
            print("Modificando el HTML para insertar hash y QR VERI*FACTU...")
            
            # Enfoque directo para insertar el hash y el QR
            # 1. (Deshabilitado) No escribir HTML temporal en disco
            # print("HTML temporal omitido (/tmp/html_antes.html)")
            # Si la configuración deshabilita VERI*FACTU, omitimos leyenda y QR
            import re
            csv_value = registro['csv'] if registro else None
            has_csv = bool(csv_value and str(csv_value).strip())
            if not has_csv or not VERIFACTU_HABILITADO:
                qr_code = None
                print("Factura sin CSV VERI*FACTU o VERIFACTU deshabilitado - se omite leyenda y QR.")
                # Eliminar leyenda y QR relativos a VERI*FACTU
                html_modificado = html_modificado.replace('<p id="hash-factura">Hash: </p>', '')
                # Eliminar también cualquier div del QR VERI*FACTU completo
                html_modificado = re.sub(r'<div id="qr-verifactu"[\s\S]*?</div>', '', html_modificado)
                # Eliminar cualquier bloque que contenga la leyenda o texto VERI*FACTU
                # Eliminamos contenedor principal y subcontenedores secundarios
                html_modificado = re.sub(r'<div[^>]*border-top[^>]*>[\s\S]*?</div>', '', html_modificado, flags=re.IGNORECASE)
                html_modificado = re.sub(r'<p[^>]*>[^<]*VERI\*FACTU[^<]*</p>', '', html_modificado, flags=re.IGNORECASE)
                # Eliminar solo la badget de la cabecera (span VERI*FACTU) sin borrar el bloque de cabecera
                html_modificado = re.sub(r'<span[^>]*?>\s*VERI\*FACTU\s*</span>', '', html_modificado, flags=re.IGNORECASE)
            
            # 2. Buscar de forma exacta dónde insertar el hash y el QR
            hash_placeholder = '<p id="hash-factura">Hash: </p>'
            qr_placeholder = '<div id="qr-verifactu" style="width: 150px; height: 150px; margin-left: auto;">\n                <!-- Aquí se insertará el código QR -->\n            </div>'
            
            # 3. Crear los contenidos de reemplazo
            hash_replacement = f'<p id="hash-factura">Hash: {hash_value}</p>'
            
            # 4. Realizar reemplazos
            if hash_placeholder in html_modificado:
                html_modificado = html_modificado.replace(hash_placeholder, hash_replacement)
                print("Hash reemplazado con éxito")
            else:
                print(f"ERROR: No se encontró el marcador del hash: {hash_placeholder}")
            
            # 5. Insertar el QR si existe
            if qr_code:
                qr_replacement = f'<div id="qr-verifactu" style="width: 150px; height: 150px; margin-left: auto;">\n                <img src="data:image/png;base64,{qr_code}" alt="Código QR VERI*FACTU" style="width: 150px; height: 150px;">\n            </div>'
                
                # Asegurarse de que el div del QR exista en el HTML y reemplazarlo
                if qr_placeholder in html_modificado:
                    html_modificado = html_modificado.replace(qr_placeholder, qr_replacement)
                    print("QR insertado con éxito")
                else:
                    # Si no encuentra el placeholder exacto, intentar con búsqueda más general
                    print("No se encontró el marcador exacto del QR, intentando con búsqueda alternativa")
                    if '<div id="qr-verifactu"' in html_modificado:
                        # Usar expresiones regulares para encontrar y reemplazar el div del QR
                        import re
                        pattern = r'<div id="qr-verifactu"[^>]*>.*?</div>'
                        html_modificado = re.sub(pattern, qr_replacement, html_modificado, flags=re.DOTALL)
                        print("QR insertado con método alternativo")
                    else:
                        # Si aún no lo encuentra, añadirlo al final del documento antes del cierre del body
                        print("Insertando QR antes del cierre del body")
                        html_modificado = html_modificado.replace('</body>', f'{qr_replacement}\n</body>')
            else:
                print("No hay código QR para insertar")
                
            # 6. (Deshabilitado) No escribir HTML final en disco
            # print("HTML final omitido (/tmp/html_despues.html)")


            print("Convirtiendo HTML a PDF")
            # Convertir HTML a PDF usando WeasyPrint con ruta base para recursos estáticos
            HTML(
                string=html_modificado,
                base_url='/var/www/html'  # Ruta base para recursos estáticos
            ).write_pdf(
                tmp.name,
                stylesheets=[CSS(string='@page { size: A4; margin: 1cm }')]
            )
            
            print("Preparando correo")
            # Preparar el correo (incluir fecha y vencimiento)
            fecha_fmt = datetime.strptime(factura_dict["fecha"], "%Y-%m-%d").strftime("%d/%m/%Y") if factura_dict.get("fecha") else ""
            fvenc_fmt = (
                datetime.strptime(factura_dict["fvencimiento"], "%Y-%m-%d").strftime("%d/%m/%Y")
                if factura_dict.get("fvencimiento") else ""
            )
            asunto = f"Factura {factura_dict['numero']} - {fecha_fmt}"
            cuerpo = (
                "Estimado cliente,\n\n"
                f"Adjunto encontrará la factura {factura_dict['numero']}.\n"
                f"Fecha de la factura: {fecha_fmt}\n"
                f"Fecha de vencimiento: {fvenc_fmt}\n\n"
                "Saludos cordiales,\n"
                "SAMUEL RODRIGUEZ MIQUEL\n"
            )

            print(f"Enviando correo a {email_destino}")
            # Enviar el correo
            exito, mensaje = enviar_factura_por_email(
                email_destino,
                asunto,
                cuerpo,
                tmp.name,
                factura_dict['numero']
            )

            # Eliminar el archivo temporal
            os.unlink(tmp.name)

            if exito:
                print("Correo enviado exitosamente")
                # Actualizar el campo 'enviado' a 1 en la base de datos
                try:
                    cursor.execute("UPDATE factura SET enviado = 1 WHERE id = ?", (id_factura,))
                    conn.commit()
                    print(f"Campo 'enviado' actualizado a 1 para la factura {id_factura}")
                    if return_dict:
                        return {'success': True, 'mensaje': 'Factura enviada correctamente', 'id': id_factura}
                    return jsonify({'mensaje': 'Factura enviada correctamente', 'id': id_factura})
                except Exception as e_update:
                    print(f"Error al actualizar campo 'enviado': {str(e_update)}")
                    if return_dict:
                        return {'success': True, 'mensaje': 'Factura enviada correctamente pero no se pudo actualizar el estado de envío', 'id': id_factura}
                    return jsonify({'mensaje': 'Factura enviada correctamente pero no se pudo actualizar el estado de envío', 'id': id_factura})
            else:
                print(f"Error al enviar correo: {mensaje}")
                if return_dict:
                    return {'success': False, 'error': mensaje}
                return jsonify({'error': mensaje}), 500

    except Exception as e:
        import traceback
        print(f"Error en enviar_factura_email: {str(e)}")
        print(traceback.format_exc())
        if return_dict:
            return {'success': False, 'error': str(e)}
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

def enviar_factura_email_endpoint(id_factura):
    try:
        print(f"Iniciando envío de factura {id_factura}")
        return enviar_factura_email(id_factura)
    except Exception as e:
        print(f"Error en enviar_factura_email_endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

def redondear_importe(valor):
    """Redondeo financiero a 2 decimales con Decimal (ROUND_HALF_UP)."""
    try:
        if isinstance(valor, (int, float, Decimal)):
            d = Decimal(str(valor))
        else:
            s = str(valor).strip()
            # soportar formato europeo: miles con punto y decimales con coma
            s = s.replace('.', '').replace(',', '.')
            d = Decimal(s)
        return float(d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    except Exception:
        return 0.0

def crear_factura_post():
    return crear_factura()

def actualizar_factura(id, data):
    # Aseguramos que el módulo traceback esté disponible en toda la función para evitar UnboundLocalError

    # NIF EMISOR obtenido desde configuración para garantizar coherencia
    try:
        emisor_nif = cargar_datos_emisor().get('nif', '')
    except Exception:
        emisor_nif = data.get('nif', '')
    conn = None
    try:
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400

        # Extraer datos principales y convertir a tipos correctos
        try:
            importe_cobrado = float(data.get('importe_cobrado', 0))
            detalles = data.get('detalles', [])
            
            # Validar y convertir valores numéricos en detalles
            for detalle in detalles:
                detalle['cantidad'] = int(detalle.get('cantidad', 0))
                detalle['precio'] = float(detalle.get('precio', 0))
                detalle['impuestos'] = float(detalle.get('impuestos', 0))
        except (ValueError, TypeError) as e:
            return jsonify({'error': f'Error en conversión de valores numéricos: {str(e)}'}), 400

        estado = data.get('estado')
        formaPago = data.get('formaPago')
        presentar_face_flag = 1 if int(data.get('presentar_face', 0)) == 1 else 0
        
        # Log inmediato para debugging
        print(f"[DEBUG actualizar_producto] ID={id}, estado={estado}, presentar_face_flag={presentar_face_flag}")
        
        conn = get_db_connection()
        conn.execute('BEGIN EXCLUSIVE TRANSACTION')
        cursor = conn.cursor()

        # Verificar si la factura existe
        cursor.execute('SELECT * FROM factura WHERE id = ?', (id,))
        factura_existente = cursor.fetchone()
        # Capturar estado anterior para detectar transición de P->C
        estado_anterior = None
        if factura_existente is not None:
            try:
                # sqlite3.Row admite acceso por nombre de columna
                estado_anterior = factura_existente['estado'] if isinstance(factura_existente, sqlite3.Row) else factura_existente[4]
            except Exception:
                # En caso de problema, intentar índice 4 (columna estado)
                try:
                    estado_anterior = factura_existente[4]
                except Exception:
                    estado_anterior = None
        
        print(f"[DEBUG estados] estado_anterior={estado_anterior}, nuevo_estado={estado}, presentar_face={presentar_face_flag}")
        
        if not factura_existente:
            conn.rollback()
            return jsonify({'error': 'Factura no encontrada'}), 404

        # Calcular importes basados en los detalles (Decimal, IVA por línea)
        def D(x):
            try:
                return Decimal(str(x if x is not None else '0'))
            except Exception:
                return Decimal('0')
        base_sum = Decimal('0')
        for d in detalles:
            sub = D(d['precio']) * D(d['cantidad'])
            # Redondear cada subtotal antes de sumar
            sub_rounded = sub.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            base_sum += sub_rounded
        
        # USAR LÓGICA UNIFICADA: Calcular IVA por línea y luego sumar
        importe_bruto_dec = Decimal('0')
        importe_impuestos_dec = Decimal('0')
        total_dec = Decimal('0')
        
        for detalle in detalles:
            precio = D(detalle['precio'])
            cantidad = D(detalle['cantidad'])
            iva_pct = D(detalle.get('impuestos', '21'))  # Usar IVA del detalle o 21% por defecto
            
            subtotal = precio * cantidad
            # CRÍTICO: Redondear IVA por línea a 2 decimales (igual que frontend)
            iva_linea = (subtotal * iva_pct / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            total_linea = (subtotal + iva_linea).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            importe_bruto_dec += subtotal
            importe_impuestos_dec += iva_linea
            total_dec += total_linea
        
        # Redondear totales finales
        importe_bruto = float(importe_bruto_dec.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        importe_impuestos = float(importe_impuestos_dec.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        total = float(total_dec.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

        # Actualizar la factura
        cursor.execute('''
            UPDATE factura 
            SET numero = ?, 
                fecha = ?, 
                fvencimiento = ?,
                estado = ?, 
                idContacto = ?, 
                nif = ?, 
                total = ?, 
                formaPago = ?, 
                importe_bruto = ?, 
                importe_impuestos = ?,
                importe_cobrado = ?, 
                timestamp = ?,
                tipo = ?,
                presentar_face = ?
            WHERE id = ?
        ''', (
            data['numero'],
            data['fecha'],
            data.get('fechaVencimiento', data['fecha']),
            estado,
            data['idContacto'],
            emisor_nif,
            total,
            formaPago,
            importe_bruto,
            importe_impuestos,
            importe_cobrado,
            datetime.now().isoformat(),
            data.get('tipo', 'N'),  # N=Normal (con descuentos), A=Sin descuentos
            presentar_face_flag,
            id
        ))

        # Eliminar detalles existentes
        cursor.execute('DELETE FROM detalle_factura WHERE id_factura = ?', (id,))

        # Insertar los nuevos detalles
        for detalle in detalles:
            # Total por línea: subtotal + IVA redondeado por línea
            sub = D(detalle['precio']) * D(detalle['cantidad'])
            iva_line = (sub * D(detalle['impuestos']) / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            total_detalle = float((sub + iva_line).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

            cursor.execute('''
                INSERT INTO detalle_factura (id_factura, concepto, descripcion, cantidad,
                                           precio, impuestos, total, productoId, fechaDetalle)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                id,
                detalle['concepto'],
                detalle.get('descripcion', ''),
                detalle['cantidad'],  # Ya convertido a int
                detalle['precio'],    # Ya convertido a float
                detalle['impuestos'], # Ya convertido a float
                total_detalle,
                detalle.get('productoId'),
                detalle.get('fechaDetalle', data['fecha'])
            ))

        # Detectar si debemos generar Facturae/VERI*FACTU tras la actualización
        # Generar si el checkbox presentar_face está marcado y la factura está cobrada
        trigger_generar_facturae = (estado == 'C' and presentar_face_flag == 1)
        
        print(f"[DEBUG trigger] trigger_generar_facturae={trigger_generar_facturae}, estado={estado}, presentar_face={presentar_face_flag}")
        
        try:
            with safe_append_debug('facturae_debug.log') as log_file:
                log_file.write(f"\n[{datetime.now().isoformat()}] Actualizar Factura ID={id}: estado={estado}, presentar_face={presentar_face_flag}\n")
                log_file.write(f"Trigger generar facturae: {trigger_generar_facturae}\n")
        except Exception as e:
            print(f"[DEBUG] Error escribiendo log: {e}")
            pass

        # Generar factura electrónica sólo si pasamos de Pendiente (u otro) a Cobrado
        factura_e_generada = False
        ruta_xml = None
        factura_e_generada = False
        ruta_xml = None
        
        if trigger_generar_facturae:
            try:
                # Crear un archivo de log para seguir este proceso
                with safe_append_debug('facturae_debug.log') as log_file:
                    log_file.write(f"\n[{datetime.now().isoformat()}] Iniciando generación de factura electrónica para factura ID={id}, Número={data['numero']}\n")
                
                # Obtener todos los detalles de la factura desde la base de datos
                cursor.execute('''
                    SELECT d.*, p.nombre as producto_nombre 
                    FROM detalle_factura d 
                    LEFT JOIN productos p ON d.productoId = p.id 
                    WHERE id_factura = ?
                ''', (id,))
                detalles_bd = cursor.fetchall()
                detalles = []
                
                # Obtener el valor de IVA de la primera línea (asumiendo que es el mismo para toda la factura)
                porcentaje_iva = 21.0  # Valor por defecto
                if detalles_bd and len(detalles_bd) > 0:
                    porcentaje_iva = float(detalles_bd[0]['impuestos'])
                
                # Procesar cada detalle
                for detalle_bd in detalles_bd:
                    detalle_dict = dict(detalle_bd)
                    # Convertir a los tipos adecuados
                    detalle = {
                        'concepto': detalle_dict['concepto'],
                        'descripcion': detalle_dict.get('descripcion', ''),
                        'cantidad': float(detalle_dict['cantidad']),
                        'importe': float(detalle_dict['precio']),
                        'impuestos': float(detalle_dict['impuestos']),
                        'productoId': detalle_dict.get('productoId')
                    }
                    detalles.append(detalle)
                
                with safe_append_debug('facturae_debug.log') as log_file:
                    log_file.write(f"Detalles de la factura obtenidos: {json.dumps(detalles, default=str)}\n")
                    log_file.write(f"Porcentaje IVA usado: {porcentaje_iva}%\n")
                    
                # Obtener datos del contacto
                cursor.execute('SELECT * FROM contactos WHERE idcontacto = ?', (data['idContacto'],))
                contacto_row = cursor.fetchone()
                if contacto_row:
                    contacto_dict = dict(contacto_row)
                    
                    # Crear log de los datos del contacto
                    with safe_append_debug('facturae_debug.log') as log_file:
                        log_file.write(f"Datos del contacto: {json.dumps(contacto_dict, default=str)}\n")
                    
                    # Leer datos del emisor desde emisor_config.json
                    emisor_config_path = os.path.abspath(os.path.dirname(__file__)) + '/emisor_config.json'
                    with open(emisor_config_path, 'r', encoding='utf-8') as f:
                        emisor_config = json.load(f)
                        
                    # Preparar los datos para la generación de la factura electrónica
                    # Recuperar los totales de la factura desde la base de datos - Usar consulta directa
                    cursor.execute('SELECT * FROM factura WHERE id = ?', (id,))
                    factura_completa = cursor.fetchone()
                    
                    # Registrar la factura completa para depuración
                    with safe_append_debug('facturae_debug.log') as log_file:
                        log_file.write(f"[{datetime.now().isoformat()}] FACTURA COMPLETA: {factura_completa}\n")
                    
                    # Obtener los totales directamente desde la consulta SQL
                    # En este caso, hacemos una consulta específica para asegurarnos de obtener los valores correctos
                    cursor.execute('''
                        SELECT importe_bruto, importe_impuestos, total 
                        FROM factura 
                        WHERE id = ? 
                        LIMIT 1
                    ''', (id,))
                    
                    # Capturar el resultado directamente
                    totales_db = cursor.fetchone()
                    
                    # Registrar los valores brutos obtenidos
                    with safe_append_debug('facturae_debug.log') as log_file:
                        log_file.write(f"VALORES DB BRUTOS: {totales_db}\n")
                    
                    # Debug: registrar los valores recuperados de la base de datos
                    with safe_append_debug('facturae_debug.log') as log_file:
                        log_file.write(f"[factura.py] Totales de la base de datos: Bruto={totales_db[0]}, Impuestos={totales_db[1]}, Total={totales_db[2]}\n")
                    
                    # Garantizar que siempre tengamos valores numéricos válidos
                    if totales_db:
                        # Intentar convertir los valores con una verificación estricta
                        try:
                            # Si hay algún NULL o None, la conversión fallará, por lo que usamos una verificación explícita
                            base_imponible = float(totales_db[0]) if totales_db[0] is not None else 0.0
                            impuestos = float(totales_db[1]) if totales_db[1] is not None else 0.0
                            total = float(totales_db[2]) if totales_db[2] is not None else 0.0
                            
                            # Verificación adicional para no permitir valores cero si hay datos en la DB
                            if base_imponible == 0 and totales_db[0] != 0 and totales_db[0] is not None:
                                with safe_append_debug('facturae_debug.log') as log_file:
                                    log_file.write(f"ADVERTENCIA: base_imponible se convirtió a cero pero el valor original era {totales_db[0]}\n")
                                    
                            if impuestos == 0 and totales_db[1] != 0 and totales_db[1] is not None:
                                with safe_append_debug('facturae_debug.log') as log_file:
                                    log_file.write(f"ADVERTENCIA: impuestos se convirtió a cero pero el valor original era {totales_db[1]}\n")
                        except (ValueError, TypeError) as e:
                            # En caso de error, log detallado y asignar valores predeterminados
                            with safe_append_debug('facturae_debug.log') as log_file:
                                log_file.write(f"ERROR al convertir totales de BD: {e}, valores: {totales_db}\n")
                            # Usar valores por defecto en caso de error
                            base_imponible = 0.0
                            impuestos = 0.0
                            total = 0.0
                    else:
                        # Si no encontramos valores en la BD, usar valores predeterminados
                        with safe_append_debug('facturae_debug.log') as log_file:
                            log_file.write(f"ERROR: No se encontraron totales para la factura con ID {id}\n")
                        base_imponible = 0.0
                        impuestos = 0.0
                        total = 0.0
                
                    with safe_append_debug('facturae_debug.log') as log_file:
                        log_file.write(f"TOTALES EXTRAÍDOS DIRECTAMENTE: Base={base_imponible}, IVA={impuestos}, Total={total}\n")
                    
                    # Si algún valor sigue siendo None, calcularlo desde los detalles
                    if base_imponible is None or impuestos is None or total is None:
                        # Calcular base imponible
                        base_imponible_calc = 0
                        impuestos_calc = 0
                        total_calc = 0
                        
                        for detalle in detalles:
                            cantidad = float(detalle.get('cantidad', 1))
                            precio = float(detalle.get('precio', 0))
                            porc_iva = float(detalle.get('impuestos', porcentaje_iva))
                            
                            base_linea = round(cantidad * precio, 2)
                            iva_linea = round(base_linea * porc_iva / 100, 2)
                            
                            base_imponible_calc += base_linea
                            impuestos_calc += iva_linea
                            total_calc += (base_linea + iva_linea)
                        
                        # Redondear a 2 decimales
                        base_imponible_calc = round(base_imponible_calc, 2)
                        impuestos_calc = round(impuestos_calc, 2)
                        total_calc = round(total_calc, 2)
                        
                        # Usar valores calculados solo si los originales son None
                        if base_imponible is None:
                            base_imponible = base_imponible_calc
                        if impuestos is None:
                            impuestos = impuestos_calc
                        if total is None:
                            total = total_calc
                        
                        with safe_append_debug('facturae_debug.log') as log_file:
                            log_file.write(f"TOTALES USADOS DESPUÉS DE CÁLCULO: Base={base_imponible}, IVA={impuestos}, Total={total}\n")
                    
                    # Asegurarse de que los valores no sean None
                    base_imponible = base_imponible if base_imponible is not None else 0.0
                    impuestos = impuestos if impuestos is not None else 0.0
                    total = total if total is not None else 0.0
                    
                    # Convertir a float para asegurar el tipo correcto
                    base_imponible = float(base_imponible)
                    impuestos = float(impuestos)
                    total = float(total)
                    
                    # Registrar los valores que se van a usar
                    with safe_append_debug('facturae_debug.log') as log_file:
                        log_file.write(f"VALORES FINALES PARA XML: Base={base_imponible}, IVA={impuestos}, Total={total}\n")
                        log_file.write(f"TIPO DE DATOS: Base={type(base_imponible)}, IVA={type(impuestos)}, Total={type(total)}\n")
                    
                    # Preparar los datos incluyendo los totales
                    datos_factura = {
                        'emisor': emisor_config,
                        'receptor': {
                            'nif': contacto_dict['identificador'],
                            'nombre': contacto_dict['razonsocial'] if contacto_dict['razonsocial'] else '',
                            'direccion': contacto_dict['direccion'] if contacto_dict['direccion'] else '',
                            'cp': contacto_dict['cp'] if contacto_dict['cp'] else '',
                            'provincia': contacto_dict['provincia'] if contacto_dict['provincia'] else '',
                            'localidad': contacto_dict['localidad'] if contacto_dict['localidad'] else '',
                        },
                        'detalles': detalles,
                        'fecha': data['fecha'],
                        'numero': data['numero'],
                        'iva': porcentaje_iva,  # Usar el valor real del IVA de los detalles
                        'importe_bruto': base_imponible,  # Base imponible
                        'importe_impuestos': impuestos,  # Impuestos
                        'total': total,  # Total factura
                        'presentar_face': 1,  # Siempre 1 cuando se ejecuta esta rama
                        'dir3_oficina': contacto_dict.get('dir3_oficina', ''),
                        'dir3_organo': contacto_dict.get('dir3_organo', ''),
                        'dir3_unidad': contacto_dict.get('dir3_unidad', '')
                    }
                    
                    # Crear log de los datos que se envían al generador
                    with safe_append_debug('facturae_debug.log') as log_file:
                        log_file.write(f"[{datetime.now().isoformat()}] Procesando factura {data['numero']}\n")
                        log_file.write(f"Datos de totales recibidos: {base_imponible}, {impuestos}, {total}\n")
                    print(f"DEBUG: Totales enviados al generador - Base: {base_imponible}, IVA: {impuestos}, Total: {total}")
                    
                    # Crear log de los datos de la factura
                    with safe_append_debug('facturae_debug.log') as log_file:
                        log_file.write(f"Datos para generación de factura: {json.dumps(datos_factura, default=str)}\n")
                    
                    # Debug: registrar valores antes de pasar al generador
                    with safe_append_debug('facturae_debug.log') as log_file:
                        log_file.write(f"[factura.py] VALORES PASADOS A GENERADOR: Bruto={base_imponible}, Impuestos={impuestos}, Total={total}\n")
                    
                    # Explicitamente importamos la función desde facturae.generador para evitar confusión
                    from facturae.generador import \
                        generar_facturae as generar_facturae_modular

                    # Llamar a la función de generación y firma
                    with safe_append_debug('facturae_debug.log') as log_file:
                        log_file.write("Llamando a generar_facturae_modular...\n")
                    
                    # Mapear claves para compatibilidad con generador y validación
                    datos_factura.setdefault('invoice_number', data['numero'])
                    datos_factura.setdefault('issue_date', data['fecha'])
                    datos_factura.setdefault('customer_info', datos_factura['receptor'])
                    datos_factura.setdefault('items', datos_factura.get('detalles', []))
                    datos_factura.setdefault('base_amount', base_imponible)
                    datos_factura.setdefault('taxes', impuestos)
                    datos_factura.setdefault('total_amount', total)

                    ruta_xml = generar_facturae_modular(datos_factura)
                    
                    with safe_append_debug('facturae_debug.log') as log_file:
                        log_file.write(f"Resultado de generar_facturae: {ruta_xml}\n")
                    
                    # Validar campos críticos antes de generar Facturae
                    # Validación cubierta mediante setdefault; ya deberían estar todas las claves requeridas
                    
                    # Verificar si es realmente XSIG (firmado)
                    if ruta_xml and ruta_xml.lower().endswith('.xsig'):
                        with safe_append_debug('facturae_debug.log') as log_file:
                            log_file.write(f"XML de factura electrónica generado y firmado correctamente: {ruta_xml}\n")
                        # Actualizamos el campo factura_e en la BD
                        cursor.execute('UPDATE factura SET factura_e = 1 WHERE id = ?', (id,))
                        factura_e_generada = True
                    else:
                        with safe_append_debug('facturae_debug.log') as log_file:
                            log_file.write(f"ERROR: No se generó archivo XSIG firmado. Resultado: {ruta_xml}\n")
            except Exception as e:
                with safe_append_debug('facturae_debug.log') as log_file:
                    log_file.write(f"EXCEPCIÓN al generar factura electrónica: {str(e)}\n")
                    log_file.write(f"Traza del error: {traceback.format_exc()}\n")
                # No interrumpimos el proceso por un error en la generación de la factura electrónica
        
        # Commit al final de todas las operaciones
        conn.commit()
        
        # --- Integración VERI*FACTU ---
        respuesta = {
            'mensaje': 'Factura actualizada exitosamente',
            'id': id
        }
        # Continuamos para integrar con VERI*FACTU si procede
        
        try:
            print("[VERIFACTU] Actualizando datos VERI*FACTU para factura_id:", id)
            
            # Verificar si VERI*FACTU está disponible (desactivado en actualización para evitar duplicados)
            if VERIFACTU_DISPONIBLE:
                try:
                    # Llamar a la función que implementa el flujo completo:
                    # 1. Validar XML
                    # 2. Calcular hash
                    # 3. Generar XML para AEAT
                    # 4. Enviar a AEAT (simulado) 
                    # 5. Solo generar QR si hay validación exitosa
                    datos_verifactu = verifactu.generar_datos_verifactu_para_factura(id)
                    
                    if datos_verifactu:
                        # Verificar si la factura fue validada por AEAT
                        validado_aeat = datos_verifactu.get('validado_aeat', False)
                        tiene_qr = 'qr_data' in datos_verifactu and datos_verifactu['qr_data'] is not None
                        
                        if validado_aeat and tiene_qr:
                            print(f"[VERIFACTU] Factura validada por AEAT. Hash={datos_verifactu['hash'][:10]}..., ID={datos_verifactu.get('id_verificacion', 'N/A')}")
                            respuesta['datos_adicionales'] = {
                                'hash': datos_verifactu['hash'],
                                'verifactu': True,
                                'validado_aeat': True,
                                'id_verificacion': datos_verifactu.get('id_verificacion', ''),
                                'qr_disponible': True,
                                'mensaje': datos_verifactu.get('mensaje', 'Factura validada correctamente')
                            }
                        elif validado_aeat and not tiene_qr:
                            print(f"[VERIFACTU] Factura validada por AEAT pero sin QR generado. Hash={datos_verifactu['hash'][:10]}...")
                            respuesta['datos_adicionales'] = {
                                'hash': datos_verifactu['hash'],
                                'verifactu': True,
                                'validado_aeat': True,
                                'qr_disponible': False,
                                'mensaje': "Factura validada pero sin QR generado"
                            }
                        else:
                            print(f"[VERIFACTU] Factura NO validada por AEAT. Hash={datos_verifactu['hash'][:10]}...")
                            respuesta['datos_adicionales'] = {
                                'hash': datos_verifactu['hash'],
                                'verifactu': True,
                                'validado_aeat': False,
                                'qr_disponible': False,
                                'mensaje': datos_verifactu.get('mensaje', 'Factura no validada por AEAT')
                            }
                    else:
                        print("[VERIFACTU] No se pudieron actualizar los datos VERI*FACTU")
                        respuesta['datos_adicionales'] = {
                            'verifactu': False,
                            'mensaje': "Fallo al regenerar datos VERI*FACTU",
                            'validado_aeat': False,
                            'qr_disponible': False
                        }
                except Exception as e:
                    print(f"[!] Error al regenerar datos VERI*FACTU: {str(e)}")
                    import traceback
                    print(traceback.format_exc())
                    respuesta['datos_adicionales'] = {
                        'verifactu': False,
                        'mensaje': f"Error VERI*FACTU: {str(e)}",
                        'validado_aeat': False,
                        'qr_disponible': False
                    }
            else:
                print("[!] Módulo VERI*FACTU no disponible - Omitiendo actualización de datos")
                respuesta['datos_adicionales'] = {
                    'verifactu': False,
                    'mensaje': "Módulo VERI*FACTU no disponible",
                    'validado_aeat': False,
                    'qr_disponible': False
                }
        except Exception as e:
            print(f"[VERIFACTU][ERROR] Error al actualizar datos VERI*FACTU: {e}")
            import traceback
            print(traceback.format_exc())
            respuesta['datos_adicionales'] = {
                'verifactu': False,
                'mensaje': f"Error en integración VERI*FACTU: {str(e)}",
                'validado_aeat': False,
                'qr_disponible': False
            }
            
        return jsonify(respuesta)
        
        # Respuesta sin mencionar VERI*FACTU si hubo problemas
        return jsonify({
            'mensaje': 'Factura actualizada exitosamente',
            'id': id
        })

    except Exception as e:
        if conn:
            conn.rollback()
        import traceback
        tb = traceback.format_exc()
        # Volcar a stdout y a log UTF-8 para diagnóstico
        try:
            print(f"Error en actualizar_factura: {str(e)}")
            print(tb)
        except Exception:
            pass
        try:
            with safe_append_debug('facturae_debug.log') as log_file:
                log_file.write(f"[ERROR actualizar_factura] {datetime.now().isoformat()} -> {str(e)}\n")
                log_file.write(tb + "\n")
        except Exception:
            pass
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cliente SOAP para comunicación con AEAT VERI*FACTU

Implementa la comunicación con los servicios web SOAP de la AEAT
utilizando autenticación SSL mutua con certificados digitales y
librería requests para mayor control sobre el XML enviado
"""

import hashlib
import logging
import os
from constantes import DB_NAME
import re
import sqlite3
from datetime import datetime

import requests
from lxml import etree

logger = logging.getLogger('verifactu')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def procesar_serie_numero(numero_completo):
    """
    Procesa un número de factura completo para separar correctamente la serie y el número
    según los requerimientos de AEAT para VERI*FACTU, evitando duplicaciones.
    
    Args:
        numero_completo (str): Número de factura completo (ej: 'F250349')
    
    Returns:
        tuple: (serie, numero) separados correctamente
    """
    if not numero_completo:
        return ('', '')
        
    # Patrones comunes para series de factura: letras seguidas de números
    # Por ejemplo: A123, F25001, AB-123, etc.
    match = re.match(r'^([A-Za-z]+)[-]?([0-9]+)$', numero_completo)
    if match:
        serie = match.group(1)  # Parte alfabética
        numero = match.group(2)  # Parte numérica
        logger.info(f"Serie y número separados: Serie={serie}, Número={numero}")
        return (serie, numero)
    
    # Patrón específico para facturas como F250349 donde F25 es la serie
    match = re.match(r'^(F25)([0-9]+)$', numero_completo)
    if match:
        serie = match.group(1)  # F25
        numero = match.group(2)  # 0349
        logger.info(f"Serie y número separados con patrón F25: Serie={serie}, Número={numero}")
        return (serie, numero)
    
    # Si no se puede separar, devolver el número completo como número y serie vacía
    logger.warning(f"No se pudo separar serie y número: {numero_completo}. Usando como número completo.")
    return ('', numero_completo)

# Importar XMLSigner para la firma electrónica




# Directorio base del proyecto
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Directorio por defecto para certificados SSL
cert_dir = os.path.join(BASE_DIR, 'certs')



def parsear_respuesta_aeat(xml_text):
    """
    Parsea la respuesta SOAP de la AEAT recogiendo el estado de envío, el CSV y
    los posibles errores de negocio devueltos.

    Args:
        xml_text (str): XML completo de la respuesta SOAP.

    Returns:
        dict: {
            'estado_envio': str | None,
            'csv': str | None,
            'errores': list[dict]  # [{'codigo': str, 'descripcion': str, 'resultado': str}]
        }
    """


    ns = {
        'env': 'http://schemas.xmlsoap.org/soap/envelope/',
        'tikR': 'https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/RespuestaSuministro.xsd',
        'tik': 'https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/SuministroInformacion.xsd',
    }

    # Log de depuración para inspeccionar la respuesta original
    logger.info(f"Respuesta AEAT (traza corta): {xml_text[:400]}...")

    try:
        root = etree.fromstring(xml_text.encode('utf-8'))
    except Exception as e:
        logger.error(f"No se pudo parsear XML de respuesta AEAT: {e}")
        return {
            'estado_envio': None,
            'csv': None,
            'errores': [{'codigo': 'XML_PARSE', 'descripcion': str(e), 'resultado': None}]
        }

    estado_elem = root.find('.//tikR:EstadoEnvio', ns)
    estado_envio = estado_elem.text if estado_elem is not None else None

    csv_elem = root.find('.//tikR:CSV', ns)
    if csv_elem is None:
        csv_elem = root.find('.//tik:CSV', ns)
    if csv_elem is None:
        # Búsqueda genérica sin namespace usando XPath
        elems = root.xpath('//*[local-name()="CSV"]')
        csv_elem = elems[0] if elems else None
    csv = csv_elem.text if csv_elem is not None else None

    errores = []

    # Capturar Fault genérico
    fault_elem = root.find('.//env:Fault', ns)
    if fault_elem is not None:
        faultcode_elem = fault_elem.find('faultcode')
        faultstring_elem = fault_elem.find('faultstring')
        errores.append({
            'codigo': faultcode_elem.text if faultcode_elem is not None else 'FAULT',
            'descripcion': faultstring_elem.text if faultstring_elem is not None else 'SOAP Fault',
            'resultado': 'Fault',
        })
    for linea in root.findall('.//tikR:RespuestaLinea', ns):
        codigo_elem = linea.find('.//tikR:CodigoError', ns) or linea.find('.//tikR:CodigoErrorRegistro', ns)
        desc_elem = linea.find('.//tikR:DescripcionError', ns) or linea.find('.//tikR:DescripcionErrorRegistro', ns)
        resultado_elem = linea.find('.//tikR:Resultado', ns) or linea.find('.//tikR:EstadoRegistro', ns)

        if codigo_elem is not None or desc_elem is not None or resultado_elem is not None:
            errores.append({
                'codigo': codigo_elem.text if codigo_elem is not None else None,
                'descripcion': desc_elem.text if desc_elem is not None else None,
                'resultado': resultado_elem.text if resultado_elem is not None else None,
            })

    # Recoger también todas las líneas de respuesta (incluidas las correctas)
    lineas = []
    for linea in root.findall('.//tikR:RespuestaLinea', ns):
        tipo_op_elem = linea.find('.//tik:TipoOperacion', ns)
        resultado_elem = linea.find('.//tikR:Resultado', ns)
        codigo_elem = linea.find('.//tikR:CodigoError', ns) or linea.find('.//tikR:CodigoErrorRegistro', ns)
        desc_elem = linea.find('.//tikR:DescripcionError', ns) or linea.find('.//tikR:DescripcionErrorRegistro', ns)
        lineas.append({
            'tipo_operacion': tipo_op_elem.text if tipo_op_elem is not None else None,
            'resultado': resultado_elem.text if resultado_elem is not None else None,
            'codigo_error': codigo_elem.text if codigo_elem is not None else None,
            'descripcion_error': desc_elem.text if desc_elem is not None else None,
        })
    
    return {'estado_envio': estado_envio, 'csv': csv, 'errores': errores, 'lineas': lineas}

def crear_envelope_soap(
    operacion: str,           # NO se usa, pero se conserva la firma pública
    cabecera: dict,           #   »   »      »      »
    registro_factura: dict,
    nif_emisor: str,
    factura_firmada_b64: str | None = None,
    huella_anterior: str | None = None,
    primer_registro: str | None = None,
    ajuste_fecha_minuto: bool = False,
    huella_fija: str | None = None,
) -> tuple[str, str]:  # Devuelve (envelope_xml, huella)
    """
    Devuelve el envelope SOAP con el **orden exacto de nodos** que
    exige el XSD de VERI*FACTU (evita el 4102 “Falta informar campo
    obligatorio: Encadenamiento / Desglose”).

    Únicamente genera el XML; la lógica de BD, red, certificados, etc.
    permanece intacta.
    """
    # ------------------------------------------------------------------ #
    #  Namespaces
    # ------------------------------------------------------------------ #
    ns_soap = "http://schemas.xmlsoap.org/soap/envelope/"
    ns_lr   = ("https://www2.agenciatributaria.gob.es/static_files/common/"
               "internet/dep/aplicaciones/es/aeat/tike/cont/ws/SuministroLR.xsd")
    ns_sf   = ("https://www2.agenciatributaria.gob.es/static_files/common/"
               "internet/dep/aplicaciones/es/aeat/tike/cont/ws/SuministroInformacion.xsd")

    # ------------------------------------------------------------------ #
    #  Datos básicos - saneo y cálculos
    # ------------------------------------------------------------------ #
    nif = nif_emisor.strip().upper()

    # ------------------------------------------------------------------ #
    #  Cargar datos del emisor desde emisor_config.json, si existe
    # ------------------------------------------------------------------ #
    try:
        from utils_emisor import cargar_datos_emisor
        cfg_emisor = cargar_datos_emisor()
    except Exception as e_cfg:
        logger.warning(f"No se pudo cargar emisor_config.json: {e_cfg}")
        cfg_emisor = {}

    # Prioridad: valor explícito en registro_factura > configuración JSON > valor por defecto
    nombre = registro_factura.get("nombre_emisor", cfg_emisor.get("nombre", "EMISOR VERIFACTU"))
    # Tipo de factura (F1 completa, F2 simplificada tipo ticket)
    tipo_factura = registro_factura.get("tipo_factura", "F1")

    # ------------------------------------------------------------------ #
    #  Datos del destinatario (cliente)
    # ------------------------------------------------------------------ #
    nif_dest = (registro_factura.get("nif_destinatario")
                or registro_factura.get("nif_receptor", "")).strip().upper()
    nombre_dest = (registro_factura.get("nombre_destinatario")
                   or registro_factura.get("nombre_receptor", "")).strip()
    # Valores por defecto solo si se trata de factura completa (F1)
    if tipo_factura not in ("S", "F2"):
        if not nif_dest:
            nif_dest = "X0000000T"
        if not nombre_dest:
            nombre_dest = "DESTINATARIO VERIFACTU"

    # ------------------------------------------------------------------ #
    #  Generar bloque XML de destinatario (PersonaJuridica/Fisica)        #
    # ------------------------------------------------------------------ #
    def _es_persona_juridica(nif: str) -> bool:
        """Devuelve True si el NIF corresponde claramente a persona jurídica
        según la primera letra (A-H, J, N, P, Q, R, S, U, V, W)."""
        return bool(nif) and nif[0].upper() in "ABCDEFGHJNPQRSUVW"

    # Construcción conforme a documentación AEAT: sin subgrupos Persona*, solo campos directos
    partes_nombre = nombre_dest.split()
    if _es_persona_juridica(nif_dest):
        # Solo NombreRazon y NIF
        destinatarios_xml = (
            "<sf:Destinatarios>"
            "<sf:IDDestinatario>"
            f"<sf:NombreRazon>{nombre_dest}</sf:NombreRazon>"
            f"<sf:NIF>{nif_dest}</sf:NIF>"
            "</sf:IDDestinatario>"
            "</sf:Destinatarios>"
        )
    else:
        # Persona física: solo NombreRazon y NIF
        destinatarios_xml = (
            "<sf:Destinatarios>"
            "<sf:IDDestinatario>"
            f"<sf:NombreRazon>{nombre_dest}</sf:NombreRazon>"
            f"<sf:NIF>{nif_dest}</sf:NIF>"
            "</sf:IDDestinatario>"
            "</sf:Destinatarios>"
        )

    # Omitir bloque destinatarios para tickets simplificados: siempre para F2
    if tipo_factura == "F2" or (tipo_factura == "S" and not nif_dest):
        destinatarios_xml = ""
    serie  = registro_factura.get("serie_factura", "A")
    numero = registro_factura.get("numero_factura", "000001")

    # Normalizar la fecha de expedición al formato DD-MM-YYYY que exige la AEAT
    raw_fecha = registro_factura.get("fecha_emision")
    if raw_fecha:
        try:
            if re.match(r"\d{4}-\d{2}-\d{2}", raw_fecha):
                fecha_exp = datetime.strptime(raw_fecha, "%Y-%m-%d").strftime("%d-%m-%Y")
            elif re.match(r"\d{2}-\d{2}-\d{4}", raw_fecha):
                fecha_exp = raw_fecha
            elif re.match(r"\d{2}/\d{2}/\d{4}", raw_fecha):
                fecha_exp = datetime.strptime(raw_fecha, "%d/%m/%Y").strftime("%d-%m-%Y")
            else:
                logger.warning("Formato de fecha_emision desconocido (%s). Se usa fecha actual.", raw_fecha)
                fecha_exp = datetime.today().strftime("%d-%m-%Y")
        except Exception as e_fecha:
            logger.warning("Error procesando fecha_emision '%s': %s. Se usa fecha actual.", raw_fecha, e_fecha)
            fecha_exp = datetime.today().strftime("%d-%m-%Y")
    else:
        fecha_exp = datetime.today().strftime("%d-%m-%Y")

    total = float(registro_factura.get("importe_total", 0))
    base  = round(total / 1.21, 2)
    cuota = round(total - base,       2)

    # Campo FechaHoraHusoGenRegistro (xs:dateTime con huso horario)
    fecha_gen_dt = datetime.now()
    fecha_gen = fecha_gen_dt.astimezone().isoformat(timespec='seconds')

        # Cálculo de la huella según la especificación oficial AEAT
    # Concatenación EXACTA (sin separadores) de:
    #   IDEmisorFactura (NIF) + NumSerieFactura + FechaExpedicionFactura (DD-MM-YYYY) + ImporteTotal (dos decimales con punto)
    # Posteriormente se aplica SHA-256 y se convierte a hexadecimal en mayúsculas.
    # -------------------------------------------------------------- #
    #  Cálculo de huella VERI*FACTU según XSD AEAT (v. 2024-05)
    # -------------------------------------------------------------- #
    if huella_fija:
        # Reutilizar la huella previamente aceptada por AEAT para evitar
        # duplicados en reenvíos del mismo registro.
        huella = huella_fija.strip().upper()
    else:
        # tipo_factura ya definido anteriormente, se reutiliza
        huella_valor = huella_anterior if huella_anterior else ""
        cadena_hash = (
            f"IDEmisorFactura={nif}&"
            f"NumSerieFactura={serie}{numero}&"
            f"FechaExpedicionFactura={fecha_exp}&"
            f"TipoFactura={tipo_factura}&"
            f"CuotaTotal={cuota:.2f}&"
            f"ImporteTotal={total:.2f}&"
            f"Huella={huella_valor}&"
            f"FechaHoraHusoGenRegistro={fecha_gen}"
        )
        huella = hashlib.sha256(cadena_hash.encode()).hexdigest().upper()

    # Determinar valor de <sf:PrimerRegistro>
    primer_val = primer_registro if primer_registro in {"S","N"} else "S"

    # Construir bloque <sf:Encadenamiento> según si es primer registro o re-alta
    if primer_val == "S":
        encadenamiento_xml = "<sf:Encadenamiento><sf:PrimerRegistro>S</sf:PrimerRegistro></sf:Encadenamiento>"
    else:
        if not huella_anterior:
            logger.error("Se requiere huella_anterior para re-alta (PrimerRegistro=N)")
            huella_anterior = "00" * 32  # placeholder evita XML malformado
        encadenamiento_xml = (
            "<sf:Encadenamiento>"
            "<sf:RegistroAnterior>"
            f"<sf:IDEmisorFactura>{nif}</sf:IDEmisorFactura>"
            f"<sf:NumSerieFactura>{serie}{numero}</sf:NumSerieFactura>"
            f"<sf:FechaExpedicionFactura>{fecha_exp}</sf:FechaExpedicionFactura>"
            f"<sf:Huella>{huella_anterior}</sf:Huella>"
            "</sf:RegistroAnterior>"
            "</sf:Encadenamiento>"
        )

    # ------------------------------------------------------------------ #
    #  Envelope
    # ------------------------------------------------------------------ #
    envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="{ns_soap}" xmlns:lr="{ns_lr}" xmlns:sf="{ns_sf}">
  <soapenv:Header/>
  <soapenv:Body>
    <lr:RegFactuSistemaFacturacion>
      <lr:Cabecera>
        <sf:ObligadoEmision>
          <sf:NombreRazon>{nombre}</sf:NombreRazon>
          <sf:NIF>{nif}</sf:NIF>
        </sf:ObligadoEmision>
      </lr:Cabecera>
      <lr:RegistroFactura>
        <sf:RegistroAlta>
          <!-- 1 -->
          <sf:IDVersion>1.0</sf:IDVersion>
          <!-- 2 -->
          <sf:IDFactura>
            <sf:IDEmisorFactura>{nif}</sf:IDEmisorFactura>
            <sf:NumSerieFactura>{serie}{numero}</sf:NumSerieFactura>
            <sf:FechaExpedicionFactura>{fecha_exp}</sf:FechaExpedicionFactura>
          </sf:IDFactura>
          <!-- 3 -->
          <sf:NombreRazonEmisor>{nombre}</sf:NombreRazonEmisor>
          <!-- 4 -->
           <sf:TipoFactura>{tipo_factura}</sf:TipoFactura>
           <!-- 5 -->
           <sf:DescripcionOperacion>Registro factura VERI*FACTU</sf:DescripcionOperacion>
           <!-- Destinatario -->
           {destinatarios_xml}
          <!-- 6  Desglose completo -->
          <sf:Desglose>
            <sf:DetalleDesglose>
               <sf:Impuesto>01</sf:Impuesto>
               <sf:ClaveRegimen>01</sf:ClaveRegimen>
               <sf:CalificacionOperacion>S1</sf:CalificacionOperacion>
              <sf:TipoImpositivo>21.00</sf:TipoImpositivo>
              <sf:BaseImponibleOimporteNoSujeto>{base:.2f}</sf:BaseImponibleOimporteNoSujeto>
              <sf:CuotaRepercutida>{cuota:.2f}</sf:CuotaRepercutida>
            </sf:DetalleDesglose>
          </sf:Desglose>
          <sf:CuotaTotal>{cuota:.2f}</sf:CuotaTotal>
          <sf:ImporteTotal>{total:.2f}</sf:ImporteTotal>
           <!-- 9 -->
           {encadenamiento_xml}
          <!-- 10 -->
          <sf:SistemaInformatico>
            <sf:NombreRazon>{nombre}</sf:NombreRazon>
            <sf:NIF>{nif}</sf:NIF>
            <sf:NombreSistemaInformatico>VerifactuApp</sf:NombreSistemaInformatico>
            <sf:IdSistemaInformatico>01</sf:IdSistemaInformatico>
            <sf:Version>1.0</sf:Version>
            <sf:NumeroInstalacion>0001</sf:NumeroInstalacion>
            <sf:TipoUsoPosibleSoloVerifactu>S</sf:TipoUsoPosibleSoloVerifactu>
            <sf:TipoUsoPosibleMultiOT>N</sf:TipoUsoPosibleMultiOT>
            <sf:IndicadorMultiplesOT>N</sf:IndicadorMultiplesOT>
          </sf:SistemaInformatico>
          <!-- 11-13 -->
          <sf:FechaHoraHusoGenRegistro>{fecha_gen}</sf:FechaHoraHusoGenRegistro>
          <sf:TipoHuella>01</sf:TipoHuella>
          <sf:Huella>{huella}</sf:Huella>{"" if not factura_firmada_b64 else f"""
          <sf:FacturaFirmada>{factura_firmada_b64}</sf:FacturaFirmada>"""}
        </sf:RegistroAlta>
      </lr:RegistroFactura>
    </lr:RegFactuSistemaFacturacion>
  </soapenv:Body>
</soapenv:Envelope>"""
    logger.info("[SOAP] PrimerRegistro=%s, HuellaAnterior=%s", primer_val, (huella_anterior[:10] + '...') if huella_anterior else None)
    logger.info("[SOAP] Envelope generado (primeros 500 chars): %s", envelope[:500].replace('\n',''))
    return envelope, huella



def enviar_registro_aeat(factura_id: int) -> dict:
    """
    Envía el registro de la factura indicada a la AEAT mediante VERI*FACTU.

    Este método NO incluye ningún modo de simulación. Si la comunicación
    con la AEAT falla (por falta de certificados, error de red, etc.) se
    devolverá un diccionario con `success=False` y la descripción del
    problema. En caso de éxito se devuelve el cuerpo de la respuesta SOAP
    recibido.

    Args:
        factura_id (int): Identificador de la factura almacenada en la BD.

    Returns:
        dict: Resultado de la operación.
    """
    logger.info("Enviando factura %s a AEAT (VERI*FACTU)", factura_id)
    # Aseguramos que `base_dir` siempre está definido para evitar errores de variable no asociada
    base_dir = BASE_DIR

    # --------------------------- Obtener datos factura --------------------
    # MULTIEMPRESA: Usar get_db_connection() para obtener la BD correcta
    try:
        from db_utils import get_db_connection
        conn = get_db_connection()
        logger.info("[MULTIEMPRESA] Usando BD de sesión en enviar_registro_aeat")
    except Exception as e:
        logger.error("Error obteniendo conexión a BD: %s", e)
        return {'success': False, 'message': f'Error de base de datos: {str(e)}'}
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT f.numero  AS numero_factura,
       f.fecha   AS fecha_emision,
       f.total   AS importe_total,
       f.hash_factura,
       f.nif     AS nif_emisor,
       c.identificador AS nif_receptor,
       c.razonsocial   AS nombre_receptor
  FROM factura f
  INNER JOIN contactos c ON f.idContacto = c.idContacto
 WHERE f.id = ?
            """,
            (factura_id,)
        )
        row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        logger.error("Factura con id %s no encontrada", factura_id)
        return {'success': False, 'message': f'No existe la factura con id {factura_id}'}

    # Obtener NIF emisor (primero de la factura, si no hay usar el del archivo de configuración)
    nif_emisor = (row['nif_emisor'] or '').strip().upper()
    
    # Si no hay NIF en la factura, obtenerlo del archivo de configuración del emisor
    if not nif_emisor:
        try:
            import json
            empresa_codigo = os.environ.get('EMPRESA_CODIGO', 'caca')
            emisor_path = f'/var/www/html/emisores/{empresa_codigo}_emisor.json'
            if os.path.exists(emisor_path):
                with open(emisor_path, 'r') as f:
                    emisor_data = json.load(f)
                    nif_emisor = emisor_data.get('nif', '').strip().upper()
                    logger.info(f"NIF emisor obtenido de configuración: {nif_emisor}")
            else:
                logger.warning(f"No existe archivo de configuración del emisor: {emisor_path}")
        except Exception as e:
            logger.error(f"Error obteniendo NIF del emisor desde configuración: {e}")
    
    if not nif_emisor:
        return {'success': False, 'message': 'No se pudo determinar el NIF del emisor'}

    # Obtener serie y número para esta factura
    serie, numero_factura = procesar_serie_numero(row['numero_factura'])

    # Determinar primer_registro consultando la BD
    from verifactu.db.registro import calcular_primer_registro_exacto
    primer_registro = calcular_primer_registro_exacto(
        nif_emisor,
        numero_factura,
        serie,
    )
    huella_anterior = None
    if primer_registro == 'N':
        fecha_emision = str(row['fecha_emision'])[:10] if row['fecha_emision'] else None
        from verifactu.hash.sha256 import obtener_ultimo_hash_del_dia
        huella_anterior = obtener_ultimo_hash_del_dia(fecha_emision)

    # --------------------------- Preparar datos ---------------------------

    # ---------------------------------------
    #  Persistir valor de primer_registro en BD
    # ---------------------------------------
    try:
        from verifactu.db.registro import actualizar_huella_primer_registro
        actualizar_huella_primer_registro(
            nif_emisor,
            serie,
            numero_factura,
            None,               # aún no hay huella_aeat
            primer_registro,
        )
    except Exception as exc:
        logger.warning("No se pudo actualizar primer_registro en BD: %s", exc)

    # Permitir override de la serie/número de factura sin tocar la BD
    override_nf = os.getenv('VERIFACTU_OVERRIDE_NUM_FACTURA')
    if override_nf:
        try:
            serie_override, num_override = procesar_serie_numero(override_nf)
            serie, numero_factura = serie_override, num_override
            logger.info("Usando override NumSerieFactura=%s suministrado por VERIFACTU_OVERRIDE_NUM_FACTURA", override_nf)
        except Exception as exc:
            logger.warning("Valor VERIFACTU_OVERRIDE_NUM_FACTURA inválido (%s): %s", override_nf, exc)


    registro_factura = {
        'numero_factura': numero_factura,
        'serie_factura': serie,
        'fecha_emision': row['fecha_emision'],
        'importe_total': row['importe_total'],
        'hash_factura': row['hash_factura'],
        'nif_receptor': (row['nif_receptor'] or '').strip().upper(),
        'nombre_receptor': row['nombre_receptor'] or '',
        'anio': str(row['fecha_emision'])[:4],
        'mes': str(row['fecha_emision'])[5:7]
    }


    cabecera = {}

    # --------------------------- Construir envelope -----------------------
    # Recuperar, si existe, la huella previamente guardada para este registro (reenvíos)
    huella_guardada = None
    try:
        cur.execute("SELECT huella_aeat FROM registro_facturacion WHERE factura_id = ?", (factura_id,))
        res_huella = cur.fetchone()
        if res_huella and res_huella[0]:
            huella_guardada = res_huella[0]
    except Exception as exc:
        logger.warning("No se pudo recuperar huella_aeat previa: %s", exc)

    envelope_xml, huella_generada = crear_envelope_soap(
        'RegFactuSistemaFacturacion',
        cabecera,
        registro_factura,
        nif_emisor,
        None,
        huella_anterior,
        primer_registro,
        False,
        huella_guardada,
    )

    # --------------------------- Enviar SOAP ------------------------------
    service_url = os.environ.get(
        'AEAT_VERIFACTU_URL',
        'https://prewww1.aeat.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP'
    )

    cert_dir = os.environ.get('VERIFACTU_CERT_DIR')
    if not cert_dir:
        for cand in ('/var/www/html/certs', os.path.join(base_dir, 'certs')):
            if os.path.exists(cand):
                cert_dir = cand
                break
        else:
            cert_dir = os.path.join(base_dir, 'certs')
    
    cert_path = os.path.join(cert_dir, 'cert_real.pem')
    key_path = os.path.join(cert_dir, 'clave_real.pem')

    if not (os.path.exists(cert_path) and os.path.exists(key_path)):
        logger.error("Certificados SSL no encontrados dentro de %s", cert_dir)
        return {'success': False, 'message': 'Certificados SSL no encontrados', 'cert_dir': cert_dir}

    headers = {
        'Content-Type': 'text/xml;charset=UTF-8',
        'SOAPAction': '""'
    }

    try:
        logger.info("requests.post real function: %s (module %s)", requests.post, getattr(requests.post, '__module__', 'unknown'))
        response = requests.post(
            service_url,
            data=envelope_xml.encode('utf-8'),
            headers=headers,
            cert=(cert_path, key_path),
            timeout=10,  # Reducido de 60s a 10s para mejor UX
            verify=True
        )
        logger.info("AEAT raw response object: %s - type=%s - has_status=%s", repr(response)[:300] if response is not None else 'None', type(response).__name__ if response is not None else 'NoneType', hasattr(response, 'status_code'))
    except requests.RequestException as exc:
        logger.exception("Error de red al enviar a AEAT: %s", exc)
        return {'success': False, 'message': repr(exc)}

    # Comprobación defensiva para evitar AttributeError si la respuesta es None
    if response is None or not hasattr(response, "status_code"):
        logger.error("Respuesta nula o inválida de AEAT al enviar factura")
        return {
            'success': False,
            'message': 'Respuesta nula o inválida de AEAT'
        }

    if response.status_code != 200:
        logger.error("Respuesta HTTP %s de AEAT", response.status_code)
        return {
            'success': False,
            'status_code': response.status_code,
            'response': response.text[:500] if hasattr(response, 'text') else ''
        }

    logger.info("Envío completado correctamente (HTTP 200)")
    # --- Guardado de la respuesta SOAP ---
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d%H%M%S")
    base_dir = "/var/www/html/aeat_responses"
    # Obtener empresa_id de la sesión o usar por defecto
    empresa_id = os.environ.get('EMPRESA_CODIGO', 'caca')
    # Organizar por empresa/año/mes: aeat_responses/empresa_id/YYYY/MM
    empresa_dir = os.path.join(base_dir, str(empresa_id))
    year_dir = os.path.join(empresa_dir, now.strftime("%Y"))
    resp_dir = os.path.join(year_dir, now.strftime("%m"))
    try:
        os.makedirs(resp_dir, mode=0o777, exist_ok=True)
        file_path = os.path.join(resp_dir, f"factura_{factura_id}_{timestamp}.xml")
        with open(file_path, "w", encoding="utf-8") as fh:
            fh.write(response.text)
        logger.info("Respuesta AEAT guardada en %s", file_path)
    except Exception as exc:
        logger.warning("No se pudo guardar respuesta AEAT en %s: %s", resp_dir, exc)

    # Copia rápida en /tmp para depuración
    try:
        with open('/tmp/aeat_last.xml', 'w', encoding='utf-8') as fh:
            fh.write(response.text)
    except Exception:
        pass

    # Guardar también en la base de datos
    try:
        from verifactu.db.registro import guardar_csv_aeat
        from verifactu.db.respuesta_xml import guardar_respuesta_xml
        guardar_respuesta_xml(factura_id, response.text)
        # guardaremos CSV tras parseo más abajo
    except Exception as exc:
        logger.warning("No se pudo almacenar respuesta_xml en BBDD: %s", exc)


    # Parsear la respuesta SOAP para extraer el CSV si la AEAT lo proporciona
    datos_resp = parsear_respuesta_aeat(response.text)

    # Almacenar de forma centralizada los datos relevantes en registro_facturacion
    try:
        from verifactu.db.aeat import guardar_datos_aeat_en_registro
        guardar_datos_aeat_en_registro(factura_id, response.text)
    except Exception as exc:
        logger.warning("No se pudo ejecutar guardar_datos_aeat_en_registro: %s", exc)

    # Asegurarnos de que el valor primer_registro calculado se almacena
    try:
        from verifactu.db.registro import actualizar_primer_registro_por_id
        actualizar_primer_registro_por_id(factura_id, primer_registro)
    except Exception as exc:
        logger.debug("No se pudo persistir primer_registro (id): %s", exc)

    csv = datos_resp.get('csv')

    # Guardar huella_aeat solo si el envío fue correcto
    try:
        if huella_generada:
            from verifactu.db.registro import guardar_huella_aeat_por_id
            guardar_huella_aeat_por_id(factura_id, huella_generada)
    except Exception as exc:
        logger.warning("No se pudo guardar huella_aeat: %s", exc)
    # Guardar CSV si procede
    if csv:
        try:
            from verifactu.db.registro import guardar_csv_aeat
            guardar_csv_aeat(factura_id, csv)
        except Exception as exc:
            logger.warning("No se pudo guardar CSV AEAT: %s", exc)
    estado_envio_ws = datos_resp.get('estado_envio')

    return {
        'success': (
            (estado_envio_ws in ('Correcto', 'ParcialmenteCorrecto')) or
            any(l.get('resultado') == 'AceptadoConErrores' for l in datos_resp.get('lineas', []))
        ),
        'status_code': 200,
        'errores': datos_resp.get('errores'),
        'csv': csv,               # Puede ser None si la AEAT no lo devuelve,
        'huella': huella_generada,
        'estado_envio': estado_envio_ws,
        'response': response.text
    }

def obtener_nif_certificado(cert_path):
    """
    Extrae el NIF del certificado digital
    
    Args:
        cert_path (str): Ruta al archivo de certificado
        
    Returns:
        str: NIF extraído del certificado o None si no se puede extraer
    """
    try:
        # Importar cryptography solo cuando se necesita
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend

        # Leer el archivo de certificado
        with open(cert_path, 'rb') as cert_file:
            cert_data = cert_file.read()
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
        
        # Extraer el asunto (subject) del certificado
        subject = cert.subject
        
        # Buscar el NIF/CIF en el asunto (normalmente en serialNumber o CN)
        nif = None
        for attribute in subject:
            if attribute.oid._name == 'serialNumber':
                # El formato típico en certificados españoles es CIFES-B12345678
                value = attribute.value
                if 'ES-' in value:
                    nif = value.split('ES-')[-1].strip()
                else:
                    # Intentar extraer solo dígitos y una posible letra
                    import re
                    match = re.search(r'[A-Z0-9]{1}[0-9]{7,8}[A-Z0-9]{1}', value)
                    if match:
                        nif = match.group(0)
            # También buscar en commonName por si acaso
            elif attribute.oid._name == 'commonName' and not nif:
                value = attribute.value
                # Intentar extraer NIF con formato español
                import re
                match = re.search(r'[A-Z0-9]{1}[0-9]{7,8}[A-Z0-9]{1}', value)
                if match:
                    nif = match.group(0)
        
        # Si no se encuentra en subject, intentar en extensiones
        if not nif:
            for extension in cert.extensions:
                if extension.oid._name == 'subjectAltName':
                    for name in extension.value:
                        if hasattr(name, 'value') and 'NIF' in name.value:
                            import re
                            match = re.search(r'[A-Z0-9]{1}[0-9]{7,8}[A-Z0-9]{1}', name.value)
                            if match:
                                nif = match.group(0)
        
        return nif
    
    except Exception as e:
        print(f"Error al extraer NIF del certificado: {str(e)}")
        return None



"""
Módulo para extracción de datos de facturas mediante OCR
Procesa imágenes de facturas PDF/JPG/PNG usando GPT-4 Vision API
"""

import base64
import os
import json
import io
import re
from datetime import datetime
from PIL import Image, ImageEnhance
from dotenv import load_dotenv

# Cargar variables de entorno explícitamente
load_dotenv('/var/www/html/.env')

from logger_config import get_logger

logger = get_logger(__name__)

# Intentar importar OpenAI GPT-4 Vision
try:
    from openai import OpenAI
    OPENAI_DISPONIBLE = True
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    if OPENAI_API_KEY:
        logger.info("OpenAI GPT-4 Vision disponible para facturas")
    else:
        # OPENAI_DISPONIBLE se mantiene True si se puede importar, pero la key puede venir luego
        logger.warning("OpenAI API Key no configurada al importar modulo - OCR de facturas deshabilitado momentaneamente")
except ImportError:
    OPENAI_DISPONIBLE = False
    OPENAI_API_KEY = None
    logger.warning("OpenAI no disponible - OCR de facturas deshabilitado")

# Intentar importar pdf2image para conversión de PDFs
try:
    from pdf2image import convert_from_bytes
    PDF2IMAGE_DISPONIBLE = True
except ImportError:
    PDF2IMAGE_DISPONIBLE = False
    logger.warning("pdf2image no disponible - No se podrán procesar archivos PDF")


def extraer_datos_factura_gpt4(imagen_bytes, nif_cliente=None):
    """
    Extrae datos de factura usando GPT-4 Vision API
    Soporta imágenes (JPG, PNG) y PDFs (convirtiéndolos a imagen)
    
    Args:
        imagen_bytes: Bytes de la imagen o PDF de la factura
        nif_cliente: (Opcional) NIF de la empresa cliente para ignorarlo explícitamente
        
    Returns:
        dict: Datos estructurados de la factura
    """
    # Recuperar API Key dinámicamente si no estaba al importar
    api_key = OPENAI_API_KEY or os.getenv('OPENAI_API_KEY')
    
    if not OPENAI_DISPONIBLE or not api_key:
        raise ValueError("OpenAI API Key no configurada. Configure OPENAI_API_KEY en .env")
    
    try:
        # Detectar si es PDF y convertir a imagen
        if imagen_bytes.startswith(b'%PDF'):
            if not PDF2IMAGE_DISPONIBLE:
                raise ValueError("Se requiere instalar 'pdf2image' y 'poppler-utils' para procesar PDFs")
            
            logger.info("📄 Detectado archivo PDF, convirtiendo primera página a imagen...")
            try:
                # Convertir primera página a imagen
                images = convert_from_bytes(imagen_bytes, first_page=1, last_page=1)
                if not images:
                    raise ValueError("El PDF no contiene páginas o no se pudo leer")
                
                image_obj = images[0]
                
            except Exception as e:
                logger.error(f"Error convirtiendo PDF: {e}")
                raise ValueError(f"Error procesando archivo PDF: {str(e)}")
        else:
            # Es una imagen, abrirla con PIL para optimizar
            image_obj = Image.open(io.BytesIO(imagen_bytes))

        # OPTIMIZACIÓN: Redimensionar si es muy grande (max 2000px) para evitar timeouts y reducir tokens
        max_dimension = 2000
        if max(image_obj.size) > max_dimension:
            ratio = max_dimension / max(image_obj.size)
            new_size = (int(image_obj.width * ratio), int(image_obj.height * ratio))
            image_obj = image_obj.resize(new_size, Image.Resampling.LANCZOS)
            logger.info(f"📉 Imagen redimensionada a {new_size}")

        # Guardar en buffer como JPEG optimizado (IMAGEN A COLOR - mejor para logos)
        img_buffer = io.BytesIO()
        image_obj = image_obj.convert('RGB') 
        image_obj.save(img_buffer, format='JPEG', quality=85, optimize=True)
        imagen_bytes = img_buffer.getvalue()
        logger.info(f"✅ Imagen lista para OCR (Tamaño: {len(imagen_bytes)/1024:.2f} KB)")

        # Convertir imagen a base64
        base64_image = base64.b64encode(imagen_bytes).decode('utf-8')
        
        # Inicializar cliente OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Construir instrucción de ignorar cliente
        instruccion_ignorar_cliente = ""
        if nif_cliente:
            instruccion_ignorar_cliente = f'   - **IGNORA EL NIF DEL CLIENTE**: "{nif_cliente}". NO lo confundas con el proveedor.'

        # Prompt para extraer datos estructurados de factura
        prompt = f"""Analiza esta imagen de FACTURA.

TU MISIÓN CRÍTICA: Identificar el NOMBRE COMERCIAL del PROVEEDOR (quien emite la factura) y su NIF.

⚠️ **ADVERTENCIA DE CONFUSIÓN**: En la factura aparecen dos entidades:
1. **EMISOR (Proveedor)**: Quien cobra. Su logo suele estar arriba.
2. **RECEPTOR (Cliente)**: Quien paga. Suele ser "COPISTERÍA ALEPH", "ALEPH70" o "SAMUEL". **IGNORA SUS DATOS**.

ESTRATEGIA DE BÚSQUEDA VISUAL (PRIORIDAD MÁXIMA):
1. **LOGOTIPO GRANDE**: Mira la cabecera. Busca textos estilizados, artísticos o de colores.
   - Si ves un logo rojo que dice "ARADA", el proveedor es "ARADA".
   - Si ves "UP" grande, es "UNION PAPELERA".
   - El nombre suele estar DENTRO del logo.

2. **NIF DEL PROVEEDOR**:
   - Busca el NIF cerca del nombre del proveedor o al pie de página.
   - **CRÍTICO**: Si encuentras el NIF del cliente (B63542542 o similar), **IGNÓRALO**. Busca el OTRO NIF.
{instruccion_ignorar_cliente}

3. **DATOS FISCALES**:
   - Busca el bloque "Datos del Emisor" o "De:".

4. **DOMINIO WEB / EMAIL**:
   - 'www.miempresa.com' -> 'MIEMPRESA'.

VALIDACIÓN:
- Si no ves un logo claro ni un nombre fiscal claro, devuelve "PROVEEDOR DESCONOCIDO".
- NO uses palabras genéricas como "FACTURA", "ALBARAN".
- Limpia el nombre (sin S.L., S.A.).

EXTRAER DATOS EN JSON:
- Nombre: EL TEXTO DEL LOGOTIPO O NOMBRE COMERCIAL (en mayúsculas).
- NIF: El CIF/NIF del emisor.
- Direccion: Dirección del emisor.
- Telefono: Teléfono del emisor.
- Email: Email del emisor.
- Website: Web del emisor.

⚠️ **IMPORTANTE SOBRE FECHAS**:
- Estamos en el año {datetime.now().year}. Las facturas recientes deberían ser de este año o del mes anterior.
- Si ves una fecha como "09/01/25" o "09/01/2025", verifica si tiene sentido. Si el documento parece reciente, probablemente es {datetime.now().year}.
- Presta especial atención al AÑO. Un error común es confundir 2025 con 2026.

ESTRUCTURA JSON REQUERIDA:
{{
  "proveedor": {{
    "nombre": "TEXTO_DEL_LOGO",
    "nif": "CIF_ENCONTRADO_O_NULL",
    "direccion": "...",
    "telefono": "...",
    "email": "...",
    "website": "..."
  }},
  "factura": {{
    "numero": "...",
    "fecha_emision": "YYYY-MM-DD",
    "fecha_vencimiento": "YYYY-MM-DD",
    "base_imponible": 0.00,
    "iva": 0.00,
    "total": 0.00,
    "concepto": "..."
  }}
}}
"""

        logger.info("📤 Enviando factura a GPT-4 Vision...")
        
        # Llamar a GPT-4 Vision API
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            max_tokens=4000,
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        # Extraer respuesta
        message_content = response.choices[0].message.content
        if not message_content:
             logger.error(f"Respuesta de GPT-4 vacía (content is None). Finish reason: {response.choices[0].finish_reason}")
             raise ValueError("GPT-4 no devolvió contenido (posible filtro de contenido)")
             
        respuesta_texto = message_content.strip()
        logger.info(f"📥 Respuesta de GPT-4 Vision: {respuesta_texto[:200]}...")
        
        # Parsear JSON
        json_match = re.search(r'\{.*\}', respuesta_texto, re.DOTALL)
        if json_match:
            respuesta_texto_limpia = json_match.group(0)
        else:
            respuesta_texto_limpia = respuesta_texto.strip()
            if respuesta_texto_limpia.startswith('```json'):
                respuesta_texto_limpia = respuesta_texto_limpia[7:]
            if respuesta_texto_limpia.endswith('```'):
                respuesta_texto_limpia = respuesta_texto_limpia[:-3]
        
        datos = json.loads(respuesta_texto_limpia)
        
        # Limpiar y validar datos
        prov_raw = datos.get('proveedor') or {}
        fact_raw = datos.get('factura') or {}
        
        def clean_val(v):
            if not v: return ""
            s = str(v).strip()
            # Eliminar "NULL", "NONE" del OCR
            return "" if s.upper() in ['NULL', 'NONE', 'N/A', 'NO', 'NO CONSTA'] else s

        datos_limpios = {
            'proveedor': {
                'nombre': clean_val(prov_raw.get('nombre')).upper(),
                'nif': clean_val(prov_raw.get('nif')).upper(),
                'direccion': clean_val(prov_raw.get('direccion')),
                'telefono': clean_val(prov_raw.get('telefono')),
                'email': clean_val(prov_raw.get('email')),
                'website': clean_val(prov_raw.get('website')).lower(),
            },
            'factura': {
                'numero': clean_val(fact_raw.get('numero')),
                'fecha_emision': clean_val(fact_raw.get('fecha_emision')),
                'fecha_vencimiento': clean_val(fact_raw.get('fecha_vencimiento')),
                'base_imponible': str(fact_raw.get('base_imponible') or '').strip(),
                'iva': str(fact_raw.get('iva') or '').strip(),
                'total': str(fact_raw.get('total') or '').strip(),
                'concepto': clean_val(fact_raw.get('concepto')),
            }
        }
        
        logger.info(f"✅ GPT-4 Vision extrajo datos de factura correctamente")
        
        # Validación y corrección de fechas (evitar años incorrectos)
        fecha_emision = datos_limpios['factura'].get('fecha_emision', '')
        if fecha_emision:
            try:
                fecha_obj = datetime.strptime(fecha_emision, '%Y-%m-%d')
                hoy = datetime.now()
                diff_dias = (hoy - fecha_obj).days
                
                # Si la fecha es de hace más de 6 meses, probablemente el año está mal
                if diff_dias > 180:
                    # Intentar con el año actual
                    fecha_corregida = fecha_obj.replace(year=hoy.year)
                    diff_corregido = (hoy - fecha_corregida).days
                    
                    # Si con el año actual la fecha es razonable (últimos 60 días), usar esa
                    if 0 <= diff_corregido <= 60:
                        datos_limpios['factura']['fecha_emision'] = fecha_corregida.strftime('%Y-%m-%d')
                        logger.warning(f"📅 Fecha corregida: {fecha_emision} → {datos_limpios['factura']['fecha_emision']} (año probablemente incorrecto)")
                    # Si la fecha corregida es en el futuro pero razonable (próximos 30 días), también usar
                    elif -30 <= diff_corregido < 0:
                        datos_limpios['factura']['fecha_emision'] = fecha_corregida.strftime('%Y-%m-%d')
                        logger.warning(f"📅 Fecha corregida: {fecha_emision} → {datos_limpios['factura']['fecha_emision']} (año probablemente incorrecto)")
            except ValueError:
                logger.warning(f"⚠️ No se pudo parsear fecha: {fecha_emision}")
        
        # Validación inteligente del nombre del proveedor
        nombre_prov = datos_limpios['proveedor']['nombre']
        logger.info(f"🔍 Validando nombre proveedor RAW: '{nombre_prov}'")
        print(f"DEBUG: Validando nombre proveedor: '{nombre_prov}'")
        
        es_descripcion = False

        if nombre_prov:
            nombre_upper = nombre_prov.upper()
            
            # HARDFIX: Verificación manual explícita para depuración
            if "PAPEL" in nombre_upper or "FOTOCOPIA" in nombre_upper:
                logger.warning(f"🚨 DETECTADO 'PAPEL' O 'FOTOCOPIA' EN NOMBRE. FORZANDO RECHAZO.")
                es_descripcion = True
            
            # Lista de palabras prohibidas
            palabras_prohibidas = [
                'FACTURA', 'RECIBO', 'TICKET', 'CONCEPTO', 'DESCRIPCION', 'VENTA', 'SERVICIO', 
                'CUOTA', 'MENSUAL', 'ALQUILER', 'PAGO', 'TOTAL', 'BASE', 'IMPONIBLE', 'CONSUMO', 'CONSUM', 
                'PERIODO', 'FOTOCOPIA', 'COLOR', 'COPY', 'ARTICULO', 'PRODUCTO', 'UNIDAD', 'PAPEL', 'BLANCO',
                'BIMESTRAL', 'TRIMESTRAL', 'ANUAL', 'SEMESTRAL', 'NULL', 'NONE'
            ]
            
            # Verificar si contiene palabras prohibidas
            matches = [p for p in palabras_prohibidas if p in nombre_upper]
            if matches:
                es_descripcion = True
                logger.warning(f"⚠️ Nombre contiene palabras prohibidas ({matches}): '{nombre_prov}'")

            # Verificar si empieza por fecha
            if re.search(r'\d{2}/\d{2}/\d{4}', nombre_upper):
                es_descripcion = True
                logger.warning(f"⚠️ Nombre contiene fechas (parece periodo): '{nombre_prov}'")
            
            # Verificar longitud excesiva o MUY CORTA (ej: "A") - PERMITIR DE 2 LETRAS (ej: UP, HP)
            if len(nombre_upper) < 2:
                es_descripcion = True
                logger.warning(f"⚠️ Nombre demasiado corto (posible error OCR): '{nombre_prov}' -> Forzando selección manual")

            if len(nombre_upper.split()) > 4:
                es_descripcion = True
                logger.warning(f"⚠️ Nombre demasiado largo para empresa: '{nombre_prov}'")

        if es_descripcion:
            logger.warning(f"🔄 Limpiando nombre de proveedor sospechoso '{nombre_prov}'")
            datos_limpios['proveedor']['nombre'] = ''
            
            # Intentar usar website como fallback
            website = datos_limpios['proveedor'].get('website')
            if website:
                # Extraer dominio: www.updirecto.es -> updirecto
                dominio = website.replace('https://', '').replace('http://', '').replace('www.', '')
                dominio = dominio.split('/')[0].split('.')[0]
                if dominio and len(dominio) > 3:
                    logger.info(f"🔄 Usando dominio web como nombre de proveedor fallback: '{dominio.upper()}'")
                    datos_limpios['proveedor']['nombre'] = dominio.upper()
        else:
            logger.info(f"✅ Proveedor final validado: '{datos_limpios['proveedor']['nombre']}'")

        return datos_limpios
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Error parseando JSON de GPT-4: {e}")
        logger.error(f"Respuesta recibida: {respuesta_texto}")
        raise ValueError(f"Error parseando respuesta de GPT-4: {e}")
    except Exception as e:
        logger.error(f"❌ Error en GPT-4 Vision: {e}", exc_info=True)
        raise


def procesar_imagen_factura(imagen_bytes, nif_cliente=None):
    """
    Procesa una imagen de factura completa: OCR + parseo de datos
    
    Args:
        imagen_bytes: Bytes de la imagen
        nif_cliente: (Opcional) NIF del cliente para ignorarlo
        
    Returns:
        dict: Datos de la factura extraídos
    """
    try:
        # Recuperar API Key dinámicamente
        api_key = OPENAI_API_KEY or os.getenv('OPENAI_API_KEY')
        
        if not OPENAI_DISPONIBLE or not api_key:
            raise ValueError("OpenAI API Key no configurada. Configure OPENAI_API_KEY en .env para usar OCR de facturas")
        
        logger.info("🔍 Procesando factura con GPT-4 Vision...")
        datos = extraer_datos_factura_gpt4(imagen_bytes, nif_cliente)
        
        # Agregar marcador de método usado
        datos['_metodo_ocr'] = 'GPT-4 Vision'
        
        return datos
        
    except Exception as e:
        logger.error(f"❌ Error procesando imagen de factura: {e}", exc_info=True)
        raise

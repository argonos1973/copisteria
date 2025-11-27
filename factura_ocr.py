"""
Módulo para extracción de datos de facturas mediante OCR
Procesa imágenes de facturas PDF/JPG/PNG usando GPT-4 Vision API
"""

import base64
import os
import json
import io
import re
from PIL import Image
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
        OPENAI_DISPONIBLE = False
        logger.warning("OpenAI API Key no configurada - OCR de facturas deshabilitado")
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


def extraer_datos_factura_gpt4(imagen_bytes):
    """
    Extrae datos de factura usando GPT-4 Vision API
    Soporta imágenes (JPG, PNG) y PDFs (convirtiéndolos a imagen)
    
    Args:
        imagen_bytes: Bytes de la imagen o PDF de la factura
        
    Returns:
        dict: Datos estructurados de la factura
    """
    if not OPENAI_DISPONIBLE or not OPENAI_API_KEY:
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

        # Guardar en buffer como JPEG optimizado
        img_buffer = io.BytesIO()
        image_obj = image_obj.convert('RGB') # Asegurar RGB
        image_obj.save(img_buffer, format='JPEG', quality=85, optimize=True)
        imagen_bytes = img_buffer.getvalue()
        logger.info(f"✅ Imagen lista para OCR (Tamaño: {len(imagen_bytes)/1024:.2f} KB)")

        # Convertir imagen a base64
        base64_image = base64.b64encode(imagen_bytes).decode('utf-8')
        
        # Inicializar cliente OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Prompt para extraer datos estructurados de factura
        prompt = """Analiza esta imagen de FACTURA, TICKET O RECIBO BANCARIO y extrae los datos.

PASO 1 - IDENTIFICAR AL PROVEEDOR (MUY IMPORTANTE):
El proveedor es la EMPRESA QUE EMITE la factura.
- Busca el LOGOTIPO principal. Esa es la marca.
- Busca la RAZÓN SOCIAL (S.L., S.A., etc) para confirmar.
- Busca el CIF/NIF.

PASO 2 - NORMALIZACIÓN DEL NOMBRE DEL PROVEEDOR (CRÍTICO):
Para el campo "nombre", debes devolver la MARCA COMERCIAL o NOMBRE COMÚN, simplificado y en MAYÚSCULAS.
- ELIMINA sufijos legales: S.L., S.A., S.L.U., S.A.U., C.B., S.C., etc.
- ELIMINA apellidos geográficos o funcionales si son secundarios a la marca principal.
- EJEMPLOS:
  * "VODAFONE ESPAÑA S.A.U." -> "VODAFONE"
  * "VODAFONE SERVICIOS S.L." -> "VODAFONE"
  * "UNIÓN PAPELERA MERCHANTING S.L." -> "UNIÓN PAPELERA"
  * "AMAZON EU SARL SUCURSAL EN ESPAÑA" -> "AMAZON"
  * "REPSOL COMERCIAL DE PRODUCTOS PETROLIFEROS S.A." -> "REPSOL"
- El objetivo es que facturas de distintas filiales de la misma empresa (mismo logo) tengan el MISMO "nombre".

PASO 3 - Devuelve un JSON con esta estructura:
{
  "proveedor": {
    "nombre": "MARCA COMERCIAL NORMALIZADA (ej: VODAFONE)",
    "razon_social_completa": "Nombre legal completo tal cual aparece (ej: VODAFONE ESPAÑA S.A.U.)",
    "nif": "CIF/NIF del proveedor (ej: B12345678)",
    "direccion": "dirección completa del proveedor",
    "telefono": "teléfono del proveedor",
    "email": "email del proveedor"
  },
  "factura": {
    "numero": "número de factura/ticket/documento",
    "fecha_emision": "YYYY-MM-DD",
    "fecha_vencimiento": "YYYY-MM-DD",
    "base_imponible": 0.00,
    "iva": 0.00,
    "total": 0.00,
    "concepto": "descripción breve del contenido"
  },
  "lineas_detalle": [
    {
      "codigo": "código del artículo",
      "descripcion": "descripción del producto/servicio",
      "importe": 0.00
    }
  ]
}

REGLAS:
- El nombre del proveedor es OBLIGATORIO.
- Usa "" (vacío) si un campo no aparece.
- Ignora datos del cliente.
- Fechas YYYY-MM-DD.
- Importes decimales.
"""

        logger.info("📤 Enviando factura a GPT-4 Vision...")
        
        # Llamar a GPT-4 Vision API
        response = client.chat.completions.create(
            model="gpt-4o",  # Modelo más reciente y eficiente
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
                                "detail": "high"  # Alta resolución para mejor OCR
                            }
                        }
                    ]
                }
            ],
            max_tokens=4000,
            temperature=0.1,  # Baja temperatura para respuestas más determinísticas
            response_format={"type": "json_object"}  # Forzar respuesta JSON válida
        )
        
        # Extraer respuesta
        message_content = response.choices[0].message.content
        if not message_content:
             logger.error(f"Respuesta de GPT-4 vacía (content is None). Finish reason: {response.choices[0].finish_reason}")
             raise ValueError("GPT-4 no devolvió contenido (posible filtro de contenido)")
             
        respuesta_texto = message_content.strip()
        logger.info(f"📥 Respuesta de GPT-4 Vision: {respuesta_texto[:200]}...")
        
        # Parsear JSON
        # Limpiar posibles markdown code blocks
        
        # 1. Intentar extraer JSON con regex (más robusto)
        json_match = re.search(r'\{.*\}', respuesta_texto, re.DOTALL)
        if json_match:
            respuesta_texto_limpia = json_match.group(0)
        else:
            # 2. Fallback a limpieza manual
            respuesta_texto_limpia = respuesta_texto
            if respuesta_texto_limpia.startswith('```'):
                parts = respuesta_texto_limpia.split('```')
                if len(parts) > 1:
                    respuesta_texto_limpia = parts[1]
                    if respuesta_texto_limpia.startswith('json'):
                        respuesta_texto_limpia = respuesta_texto_limpia[4:]
            respuesta_texto_limpia = respuesta_texto_limpia.strip()
        
        if not respuesta_texto_limpia:
             logger.error(f"Respuesta de GPT-4 vacía o sin JSON. Raw: {respuesta_texto}")
             raise ValueError("La respuesta de GPT-4 está vacía o no contiene JSON válido")

        # Validación extra: debe empezar por { y terminar por }
        if not respuesta_texto_limpia.startswith('{'):
             logger.error(f"La respuesta no parece un JSON válido. Raw: {respuesta_texto_limpia}")
             raise ValueError(f"GPT-4 devolvió texto plano en lugar de JSON: {respuesta_texto_limpia[:50]}...")

        datos = json.loads(respuesta_texto_limpia)
        
        # Validar estructura
        if 'proveedor' not in datos or 'factura' not in datos:
            logger.error("Respuesta de GPT-4 no tiene la estructura esperada")
            raise ValueError("Estructura de respuesta inválida")
        
        # Limpiar y validar datos
        # CORRECCIÓN: Usar (get() or '') para evitar que un valor null provoque error en .strip()
        prov_raw = datos.get('proveedor') or {}
        fact_raw = datos.get('factura') or {}
        
        datos_limpios = {
            'proveedor': {
                'nombre': (prov_raw.get('nombre') or '').strip().upper(),
                'nif': (prov_raw.get('nif') or '').strip().upper(),
                'direccion': (prov_raw.get('direccion') or '').strip(),
                'telefono': (prov_raw.get('telefono') or '').strip(),
                'email': (prov_raw.get('email') or '').strip(),
            },
            'factura': {
                'numero': (fact_raw.get('numero') or '').strip(),
                'fecha_emision': (fact_raw.get('fecha_emision') or '').strip(),
                'fecha_vencimiento': (fact_raw.get('fecha_vencimiento') or '').strip(),
                'base_imponible': str(fact_raw.get('base_imponible') or '').strip(),
                'iva': str(fact_raw.get('iva') or '').strip(),
                'total': str(fact_raw.get('total') or '').strip(),
                'concepto': (fact_raw.get('concepto') or '').strip(),
            }
        }
        
        logger.info(f"✅ GPT-4 Vision extrajo datos de factura correctamente")
        logger.info(f"   Proveedor: {datos_limpios['proveedor']['nombre']}")
        logger.info(f"   Factura: {datos_limpios['factura']['numero']}")
        logger.info(f"   Total: {datos_limpios['factura']['total']}")
        
        # Validación estructural inteligente del nombre del proveedor
        nombre_prov = datos_limpios['proveedor']['nombre']
        nif_prov = datos_limpios['proveedor']['nif']
        
        # Si tiene NIF válido (empieza por letra y tiene 8-9 caracteres alfanuméricos), confiamos más
        nif_valido = bool(nif_prov and len(nif_prov) >= 8 and nif_prov[0].isalpha())
        
        # Verificar si el nombre parece una DESCRIPCIÓN DE PRODUCTO en lugar de empresa
        es_descripcion_producto = False
        if nombre_prov:
            nombre_upper = nombre_prov.upper()
            palabras = nombre_upper.split()
            
            # Indicadores de que ES una empresa válida
            indicadores_empresa = ['S.L.', 'SL', 'S.A.', 'SA', 'S.L.U.', 'SLU', 'C.B.', 'S.C.', 'LTDA', 'INC', 'CORP']
            tiene_indicador_empresa = any(ind in nombre_upper for ind in indicadores_empresa)
            
            # Si tiene indicador de empresa, es válido
            if tiene_indicador_empresa:
                logger.info(f"✅ Proveedor válido (tiene indicador empresa): '{nombre_prov}'")
            elif nif_valido:
                logger.info(f"✅ Proveedor válido (tiene NIF válido {nif_prov}): '{nombre_prov}'")
            else:
                # Sin indicador de empresa ni NIF válido, verificar estructura
                # Las descripciones de producto suelen ser largas y tener conectores
                conectores_descripcion = [' Y ', ' DE ', ' PARA ', ' CON ', ' EN ']
                tiene_conectores = sum(1 for c in conectores_descripcion if c in nombre_upper) >= 2
                
                # Más de 4 palabras sin indicador de empresa es sospechoso
                if len(palabras) > 4 and tiene_conectores:
                    es_descripcion_producto = True
                    logger.warning(f"⚠️ Nombre parece descripción de producto: '{nombre_prov}' (muchas palabras + conectores)")
                elif len(palabras) > 6:
                    es_descripcion_producto = True
                    logger.warning(f"⚠️ Nombre demasiado largo para empresa: '{nombre_prov}'")
        
        # Si parece descripción de producto, limpiar para forzar asignación manual
        if es_descripcion_producto:
            logger.warning(f"🔄 Limpiando nombre de proveedor sospechoso, el usuario asignará manualmente")
            datos_limpios['proveedor']['nombre'] = ''
        else:
            logger.info(f"✅ Proveedor final: '{datos_limpios['proveedor']['nombre']}'")

        return datos_limpios
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Error parseando JSON de GPT-4: {e}")
        logger.error(f"Respuesta recibida: {respuesta_texto}")
        raise ValueError(f"Error parseando respuesta de GPT-4: {e}")
    except Exception as e:
        logger.error(f"❌ Error en GPT-4 Vision: {e}", exc_info=True)
        raise


def procesar_imagen_factura(imagen_bytes):
    """
    Procesa una imagen de factura completa: OCR + parseo de datos
    
    Args:
        imagen_bytes: Bytes de la imagen
        
    Returns:
        dict: Datos de la factura extraídos
    """
    try:
        if not OPENAI_DISPONIBLE or not OPENAI_API_KEY:
            raise ValueError("OpenAI API Key no configurada. Configure OPENAI_API_KEY en .env para usar OCR de facturas")
        
        logger.info("🔍 Procesando factura con GPT-4 Vision...")
        datos = extraer_datos_factura_gpt4(imagen_bytes)
        
        # Agregar marcador de método usado
        datos['_metodo_ocr'] = 'GPT-4 Vision'
        
        return datos
        
    except Exception as e:
        logger.error(f"❌ Error procesando imagen de factura: {e}", exc_info=True)
        raise

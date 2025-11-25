"""
Módulo para extracción de datos de facturas mediante OCR
Procesa imágenes de facturas PDF/JPG/PNG usando GPT-4 Vision API
"""

import base64
import os
import json
import io
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
        prompt = """Analiza esta imagen de FACTURA RECIBIDA y extrae los siguientes datos.

⚠️ MUY IMPORTANTE: 
- El PROVEEDOR es quien EMITE la factura (aparece arriba, en el encabezado)
- El CLIENTE es quien RECIBE la factura (aparece abajo, como "Facturar a:" o "Cliente:")
- SOLO extrae los datos del PROVEEDOR/EMISOR, NO del cliente/destinatario

Devuelve SOLO un objeto JSON válido con estos campos:

{
  "proveedor": {
    "nombre": "nombre o razón social del EMISOR de la factura (quien vende)",
    "nif": "NIF o CIF del EMISOR (NO del cliente)",
    "direccion": "dirección del EMISOR",
    "telefono": "teléfono del EMISOR",
    "email": "email del EMISOR"
  },
  "factura": {
    "numero": "número de factura (ej: FAC-2024-001, F-123, etc)",
    "fecha_emision": "fecha de emisión en formato YYYY-MM-DD",
    "fecha_vencimiento": "fecha de vencimiento en formato YYYY-MM-DD (si existe)",
    "base_imponible": "base imponible en número decimal (ej: 100.50)",
    "iva": "importe del IVA en número decimal (ej: 21.00)",
    "total": "importe total en número decimal (ej: 121.50)",
    "concepto": "descripción breve de los productos/servicios"
  }
}

REGLAS CRÍTICAS:
1. El proveedor.nif debe ser del EMISOR de la factura, NO del destinatario
2. Busca el NIF PRINCIPAL que está junto al nombre de la empresa en el ENCABEZADO
3. Si hay múltiples NIFs en el encabezado, usa el PRIMERO o el más prominente
4. Si ves "Facturar a:" o "Cliente:", esos datos NO son del proveedor
5. IGNORA NIFs que aparezcan en pie de página, notas legales o información adicional
6. Para números decimales, usa punto como separador (ej: 123.45)
7. Para fechas, usa formato YYYY-MM-DD (ej: 2024-11-15)
8. Si no encuentras un campo, déjalo vacío ""
9. Para importes, solo el número sin símbolos de moneda
10. Devuelve SOLO el JSON, sin texto adicional ni markdown

EJEMPLOS:

Ejemplo 1 - NIF único:
  Encabezado: "ECOMPUTER S.L. - NIF: B12345678"
  Cliente: "GETNET - NIF: B99999999"
  → proveedor.nif = "B12345678" ✅

Ejemplo 2 - Múltiples NIFs del mismo grupo (Vodafone):
  Encabezado: "Vodafone España S.A.U. - NIF: A80907397"
  Pie: "Vodafone Servicios S.L.U. - NIF: B83788964"
  → proveedor.nif = "A80907397" ✅ (el primero/principal)

Ejemplo 3 - NIF en diferentes formatos:
  "Canon España S.A.U. - CIF: A-28122125"
  → proveedor.nif = "A-28122125" ✅ (incluir guiones si existen)"""

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
            max_tokens=800,
            temperature=0.1  # Baja temperatura para respuestas más determinísticas
        )
        
        # Extraer respuesta
        respuesta_texto = response.choices[0].message.content.strip()
        logger.info(f"📥 Respuesta de GPT-4 Vision: {respuesta_texto[:200]}...")
        
        # Parsear JSON
        # Limpiar posibles markdown code blocks
        if respuesta_texto.startswith('```'):
            respuesta_texto = respuesta_texto.split('```')[1]
            if respuesta_texto.startswith('json'):
                respuesta_texto = respuesta_texto[4:]
            respuesta_texto = respuesta_texto.strip()
        
        datos = json.loads(respuesta_texto)
        
        # Validar estructura
        if 'proveedor' not in datos or 'factura' not in datos:
            logger.error("Respuesta de GPT-4 no tiene la estructura esperada")
            raise ValueError("Estructura de respuesta inválida")
        
        # Limpiar y validar datos
        datos_limpios = {
            'proveedor': {
                'nombre': datos.get('proveedor', {}).get('nombre', '').strip(),
                'nif': datos.get('proveedor', {}).get('nif', '').strip(),
                'direccion': datos.get('proveedor', {}).get('direccion', '').strip(),
                'telefono': datos.get('proveedor', {}).get('telefono', '').strip(),
                'email': datos.get('proveedor', {}).get('email', '').strip(),
            },
            'factura': {
                'numero': datos.get('factura', {}).get('numero', '').strip(),
                'fecha_emision': datos.get('factura', {}).get('fecha_emision', '').strip(),
                'fecha_vencimiento': datos.get('factura', {}).get('fecha_vencimiento', '').strip(),
                'base_imponible': str(datos.get('factura', {}).get('base_imponible', '')).strip(),
                'iva': str(datos.get('factura', {}).get('iva', '')).strip(),
                'total': str(datos.get('factura', {}).get('total', '')).strip(),
                'concepto': datos.get('factura', {}).get('concepto', '').strip(),
            }
        }
        
        logger.info(f"✅ GPT-4 Vision extrajo datos de factura correctamente")
        logger.info(f"   Proveedor: {datos_limpios['proveedor']['nombre']}")
        logger.info(f"   Factura: {datos_limpios['factura']['numero']}")
        logger.info(f"   Total: {datos_limpios['factura']['total']}")
        
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

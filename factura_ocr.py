"""
Módulo para extracción de datos de facturas mediante OCR
Procesa imágenes de facturas PDF/JPG/PNG usando GPT-4 Vision API
"""

import base64
import os
import json
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


def extraer_datos_factura_gpt4(imagen_bytes):
    """
    Extrae datos de factura usando GPT-4 Vision API
    
    Args:
        imagen_bytes: Bytes de la imagen de la factura
        
    Returns:
        dict: Datos estructurados de la factura
    """
    if not OPENAI_DISPONIBLE or not OPENAI_API_KEY:
        raise ValueError("OpenAI API Key no configurada. Configure OPENAI_API_KEY en .env")
    
    try:
        # Convertir imagen a base64
        base64_image = base64.b64encode(imagen_bytes).decode('utf-8')
        
        # Inicializar cliente OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Prompt para extraer datos estructurados de factura
        prompt = """Analiza esta imagen de factura y extrae los siguientes datos.
Devuelve SOLO un objeto JSON válido con estos campos (deja vacíos los que no encuentres):

{
  "proveedor": {
    "nombre": "nombre o razón social del proveedor/emisor",
    "nif": "NIF o CIF del proveedor",
    "direccion": "dirección del proveedor",
    "telefono": "teléfono del proveedor",
    "email": "email del proveedor"
  },
  "factura": {
    "numero": "número de factura (ej: FAC-2024-001, F-123, etc)",
    "fecha_emision": "fecha de emisión en formato YYYY-MM-DD",
    "fecha_vencimiento": "fecha de vencimiento en formato YYYY-MM-DD (si existe)",
    "base_imponible": "base imponible en número decimal (ej: 100.50)",
    "iva": "importe del IVA en número decimal (ej: 21.00)",
    "total": "importe total en número decimal (ej: 121.50)",
    "concepto": "descripción o concepto de la factura"
  }
}

IMPORTANTE:
- Para números decimales, usa punto como separador (ej: 123.45)
- Para fechas, usa formato YYYY-MM-DD (ej: 2024-11-15)
- Si no encuentras un campo, déjalo vacío ""
- Para el número de factura, incluye el formato completo como aparece
- Para importes, solo el número sin símbolos de moneda
- Devuelve SOLO el JSON, sin texto adicional ni markdown."""

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

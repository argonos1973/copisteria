"""
Módulo para extracción de datos de contactos mediante OCR
Procesa imágenes de tarjetas de visita, documentos, etc.
"""

import pytesseract
from PIL import Image
import re
import io
from logger_config import get_logger

logger = get_logger(__name__)


def extraer_texto_imagen(imagen_bytes):
    """
    Extrae texto de una imagen usando Tesseract OCR
    
    Args:
        imagen_bytes: Bytes de la imagen
        
    Returns:
        str: Texto extraído de la imagen
    """
    try:
        # Abrir imagen desde bytes
        imagen = Image.open(io.BytesIO(imagen_bytes))
        
        # Convertir a RGB si es necesario
        if imagen.mode != 'RGB':
            imagen = imagen.convert('RGB')
        
        # Extraer texto con OCR (español y catalán)
        texto = pytesseract.image_to_string(imagen, lang='spa+cat')
        
        logger.info(f"Texto extraído por OCR: {texto[:200]}...")
        return texto
        
    except Exception as e:
        logger.error(f"Error en OCR: {e}", exc_info=True)
        raise


def parsear_datos_contacto(texto):
    """
    Parsea el texto extraído por OCR para identificar datos del contacto
    
    Args:
        texto: Texto extraído por OCR
        
    Returns:
        dict: Diccionario con los datos identificados
    """
    datos = {
        'razon_social': '',
        'nif': '',
        'direccion': '',
        'cp': '',
        'poblacion': '',
        'telefono': '',
        'email': '',
        'nombre_contacto': ''
    }
    
    try:
        lineas = [l.strip() for l in texto.split('\n') if l.strip()]
        
        # Patrones de búsqueda
        patron_nif = r'\b[A-Z]\d{8}|[A-Z]\d{7}[A-Z]|\d{8}[A-Z]\b'
        patron_email = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        patron_telefono = r'\b(?:\+34\s?)?[6789]\d{2}\s?\d{2}\s?\d{2}\s?\d{2}\b'
        patron_cp = r'\b\d{5}\b'
        
        # Buscar NIF/CIF
        for linea in lineas:
            match_nif = re.search(patron_nif, linea.upper().replace(' ', ''))
            if match_nif:
                datos['nif'] = match_nif.group(0)
                break
        
        # Buscar email
        for linea in lineas:
            match_email = re.search(patron_email, linea, re.IGNORECASE)
            if match_email:
                datos['email'] = match_email.group(0).lower()
                break
        
        # Buscar teléfono
        for linea in lineas:
            match_telefono = re.search(patron_telefono, linea.replace('-', '').replace('.', ''))
            if match_telefono:
                telefono = match_telefono.group(0)
                # Limpiar formato
                telefono = re.sub(r'\s+', '', telefono)
                if telefono.startswith('+34'):
                    telefono = telefono[3:]
                datos['telefono'] = telefono
                break
        
        # Buscar código postal
        for linea in lineas:
            match_cp = re.search(patron_cp, linea)
            if match_cp:
                datos['cp'] = match_cp.group(0)
                # La población suele estar en la misma línea después del CP
                resto_linea = linea[match_cp.end():].strip()
                if resto_linea:
                    datos['poblacion'] = resto_linea.split(',')[0].strip()
                break
        
        # Buscar dirección (líneas que contienen palabras clave)
        palabras_direccion = ['calle', 'carrer', 'avinguda', 'avenida', 'plaza', 'plaça', 'c/', 'av.', 'pl.']
        for linea in lineas:
            linea_lower = linea.lower()
            if any(palabra in linea_lower for palabra in palabras_direccion):
                # Limpiar la línea de posibles números de teléfono o emails
                linea_limpia = re.sub(patron_telefono, '', linea)
                linea_limpia = re.sub(patron_email, '', linea_limpia)
                if linea_limpia.strip():
                    datos['direccion'] = linea_limpia.strip()
                    break
        
        # Razón social: primera línea no vacía que no sea email, teléfono o dirección
        for linea in lineas:
            if (linea and 
                not re.search(patron_email, linea) and 
                not re.search(patron_telefono, linea) and
                not re.search(patron_nif, linea.upper()) and
                linea != datos['direccion']):
                datos['razon_social'] = linea
                break
        
        # Nombre de contacto: buscar líneas con "Sr.", "Sra.", nombres comunes
        titulos = ['sr.', 'sra.', 'sr', 'sra', 'd.', 'dña.', 'don', 'doña']
        for linea in lineas:
            linea_lower = linea.lower()
            if any(titulo in linea_lower for titulo in titulos):
                datos['nombre_contacto'] = linea.strip()
                break
        
        logger.info(f"Datos parseados: {datos}")
        return datos
        
    except Exception as e:
        logger.error(f"Error parseando datos: {e}", exc_info=True)
        return datos


def procesar_imagen_contacto(imagen_bytes):
    """
    Procesa una imagen completa: OCR + parseo de datos
    
    Args:
        imagen_bytes: Bytes de la imagen
        
    Returns:
        dict: Datos del contacto extraídos
    """
    try:
        # Extraer texto
        texto = extraer_texto_imagen(imagen_bytes)
        
        # Parsear datos
        datos = parsear_datos_contacto(texto)
        
        # Agregar texto completo para referencia
        datos['texto_completo'] = texto
        
        return datos
        
    except Exception as e:
        logger.error(f"Error procesando imagen: {e}", exc_info=True)
        raise

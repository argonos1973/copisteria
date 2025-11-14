"""
Módulo para extracción de datos de contactos mediante OCR
Procesa imágenes de tarjetas de visita, documentos, etc.
Soporta Tesseract OCR y EasyOCR (deep learning)
"""

import pytesseract
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
import re
import io
import numpy as np
from logger_config import get_logger

logger = get_logger(__name__)

# Intentar importar EasyOCR (opcional, mejor para diseños complejos)
try:
    import easyocr
    EASYOCR_DISPONIBLE = True
    logger.info("EasyOCR disponible - se usará para tarjetas complejas")
except ImportError:
    EASYOCR_DISPONIBLE = False
    logger.info("EasyOCR no disponible - solo se usará Tesseract")

# Cache del reader de EasyOCR (tarda en inicializar)
_easyocr_reader = None


def preprocesar_imagen(imagen):
    """
    Preprocesa la imagen para mejorar la precisión del OCR
    Aplica múltiples técnicas de mejora de imagen
    
    Args:
        imagen: Objeto PIL Image
        
    Returns:
        PIL Image: Imagen preprocesada
    """
    try:
        # Convertir a RGB si es necesario
        if imagen.mode != 'RGB':
            imagen = imagen.convert('RGB')
        
        # Aumentar tamaño significativamente (OCR funciona mejor con imágenes grandes)
        ancho, alto = imagen.size
        if ancho < 2000 or alto < 2000:
            factor = max(2000 / ancho, 2000 / alto)
            nuevo_ancho = int(ancho * factor)
            nuevo_alto = int(alto * factor)
            imagen = imagen.resize((nuevo_ancho, nuevo_alto), Image.Resampling.LANCZOS)
            logger.info(f"Imagen redimensionada a {nuevo_ancho}x{nuevo_alto}")
        
        # Convertir a escala de grises
        imagen_gris = imagen.convert('L')
        
        # Detectar si es fondo oscuro (tarjeta oscura con texto claro)
        # Calcular brillo promedio
        np_imagen = np.array(imagen_gris)
        brillo_promedio = np.mean(np_imagen)
        
        logger.info(f"Brillo promedio de la imagen: {brillo_promedio}")
        
        # Si el brillo promedio es bajo (<128), es fondo oscuro → invertir
        if brillo_promedio < 128:
            logger.info("Detectado fondo oscuro - invirtiendo colores")
            imagen_gris = ImageOps.invert(imagen_gris)
            np_imagen = np.array(imagen_gris)
        
        # Reducir ruido con filtro de mediana (elimina puntos aislados)
        from PIL import ImageFilter
        imagen_sin_ruido = imagen_gris.filter(ImageFilter.MedianFilter(size=3))
        
        # Aumentar contraste agresivamente
        enhancer = ImageEnhance.Contrast(imagen_sin_ruido)
        imagen_contraste = enhancer.enhance(3.0)  # Aumentado de 2.0 a 3.0
        
        # Aumentar brillo si es necesario
        np_contraste = np.array(imagen_contraste)
        if np.mean(np_contraste) < 140:
            enhancer_brillo = ImageEnhance.Brightness(imagen_contraste)
            imagen_contraste = enhancer_brillo.enhance(1.3)
        
        # Aplicar nitidez múltiple
        imagen_nitida = imagen_contraste.filter(ImageFilter.SHARPEN)
        imagen_nitida = imagen_nitida.filter(ImageFilter.SHARPEN)  # Doble nitidez
        
        # Binarización adaptativa usando método de Otsu (mejor que umbral fijo)
        np_nitida = np.array(imagen_nitida)
        
        # Calcular umbral óptimo (método de Otsu simplificado)
        hist, bins = np.histogram(np_nitida.flatten(), 256, [0, 256])
        total = np_nitida.size
        
        sum_total = np.sum(np.arange(256) * hist)
        sum_background = 0
        weight_background = 0
        max_variance = 0
        threshold_otsu = 128
        
        for t in range(256):
            weight_background += hist[t]
            if weight_background == 0:
                continue
            
            weight_foreground = total - weight_background
            if weight_foreground == 0:
                break
            
            sum_background += t * hist[t]
            
            mean_background = sum_background / weight_background
            mean_foreground = (sum_total - sum_background) / weight_foreground
            
            variance = weight_background * weight_foreground * (mean_background - mean_foreground) ** 2
            
            if variance > max_variance:
                max_variance = variance
                threshold_otsu = t
        
        logger.info(f"Umbral Otsu calculado: {threshold_otsu}")
        
        # Aplicar binarización con umbral calculado
        imagen_binaria = imagen_nitida.point(lambda x: 255 if x > threshold_otsu else 0)
        
        # Dilatar ligeramente para conectar letras fragmentadas
        # (útil si el texto está pixelado o tiene gaps)
        from PIL import ImageFilter
        imagen_final = imagen_binaria.filter(ImageFilter.MaxFilter(size=3))
        
        return imagen_final
        
    except Exception as e:
        logger.error(f"Error en preprocesamiento: {e}", exc_info=True)
        # Si falla el preprocesamiento, devolver imagen original en escala de grises
        return imagen.convert('L')


def extraer_texto_imagen(imagen_bytes, debug=False):
    """
    Extrae texto de una imagen usando Tesseract OCR
    Intenta múltiples configuraciones para mejor resultado
    
    Args:
        imagen_bytes: Bytes de la imagen
        debug: Si es True, guarda la imagen procesada para debugging
        
    Returns:
        str: Texto extraído de la imagen
    """
    try:
        # Abrir imagen desde bytes
        imagen = Image.open(io.BytesIO(imagen_bytes))
        
        # Preprocesar imagen para mejorar OCR
        imagen_procesada = preprocesar_imagen(imagen)
        
        # Guardar imagen procesada para debugging si se solicita
        if debug:
            try:
                debug_path = '/tmp/ocr_debug_processed.png'
                imagen_procesada.save(debug_path)
                logger.info(f"Imagen procesada guardada en: {debug_path}")
            except Exception as e:
                logger.warning(f"No se pudo guardar imagen debug: {e}")
        
        # Intentar con diferentes configuraciones de PSM (Page Segmentation Mode)
        # PSM 3: Segmentación automática completa (mejor para tarjetas complejas)
        # PSM 6: Bloque uniforme de texto (mejor para documentos simples)
        # PSM 11: Texto disperso (mejor para tarjetas con diseño complejo)
        
        configs = [
            '--psm 3 --oem 3',   # Segmentación automática completa
            '--psm 6 --oem 3',   # Bloque uniforme
            '--psm 11 --oem 3',  # Texto disperso
        ]
        
        mejor_texto = ""
        max_longitud = 0
        
        for config in configs:
            try:
                texto = pytesseract.image_to_string(
                    imagen_procesada, 
                    lang='spa+cat',
                    config=config
                )
                
                # Quedarse con el texto más largo (generalmente mejor resultado)
                if len(texto.strip()) > max_longitud:
                    max_longitud = len(texto.strip())
                    mejor_texto = texto
                    logger.info(f"Mejor resultado con config: {config}, longitud: {max_longitud}")
                    
            except Exception as e:
                logger.warning(f"Error con config {config}: {e}")
                continue
        
        if not mejor_texto:
            # Si todos fallaron, intentar con configuración básica
            mejor_texto = pytesseract.image_to_string(
                imagen_procesada, 
                lang='spa+cat'
            )
        
        logger.info(f"Texto extraído por OCR (primeros 200 chars): {mejor_texto[:200]}...")
        return mejor_texto
        
    except Exception as e:
        logger.error(f"Error en OCR: {e}", exc_info=True)
        raise


def extraer_texto_easyocr(imagen_bytes):
    """
    Extrae texto usando EasyOCR (deep learning)
    Funciona mejor con diseños complejos y tarjetas
    
    Args:
        imagen_bytes: Bytes de la imagen
        
    Returns:
        str: Texto extraído de la imagen
    """
    global _easyocr_reader
    
    if not EASYOCR_DISPONIBLE:
        raise ImportError("EasyOCR no está instalado")
    
    try:
        # Inicializar reader si no existe (se cachea)
        if _easyocr_reader is None:
            logger.info("Inicializando EasyOCR reader (esto puede tardar unos segundos)...")
            _easyocr_reader = easyocr.Reader(['es', 'en'], gpu=False)  # Español e inglés
            logger.info("EasyOCR reader inicializado")
        
        # Convertir bytes a array numpy
        imagen = Image.open(io.BytesIO(imagen_bytes))
        imagen_array = np.array(imagen)
        
        # Extraer texto
        logger.info("Extrayendo texto con EasyOCR...")
        resultados = _easyocr_reader.readtext(imagen_array)
        
        # Convertir resultados a texto
        # Formato: [(bbox, texto, confianza), ...]
        lineas = []
        for (bbox, texto, confianza) in resultados:
            if confianza > 0.1:  # Filtrar detecciones de baja confianza
                lineas.append(texto)
                logger.debug(f"EasyOCR: '{texto}' (confianza: {confianza:.2f})")
        
        texto_completo = '\n'.join(lineas)
        logger.info(f"EasyOCR extrajo {len(lineas)} líneas de texto")
        
        return texto_completo
        
    except Exception as e:
        logger.error(f"Error en EasyOCR: {e}", exc_info=True)
        raise


def extraer_texto_con_mejor_metodo(imagen_bytes, debug=False):
    """
    Intenta extraer texto usando el mejor método disponible
    Prueba primero EasyOCR (mejor para diseños complejos) y luego Tesseract
    
    Args:
        imagen_bytes: Bytes de la imagen
        debug: Si es True, guarda la imagen procesada
        
    Returns:
        str: Texto extraído de la imagen
    """
    try:
        # Intentar primero con EasyOCR si está disponible
        if EASYOCR_DISPONIBLE:
            try:
                logger.info("Intentando extracción con EasyOCR...")
                texto_easyocr = extraer_texto_easyocr(imagen_bytes)
                
                if texto_easyocr and len(texto_easyocr.strip()) > 10:
                    logger.info(f"EasyOCR exitoso - {len(texto_easyocr)} caracteres extraídos")
                    return texto_easyocr
                else:
                    logger.warning("EasyOCR no extrajo suficiente texto, intentando con Tesseract...")
            except Exception as e:
                logger.warning(f"EasyOCR falló: {e}, intentando con Tesseract...")
        
        # Fallback a Tesseract
        logger.info("Usando Tesseract OCR...")
        return extraer_texto_imagen(imagen_bytes, debug=debug)
        
    except Exception as e:
        logger.error(f"Error en extracción de texto: {e}", exc_info=True)
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
        
        # Patrones de búsqueda mejorados
        patron_nif = r'\b[A-Z]\d{8}|[A-Z]\d{7}[A-Z]|\d{8}[A-Z]\b'
        patron_email = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        # Patrón de teléfono más flexible (con espacios, puntos, guiones)
        patron_telefono = r'\b(?:\+34\s?)?[6789]\d{2}[\s.-]?\d{2,3}[\s.-]?\d{2,3}[\s.-]?\d{2,3}\b'
        patron_cp = r'\b\d{5}\b'
        # Patrón para móvil con formato "M.: 690 924 069" o "T. 93 342 99 20"
        patron_movil = r'(?:M\.|T\.|Tel\.|Móvil|Movil|Telf)[\s:\.]+(\+?[\d\s]+)'
        # Patrón para web
        patron_web = r'www\.[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
        
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
        
        # Buscar teléfono (primero con prefijos M., T., etc.)
        for linea in lineas:
            match_movil = re.search(patron_movil, linea, re.IGNORECASE)
            if match_movil:
                telefono = match_movil.group(1)
                # Limpiar formato (quitar espacios, puntos, guiones)
                telefono = re.sub(r'[\s.-]', '', telefono)
                if telefono.startswith('+34'):
                    telefono = telefono[3:]
                # Validar que tenga 9 dígitos
                if len(telefono) == 9 and telefono.isdigit():
                    datos['telefono'] = telefono
                    break
        
        # Si no encontró con prefijo, buscar patrón general
        if not datos['telefono']:
            for linea in lineas:
                match_telefono = re.search(patron_telefono, linea)
                if match_telefono:
                    telefono = match_telefono.group(0)
                    # Limpiar formato
                    telefono = re.sub(r'[\s.-]', '', telefono)
                    if telefono.startswith('+34'):
                        telefono = telefono[3:]
                    # Validar que tenga 9 dígitos
                    if len(telefono) == 9 and telefono.isdigit():
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
        
        # Razón social: buscar líneas largas al inicio (típicamente nombre de empresa)
        # Ignorar líneas muy cortas, emails, teléfonos, webs, direcciones
        for linea in lineas[:5]:  # Buscar en las primeras 5 líneas
            if (len(linea) > 3 and 
                not re.search(patron_email, linea, re.IGNORECASE) and 
                not re.search(patron_telefono, linea) and
                not re.search(patron_movil, linea, re.IGNORECASE) and
                not re.search(patron_web, linea, re.IGNORECASE) and
                not re.search(patron_nif, linea.upper().replace(' ', '')) and
                not re.search(patron_cp, linea) and
                linea != datos['direccion'] and
                not linea.lower().startswith(('tel', 'telf', 'móvil', 'movil', 'email', 'm.', 't.'))):
                datos['razon_social'] = linea.strip()
                break
        
        # Nombre de contacto: buscar líneas con nombres propios o títulos
        # Típicamente después de la razón social
        titulos = ['sr.', 'sra.', 'sr', 'sra', 'd.', 'dña.', 'don', 'doña', 'director', 'gerente', 'presidente']
        for i, linea in enumerate(lineas):
            linea_lower = linea.lower()
            # Buscar títulos
            if any(titulo in linea_lower for titulo in titulos):
                datos['nombre_contacto'] = linea.strip()
                break
            # O buscar líneas que parezcan nombres (2-4 palabras, cada una capitalizada)
            palabras = linea.split()
            if (2 <= len(palabras) <= 4 and 
                all(p[0].isupper() for p in palabras if len(p) > 1) and
                not re.search(patron_email, linea) and
                not re.search(patron_telefono, linea) and
                linea != datos['razon_social']):
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
    Usa EasyOCR si está disponible (mejor para diseños complejos)
    o Tesseract como fallback
    
    Args:
        imagen_bytes: Bytes de la imagen
        
    Returns:
        dict: Datos del contacto extraídos
    """
    try:
        # Extraer texto con el mejor método disponible
        texto = extraer_texto_con_mejor_metodo(imagen_bytes)
        
        # Parsear datos
        datos = parsear_datos_contacto(texto)
        
        # Agregar texto completo para referencia
        datos['texto_completo'] = texto
        
        return datos
        
    except Exception as e:
        logger.error(f"Error procesando imagen: {e}", exc_info=True)
        raise

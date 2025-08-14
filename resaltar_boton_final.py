#!/var/www/html/venv/bin/python

import os
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright

# Configurar logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Selector específico para el botón de descarga según la información proporcionada
SELECTORES_BOTON = [
    "button[aria-label*='Descargar' i]",
    "button:has-text('Descargar')",
    "button:has(san-icon.flame-icon-download)",
    "san-chip#downloadPill",
    "button:has(slot[name='text-chip']:has-text('Descargar'))",
    ".flame-icon-download",
    "[aria-label*='Descargar' i]",
    "button span[class*='flame-icon-download']",
    "*[aria-label*='descargar' i]",
    "*[class*='download' i]",
    "*[id*='download' i]",
    "button"
]

def resaltar_boton_descargar(page):
    """Buscar y resaltar el botón de descarga"""
    # Probar diferentes selectores para encontrar el botón
    for selector in SELECTORES_BOTON:
        try:
            logging.info(f"Buscando botón con selector: {selector}")
            # Esperar a que el elemento esté disponible
            page.wait_for_selector(selector, timeout=10000)
            botones = page.query_selector_all(selector)
            
            for i, boton in enumerate(botones):
                if boton and boton.is_visible():
                    # Verificar si el botón contiene texto o atributos relacionados con "descargar"
                    texto_boton = boton.inner_text().lower() if boton.inner_text() else ""
                    aria_label = boton.get_attribute("aria-label") or ""
                    
                    # Verificar si es el botón de descarga
                    if "descargar" in texto_boton or "descargar" in aria_label.lower():
                        logging.info(f"Botón de descarga encontrado con selector: {selector} (botón #{i})")
                        
                        # Resaltar el botón
                        page.evaluate("""
                            boton => {
                                // Añadir atributo para identificarlo
                                boton.setAttribute('data-resaltado', 'true');
                                
                                // Aplicar estilos de resaltado
                                boton.style.transition = 'all 0.3s ease';
                                boton.style.outline = '4px solid #ff0000';
                                boton.style.boxShadow = '0 0 0 6px rgba(255, 0, 0, 0.3), 0 0 20px 10px rgba(255, 0, 0, 0.5)';
                                boton.style.backgroundColor = boton.style.backgroundColor ? 
                                    boton.style.backgroundColor : '#ffeeee';
                                
                                // Hacer scroll para que sea visible
                                boton.scrollIntoView({behavior: 'smooth', block: 'center'});
                                
                                return true;
                            }
                        """, boton)
                        
                        logging.info(f"Botón de descarga #{i} resaltado exitosamente")
                        return boton
                    
        except Exception as e:
            logging.warning(f"Error al buscar/resaltar con selector {selector}: {e}")
            continue
    
    logging.warning("No se encontró el botón de descarga con ninguno de los selectores")
    return None

def guardar_evidencia_html(page, directorio_evidencias="/home/sami/logs"):
    """Guardar una evidencia HTML de la página con el botón resaltado"""
    try:
        # Crear directorio si no existe
        os.makedirs(directorio_evidencias, exist_ok=True)
        
        # Generar nombre de archivo con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"evidencia_boton_descarga_{timestamp}.html"
        ruta_completa = os.path.join(directorio_evidencias, nombre_archivo)
        
        # Obtener el contenido HTML de la página
        html_content = page.content()
        
        # Guardar el archivo
        with open(ruta_completa, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logging.info(f"Evidencia HTML guardada en: {ruta_completa}")
        return ruta_completa
        
    except Exception as e:
        logging.error(f"Error al guardar evidencia HTML: {e}")
        return None

def main():
    """Función principal"""
    logging.info("Iniciando script para resaltar botón de descarga")
    
    # Verificar que el directorio de evidencias exista
    directorio_evidencias = "/home/sami/logs"
    os.makedirs(directorio_evidencias, exist_ok=True)
    
    with sync_playwright() as p:
        try:
            # Lanzar el navegador en modo visible para observación
            browser = p.chromium.launch(
                headless=False,  # Ejecutar en modo visible
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu'
                ]
            )
            
            # Crear contexto con viewport fijo
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            # Crear página
            page = context.new_page()
            
            # Navegar a la página correcta donde está el botón de descarga
            logging.info("Navegando a la página de cuentas del banco Santander")
            page.goto("https://particulares.bancosantander.es/oneweb/accounts", timeout=30000)
            
            # Esperar a que la página cargue
            page.wait_for_timeout(10000)
            
            # Buscar y resaltar el botón de descarga
            boton_resaltado = resaltar_boton_descargar(page)
            
            if boton_resaltado:
                # Guardar evidencia HTML
                ruta_evidencia = guardar_evidencia_html(page, directorio_evidencias)
                
                if ruta_evidencia:
                    logging.info("Proceso completado exitosamente")
                    print(f"\nBotón de descarga resaltado y evidencia guardada en: {ruta_evidencia}")
                    print("Puedes abrir este archivo en un navegador para verificar el resaltado.")
                else:
                    logging.error("No se pudo guardar la evidencia HTML")
            else:
                logging.error("No se pudo encontrar ni resaltar el botón de descarga")
                
                # Guardar evidencia aunque no se haya encontrado el botón
                ruta_evidencia = guardar_evidencia_html(page, directorio_evidencias)
                if ruta_evidencia:
                    print(f"\nEvidencia guardada (sin botón resaltado) en: {ruta_evidencia}")
            
            # Mantener el navegador abierto por 30 segundos para observación
            print("\nManteniendo el navegador abierto por 30 segundos para observación...")
            page.wait_for_timeout(30000)
            
        except Exception as e:
            logging.error(f"Error durante la ejecución: {e}")
            import traceback
            logging.error(traceback.format_exc())
            
        finally:
            try:
                context.close()
            except:
                pass
            try:
                browser.close()
            except:
                pass
            
    logging.info("Script finalizado")

if __name__ == "__main__":
    main()

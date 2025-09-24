#!/var/www/html/venv/bin/python

import os
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright

# Configurar logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def guardar_evidencia_html(page, nombre_base, directorio_evidencias="/home/sami/logs"):
    """Guardar una evidencia HTML de la página"""
    try:
        # Crear directorio si no existe
        os.makedirs(directorio_evidencias, exist_ok=True)
        
        # Generar nombre de archivo con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"{nombre_base}_{timestamp}.html"
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
    logging.info("Iniciando análisis de la página de cuentas")
    
    # Verificar que el directorio de evidencias exista
    directorio_evidencias = "/home/sami/logs"
    os.makedirs(directorio_evidencias, exist_ok=True)
    
    with sync_playwright() as p:
        try:
            # Lanzar el navegador en modo headless
            browser = p.chromium.launch(
                headless=True,  # Ejecutar en modo headless
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process'
                ]
            )
            
            # Crear contexto con viewport fijo
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            # Crear página
            page = context.new_page()
            
            # Navegar directamente a la página de cuentas
            logging.info("Navegando directamente a la página de cuentas")
            response = page.goto("https://particulares.bancosantander.es/oneweb/accounts", timeout=30000)
            
            # Imprimir información de la respuesta
            if response:
                logging.info(f"Status code: {response.status}")
                logging.info(f"URL final: {response.url}")
            
            # Esperar un poco para que la página cargue
            page.wait_for_timeout(5000)
            
            # Guardar evidencia de la página de cuentas
            ruta_evidencia = guardar_evidencia_html(page, "pagina_cuentas_analisis", directorio_evidencias)
            
            if ruta_evidencia:
                logging.info("Evidencia guardada exitosamente")
                print(f"\nEvidencia guardada en: {ruta_evidencia}")
                print("Puedes abrir este archivo en un navegador para verificar el contenido.")
            else:
                logging.error("No se pudo guardar la evidencia HTML")
                
            # Imprimir el título de la página
            try:
                title = page.title()
                logging.info(f"Título de la página: {title}")
                print(f"\nTítulo de la página: {title}")
            except Exception as e:
                logging.error(f"Error al obtener el título: {e}")
                
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

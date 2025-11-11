#!/usr/bin/env python3
"""
Script de prueba para verificar el nuevo selector del botón Descargar
Ejecutar manualmente en el servidor para debug
"""

from playwright.sync_api import sync_playwright
import logging
import time

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_download_button():
    """Prueba específica para el botón de descarga con el nuevo formato"""
    
    with sync_playwright() as p:
        # Lanzar navegador visible para debugging
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        logger.info("🔍 Navegando al banco...")
        # NOTA: Necesitarás hacer login manualmente primero
        page.goto("https://particulares.bancosantander.es/login/")
        
        # Esperar login manual
        input("✋ Por favor, haz login manualmente y navega hasta los movimientos de la cuenta. Luego presiona ENTER...")
        
        logger.info("🔍 Buscando botón de descarga...")
        
        # Lista de selectores a probar (nuevo formato primero)
        selectores = [
            # Nuevo formato con slot (Web Components)
            ("span:has(slot:text('Descargar'))", "SLOT en SPAN"),
            ("*:has(slot:text('Descargar'))", "SLOT genérico"),
            ("slot:text('Descargar')", "SLOT directo"),
            # Buscar el elemento padre del span
            ("span.label:has(slot)", "SPAN con clase label"),
            # Formatos anteriores por si acaso
            ("button:has-text('Descargar')", "BUTTON con texto"),
            ("[role='button']:has-text('Descargar')", "Elemento con role button"),
        ]
        
        encontrado = False
        for selector, descripcion in selectores:
            try:
                elemento = page.locator(selector).first
                if elemento and elemento.count() > 0 and elemento.is_visible():
                    logger.info(f"✅ ENCONTRADO con: {descripcion} ({selector})")
                    
                    # Obtener información del elemento
                    try:
                        # Intentar obtener el elemento padre
                        parent = elemento.locator("..")
                        parent_tag = parent.evaluate("el => el.tagName")
                        parent_class = parent.evaluate("el => el.className")
                        logger.info(f"   Padre: <{parent_tag} class='{parent_class}'>")
                    except:
                        pass
                    
                    # Hacer screenshot del elemento
                    try:
                        elemento.screenshot(path=f"/tmp/boton_descarga_{int(time.time())}.png")
                        logger.info(f"   Screenshot guardado en /tmp/")
                    except:
                        pass
                    
                    # Intentar hacer clic
                    respuesta = input("   ¿Intentar hacer clic? (s/n): ")
                    if respuesta.lower() == 's':
                        try:
                            # Intentar clic en el padre primero
                            parent = elemento.locator("..")
                            if parent.count() > 0:
                                logger.info("   Haciendo clic en elemento padre...")
                                parent.click()
                            else:
                                logger.info("   Haciendo clic en elemento...")
                                elemento.click()
                            
                            # Esperar y verificar si se abrió modal
                            page.wait_for_timeout(2000)
                            modal = page.locator(":is([role=dialog], san-modal, .modal)")
                            if modal.count() > 0:
                                logger.info("   ✅ ¡Modal abierto!")
                            else:
                                logger.info("   ⚠️ No se detectó modal")
                        except Exception as e:
                            logger.error(f"   Error al hacer clic: {e}")
                    
                    encontrado = True
                    break
            except Exception as e:
                logger.debug(f"❌ No encontrado con {descripcion}: {e}")
        
        if not encontrado:
            logger.warning("⚠️ No se encontró el botón con ningún selector")
            
            # Intentar buscar cualquier elemento con texto "Descargar"
            logger.info("🔍 Buscando cualquier elemento con texto 'Descargar'...")
            try:
                todos = page.locator("*:text('Descargar')").all()
                logger.info(f"   Encontrados {len(todos)} elementos con texto 'Descargar'")
                for i, elem in enumerate(todos[:5]):  # Mostrar máximo 5
                    tag = elem.evaluate("el => el.tagName")
                    clase = elem.evaluate("el => el.className")
                    logger.info(f"   {i+1}. <{tag} class='{clase}'>")
            except Exception as e:
                logger.error(f"Error buscando elementos: {e}")
        
        input("Presiona ENTER para cerrar el navegador...")
        browser.close()

if __name__ == "__main__":
    test_download_button()

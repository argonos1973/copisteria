#!/var/www/html/venv/bin/python

import os
import sys
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

# Configurar logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def gestionar_cookies(page):
    """Gestionar el banner de cookies"""
    try:
        logging.info("Intentando aceptar/ocultar banner de cookies...")
        # 1) Esperar a que el banner de cookies esté presente
        try:
            page.wait_for_selector("#onetrust-banner-sdk, .onetrust-banner, .cookie-banner, .cookies-banner", timeout=10000)
            logging.info("Banner de cookies detectado")
            
            # 2) Intentar hacer clic en el botón de aceptar
            try:
                page.click("#onetrust-accept-btn-handler, .onetrust-accept-btn, .cookie-accept-button, .accept-cookies-button", timeout=5000)
                logging.info("Banner de cookies aceptado")
            except:
                logging.warning("No se pudo hacer clic en el botón de aceptar cookies")
                
            # 3) Forzar ocultación del banner si sigue visible
            try:
                page.evaluate("""
                    () => {
                        const banners = document.querySelectorAll('#onetrust-banner-sdk, .onetrust-banner, .cookie-banner, .cookies-banner');
                        banners.forEach(banner => {
                            banner.style.display = 'none';
                            banner.style.visibility = 'hidden';
                        });
                        
                        // Ocultar overlay oscuro si existe
                        const overlays = document.querySelectorAll('#onetrust-consent-sdk .onetrust-pc-dark-filter, .cookie-overlay, .cookies-overlay');
                        overlays.forEach(overlay => {
                            overlay.style.display = 'none';
                            overlay.style.visibility = 'hidden';
                        });
                    }
                """)
                logging.info("Banner de cookies ocultado forzadamente")
            except Exception as e:
                logging.warning(f"No se pudo ocultar forzadamente el banner de cookies: {e}")
                
        except Exception as e:
            logging.info("Banner de cookies no detectado o ya gestionado")
            
    except Exception as e:
        logging.warning(f"No se pudo gestionar el banner de cookies: {e}")
    
    # Esperar a estado de red estable tras gestionar cookies
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except:
        pass

def resaltar_boton_descarga(page):
    """Buscar y resaltar el botón de descarga"""
    try:
        # Selectores para el botón de descarga
        selectores_descarga = [
            'button[aria-label*="Descargar" i]',
            'a[aria-label*="Descargar" i]',
            '[aria-label*="Exportar" i]',
            '[title*="Descargar" i]',
            '[title*="Exportar" i]',
            'button:has(san-icon[iconcontent*="download" i])',
            'a:has(san-icon[iconcontent*="download" i])',
            'san-icon[iconcontent*="download" i]',
            'button:has(san-icon[iconcontent*="arrow-down" i])',
            'a:has(san-icon[iconcontent*="arrow-down" i])',
            'san-icon[iconcontent*="arrow-down" i]',
            'em.c-sanicon__download',
            '[data-dtname*="download" i]',
            '[data-dtname*="export" i]',
            '[data-testid*="export" i]',
            '[data-icon*="download" i]',
            '[class*="download" i]',
            '[class*="export" i]',
            '[class*="descarg" i]',
            'button[aria-label*="descargar" i]',
            'a[aria-label*="descargar" i]',
            '.flame-icon-download',
            'san-chip#downloadPill'
        ]
        
        # Contenedores de acciones
        contenedores_acciones = [
            '.buttons', '.actions', '.toolbar', '.filters', '.panel', '.wrapper', 
            '[role="toolbar"]', '.san-actions', '.san-toolbar', '.table-actions', 
            '.actions-bar', '.filters__actions', '.san-section__actions', '.san-card__actions'
        ]
        
        # Evaluar en el contexto de la página para encontrar el botón
        res = page.evaluate(
            r"""
            () => {
              const pageRoot = document.querySelector('main') || document.body;
              const actionContainers = Array.from(pageRoot.querySelectorAll('.buttons, .actions, .toolbar, .filters, .panel, .wrapper, [role="toolbar"], .san-actions, .san-toolbar, .table-actions, .actions-bar, .filters__actions, .san-section__actions, .san-card__actions'))
                .filter(el => !el.closest('.header__buttons, header, nav, san-sidebar-menu, #personalAreaMenu, #mailboxMenu, #helpMenu, .menu, [role="menu"]'));
              const dlSelParts = [
                'a[aria-label*="Descargar" i]','button[aria-label*="Descargar" i]','[aria-label*="Exportar" i]','[title*="Descargar" i]','[title*="Exportar" i]',
                'button:has(san-icon[iconcontent*="download" i])','a:has(san-icon[iconcontent*="download" i])','san-icon[iconcontent*="download" i]',
                'button:has(san-icon[iconcontent*="arrow-down" i])','a:has(san-icon[iconcontent*="arrow-down" i])','san-icon[iconcontent*="arrow-down" i]',
                'em.c-sanicon__download',
                '[data-dtname*="download" i]','[data-dtname*="export" i]','[data-testid*="export" i]','[data-icon*="download" i]',
                '[class*="download" i]','[class*="export" i]','[class*="descarg" i]',
                'button[aria-label*="descargar" i]','a[aria-label*="descargar" i]',
                '.flame-icon-download',
                'san-chip#downloadPill'
              ];
              const collectSel = dlSelParts.join(',');
              const all = Array.from(pageRoot.querySelectorAll(collectSel)).filter(el => {
                if (!el) return false;
                const anc = el.closest('header, nav, san-sidebar-menu, #personalAreaMenu, #mailboxMenu, #helpMenu, .menu, [role="menu"]');
                if (anc) return false;
                const hrefEl = (el.tagName && el.tagName.toLowerCase()==='a') ? el : el.closest('a');
                const href = hrefEl && hrefEl.getAttribute && (hrefEl.getAttribute('href')||'');
                if (href && /asuntos-clientes|buzon|ayuda|gestiones/i.test(href)) return false;
                const st = getComputedStyle(el);
                if (st.display==='none' || st.visibility==='hidden' || parseFloat(st.opacity||'1')===0) return false;
                return true;
              });
              const cont = actionContainers.find(c => c.querySelector(collectSel)) || pageRoot;
              let cand = all.find(el => cont.contains(el)) || all[0] || null;
              if (!cand) return { mark: null };
              if (cand && cand.tagName && cand.tagName.toLowerCase()==='san-icon') {
                const wrap = cand.closest('a,button,[role=button]');
                if (wrap) cand = wrap;
              }
              const mark = 'cascade_'+Date.now();
              try { cand.setAttribute('data-cascade-click', mark); } catch(e) {}
              try { cand.scrollIntoView({block:'center', inline:'center'}); } catch(e) {}
              return { mark };
            }
            """
        )
        
        if isinstance(res, dict) and res.get('mark'):
            mk = res.get('mark')
            # Aplicar realce visual persistente (sin hacer clic)
            try:
                page.evaluate(
                    """
                    sel => {
                      const t = document.querySelector(sel);
                      if(!t) return false;
                      try { t.scrollIntoView({block:'center', inline:'center'}); } catch(e){}
                      // Estilos persistentes hasta el fin del script
                      try { t.style.setProperty('transition','box-shadow .2s ease, outline .2s ease','important'); } catch(e){}
                      try { t.style.setProperty('outline','3px solid #1e90ff','important'); } catch(e){}
                      try { t.style.setProperty('box-shadow','0 0 0 4px rgba(30,144,255,.25), 0 0 12px 2px rgba(30,144,255,.6)','important'); } catch(e){}
                      return true;
                    }
                    """,
                    f"[data-cascade-click='{mk}']"
                )
                
                logging.info("Botón de descarga resaltado exitosamente")
                return True
                
            except Exception as e:
                logging.error(f"Error al resaltar el botón de descarga: {e}")
                return False
        else:
            logging.warning("No se encontró el botón de descarga")
            return False
            
    except Exception as e:
        logging.error(f"Error al buscar el botón de descarga: {e}")
        return False

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
    logging.info("Iniciando script para resaltar botón de descarga del Banco Santander")
    
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
            
            # Navegar a la página de login
            logging.info("Navegando a la página de login del Banco Santander")
            page.goto("https://particulares.bancosantander.es/login/", timeout=30000)
            
            # Esperar a que la página cargue
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(3000)
            
            # Gestionar banner de cookies
            gestionar_cookies(page)
            
            # Aquí normalmente se haría el login, pero para este script simplificado
            # vamos directamente a la página de cuentas
            logging.info("Navegando a la página de cuentas")
            page.goto("https://particulares.bancosantander.es/oneweb/accounts", timeout=30000)
            
            # Esperar a que la página cargue
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(5000)
            
            # Gestionar banner de cookies nuevamente si aparece
            gestionar_cookies(page)
            
            # Buscar y resaltar el botón de descarga
            boton_resaltado = resaltar_boton_descarga(page)
            
            # Guardar evidencia HTML
            ruta_evidencia = guardar_evidencia_html(page, directorio_evidencias)
            
            if boton_resaltado and ruta_evidencia:
                logging.info("Botón de descarga resaltado y evidencia guardada exitosamente")
                print(f"\nBotón de descarga resaltado y evidencia guardada en: {ruta_evidencia}")
                print("Puedes abrir este archivo en un navegador para verificar el resaltado.")
            elif ruta_evidencia:
                logging.warning("No se encontró el botón de descarga, pero se guardó la evidencia")
                print(f"\nEvidencia guardada (sin botón resaltado) en: {ruta_evidencia}")
            else:
                logging.error("No se pudo guardar la evidencia HTML")
            
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

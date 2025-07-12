#!/var/www/html/venv/bin/python

import logging
import os
import random
import sys
import time
from datetime import datetime

# Registrar inicio del script
print("=== scrapeo.py iniciado ===")

# Verificar dependencias
try:
    from playwright.sync_api import sync_playwright
    print("✓ Playwright importado correctamente")
except ImportError:
    print("✗ ERROR: Playwright no está instalado. Intentando instalar...")
    try:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
        from playwright.sync_api import sync_playwright
        print("✓ Playwright instalado correctamente")
    except Exception as e:
        print(f"✗ ERROR: No se pudo instalar Playwright: {e}")
        sys.exit(1)

# Crear directorio para logs si no existe
log_dir = '/var/www/html/logs'
os.makedirs(log_dir, exist_ok=True)

# Configurar logging
try:
    logging.basicConfig(
        filename=f'{log_dir}/scrapeo.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    with open(f"{log_dir}/scrapeo_last_run.txt", "w") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Iniciando script\n")
    logging.info("=== scrapeo.py iniciado ===")
except Exception as e:
    print(f"Error al configurar logging: {e}")
    # Fallback a stdout si no podemos escribir en archivo
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

from db_utils import get_db_connection

MAX_LOGIN_TIME = 60  # segundos
nif = "44007535W"
clave = "19731898"

fecha_inicio = datetime.now().replace(day=1).strftime("%d/%m/%Y")
#fecha_inicio = "01/01/2025"
fecha_hoy = datetime.now().strftime("%d/%m/%Y")

# Guardar mes y año del filtro para comparación posterior
mes_filtro = int(fecha_inicio[3:5])
anio_filtro = int(fecha_inicio[6:10])
mes_anio = f"{str(mes_filtro).zfill(2)}/{anio_filtro}"

with sync_playwright() as p:
    import pathlib
    downloads_dir = "/tmp/descargas_bancarias"
    pathlib.Path(downloads_dir).mkdir(parents=True, exist_ok=True)
    try:
        # Configuración para evitar detección anti-bot más avanzada
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu',
            '--window-size=1920,1080',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            '--disable-extensions',
            '--disable-features=IsolateOrigins,site-per-process',
            '--enable-features=NetworkService',
            '--ignore-certificate-errors',
            '--disable-web-security',
            '--allow-running-insecure-content',
            '--disable-webgl'
        ]
        
        # Usar modo headless ya que estamos en un servidor sin interfaz gráfica
        # Si sigue fallando, una opción sería usar xvfb-run para simular un entorno gráfico
        browser = p.chromium.launch(
            headless=True,
            args=browser_args
        )
        
        logging.info("Navegador iniciado en modo headless con configuración anti-detección avanzada")
    except Exception as e:
        logging.error(f"Error al iniciar el navegador: {e}")
        sys.exit(1)
        
    # Configuración del contexto para simular usuario real con más detalles
    context = browser.new_context(
        accept_downloads=True,
        viewport={'width': 1920, 'height': 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        locale="es-ES",
        timezone_id="Europe/Madrid",
        permissions=['geolocation', 'notifications'],
        extra_http_headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Accept-Language": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1"
        }
    )
    
    # Inyectar JavaScript para evadir detección de bots (overriding navigator properties)
    context.add_init_script('''
    Object.defineProperty(navigator, 'webdriver', { get: () => false });    
    Object.defineProperty(navigator, 'languages', { get: () => ['es-ES', 'es', 'en-US', 'en'] });    
    Object.defineProperty(navigator, 'plugins', { get: () => Array(3).fill().map((_, i) => i) });    
    window.chrome = { runtime: {} };
    ''')
    
    # Crear página con configuración avanzada
    page = context.new_page()
    
    # Configuración avanzada de Playwright
    page.set_default_timeout(30000) # 30 segundos por defecto para todas las operaciones
    
    # Agregar simulación de movimientos de ratón aleatorios para parecer más humano
    page.evaluate('''
    () => {
      const events = ['click', 'touchstart', 'mouseover', 'mousemove'];
      events.forEach(event => {
        document.addEventListener(event, () => {}, true);
      });
    }
    ''')

    logging.info("→ Abriendo página...")
    try:
        # Simular comportamiento humano con intervalos aleatorios
        logging.info("Navegando a página de inicio del banco...")
        page.goto("https://bancosantander.es")
        time.sleep(random.uniform(1.0, 3.0))
        
        # Navegar primero a la página principal y luego al login
        logging.info("Buscando enlace a la página de login")
        try:
            page.click("a[href*='login']", timeout=5000)
            logging.info("Haciendo clic en enlace de login")
        except Exception:
            logging.info("No se encontró enlace directo a login, navegando directamente")
            page.goto("https://particulares.bancosantander.es/login/")
        
        login_start = time.time()
        logging.info("Página de login cargada")
        
        # Tomar captura de pantalla para diagnóstico
        screenshot_path = f"{os.path.dirname(os.path.abspath(__file__))}/logs/pantalla_inicial_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        page.screenshot(path=screenshot_path)
        logging.info(f"Captura de pantalla guardada en {screenshot_path}")
        
        # Guardar HTML para análisis
        html_content = page.content()
        html_path = f"{os.path.dirname(os.path.abspath(__file__))}/logs/pagina_inicial_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logging.info(f"Contenido HTML guardado en {html_path}")
        
        # Intentar detectar redirecciones o cambios en la URL
        current_url = page.url
        logging.info(f"URL actual: {current_url}")
        
    except Exception as e:
        logging.error(f"Error al cargar la página: {e}")
        sys.exit(1)

    # Aceptar cookies - intentar varias estrategias
    cookie_buttons = [
        "#onetrust-accept-btn-handler",
        "button:has-text('Aceptar')",
        "button:has-text('Aceptar todas')",
        "button:has-text('Aceptar cookies')",
        ".cookie-accept-button",
        "#cookie-accept",
        "#accept-cookies"
    ]
    
    for cookie_selector in cookie_buttons:
        try:
            logging.info(f"Intentando aceptar cookies con selector: {cookie_selector}")
            if page.is_visible(cookie_selector):
                page.click(cookie_selector)
                logging.info(f"Cookies aceptadas correctamente con {cookie_selector}")
                time.sleep(random.uniform(0.8, 2.0))
                break
        except Exception as e:
            logging.warning(f"No se pudieron aceptar cookies con {cookie_selector}: {e}")
    
    # Esperar un poco para que la página se cargue completamente después de aceptar cookies
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(5000)
    
    # Tomar captura después de aceptar cookies
    screenshot_path = f"{os.path.dirname(os.path.abspath(__file__))}/logs/pantalla_cookies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    page.screenshot(path=screenshot_path)
    logging.info(f"Captura después de cookies guardada en {screenshot_path}")
    
    # Guardar HTML actualizado después de aceptar cookies
    html_path = f"{os.path.dirname(os.path.abspath(__file__))}/logs/html_despues_cookies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(page.content())
    
    if time.time() - login_start > MAX_LOGIN_TIME:
        logging.error("Demasiado tiempo intentando hacer login. Reiniciando script...")
        python = sys.executable
        os.execl(python, python, *sys.argv)
    
    # Buscar todos los campos de entrada visibles para analizar
    logging.info("Analizando todos los campos de entrada visibles en la página")
    try:
        # Obtener lista de todos los inputs en la página
        all_inputs = page.evaluate('''
            () => {
                const inputs = Array.from(document.querySelectorAll('input'));
                return inputs.map(input => {
                    return {
                        id: input.id || 'sin-id',
                        type: input.type || 'sin-tipo',
                        name: input.name || 'sin-nombre',
                        placeholder: input.placeholder || 'sin-placeholder',
                        class: input.className || 'sin-clase',
                        visible: input.offsetParent !== null
                    };
                });
            }
        ''')
        
        logging.info(f"Se encontraron {len(all_inputs)} campos de entrada")
        for i, inp in enumerate(all_inputs):
            logging.info(f"Input {i}: id={inp['id']}, type={inp['type']}, name={inp['name']}, visible={inp['visible']}")
    except Exception as e:
        logging.error(f"Error al analizar campos de entrada: {e}")
    
    # Rellenar NIF - probar diferentes selectores posibles
    # Ampliamos la lista de selectores posibles basados en la experiencia y posibles cambios en la web
    input_selectors = [
        "#inputDocuNumber",
        "input[name='documento']", 
        ".documento-input",
        "input[placeholder*='DNI']", 
        "input[placeholder*='documento']",
        "input[placeholder*='N.I.F']",
        "input[placeholder*='Documento']",
        "input[type='text']:visible",
        "#docNumber",
        "input.login-document",
        "input[name*='doc']",
        "input[name*='nif']",
        "input[name*='dni']",
        "input[id*='doc']",
        "input[id*='dni']",
        "input[id*='nif']",
        "input.form-control:visible"
    ]
                      
    selector_encontrado = False
    
    for selector in input_selectors:
        try:
            logging.info(f"Intentando encontrar el selector: {selector}")
            # Usamos una estrategia diferente: primero verificamos si existe y es visible
            exists = page.evaluate(f'''
                () => {{
                    const element = document.querySelector("{selector}");
                    if (element) {{
                        const style = window.getComputedStyle(element);
                        const isVisible = style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
                        return isVisible;
                    }}
                    return false;
                }}
            ''')
            
            if exists:
                logging.info(f"Selector encontrado y visible: {selector}")
                # Tomar captura para ver qué elemento estamos detectando
                screenshot_path = f"{os.path.dirname(os.path.abspath(__file__))}/logs/selector_encontrado_{selector.replace('#', '').replace('[', '_').replace(']', '_').replace('*', '_').replace('=', '_').replace(':', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                page.screenshot(path=screenshot_path)
                
                # Simular comportamiento humano con tiempo de escritura
                page.click(selector)
                time.sleep(random.uniform(0.5, 1.2))
                
                # Escribir el NIF letra por letra con pequeños retrasos aleatorios
                for char in nif:
                    page.keyboard.type(char)
                    time.sleep(random.uniform(0.05, 0.2))
                
                selector_encontrado = True
                break
        except Exception as e:
            logging.warning(f"Error al interactuar con selector {selector}: {e}")
    
    if not selector_encontrado:
        logging.error("No se encontró ningún campo para introducir el NIF")
        # Tomar captura para ver el problema
        screenshot_path = f"{os.path.dirname(os.path.abspath(__file__))}/logs/error_no_selector_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        page.screenshot(path=screenshot_path)
        # Guardar HTML para analizar la estructura
        html_path = f"{os.path.dirname(os.path.abspath(__file__))}/logs/error_html_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(page.content())
        sys.exit(1)
        
    if time.time() - login_start > MAX_LOGIN_TIME:
        print("Demasiado tiempo intentando hacer login. Reiniciando script...")
        python = sys.executable
        os.execl(python, python, *sys.argv)

    # Esperar campos clave y rellenar solo los visibles
    page.wait_for_selector("#inputPW0", timeout=10000)
    for i in range(8):
        sel = f"#inputPW{i}"
        el = page.query_selector(sel)
        if el and el.is_visible() and el.is_enabled():
            page.click(sel)
            page.type(sel, clave[i])
        if time.time() - login_start > MAX_LOGIN_TIME:
            print("Demasiado tiempo intentando hacer login. Reiniciando script...")
            python = sys.executable
            os.execl(python, python, *sys.argv)

    # Pulsar botón Entrar
    page.locator("button:has-text('Entrar')").click()
    if time.time() - login_start > MAX_LOGIN_TIME:
        print("Demasiado tiempo intentando hacer login. Reiniciando script...")
        python = sys.executable
        os.execl(python, python, *sys.argv)

    # Cerrar ventana emergente si aparece
    try:
        page.locator("#mcp-cross-close").click(timeout=5000)
    except:
        pass

    # Ir a la página de movimientos
    page.wait_for_timeout(3000)
    page.goto("https://particulares.bancosantander.es/nhb/#/cuentas/detalle")

    # Intentar cerrar modal de filtros si aparece
    try:
        cerrar_btn = page.locator(".c-sanicon__close")
        if cerrar_btn.count() > 0 and cerrar_btn.first.is_visible():
            cerrar_btn.first.click()
            print("Modal de filtros cerrado")
    except Exception as e:
        print("No se pudo cerrar el modal de filtros (puede que no esté visible):", e)

    # Intentar con selectores alternativos para los campos de fecha
    fecha_inicio_selectores = ["#filterComponent-input2", "input[placeholder*='Desde']", "input[name*='fecha_inicio']", "input[name*='desde']", "input[id*='fecha_desde']", "input[type='date']:nth-child(1)"]
    fecha_fin_selectores = ["#filterComponent-input3", "input[placeholder*='Hasta']", "input[name*='fecha_fin']", "input[name*='hasta']", "input[id*='fecha_hasta']", "input[type='date']:nth-child(2)"]
    
    fecha_inicio_ok = False
    fecha_fin_ok = False
    
    for selector in fecha_inicio_selectores:
        try:
            print(f"Intentando encontrar campo fecha inicio con selector: {selector}")
            if page.is_visible(selector):
                page.fill(selector, fecha_inicio)
                print(f"Campo fecha inicio rellenado con selector: {selector}")
                fecha_inicio_ok = True
                break
        except Exception as e:
            print(f"Error con selector {selector}: {e}")
    
    for selector in fecha_fin_selectores:
        try:
            print(f"Intentando encontrar campo fecha fin con selector: {selector}")
            if page.is_visible(selector):
                page.fill(selector, fecha_hoy)
                print(f"Campo fecha fin rellenado con selector: {selector}")
                fecha_fin_ok = True
                break
        except Exception as e:
            print(f"Error con selector {selector}: {e}")
    
    if not (fecha_inicio_ok and fecha_fin_ok):
        print("No se pudieron encontrar o rellenar los campos de fecha")
        # Continuar de todos modos, puede que la página ya muestre los movimientos sin filtros
    
    # Intentar hacer click en el botón buscar/aplicar filtro
    buscar_selectores = [
        'button:has-text("BUSCAR")', 
        'button:has-text("Buscar")', 
        'button:has-text("Aplicar")',
        'button:has-text("Filtrar")',
        'button.buscar', 
        'button.filtrar', 
        'button.aplicar',
        'input[type="submit"]'
    ]
    
    for selector in buscar_selectores:
        try:
            print(f"Intentando hacer click en botón con selector: {selector}")
            if page.is_visible(selector):
                page.click(selector)
                print(f"Click realizado en botón con selector: {selector}")
                break
        except Exception as e:
            print(f"Error al hacer click en botón {selector}: {e}")
    
    print("Esperando resultados...")
    page.wait_for_timeout(5000)

    # Hacer click en el icono de descarga
    print("Buscando icono de descarga...")
    try:
        download_icon = page.locator('.c-sanicon__download').first
        if download_icon.is_visible():
            print("Clickando en el icono de descarga...")
            download_icon.click()
            print("Click realizado en el icono de descarga.")
            print("Esperando 5 segundos tras el click de descarga...")
            page.wait_for_timeout(5000)
            # Hacer click en el botón Exportar Excel
            print("Buscando botón 'Exportar Excel'...")
            try:
                exportar_excel_btn = page.locator('#exportModal-a1').first
                if exportar_excel_btn.is_visible():
                    print("Clickando en el botón 'Exportar Excel'...")
                    exportar_excel_btn.click()
                    print("Click realizado en 'Exportar Excel'. Esperando 5 segundos...")
                    page.wait_for_timeout(5000)
                    # Hacer click en el enlace 'Descargar EXCEL'
                    print("Buscando enlace 'Descargar EXCEL'...")
                    try:
                        descargar_excel_link = page.locator('#blobButtons-a10').first
                        if descargar_excel_link.is_visible():
                            print("Clickando en el enlace 'Descargar EXCEL'...")
                            print("Preparando para capturar la descarga...")
                            with page.expect_download() as download_info:
                                descargar_excel_link.click()
                            download = download_info.value
                            import pathlib
                            downloads_dir = "/tmp/descargas_bancarias"
                            pathlib.Path(downloads_dir).mkdir(parents=True, exist_ok=True)
                            destino = f"{downloads_dir}/descarga.xlsx"
                            download.save_as(destino)
                            print(f"Archivo XLS guardado en: {destino}")
                            print("Descarga completada.")

                            # Leer el Excel sin encabezado para inspeccionar la estructura real
                            import os
                            import sqlite3

                            import pandas as pd
                            try:
                                ext = os.path.splitext(destino)[1].lower()
                                if ext == ".xls":
                                    df = pd.read_excel(destino, header=7, engine="xlrd")
                                else:
                                    df = pd.read_excel(destino, header=7)
                                print(f"Columnas detectadas en el Excel: {list(df.columns)}")
                                print("Primeras filas del Excel:")
                                print(df.head())
                                columnas = ['FECHA OPERACIÓN', 'FECHA VALOR', 'CONCEPTO', 'IMPORTE EUR', 'SALDO']
                                for col in columnas:
                                    if col not in df.columns:
                                        raise Exception(f"No se encuentra la columna requerida: {col}")
                                # Renombrar las columnas al formato de la tabla gastos
                                df = df.rename(columns={
                                    'FECHA OPERACIÓN': 'fecha_operacion',
                                    'FECHA VALOR': 'fecha_valor',
                                    'CONCEPTO': 'concepto',
                                    'IMPORTE EUR': 'importe_eur',
                                    'SALDO': 'saldo'
                                })
                                # Seleccionar solo las columnas necesarias para la tabla
                                default_saldo = None
                                if 'saldo' not in df.columns:
                                    df['saldo'] = default_saldo
                                # Seleccionar columnas base primero
                                df = df[['fecha_operacion', 'fecha_valor', 'concepto', 'importe_eur', 'saldo']]

                                # Borrar registros del mes y año en curso antes de insertar
                                ahora = datetime.now()
                                mes_actual = ahora.month
                                anio_actual = ahora.year
                                conn = get_db_connection()
                                cursor = conn.cursor()
                                # Borrado robusto para fechas en formato DD/MM/YYYY
                                patron = f"%/{mes_actual:02d}/{anio_actual}"
                                cursor.execute("DELETE FROM gastos WHERE fecha_operacion LIKE ?", (patron,))
                                conn.commit()
                                print(f"Registros del mes {mes_actual:02d}/{anio_actual} eliminados antes de la inserción.")
                                # Añadir columna TS (en mayúsculas) con el timestamp más reciente posible y ejercicio (año en curso)
                                timestamp_reciente = datetime.now().isoformat()
                                print(f"Asignando timestamp de actualización: {timestamp_reciente}")
                                # Usar TS en mayúsculas para coincidir con el nombre en la base de datos
                                df['TS'] = timestamp_reciente
                                df['ejercicio'] = anio_actual
                                # Ahora sí, selecciona todas las columnas para la inserción
                                df = df[['fecha_operacion', 'fecha_valor', 'concepto', 'importe_eur', 'saldo', 'ejercicio', 'TS']]

                                try:
                                    # Insertar los datos en la tabla 'gastos'
                                    df.to_sql('gastos', conn, if_exists='append', index=False)
                                    print("Gastos insertados correctamente en la base de datos aleph70.db (tabla gastos)")
                                except Exception as e:
                                    print(f"Error al insertar los gastos en la base de datos: {e}")
                                finally:
                                    conn.close()
                            except Exception as e:
                                print(f"Error al procesar el Excel: {e}")
                    except Exception as e:
                        print(f"Error al buscar o hacer click en el enlace 'Descargar EXCEL': {e}")
            except Exception as e:
                print(f"Error al buscar o hacer click en el botón 'Exportar Excel': {e}")
    except Exception as e:
        print(f"Error al buscar o hacer click en el icono de descarga: {e}")
        print("No se encontró el icono de descarga visible.")

    browser.close()

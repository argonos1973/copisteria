import csv
import os
import sqlite3
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from format_utils import format_currency_es_two, format_total_es_two, format_number_es_max5, format_percentage

from flask import (Flask, Response, jsonify, request, send_file,
                   stream_with_context, session, make_response, send_from_directory)
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
import logging
from logger_config import get_logger

# Sistema Multiempresa
from multiempresa_config import SESSION_CONFIG, inicializar_bd_usuarios
from auth_routes import auth_bp
from empresas_api import empresas_bp
from admin_routes import admin_bp
from plantillas_routes import plantillas_bp
from usuario_api import usuario_bp
from avatares_api import avatares_bp
from auth_middleware import login_required, require_admin, require_permission

logger = get_logger('aleph70.app')

try:
    from weasyprint import CSS, HTML
except ImportError:
    logger.warning("WeasyPrint no está instalado. La generación de PDF no estará disponible.")

import datetime
import json
import subprocess
import time
from datetime import datetime

# Importación de módulos locales
import contactos
import factura
try:
    import generar_pdf
except Exception as e:
    logger.error(f"[AVISO] Error importando generar_pdf: {e}. Se deshabilita la generación de PDF.")
    generar_pdf = None
import productos
import productos_franjas_utils
import proforma
import presupuesto
import tickets
import facturas_proveedores
import verifactu
import conciliacion

# Configuración externa para habilitar o deshabilitar VeriFactu
try:
    from config_loader import get as get_config
    VERIFACTU_HABILITADO = bool(get_config("verifactu_enabled", True))
except Exception as _e:
    logger.info(f"[AVISO] No se pudo cargar config.json: {_e}. Suponemos VeriFactu HABILITADO")
    VERIFACTU_HABILITADO = True
# Nota: Los módulos recibos y usuarios no existen, se han comentado
# import recibos
# import usuarios
# Fin de importaciones
from constantes import *
from dashboard_routes import dashboard_bp
from db_utils import (formatear_numero_documento, get_db_connection,
                      redondear_importe)
from factura import obtener_factura_abierta
from gastos import gastos_bp
from estadisticas_gastos_routes import estadisticas_gastos_bp
from proforma import obtener_proforma_abierta
from verifactu.core import generar_datos_verifactu_para_ticket

# Versión de la aplicación
APP_VERSION = '1.2.8'

def _to_decimal(val, default='0'):
    """Convierte un valor a Decimal de forma segura"""
    try:
        return Decimal(str(val).replace(',', '.'))
    except Exception:
        return Decimal(default)

application = Flask(__name__, 
                   template_folder='templates',
                   static_folder='static')
app = application
CORS(app, supports_credentials=True, origins=['https://*.trycloudflare.com', 'http://localhost:*', 'http://192.168.*:*'])

# Configurar para proxy reverso (Cloudflare, nginx, etc)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Configurar sesiones - CONFIGURACIÓN PARA PROXY CLOUDFLARE
app.config['SECRET_KEY'] = 'clave-super-secreta-cambiar-en-produccion-12345'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Lax funciona mejor que None
app.config['SESSION_COOKIE_PATH'] = '/'
app.config['SESSION_COOKIE_SECURE'] = False  # False porque el backend recibe HTTP
app.config['SESSION_COOKIE_NAME'] = 'aleph70_session'
app.config['SESSION_COOKIE_DOMAIN'] = None

# Configuración especial para que funcione con Cloudflare
app.config['SESSION_COOKIE_SECURE'] = False
app.config['PREFERRED_URL_SCHEME'] = 'https'

# NO usar Flask-Session, usar sesiones nativas de Flask que funcionan mejor con proxy
# Session(app) - DESACTIVADO

# Middleware para manejar sesiones con proxy
@app.before_request
def before_request():
    # Headers para permitir cookies cross-origin (preflight)
    if request.method == "OPTIONS":
        response = make_response()
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Session-Data'
        origin = request.headers.get('Origin')
        if origin and 'trycloudflare.com' in origin:
            response.headers['Access-Control-Allow-Origin'] = origin
        return response
    
    # WORKAROUND: Si no hay sesión pero hay header X-Session-Data, restaurar sesión
    if not session.get('user_id') and request.headers.get('X-Session-Data'):
        try:
            import json
            session_data = json.loads(request.headers.get('X-Session-Data'))
            # Restaurar datos básicos de sesión desde el header
            if session_data.get('username'):
                session['username'] = session_data['username']
                session['empresa_codigo'] = session_data.get('empresa', 'copisteria')
                session['empresa_db'] = '/var/www/html/db/caca/caca.db'  # BD por defecto
                session['rol'] = session_data.get('rol', 'usuario')
                session.modified = True
        except:
            pass

@app.after_request
def after_request(response):
    # Detectar si viene de Cloudflare
    origin = request.headers.get('Origin')
    forwarded_proto = request.headers.get('X-Forwarded-Proto')
    
    if origin and 'trycloudflare.com' in origin:
        # Headers CORS
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        
        # Manejar cookies para proxy HTTPS->HTTP
        if 'Set-Cookie' in response.headers:
            cookies = response.headers.getlist('Set-Cookie')
            response.headers.pop('Set-Cookie')
            
            for cookie in cookies:
                # Para Cloudflare necesitamos Secure=true y SameSite=None
                # aunque el backend reciba HTTP
                if forwarded_proto == 'https':
                    # Asegurar que tiene Secure
                    if '; Secure' not in cookie:
                        cookie += '; Secure'
                    # Cambiar SameSite a None
                    import re
                    cookie = re.sub(r'; SameSite=[^;]+', '', cookie)
                    cookie += '; SameSite=None'
                
                response.headers.add('Set-Cookie', cookie)
    
    return response

# Inicializar BD de usuarios al arrancar
inicializar_bd_usuarios()

# Registrar blueprints
app.register_blueprint(auth_bp)  # Sistema de autenticación
app.register_blueprint(empresas_bp)  # Gestión de empresas
app.register_blueprint(admin_bp)  # Sistema de administración
app.register_blueprint(plantillas_bp)  # Plantillas personalizadas
app.register_blueprint(usuario_bp)  # Gestión de perfil de usuario
app.register_blueprint(avatares_bp)  # Gestión de avatares predefinidos
app.register_blueprint(dashboard_bp)
app.register_blueprint(gastos_bp, url_prefix='')
app.register_blueprint(estadisticas_gastos_bp, url_prefix='')
app.register_blueprint(conciliacion.conciliacion_bp, url_prefix='')

# Registrar integración con Plaid
try:
    from plaid_routes import plaid_bp
    app.register_blueprint(plaid_bp)  # Integración bancaria con Plaid
except ImportError:
    pass  # Plaid es opcional

# Registrar rutas públicas y de registro (landing page)
try:
    from public_routes import public_bp
    from public.register_api import register_bp
    app.register_blueprint(public_bp)  # Landing page y sitio público
    app.register_blueprint(register_bp)  # API de registro de nuevos usuarios
except ImportError:
    pass  # Las rutas públicas son opcionales

# Configurar CORS
CORS(app, resources={
    r"/*": {"origins": "*"}  # Permitir cualquier ruta
})

# Configurar logging de aplicación solo a stdout (evitar escritura en disco)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('app_actions')

# Producción
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False') == 'True'
app.config['DATABASE'] = DB_NAME

# Asegurar recursos de BD necesarios al iniciar
try:
    productos.ensure_tabla_descuentos_bandas()
except Exception as e:
    logger.info(f"[AVISO] No se pudo asegurar la tabla de franjas de descuento: {e}")

# ================== CONFIG.JSON ================== #
@app.route('/config.json', methods=['GET'])
def servir_config_json():
    """Sirve el archivo config.json"""
    try:
        ruta = os.path.join(BASE_DIR, 'config.json')
        if not os.path.exists(ruta):
            return jsonify({'verifactu_enabled': False}), 200
        return send_file(ruta, mimetype='application/json')
    except Exception as e:
        return jsonify({'verifactu_enabled': False}), 200

# ================== VERSION ================== #
@app.route('/api/version', methods=['GET'])
def obtener_version():
    """Retorna la versión de la aplicación"""
    return jsonify({
        'version': APP_VERSION,
        'nombre': 'Aleph70 - Sistema de Gestión'
    }), 200

# ================== HTML: imprimir ticket ================== #
@login_required
@app.route('/api/imprimir-ticket.html', methods=['GET'])
def servir_imprimir_ticket_html():
    """Sirve la página de impresión del ticket con el logo de la empresa"""
    try:
        ruta = os.path.join(BASE_DIR, 'frontend', 'imprimir-ticket.html')
        if not os.path.exists(ruta):
            return Response('imprimir-ticket.html no encontrado', status=404)
        
        # Leer el contenido del HTML
        with open(ruta, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Obtener logo de la empresa desde la sesión
        empresa_logo = session.get('empresa_logo', 'default_header.png')
        logo_header = f'/static/logos/{empresa_logo}'
        
        # Reemplazar el logo hardcoded con el logo de la empresa
        html_content = html_content.replace('src="/static/img/logo.png"', f'src="{logo_header}"')
        
        return Response(html_content, mimetype='text/html')
    except Exception as e:
        return Response(f'Error sirviendo imprimir-ticket.html: {e}', status=500)

@app.route('/api/productos/aplicar_franjas', methods=['POST'])
def api_aplicar_franjas_todos():
    try:
        # Permitir parámetros por query o body JSON
        args = request.get_json(silent=True) or {}
        ancho = request.args.get('ancho', args.get('ancho', 10))
        max_unidades = request.args.get('max_unidades', args.get('max_unidades', 500))
        descuento_max = request.args.get('descuento_max', args.get('descuento_max', 60))
        try:
            ancho = int(ancho)
        except Exception:
            ancho = 10
        try:
            max_unidades = int(max_unidades)
        except Exception:
            max_unidades = 500
        try:
            descuento_max = float(descuento_max)
        except Exception:
            descuento_max = 60.0

        resultado = productos.aplicar_franjas_a_todos(ancho=ancho, max_unidades=max_unidades, descuento_max=descuento_max)
        status = 200 if resultado.get('success') else 400
        try:
            logger.info(f"[API] aplicar_franjas todos ancho={ancho} max_unidades={max_unidades} descuento_max={descuento_max} -> {resultado}")
        except Exception:
            pass
        return jsonify(resultado), status
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ================== DEBUG: esquema de la tabla productos ================== #
@app.route('/api/debug/schema_productos', methods=['GET'])
def debug_schema_productos():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'No se pudo abrir la base de datos'}), 500
        cur = conn.cursor()
        # Buscar tabla productos
        cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name='productos'")
        row = cur.fetchone()
        exists = bool(row)
        create_sql = row['sql'] if row and 'sql' in row.keys() else (row[1] if row else None)
        # PRAGMA table_info
        table_info = []
        if exists:
            cur.execute('PRAGMA table_info(productos)')
            table_info = [tuple(r) for r in cur.fetchall()]
        # Conteo/Max id
        count_max = None
        if exists:
            try:
                cur.execute('SELECT COUNT(*) as c, MAX(id) as m FROM productos')
                r = cur.fetchone()
                count_max = {'count': (r['c'] if 'c' in r.keys() else r[0]), 'max_id': (r['m'] if 'm' in r.keys() else r[1])}
            except Exception:
                count_max = None
        return jsonify({
            'exists': exists,
            'create_sql': create_sql,
            'table_info': table_info,
            'count_max': count_max
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

def format_date(date_value):
    """Función auxiliar para formatear fechas en formato DD/MM/AAAA"""
    if date_value is None:
        return None
    if isinstance(date_value, str):
        try:
            # Intentar convertir la cadena a datetime para asegurar formato correcto
            from datetime import datetime
            date_obj = datetime.strptime(date_value, '%Y-%m-%d')
            return date_obj.strftime('%d/%m/%Y')
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            return date_value
    return date_value.strftime('%d/%m/%Y')

@app.route('/api/exportar', methods=['GET'])
def exportar():
    # Obtener parámetros de la consulta
    ejercicio = request.args.get('ejercicio')
    trimestre = request.args.get('trimestre')

    # Validación de parámetros
    if not ejercicio or not ejercicio.isdigit():
        return jsonify({'error': 'El parámetro "ejercicio" es obligatorio y debe ser un número.'}), 400

    # Mapa de trimestres con meses en dos dígitos
    trimestre_map = {
        '1': ('01', '03'),
        '2': ('04', '06'),
        '3': ('07', '09'),
        '4': ('10', '12')
    }

    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'No se pudo establecer conexión con la base de datos.'}), 500

        with conn:
            cursor = conn.cursor()

            # ================ 1) CONSULTA TICKETS =====================
            query_tickets = """
                SELECT
                    fecha,
                    numero,
                    importe_bruto,
                    importe_impuestos,
                    importe_cobrado,
                    total
                FROM tickets
                WHERE strftime('%Y', fecha) = ?
                AND estado = 'C'
            """
            params_tickets = [ejercicio]

            if trimestre in trimestre_map:
                inicio_mes, fin_mes = trimestre_map[trimestre]
                query_tickets += " AND strftime('%m', fecha) BETWEEN ? AND ?"
                params_tickets.extend([inicio_mes, fin_mes])
            elif trimestre and trimestre.lower() != 'todos':
                return jsonify({'error': 'Trimestre inválido. Debe ser 1, 2, 3, 4 o "todos".'}), 400

            cursor.execute(query_tickets, tuple(params_tickets))
            resultados_tickets = cursor.fetchall()

            # ================ 2) CONSULTA FACTURAS =====================
            query_facturas = """
                SELECT
                    f.fecha,
                    f.numero,
                    c.identificador AS nif,
                    c.razonSocial,
                    f.importe_bruto,
                    f.importe_impuestos,
                    f.importe_cobrado,
                    f.total
                FROM factura f
                INNER JOIN contactos c ON f.idContacto = c.idContacto
                WHERE strftime('%Y', f.fecha) = ?
            """
            params_facturas = [ejercicio]

            if trimestre in trimestre_map:
                inicio_mes, fin_mes = trimestre_map[trimestre]
                query_facturas += " AND strftime('%m', f.fecha) BETWEEN ? AND ?"
                params_facturas.extend([inicio_mes, fin_mes])
            elif trimestre and trimestre.lower() != 'todos':
                return jsonify({'error': 'Trimestre inválido. Debe ser 1, 2, 3, 4 o "todos".'}), 400

            cursor.execute(query_facturas, tuple(params_facturas))
            resultados_facturas = cursor.fetchall()

            # Verificar datos
            if not resultados_tickets and not resultados_facturas:
                return jsonify({
                    'mensaje': 'No se encontraron tickets ni facturas con los filtros proporcionados.'
                }), 404

            # ================ 3) UNIFICAR DATOS =====================
            columnas_csv = [
                "fecha",
                "numero",
                "nif",
                "razonSocial",
                "importe_bruto",
                "importe_impuestos",
                "importe_cobrado",
                "total"
            ]

            filas_unificadas = []

            # Procesar tickets
            for t in resultados_tickets:
                filas_unificadas.append({
                    "fecha": t["fecha"],
                    "numero": t["numero"],
                    "nif": "",
                    "razonSocial": "",
                    "importe_bruto": t["importe_bruto"],
                    "importe_impuestos": t["importe_impuestos"],
                    "importe_cobrado": t["importe_cobrado"],
                    "total": t["total"]
                })

            # Procesar facturas
            for f in resultados_facturas:
                filas_unificadas.append({
                    "fecha": f["fecha"],
                    "numero": f["numero"],
                    "nif": f["nif"],
                    "razonSocial": f["razonSocial"],
                    "importe_bruto": f["importe_bruto"],
                    "importe_impuestos": f["importe_impuestos"],
                    "importe_cobrado": f["importe_cobrado"],
                    "total": f["total"]
                })

            # ================ 4) GENERAR CSV =====================
            # Formatear nombre del archivo
            trimestre_nombre = trimestre if trimestre else "todos"
            if trimestre in trimestre_map:
                inicio_mes, fin_mes = trimestre_map[trimestre]
                trimestre_nombre = f"{inicio_mes}-{fin_mes}"

            nombre_archivo = f'UNICO_{ejercicio}_TRIMESTRE_{trimestre_nombre}.csv'
            ruta_archivo = os.path.join(BASE_DIR, 'exports', nombre_archivo)
            os.makedirs(os.path.dirname(ruta_archivo), exist_ok=True)

            # Escribir CSV
            with open(ruta_archivo, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, delimiter=';')
                writer.writerow(columnas_csv)
                
                for fila in filas_unificadas:
                    row = [
                        datetime.strptime(fila["fecha"], '%Y-%m-%d').strftime('%d/%m/%Y') if fila["fecha"] else "",
                        fila["numero"] or "",
                        fila["nif"] or "",
                        fila["razonSocial"] or "",
                        f"{float(fila['importe_bruto'] or 0):.2f}".replace('.', ','),
                        f"{float(fila['importe_impuestos'] or 0):.2f}".replace('.', ','),
                        f"{float(fila['importe_cobrado'] or 0):.2f}".replace('.', ','),
                        f"{float(fila['total'] or 0):.2f}".replace('.', ',')
                    ]
                    writer.writerow(row)

            # ================ 5) ENVIAR ARCHIVO =====================
            return send_file(
                ruta_archivo,
                mimetype='text/csv',
                as_attachment=True,
                download_name=nombre_archivo
            )

    except sqlite3.Error as e:
        return jsonify({'error': f'Error de base de datos: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Error inesperado: {str(e)}'}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# ================== API: Franjas de descuento por producto ================== #
@app.route('/api/productos/<int:producto_id>/franjas_descuento', methods=['GET'])
@app.route('/productos/<int:producto_id>/franjas_descuento', methods=['GET'])
def api_get_franjas_descuento_producto(producto_id):
    try:
        franjas = productos.obtener_franjas_descuento_por_producto(producto_id)
        try:
            logger.info(f"[API] GET franjas_descuento producto_id={producto_id}, total_franjas={len(franjas)}")
        except Exception:
            pass
        return jsonify({'producto_id': producto_id, 'franjas': franjas})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/productos/<int:producto_id>/franjas_descuento', methods=['POST', 'PUT'])
@app.route('/productos/<int:producto_id>/franjas_descuento', methods=['POST', 'PUT'])
def api_set_franjas_descuento_producto(producto_id):
    try:
        body = request.get_json() or {}
        try:
            body_size = len(body) if isinstance(body, list) else (len(body.get('franjas', [])) if isinstance(body, dict) else 0)
            logger.info(f"[API] SET franjas_descuento producto_id={producto_id}, recibido_tipo={'list' if isinstance(body, list) else 'dict'}, elementos={body_size}")
        except Exception:
            pass
        # Aceptar tanto {franjas:[...]} como lista directa
        if isinstance(body, list):
            franjas = body
        else:
            franjas = body.get('franjas', [])
        if not isinstance(franjas, list):
            return jsonify({'error': 'Formato inválido: se espera lista de franjas'}), 400
        productos.reemplazar_franjas_descuento_producto(producto_id, franjas)
        try:
            logger.info(f"[API] OK guardadas franjas_descuento producto_id={producto_id}, total_franjas={len(franjas)}")
        except Exception:
            pass
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# ================== API: Configuración de franjas automáticas ================== #
@app.route('/api/productos/<int:producto_id>/franjas_config', methods=['GET'])
def api_get_franjas_config_producto(producto_id):
    """Obtiene la configuración de franjas automáticas de un producto"""
    try:
        config = productos_franjas_utils.obtener_configuracion_franjas_producto(producto_id)
        if config is None:
            return jsonify({'error': 'Producto no encontrado'}), 404
        return jsonify({'producto_id': producto_id, 'config': config})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/productos/<int:producto_id>/franjas_config', methods=['POST', 'PUT'])
def api_set_franjas_config_producto(producto_id):
    """Actualiza la configuración de franjas automáticas de un producto"""
    try:
        config = request.get_json() or {}
        productos_franjas_utils.actualizar_configuracion_franjas_producto(producto_id, config)
        return jsonify({'success': True, 'mensaje': 'Configuración actualizada correctamente'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/productos/<int:producto_id>/generar_franjas_automaticas', methods=['POST'])
def api_generar_franjas_automaticas(producto_id):
    """Genera franjas automáticas basadas en la configuración del producto"""
    try:
        # Obtener configuración actual
        config = productos_franjas_utils.obtener_configuracion_franjas_producto(producto_id)
        if config is None:
            return jsonify({'error': 'Producto no encontrado'}), 404
        
        # Generar franjas automáticas
        franjas = productos_franjas_utils.generar_franjas_automaticas(producto_id, config)
        
        # Reemplazar franjas existentes
        productos.reemplazar_franjas_descuento_producto(producto_id, franjas)
        
        return jsonify({
            'success': True, 
            'mensaje': f'Se generaron {len(franjas)} franjas automáticamente',
            'franjas': franjas
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


 

@login_required
@app.route('/tickets/paginado', methods=['GET'])
def tickets_paginado_route():
    return tickets.tickets_paginado()

@login_required
@app.route('/api/tickets/paginado', methods=['GET'])
def api_tickets_paginado():
    return tickets.tickets_paginado()

# ===== Alias con prefijo /api para compatibilidad con el frontend (contactos) =====
@app.route('/api/contactos/paginado', methods=['GET'])
def api_contactos_paginado():
    return contactos_paginado()

@app.route('/contactos/paginado', methods=['GET'])
def contactos_paginado():
    try:
        # Parámetros de filtros
        razon_social = request.args.get('razonSocial', '')
        nif = request.args.get('nif', '')

        # Parámetros de paginación/orden
        page = request.args.get('page', 1)
        page_size = request.args.get('page_size', 10)
        sort = request.args.get('sort', 'razonsocial')
        order = request.args.get('order', 'ASC')

        filtros = {
            'razonSocial': razon_social,
            'nif': nif
        }

        resultado = contactos.obtener_contactos_paginados(
            filtros=filtros,
            page=page,
            page_size=page_size,
            sort=sort,
            order=order
        )
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@login_required
@app.route('/api/facturas/paginado', methods=['GET'])
@login_required
def api_facturas_paginado():
    return facturas_paginado()


@app.route('/facturas/paginado', methods=['GET'])
@login_required
def facturas_paginado():
    try:
        # Filtros de consulta
        fecha_inicio = request.args.get('fecha_inicio', '')
        fecha_fin = request.args.get('fecha_fin', '')
        estado = request.args.get('estado', '')
        numero = request.args.get('numero', '')
        contacto = request.args.get('contacto', '')
        identificador = request.args.get('identificador', '')
        concepto = request.args.get('concepto', '')

        # Parámetros de paginación/orden
        page = request.args.get('page', 1)
        page_size = request.args.get('page_size', 10)
        sort = request.args.get('sort', 'fecha')
        order = request.args.get('order', 'DESC')

        filtros = {
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'estado': estado,
            'numero': numero,
            'contacto': contacto,
            'identificador': identificador,
            'concepto': concepto
        }

        resultado = factura.obtener_facturas_paginadas(
            filtros=filtros,
            page=page,
            page_size=page_size,
            sort=sort,
            order=order
        )
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/contactos', methods=['GET'])
def listar_contactos():
    try:
        return jsonify(contactos.obtener_contactos())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/contactos/buscar', methods=['GET'])
def filtrar_contactos():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener parámetros de búsqueda
        razon_social = request.args.get('razonSocial', '')
        nif = request.args.get('nif', '')

        # Construir la consulta SQL base
        sql = '''
            SELECT 
                c.idContacto,
                c.razonsocial,
                c.identificador,
                c.mail,
                c.telf1,
                c.telf2,
                c.direccion,
                c.localidad,
                c.cp,
                c.provincia,
                c.tipo,
                c.dir3_oficina,
                c.dir3_organo,
                c.dir3_unidad,
                c.face_presentacion,
                c.idContacto as id,
                (
                    SELECT p.numero 
                    FROM proforma p 
                    WHERE p.idcontacto = c.idContacto 
                    AND p.estado = 'A'
                    ORDER BY p.fecha DESC, p.id DESC
                    LIMIT 1
                ) as numero_proforma_abierta
            FROM contactos c
            WHERE 1=1
                AND COALESCE(TRIM(c.identificador), '') <> ''
        '''
        params = []

        # Añadir condiciones según los parámetros
        if razon_social:
            sql += ' AND LOWER(c.razonsocial) LIKE LOWER(?)'
            params.append(f'%{razon_social}%')
        if nif:
            sql += ' AND LOWER(c.identificador) LIKE LOWER(?)'
            params.append(f'%{nif}%')

        # Ordenar por razón social y limitar a 20 resultados
        sql += ' ORDER BY c.razonsocial ASC LIMIT 20'

        # Ejecutar la consulta
        cursor.execute(sql, params)
        resultados = cursor.fetchall()

        # Convertir los resultados a una lista de diccionarios
        contactos_list = [dict(row) for row in resultados]

        return jsonify(contactos_list)

    except Exception as e:
        logger.error(f"Error en filtrar_contactos: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/api/contactos/search', methods=['GET'])
def search_contactos():
    """Endpoint para búsqueda de contactos por razón social"""
    query = request.args.get('query', '').strip()
    sort = request.args.get('sort', 'razonsocial')
    order = request.args.get('order', 'ASC')
    
    if not query:
        return jsonify([])
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = '''
            SELECT 
                c.idContacto,
                c.razonsocial,
                c.identificador,
                c.mail,
                c.telf1,
                c.direccion,
                c.cp,
                c.localidad,
                c.provincia
            FROM contactos c
            WHERE LOWER(c.razonsocial) LIKE LOWER(?)
        '''
        
        params = [f'%{query}%']
        
        # Añadir ordenación
        if sort == 'razonsocial':
            sql += f' ORDER BY c.razonsocial {order}'
        else:
            sql += f' ORDER BY c.{sort} {order}'
            
        sql += ' LIMIT 50'
        
        cursor.execute(sql, params)
        resultados = cursor.fetchall()
        
        contactos_list = []
        for row in resultados:
            contactos_list.append({
                'idContacto': row[0],
                'razonsocial': row[1],
                'identificador': row[2],
                'mail': row[3],
                'telf1': row[4],
                'direccion': row[5],
                'cp': row[6],
                'localidad': row[7],
                'provincia': row[8]
            })
        
        return jsonify(contactos_list)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/api/contactos/searchCarrer', methods=['GET'])
def search_carrer():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify([])
    
    try:
        sugerencias = contactos.obtener_sugerencias_carrer(query)
        return jsonify(sugerencias)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/contactos/search_cp', methods=['GET'])
def search_cp():
    term = request.args.get('term', '').strip()[:5]
    if not term:
        return jsonify([])
    try:
        datos = contactos.buscar_codigos_postales(term)
        return jsonify(datos)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/contactos/get_cp', methods=['GET'])
def get_cp():
    cp = request.args.get('cp', '').strip()
    if not cp:
        return jsonify([])
    
    try:
        datos = contactos.obtener_datos_cp(cp)
        return jsonify(datos)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/contactos/get_contacto/<int:idContacto>', methods=['GET'])
def get_contacto_endpoint(idContacto):
    try:
        contacto = contactos.obtener_contacto(idContacto)
        if contacto:
            return jsonify(contacto)
        else:
            return jsonify({'error': 'Contacto no encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/contactos/create_contacto', methods=['POST'])
def crear():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400

        # Validar campos requeridos
        required_fields = ['razonsocial', 'identificador']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'El campo {field} es requerido'}), 400

        resultado = contactos.crear_contacto(data)
        if resultado['success']:
            return jsonify(resultado), 201
        else:
            return jsonify(resultado), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/contactos/update_contacto/<int:idContacto>', methods=['PUT'])
def actualizar(idContacto):
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400

        # Validar campos requeridos
        required_fields = ['razonsocial', 'identificador']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'El campo {field} es requerido'}), 400

        resultado = contactos.actualizar_contacto(idContacto, data)
        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/contactos/eliminar_contacto/<int:idContacto>', methods=['DELETE'])
def eliminar(idContacto):
    try:
        if contactos.delete_contacto(idContacto):
            return jsonify({'mensaje': 'Contacto eliminado exitosamente'})
        return jsonify({'error': 'No se pudo eliminar el contacto'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/contactos/ocr', methods=['POST'])
def procesar_ocr_contacto():
    """
    Procesa un contacto mediante OCR
    Busca en el buzón de correo el último email con asunto 'C'
    y procesa la imagen adjunta
    """
    try:
        import contacto_ocr
        import imaplib
        import email
        from email.header import decode_header
        import os
        
        # Obtener configuración de email desde variables de entorno
        # Usar la misma configuración que para enviar emails (SMTP_USERNAME/PASSWORD)
        EMAIL_USER = os.getenv('SMTP_USERNAME', os.getenv('EMAIL_USER'))
        EMAIL_PASSWORD = os.getenv('SMTP_PASSWORD', os.getenv('EMAIL_PASSWORD'))
        EMAIL_IMAP_HOST = os.getenv('EMAIL_IMAP_HOST', 'imap.ionos.es')  # IONOS por defecto
        EMAIL_IMAP_PORT = int(os.getenv('EMAIL_IMAP_PORT', '993'))
        
        if not EMAIL_USER or not EMAIL_PASSWORD:
            return jsonify({'error': 'Email no configurado. Configure SMTP_USERNAME y SMTP_PASSWORD en .env'}), 500
        
        # Conectar al buzón
        logger.info(f"📧 Conectando a buzón {EMAIL_USER}...")
        mail = imaplib.IMAP4_SSL(EMAIL_IMAP_HOST, EMAIL_IMAP_PORT)
        mail.login(EMAIL_USER, EMAIL_PASSWORD)
        mail.select('INBOX')
        logger.info(f"✓ Conexión establecida con {EMAIL_IMAP_HOST}")
        
        # Buscar emails NO LEÍDOS con asunto "C" o "c"
        logger.info("🔍 Buscando emails NO LEÍDOS con asunto 'C' o 'c'...")
        # Buscar con UNSEEN (no leídos) y asunto C o c
        status, messages = mail.search(None, 'UNSEEN', '(OR SUBJECT "C" SUBJECT "c")')
        
        if status != 'OK' or not messages[0]:
            mail.close()
            mail.logout()
            logger.warning("⚠️ No se encontraron emails no leídos con asunto 'C' o 'c'")
            return jsonify({'error': 'No hay emails no leídos con asunto "C" o "c"'}), 404
        
        # Obtener el último email (más reciente)
        email_ids = messages[0].split()
        total_emails = len(email_ids)
        ultimo_email_id = email_ids[-1]
        
        logger.info(f"✓ Encontrados {total_emails} email(s) no leído(s)")
        logger.info(f"📨 Procesando email más reciente (ID: {ultimo_email_id.decode()})")
        
        # Obtener el email
        status, msg_data = mail.fetch(ultimo_email_id, '(RFC822)')
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)
        
        # Extraer imágenes adjuntas
        imagen_bytes = None
        nombre_archivo = None
        
        logger.info("📎 Buscando imágenes adjuntas...")
        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue
            
            content_type = part.get_content_type()
            if content_type and content_type.startswith('image/'):
                nombre_archivo = part.get_filename()
                imagen_bytes = part.get_payload(decode=True)
                tamanio_kb = len(imagen_bytes) / 1024
                logger.info(f"✓ Imagen encontrada: {nombre_archivo} ({content_type}, {tamanio_kb:.1f} KB)")
                break
        
        # Cerrar conexión
        mail.close()
        mail.logout()
        logger.info("✓ Conexión cerrada")
        
        if not imagen_bytes:
            logger.error("❌ El email no contiene ninguna imagen adjunta")
            return jsonify({'error': 'El email no contiene ninguna imagen adjunta'}), 400
        
        # Procesar con OCR
        logger.info("🤖 Procesando imagen con OCR (GPT-4 Vision)...")
        datos = contacto_ocr.procesar_imagen_contacto(imagen_bytes)
        logger.info(f"✓ OCR completado - Método: {datos.get('_metodo_ocr', 'N/A')}")
        
        # Marcar email como leído
        logger.info("✉️ Marcando email como leído...")
        try:
            mail = imaplib.IMAP4_SSL(EMAIL_IMAP_HOST, EMAIL_IMAP_PORT)
            mail.login(EMAIL_USER, EMAIL_PASSWORD)
            mail.select('INBOX')
            mail.store(ultimo_email_id, '+FLAGS', '\\Seen')
            mail.close()
            mail.logout()
            logger.info("✓ Email marcado como leído")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo marcar como leído: {e}")
        
        logger.info("🎉 Proceso completado exitosamente")
        return jsonify({
            'success': True,
            'datos': datos,
            'email_procesado': True,
            'total_emails_no_leidos': total_emails
        }), 200
        
    except imaplib.IMAP4.error as e:
        logger.error(f"Error de conexión IMAP: {e}", exc_info=True)
        return jsonify({'error': f'Error conectando al buzón: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Error en OCR de contacto: {e}", exc_info=True)
        return jsonify({'error': f'Error procesando imagen: {str(e)}'}), 500

# ============================================================================
# ENDPOINTS: FACTURAS DE PROVEEDORES
# ============================================================================

# Endpoint de prueba para verificar que el código se está cargando
@app.route('/api/test-reload', methods=['GET'])
def test_reload():
    """Endpoint de prueba para verificar recarga de código"""
    return jsonify({
        'status': 'ok',
        'message': 'Código recargado correctamente',
        'timestamp': '2025-11-15 11:47:00'
    })

@app.route('/api/facturas-proveedores/ocr', methods=['POST'])
@login_required
def procesar_ocr_factura():
    """
    Procesa una factura mediante OCR usando GPT-4 Vision
    Recibe una imagen y extrae los datos automáticamente
    """
    try:
        import factura_ocr
        from werkzeug.datastructures import FileStorage
        
        # Verificar que se envió un archivo
        if 'archivo' not in request.files:
            return jsonify({'error': 'No se envió ningún archivo'}), 400
        
        archivo = request.files['archivo']
        
        if archivo.filename == '':
            return jsonify({'error': 'Archivo vacío'}), 400
        
        # Validar extensión
        extension = archivo.filename.rsplit('.', 1)[1].lower() if '.' in archivo.filename else ''
        if extension not in ['pdf', 'jpg', 'jpeg', 'png']:
            return jsonify({'error': 'Formato no válido. Use PDF, JPG o PNG'}), 400
        
        # Leer bytes del archivo
        imagen_bytes = archivo.read()
        
        # Si es PDF, convertir primera página a imagen
        if extension == 'pdf':
            try:
                from pdf2image import convert_from_bytes
                from PIL import Image
                import io
                
                logger.info("📄 Convirtiendo PDF a imagen...")
                imagenes = convert_from_bytes(imagen_bytes, first_page=1, last_page=1, dpi=200)
                
                if not imagenes:
                    return jsonify({'error': 'No se pudo convertir el PDF'}), 400
                
                # Convertir PIL Image a bytes
                img_buffer = io.BytesIO()
                imagenes[0].save(img_buffer, format='JPEG', quality=95)
                imagen_bytes = img_buffer.getvalue()
                logger.info("✓ PDF convertido a imagen")
                
            except ImportError:
                return jsonify({'error': 'pdf2image no está instalado. Instale: pip install pdf2image'}), 500
            except Exception as e:
                logger.error(f"Error convirtiendo PDF: {e}")
                return jsonify({'error': f'Error convirtiendo PDF: {str(e)}'}), 500
        
        # Procesar con OCR
        logger.info("🤖 Procesando factura con OCR (GPT-4 Vision)...")
        datos = factura_ocr.procesar_imagen_factura(imagen_bytes)
        logger.info(f"✓ OCR completado - Método: {datos.get('_metodo_ocr', 'N/A')}")
        
        return jsonify({
            'success': True,
            'datos': datos
        }), 200
        
    except ValueError as e:
        logger.error(f"Error de validación: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error en OCR de factura: {e}", exc_info=True)
        return jsonify({'error': f'Error procesando factura: {str(e)}'}), 500

@app.route('/api/facturas-proveedores/consultar', methods=['POST'])
@login_required
def consultar_facturas_proveedores_endpoint():
    """
    Consulta facturas recibidas con filtros
    """
    empresa_id = session.get('empresa_id')
    if not empresa_id:
        return jsonify({'error': 'No hay empresa seleccionada'}), 400
    
    try:
        filtros = request.json or {}
        resultado = facturas_proveedores.consultar_facturas_recibidas(empresa_id, filtros)
        
        return jsonify({
            'success': True,
            **resultado
        })
        
    except Exception as e:
        logger.error(f"Error consultando facturas proveedores: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/proveedores/listar', methods=['GET'])
@login_required
def listar_proveedores_endpoint():
    """
    Lista todos los proveedores de la empresa
    """
    empresa_id = session.get('empresa_id')
    if not empresa_id:
        return jsonify({'error': 'No hay empresa seleccionada'}), 400
    
    try:
        activos_solo = request.args.get('activos', 'true').lower() == 'true'
        proveedores = facturas_proveedores.obtener_proveedores(empresa_id, activos_solo)
        
        return jsonify({
            'success': True,
            'proveedores': proveedores
        })
        
    except Exception as e:
        logger.error(f"Error listando proveedores: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/proveedores/<int:proveedor_id>', methods=['GET'])
@login_required
def obtener_proveedor_endpoint(proveedor_id):
    """
    Obtiene un proveedor por su ID
    """
    empresa_id = session.get('empresa_id')
    if not empresa_id:
        return jsonify({'error': 'No hay empresa seleccionada'}), 400
    
    try:
        proveedor = facturas_proveedores.obtener_proveedor_por_id(proveedor_id, empresa_id)
        
        if not proveedor:
            return jsonify({'error': 'Proveedor no encontrado'}), 404
        
        return jsonify({
            'success': True,
            'proveedor': proveedor
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo proveedor: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/proveedores/crear', methods=['POST'])
@login_required
def crear_proveedor_endpoint():
    """
    Crea un nuevo proveedor
    """
    empresa_id = session.get('empresa_id')
    usuario = session.get('username')
    
    if not empresa_id:
        return jsonify({'error': 'No hay empresa seleccionada'}), 400
    
    try:
        datos = request.json
        
        if not datos.get('nombre'):
            return jsonify({'error': 'El nombre es obligatorio'}), 400
        
        # Obtener NIF de la empresa para validar
        conn_usuarios = sqlite3.connect('db/usuarios_sistema.db')
        conn_usuarios.row_factory = sqlite3.Row
        cursor_usuarios = conn_usuarios.cursor()
        cursor_usuarios.execute('SELECT cif FROM empresas WHERE id = ?', (empresa_id,))
        empresa = cursor_usuarios.fetchone()
        conn_usuarios.close()
        
        empresa_nif = empresa['cif'].upper().strip() if empresa and empresa['cif'] else ''
        proveedor_nif = datos.get('nif', '').upper().strip()
        
        # Si el NIF del proveedor es el mismo que el de la empresa, dejarlo vacío
        if proveedor_nif and empresa_nif and proveedor_nif == empresa_nif:
            logger.info(f"NIF del proveedor coincide con NIF de la empresa ({empresa_nif}), dejando vacío")
            datos['nif'] = ''
            proveedor_nif = ''
        
        # Verificar si ya existe un proveedor
        proveedor_existente = None
        
        # 1. Buscar por NIF si existe
        if proveedor_nif:
            proveedor_existente = facturas_proveedores.obtener_proveedor_por_nif(proveedor_nif, empresa_id)
            if proveedor_existente:
                logger.info(f"Proveedor ya existe con NIF {proveedor_nif}: {proveedor_existente['nombre']}")
        
        # 2. Si no se encontró por NIF (o no tiene NIF), buscar por nombre
        if not proveedor_existente:
            proveedor_existente = facturas_proveedores.obtener_proveedor_por_nombre(datos.get('nombre'), empresa_id)
            if proveedor_existente:
                logger.info(f"Proveedor ya existe con nombre '{datos.get('nombre')}': ID {proveedor_existente['id']}")
        
        # Si existe, retornarlo
        if proveedor_existente:
            return jsonify({
                'success': True,
                'proveedor_id': proveedor_existente['id'],
                'proveedor': proveedor_existente,
                'mensaje': 'Proveedor ya existente',
                'ya_existia': True
            })
        
        proveedor_id = facturas_proveedores.crear_proveedor(empresa_id, datos, usuario)
        
        # Obtener el proveedor creado
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM proveedores WHERE id = ?', (proveedor_id,))
        proveedor = dict(cursor.fetchone())
        conn.close()
        
        return jsonify({
            'success': True,
            'proveedor_id': proveedor_id,
            'proveedor': proveedor,
            'mensaje': 'Proveedor creado exitosamente'
        })
        
    except Exception as e:
        logger.error(f"Error creando proveedor: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/facturas-proveedores/subir', methods=['POST'])
@login_required
def subir_factura_proveedor():
    """
    Sube una factura de proveedor con archivos adjuntos
    """
    empresa_id = session.get('empresa_id')
    usuario = session.get('username')
    
    if not empresa_id:
        return jsonify({'error': 'No hay empresa seleccionada'}), 400
    
    try:
        # Obtener datos del formulario
        proveedor_id = request.form.get('proveedor_id')
        numero_factura = request.form.get('numero_factura')
        fecha_emision = request.form.get('fecha_emision')
        fecha_vencimiento = request.form.get('fecha_vencimiento', '')
        base_imponible = float(request.form.get('base_imponible', 0))
        iva = float(request.form.get('iva', 0))
        total = float(request.form.get('total', 0))
        concepto = request.form.get('concepto', '')
        
        if not proveedor_id or not numero_factura or not fecha_emision:
            return jsonify({'error': 'Faltan datos obligatorios'}), 400
        
        # Crear factura en BD
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si la factura ya existe
        # Si tiene número de factura, buscar por número
        if numero_factura and numero_factura.strip():
            cursor.execute('''
                SELECT id, numero_factura, total, fecha_emision FROM facturas_proveedores 
                WHERE empresa_id = ? AND proveedor_id = ? AND numero_factura = ?
            ''', (empresa_id, proveedor_id, numero_factura.strip()))
            
            factura_existente = cursor.fetchone()
            
            if factura_existente:
                conn.close()
                logger.info(f"Factura duplicada detectada (por número): {numero_factura} (ID: {factura_existente['id']})")
                return jsonify({
                    'success': False,
                    'duplicada': True,
                    'factura_id': factura_existente['id'],
                    'mensaje': f'La factura {numero_factura} ya existe para este proveedor',
                    'info': 'Factura duplicada, no se ha insertado'
                }), 200
        
        # Si no tiene número o no se encontró por número, buscar por proveedor + fecha + total
        cursor.execute('''
            SELECT id, numero_factura, total, fecha_emision FROM facturas_proveedores 
            WHERE empresa_id = ? AND proveedor_id = ? AND fecha_emision = ? AND total = ?
        ''', (empresa_id, proveedor_id, fecha_emision, total))
        
        factura_existente = cursor.fetchone()
        
        if factura_existente:
            conn.close()
            logger.info(f"Factura duplicada detectada (por fecha+total): Proveedor {proveedor_id}, Fecha {fecha_emision}, Total {total} (ID: {factura_existente['id']})")
            return jsonify({
                'success': False,
                'duplicada': True,
                'factura_id': factura_existente['id'],
                'mensaje': f'Ya existe una factura del mismo proveedor con la misma fecha ({fecha_emision}) y total ({total}€)',
                'info': 'Factura duplicada, no se ha insertado'
            }), 200
        
        # Marcar como pagada automáticamente (facturas escaneadas ya están pagadas)
        fecha_pago = fecha_emision if fecha_emision else datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute('''
            INSERT INTO facturas_proveedores (
                empresa_id, proveedor_id, numero_factura, fecha_emision,
                fecha_vencimiento, base_imponible, iva_importe, total, concepto,
                estado, fecha_pago, metodo_pago, usuario_alta
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pagada', ?, 'transferencia', ?)
        ''', (empresa_id, proveedor_id, numero_factura, fecha_emision,
              fecha_vencimiento or None, base_imponible, iva, total, concepto, fecha_pago, usuario))
        
        factura_id = cursor.lastrowid
        
        # Guardar archivos si existen
        archivos_guardados = []
        if 'archivos' in request.files:
            archivos = request.files.getlist('archivos')
            
            # Obtener código de empresa
            conn_usuarios = sqlite3.connect('db/usuarios_sistema.db')
            conn_usuarios.row_factory = sqlite3.Row
            cursor_usuarios = conn_usuarios.cursor()
            cursor_usuarios.execute('SELECT codigo FROM empresas WHERE id = ?', (empresa_id,))
            empresa = cursor_usuarios.fetchone()
            conn_usuarios.close()
            empresa_codigo = empresa['codigo'] if empresa else 'default'
            
            # Determinar año
            fecha_obj = datetime.strptime(fecha_emision, '%Y-%m-%d')
            año = fecha_obj.year
            
            # Crear estructura: facturas_proveedores/EMPRESA/facturas_recibidas/YYYY/originales/
            facturas_dir = Path('/var/www/html/facturas_proveedores') / empresa_codigo / 'facturas_recibidas' / str(año) / 'originales'
            facturas_dir.mkdir(parents=True, exist_ok=True)
            
            for archivo in archivos:
                if archivo.filename:
                    # Generar nombre único
                    extension = archivo.filename.rsplit('.', 1)[1].lower()
                    nombre_archivo = f"factura_{factura_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{extension}"
                    ruta_archivo = facturas_dir / nombre_archivo
                    
                    # Guardar archivo
                    archivo.save(str(ruta_archivo))
                    # Guardar ruta relativa
                    ruta_relativa = f"{empresa_codigo}/facturas_recibidas/{año}/originales/{nombre_archivo}"
                    archivos_guardados.append(ruta_relativa)
                    
                    logger.info(f"Archivo guardado: {ruta_relativa}")
            
            # Actualizar ruta_archivo en la BD con el primer archivo guardado
            if archivos_guardados:
                cursor.execute('''
                    UPDATE facturas_proveedores 
                    SET ruta_archivo = ?
                    WHERE id = ?
                ''', (archivos_guardados[0], factura_id))
                logger.info(f"Ruta archivo actualizada en BD: {archivos_guardados[0]}")
        
        # Registrar en historial
        cursor.execute('''
            INSERT INTO historial_facturas_proveedores (
                factura_id, usuario, accion, datos_nuevos
            ) VALUES (?, ?, 'creacion', ?)
        ''', (factura_id, usuario, f'Factura creada. Archivos: {len(archivos_guardados)}'))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Factura {numero_factura} creada con ID {factura_id}")
        
        return jsonify({
            'success': True,
            'factura_id': factura_id,
            'archivos_guardados': archivos_guardados,
            'mensaje': 'Factura guardada exitosamente'
        })
        
    except Exception as e:
        logger.error(f"Error subiendo factura: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/facturas-proveedores/<int:factura_id>', methods=['GET'])
@login_required
def obtener_factura_detalle_endpoint(factura_id):
    """
    Obtiene el detalle completo de una factura
    """
    empresa_id = session.get('empresa_id')
    if not empresa_id:
        return jsonify({'error': 'No hay empresa seleccionada'}), 400
    
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Obtener factura con datos del proveedor
        cursor.execute('''
            SELECT 
                f.*,
                p.nombre as proveedor_nombre,
                p.nif as proveedor_nif,
                p.direccion as proveedor_direccion,
                p.cp as proveedor_cp,
                p.poblacion as proveedor_poblacion,
                p.provincia as proveedor_provincia,
                p.email as proveedor_email,
                p.telefono as proveedor_telefono
            FROM facturas_proveedores f
            JOIN proveedores p ON f.proveedor_id = p.id
            WHERE f.id = ? AND f.empresa_id = ?
        ''', (factura_id, empresa_id))
        
        factura = cursor.fetchone()
        
        if not factura:
            return jsonify({'error': 'Factura no encontrada'}), 404
        
        factura_dict = dict(factura)
        
        # Obtener líneas de la factura
        cursor.execute('''
            SELECT * FROM lineas_factura_proveedor
            WHERE factura_id = ?
            ORDER BY id
        ''', (factura_id,))
        
        lineas = [dict(row) for row in cursor.fetchall()]
        factura_dict['lineas'] = lineas
        
        # Obtener historial
        cursor.execute('''
            SELECT * FROM historial_facturas_proveedores
            WHERE factura_id = ?
            ORDER BY fecha DESC
            LIMIT 10
        ''', (factura_id,))
        
        historial = [dict(row) for row in cursor.fetchall()]
        factura_dict['historial'] = historial
        
        conn.close()
        
        return jsonify({
            'success': True,
            'factura': factura_dict
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo detalle de factura: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/facturas-proveedores/<int:factura_id>/pagar', methods=['PUT'])
@login_required
def marcar_factura_pagada_endpoint(factura_id):
    """
    Marca una factura como pagada
    """
    empresa_id = session.get('empresa_id')
    usuario = session.get('username')
    
    if not empresa_id:
        return jsonify({'error': 'No hay empresa seleccionada'}), 400
    
    try:
        datos = request.json
        fecha_pago = datos.get('fecha_pago')
        metodo_pago = datos.get('metodo_pago', 'transferencia')
        referencia_pago = datos.get('referencia_pago', '')
        
        if not fecha_pago:
            return jsonify({'error': 'Fecha de pago es obligatoria'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar que la factura existe y pertenece a la empresa
        cursor.execute('''
            SELECT id, estado FROM facturas_proveedores
            WHERE id = ? AND empresa_id = ?
        ''', (factura_id, empresa_id))
        
        factura = cursor.fetchone()
        if not factura:
            conn.close()
            return jsonify({'error': 'Factura no encontrada'}), 404
        
        # Actualizar factura
        cursor.execute('''
            UPDATE facturas_proveedores
            SET estado = 'pagada',
                fecha_pago = ?,
                metodo_pago = ?,
                referencia_pago = ?
            WHERE id = ?
        ''', (fecha_pago, metodo_pago, referencia_pago, factura_id))
        
        conn.commit()
        conn.close()
        
        # Registrar en historial
        facturas_proveedores.registrar_historial(
            factura_id,
            'pagada',
            usuario,
            datos_nuevos={
                'fecha_pago': fecha_pago,
                'metodo_pago': metodo_pago,
                'referencia_pago': referencia_pago
            }
        )
        
        return jsonify({
            'success': True,
            'mensaje': 'Factura marcada como pagada'
        })
        
    except Exception as e:
        logger.error(f"Error marcando factura como pagada: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/facturas-proveedores/<int:factura_id>', methods=['PUT'])
@login_required
def editar_factura_endpoint(factura_id):
    """
    Edita los datos de una factura
    """
    empresa_id = session.get('empresa_id')
    usuario = session.get('username')
    
    if not empresa_id:
        return jsonify({'error': 'No hay empresa seleccionada'}), 400
    
    try:
        datos = request.json
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener datos anteriores para historial
        cursor.execute('SELECT * FROM facturas_proveedores WHERE id = ? AND empresa_id = ?', 
                      (factura_id, empresa_id))
        factura_anterior = cursor.fetchone()
        
        if not factura_anterior:
            conn.close()
            return jsonify({'error': 'Factura no encontrada'}), 404
        
        # Actualizar campos permitidos
        campos_actualizables = [
            'numero_factura', 'fecha_emision', 'fecha_vencimiento',
            'base_imponible', 'iva_porcentaje', 'iva_importe', 'total',
            'concepto', 'notas', 'revisado'
        ]
        
        updates = []
        valores = []
        
        for campo in campos_actualizables:
            if campo in datos:
                updates.append(f"{campo} = ?")
                valores.append(datos[campo])
        
        if updates:
            valores.append(factura_id)
            sql = f"UPDATE facturas_proveedores SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(sql, valores)
            conn.commit()
        
        conn.close()
        
        # Registrar en historial
        facturas_proveedores.registrar_historial(
            factura_id,
            'editada',
            usuario,
            datos_anteriores=dict(factura_anterior) if factura_anterior else None,
            datos_nuevos=datos
        )
        
        return jsonify({
            'success': True,
            'mensaje': 'Factura actualizada correctamente'
        })
        
    except Exception as e:
        logger.error(f"Error editando factura: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/facturas-proveedores/<int:factura_id>', methods=['DELETE'])
@login_required
def eliminar_factura_endpoint(factura_id):
    """
    Elimina una factura (soft delete)
    """
    empresa_id = session.get('empresa_id')
    usuario = session.get('username')
    
    if not empresa_id:
        return jsonify({'error': 'No hay empresa seleccionada'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar que existe
        cursor.execute('''
            SELECT id FROM facturas_proveedores
            WHERE id = ? AND empresa_id = ?
        ''', (factura_id, empresa_id))
        
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Factura no encontrada'}), 404
        
        # Eliminar (o marcar como eliminada si prefieres soft delete)
        cursor.execute('DELETE FROM facturas_proveedores WHERE id = ?', (factura_id,))
        conn.commit()
        conn.close()
        
        # Registrar en historial
        facturas_proveedores.registrar_historial(
            factura_id,
            'eliminada',
            usuario
        )
        
        return jsonify({
            'success': True,
            'mensaje': 'Factura eliminada correctamente'
        })
        
    except Exception as e:
        logger.error(f"Error eliminando factura: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/facturas-proveedores/<int:factura_id>/pdf', methods=['GET'])
@login_required
def descargar_pdf_factura_endpoint(factura_id):
    """
    Descarga el PDF de una factura
    """
    empresa_id = session.get('empresa_id')
    
    if not empresa_id:
        return jsonify({'error': 'No hay empresa seleccionada'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ruta_archivo FROM facturas_proveedores
            WHERE id = ? AND empresa_id = ?
        ''', (factura_id, empresa_id))
        
        resultado = cursor.fetchone()
        conn.close()
        
        if not resultado or not resultado[0]:
            return jsonify({'error': 'PDF no encontrado'}), 404
        
        ruta_archivo = resultado[0]
        
        # Construir ruta completa: facturas_proveedores/ + ruta_relativa
        ruta_completa = os.path.join('/var/www/html/facturas_proveedores', ruta_archivo)
        
        logger.info(f"Intentando descargar PDF: {ruta_completa}")
        
        if not os.path.exists(ruta_completa):
            logger.error(f"Archivo no existe: {ruta_completa}")
            return jsonify({'error': 'Archivo no existe en el servidor', 'ruta': ruta_archivo}), 404
        
        from flask import send_file
        return send_file(ruta_completa, mimetype='application/pdf', as_attachment=True)
        
    except Exception as e:
        logger.error(f"Error descargando PDF: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@login_required
@app.route('/api/tickets/obtener_numerador/<string:tipoNum>', methods=['GET'])
def obtener_numero_ticket_route(tipoNum):
    return tickets.obtener_numero_ticket(tipoNum)

@login_required
@app.route('/api/facturas/siguiente_numero', methods=['GET'])
def obtener_siguiente_numero_factura():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        ejercicio = datetime.now().year

        cursor.execute("SELECT numerador FROM numerador WHERE tipo = ? AND ejercicio = ?", ('F', ejercicio))
        resultado = cursor.fetchone()
        
        if not resultado:
            return jsonify({"error": "No se encontró el numerador para facturas"}), 404

        numerador = resultado[0]
        
        return jsonify({"numero": numerador})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@login_required
@app.route('/api/proformas/siguiente_numero', methods=['GET'])
def obtener_siguiente_numero_proforma():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        ejercicio = datetime.now().year

        cursor.execute("SELECT numerador FROM numerador WHERE tipo = ? AND ejercicio = ?", ('P', ejercicio))
        resultado = cursor.fetchone()
        
        if not resultado:
            return jsonify({"error": "No se encontró el numerador para proformas"}), 404

        numerador = resultado[0]
        
        return jsonify({"numero": numerador})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/tickets/total_cobrados_ano_actual', methods=['GET'])
def total_tickets_cobrados_ano_actual():
    return tickets.total_tickets_cobrados_ano_actual()

@app.route('/tickets/media_ventas_mensual', methods=['GET'])
def media_ventas_mensual():
    return tickets.media_ventas_mensual()

@app.route('/tickets/media_ventas_diaria', methods=['GET'])
def media_ventas_diaria():
    return tickets.media_ventas_diaria()

@app.route('/tickets/media_gasto_por_ticket', methods=['GET'])
def media_gasto_por_ticket():
    return tickets.media_gasto_por_ticket()

@login_required
@app.route('/api/tickets/guardar', methods=['POST'])
def guardar_ticket_route():
    return tickets.guardar_ticket()

@login_required
@app.route('/api/tickets/actualizar', methods=['PATCH', 'PUT', 'POST'])
def actualizar_ticket():
    conn = None
    try:
        # Parseo robusto de JSON: leer primero el cuerpo crudo y parsear manualmente
        data = {}
        try:
            ct = request.headers.get('Content-Type')
            cl = request.headers.get('Content-Length')
        except Exception:
            ct = None
            cl = None
        try:
            raw = request.get_data(cache=True, as_text=True) or ''
        except Exception:
            raw = ''
        try:
            preview = raw[:200] if isinstance(raw, str) else str(raw)[:200]
            logger.debug(f"[DEBUG][/api/tickets/actualizar] CT={ct} CL={cl} len_raw={len(raw) if isinstance(raw,str) else 'NA'} raw_preview={preview}")
        except Exception:
            pass
        if raw and raw.strip():
            try:
                data = json.loads(raw)
            except Exception:
                data = {}
        if not data:
            # Fallback a get_json por si el servidor ya decodificó el body
            data = request.get_json(force=True, silent=True) or {}
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400

        id_ticket = data.get('id')
        if not id_ticket:
            return jsonify({'error': 'El campo id es requerido'}), 400

        # Procesar fecha (aceptar DD/MM/YYYY o YYYY-MM-DD)
        fecha_str = data.get('fecha')
        if not fecha_str:
            return jsonify({'error': 'La fecha es requerida'}), 400
        try:
            if '/' in fecha_str:
                dia, mes, anio = fecha_str.split('/')
                fecha = f"{anio}-{mes.zfill(2)}-{dia.zfill(2)}"
            else:
                fecha = fecha_str
        except Exception as e:
            return jsonify({'error': 'Error al procesar la fecha', 'detalle': str(e), 'fecha_recibida': fecha_str}), 400

        numero = data.get('numero')
        detalles = data.get('detalles') or []
        estado = (data.get('estado') or 'C')
        formaPago = data.get('formaPago', 'E')

        try:
            importe_cobrado = redondear_importe(float(data.get('importe_cobrado', 0)))
            total_ticket = redondear_importe(float(data.get('total', 0)))
        except Exception as e:
            return jsonify({'error': 'Importes inválidos', 'detalle': str(e)}), 400

        if not numero or not detalles:
            return jsonify({'error': 'Datos incompletos', 'datos_recibidos': {'numero': numero, 'detalles': len(detalles)}}), 400

        # Recalcular importes usando LÓGICA UNIFICADA (redondeo por línea)
        try:
            importe_bruto = 0
            importe_impuestos = 0
            total_calculado = 0
            
            # APLICAR MISMA LÓGICA QUE FRONTEND UNIFICADO
            for detalle in detalles:
                precio = float(detalle['precio'])
                cantidad = float(detalle['cantidad'])
                iva_pct = float(detalle['impuestos'])
                
                subtotal = precio * cantidad
                # CRÍTICO: Redondear IVA por línea a 2 decimales (igual que frontend)
                iva_linea = round(subtotal * (iva_pct / 100), 2)
                total_linea = round(subtotal + iva_linea, 2)
                
                importe_bruto += subtotal
                importe_impuestos += iva_linea
                total_calculado += total_linea
            
            # Redondear totales finales
            importe_bruto = redondear_importe(importe_bruto)
            importe_impuestos = redondear_importe(importe_impuestos)
        except Exception as e:
            return jsonify({'error': 'Error al calcular importes', 'detalle': str(e)}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verificar existencia del ticket y unicidad de número si cambia
        cursor.execute('SELECT id, numero FROM tickets WHERE id = ?', (id_ticket,))
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'Ticket no encontrado'}), 404
        numero_actual = row['numero'] if isinstance(row, sqlite3.Row) else row[1]
        if numero != numero_actual:
            cursor.execute('SELECT id FROM tickets WHERE numero = ? AND id <> ?', (numero, id_ticket))
            if cursor.fetchone():
                return jsonify({'error': f'Ya existe un ticket con el número {numero}'}), 400

        try:
            conn.execute('BEGIN TRANSACTION')
            cursor.execute('''
                UPDATE tickets
                   SET fecha = ?, numero = ?, importe_bruto = ?, importe_impuestos = ?,
                       importe_cobrado = ?, total = ?, timestamp = ?, estado = ?, formaPago = ?
                 WHERE id = ?
            ''', (
                fecha, numero, importe_bruto, importe_impuestos,
                importe_cobrado, total_ticket, datetime.now().isoformat(), estado, formaPago,
                id_ticket
            ))

            cursor.execute('DELETE FROM detalle_tickets WHERE id_ticket = ?', (id_ticket,))
            for d in detalles:
                cantidad = float(d['cantidad'])
                precio = float(d['precio'])
                impuestos = float(d['impuestos'])
                # Cálculo correcto: IVA desde subtotal sin redondear
                subtotal_raw = cantidad * precio
                iva_detalle = redondear_importe(subtotal_raw * (impuestos / 100.0))
                total_detalle = redondear_importe(subtotal_raw + iva_detalle)
                cursor.execute('''
                    INSERT INTO detalle_tickets (
                        id_ticket, concepto, descripcion, cantidad, precio, impuestos, total, productoId
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    id_ticket,
                    d.get('concepto', ''),
                    d.get('descripcion', ''),
                    cantidad,
                    precio,
                    impuestos,
                    total_detalle,
                    d.get('productoId', None)
                ))

            conn.commit()
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            return jsonify({'error': 'Error al actualizar en la base de datos', 'detalle': str(e)}), 500

        return jsonify({'mensaje': 'Ticket actualizado correctamente', 'id': id_ticket})
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return jsonify({'error': 'Error al procesar la solicitud', 'detalle': str(e)}), 500
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

@login_required
@app.route('/tickets/consulta', methods=['GET'])
def consulta_tickets():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener parámetros de la consulta
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        estado = request.args.get('estado')
        numero = request.args.get('numero')
        forma_pago = request.args.get('formaPago')
        concepto = request.args.get('concepto')

        # Construir la consulta SQL base
        sql = '''
            SELECT t.*
            FROM tickets t
            WHERE 1=1
        '''
        params = []

        # Añadir condiciones según los parámetros
        if fecha_inicio:
            sql += ' AND t.fecha >= ?'
            params.append(fecha_inicio)
        if fecha_fin:
            sql += ' AND t.fecha <= ?'
            params.append(fecha_fin)
        if estado:
            sql += ' AND t.estado = ?'
            params.append(estado)
        if numero:
            sql += ' AND t.numero LIKE ?'
            params.append(f'%{numero}%')
        if forma_pago:
            sql += ' AND t.formaPago = ?'
            params.append(forma_pago)
        if concepto:
            sql += ' AND EXISTS (SELECT 1 FROM detalle_tickets d WHERE d.id_ticket = t.id AND (lower(d.concepto) LIKE ? OR lower(d.descripcion) LIKE ?))'
            like_val = f"%{concepto.lower()}%"
            params.extend([like_val, like_val])

        sql += ' ORDER BY t.fecha DESC, t.timestamp DESC'

        logger.debug("SQL Query:", sql)  # Para depuración
        logger.debug("Params:", params)  # Para depuración

        # Ejecutar la consulta
        cursor.execute(sql, params)
        tickets = cursor.fetchall()

        # Convertir los resultados a una lista de diccionarios
        tickets_list = []
        for ticket in tickets:
            ticket_dict = dict(ticket)
            tickets_list.append(ticket_dict)

        return jsonify(tickets_list)

    except Exception as e:
        logger.error("Error en consulta_tickets:", str(e))  # Para depuración
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/tickets/actualizar_estado/<int:id>', methods=['PATCH'])
def actualizar_estado_ticket(id):
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        if not nuevo_estado:
            return jsonify({'error': 'El estado es requerido'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verificar si el ticket existe
        cursor.execute('SELECT id FROM tickets WHERE id = ?', (id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Ticket no encontrado'}), 404

        # Actualizar el estado
        cursor.execute('UPDATE tickets SET estado = ? WHERE id = ?', (nuevo_estado, id))
        conn.commit()

        return jsonify({'mensaje': 'Estado actualizado correctamente'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/productos/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def manejar_producto_por_id(id):
    """Maneja GET, PUT y DELETE para un producto específico"""
    if request.method == 'GET':
        try:
            producto = productos.obtener_producto(id)
            if producto:
                # Asegurar que subtotal mantenga 5 decimales en la respuesta JSON
                if 'subtotal' in producto:
                    producto['subtotal'] = round(float(producto['subtotal']), 5)
                return jsonify(producto)
            else:
                return jsonify({'error': 'Producto no encontrado'}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'PUT':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No se recibieron datos'}), 400
                
            # Validar campos requeridos
            if not data.get('nombre'):
                return jsonify({'error': 'El campo nombre es requerido'}), 400
            
            import sys
            logger.debug(f"DEBUG app.py - Actualizando producto ID: {id}", file=sys.stderr)
            logger.debug(f"DEBUG app.py - Data recibida: {data}", file=sys.stderr)
            sys.stderr.flush()
                
            resultado = productos.actualizar_producto(id, data)
            if resultado['success']:
                return jsonify(resultado)
            else:
                return jsonify(resultado), 400
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    else:  # DELETE
        try:
            resultado = productos.eliminar_producto(id)
            status = 200 if resultado.get('success') else 400
            return jsonify(resultado), status
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/productos/nombre/<string:nombre>', methods=['GET'])
def buscar_producto_por_nombre(nombre):
    try:
        resultado = productos.buscar_productos({'nombre': nombre})
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/productos', methods=['GET', 'POST'])
def manejar_productos():
    """Maneja GET (listar) y POST (crear) productos"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No se recibieron datos'}), 400
            resultado = productos.crear_producto(data)
            status = 201 if resultado.get('success') else 400
            return jsonify(resultado), status
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    else:  # GET
        try:
            return jsonify(productos.obtener_productos())
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/productos/buscar', methods=['GET'])
def filtrar_productos():
    try:
        # Obtener parámetros de búsqueda
        nombre = request.args.get('nombre', '')
        descripcion = request.args.get('descripcion', '')
        impuestos = request.args.get('impuestos')
        
        # Construir filtros
        filtros = {}
        if nombre:
            filtros['nombre'] = nombre
        if descripcion:
            filtros['descripcion'] = descripcion
        if impuestos is not None:
            # Intentar convertir impuestos sin validación previa
            try:
                if impuestos.strip():
                    filtros['impuestos'] = int(impuestos)
            except (ValueError, TypeError, AttributeError):
                # Si hay error de conversión, no incluir el filtro
                logger.error(f"Error al convertir impuestos: {impuestos}")
                pass
        
        # Buscar productos con los filtros
        resultados = productos.buscar_productos(filtros)
        return jsonify(resultados)
    except Exception as e:
        logger.error(f"Error en filtrar_productos: {str(e)}")
        return jsonify({'error': str(e), 'message': 'Error en la búsqueda'}), 500

@app.route('/productos/paginado', methods=['GET'])
def productos_paginado():
    try:
        nombre = request.args.get('nombre', '').strip()
        # Normalizar y limitar parámetros de paginación
        try:
            page = int(request.args.get('page', 1))
        except Exception:
            page = 1
        try:
            page_size = int(request.args.get('page_size', 10))
        except Exception:
            page_size = 10
        # Límite duro: 1..100
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 1
        if page_size > 100:
            page_size = 100
        sort = request.args.get('sort', 'nombre')
        order = request.args.get('order', 'ASC')

        filtros = {}
        if nombre:
            filtros['nombre'] = nombre

        data = productos.obtener_productos_paginados(
            filtros=filtros,
            page=page,
            page_size=page_size,
            sort=sort,
            order=order
        )
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# crear_producto() consolidado en manejar_productos()
# eliminar_producto_legacy() consolidado en manejar_producto_por_id()

# Definición de crear_producto ya implementada anteriormente
# Esta versión duplicada ha sido eliminada


# ===== Alias con prefijo /api para compatibilidad con el frontend =====
# NOTA: /api/clientes/ventas_mes está ahora en dashboard_routes.py (no duplicar)

@login_required
@app.route('/api/productos', methods=['GET', 'POST'])
def api_manejar_productos():
    """Maneja GET (listar) y POST (crear) productos - versión API"""
    return manejar_productos()

@login_required
@app.route('/api/productos/buscar', methods=['GET'])
def api_filtrar_productos():
    return filtrar_productos()


@login_required
@app.route('/api/productos/paginado', methods=['GET'])
def api_productos_paginado():
    return productos_paginado()


@login_required
@app.route('/api/productos/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def api_manejar_producto_por_id(id):
    """Maneja GET, PUT y DELETE para un producto - versión API"""
    return manejar_producto_por_id(id)

# Funciones PUT, POST y DELETE consolidadas en api_manejar_producto_por_id() y api_manejar_productos()
# actualizar_producto() consolidado en manejar_producto_por_id()
# Segunda definición de eliminar_producto eliminada - Ver implementación anterior

@app.route('/tickets/detalles/<int:id_ticket>', methods=['GET'])
def obtener_ticket_con_detalles_route(id_ticket):
    return tickets.obtener_ticket_con_detalles(id_ticket)

@login_required
@app.route('/api/tickets/obtenerTicket/<int:id_ticket>', methods=['GET'])
def consultar_ticket_detalles(id_ticket):
    return tickets.obtener_ticket_con_detalles(id_ticket)

@app.route('/tickets/actualizar', methods=['PATCH'])
def actualizar_ticket_legacy():
    try:
        data = request.get_json()
        if not data or 'id' not in data:
            return jsonify({"error": "No se recibieron datos o falta el ID"}), 400

        id_ticket = data['id']
        
        # Validar y convertir el importe_cobrado
        try:
            # Asegurarnos de que el importe_cobrado esté presente en los datos
            if 'importe_cobrado' not in data:
                logger.debug("importe_cobrado no está presente en los datos")
                return jsonify({"error": "El campo importe_cobrado es requerido"}), 400

            # Convertir el importe_cobrado a float, reemplazando comas por puntos
            importe_cobrado_str = str(data['importe_cobrado']).replace(',', '.')
            importe_cobrado = redondear_importe(float(importe_cobrado_str))
            logger.debug(f"Datos completos recibidos: {data}")
            logger.info(f"Importe cobrado recibido (raw): {data['importe_cobrado']}")
            logger.debug(f"Importe cobrado convertido: {importe_cobrado}")
        except (ValueError, TypeError) as e:
            logger.error(f"Error al convertir importe_cobrado: {e}")
            return jsonify({"error": f"Error al procesar importe_cobrado: {str(e)}"}), 400

        total = redondear_importe(data.get('total', 0))
        estado = data.get('estado')
        formaPago = data.get('formaPago')
        detalles_nuevos = data.get('detalles', [])


        conn = get_db_connection()
        conn.execute('BEGIN EXCLUSIVE TRANSACTION')
        cursor = conn.cursor()

        # Verificar si el ticket existe y obtener datos actuales
        cursor.execute('SELECT id, importe_cobrado, total FROM tickets WHERE id = ?', (id_ticket,))
        ticket_actual = cursor.fetchone()
        if not ticket_actual:
            conn.rollback()
            return jsonify({"error": "Ticket no encontrado"}), 404

        logger.debug(f"Datos actuales del ticket: {dict(ticket_actual)}")

        # 1. Recuperar todos los detalles existentes
        cursor.execute('''
            SELECT id, concepto, descripcion, cantidad, precio, impuestos, total
            FROM detalle_tickets 
            WHERE id_ticket = ?
        ''', (id_ticket,))
        detalles_existentes = {str(row['id']): dict(row) for row in cursor.fetchall()}

        # 2. Procesar los detalles
        detalles_finales = []
        for detalle in detalles_nuevos:
            detalle_procesado = detalle.copy()
            
            if 'id' in detalle and detalle['id'] and str(detalle['id']) in detalles_existentes:
                # Es un detalle existente
                detalle_original = detalles_existentes[str(detalle['id'])]
                # Comparar si el detalle ha sido modificado
                ha_cambiado = (
                    detalle['concepto'] != detalle_original['concepto'] or
                    detalle.get('descripcion', '') != detalle_original['descripcion'] or
                    float(detalle['cantidad']) != float(detalle_original['cantidad']) or
                    float(detalle['precio']) != float(detalle_original['precio']) or
                    float(detalle['impuestos']) != float(detalle_original['impuestos']) or
                    float(detalle['total']) != float(detalle_original['total'])
                )
                
                if ha_cambiado:
                    # Si el detalle ha sido modificado, usar la nueva forma de pago
                    detalle_procesado['formaPago'] = formaPago
                    logger.info(f"Detalle {detalle['id']} modificado, asignando nueva formaPago: {formaPago}")
                else:
                    # Si no ha sido modificado, mantener la forma de pago original
                    detalle_procesado['formaPago'] = detalle_original['formaPago']
                    logger.info(f"Detalle {detalle['id']} sin cambios, manteniendo formaPago: {detalle_original['formaPago']}")
            else:
                # Es un detalle nuevo, asignar la nueva forma de pago
                detalle_procesado['formaPago'] = formaPago
                logger.debug(f"Detalle nuevo, asignando formaPago: {formaPago}")
            
            detalles_finales.append(detalle_procesado)

        # Calcular importes
        importe_bruto = redondear_importe(sum(float(d['precio']) * int(d['cantidad']) for d in detalles_finales))
        importe_impuestos = redondear_importe(sum((float(d['precio']) * int(d['cantidad'])) * (float(d['impuestos']) / 100) for d in detalles_finales))
        total_ticket = redondear_importe(total)

        logger.debug(f"Importes calculados: bruto={importe_bruto}, impuestos={importe_impuestos}, total={total_ticket}, cobrado={importe_cobrado}")

        # Actualizar todos los campos de una vez, incluyendo el importe_cobrado
        cursor.execute('''
            UPDATE tickets 
            SET importe_bruto = ?,
                importe_impuestos = ?,
                importe_cobrado = ?,
                total = ?,
                estado = ?,
                formaPago = ?,
                timestamp = ?
            WHERE id = ?
        ''', (
            importe_bruto,
            importe_impuestos,
            importe_cobrado,
            total_ticket,
            estado,
            formaPago,
            datetime.now().isoformat(),
            id_ticket
        ))

        # Verificar el estado final
        cursor.execute('SELECT importe_cobrado, total FROM tickets WHERE id = ?', (id_ticket,))
        resultado_final = cursor.fetchone()
        logger.debug("Estado final del ticket:")
        logger.info(f"Importe cobrado: {resultado_final['importe_cobrado']}")
        logger.info(f"Total: {resultado_final['total']}")

        # Actualizar detalles
        cursor.execute('DELETE FROM detalle_tickets WHERE id_ticket = ?', (id_ticket,))

        for detalle in detalles_finales:
            # Recalcular el total correctamente en el backend
            cantidad = float(detalle['cantidad'])
            precio = float(detalle['precio'])
            impuestos = float(detalle['impuestos'])
            
            # Cálculo correcto: IVA desde subtotal sin redondear
            subtotal_raw = cantidad * precio
            iva_detalle = redondear_importe(subtotal_raw * (impuestos / 100))
            total_detalle = redondear_importe(subtotal_raw + iva_detalle)
            
            cursor.execute('''
                INSERT INTO detalle_tickets (
                    id_ticket, concepto, descripcion, cantidad, 
                    precio, impuestos, total, productoId
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                id_ticket,
                detalle['concepto'],
                detalle.get('descripcion', ''),
                cantidad,
                precio,
                impuestos,
                redondear_importe(total_detalle),
                detalle.get('productoId', None)
            ))

        conn.commit()
        logger.info(f"Ticket {id_ticket} actualizado correctamente")
        logger.debug(f"Importe cobrado final: {importe_cobrado}")
        
        return jsonify({
            "mensaje": "Ticket actualizado correctamente",
            "id": id_ticket,
            "importe_cobrado": importe_cobrado,
            "total": total_ticket
        })

    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        logger.error(f"Error al actualizar ticket: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/tickets/verificar_numero/<string:numero>', methods=['GET'])
def verificar_numero_ticket_route(numero):
    return tickets.verificar_numero_ticket(numero)

@login_required
@app.route('/api/facturas/actualizar', methods=['PATCH'])
def actualizar_factura_endpoint():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
        if 'id' not in data:
            return jsonify({'error': 'Se requiere el ID de la factura'}), 400
            
        result = factura.actualizar_factura(data['id'], data)
        
        # Si result es una tupla, significa que es un error con código de estado
        if isinstance(result, tuple):
            return result
            
        # Si no es una tupla, es una respuesta exitosa
        return result
    except Exception as e:
        import traceback
        logger.error(f"Error en actualizar factura: {str(e)}")
        logger.error("Traceback:", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/facturas/<int:idContacto>/<int:idFactura>', methods=['GET'])
def buscar_factura_abierta(idContacto, idFactura):
    try:
        logger.debug(f"Obteniendo factura {idFactura} para contacto {idContacto}")  # Debug
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Consulta para obtener la factura con los datos del contacto
        query = """
            SELECT 
                f.*,
                c.razonsocial,
                c.identificador,
                c.direccion,
                c.cp,
                c.localidad,
                c.provincia
            FROM factura f
            INNER JOIN contactos c ON f.idContacto = c.idContacto
            WHERE f.id = %s AND f.idContacto = %s
        """
        logger.info(f"Ejecutando query: {query}")  # Debug
        logger.debug(f"Con parámetros: idFactura={idFactura}, idContacto={idContacto}")  # Debug
        
        cursor.execute(query, (idFactura, idContacto))
        
        factura = cursor.fetchone()
        logger.debug(f"Resultado de la query: {factura}")  # Debug
        
        if not factura:
            logger.debug("No se encontró la factura")  # Debug
            return jsonify({'error': 'Factura no encontrada'}), 404

        # Convertir a diccionario usando los nombres de columnas
        columnas = [desc[0] for desc in cursor.description]
        logger.debug("Nombres de columnas:", columnas)  # Debug
        
        factura_dict = dict(zip(columnas, factura))
        logger.debug("Factura dict:", factura_dict)  # Debug
        
        # Obtener detalles
        cursor.execute('SELECT * FROM detalle_factura WHERE id_factura = %s', (idFactura,))
        detalles = cursor.fetchall()
        logger.debug(f"Detalles encontrados: {len(detalles)}")  # Debug
        
        # Convertir detalles a lista de diccionarios
        columnas_detalle = [desc[0] for desc in cursor.description]
        detalles_list = [dict(zip(columnas_detalle, detalle)) for detalle in detalles]
        
        # Agregar detalles al diccionario de la factura
        factura_dict['detalles'] = detalles_list
        
        logger.debug("Datos completos de factura a devolver:", factura_dict)  # Debug
        return jsonify(factura_dict)
        
    except Exception as e:
        logger.error(f"Error al obtener factura: {str(e)}")
        import traceback
        logger.error("Traceback:", exc_info=True)  # Debug - muestra el stack trace completo
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@login_required
@app.route('/api/facturas', methods=['POST'])
def crear_factura_endpoint():
    try:
        return factura.crear_factura()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@login_required
@app.route('/api/factura/numero', methods=['GET'])
def obtener_numero_factura_endpoint():
    try:
      
        numerador = formatear_numero_documento('F')
       
        if numerador is None:
            return jsonify({"error": "No se encontró el numerador"}), 404
        return jsonify({"numerador": numerador})
    except Exception as e:
      
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@login_required
@app.route('/api/proforma/abierta/<int:idContacto>', methods=['GET'])
def buscar_proforma_abierta(idContacto):
    return obtener_proforma_abierta(idContacto)

@login_required
@app.route('/api/proforma/numero', methods=['GET'])
def obtener_numero_proforma_endpoint():
    try:
        numero_proforma = formatear_numero_documento('P')
        
        if numero_proforma is None:
            return jsonify({"error": "No se encontró el numerador"}), 404
            
        return jsonify({"numerador": numero_proforma})
    except Exception as e:
      
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/proforma/<int:id>', methods=['GET'])
def obtener_proforma(id):
    try:
        return proforma.obtener_proforma(id)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@login_required
@app.route('/api/proforma', methods=['POST'])
def crear_proforma():
    try:
        return proforma.crear_proforma(request.get_json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@login_required
@app.route('/api/proformas/actualizar', methods=['PATCH'])
def actualizar_proforma():
    try:
        data = request.get_json()
        if not data or 'id' not in data:
            return jsonify({"error": "No se recibieron datos o falta el ID"}), 400

        proforma_id = data['id']
        
        # Validar y convertir el importe_cobrado
        try:
            # Asegurarnos de que el importe_cobrado esté presente en los datos
            if 'importe_cobrado' not in data:
                logger.debug("importe_cobrado no está presente en los datos")
                return jsonify({"error": "El campo importe_cobrado es requerido"}), 400

            # Convertir el importe_cobrado a float, reemplazando comas por puntos
            importe_cobrado_str = str(data['importe_cobrado']).replace(',', '.')
            importe_cobrado = redondear_importe(float(importe_cobrado_str))
            logger.debug(f"Datos completos recibidos: {data}")
            logger.info(f"Importe cobrado recibido (raw): {data['importe_cobrado']}")
            logger.debug(f"Importe cobrado convertido: {importe_cobrado}")
        except (ValueError, TypeError) as e:
            logger.error(f"Error al convertir importe_cobrado: {e}")
            return jsonify({"error": f"Error al procesar importe_cobrado: {str(e)}"}), 400

        total = redondear_importe(data.get('total', 0))
        estado = data.get('estado')
        formaPago = data.get('formaPago')
        detalles_nuevos = data.get('detalles', [])


        conn = get_db_connection()
        conn.execute('BEGIN EXCLUSIVE TRANSACTION')
        cursor = conn.cursor()

        # Verificar si la proforma existe y obtener datos actuales
        cursor.execute('SELECT id, importe_cobrado, total FROM proforma WHERE id = ?', (proforma_id,))
        proforma_actual = cursor.fetchone()
        if not proforma_actual:
            conn.rollback()
            return jsonify({"error": "Proforma no encontrada"}), 404

        logger.debug(f"Datos actuales de la proforma: {dict(proforma_actual)}")

        # 1. Recuperar todos los detalles existentes
        cursor.execute('''
            SELECT id, formaPago, concepto, descripcion, cantidad, precio, impuestos, total
            FROM detalle_proforma 
            WHERE id_proforma = ?
        ''', (proforma_id,))
        detalles_existentes = {str(row['id']): dict(row) for row in cursor.fetchall()}

        # 2. Procesar los detalles
        detalles_finales = []
        for detalle in detalles_nuevos:
            detalle_procesado = detalle.copy()
            
            if 'id' in detalle and detalle['id'] and str(detalle['id']) in detalles_existentes:
                # Es un detalle existente
                detalle_original = detalles_existentes[str(detalle['id'])]
                # Comparar si el detalle ha sido modificado
                ha_cambiado = (
                    detalle['concepto'] != detalle_original['concepto'] or
                    detalle.get('descripcion', '') != detalle_original['descripcion'] or
                    float(detalle['cantidad']) != float(detalle_original['cantidad']) or
                    float(detalle['precio']) != float(detalle_original['precio']) or
                    float(detalle['impuestos']) != float(detalle_original['impuestos']) or
                    float(detalle['total']) != float(detalle_original['total'])
                )
                
                if ha_cambiado:
                    # Si el detalle ha sido modificado, usar la nueva forma de pago
                    detalle_procesado['formaPago'] = formaPago
                    logger.info(f"Detalle {detalle['id']} modificado, asignando nueva formaPago: {formaPago}")
                else:
                    # Si no ha sido modificado, mantener la forma de pago original
                    detalle_procesado['formaPago'] = detalle_original['formaPago']
                    logger.info(f"Detalle {detalle['id']} sin cambios, manteniendo formaPago: {detalle_original['formaPago']}")
            else:
                # Es un detalle nuevo, asignar la nueva forma de pago
                detalle_procesado['formaPago'] = formaPago
                logger.debug(f"Detalle nuevo, asignando formaPago: {formaPago}")
            
            detalles_finales.append(detalle_procesado)

        # Calcular importes usando función unificada
        from utilities import calcular_importes
        importe_bruto = 0
        importe_impuestos = 0
        total_calculado = 0
        
        for detalle in detalles_finales:
            res = calcular_importes(detalle['cantidad'], detalle['precio'], detalle['impuestos'])
            importe_bruto += res['subtotal']
            importe_impuestos += res['iva']
            total_calculado += res['total']
            # Actualizar el total del detalle con el calculado
            detalle['total'] = res['total']
        
        total_proforma = redondear_importe(total_calculado)

        logger.debug(f"Importes calculados: bruto={importe_bruto}, impuestos={importe_impuestos}, total={total_proforma}, cobrado={importe_cobrado}")

        # Actualizar todos los campos de una vez, incluyendo el importe_cobrado
        cursor.execute('''
            UPDATE proforma 
            SET importe_bruto = ?,
                importe_impuestos = ?,
                importe_cobrado = ?,
                total = ?,
                estado = ?,
                formaPago = ?,
                timestamp = ?
            WHERE id = ?
        ''', (
            importe_bruto,
            importe_impuestos,
            importe_cobrado,
            total_proforma,
            estado,
            formaPago,
            datetime.now().isoformat(),
            proforma_id
        ))

        # Verificar el estado final
        cursor.execute('SELECT importe_cobrado, total FROM proforma WHERE id = ?', (proforma_id,))
        resultado_final = cursor.fetchone()
      
        # Actualizar detalles
        cursor.execute('DELETE FROM detalle_proforma WHERE id_proforma = ?', (proforma_id,))

        for detalle in detalles_finales:
            cursor.execute('''
                INSERT INTO detalle_proforma (
                    id_proforma, concepto, descripcion, cantidad, 
                    precio, impuestos, total, formaPago, productoId, fechaDetalle
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                proforma_id,
                detalle['concepto'],
                detalle.get('descripcion', ''),
                int(detalle['cantidad']),
                float(detalle['precio']),
                float(detalle['impuestos']),
                redondear_importe(float(detalle['total'])),
                detalle['formaPago'],
                detalle.get('productoId', None),
                detalle.get('fechaDetalle', data.get('fecha'))
            ))

        conn.commit()
        logger.debug(f"Proforma {proforma_id} actualizada correctamente")
        logger.debug(f"Importe cobrado final: {importe_cobrado}")
        
        return jsonify({
            "mensaje": "Proforma actualizada correctamente",
            "id": proforma_id,
            "importe_cobrado": importe_cobrado,
            "total": total_proforma
        })

    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        logger.error(f"Error al actualizar proforma: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@login_required
@app.route('/api/proformas/consulta', methods=['GET'])
def consultar_proformas():
    return proforma.consultar_proformas()

@login_required
@app.route('/api/proformas/consulta/<int:id>', methods=['GET'])
def consultar_proforma_por_id(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Consulta para obtener la proforma y los datos del contacto
        query = """
            SELECT 
                p.*,
                c.razonsocial,
                c.identificador,
                c.direccion,
                c.localidad,
                c.cp,
                c.provincia
            FROM proforma p
            INNER JOIN contactos c ON p.idcontacto = c.idContacto
            WHERE p.id = ?
        """
        cursor.execute(query, (id,))
        proforma = cursor.fetchone()

        if not proforma:
            return jsonify({'error': 'Proforma no encontrada'}), 404

        # Obtener los detalles de la proforma (ordenados de mayor a menor por ts)
        cursor.execute('SELECT * FROM detalle_proforma WHERE id_proforma = ? ORDER BY ts DESC', (id,))
        detalles = cursor.fetchall()

        # Construir la respuesta
        resultado = {
            'id': proforma['id'],
            'numero': proforma['numero'],
            'fecha': format_date(proforma['fecha']),
            'estado': proforma['estado'],
            'total': float(proforma['total']) if proforma['total'] is not None else 0,
            'idContacto': proforma['idcontacto'],
            'contacto': {
                'id': proforma['idcontacto'],
                'razonsocial': proforma['razonsocial'],
                'identificador': proforma['identificador'],
                'direccion': proforma['direccion'],
                'localidad': proforma['localidad'],
                'cp': proforma['cp'],
                'provincia': proforma['provincia']
            },
            'detalles': [dict(detalle) for detalle in detalles]
        }

        return jsonify(resultado)

    except Exception as e:
        logger.error(f"Error al consultar proforma: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/proforma/verificar_numero/<string:numero>', methods=['GET'])
def verificar_numero_proforma_endpoint(numero):
    try:
        return proforma.verificar_numero_proforma(numero)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/proformas', methods=['POST'])
def crear_proforma_endpoint():
    try:
        return proforma.crear_proforma()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/proformas/<int:id>/convertir', methods=['POST'])
def convertir_proforma_a_factura_endpoint(id):
    try:
        return proforma.convertir_proforma_a_factura(id)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/facturas/obtener_contacto/<int:factura_id>', methods=['GET'])
def obtener_contacto_por_factura_id(factura_id):
    try:
        # Consulta para obtener solo el idContacto asociado a una factura
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT idContacto FROM factura WHERE id = ?"
        cursor.execute(query, (factura_id,))
        resultado = cursor.fetchone()
        
        if resultado:
            return jsonify({'idContacto': resultado['idContacto']})
        else:
            return jsonify({'error': 'Factura no encontrada'}), 404
    
    except Exception as e:
        logger.error(f"Error al obtener contacto para factura ID {factura_id}: {str(e)}")
        return jsonify({'error': 'Error interno del servidor', 'details': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/facturas/consulta/<int:factura_id>', methods=['GET'])
def obtener_factura_para_imprimir(factura_id):
    try:
        # Consulta para obtener los datos de la factura
        query = """
            SELECT 
                f.id,
                f.numero,
                f.fecha,
                f.fvencimiento,
                f.importe_bruto as base,
                f.importe_impuestos as iva,
                f.total,
                f.estado,
                f.formaPago,
                f.importe_cobrado,
                f.tipo,
                f.id_factura_rectificada,
                f.hash_factura,
                c.razonsocial,
                c.direccion,
                c.localidad,
                c.provincia,
                c.cp,
                c.identificador,
                c.mail,
                c.telf1,
                c.telf2,
                c.idContacto as idcontacto,
                d.concepto,
                d.descripcion,
                d.cantidad,
                d.precio,
                d.impuestos,
                d.total as subtotal,
                d.productoId,
                d.fechaDetalle
            FROM factura f
            INNER JOIN contactos c ON f.idContacto = c.idContacto
            INNER JOIN detalle_factura d ON f.id = d.id_factura
            WHERE f.id = ?
            ORDER BY d.id
        """
        
        # Ejecutar la consulta
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, (factura_id,))
        resultados = cursor.fetchall()
        
        if not resultados:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Factura no encontrada'}), 404
            
        # Procesar los resultados
        columnas = [desc[0] for desc in cursor.description]  # Obtener nombres de columnas
        resultados_dict = []
        
        for row in resultados:
            resultado = dict(zip(columnas, row))
            resultados_dict.append(resultado)

        # Obtener código QR, hash, CSV, estado y errores de la tabla registro_facturacion si existe
        logger.debug(f"[DEBUG] Obteniendo QR, hash y CSV para factura_id: {factura_id}")
        cursor.execute("""
            SELECT codigo_qr, hash, csv, estado_envio, errores FROM registro_facturacion
            WHERE factura_id = ?
        """, (factura_id,))
        registro = cursor.fetchone()
        
        logger.debug(f"[DEBUG] ¿Se encontró registro en registro_facturacion?: {registro is not None}")
        if registro:
            logger.debug(f"[DEBUG] Tipo de datos de registro['codigo_qr']: {type(registro['codigo_qr']) if registro['codigo_qr'] else 'None'}")
            logger.debug(f"[DEBUG] Tamaño de datos QR: {len(registro['codigo_qr']) if registro['codigo_qr'] else 0} bytes")
        
        # Definimos variables para el QR, hash, CSV, estado y errores
        qr_code_base64 = None
        hash_value = 'No disponible'
        csv_value = None
        estado_envio = None
        errores_aeat = None
        
        # Obtener hash, CSV, estado y errores desde registro_facturacion si existe
        if registro:
            if registro['hash']:
                hash_value = registro['hash']
                logger.debug(f"[DEBUG] Usando hash de registro_facturacion: {hash_value}")
            if registro['csv']:
                csv_value = registro['csv']
                logger.debug(f"[DEBUG] CSV encontrado: {csv_value}")
            if registro['estado_envio']:
                estado_envio = registro['estado_envio']
                logger.debug(f"[DEBUG] Estado envío: {estado_envio}")
            if registro['errores']:
                errores_aeat = registro['errores']
                logger.debug(f"[DEBUG] Errores AEAT: {errores_aeat[:100]}...")
        # Si no hay hash en registro, usar el hash de la tabla factura
        if hash_value == 'No disponible' and resultados_dict[0]['hash_factura']:
            hash_value = resultados_dict[0]['hash_factura']
            logger.debug(f"[DEBUG] Usando hash de tabla factura: {hash_value}")
        
        # Codificar el QR en base64 si existe o generarlo si no existe
        try:
            import base64

            
            qr_bytes = None
            qr_code_base64 = None  # Nueva variable para mantener la representación base64 final

            # 1. Intentar obtener el QR de la base de datos
            if registro and registro['codigo_qr']:
                logger.debug("[DEBUG] QR encontrado en la base de datos")
                qr_db_value = registro['codigo_qr']
                logger.debug(f"[DEBUG] Tipo de datos QR almacenado: {type(qr_db_value)}")

                # Caso A: el valor es bytes (BLOB) ➜ codificar a base64
                if isinstance(qr_db_value, (bytes, bytearray)):
                    qr_bytes = bytes(qr_db_value)
                    qr_code_base64 = base64.b64encode(qr_bytes).decode('utf-8')
                    logger.debug("[DEBUG] QR obtenido como bytes y codificado a base64")

                # Caso B: el valor es str (probablemente ya base64) ➜ usar directamente
                elif isinstance(qr_db_value, str):
                    # Verificar de forma heurística si parece base64 (empieza con iVBOR para PNG)
                    if qr_db_value.startswith('iVBOR') or qr_db_value.startswith('/9j/'):
                        qr_code_base64 = qr_db_value
                        try:
                            qr_bytes = base64.b64decode(qr_db_value)
                            logger.debug("[DEBUG] QR era cadena base64: decodificado a bytes correctamente")
                        except Exception as e:
                            logger.info(f"[WARNING] No se pudo decodificar la cadena base64 del QR: {e}")
                            qr_bytes = None
                    else:
                        # Si la cadena no parece base64 (p.ej. se ha guardado como texto plano de bytes)
                        logger.debug("[DEBUG] La cadena QR no parece base64, convirtiendo con latin1 y recodificando")
                        qr_bytes = qr_db_value.encode('latin1')
                        qr_code_base64 = base64.b64encode(qr_bytes).decode('utf-8')
            
            # 2. Si no hay QR en la base de datos, NO generarlo: esperar a AEAT
            else:
                logger.debug("[DEBUG] QR no disponible en BBDD y no se generará hasta recibir CSV de AEAT")
                qr_bytes = None
                qr_code_base64 = None
                
                # QR todavía no disponible; se mostrará cuando la AEAT proporcione el CSV.
                logger.debug("[DEBUG] QR no disponible en BBDD. Esperando validación de AEAT para generarlo.")
                qr_bytes = None
                qr_code_base64 = None

            
            # 3. Asegurarse de tener representación base64 válida para enviar al frontend
            if qr_code_base64 is None and qr_bytes is not None:
                qr_code_base64 = base64.b64encode(qr_bytes).decode('utf-8')
                logger.debug("[DEBUG] QR bytes codificados a base64 (no venían de BBDD en base64)")

            if qr_code_base64:
                logger.debug(f"[DEBUG] Longitud de qr_code_base64 final: {len(qr_code_base64)}")
            else:
                logger.error("[ERROR] qr_code_base64 es None. No se podrá mostrar el QR en el frontal")
            
            # 4. Guardar el QR en un archivo accesible (solo si se ha obtenido QR)
            if qr_bytes:
                try:
                    import os
                    qr_dir = '/var/www/html/static/tmp_qr'
                    os.makedirs(qr_dir, exist_ok=True)
                    qr_path = os.path.join(qr_dir, 'qr_temp.png')
                    with open(qr_path, 'wb') as f:
                        f.write(qr_bytes)
                    # Ajustar permisos para que Apache pueda leerlo
                    os.chmod(qr_path, 0o644)
                    logger.debug(f"[DEBUG] QR guardado en {qr_path} para verificación")
                except Exception as e:
                    logger.error(f"[ERROR] Error al guardar archivo QR: {str(e)}")
                    import traceback
                    traceback.print_exc()
                
        except Exception as e:
            logger.error(f"[ERROR] Error al procesar QR: {str(e)}")
            import traceback
            traceback.print_exc()
            qr_code_base64 = None
            
        logger.debug(f"[DEBUG] ¿Se generó qr_code_base64?: {qr_code_base64 is not None}")
        if qr_code_base64:
            logger.debug(f"[DEBUG] Inicio del QR base64: {qr_code_base64[:30]}...")
        else:
            logger.debug("[DEBUG] qr_code_base64 es None")
        
        # Procesar los resultados
        base_total_dec = Decimal('0')
        iva_total_dec = Decimal('0')

        factura = {
            'id': resultados_dict[0]['id'],
            'numero': resultados_dict[0]['numero'],
            'fecha': format_date(resultados_dict[0]['fecha']),
            'fvencimiento': format_date(resultados_dict[0]['fvencimiento']) if resultados_dict[0]['fvencimiento'] else None,
            'base': format_currency_es_two(resultados_dict[0].get('base')), 
            'iva': format_currency_es_two(resultados_dict[0].get('iva')),
            'total': format_currency_es_two(resultados_dict[0].get('total')),
            'estado': resultados_dict[0]['estado'],
            'tipo': resultados_dict[0]['tipo'],
            'id_factura_rectificada': resultados_dict[0]['id_factura_rectificada'],
            'formaPago': resultados_dict[0]['formaPago'],
            'importe_cobrado': format_currency_es_two(resultados_dict[0].get('importe_cobrado')),
            'hash_verifactu': (hash_value if VERIFACTU_HABILITADO else None),
            'qr_verifactu': (qr_code_base64 if VERIFACTU_HABILITADO else None),
            'codigo_qr': (qr_code_base64 if VERIFACTU_HABILITADO else None),  # Alias para compatibilidad
            'csv': csv_value,
            'estado_envio': estado_envio,
            'errores_aeat': errores_aeat,
            'contacto': {
                'id': resultados_dict[0]['idcontacto'],
                'razonsocial': resultados_dict[0]['razonsocial'],
                'direccion': resultados_dict[0]['direccion'],
                'localidad': resultados_dict[0]['localidad'],
                'provincia': resultados_dict[0]['provincia'],
                'cp': resultados_dict[0]['cp'],
                'identificador': resultados_dict[0]['identificador'],
                'email': resultados_dict[0]['mail'],
                'telefono1': resultados_dict[0]['telf1'],
                'telefono2': resultados_dict[0]['telf2']
            },
            'detalles': []
        }
        
        # Procesar las líneas de la factura
        for resultado in resultados_dict:
            if resultado['concepto'] or resultado['descripcion']:  # Solo si hay concepto o descripción (evita líneas nulas)
                qty_dec = _to_decimal(resultado.get('cantidad'))
                price_dec = _to_decimal(resultado.get('precio'))
                iva_pct_dec = _to_decimal(resultado.get('impuestos'))
                base_line = (qty_dec * price_dec).quantize(Decimal('0.00001'), rounding=ROUND_HALF_UP)
                iva_line = (base_line * iva_pct_dec / Decimal('100')).quantize(Decimal('0.00001'), rounding=ROUND_HALF_UP)
                base_total_dec += base_line
                iva_total_dec += iva_line

                linea = {
                    'concepto': resultado['concepto'],
                    'descripcion': resultado['descripcion'],
                    'cantidad': format_number_es_max5(resultado.get('cantidad')),
                    'precio': format_number_es_max5(resultado.get('precio')) if resultado.get('precio') is not None else '',
                    'impuestos': format_percentage(resultado.get('impuestos')),
                    'total': format_currency_es_two(base_line),
                    'productoId': resultado['productoId'] if 'productoId' in resultado else None,
                    'fechaDetalle': resultado['fechaDetalle'] if 'fechaDetalle' in resultado else None
                }
                logger.debug(f"Agregando línea de detalle: {linea}")  # Debug
                factura['detalles'].append(linea)

        # Si los importes de cabecera no existen, usar sumas calculadas
        if not factura['base']:
            factura['base'] = format_currency_es_two(base_total_dec)
        if not factura['iva']:
            factura['iva'] = format_currency_es_two(iva_total_dec)
        if not factura['total']:
            factura['total'] = format_currency_es_two(base_total_dec + iva_total_dec)

        # Añadir CSV y estado de Verifactu
        factura['csv'] = csv_value
        
        # Cargar configuración de Verifactu
        try:
            from config_loader import get as get_config
            verifactu_enabled = bool(get_config("verifactu_enabled", False))
        except Exception:
            verifactu_enabled = False
        
        logger.debug("Datos completos de factura a enviar:", factura)  # Debug
        cursor.close()
        conn.close()
        return jsonify({
            'factura': factura,
            'verifactu_enabled': verifactu_enabled
        })
        
    except Exception as e:
        logger.error(f"Error al obtener la factura: {str(e)}")
        return jsonify({'error': 'Error interno del servidor', 'details': str(e)}), 500

@app.route('/api/factura/abierta/<int:idContacto>/<int:idFactura>', methods=['GET'])
def obtener_factura_abierta_endpoint(idContacto, idFactura):
    logger.debug(f"Endpoint obtener_factura_abierta llamado con idContacto={idContacto}, idFactura={idFactura}")
    try:
        result = obtener_factura_abierta(idContacto, idFactura)
        logger.debug(f"Resultado de obtener_factura_abierta: {result}")
        return result
    except Exception as e:
        logger.error(f"Error al obtener factura abierta: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Importar la función enviar_factura_email_endpoint desde el módulo factura
from factura import enviar_factura_email_endpoint


@app.route('/facturas/email/<int:id_factura>', methods=['POST'])
@app.route('/api/facturas/email/<int:id_factura>', methods=['POST'])
def enviar_factura_email_route(id_factura):
    try:
        logger.debug(f"Intentando enviar factura {id_factura} por email")
        return enviar_factura_email_endpoint(id_factura)
    except Exception as e:
        logger.error(f"Error al enviar factura por email: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/facturas/anular/<int:id_factura>', methods=['POST'])
def anular_factura_route(id_factura):
    from anulacion import anular_factura
    return anular_factura(id_factura)

@app.route('/tickets/anular/<int:id_ticket>', methods=['POST'])
@app.route('/api/tickets/anular/<int:id_ticket>', methods=['POST'])
def anular_ticket_route(id_ticket):
    from anulacion_ticket import anular_ticket
    return anular_ticket(id_ticket)

@app.route('/facturas/consulta', methods=['GET'])
def consultar_facturas_route():
    try:
        return factura.consultar_facturas()
    except Exception as e:
        logger.error(f"Error al consultar facturas: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Rutas para API con redirecciones a las rutas sin prefijo
@app.route('/api/scraping/ejecutar_scrapeo', methods=['POST'])
def api_ejecutar_scrapeo():
    """Endpoint API para ejecutar el script de scraping (redirección)"""
    return ejecutar_scrapeo()

@app.route('/api/scraping/estado_scraping', methods=['GET'])
def api_estado_scraping():
    """Endpoint API para verificar el estado del scraping (redirección)"""
    return estado_scraping()

@app.route('/api/estadisticas_gastos', methods=['GET'])
def api_estadisticas_gastos():
    """Endpoint API para obtener estadísticas de gastos (redirección)"""
    from dashboard_routes import estadisticas_gastos
    return estadisticas_gastos()

@app.route('/api/ingresos_gastos_mes', methods=['GET'])
def api_ingresos_gastos_mes():
    """Endpoint API para obtener ingresos y gastos por mes (redirección)"""
    from gastos import ingresos_gastos_mes
    return ingresos_gastos_mes()

@app.route('/scraping/ejecutar_scrapeo', methods=['POST'])
def ejecutar_scrapeo():
    """Endpoint para ejecutar el script de scraping de forma asíncrona"""
    try:
        # Ejecutar el script de scraping en un subproceso
        # Usar python con el entorno virtual adecuado
        python_path = '/var/www/html/venv/bin/python'
        script_path = '/var/www/html/scrapeo.py'
        log_path = '/tmp/scrapeo_web.log'  # Usar /tmp para garantizar permisos de escritura
        
        # Registrar en el log de scraping que se intenta ejecutar el script
        with open('/var/www/html/scraping_status.log', 'a') as f:
            timestamp = datetime.now().strftime('[%Y-%m-%d %H:%M:%S]')
            f.write(f"{timestamp} Intentando ejecutar script de scraping con xvfb-run\n")
            
        # Verificar que los archivos existen
        if not os.path.exists(python_path):
            return jsonify({'exito': False, 'error': f'No se encontró Python en {python_path}'}), 500
        
        if not os.path.exists(script_path):
            return jsonify({'exito': False, 'error': f'No se encontró el script en {script_path}'}), 500
        
        # Ejecutar directamente el script con sudo para garantizar permisos
        # Usamos sudo -u sami para ejecutarlo con el usuario que tiene todos los permisos
        comando = f"sudo -u sami /usr/bin/xvfb-run -a -s \"-screen 0 1920x1080x24\" {python_path} {script_path} >> {log_path} 2>&1"
        
        # Ejecutar el comando shell completo (asíncrono)
        subprocess.Popen(comando, 
                         shell=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
        
        # Guardar log en un archivo con permisos adecuados
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file = "/var/www/html/scraping_status.log"
        
        # Crear el archivo de log si no existe y asegurarse de que tenga permisos adecuados
        try:
            with open(log_file, "a") as f:
                f.write(f"[{timestamp}] Iniciando proceso de scraping bancario\n")
            
            # Asegurar que el archivo tiene permisos adecuados
            os.chmod(log_file, 0o666)  # Permisos de lectura/escritura para todos
        except Exception as e:
            logger.error(f"Error al escribir en el archivo de log: {str(e)}")
            
        return jsonify({
            'exito': True, 
            'mensaje': 'Proceso de actualización bancaria iniciado correctamente'
        })
        
    except Exception as e:
        # Registrar el error
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open('/var/www/html/log_scraping.txt', 'a') as f:
            f.write(f"[{timestamp}] Error al iniciar el scraping: {str(e)}\n")
            
        return jsonify({
            'exito': False,
            'error': f'Error al ejecutar el script: {str(e)}'
        }), 500

@app.route('/scraping/estado_scraping', methods=['GET'])
def estado_scraping():
    """Endpoint para verificar si el proceso de scraping está en ejecución"""
    try:
        # Verificar el archivo de estado
        log_file = "/var/www/html/scraping_status.log"
        ultima_actualizacion = None
        estado_actual = "desconocido"
        mensaje = ""
        timestamp_actual = datetime.now()
        
        # Verificar si hay algún proceso de python ejecutando scrapeo.py o xvfb-run
        resultado_python = subprocess.run(["pgrep", "-f", "scrapeo.py"], capture_output=True, text=True)
        resultado_xvfb = subprocess.run(["pgrep", "-f", "xvfb-run"], capture_output=True, text=True)
        
        # Comprobar si los procesos están ejecutándose
        en_ejecucion = bool(resultado_python.stdout.strip() or resultado_xvfb.stdout.strip())
        
        # Leer el archivo de estado si existe
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    lineas = f.readlines()
                    if lineas:
                        ultima_linea = lineas[-1].strip()
                        # Tratar de extraer el timestamp
                        if ultima_linea.startswith('[') and ']' in ultima_linea:
                            timestamp_str = ultima_linea[1:ultima_linea.find(']')]
                            try:
                                ultima_actualizacion = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                                # Si la última actualización es de hace más de 10 minutos y
                                # no hay procesos ejecutándose, considerarlo como completado
                                if (timestamp_actual - ultima_actualizacion).total_seconds() > 600 and not en_ejecucion:
                                    estado_actual = "completado"
                                    mensaje = "Proceso completado o interrumpido"
                                else:
                                    estado_actual = "en_ejecucion" if en_ejecucion else "completado_recientemente"
                                    mensaje = ultima_linea[ultima_linea.find(']') + 1:].strip()
                            except ValueError:
                                estado_actual = "error_formato"
                                mensaje = "Error al analizar el timestamp en el log"
            except Exception as e:
                estado_actual = "error_lectura"
                mensaje = f"Error al leer el archivo de log: {str(e)}"
        else:
            estado_actual = "sin_historial"
            mensaje = "No hay historial de ejecuciones previas"
        
        # Registrar esta consulta de estado
        try:
            with open(log_file, "a") as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] Consulta de estado: {estado_actual}, Procesos activos: {en_ejecucion}\n")
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            pass  # No hacemos nada si falla el registro
        
        return jsonify({
            'exito': True,
            'en_ejecucion': en_ejecucion,
            'estado': estado_actual,
            'mensaje': mensaje,
            'ultima_actualizacion': ultima_actualizacion.strftime("%Y-%m-%d %H:%M:%S") if ultima_actualizacion else None
        })
        
    except Exception as e:
        return jsonify({
            'exito': False,
            'error': f'Error al verificar el estado: {str(e)}'
        }), 500

# Endpoints de notificaciones eliminados por requerimiento: no se sirve histórico ni SSE

# Rutas para imprimir facturas como PDF
@app.route('/imprimir_factura_pdf/<int:id_factura>', methods=['GET'])
def imprimir_factura_pdf(id_factura):
    """
    Genera un PDF de la factura con el código QR y permite descargarlo
    """
    try:
        pdf_path = generar_pdf.generar_factura_pdf(id_factura)
        if pdf_path and os.path.exists(pdf_path):
            # Devolver el PDF como descarga
            return send_file(
                pdf_path,
                as_attachment=True,
                download_name=f'factura_{id_factura}.pdf',
                mimetype='application/pdf'
            )
        else:
            return jsonify({'error': 'No se pudo generar el PDF de la factura'}), 500
    except Exception as e:
        import traceback
        logger.error(f"Error en endpoint imprimir_factura_pdf: {str(e)}")
        logger.error("Traceback:", exc_info=True)
        return jsonify({'error': f'Error al generar el PDF: {str(e)}'}), 500

# Agregar la ruta al API también
@app.route('/api/imprimir_factura_pdf/<int:id_factura>', methods=['GET'])
def api_imprimir_factura_pdf(id_factura):
    return imprimir_factura_pdf(id_factura)

# Endpoint para descargar carta de reclamación
@app.route('/api/carta-reclamacion/<string:numero_factura>', methods=['GET'])
def descargar_carta_reclamacion(numero_factura):
    """
    Descarga la carta de reclamación de una factura
    
    Args:
        numero_factura: Número de la factura (ej: F250313)
    
    Returns:
        PDF de la carta de reclamación
    """
    import os
    import glob
    from flask import send_file
    
    try:
        # Obtener empresa_id del usuario actual
        empresa_id = session.get('empresa_id', 'default')
        
        # Buscar el archivo de carta más reciente para esta factura en el directorio de la empresa
        cartas_base_dir = '/var/www/html/cartas_reclamacion'
        cartas_dir = os.path.join(cartas_base_dir, str(empresa_id))
        # Buscar recursivamente en subdirectorios año/mes
        patron = f'{cartas_dir}/**/carta_reclamacion_{numero_factura}_*.pdf'
        
        archivos = glob.glob(patron, recursive=True)
        
        if not archivos:
            return jsonify({'error': f'No se encontró carta de reclamación para la factura {numero_factura}'}), 404
        
        # Obtener el archivo más reciente
        archivo_mas_reciente = max(archivos, key=os.path.getctime)
        
        # Enviar el archivo
        return send_file(
            archivo_mas_reciente,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'carta_reclamacion_{numero_factura}.pdf'
        )
        
    except Exception as e:
        logger.error(f"Error al descargar carta de reclamación: {str(e)}")
        logger.error("Traceback:", exc_info=True)
        return jsonify({'error': f'Error al descargar la carta: {str(e)}'}), 500

# Endpoints para manejar facturas firmadas electrónicamente (XSIG)
@app.route('/validar-factura-xsig/<int:id_factura>', methods=['GET'])
def validar_factura_xsig(id_factura):
    """
    Valida una factura firmada electrónicamente (XSIG)
    
    Args:
        id_factura: ID de la factura con archivo XSIG
        
    Returns:
        JSON con el resultado de la validación incluyendo información de firma
    """
    try:
        # Usar la función de validación que hemos creado en verifactu.py
        resultado = verifactu.validar_factura_xml_antes_procesar(id_factura)
        
        # Verificar si realmente es un archivo XSIG
        if not resultado.get('firmado', False):
            return jsonify({
                'error': 'El archivo no es una factura firmada electrónicamente (XSIG)',
                'valido': False
            }), 400
            
        return jsonify(resultado)
        
    except Exception as e:
        return jsonify({
            'error': f'Error al validar la factura XSIG: {str(e)}',
            'valido': False
        }), 500

@app.route('/procesar-factura-xsig/<int:id_factura>', methods=['POST'])
def procesar_factura_xsig(id_factura):
    """
    Procesa una factura firmada electrónicamente (XSIG) para VERI*FACTU
    generando hash encadenado y código QR
    
    Args:
        id_factura: ID de la factura con archivo XSIG
        
    Returns:
        JSON con los datos generados para VERI*FACTU
    """
    try:
        # Primero validar que sea un archivo XSIG válido
        validacion = verifactu.validar_factura_xml_antes_procesar(id_factura)
        
        if not validacion.get('valido', False):
            return jsonify({
                'error': 'La factura XSIG no es válida',
                'detalles': validacion.get('errores', [])
            }), 400
            
        # Generar datos VERI*FACTU para la factura
        # Intentar obtener empresa_codigo de la sesión, si no, de la BD
        empresa_codigo = session.get('empresa_codigo')
        if not empresa_codigo:
            # Fallback: obtener de la ruta de la BD
            from db_utils import get_db_connection
            import re
            conn = get_db_connection()
            db_path = conn.execute('PRAGMA database_list').fetchone()[2]
            match = re.search(r'/db/([^/]+)/\1\.db', db_path)
            if match:
                empresa_codigo = match.group(1)
            else:
                import os
                db_name = os.path.basename(db_path)
                empresa_codigo = db_name.replace('.db', '')
            conn.close()
        
        resultados = verifactu.generar_datos_verifactu_para_factura(id_factura, empresa_codigo=empresa_codigo)
        
        if not resultados:
            return jsonify({
                'error': 'Error al generar datos VERI*FACTU para la factura'
            }), 500
            
        return jsonify({
            'factura_id': id_factura,
            'hash': resultados.get('hash'),
            'qr_data': resultados.get('qr_data'),
            'firmado': resultados.get('firmado', False),
            'estado': 'Procesada correctamente'
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Error al procesar la factura XSIG: {str(e)}'
        }), 500

# Endpoint API para validación de facturas XSIG (con prefijo api)
@app.route('/api/validar-factura-xsig/<int:id_factura>', methods=['GET'])
def api_validar_factura_xsig(id_factura):
    return validar_factura_xsig(id_factura)

# Endpoint API para procesamiento de facturas XSIG (con prefijo api)
@app.route('/api/factura/xsig/procesar/<int:id_factura>', methods=['POST'])
def api_procesar_factura_xsig(id_factura):
    return procesar_factura_xsig(id_factura)

# Endpoint para enviar facturas a AEAT usando VERI*FACTU
@app.route('/factura/enviar/<int:factura_id>', methods=['POST'])
def enviar_factura_aeat(factura_id):
    """
    Envía una factura al servicio web de AEAT para VERI*FACTU
    
    Args:
        factura_id: ID de la factura a enviar
    
    Returns:
        JSON con el resultado del envío
    """
    try:
        from verifactu.soap.client import enviar_registro_aeat

        # Verificar que la factura existe
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM factura WHERE id = ?', (factura_id,))
        factura = cursor.fetchone()
        conn.close()
        
        if not factura:
            return jsonify({
                'success': False,
                'mensaje': f'No se encontró la factura con ID {factura_id}'
            }), 404
            
        # Realizar el envío a AEAT
        resultado = enviar_registro_aeat(factura_id)
        
        return jsonify(resultado)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'mensaje': f'Error al enviar la factura a AEAT: {str(e)}'
        }), 500
        
@app.route('/api/factura/enviar/<int:factura_id>', methods=['POST'])
def api_enviar_factura_aeat(factura_id):
    return enviar_factura_aeat(factura_id)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001)

import traceback

@app.route('/api/ventas/media_por_documento', methods=['GET'])
def obtener_media_por_documento():
    try:
        # Obtener mes y año de los parámetros de consulta
        mes = request.args.get('mes')
        anio = request.args.get('anio', str(datetime.now().year))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Diccionario para almacenar resultados
        resultado = {
            'tickets': {
                'actual': {'total': 0, 'cantidad': 0, 'media': 0, 'media_mensual': 0},
                'anterior': {'total': 0, 'cantidad': 0, 'media': 0, 'mismo_mes': {'total': 0, 'cantidad': 0}},
                'porcentaje_diferencia': 0,
                'porcentaje_diferencia_mes': 0
            },
            'facturas': {
                'actual': {'total': 0, 'cantidad': 0, 'media': 0, 'media_mensual': 0},
                'anterior': {'total': 0, 'cantidad': 0, 'media': 0, 'mismo_mes': {'total': 0, 'cantidad': 0}},
                'porcentaje_diferencia': 0,
                'porcentaje_diferencia_mes': 0
            },
            'global': {
                'actual': {'total': 0, 'cantidad': 0, 'media': 0, 'media_mensual': 0},
                'anterior': {'total': 0, 'cantidad': 0, 'media': 0, 'mismo_mes': {'total': 0, 'cantidad': 0}},
                'porcentaje_diferencia': 0,
                'porcentaje_diferencia_mes': 0
            }
        }
        
        # Año anterior para comparativas
        anio_anterior = str(int(anio) - 1)
        
        # Obtener datos de tickets del año actual
        cursor.execute('''
            SELECT 
                SUM(total) as total_anual,
                COUNT(*) as cantidad_anual
            FROM tickets
            WHERE estado = 'C' AND strftime('%Y', fecha) = ?
        ''', (anio,))
        tickets_actual = cursor.fetchone()
        
        # Obtener datos de tickets del mes actual
        cursor.execute('''
            SELECT 
                SUM(total) as total_mes,
                COUNT(*) as cantidad_mes
            FROM tickets
            WHERE estado = 'C' AND strftime('%Y-%m', fecha) = ?
        ''', (f"{anio}-{mes}",))
        tickets_mes_actual = cursor.fetchone()
        
        # Obtener datos de tickets del año anterior
        cursor.execute('''
            SELECT 
                SUM(total) as total_anual,
                COUNT(*) as cantidad_anual
            FROM tickets
            WHERE estado = 'C' AND strftime('%Y', fecha) = ?
        ''', (anio_anterior,))
        tickets_anterior = cursor.fetchone()
        
        # Obtener datos de tickets del mismo mes del año anterior
        cursor.execute('''
            SELECT 
                SUM(total) as total_mes,
                COUNT(*) as cantidad_mes
            FROM tickets
            WHERE estado = 'C' AND strftime('%Y-%m', fecha) = ?
        ''', (f"{anio_anterior}-{mes}",))
        tickets_mes_anterior = cursor.fetchone()
        
        # Obtener datos de facturas del año actual
        cursor.execute('''
            SELECT 
                SUM(total) as total_anual,
                COUNT(*) as cantidad_anual
            FROM factura
            WHERE estado = 'C' AND strftime('%Y', fecha) = ?
        ''', (anio,))
        facturas_actual = cursor.fetchone()
        
        # Obtener datos de facturas del mes actual
        cursor.execute('''
            SELECT 
                SUM(total) as total_mes,
                COUNT(*) as cantidad_mes
            FROM factura
            WHERE estado = 'C' AND strftime('%Y-%m', fecha) = ?
        ''', (f"{anio}-{mes}",))
        facturas_mes_actual = cursor.fetchone()
        
        # Obtener datos de facturas del año anterior
        cursor.execute('''
            SELECT 
                SUM(total) as total_anual,
                COUNT(*) as cantidad_anual
            FROM factura
            WHERE estado = 'C' AND strftime('%Y', fecha) = ?
        ''', (anio_anterior,))
        facturas_anterior = cursor.fetchone()
        
        # Obtener datos de facturas del mismo mes del año anterior
        cursor.execute('''
            SELECT 
                SUM(total) as total_mes,
                COUNT(*) as cantidad_mes
            FROM factura
            WHERE estado = 'C' AND strftime('%Y-%m', fecha) = ?
        ''', (f"{anio_anterior}-{mes}",))
        facturas_mes_anterior = cursor.fetchone()
        
        # Procesar datos de tickets
        tickets_total_actual = float(tickets_actual['total_anual'] or 0)
        tickets_cantidad_actual = int(tickets_actual['cantidad_anual'] or 0)
        tickets_total_mes_actual = float(tickets_mes_actual['total_mes'] or 0)
        tickets_cantidad_mes_actual = int(tickets_mes_actual['cantidad_mes'] or 0)
        
        tickets_total_anterior = float(tickets_anterior['total_anual'] or 0)
        tickets_cantidad_anterior = int(tickets_anterior['cantidad_anual'] or 0)
        tickets_total_mes_anterior = float(tickets_mes_anterior['total_mes'] or 0)
        tickets_cantidad_mes_anterior = int(tickets_mes_anterior['cantidad_mes'] or 0)
        
        # Procesar datos de facturas
        facturas_total_actual = float(facturas_actual['total_anual'] or 0)
        facturas_cantidad_actual = int(facturas_actual['cantidad_anual'] or 0)
        facturas_total_mes_actual = float(facturas_mes_actual['total_mes'] or 0)
        facturas_cantidad_mes_actual = int(facturas_mes_actual['cantidad_mes'] or 0)
        
        facturas_total_anterior = float(facturas_anterior['total_anual'] or 0)
        facturas_cantidad_anterior = int(facturas_anterior['cantidad_anual'] or 0)
        facturas_total_mes_anterior = float(facturas_mes_anterior['total_mes'] or 0)
        facturas_cantidad_mes_anterior = int(facturas_mes_anterior['cantidad_mes'] or 0)
        
        # Calcular medias y porcentajes para tickets
        tickets_media_actual = tickets_total_actual / tickets_cantidad_actual if tickets_cantidad_actual > 0 else 0
        tickets_media_anterior = tickets_total_anterior / tickets_cantidad_anterior if tickets_cantidad_anterior > 0 else 0
        tickets_porcentaje_diferencia = ((tickets_total_actual - tickets_total_anterior) / tickets_total_anterior * 100) if tickets_total_anterior > 0 else 0
        tickets_porcentaje_diferencia_mes = ((tickets_total_mes_actual - tickets_total_mes_anterior) / tickets_total_mes_anterior * 100) if tickets_total_mes_anterior > 0 else 0
        
        # Calcular medias y porcentajes para facturas
        facturas_media_actual = facturas_total_actual / facturas_cantidad_actual if facturas_cantidad_actual > 0 else 0
        facturas_media_anterior = facturas_total_anterior / facturas_cantidad_anterior if facturas_cantidad_anterior > 0 else 0
        facturas_porcentaje_diferencia = ((facturas_total_actual - facturas_total_anterior) / facturas_total_anterior * 100) if facturas_total_anterior > 0 else 0
        facturas_porcentaje_diferencia_mes = ((facturas_total_mes_actual - facturas_total_mes_anterior) / facturas_total_mes_anterior * 100) if facturas_total_mes_anterior > 0 else 0
        
        # Calcular datos globales
        global_total_actual = tickets_total_actual + facturas_total_actual
        global_cantidad_actual = tickets_cantidad_actual + facturas_cantidad_actual
        global_media_actual = global_total_actual / global_cantidad_actual if global_cantidad_actual > 0 else 0
        
        global_total_anterior = tickets_total_anterior + facturas_total_anterior
        global_cantidad_anterior = tickets_cantidad_anterior + facturas_cantidad_anterior
        global_media_anterior = global_total_anterior / global_cantidad_anterior if global_cantidad_anterior > 0 else 0
        
        global_total_mes_actual = tickets_total_mes_actual + facturas_total_mes_actual
        global_cantidad_mes_actual = tickets_cantidad_mes_actual + facturas_cantidad_mes_actual
        
        global_total_mes_anterior = tickets_total_mes_anterior + facturas_total_mes_anterior
        global_cantidad_mes_anterior = tickets_cantidad_mes_anterior + facturas_cantidad_mes_anterior
        
        global_porcentaje_diferencia = ((global_total_actual - global_total_anterior) / global_total_anterior * 100) if global_total_anterior > 0 else 0
        global_porcentaje_diferencia_mes = ((global_total_mes_actual - global_total_mes_anterior) / global_total_mes_anterior * 100) if global_total_mes_anterior > 0 else 0
        
        # Rellenar el diccionario resultado para tickets
        resultado['tickets']['actual'] = {
            'total': tickets_total_actual,
            'cantidad': tickets_cantidad_actual,
            'media': tickets_media_actual,
            'mes_actual': {
                'total': tickets_total_mes_actual,
                'cantidad': tickets_cantidad_mes_actual
            }
            # La media_mensual se calcula en el frontend
        }
        resultado['tickets']['anterior'] = {
            'total': tickets_total_anterior,
            'cantidad': tickets_cantidad_anterior,
            'media': tickets_media_anterior,
            'mismo_mes': {
                'total': tickets_total_mes_anterior,
                'cantidad': tickets_cantidad_mes_anterior
            }
        }
        resultado['tickets']['porcentaje_diferencia'] = tickets_porcentaje_diferencia
        resultado['tickets']['porcentaje_diferencia_mes'] = tickets_porcentaje_diferencia_mes
        
        # Rellenar el diccionario resultado para facturas
        resultado['facturas']['actual'] = {
            'total': facturas_total_actual,
            'cantidad': facturas_cantidad_actual,
            'media': facturas_media_actual,
            'mes_actual': {
                'total': facturas_total_mes_actual,
                'cantidad': facturas_cantidad_mes_actual
            }
            # La media_mensual se calcula en el frontend
        }
        resultado['facturas']['anterior'] = {
            'total': facturas_total_anterior,
            'cantidad': facturas_cantidad_anterior,
            'media': facturas_media_anterior,
            'mismo_mes': {
                'total': facturas_total_mes_anterior,
                'cantidad': facturas_cantidad_mes_anterior
            }
        }
        resultado['facturas']['porcentaje_diferencia'] = facturas_porcentaje_diferencia
        resultado['facturas']['porcentaje_diferencia_mes'] = facturas_porcentaje_diferencia_mes
        
        # Rellenar el diccionario resultado para global
        resultado['global']['actual'] = {
            'total': global_total_actual,
            'cantidad': global_cantidad_actual,
            'media': global_media_actual,
            'mes_actual': {
                'total': global_total_mes_actual,
                'cantidad': global_cantidad_mes_actual
            }
            # La media_mensual se calcula en el frontend
        }
        resultado['global']['anterior'] = {
            'total': global_total_anterior,
            'cantidad': global_cantidad_anterior,
            'media': global_media_anterior,
            'mismo_mes': {
                'total': global_total_mes_anterior,
                'cantidad': global_cantidad_mes_anterior
            }
        }
        resultado['global']['porcentaje_diferencia'] = global_porcentaje_diferencia
        resultado['global']['porcentaje_diferencia_mes'] = global_porcentaje_diferencia_mes
        
        # Buscar si hay tabla de proformas y añadir esos datos si existe
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='proforma';")
            if cursor.fetchone():
                # Obtener datos de proformas del año actual
                cursor.execute('''
                    SELECT 
                        SUM(total) as total_anual,
                        COUNT(*) as cantidad_anual
                    FROM proforma
                    WHERE estado = 'C' AND strftime('%Y', fecha) = ?
                ''', (anio,))
                proformas_actual = cursor.fetchone()
                
                # Obtener datos de proformas del mes actual
                cursor.execute('''
                    SELECT 
                        SUM(total) as total_mes,
                        COUNT(*) as cantidad_mes
                    FROM proforma
                    WHERE estado = 'C' AND strftime('%Y-%m', fecha) = ?
                ''', (f"{anio}-{mes}",))
                proformas_mes_actual = cursor.fetchone()
                
                # Obtener datos de proformas del año anterior
                cursor.execute('''
                    SELECT 
                        SUM(total) as total_anual,
                        COUNT(*) as cantidad_anual
                    FROM proforma
                    WHERE estado = 'C' AND strftime('%Y', fecha) = ?
                ''', (anio_anterior,))
                proformas_anterior = cursor.fetchone()
                
                # Obtener datos de proformas del mismo mes del año anterior
                cursor.execute('''
                    SELECT 
                        SUM(total) as total_mes,
                        COUNT(*) as cantidad_mes
                    FROM proforma
                    WHERE estado = 'C' AND strftime('%Y-%m', fecha) = ?
                ''', (f"{anio_anterior}-{mes}",))
                proformas_mes_anterior = cursor.fetchone()
                
                # Procesar datos de proformas
                proformas_total_actual = float(proformas_actual['total_anual'] or 0)
                proformas_cantidad_actual = int(proformas_actual['cantidad_anual'] or 0)
                proformas_total_mes_actual = float(proformas_mes_actual['total_mes'] or 0)
                proformas_cantidad_mes_actual = int(proformas_mes_actual['cantidad_mes'] or 0)
                
                proformas_total_anterior = float(proformas_anterior['total_anual'] or 0)
                proformas_cantidad_anterior = int(proformas_anterior['cantidad_anual'] or 0)
                proformas_total_mes_anterior = float(proformas_mes_anterior['total_mes'] or 0)
                proformas_cantidad_mes_anterior = int(proformas_mes_anterior['cantidad_mes'] or 0)
                
                # Calcular medias y porcentajes para proformas
                proformas_media_actual = proformas_total_actual / proformas_cantidad_actual if proformas_cantidad_actual > 0 else 0
                proformas_media_anterior = proformas_total_anterior / proformas_cantidad_anterior if proformas_cantidad_anterior > 0 else 0
                proformas_porcentaje_diferencia = ((proformas_total_actual - proformas_total_anterior) / proformas_total_anterior * 100) if proformas_total_anterior > 0 else 0
                proformas_porcentaje_diferencia_mes = ((proformas_total_mes_actual - proformas_total_mes_anterior) / proformas_total_mes_anterior * 100) if proformas_total_mes_anterior > 0 else 0
                
                # Añadir proformas al diccionario resultado
                resultado['proformas'] = {
                    'actual': {
                        'total': proformas_total_actual,
                        'cantidad': proformas_cantidad_actual,
                        'media': proformas_media_actual,
                        'mes_actual': {
                            'total': proformas_total_mes_actual,
                            'cantidad': proformas_cantidad_mes_actual
                        }
                        # La media_mensual se calcula en el frontend
                    },
                    'anterior': {
                        'total': proformas_total_anterior,
                        'cantidad': proformas_cantidad_anterior,
                        'media': proformas_media_anterior,
                        'mismo_mes': {
                            'total': proformas_total_mes_anterior,
                            'cantidad': proformas_cantidad_mes_anterior
                        }
                    },
                    'porcentaje_diferencia': proformas_porcentaje_diferencia,
                    'porcentaje_diferencia_mes': proformas_porcentaje_diferencia_mes
                }
        except Exception as e:
            # Si hay error al buscar proformas, continuamos sin ellas
            logger.error(f"Error al buscar proformas: {e}")
        
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error en obtener_media_por_documento: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        if 'cursor' in locals() and cursor is not None:
            cursor.close()
        if 'conn' in locals() and conn is not None:
            conn.close()

@app.route('/api/ventas/total_mes', methods=['GET'])
def obtener_totales_mes():
    try:
        anio = request.args.get('anio', str(datetime.now().year))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener totales de tickets por mes
        cursor.execute('''
            SELECT 
                strftime('%m', fecha) as mes,
                COUNT(*) as cantidad,
                SUM(total) as total
            FROM tickets
            WHERE estado = 'C' AND strftime('%Y', fecha) = ?
            GROUP BY mes
            ORDER BY mes
        ''', (anio,))
        
        tickets = {}
        for row in cursor.fetchall():
            tickets[row['mes']] = {
                'cantidad': row['cantidad'],
                'total': float(row['total']) if row['total'] else 0.0
            }
        
        # Obtener totales de facturas por mes
        cursor.execute('''
            SELECT 
                strftime('%m', fecha) as mes,
                COUNT(*) as cantidad,
                SUM(total) as total
            FROM factura
            WHERE estado = 'C' AND strftime('%Y', fecha) = ?
            GROUP BY mes
            ORDER BY mes
        ''', (anio,))
        
        facturas = {}
        for row in cursor.fetchall():
            facturas[row['mes']] = {
                'cantidad': row['cantidad'],
                'total': float(row['total']) if row['total'] else 0.0
            }
        
        # Calcular totales globales
        global_data = {}
        for mes in range(1, 13):
            mes_str = f"{mes:02d}"
            total_tickets = tickets.get(mes_str, {'total': 0})['total']
            total_facturas = facturas.get(mes_str, {'total': 0})['total']
            global_data[mes_str] = total_tickets + total_facturas
        
        return jsonify({
            'anio': anio,
            'tickets': tickets,
            'facturas': facturas,
            'global': global_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/estadisticas.html')
@require_admin
def estadisticas_html():
    """Serve estadisticas.html with corrected paths - Solo admin"""
    import os
    try:
        # Read the original file and fix the paths
        with open(os.path.join(BASE_DIR, 'frontend', 'estadisticas.html'), 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix relative paths for root serving
        content = content.replace('../static/', './static/')
        
        from flask import Response
        return Response(content, mimetype='text/html')
    except Exception as e:
        return f"Error loading estadisticas.html: {str(e)}", 500

# ================== API: Presupuestos ================== #
@login_required
@app.route('/api/presupuesto/numero', methods=['GET'])
def obtener_numero_presupuesto_endpoint():
    try:
        numero = formatear_numero_documento('O')
        if numero is None:
            return jsonify({"error": "No se encontró el numerador"}), 404
        return jsonify({"numerador": numero})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/presupuesto/abierta/<int:idContacto>', methods=['GET'])
def buscar_presupuesto_abierto(idContacto):
    return presupuesto.obtener_presupuesto_abierto(idContacto)

@app.route('/api/presupuesto', methods=['POST'])
def crear_presupuesto_endpoint():
    try:
        return presupuesto.crear_presupuesto()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/presupuestos/actualizar', methods=['PATCH'])
def actualizar_presupuesto_endpoint():
    try:
        data = request.get_json() or {}
        if 'id' not in data:
            return jsonify({"error": "Falta el ID"}), 400
        return presupuesto.actualizar_presupuesto(data['id'], data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/presupuestos/consulta', methods=['GET'])
def consultar_presupuestos_endpoint():
    return presupuesto.consultar_presupuestos()

@app.route('/api/presupuestos/consulta/<int:id>', methods=['GET'])
def consultar_presupuesto_por_id(id):
    try:
        return presupuesto.obtener_presupuesto(id)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/presupuestos/<int:id>/convertir_factura', methods=['POST'])
def convertir_presupuesto_a_factura_endpoint(id):
    try:
        return presupuesto.convertir_presupuesto_a_factura(id)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/presupuestos/<int:id>/convertir_ticket', methods=['POST'])
def convertir_presupuesto_a_ticket_endpoint(id):
    try:
        return presupuesto.convertir_presupuesto_a_ticket(id)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/presupuestos/<int:id>/imprimir', methods=['GET'])
def imprimir_presupuesto_endpoint(id):
    try:
        return presupuesto.generar_pdf_presupuesto(id)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/presupuestos/<int:id>/enviar_email', methods=['POST'])
def enviar_email_presupuesto_endpoint(id):
    try:
        return presupuesto.enviar_email_presupuesto(id)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ================== RUTAS HTML FRONTEND ================== #

# ENDPOINT ELIMINADO - Ahora se usa el de auth_routes.py que solo devuelve plantilla JSON
# @app.route('/api/auth/branding', methods=['GET'])

# Endpoint de debug para sesiones (TEMPORAL - ELIMINAR EN PRODUCCIÓN)
@app.route('/api/debug/session')
def debug_session():
    """Debug endpoint para verificar estado de sesiones"""
    return jsonify({
        'session_data': dict(session),
        'session_new': session.new if hasattr(session, 'new') else None,
        'session_modified': session.modified if hasattr(session, 'modified') else None,
        'cookies_in_request': dict(request.cookies),
        'headers': dict(request.headers),
        'remote_addr': request.remote_addr,
        'scheme': request.scheme,
        'is_secure': request.is_secure,
        'forwarded_proto': request.headers.get('X-Forwarded-Proto'),
        'config': {
            'SESSION_COOKIE_SECURE': app.config.get('SESSION_COOKIE_SECURE'),
            'SESSION_COOKIE_SAMESITE': app.config.get('SESSION_COOKIE_SAMESITE'),
            'SESSION_COOKIE_HTTPONLY': app.config.get('SESSION_COOKIE_HTTPONLY'),
            'SESSION_COOKIE_NAME': app.config.get('SESSION_COOKIE_NAME')
        }
    })

# Ruta raíz e index - debe estar ANTES de la ruta genérica
@app.route('/')
@app.route('/index')
def ruta_raiz():
    """Redirige a index.html que manejará la lógica de sesión"""
    # NO limpiar sesión aquí, dejar que index.html verifique
    return redirect('/index.html')

@app.route('/app')
@app.route('/app.html')
@login_required
def servir_app():
    """Sirve la aplicación principal (requiere autenticación)"""
    try:
        with open(os.path.join(BASE_DIR, 'frontend', '_app_private.html'), 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, mimetype='text/html')
    except Exception as e:
        logger.error(f"Error sirviendo aplicación: {e}", exc_info=True)
        return Response(f'Error sirviendo aplicación: {e}', status=500)

@app.route('/LOGIN.html')
def servir_login():
    """Sirve la página de login del sistema multiempresa"""
    try:
        with open(os.path.join(BASE_DIR, 'frontend', 'LOGIN.html'), 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, mimetype='text/html')
    except Exception as e:
        logger.error(f"Error sirviendo LOGIN.html: {e}", exc_info=True)
        return Response(f'Error sirviendo LOGIN.html: {e}', status=500)

@app.route('/forgot-password.html')
def servir_forgot_password():
    """Sirve la página de recuperación de contraseña"""
    try:
        with open(os.path.join(BASE_DIR, 'frontend', 'forgot-password.html'), 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, mimetype='text/html')
    except Exception as e:
        logger.error(f"Error sirviendo forgot-password.html: {e}", exc_info=True)
        return Response(f'Error sirviendo forgot-password.html: {e}', status=500)

@app.route('/reset-password')
def servir_reset_password():
    """Sirve la página de reseteo de contraseña"""
    try:
        with open(os.path.join(BASE_DIR, 'frontend', 'reset-password.html'), 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, mimetype='text/html')
    except Exception as e:
        logger.error(f"Error sirviendo reset-password.html: {e}", exc_info=True)
        return Response(f'Error sirviendo reset-password.html: {e}', status=500)

@app.route('/<path:filename>.html')
@login_required
def servir_html_protegido(filename):
    """
    Ruta genérica para servir todos los archivos HTML del frontend con protección de login.
    Excepciones: LOGIN.html (ya tiene su propia ruta sin protección)
    """
    try:
        # Páginas especiales que requieren permisos de admin
        if filename == 'ADMIN_PERMISOS':
            if not (session.get('es_admin_empresa') or session.get('es_superadmin')):
                return Response('Acceso denegado. Se requieren permisos de administrador.', status=403)
        
        # Construir ruta del archivo
        archivo_path = os.path.join(BASE_DIR, 'frontend', f'{filename}.html')
        
        # Verificar que el archivo existe
        if not os.path.exists(archivo_path):
            logger.warning(f"Archivo HTML no encontrado: {filename}.html")
            return Response(f'Página no encontrada: {filename}.html', status=404)
        
        # Leer y servir el archivo
        with open(archivo_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Correcciones especiales para estadisticas.html
        if filename == 'estadisticas':
            content = content.replace('../static/', './static/')
        
        return Response(content, mimetype='text/html')
        
    except Exception as e:
        logger.error(f"Error sirviendo {filename}.html: {e}", exc_info=True)
        return Response(f'Error sirviendo {filename}.html: {e}', status=500)

# Rutas específicas mantenidas por compatibilidad
@app.route('/DASHBOARD.html')
@login_required
def servir_dashboard():
    """Sirve el dashboard principal del sistema"""
    try:
        with open(os.path.join(BASE_DIR, 'frontend', 'DASHBOARD.html'), 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content, mimetype='text/html')
    except Exception as e:
        logger.error(f"Error sirviendo DASHBOARD.html: {e}", exc_info=True)
        return Response(f'Error sirviendo DASHBOARD.html: {e}', status=500)

@app.route('/ADMIN_USUARIOS.html')
@login_required
def admin_usuarios():
    """Página de administración de usuarios"""
    return send_from_directory('frontend', 'ADMIN_USUARIOS.html')

@app.route('/perfil')
@login_required
def perfil():
    """Página de perfil de usuario"""
    return send_from_directory('frontend', 'perfil.html')

@app.route('/cambiar_password')
@login_required
def cambiar_password_page():
    """Página para cambiar contraseña"""
    return send_from_directory('frontend', 'cambiar_password.html')

@app.route('/solicitar_empresa')
@login_required
def solicitar_empresa():
    """Página para solicitar acceso a empresa"""
    return send_from_directory('frontend', 'solicitar_empresa.html')

@app.route('/crear_empresa')
@login_required
def crear_empresa_page():
    """Página para crear empresa"""
    return send_from_directory('frontend', 'crear_empresa.html')

@app.route('/conectar_banco')
@login_required
def conectar_banco_page():
    """Página para conectar banco con Plaid"""
    return send_from_directory('frontend', 'CONECTAR_BANCO.html')

@app.route('/extracto_bancario')
@login_required
def extracto_bancario_page():
    """Página para consultar extractos bancarios"""
    return send_from_directory('frontend', 'EXTRACTO_BANCARIO.html')

@app.route('/ADMIN_PERMISOS.html')
@login_required
@require_admin
def servir_admin_permisos():
    """Sirve la pantalla de administración de permisos (solo admins)"""
    try:
        with open(os.path.join(BASE_DIR, 'frontend', 'ADMIN_PERMISOS.html'), 'r', encoding='utf-8') as f:
            content = f.read()

        return content
    except Exception as e:
        logger.error(f"Error sirviendo ADMIN_PERMISOS.html: {e}")
        return "Error cargando página", 500

@app.route("/callback")
def callback():
    """Endpoint de callback para OAuth o integraciones externas (Tink)"""
    code = request.args.get("code")
    
    # Guardar el código en un archivo para fácil acceso
    if code:
        try:
            with open('/tmp/tink_code.txt', 'w') as f:
                f.write(code)
            logger.info(f"Código Tink guardado: {code}")
        except Exception as e:
            logger.error(f"Error guardando código: {e}")
    
    return f"<h1>OK</h1><p>code: {code}</p><p>Código guardado en /tmp/tink_code.txt</p>", 200

@app.route("/nordigen/callback")
def nordigen_callback():
    """Endpoint de callback para Nordigen (GoCardless)"""
    ref = request.args.get("ref")
    error = request.args.get("error")
    
    if error:
        logger.error(f"Error en callback de Nordigen: {error}")
        return f"""
        <html>
        <head><title>Error - Nordigen</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1 style="color: #c33;">❌ Error</h1>
            <p>Hubo un error en la autorización: {error}</p>
            <p><a href="/">Volver al inicio</a></p>
        </body>
        </html>
        """, 400
    
    if ref:
        try:
            with open('/tmp/nordigen_ref.txt', 'w') as f:
                f.write(ref)
            logger.info(f"Referencia de Nordigen guardada: {ref}")
        except Exception as e:
            logger.error(f"Error guardando referencia: {e}")
    
    return f"""
    <html>
    <head><title>Autorización Completada - Nordigen</title></head>
    <body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1 style="color: #3c3;">✅ Autorización Completada</h1>
        <p>Tu banco ha sido conectado exitosamente.</p>
        <p>Referencia: <code>{ref}</code></p>
        <hr style="margin: 30px auto; width: 300px;">
        <p>Puedes cerrar esta ventana.</p>
        <p><small>Para obtener tus transacciones, ejecuta:<br>
        <code>python3 setup_nordigen.py transactions</code></small></p>
    </body>
    </html>
    """, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=False)

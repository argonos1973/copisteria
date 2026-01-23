# -*- coding: utf-8 -*-
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file, session, make_response
from auth_middleware import superadmin_required, require_admin, login_required
import sqlite3
import os
import json
import re
import shutil
import subprocess
import tempfile
import uuid
from werkzeug.utils import secure_filename
from logger_config import get_logger
from email_utils import enviar_email_bienvenida_empresa
from utils_emisor import resetear_cache_emisor

logger = get_logger(__name__)

def es_nif_valido(nif):
    """Valida NIF/CIF/NIE español"""
    if not nif: return False
    nif = nif.upper().replace(' ', '').replace('-', '')
    
    # DNI/NIE
    if re.match(r'^[XYZ]?[0-9]{7,8}[A-Z]$', nif):
        nie = nif
        if nie.startswith('X'): nie = '0' + nie[1:]
        elif nie.startswith('Y'): nie = '1' + nie[1:]
        elif nie.startswith('Z'): nie = '2' + nie[1:]
        
        letras = "TRWAGMYFPDXBNJZSQVHLCKE"
        try:
            numero = int(nie[:-1])
            letra = nie[-1]
            return letra == letras[numero % 23]
        except:
            return False
    
    # CIF
    if re.match(r'^[ABCDEFGHJKLMNPQRSUVW][0-9]{7}[0-9A-J]$', nif):
        sum_val = 0
        for i in range(7):
            try:
                n = int(nif[i+1])
                if i % 2 == 0:
                    n *= 2
                    if n > 9: n = (n // 10) + (n % 10)
                sum_val += n
            except:
                return False
        
        control = (10 - (sum_val % 10)) % 10
        control_letras = "JABCDEFGHI"
        
        ultimo = nif[-1]
        if ultimo.isdigit():
            return int(ultimo) == control
        else:
            return ultimo == control_letras[control]
            
    return False


def convertir_tokens_a_legacy(theme_json):
    """Convierte formato nuevo (design tokens) a formato antiguo (color_x)"""
    
    def resolver_referencia(valor, context):
        """Resuelve referencias {palette.x} y {semantic.x}"""
        if not isinstance(valor, str):
            return valor
        
        match = re.match(r'^\{(.+)\}$', valor)
        if not match:
            return valor
        
        path = match.group(1).split('.')
        resolved = context
        for key in path:
            resolved = resolved.get(key) if isinstance(resolved, dict) else None
            if resolved is None:
                return valor
        
        # Recursivo por si la referencia apunta a otra referencia
        return resolver_referencia(resolved, context)
    
    # Mapeo de nuevo formato a antiguo
    legacy = {}
    ctx = theme_json
    
    # Mapeo directo
    mapping = {
        'color_app_bg': ['semantic', 'bg'],
        'color_primario': ['semantic', 'primary'],
        'color_secundario': ['semantic', 'bg-elevated'],
        'color_success': ['semantic', 'success'],
        'color_warning': ['semantic', 'warning'],
        'color_danger': ['semantic', 'danger'],
        'color_info': ['semantic', 'info'],
        'color_button': ['components', 'button', 'bg'],
        'color_button_hover': ['components', 'button', 'hover-bg'],
        'color_button_text': ['components', 'button', 'text'],
        'color_header_bg': ['components', 'header', 'bg'],
        'color_header_text': ['components', 'header', 'text'],
        'color_grid_header': ['components', 'table', 'header-bg'],
        'color_grid_header_text': ['components', 'table', 'header-text'],
        'color_grid_bg': ['components', 'table', 'bg'],
        'color_grid_text': ['components', 'table', 'text'],
        'color_grid_hover': ['components', 'table', 'row-hover'],
        'color_grid_border': ['components', 'table', 'border'],
        'color_input_bg': ['components', 'input', 'bg'],
        'color_input_text': ['components', 'input', 'text'],
        'color_input_border': ['components', 'input', 'border'],
        'color_select_bg': ['components', 'select', 'bg'],
        'color_select_text': ['components', 'select', 'text'],
        'color_select_border': ['components', 'select', 'border'],
        'color_modal_bg': ['components', 'modal', 'bg'],
        'color_modal_text': ['components', 'modal', 'text'],
        'color_modal_border': ['components', 'modal', 'border'],
        'color_modal_overlay': ['components', 'modal', 'overlay'],
        'color_modal_shadow': ['components', 'modal', 'shadow'],
        'color_submenu_bg': ['components', 'menu', 'bg'],
        'color_submenu_text': ['components', 'menu', 'text'],
        'color_submenu_hover': ['components', 'menu', 'hover'],
        'color_icon': ['components', 'icon', 'color'],
        'color_spinner_border': ['components', 'spinner', 'border'],
        'color_tab_active_bg': ['components', 'tab', 'active-bg'],
        'color_tab_active_text': ['components', 'tab', 'active-text'],
        'color_disabled_bg': ['components', 'disabled', 'bg'],
        'color_disabled_text': ['components', 'disabled', 'text']
    }
    
    for old_key, path in mapping.items():
        value = ctx
        for key in path:
            value = value.get(key) if isinstance(value, dict) else None
            if value is None:
                break
        
        if value is not None:
            legacy[old_key] = resolver_referencia(value, ctx)
    
    # Metadata
    if 'meta' in theme_json:
        legacy['nombre'] = theme_json.get('name', 'Custom')
        legacy['descripcion'] = theme_json['meta'].get('description', '')
        legacy['icon'] = theme_json['meta'].get('icon', '🎨')
    
    return legacy


empresas_bp = Blueprint('empresas', __name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_USUARIOS_PATH = '/var/www/html/db/usuarios_sistema.db'
DB_DIR = os.path.join(BASE_DIR, 'db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'logos')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}

def allowed_file(filename):
    """Verifica si el archivo tiene una extensión permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generar_codigo_empresa(nombre):
    """Genera código de empresa a partir del nombre (5 primeros caracteres, sin espacios)"""
    # Quitar acentos y caracteres especiales
    codigo = nombre.upper()
    codigo = re.sub(r'[ÁÀÄÂ]', 'A', codigo)
    codigo = re.sub(r'[ÉÈËÊ]', 'E', codigo)
    codigo = re.sub(r'[ÍÌÏÎ]', 'I', codigo)
    codigo = re.sub(r'[ÓÒÖÔ]', 'O', codigo)
    codigo = re.sub(r'[ÚÙÜÛ]', 'U', codigo)
    codigo = re.sub(r'[^A-Z0-9]', '', codigo)  # Solo letras y números
    return codigo[:5]  # Primeros 5 caracteres


def _ensure_batch_job_definitions(conn):
    items = [
        ('batchfacturasVencidas', 'Batch Facturas Vencidas (Emitidas)', 'batchFacturasVencidas', 900),
        ('batchPol', 'Batch POL (Proformas)', 'batchPol', 900),
        ('batchTotalDia', 'Total del día (Tickets + Facturas)', 'batchTotalDia', 300),
        ('batchScanFacturasRecibidas', 'Scanear Facturas Recibidas (OCR)', 'batchScanFacturasRecibidas', 1800),
        ('batchOptimizar', 'Optimizar BD (VACUUM/ANALYZE)', 'batchOptimizar', 1800),
        ('batchReindex', 'Reindexar BD (REINDEX)', 'batchOptimizar', 1800),
    ]
    for code, name, handler, timeout_sec in items:
        conn.execute(
            """
            UPDATE batch_job_definitions
            SET name = ?,
                handler = ?,
                timeout_sec = ?,
                concurrency_mode = 'per_empresa_single',
                active = 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE code = ?
            """,
            (name, handler, timeout_sec, code),
        )
        conn.execute(
            """
            INSERT INTO batch_job_definitions (code, name, handler, schema_json, timeout_sec, concurrency_mode, active)
            SELECT ?, ?, ?, NULL, ?, 'per_empresa_single', 1
            WHERE NOT EXISTS (SELECT 1 FROM batch_job_definitions WHERE code = ?)
            """,
            (code, name, handler, timeout_sec, code),
        )


def _ensure_default_batch_schedules_for_empresa(conn, empresa_id: int, user_id: int = None):
    defaults = [
        ('batchfacturasVencidas', '0 9 * * *', 0),
        # batchPol excluido - es un proceso personalizado
        ('batchTotalDia', '0 23 * * *', 0),
        ('batchScanFacturasRecibidas', '*/15 * * * *', 0),
        ('batchReindex', '0 2 * * *', 1),
        ('batchOptimizar', '0 3 * * *', 1),
    ]

    for job_code, cron_expr, enabled in defaults:
        job_def = conn.execute("SELECT id FROM batch_job_definitions WHERE code = ?", (job_code,)).fetchone()
        if not job_def:
            continue

        exists = conn.execute(
            "SELECT 1 FROM batch_job_schedules WHERE empresa_id = ? AND job_definition_id = ?",
            (empresa_id, job_def['id']),
        ).fetchone()
        if exists:
            continue

        conn.execute(
            """
            INSERT INTO batch_job_schedules
            (empresa_id, job_definition_id, enabled, cron_expr, timezone, params_json, created_by_usuario_id, updated_by_usuario_id)
            VALUES (?, ?, ?, ?, NULL, NULL, ?, ?)
            """,
            (empresa_id, job_def['id'], enabled, cron_expr, user_id, user_id),
        )

def clonar_estructura_bd(bd_origen, bd_destino):
    """Clona la estructura de una BD y copia datos maestros (provincia, codipostal)"""
    try:
        # Conectar a BD origen
        conn_origen = sqlite3.connect(bd_origen)
        cursor_origen = conn_origen.cursor()
        
        # Obtener esquema completo
        cursor_origen.execute("SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL")
        tablas = cursor_origen.fetchall()
        
        # Obtener índices
        cursor_origen.execute("SELECT sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL")
        indices = cursor_origen.fetchall()
        
        # Crear BD destino
        if os.path.exists(bd_destino):
            os.remove(bd_destino)
        
        conn_destino = sqlite3.connect(bd_destino)
        cursor_destino = conn_destino.cursor()
        
        # Crear tablas
        for tabla_sql, in tablas:
            try:
                cursor_destino.execute(tabla_sql)
            except Exception as e:
                logger.warning(f"Error creando tabla: {e}")
        
        # Crear índices
        for indice_sql, in indices:
            try:
                cursor_destino.execute(indice_sql)
            except Exception as e:
                logger.warning(f"Error creando índice: {e}")
        
        # Copiar datos de tablas maestras
        tablas_maestras = ['provincia', 'codipostal']
        for tabla in tablas_maestras:
            try:
                # Obtener datos de la tabla
                cursor_origen.execute(f"SELECT * FROM {tabla}")
                datos = cursor_origen.fetchall()
                
                if datos:
                    # Obtener nombres de columnas
                    cursor_origen.execute(f"PRAGMA table_info({tabla})")
                    columnas = [col[1] for col in cursor_origen.fetchall()]
                    placeholders = ','.join(['?' for _ in columnas])
                    
                    # Insertar datos
                    cursor_destino.executemany(
                        f"INSERT INTO {tabla} VALUES ({placeholders})",
                        datos
                    )
                    logger.info(f"Copiados {len(datos)} registros de tabla {tabla}")
            except Exception as e:
                logger.warning(f"Error copiando datos de tabla {tabla}: {e}")
        
        conn_destino.commit()
        conn_destino.close()
        conn_origen.close()
        
        logger.info(f"BD clonada exitosamente con datos maestros: {bd_destino}")
        return True
        
    except Exception as e:
        logger.error(f"Error clonando BD: {e}", exc_info=True)
        return False

# SELECT estándar con TODAS las columnas (20 total - sin color_*)
SELECT_EMPRESAS_FULL = """
    SELECT id, codigo, nombre, razon_social, cif, direccion, telefono, email, web,
           logo_header, logo_factura,
           codigo_postal, ciudad, provincia,
           activa, fecha_alta, fecha_modificacion,
           plantilla, plantilla_personalizada,
           db_path
    FROM empresas
"""

def _row_to_dict_full(row):
    """Convierte row con 20 columnas a diccionario completo (sin color_*)"""
    if not row:
        return None
    if len(row) != 20:
        logger.error(f"Row tiene {len(row)} columnas, se esperaban 20")
        return None
    
    return {
        'id': row[0],
        'codigo': row[1],
        'nombre': row[2],
        'razon_social': row[3],
        'cif': row[4],
        'direccion': row[5],
        'telefono': row[6],
        'email': row[7],
        'web': row[8],
        'logo_header': row[9],
        'logo_factura': row[10],
        'logo_url': f'/static/logos/{row[9]}' if row[9] else '/static/img/logo.png',
        'codigo_postal': row[11],
        'ciudad': row[12],
        'provincia': row[13],
        'activa': row[14],
        'fecha_alta': row[15],
        'fecha_modificacion': row[16],
        'plantilla': row[17],
        'plantilla_personalizada': row[18],
        'db_path': row[19]
    }

@empresas_bp.route('/api/empresas', methods=['GET'])
@require_admin
def listar_empresas():
    """Lista las empresas del usuario (solo sus empresas, excepto superadmin que ve todas)"""
    try:
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        user_id = session.get('user_id')
        es_superadmin = session.get('es_superadmin', False)
        
        if es_superadmin:
            # Superadmin ve todas las empresas
            cursor.execute(SELECT_EMPRESAS_FULL + " ORDER BY nombre")
        else:
            # Admin de empresa solo ve sus empresas
            query = f"""
                {SELECT_EMPRESAS_FULL}
                WHERE e.id IN (
                    SELECT empresa_id FROM usuario_empresa 
                    WHERE usuario_id = ?
                )
                ORDER BY e.nombre
            """
            cursor.execute(query, (user_id,))
        
        empresas = []
        for row in cursor.fetchall():
            empresa = _row_to_dict_full(row)
            if empresa:
                empresas.append(empresa)
        
        conn.close()
        logger.info(f"Usuario {session.get('username')} listó {len(empresas)} empresas")
        return jsonify(empresas), 200
        
    except Exception as e:
        logger.error(f"Error listando empresas: {e}", exc_info=True)
        return jsonify({'error': 'Error listando empresas'}), 500

@empresas_bp.route('/api/empresas/<int:empresa_id>', methods=['GET'])
@login_required
def obtener_empresa(empresa_id):
    """Obtiene datos de una empresa y su JSON de emisor"""
    try:
        user_id = session.get('user_id')
        es_superadmin = session.get('es_superadmin', False)
        
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        # Verificar que el usuario tenga acceso a esta empresa
        if not es_superadmin:
            cursor.execute('''
                SELECT COUNT(*) FROM usuario_empresa 
                WHERE usuario_id = ? AND empresa_id = ?
            ''', (user_id, empresa_id))
            if cursor.fetchone()[0] == 0:
                conn.close()
                logger.warning(f"Usuario {session.get('username')} intentó acceder a empresa {empresa_id} sin permiso")
                return jsonify({'error': 'No tienes permiso para ver esta empresa'}), 403
        
        cursor.execute(SELECT_EMPRESAS_FULL + " WHERE id = ?", (empresa_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'error': 'Empresa no encontrada'}), 404
        
        empresa = _row_to_dict_full(row)
        if not empresa:
            return jsonify({'error': 'Error procesando datos de empresa'}), 500
        
        # Cargar datos de emisor desde JSON
        codigo_empresa = empresa.get('codigo', '')
        emisor_json_path = os.path.join(BASE_DIR, 'emisores', f'{codigo_empresa}_emisor.json')
        
        logger.info(f"[LOGO DEBUG] Buscando emisor en: {emisor_json_path}")
        logger.info(f"[LOGO DEBUG] Código empresa: {codigo_empresa}")
        
        if os.path.exists(emisor_json_path):
            try:
                with open(emisor_json_path, 'r', encoding='utf-8') as f:
                    emisor_data = json.load(f)
                
                logger.info(f"[LOGO DEBUG] Emisor data cargado: {emisor_data}")
                
                # Sobrescribir con datos del JSON (tienen prioridad)
                empresa['cif'] = emisor_data.get('nif', empresa.get('cif', ''))
                empresa['razon_social'] = emisor_data.get('nombre', empresa.get('razon_social', ''))
                empresa['direccion'] = emisor_data.get('direccion', empresa.get('direccion', ''))
                empresa['codigo_postal'] = emisor_data.get('cp', empresa.get('codigo_postal', ''))
                empresa['ciudad'] = emisor_data.get('ciudad', empresa.get('ciudad', ''))
                empresa['provincia'] = emisor_data.get('provincia', empresa.get('provincia', ''))
                empresa['email'] = emisor_data.get('email', empresa.get('email', ''))
                empresa['pais'] = emisor_data.get('pais', 'ESP')
                empresa['ruta_certificado'] = emisor_data.get('certificado', '')

                empresa['verifactu_enabled'] = emisor_data.get('verifactu_enabled', False)
                
                # Incluir emisor_data completo para acceso al logo y otros campos
                empresa['emisor_data'] = emisor_data
                
                logger.info(f"[LOGO DEBUG] emisor_data incluido en respuesta: {empresa.get('emisor_data')}")
                logger.info(f"Datos de emisor cargados desde {emisor_json_path}")
            except Exception as e:
                logger.error(f"Error cargando JSON de emisor: {e}")
        else:
            logger.info(f"JSON de emisor no encontrado, usando datos de BD: {emisor_json_path}")
        
        return jsonify(empresa), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo empresa: {e}", exc_info=True)
        return jsonify({'error': 'Error obteniendo empresa'}), 500

@empresas_bp.route('/api/empresas/test', methods=['GET'])
def test_empresa():
    """Ruta de prueba sin decorador"""
    print("[DEBUG TEST] Ruta de test ejecutada", flush=True)
    return jsonify({'success': True, 'message': 'Test OK'}), 200

@empresas_bp.route('/api/empresas', methods=['POST'])
@login_required
def crear_empresa():
    """
    Crea una nueva empresa con su BD independiente
    """
    conn = None  # Inicializar conn al principio
    logger.error(f"[DEBUG CRITICAL] Función crear_empresa llamada - inicio")
    try:
        # Debug: log de datos recibidos
        logger.error(f"[DEBUG] Dentro del try - Iniciando crear_empresa")
        logger.info(f"[CREAR EMPRESA] Form data recibido: {dict(request.form)}")
        logger.info(f"[CREAR EMPRESA] Files recibidos: {list(request.files.keys())}")
        logger.error(f"[DEBUG] Datos recibidos OK")
        
        # Obtener datos del formulario
        nombre = request.form.get('nombre')
        cif = request.form.get('cif', '')
        razon_social = request.form.get('razon_social', nombre)  # Si no se proporciona, usa nombre
        direccion = request.form.get('direccion', '')
        codigo_postal = request.form.get('codigo_postal', '')
        ciudad = request.form.get('ciudad', '')
        provincia = request.form.get('provincia', '')
        telefono = request.form.get('telefono', '')
        email = request.form.get('email', '')
        web = request.form.get('web', '')
        
        logger.info(f"[CREAR EMPRESA] Nombre recibido: '{nombre}'")
        
        if not nombre:
            logger.warning(f"[CREAR EMPRESA] Nombre vacío o None")
            return jsonify({'error': 'El nombre de la empresa es obligatorio'}), 400
        
        # Generar código de empresa
        codigo = generar_codigo_empresa(nombre)
        print(f"[DEBUG] Código generado: {codigo}", flush=True)
        
        # Verificar que no exista otra empresa con ese código
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM empresas WHERE codigo = ?', (codigo,))
        if cursor.fetchone():
            conn.close()
            print(f"[DEBUG] Empresa {codigo} ya existe", flush=True)
            return jsonify({'error': f'Ya existe una empresa con código "{codigo}"'}), 400
        
        print(f"[DEBUG] Empresa {codigo} no existe, continuando...", flush=True)
        
        # Procesar logo si se subió
        logo_filename = None
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Renombrar con código de empresa
                ext = filename.rsplit('.', 1)[1].lower()
                logo_filename = f"{codigo}_logo.{ext}"
                file.save(os.path.join(UPLOAD_FOLDER, logo_filename))
                logger.info(f"Logo guardado: {logo_filename}")

        # Procesar certificado si se subió
        ruta_certificado_publico = ''
        
        # Verificar si viene ruta validada previamente
        if 'ruta_certificado' in request.form and request.form['ruta_certificado']:
            posible_ruta = request.form['ruta_certificado']
            if os.path.exists(posible_ruta):
                ruta_certificado_publico = posible_ruta
                logger.info(f"[CREAR EMPRESA] Usando ruta certificado existente: {ruta_certificado_publico}")
                # Intentar extraer CIF del certificado existente si no hay CIF
                try:
                    import subprocess
                    import re
                    # Extraer Subject
                    cmd = ['openssl', 'x509', '-in', ruta_certificado_publico, '-noout', '-subject', '-nameopt', 'RFC2253,utf8']
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        subject = result.stdout.strip()
                        match_nif = re.search(r'serialNumber=IDCES-([A-Z0-9]+)', subject, re.IGNORECASE)
                        if match_nif:
                            nif_cert = match_nif.group(1).strip()
                            if nif_cert and not cif:
                                cif = nif_cert
                                logger.info(f"[CREAR EMPRESA] Usando CIF del certificado existente: {cif}")
                except Exception as e:
                    logger.error(f"Error extrayendo info de certificado existente: {e}")
        
        if 'certificado' in request.files:
            cert_file = request.files['certificado']
            cert_pass = request.form.get('password_certificado', '')
            
            if cert_file and cert_file.filename:
                logger.info(f"[CREAR EMPRESA] Procesando certificado: {cert_file.filename}")
                try:
                    import tempfile
                    import subprocess
                    import uuid
                    import re
                    import shutil
                    
                    # Guardar temporalmente
                    fd, temp_path = tempfile.mkstemp(suffix='.p12')
                    os.close(fd)
                    cert_file.save(temp_path)
                    
                    # 1. Extraer Subject para NIF (OpenSSL)
                    cmd_info = ['openssl', 'pkcs12', '-in', temp_path, '-passin', f'pass:{cert_pass}', '-nokeys', '-clcerts']
                    p1 = subprocess.Popen(cmd_info, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    cmd2 = ['openssl', 'x509', '-noout', '-subject', '-nameopt', 'RFC2253,utf8']
                    p2 = subprocess.Popen(cmd2, stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    p1.stdout.close()
                    output, error = p2.communicate()
                    
                    nif_cert = ''
                    if p2.returncode == 0:
                        subject = output.decode('utf-8').strip()
                        # Extraer NIF
                        match_nif = re.search(r'serialNumber=IDCES-([A-Z0-9]+)', subject, re.IGNORECASE)
                        if match_nif:
                            nif_cert = match_nif.group(1).strip()
                        else:
                             # Fallback CN
                             match_nif_cn = re.search(r'\b([0-9]{8}[A-Z]|[XYZ][0-9]{7}[A-Z])\b', subject)
                             if match_nif_cn:
                                nif_cert = match_nif_cn.group(0)
                        
                        # Si encontramos NIF y el usuario no puso CIF, usarlo
                        if nif_cert and not cif:
                            cif = nif_cert
                            logger.info(f"[CREAR EMPRESA] Usando CIF del certificado: {cif}")

                    # 2. Generar PEMs
                    cert_dir = '/var/www/html/certs/empresas'
                    os.makedirs(cert_dir, exist_ok=True)
                    
                    base_filename = "".join([c for c in nif_cert if c.isalnum()]) if nif_cert else f"cert_{uuid.uuid4().hex}"
                    key_path = os.path.join(cert_dir, f"{base_filename}_key.pem")
                    cert_path = os.path.join(cert_dir, f"{base_filename}_cert.pem")
                    
                    # Extraer Key
                    subprocess.run(['openssl', 'pkcs12', '-in', temp_path, '-nocerts', '-out', key_path, '-nodes', '-passin', f'pass:{cert_pass}'], check=True, capture_output=True)
                    os.chmod(key_path, 0o600)
                    
                    # Extraer Cert
                    subprocess.run(['openssl', 'pkcs12', '-in', temp_path, '-clcerts', '-nokeys', '-out', cert_path, '-passin', f'pass:{cert_pass}'], check=True, capture_output=True)
                    
                    ruta_certificado_publico = cert_path
                    logger.info(f"[CREAR EMPRESA] Certificado guardado en: {cert_path}")
                    
                except Exception as e:
                    logger.error(f"Error procesando certificado en creación: {e}")
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
        
        # Validar que tengamos NIF (del formulario o del certificado)
        if not cif:
            logger.warning("[CREAR EMPRESA] Intento de creación sin NIF")
            return jsonify({'error': 'El NIF/CIF es obligatorio'}), 400

        # Validar formato NIF
        if not es_nif_valido(cif):
            logger.warning(f"[CREAR EMPRESA] NIF inválido: {cif}")
            return jsonify({'error': 'El NIF/CIF introducido no es válido'}), 400

        # Crear directorio para la empresa
        empresa_dir = os.path.join(DB_DIR, codigo)
        print(f"[DEBUG] Creando directorio: {empresa_dir}", flush=True)
        os.makedirs(empresa_dir, exist_ok=True)
        # Establecer permisos inmediatamente después de crear el directorio
        os.chmod(empresa_dir, 0o775)
        logger.info(f"Directorio creado para empresa: {empresa_dir}")
        print(f"[DEBUG] Directorio creado OK", flush=True)
        
        # Crear BD de la empresa dentro del subdirectorio
        bd_origen = os.path.join(DB_DIR, 'plantilla.db')
        bd_destino = os.path.join(empresa_dir, f'{codigo}.db')
        
        print(f"[DEBUG] BD origen: {bd_origen}, existe: {os.path.exists(bd_origen)}", flush=True)
        print(f"[DEBUG] BD destino: {bd_destino}", flush=True)
        
        if not os.path.exists(bd_origen):
            conn.close()
            print(f"[DEBUG ERROR] Plantilla no encontrada", flush=True)
            return jsonify({'error': 'BD plantilla (plantilla.db) no encontrada'}), 500
        
        # Clonar estructura
        print(f"[DEBUG] Iniciando clonación de BD...", flush=True)
        if not clonar_estructura_bd(bd_origen, bd_destino):
            conn.close()
            print(f"[DEBUG ERROR] Error clonando BD", flush=True)
            return jsonify({'error': 'Error clonando estructura de BD'}), 500
        
        print(f"[DEBUG] BD clonada exitosamente", flush=True)
        
        
        # Establecer permisos correctos en directorio y BD
        import subprocess
        try:
            # Cambiar propietario del directorio a www-data:www-data
            subprocess.run(['sudo', 'chown', '-R', 'www-data:www-data', empresa_dir], check=True)
            # Establecer permisos 775 al directorio (rwxrwxr-x)
            subprocess.run(['sudo', 'chmod', '775', empresa_dir], check=True)
            # Establecer permisos 664 a la BD (rw-rw-r--)
            subprocess.run(['sudo', 'chmod', '664', bd_destino], check=True)
            logger.info(f"Permisos establecidos correctamente para directorio: {empresa_dir}")
            logger.info(f"Permisos establecidos correctamente para BD: {bd_destino}")
        except Exception as perm_error:
            logger.warning(f"No se pudieron establecer permisos automáticamente: {perm_error}")
            logger.warning(f"Por favor, ejecute manualmente: sudo chown -R www-data:www-data {empresa_dir} && sudo chmod 775 {empresa_dir} && sudo chmod 664 {bd_destino}")

        # Inicializar numeradores en la nueva base de datos
        try:
            # Conectar a la BD recién creada
            conn_nueva = sqlite3.connect(bd_destino)
            cursor_nueva = conn_nueva.cursor()
            
            anio_actual = datetime.now().year
            # Tipos de documentos: Factura, Proforma, Ticket, Presupuesto (Offer), Rectificativa
            tipos_doc = ['F', 'P', 'T', 'O', 'R']
            
            # Asegurar que la tabla existe (por si la plantilla fuera antigua)
            cursor_nueva.execute('''
                CREATE TABLE IF NOT EXISTS "numerador" (
                    "id"    INTEGER PRIMARY KEY AUTOINCREMENT,
                    "tipo"  TEXT,
                    "numerador"     INTEGER,
                    "ejercicio"     INTEGER,
                    UNIQUE("ejercicio","tipo")
                )
            ''')
            
            for tipo in tipos_doc:
                # Verificar si ya existe
                cursor_nueva.execute('SELECT 1 FROM numerador WHERE tipo = ? AND ejercicio = ?', (tipo, anio_actual))
                if not cursor_nueva.fetchone():
                    cursor_nueva.execute('''
                        INSERT INTO numerador (tipo, numerador, ejercicio) 
                        VALUES (?, 0, ?)
                    ''', (tipo, anio_actual))
                    logger.info(f"Numerador inicializado: Tipo {tipo}, Año {anio_actual} -> 0")
            
            conn_nueva.commit()
            
            # Añadir producto LIBRE con año en curso
            cursor_nueva = conn_nueva.cursor()
            cursor_nueva.execute('''
                INSERT INTO productos (nombre, descripcion, subtotal, iva, impuestos, total, calculo_automatico, ejercicio)
                VALUES ('LIBRE', '', 0, 0, 21, 0, 0, ?)
            ''', (anio_actual,))
            conn_nueva.commit()
            logger.info(f"Producto LIBRE añadido para empresa {codigo}, ejercicio {anio_actual}")
            
            conn_nueva.close()
            logger.info(f"Numeradores inicializados para empresa {codigo}")
            
        except Exception as e:
            logger.error(f"Error inicializando numeradores/productos: {e}")
            # No bloqueamos la creación de la empresa, pero dejamos constancia
        
        # Insertar empresa en BD de usuarios (SIN COMMIT todavía)
        cursor.execute('''
            INSERT INTO empresas (
                codigo, nombre, razon_social, cif, direccion, codigo_postal, ciudad, provincia,
                telefono, email, web,
                logo_header, logo_factura,
                db_path, activa, fecha_alta
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'))
        ''', (
            codigo, nombre, razon_social, cif, direccion, codigo_postal, ciudad, provincia,
            telefono, email, web,
            logo_filename or '/public/assets/logo.svg', logo_filename or '/public/assets/logo.svg',
            bd_destino
        ))
        empresa_id = cursor.lastrowid
        # NO cerrar conexión todavía, la necesitamos para crear el usuario admin

        try:
            conn.row_factory = sqlite3.Row
            _ensure_batch_job_definitions(conn)
            _ensure_default_batch_schedules_for_empresa(conn, int(empresa_id), session.get('user_id'))
        except Exception as e:
            logger.warning(f"[CREAR EMPRESA] No se pudieron crear procesos batch por defecto: {e}")
        
        
        # Crear archivo emisor.json para la empresa
        import json
        emisor_data = {
            "nombre": razon_social or nombre,
            "nif": cif or "",
            "direccion": direccion or "",
            "cp": codigo_postal or "",
            "ciudad": ciudad or "",
            "provincia": provincia or "",
            "telefono": telefono or "",
            "email": email or "",
            "web": web or "",
            "certificado": ruta_certificado_publico,
            "db_path": bd_destino,
            "codigo": codigo
        }
        
        emisor_path = os.path.join(BASE_DIR, 'emisores', f'{codigo}_emisor.json')
        os.makedirs(os.path.dirname(emisor_path), exist_ok=True)
        
        with open(emisor_path, 'w', encoding='utf-8') as f:
            json.dump(emisor_data, f, ensure_ascii=False, indent=4)
        
        # Resetear caché de emisor
        resetear_cache_emisor(codigo)
        
        logger.info(f"Emisor JSON creado: {emisor_path}")
        
        # Asignar empresa al usuario actual (no crear nuevo usuario)
        usuario_actual_id = session.get('user_id')
        usuario_actual_username = session.get('username')
        
        if not usuario_actual_id:
            raise Exception("No hay usuario logueado")
        
        # Usar la misma conexión que ya tenemos abierta
        try:
            # Asignar la empresa al usuario actual como administrador
            cursor.execute('''
                INSERT INTO usuario_empresa (usuario_id, empresa_id, rol, es_admin_empresa)
                VALUES (?, ?, 'admin', 1)
            ''', (usuario_actual_id, empresa_id))
            logger.info(f"Empresa {codigo} asignada al usuario {usuario_actual_username}")
            
            # Asignar TODOS los permisos al usuario sobre esta empresa
            modulos = ['facturas', 'tickets', 'proformas', 'productos', 'contactos', 'presupuestos']
            
            for modulo in modulos:
                cursor.execute('''
                    INSERT INTO permisos_usuario_modulo 
                    (usuario_id, empresa_id, modulo_codigo, puede_ver, puede_crear, puede_editar, puede_eliminar, puede_anular, puede_exportar)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (usuario_actual_id, empresa_id, modulo, 1, 1, 1, 1, 1, 1))
            
            conn.commit()
            logger.info(f"Permisos completos asignados al usuario {usuario_actual_username} para empresa {codigo}")
            
        except sqlite3.IntegrityError as e:
            logger.warning(f"Error al asignar empresa al usuario: {e}")
            # Si el usuario ya tiene la empresa asignada, continuar
        finally:
            conn.close()
        
        logger.info(f"Empresa creada: {nombre} ({codigo}) - BD: {bd_destino}")
        logger.info(f"Empresa asignada al usuario: {usuario_actual_username}")
        
        # Actualizar sesión con la nueva empresa
        session['empresa_id'] = empresa_id
        session['empresa_codigo'] = codigo
        session['empresa_nombre'] = nombre
        session['empresa_db'] = bd_destino
        session['es_admin_empresa'] = True
        session['rol'] = 'admin'
        session['empresa_logo'] = logo_filename or '/public/assets/logo.svg'
        
        # Forzar persistencia de sesión
        session.permanent = True
        session.modified = True
        
        logger.info(f"Sesión actualizada con nueva empresa: {nombre} (ID: {empresa_id})")
        
        response_data = {
            'success': True,
            'empresa_id': empresa_id,
            'codigo': codigo,
            'nombre': nombre,
            'db_path': bd_destino,
            'usuario': usuario_actual_username,
            'mensaje': f'Empresa "{nombre}" creada exitosamente y asignada a tu usuario con todos los permisos.'
        }
        
        response = make_response(jsonify(response_data), 201)
        
        # Asegurar headers para manejo de cookies en CORS si fuera necesario
        origin = request.headers.get('Origin')
        if origin and 'trycloudflare.com' in origin:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            
        return response
        
    except Exception as e:
        print(f"[DEBUG ERROR] {type(e).__name__}: {e}", flush=True)
        import traceback
        traceback.print_exc()
        logger.error(f"Error creando empresa: {e}", exc_info=True)
        # Hacer rollback de la transacción si hay error
        try:
            if 'conn' in locals() and conn:
                conn.rollback()
                conn.close()
                logger.info("Rollback de transacción realizado")
        except (ValueError, TypeError):
            pass
        # Limpiar archivos si hubo error
        if 'logo_filename' in locals() and logo_filename and os.path.exists(os.path.join(UPLOAD_FOLDER, logo_filename)):
            os.remove(os.path.join(UPLOAD_FOLDER, logo_filename))
        if 'bd_destino' in locals() and bd_destino and os.path.exists(bd_destino):
            os.remove(bd_destino)
        if 'empresa_dir' in locals() and empresa_dir and os.path.exists(empresa_dir):
            import shutil
            shutil.rmtree(empresa_dir)
        if 'emisor_path' in locals() and emisor_path and os.path.exists(emisor_path):
            os.remove(emisor_path)
        return jsonify({'error': f'Error creando empresa: {str(e)}'}), 500


@empresas_bp.route('/api/empresas/<int:empresa_id>', methods=['PUT'])
@login_required
def actualizar_empresa(empresa_id):
    """Actualiza datos de empresa y guarda datos de emisor en JSON"""
    try:
        # SEGURIDAD: Verificar permisos
        es_superadmin = session.get('es_superadmin', False)
        user_id = session.get('user_id')
        
        # Verificar si el usuario tiene acceso a esta empresa
        if not es_superadmin:
            conn_check = sqlite3.connect(DB_USUARIOS_PATH)
            cursor_check = conn_check.cursor()
            cursor_check.execute('''
                SELECT es_admin_empresa FROM usuario_empresa 
                WHERE usuario_id = ? AND empresa_id = ?
            ''', (user_id, empresa_id))
            result = cursor_check.fetchone()
            conn_check.close()
            
            if not result or not result[0]:
                logger.warning(f"Usuario {session.get('username')} intentó modificar empresa {empresa_id} sin permisos")
                return jsonify({'error': 'No tienes permisos para modificar esta empresa'}), 403
        
        # Detectar si es FormData (con archivo) o JSON
        content_type = request.content_type
        
        if 'multipart/form-data' in content_type:
            # Viene con archivo (FormData)
            data = request.form.to_dict()
            logo_file = request.files.get('logo')
        else:
            # JSON puro
            data = request.get_json()
            logo_file = None
        
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        # Obtener código, nombre y db_path de empresa para el archivo JSON
        cursor.execute('SELECT codigo, nombre, db_path FROM empresas WHERE id = ?', (empresa_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({'error': 'Empresa no encontrada'}), 404
        
        codigo_empresa = row[0]
        nombre_empresa = row[1]
        db_path_empresa = row[2]
        
        # Procesar logo si viene archivo
        logo_path_relativa = None
        if logo_file and logo_file.filename:
            # Validar archivo
            if allowed_file(logo_file.filename):
                # Eliminar logos anteriores de esta empresa
                import glob
                old_logos = glob.glob(os.path.join(UPLOAD_FOLDER, f"{codigo_empresa}_logo.*"))
                for old_logo in old_logos:
                    try:
                        os.remove(old_logo)
                        logger.info(f"Logo anterior eliminado: {old_logo}")
                    except Exception as e:
                        logger.warning(f"No se pudo eliminar logo anterior {old_logo}: {e}")
                
                # Guardar nuevo logo
                ext = logo_file.filename.rsplit('.', 1)[1].lower()
                filename = f"{codigo_empresa}_logo.{ext}"
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                
                logo_file.save(filepath)
                logger.info(f"Logo actualizado para empresa {codigo_empresa}: {filename}")
                
                # Ruta relativa para el JSON
                logo_path_relativa = f"/static/logos/{filename}"
            else:
                conn.close()
                return jsonify({'error': 'Formato de archivo no permitido'}), 400
        
        # Construir datos de emisor para JSON
        emisor_data = {
            'nif': data.get('cif', ''),
            'nombre': data.get('razon_social', data.get('nombre', '')),
            'direccion': data.get('direccion', ''),
            'cp': data.get('codigo_postal', ''),
            'ciudad': data.get('ciudad', ''),
            'provincia': data.get('provincia', ''),
            'pais': 'ESP',
            'email': data.get('email', ''),
            'certificado': data.get('ruta_certificado', ''),
            'db_path': db_path_empresa,
            'codigo': codigo_empresa
        }

        if 'verifactu_enabled' in data:
            v = data.get('verifactu_enabled')
            if v in (True, 1, '1', 'true', 'True', 'on', 'ON', 'yes', 'YES'):
                emisor_data['verifactu_enabled'] = True
            elif v in (False, 0, '0', 'false', 'False', 'off', 'OFF', 'no', 'NO', None, ''):
                emisor_data['verifactu_enabled'] = False
            else:
                emisor_data['verifactu_enabled'] = bool(v)
        
        # Agregar logo si existe
        if logo_path_relativa:
            emisor_data['logo'] = logo_path_relativa
        
        # Guardar JSON de emisor
        emisor_json_path = os.path.join(BASE_DIR, 'emisores', f'{codigo_empresa}_emisor.json')
        try:
            with open(emisor_json_path, 'w', encoding='utf-8') as f:
                json.dump(emisor_data, f, indent=4, ensure_ascii=False)
            
            # Resetear caché de emisor
            resetear_cache_emisor(codigo_empresa)
            
            logger.info(f"Datos de emisor guardados en {emisor_json_path}")
        except Exception as e:
            logger.error(f"Error guardando JSON de emisor: {e}")
            conn.close()
            return jsonify({'error': f'Error guardando datos de emisor: {str(e)}'}), 500
        
        # Actualizar solo nombre y logo en BD (lo esencial para la app)
        campos_update = []
        valores = []
        
        # Solo guardar nombre y activa en BD
        if 'nombre' in data:
            campos_update.append("nombre = ?")
            valores.append(data['nombre'])
        
        if 'activa' in data:
            campos_update.append("activa = ?")
            valor = data['activa']
            if valor in ('on', 'true', '1', True, 1):
                valores.append(1)
            else:
                valores.append(0)
        
        # Agregar logo_header al update si se procesó
        if logo_path_relativa:
            campos_update.append("logo_header = ?")
            valores.append(filename)
        
        # Ejecutar UPDATE solo si hay campos para actualizar
        if campos_update:
            query = f"UPDATE empresas SET {', '.join(campos_update)} WHERE id = ?"
            valores.append(empresa_id)
            cursor.execute(query, valores)
            logger.info(f"Empresa {empresa_id} actualizada en BD")
        
        conn.commit()
        conn.close()
        
        logger.info(f"Empresa {empresa_id} y datos de emisor actualizados correctamente")
        
        return jsonify({
            'success': True, 
            'mensaje': 'Datos de empresa guardados correctamente',
            'emisor_json': f'{codigo_empresa}_emisor.json'
        }), 200
        
    except Exception as e:
        logger.error(f"Error actualizando empresa: {e}", exc_info=True)
        logger.error(f"Datos recibidos: empresa_id={empresa_id}, user_id={session.get('user_id')}, es_superadmin={session.get('es_superadmin')}")
        return jsonify({'error': f'Error actualizando empresa: {str(e)}'}), 500


@empresas_bp.route('/api/empresas/generar-colores', methods=['POST'])
@login_required
def generar_colores_automaticos():
    """Genera una paleta de colores armónica basada en el color primario"""
    try:
        data = request.get_json()
        color_primario = data.get('color_primario', '#2c3e50')
        
        # Generar paleta armónica
        palette = generate_palette(color_primario)
        
        logger.info(f"Paleta generada para color {color_primario}: {palette}")
        
        return jsonify(palette), 200
        
    except Exception as e:
        logger.error(f"Error generando colores: {e}", exc_info=True)
        return jsonify({'error': 'Error generando colores'}), 500


@empresas_bp.route('/api/empresas/<int:empresa_id>', methods=['DELETE'])
@login_required
def eliminar_empresa(empresa_id):
    """
    Elimina una empresa físicamente: BD, logo y emisor.json
    """
    try:
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        # Obtener datos de la empresa antes de eliminar
        cursor.execute('SELECT codigo, db_path, logo_header FROM empresas WHERE id = ?', (empresa_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return jsonify({'error': 'Empresa no encontrada'}), 404
        
        codigo, db_path, logo_header = row
        
        # Verificar que no sea la empresa por defecto
        if codigo == 'copisteria' or empresa_id == 1:
            conn.close()
            return jsonify({'error': 'No se puede eliminar la empresa principal'}), 400
        
        # Eliminar de la BD
        cursor.execute('DELETE FROM empresas WHERE id = ?', (empresa_id,))
        
        # Eliminar permisos asociados
        cursor.execute('DELETE FROM permisos_usuario_modulo WHERE empresa_id = ?', (empresa_id,))
        
        # Eliminar asociaciones usuario-empresa
        cursor.execute('DELETE FROM usuario_empresa WHERE empresa_id = ?', (empresa_id,))
        
        conn.commit()
        conn.close()
        
        # Eliminar archivos físicos
        archivos_eliminados = []
        
        # Eliminar directorio completo de la empresa (incluye BD y otros archivos)
        empresa_dir = os.path.join(DB_DIR, codigo)
        if os.path.exists(empresa_dir) and os.path.isdir(empresa_dir):
            shutil.rmtree(empresa_dir)
            archivos_eliminados.append(f'Directorio: {codigo}/')
            logger.info(f"Directorio de empresa eliminado: {empresa_dir}")
        elif db_path and os.path.exists(db_path):
            # Fallback: si no existe el directorio pero existe la BD antigua (migración)
            os.remove(db_path)
            archivos_eliminados.append(f'BD: {os.path.basename(db_path)}')
            logger.info(f"BD eliminada (antigua estructura): {db_path}")
        
        # Eliminar logo
        if logo_header and not logo_header.startswith('default_'):
            logo_path = os.path.join(UPLOAD_FOLDER, logo_header)
            if os.path.exists(logo_path):
                os.remove(logo_path)
                archivos_eliminados.append(f'Logo: {logo_header}')
                logger.info(f"Logo eliminado: {logo_path}")
        
        # Eliminar emisor.json
        emisor_path = os.path.join(BASE_DIR, 'emisores', f'{codigo}_emisor.json')
        if os.path.exists(emisor_path):
            os.remove(emisor_path)
            archivos_eliminados.append(f'Emisor: {codigo}_emisor.json')
            logger.info(f"Emisor eliminado: {emisor_path}")
        
        logger.info(f"Empresa {empresa_id} ({codigo}) eliminada completamente")
        
        return jsonify({
            'success': True, 
            'mensaje': f'Empresa eliminada completamente',
            'archivos_eliminados': archivos_eliminados
        }), 200
        
    except Exception as e:
        logger.error(f"Error eliminando empresa: {e}", exc_info=True)
        return jsonify({'error': 'Error eliminando empresa'}), 500

# ENDPOINT /colores ELIMINADO - Ya no se usan colores en BD, solo plantillas JSON

@empresas_bp.route('/api/empresas/<int:empresa_id>/emisor', methods=['PUT'])
@login_required
def actualizar_emisor(empresa_id):
    """Actualiza el archivo emisor.json de una empresa"""
    try:
        data = request.get_json()
        
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT codigo, db_path FROM empresas WHERE id = ?', (empresa_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'error': 'Empresa no encontrada'}), 404
        
        codigo = row[0]
        db_path = row[1]
        
        # Actualizar emisor.json
        emisor_data = {
            "nombre": data.get('razon_social', data.get('nombre', '')),
            "nif": data.get('cif', ''),
            "direccion": data.get('direccion', ''),
            "cp": data.get('codigo_postal', ''),
            "ciudad": data.get('ciudad', ''),
            "provincia": data.get('provincia', ''),
            "telefono": data.get('telefono', ''),
            "email": data.get('email', ''),
            "web": data.get('web', ''),
            "db_path": db_path,
            "codigo": codigo
        }
        
        emisor_path = os.path.join(BASE_DIR, 'emisores', f'{codigo}_emisor.json')
        
        with open(emisor_path, 'w', encoding='utf-8') as f:
            json.dump(emisor_data, f, ensure_ascii=False, indent=4)
        
        # Resetear caché de emisor
        resetear_cache_emisor(codigo)
        
        logger.info(f"Emisor JSON actualizado: {emisor_path}")
        
        return jsonify({'success': True, 'mensaje': 'Emisor actualizado'}), 200
        
    except Exception as e:
        logger.error(f"Error actualizando emisor: {e}", exc_info=True)
        return jsonify({'error': 'Error actualizando emisor'}), 500


@empresas_bp.route('/api/empresas/procesar_certificado', methods=['POST', 'OPTIONS'])
@login_required
def procesar_certificado():
    if request.method == 'OPTIONS':
        return '', 200
        
    logger.info("➡️ [CERT] Inicio procesar_certificado")
    try:
        if 'certificado' not in request.files:
            logger.error("[CERT] No hay certificado en request.files")
            return jsonify({'error': 'No se ha subido ningún certificado'}), 400
            
        archivo = request.files['certificado']
        password = request.form.get('password', '')
        codigo_empresa = request.form.get('codigo_empresa', '')
        
        logger.info(f"[CERT] Archivo: {archivo.filename}, PassLen: {len(password)}, Empresa: {codigo_empresa}")
        
        if not archivo or archivo.filename == '':
            return jsonify({'error': 'Archivo inválido'}), 400
            
        # Guardar temporalmente
        fd, temp_path = tempfile.mkstemp(suffix='.p12')
        os.close(fd)
        logger.info(f"[CERT] Temp path: {temp_path}")
        archivo.save(temp_path)
        
        try:
            # Usar OpenSSL para extraer info
            logger.info("[CERT] Ejecutando OpenSSL pkcs12...")
            # Extraer Subject
            cmd = ['openssl', 'pkcs12', '-in', temp_path, '-passin', f'pass:{password}', '-nokeys', '-clcerts']
            # Usar communicate para evitar deadlocks y timeouts
            p1 = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            cmd2 = ['openssl', 'x509', '-noout', '-subject', '-nameopt', 'RFC2253,utf8'] # utf8 para caracteres especiales
            p2 = subprocess.Popen(cmd2, stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p1.stdout.close()
            output, error = p2.communicate()
            
            logger.info(f"[CERT] OpenSSL returncode: {p2.returncode}")
            
            if p2.returncode != 0:
                # Probablemente contraseña incorrecta
                error_msg = error.decode('utf-8') if error else "Error desconocido"
                logger.error(f"[CERT] Error OpenSSL: {error_msg}")
                return jsonify({'error': 'Error procesando certificado. Verifique la contraseña.'}), 400
                
            subject = output.decode('utf-8').strip()
            logger.info(f"[CERT] Certificado subject: {subject}")
            
            # Parsear CN y SerialNumber (NIF)
            nif = ''
            razon_social = ''
            
            # Extraer NIF de serialNumber (IDCES-...)
            match_nif = re.search(r'serialNumber=IDCES-([A-Z0-9]+)', subject, re.IGNORECASE)
            if match_nif:
                nif = match_nif.group(1).strip()
            
            # Extraer Razón Social de CN
            match_cn = re.search(r'CN=([^,]+)', subject, re.IGNORECASE)
            if match_cn:
                cn_full = match_cn.group(1).strip()
                if ' - ' in cn_full:
                    razon_social = cn_full.split(' - ')[0]
                else:
                    razon_social = cn_full
            
            # Si no hay NIF en serialNumber, buscar en CN
            if not nif:
                match_nif_cn = re.search(r'\b([0-9]{8}[A-Z]|[XYZ][0-9]{7}[A-Z])\b', subject)
                if match_nif_cn:
                    nif = match_nif_cn.group(0)
            
            logger.info(f"[CERT] Respuesta JSON: nif='{nif}', razon_social='{razon_social}'")
            
            # GENERAR ARCHIVOS PEM (Key y Cert)
            cert_dir = '/var/www/html/certs/empresas'
            os.makedirs(cert_dir, exist_ok=True)
            
            if nif:
                safe_nif = "".join([c for c in nif if c.isalnum()])
                base_filename = safe_nif
            else:
                base_filename = f"cert_{uuid.uuid4().hex}"
            
            key_filename = f"{base_filename}_key.pem"
            cert_filename = f"{base_filename}_cert.pem"
            
            key_path = os.path.join(cert_dir, key_filename)
            cert_path = os.path.join(cert_dir, cert_filename)
            
            try:
                # Extraer Clave Privada
                cmd_key = ['openssl', 'pkcs12', '-in', temp_path, '-nocerts', '-out', key_path, '-nodes', '-passin', f'pass:{password}']
                subprocess.run(cmd_key, check=True, capture_output=True)
                os.chmod(key_path, 0o600) # Permisos seguros
                
                # Extraer Certificado Público
                cmd_cert = ['openssl', 'pkcs12', '-in', temp_path, '-clcerts', '-nokeys', '-out', cert_path, '-passin', f'pass:{password}']
                subprocess.run(cmd_cert, check=True, capture_output=True)
                
                logger.info(f"[CERT] PEMs generados: Key={key_path}, Cert={cert_path}")
                
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr.decode('utf-8') if e.stderr else str(e)
                logger.error(f"[CERT] Error generando PEMs: {error_msg}")
                return jsonify({'error': 'Error extrayendo claves del certificado'}), 500

            return jsonify({
                'nif': nif, 
                'razon_social': razon_social,
                'ruta_certificado': cert_path # Devolvemos la ruta del certificado público
            })
            
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        logger.error(f"Excepción procesando certificado: {e}")
        return jsonify({'error': str(e)}), 500

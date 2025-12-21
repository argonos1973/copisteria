"""
Rutas de sistema (configuración, versión, debug, utilidades)
"""

import os
from flask import Blueprint, jsonify, request, Response, send_file, send_from_directory
from auth_middleware import login_required
from logger_config import get_logger
from db_utils import get_db_connection
from services.common_services import format_date
import csv
from datetime import datetime
import tickets
import factura

logger = get_logger('aleph70.system_routes')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_VERSION = '1.2.8'

# Blueprint para las rutas de sistema
system_bp = Blueprint('system', __name__)

@system_bp.route('/')
def index():
    """Redirige la raíz a public/index.html"""
    from flask import redirect
    return redirect('/public/index.html')

@system_bp.route('/favicon.ico')
def favicon():
    """Sirve el favicon"""
    return send_from_directory(os.path.join(BASE_DIR, 'static'), 'favicon.ico', mimetype='image/x-icon')

@system_bp.route('/public/<path:filename>')
def serve_public_files(filename):
    """Sirve archivos estáticos desde la carpeta public"""
    public_dir = os.path.join(BASE_DIR, 'public')
    return send_from_directory(public_dir, filename)

@system_bp.route('/<path:filename>')
def serve_frontend_files(filename):
    """Sirve archivos HTML estáticos desde la carpeta frontend"""
    from flask import make_response

    # Ignorar rutas de API (las manejan otros blueprints)
    if filename.startswith('api/'):
        return jsonify({'error': 'Recurso no encontrado', 'status': 404}), 404
    
    frontend_dir = os.path.join(BASE_DIR, 'frontend')
    file_to_serve = None
    
    # Si termina en .html, servir directamente
    if filename.endswith('.html'):
        if os.path.exists(os.path.join(frontend_dir, filename)):
            file_to_serve = filename
    else:
        # Si no tiene extensión, intentar añadir .html
        html_filename = filename + '.html'
        if os.path.exists(os.path.join(frontend_dir, html_filename)):
            file_to_serve = html_filename
            
    if file_to_serve:
        response = make_response(send_from_directory(frontend_dir, file_to_serve))
        # Deshabilitar caché para asegurar que se ven los cambios
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    
    # Si no es HTML o no existe, devolver 404 (dejando que otros blueprints manejen sus rutas)
    return jsonify({'error': 'Recurso no encontrado', 'status': 404}), 404

@system_bp.route('/config.json', methods=['GET'])
def servir_config_json():
    """Sirve el archivo config.json"""
    try:
        ruta = os.path.join(BASE_DIR, 'config.json')
        return send_file(ruta, as_attachment=False, mimetype='application/json')
    except Exception as e:
        logger.error(f"Error sirviendo config.json: {e}")
        return Response(f'Error sirviendo config.json: {e}', status=500)


@system_bp.route('/api/version', methods=['GET'])
def obtener_version():
    """Retorna la versión de la aplicación"""
    return jsonify({
        'version': APP_VERSION,
        'timestamp': datetime.now().isoformat()
    })


@login_required
@system_bp.route('/api/imprimir-ticket.html', methods=['GET'])
def servir_imprimir_ticket_html():
    """Sirve la página de impresión del ticket con el logo de la empresa"""
    try:
        ruta = os.path.join(BASE_DIR, 'frontend', 'imprimir-ticket.html')
        with open(ruta, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Aquí se puede personalizar el HTML con datos de la empresa
        # Por ejemplo, reemplazar placeholders con logos, datos, etc.
        
        return Response(contenido, mimetype='text/html')
        
    except FileNotFoundError:
        logger.error(f"Archivo no encontrado: {ruta}")
        return Response('Archivo imprimir-ticket.html no encontrado', status=404)
    except Exception as e:
        logger.error(f"Error sirviendo imprimir-ticket.html: {e}")
        return Response(f'Error sirviendo imprimir-ticket.html: {e}', status=500)


@system_bp.route('/api/test-reload', methods=['GET'])
def test_reload():
    """Endpoint de prueba para verificar recargas del servidor"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'mensaje': 'Servidor funcionando correctamente'
    })


@system_bp.route('/api/exportar', methods=['GET'])
def exportar():
    """Exporta datos de tickets y facturas a CSV"""
    try:
        # Obtener parámetros de la consulta
        ejercicio = request.args.get('ejercicio')
        trimestre = request.args.get('trimestre')
        mes = request.args.get('mes')
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        formato = request.args.get('formato', 'csv').lower()
        
        # Validar parámetros
        if not ejercicio:
            return jsonify({'error': 'Ejercicio es requerido'}), 400
        
        try:
            ejercicio = int(ejercicio)
        except ValueError:
            return jsonify({'error': 'Ejercicio debe ser un número'}), 400
        
        # Construir fechas de búsqueda
        if fecha_inicio and fecha_fin:
            # Usar fechas específicas
            pass
        elif trimestre:
            # Calcular fechas del trimestre
            try:
                trimestre = int(trimestre)
                if trimestre == 1:
                    fecha_inicio = f"{ejercicio}-01-01"
                    fecha_fin = f"{ejercicio}-03-31"
                elif trimestre == 2:
                    fecha_inicio = f"{ejercicio}-04-01"
                    fecha_fin = f"{ejercicio}-06-30"
                elif trimestre == 3:
                    fecha_inicio = f"{ejercicio}-07-01"
                    fecha_fin = f"{ejercicio}-09-30"
                elif trimestre == 4:
                    fecha_inicio = f"{ejercicio}-10-01"
                    fecha_fin = f"{ejercicio}-12-31"
                else:
                    return jsonify({'error': 'Trimestre debe ser 1-4'}), 400
            except ValueError:
                return jsonify({'error': 'Trimestre debe ser un número'}), 400
        elif mes:
            # Calcular fechas del mes
            try:
                mes = int(mes)
                if mes < 1 or mes > 12:
                    return jsonify({'error': 'Mes debe estar entre 1-12'}), 400
                
                # Calcular último día del mes
                if mes in [1, 3, 5, 7, 8, 10, 12]:
                    ultimo_dia = 31
                elif mes in [4, 6, 9, 11]:
                    ultimo_dia = 30
                else:  # febrero
                    # Año bisiesto
                    if (ejercicio % 4 == 0 and ejercicio % 100 != 0) or (ejercicio % 400 == 0):
                        ultimo_dia = 29
                    else:
                        ultimo_dia = 28
                
                fecha_inicio = f"{ejercicio}-{mes:02d}-01"
                fecha_fin = f"{ejercicio}-{mes:02d}-{ultimo_dia}"
                
            except ValueError:
                return jsonify({'error': 'Mes debe ser un número'}), 400
        else:
            # Todo el ejercicio
            fecha_inicio = f"{ejercicio}-01-01"
            fecha_fin = f"{ejercicio}-12-31"
        
        # ================ 1) CONSULTA TICKETS =====================
        logger.info("Consultando tickets...")
        tickets_data = []
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                query_tickets = '''
                    SELECT fecha, numero, importe_bruto, importe_impuestos, 
                           importe_cobrado, total
                    FROM tickets 
                    WHERE fecha BETWEEN ? AND ?
                    ORDER BY fecha
                '''
                
                cursor.execute(query_tickets, (fecha_inicio, fecha_fin))
                tickets_raw = cursor.fetchall()
                
                for t in tickets_raw:
                    tickets_data.append({
                        'fecha': format_date(t[0]) if t[0] else '',
                        'numero': t[1] or '',
                        'nif': '',
                        'razonSocial': '',
                        'importe_bruto': float(t[2]) if t[2] else 0.0,
                        'importe_impuestos': float(t[3]) if t[3] else 0.0,
                        'importe_cobrado': float(t[4]) if t[4] else 0.0,
                        'total': float(t[5]) if t[5] else 0.0
                    })
                
        except Exception as e:
            logger.error(f"Error consultando tickets: {e}")
            tickets_data = []
        
        # ================ 2) CONSULTA FACTURAS =====================
        logger.info("Consultando facturas...")
        facturas_data = []
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                query_facturas = '''
                    SELECT f.fecha, f.numero, f.nif, c.razonsocial,
                           f.importe_bruto, f.importe_impuestos, 
                           f.importe_cobrado, f.total
                    FROM factura f
                    LEFT JOIN contactos c ON f.idcontacto = c.idContacto
                    WHERE f.fecha BETWEEN ? AND ?
                    ORDER BY f.fecha
                '''
                
                cursor.execute(query_facturas, (fecha_inicio, fecha_fin))
                facturas_raw = cursor.fetchall()
                
                for f in facturas_raw:
                    facturas_data.append({
                        'fecha': format_date(f[0]) if f[0] else '',
                        'numero': f[1] or '',
                        'nif': f[2] or '',
                        'razonSocial': f[3] or '',
                        'importe_bruto': float(f[4]) if f[4] else 0.0,
                        'importe_impuestos': float(f[5]) if f[5] else 0.0,
                        'importe_cobrado': float(f[6]) if f[6] else 0.0,
                        'total': float(f[7]) if f[7] else 0.0
                    })
                
        except Exception as e:
            logger.error(f"Error consultando facturas: {e}")
            facturas_data = []
        
        # ================ 3) UNIFICAR DATOS =====================
        # Primero tickets ordenados por fecha, luego facturas ordenadas por fecha
        todos_los_datos = tickets_data + facturas_data
        
        # ================ 4) GENERAR ARCHIVO =====================
        if formato == 'csv':
            # Generar CSV
            output = []
            
            # Cabeceras según formato correcto
            cabeceras = [
                'fecha', 'numero', 'nif', 'razonSocial',
                'importe_bruto', 'importe_impuestos', 'importe_cobrado', 'total'
            ]
            output.append(cabeceras)
            
            # Datos
            for item in todos_los_datos:
                fila = [
                    item['fecha'],
                    item['numero'],
                    item['nif'],
                    item['razonSocial'],
                    item['importe_bruto'],
                    item['importe_impuestos'],
                    item['importe_cobrado'],
                    item['total']
                ]
                output.append(fila)
            
            # Crear respuesta CSV con separador decimal coma y 2 decimales
            def format_cell(cell):
                if isinstance(cell, float):
                    return f"{cell:.2f}".replace('.', ',')
                return str(cell)
            
            def generate():
                for row in output:
                    yield ';'.join([format_cell(cell) for cell in row]) + '\n'
            
            # Nombre del archivo
            nombre_archivo = f"exportacion_{ejercicio}"
            if trimestre:
                nombre_archivo += f"_T{trimestre}"
            elif mes:
                nombre_archivo += f"_M{mes:02d}"
            nombre_archivo += f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            return Response(
                generate(),
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename={nombre_archivo}',
                    'Content-Type': 'text/csv; charset=utf-8'
                }
            )
            
        else:
            # Formato JSON
            return jsonify({
                'success': True,
                'ejercicio': ejercicio,
                'periodo': {
                    'fecha_inicio': fecha_inicio,
                    'fecha_fin': fecha_fin,
                    'trimestre': trimestre,
                    'mes': mes
                },
                'resumen': {
                    'total_tickets': len(tickets_data),
                    'total_facturas': len(facturas_data),
                    'total_registros': len(todos_los_datos),
                    'total_importe_tickets': sum(t['total'] for t in tickets_data),
                    'total_importe_facturas': sum(f['total'] for f in facturas_data)
                },
                'datos': todos_los_datos
            })
        
    except Exception as e:
        logger.error(f"Error en exportación: {e}")
        return jsonify({'error': str(e)}), 500


@system_bp.route('/api/exportar-recibidas', methods=['GET'])
def exportar_recibidas():
    """Exporta facturas recibidas (gastos) a CSV"""
    try:
        ejercicio = request.args.get('ejercicio')
        trimestre = request.args.get('trimestre')
        
        if not ejercicio:
            return jsonify({'error': 'Ejercicio es requerido'}), 400
        
        try:
            ejercicio = int(ejercicio)
        except ValueError:
            return jsonify({'error': 'Ejercicio debe ser un número'}), 400
        
        # Construir fechas según trimestre
        if trimestre and trimestre != 'todos':
            try:
                trimestre = int(trimestre)
                if trimestre == 1:
                    fecha_inicio = f"{ejercicio}-01-01"
                    fecha_fin = f"{ejercicio}-03-31"
                elif trimestre == 2:
                    fecha_inicio = f"{ejercicio}-04-01"
                    fecha_fin = f"{ejercicio}-06-30"
                elif trimestre == 3:
                    fecha_inicio = f"{ejercicio}-07-01"
                    fecha_fin = f"{ejercicio}-09-30"
                elif trimestre == 4:
                    fecha_inicio = f"{ejercicio}-10-01"
                    fecha_fin = f"{ejercicio}-12-31"
                else:
                    return jsonify({'error': 'Trimestre debe ser 1-4'}), 400
            except ValueError:
                return jsonify({'error': 'Trimestre debe ser un número'}), 400
        else:
            fecha_inicio = f"{ejercicio}-01-01"
            fecha_fin = f"{ejercicio}-12-31"
        
        # Consultar gastos (facturas recibidas)
        logger.info(f"Exportando facturas recibidas: {fecha_inicio} a {fecha_fin}")
        gastos_data = []
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Detectar estructura de tabla gastos
                cursor.execute("PRAGMA table_info(gastos)")
                columnas = [col[1] for col in cursor.fetchall()]
                
                if 'fecha_operacion' in columnas:
                    # Estructura con fecha_operacion (formato DD/MM/YYYY)
                    # JOIN con facturas_proveedores y proveedores para obtener NIF e IVA
                    query = '''
                        SELECT g.fecha_operacion, g.concepto, g.razon_social, ABS(g.importe_eur), p.nif,
                               COALESCE(fp.base_imponible, 0) as base, COALESCE(fp.iva_importe, 0) as iva
                        FROM gastos g
                        LEFT JOIN facturas_proveedores fp ON g.factura_proveedor_id = fp.id
                        LEFT JOIN proveedores p ON fp.proveedor_id = p.id
                        WHERE substr(g.fecha_operacion, 7, 4) || '-' || substr(g.fecha_operacion, 4, 2) || '-' || substr(g.fecha_operacion, 1, 2) BETWEEN ? AND ?
                        ORDER BY substr(g.fecha_operacion, 7, 4) || '-' || substr(g.fecha_operacion, 4, 2) || '-' || substr(g.fecha_operacion, 1, 2)
                    '''
                    cursor.execute(query, (fecha_inicio, fecha_fin))
                    for row in cursor.fetchall():
                        base = float(row[5]) if row[5] else 0.0
                        iva = float(row[6]) if row[6] else 0.0
                        total = float(row[3]) if row[3] else 0.0
                        # Si no hay base/iva de factura_proveedor, usar el total como base
                        if base == 0 and iva == 0 and total > 0:
                            base = total
                        gastos_data.append({
                            'fecha': row[0] if row[0] else '',
                            'numero': '',
                            'nif': row[4] or '',
                            'razonSocial': row[2] or row[1] or '',
                            'importe_bruto': round(base, 2),
                            'importe_impuestos': round(iva, 2),
                            'importe_cobrado': 0.0,
                            'total': round(total, 2)
                        })
                elif 'fecha_operacion_iso' in columnas:
                    # Estructura con fecha ISO
                    query = '''
                        SELECT fecha_operacion_iso, concepto, razon_social, importe_eur
                        FROM gastos 
                        WHERE fecha_operacion_iso BETWEEN ? AND ?
                        ORDER BY fecha_operacion_iso
                    '''
                    cursor.execute(query, (fecha_inicio, fecha_fin))
                    for row in cursor.fetchall():
                        gastos_data.append({
                            'fecha': format_date(row[0]) if row[0] else '',
                            'numero': '',
                            'nif': '',
                            'razonSocial': row[2] or row[1] or '',
                            'importe_bruto': float(row[3]) if row[3] else 0.0,
                            'importe_impuestos': 0.0,
                            'importe_cobrado': 0.0,
                            'total': float(row[3]) if row[3] else 0.0
                        })
                elif 'fecha' in columnas:
                    # Estructura simple
                    query = '''
                        SELECT fecha, concepto, proveedor, importe
                        FROM gastos 
                        WHERE fecha BETWEEN ? AND ?
                        ORDER BY fecha
                    '''
                    cursor.execute(query, (fecha_inicio, fecha_fin))
                    for row in cursor.fetchall():
                        gastos_data.append({
                            'fecha': format_date(row[0]) if row[0] else '',
                            'numero': '',
                            'nif': '',
                            'razonSocial': row[2] or row[1] or '',
                            'importe_bruto': float(row[3]) if row[3] else 0.0,
                            'importe_impuestos': 0.0,
                            'importe_cobrado': 0.0,
                            'total': float(row[3]) if row[3] else 0.0
                        })
                        
        except Exception as e:
            logger.error(f"Error consultando gastos: {e}")
            gastos_data = []
        
        # Generar CSV
        output = []
        cabeceras = ['fecha', 'numero', 'nif', 'razonSocial', 
                     'importe_bruto', 'importe_impuestos', 'importe_cobrado', 'total']
        output.append(cabeceras)
        
        for item in gastos_data:
            fila = [
                item['fecha'],
                item['numero'],
                item['nif'],
                item['razonSocial'],
                item['importe_bruto'],
                item['importe_impuestos'],
                item['importe_cobrado'],
                item['total']
            ]
            output.append(fila)
        
        # Formato con separador ; y decimal ,
        def format_cell(cell):
            if isinstance(cell, float):
                return f"{cell:.2f}".replace('.', ',')
            return str(cell)
        
        def generate():
            for row in output:
                yield ';'.join([format_cell(cell) for cell in row]) + '\n'
        
        nombre_archivo = f"facturas_recibidas_{ejercicio}"
        if trimestre and trimestre != 'todos':
            nombre_archivo += f"_T{trimestre}"
        nombre_archivo += f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return Response(
            generate(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename={nombre_archivo}',
                'Content-Type': 'text/csv; charset=utf-8'
            }
        )
        
    except Exception as e:
        logger.error(f"Error en exportación recibidas: {e}")
        return jsonify({'error': str(e)}), 500


@system_bp.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint de health check"""
    try:
        # Verificar conexión a base de datos
        with get_db_connection() as conn:
            if conn:
                db_status = 'ok'
            else:
                db_status = 'error'
        
        return jsonify({
            'status': 'ok',
            'version': APP_VERSION,
            'timestamp': datetime.now().isoformat(),
            'database': db_status,
            'uptime': 'running'
        })
        
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

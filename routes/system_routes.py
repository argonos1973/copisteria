"""
Rutas de sistema (configuración, versión, debug, utilidades)
"""

import os
from flask import Blueprint, jsonify, request, Response, send_file
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
                    SELECT id, fecha, total, observaciones, timestamp
                    FROM tickets 
                    WHERE fecha BETWEEN ? AND ?
                    ORDER BY fecha, timestamp
                '''
                
                cursor.execute(query_tickets, (fecha_inicio, fecha_fin))
                tickets_raw = cursor.fetchall()
                
                for ticket in tickets_raw:
                    tickets_data.append({
                        'tipo': 'TICKET',
                        'id': ticket[0],
                        'fecha': format_date(ticket[1]) if ticket[1] else '',
                        'total': float(ticket[2]) if ticket[2] else 0.0,
                        'observaciones': ticket[3] or '',
                        'timestamp': ticket[4]
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
                    SELECT f.id, f.fecha, f.total, f.observaciones, f.timestamp, 
                           f.numerofactura, c.razonsocial as cliente
                    FROM factura f
                    LEFT JOIN contactos c ON f.idcontacto = c.idContacto
                    WHERE f.fecha BETWEEN ? AND ?
                    ORDER BY f.fecha, f.timestamp
                '''
                
                cursor.execute(query_facturas, (fecha_inicio, fecha_fin))
                facturas_raw = cursor.fetchall()
                
                for factura_row in facturas_raw:
                    facturas_data.append({
                        'tipo': 'FACTURA',
                        'id': factura_row[0],
                        'fecha': format_date(factura_row[1]) if factura_row[1] else '',
                        'total': float(factura_row[2]) if factura_row[2] else 0.0,
                        'observaciones': factura_row[3] or '',
                        'timestamp': factura_row[4],
                        'numero_factura': factura_row[5] or '',
                        'cliente': factura_row[6] or ''
                    })
                
        except Exception as e:
            logger.error(f"Error consultando facturas: {e}")
            facturas_data = []
        
        # ================ 3) UNIFICAR DATOS =====================
        todos_los_datos = tickets_data + facturas_data
        
        # Ordenar por fecha y timestamp
        todos_los_datos.sort(key=lambda x: (x['fecha'], x['timestamp']))
        
        # ================ 4) GENERAR ARCHIVO =====================
        if formato == 'csv':
            # Generar CSV
            output = []
            
            # Cabeceras
            cabeceras = [
                'Tipo', 'ID', 'Fecha', 'Total', 'Observaciones', 
                'Número Factura', 'Cliente', 'Timestamp'
            ]
            output.append(cabeceras)
            
            # Datos
            for item in todos_los_datos:
                fila = [
                    item['tipo'],
                    item['id'],
                    item['fecha'],
                    item['total'],
                    item['observaciones'],
                    item.get('numero_factura', ''),
                    item.get('cliente', ''),
                    item['timestamp']
                ]
                output.append(fila)
            
            # Crear respuesta CSV
            def generate():
                for row in output:
                    yield ','.join([f'"{str(cell)}"' for cell in row]) + '\n'
            
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

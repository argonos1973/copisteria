"""
Endpoints API para gestión de facturas recurrentes de proveedores.
"""

from flask import Blueprint, jsonify, request
from datetime import datetime
from dateutil.relativedelta import relativedelta

from db_utils import get_db_connection
from logger_config import get_logger
from scripts.batch_facturas_recurrentes import (
    ensure_recurrencia_columns,
    procesar_facturas_recurrentes
)

# Eximir de CSRF (endpoints API)
try:
    from security_utils import csrf
    CSRF_AVAILABLE = True
except ImportError:
    CSRF_AVAILABLE = False

logger = get_logger(__name__)

facturas_recurrentes_bp = Blueprint('facturas_recurrentes', __name__)

# Eximir blueprint de CSRF
if CSRF_AVAILABLE:
    csrf.exempt(facturas_recurrentes_bp)


@facturas_recurrentes_bp.route('/api/facturas-proveedores/<int:factura_id>/recurrencia', methods=['GET'])
def obtener_recurrencia(factura_id):
    """Obtiene el estado de recurrencia de una factura."""
    try:
        conn = get_db_connection()
        ensure_recurrencia_columns(conn)
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, recurrente, dia_recurrencia, ultima_generacion
            FROM facturas_proveedores
            WHERE id = ?
        """, (factura_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'error': 'Factura no encontrada'}), 404
        
        return jsonify({
            'factura_id': row['id'],
            'recurrente': bool(row['recurrente']),
            'dia_recurrencia': row['dia_recurrencia'] or 1,
            'ultima_generacion': row['ultima_generacion']
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo recurrencia: {e}")
        return jsonify({'error': str(e)}), 500


@facturas_recurrentes_bp.route('/api/facturas-proveedores/<int:factura_id>/recurrencia', methods=['PUT'])
def actualizar_recurrencia(factura_id):
    """
    Actualiza el estado de recurrencia de una factura.
    
    Body JSON:
        recurrente: bool - Si la factura es recurrente
        dia_recurrencia: int - Día del mes para generar (1-28)
    """
    try:
        data = request.get_json()
        
        recurrente = 1 if data.get('recurrente') else 0
        dia_recurrencia = data.get('dia_recurrencia', 1)
        
        # Validar día (1-28 para evitar problemas con meses cortos)
        if not 1 <= dia_recurrencia <= 28:
            return jsonify({'error': 'El día debe estar entre 1 y 28'}), 400
        
        conn = get_db_connection()
        ensure_recurrencia_columns(conn)
        
        cursor = conn.cursor()
        
        # Verificar que existe la factura
        cursor.execute("SELECT id FROM facturas_proveedores WHERE id = ?", (factura_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Factura no encontrada'}), 404
        
        # Actualizar
        cursor.execute("""
            UPDATE facturas_proveedores
            SET recurrente = ?, dia_recurrencia = ?
            WHERE id = ?
        """, (recurrente, dia_recurrencia, factura_id))
        
        conn.commit()
        conn.close()
        
        estado = "activada" if recurrente else "desactivada"
        logger.info(f"Recurrencia {estado} para factura {factura_id}, día {dia_recurrencia}")
        
        return jsonify({
            'success': True,
            'message': f'Recurrencia {estado}',
            'factura_id': factura_id,
            'recurrente': bool(recurrente),
            'dia_recurrencia': dia_recurrencia
        })
        
    except Exception as e:
        logger.error(f"Error actualizando recurrencia: {e}")
        return jsonify({'error': str(e)}), 500


@facturas_recurrentes_bp.route('/api/facturas-proveedores/recurrentes', methods=['GET'])
def listar_facturas_recurrentes():
    """Lista todas las facturas marcadas como recurrentes."""
    try:
        conn = get_db_connection()
        ensure_recurrencia_columns(conn)
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                fp.id, fp.numero_factura, fp.concepto, fp.total,
                fp.dia_recurrencia, fp.ultima_generacion,
                p.nombre as proveedor_nombre
            FROM facturas_proveedores fp
            LEFT JOIN proveedores p ON fp.proveedor_id = p.id
            WHERE fp.recurrente = 1
            ORDER BY p.nombre, fp.id
        """)
        
        facturas = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            'facturas': facturas,
            'total': len(facturas)
        })
        
    except Exception as e:
        logger.error(f"Error listando facturas recurrentes: {e}")
        return jsonify({'error': str(e)}), 500


@facturas_recurrentes_bp.route('/api/facturas-proveedores/recurrentes/generar', methods=['POST'])
def generar_facturas_recurrentes():
    """
    Genera manualmente las facturas recurrentes para un mes específico.
    
    Body JSON:
        mes: string - Mes objetivo en formato YYYY-MM (opcional, default: mes actual)
        dry_run: bool - Si true, solo simula sin crear (opcional)
    """
    try:
        data = request.get_json() or {}
        
        mes_objetivo = data.get('mes')
        dry_run = data.get('dry_run', False)
        
        # Validar formato de mes si se proporciona
        if mes_objetivo:
            try:
                datetime.strptime(mes_objetivo, '%Y-%m')
            except ValueError:
                return jsonify({'error': 'Formato de mes inválido. Use YYYY-MM'}), 400
        
        resultados = procesar_facturas_recurrentes(
            mes_objetivo=mes_objetivo,
            dry_run=dry_run
        )
        
        return jsonify({
            'success': True,
            'mes': mes_objetivo or datetime.now().strftime('%Y-%m'),
            'dry_run': dry_run,
            'resultados': resultados
        })
        
    except Exception as e:
        logger.error(f"Error generando facturas recurrentes: {e}")
        return jsonify({'error': str(e)}), 500


@facturas_recurrentes_bp.route('/api/facturas-proveedores/<int:factura_id>/historial-recurrencia', methods=['GET'])
def historial_recurrencia(factura_id):
    """Obtiene las facturas generadas a partir de una factura recurrente."""
    try:
        conn = get_db_connection()
        ensure_recurrencia_columns(conn)
        
        cursor = conn.cursor()
        
        # Verificar que la factura existe y es recurrente
        cursor.execute("""
            SELECT id, recurrente FROM facturas_proveedores WHERE id = ?
        """, (factura_id,))
        
        factura = cursor.fetchone()
        if not factura:
            conn.close()
            return jsonify({'error': 'Factura no encontrada'}), 404
        
        # Obtener facturas generadas
        cursor.execute("""
            SELECT 
                id, numero_factura, fecha_emision, total, estado, fecha_pago
            FROM facturas_proveedores
            WHERE factura_origen_id = ?
            ORDER BY fecha_emision DESC
        """, (factura_id,))
        
        generadas = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            'factura_origen_id': factura_id,
            'es_recurrente': bool(factura['recurrente']),
            'facturas_generadas': generadas,
            'total_generadas': len(generadas)
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo historial recurrencia: {e}")
        return jsonify({'error': str(e)}), 500

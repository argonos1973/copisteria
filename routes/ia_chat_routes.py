#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API para chat con IA local (Ollama) - Asistente de consultas SQL
Solo permite operaciones de lectura sobre la BD del usuario
"""

import re
import json
import os
import sqlite3
from flask import Blueprint, request, jsonify, session
from functools import wraps
from db_utils import get_db_connection
from logger_config import get_logger

logger = get_logger(__name__)

ia_chat_bp = Blueprint('ia_chat', __name__)

# Configuración OpenAI
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_MODEL = "gpt-4o-mini"  # Rápido y económico

# Tablas permitidas para consultas
TABLAS_PERMITIDAS = [
    'factura', 'tickets', 'contactos', 'productos', 'gastos',
    'proforma', 'presupuesto', 'detalle_factura', 'detalle_tickets',
    'detalle_proforma', 'detalle_presupuesto', 'proveedores',
    'facturas_proveedores', 'descuento_producto_franja'
]

# Palabras prohibidas en SQL
PALABRAS_PROHIBIDAS = [
    'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 
    'TRUNCATE', 'EXEC', 'EXECUTE', 'GRANT', 'REVOKE', 'COMMIT',
    'ROLLBACK', 'SAVEPOINT', 'ATTACH', 'DETACH', 'VACUUM', 'REINDEX'
]


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'No autorizado'}), 401
        return f(*args, **kwargs)
    return decorated_function


def obtener_esquema_tablas():
    """Obtiene el esquema de las tablas permitidas para el contexto de la IA"""
    
    # Esquema REAL de las tablas (columnas exactas de la BD)
    DESCRIPCIONES = {
        'factura': {
            'id': "ID único de la factura",
            'idContacto': "ID del cliente (FK a contactos.idContacto)",
            'nif': "NIF del cliente",
            'fecha': "fecha de emisión (YYYY-MM-DD)",
            'fvencimiento': "fecha de vencimiento (YYYY-MM-DD)",
            'numero': "número de factura",
            'importe_bruto': "base imponible",
            'importe_impuestos': "importe de IVA",
            'importe_cobrado': "cantidad ya cobrada",
            'total': "importe total",
            'estado': "'P'=Pendiente, 'C'=Cobrada, 'V'=Vencida",
            'formaPago': "'E'=Efectivo, 'T'=Tarjeta, 'B'=Transferencia",
            'tipo': "'N'=Normal, 'R'=Rectificativa",
            'fechaCobro': "fecha de cobro",
            'observaciones': "notas adicionales",
            'carta_enviada': "1=carta de reclamación enviada por email, 0=no enviada",
            'fecha_ultima_carta': "fecha de última carta de reclamación generada (YYYY-MM-DD)"
        },
        'tickets': {
            'id': "ID único del ticket",
            'fecha': "fecha del ticket (YYYY-MM-DD)",
            'numero': "número de ticket",
            'importe_bruto': "base imponible",
            'importe_impuestos': "importe de IVA",
            'importe_cobrado': "cantidad cobrada",
            'total': "importe total",
            'estado': "'P'=Pendiente, 'C'=Cobrado",
            'formaPago': "'E'=Efectivo, 'T'=Tarjeta, 'B'=Transferencia",
            'tipo': "tipo de ticket"
        },
        'contactos': {
            'idContacto': "ID único del contacto",
            'razonsocial': "nombre o razón social",
            'identificador': "NIF/CIF",
            'mail': "email del contacto",
            'telf1': "teléfono principal",
            'direccion': "dirección",
            'localidad': "ciudad/localidad",
            'cp': "código postal",
            'provincia': "provincia",
            'facturacion_automatica': "1=envío automático de facturas y cartas por email, 0=no enviar"
        },
        'productos': {
            'id': "ID único del producto",
            'nombre': "nombre del producto (ej: 'IMPRESSIO A4 COLOR')",
            'descripcion': "descripción del producto",
            'subtotal': "precio sin IVA",
            'iva': "importe de IVA",
            'impuestos': "porcentaje de IVA (ej: 21)",
            'total': "precio final con IVA (usar esta columna para precios)"
        },
        'detalle_tickets': {
            'id': "ID del detalle",
            'id_ticket': "ID del ticket (FK a tickets.id)",
            'concepto': "nombre del producto vendido",
            'descripcion': "descripción adicional",
            'cantidad': "cantidad vendida",
            'precio': "precio unitario",
            'impuestos': "porcentaje IVA",
            'total': "importe total de la línea",
            'productoId': "ID del producto (FK a productos.id)"
        },
        'detalle_factura': {
            'id': "ID del detalle",
            'id_factura': "ID de la factura (FK a factura.id)",
            'concepto': "nombre del producto facturado",
            'descripcion': "descripción adicional",
            'cantidad': "cantidad facturada",
            'precio': "precio unitario",
            'impuestos': "porcentaje IVA",
            'total': "importe total de la línea",
            'productoId': "ID del producto (FK a productos.id)",
            'fechaDetalle': "fecha del detalle"
        },
        'gastos': {
            'id': "ID del gasto",
            'fecha_operacion': "fecha de la operación",
            'fecha_valor': "fecha valor",
            'concepto': "descripción del gasto",
            'importe_eur': "importe en euros (negativo=gasto, positivo=ingreso)",
            'saldo': "saldo resultante"
        },
        'presupuesto': {
            'id': "ID del presupuesto",
            'numero': "número de presupuesto",
            'fecha': "fecha (YYYY-MM-DD)",
            'estado': "'B'=Borrador, 'A'=Aceptado, 'R'=Rechazado, 'F'=Facturado",
            'idContacto': "ID del cliente (FK a contactos.idContacto)",
            'total': "importe total",
            'importe_bruto': "base imponible",
            'importe_impuestos': "IVA"
        },
        'proveedores': {
            'id': "ID del proveedor",
            'nombre': "nombre del proveedor",
            'nif': "NIF/CIF",
            'email': "email",
            'telefono': "teléfono"
        },
        'facturas_proveedores': {
            'id': "ID de la factura",
            'proveedor_id': "ID del proveedor (FK a proveedores.id)",
            'numero_factura': "número de factura",
            'fecha_emision': "fecha de emisión",
            'base_imponible': "base imponible",
            'iva_importe': "importe IVA",
            'total': "total factura",
            'estado': "'pendiente', 'pagada', 'vencida'",
            'concepto': "concepto/descripción"
        },
        'descuento_producto_franja': {
            'id': "ID de la franja",
            'producto_id': "ID del producto (FK a productos.id)",
            'min_cantidad': "cantidad mínima para aplicar esta franja",
            'max_cantidad': "cantidad máxima de esta franja",
            'porcentaje_descuento': "descuento a aplicar en esta franja (%)"
        }
    }
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            esquema = []
            
            for tabla in TABLAS_PERMITIDAS:
                try:
                    cursor.execute(f"PRAGMA table_info({tabla})")
                    columnas = cursor.fetchall()
                    if columnas:
                        cols = []
                        for col in columnas:
                            col_name = col[1]
                            col_type = col[2]
                            desc = DESCRIPCIONES.get(tabla, {}).get(col_name, '')
                            if desc:
                                cols.append(f"{col_name} ({col_type}) -- {desc}")
                            else:
                                cols.append(f"{col_name} ({col_type})")
                        esquema.append(f"Tabla {tabla}:\n  " + "\n  ".join(cols))
                except:
                    pass
            
            return "\n\n".join(esquema)
    except Exception as e:
        logger.error(f"Error obteniendo esquema: {e}")
        return ""


def validar_sql(sql: str) -> tuple:
    """
    Valida que el SQL sea seguro (solo SELECT, sin operaciones peligrosas)
    Returns: (es_valido: bool, mensaje: str)
    """
    if not sql or not sql.strip():
        return False, "SQL vacío"
    
    sql_upper = sql.upper().strip()
    
    # Solo permitir SELECT
    if not sql_upper.startswith('SELECT'):
        return False, "Solo se permiten consultas SELECT"
    
    # Verificar palabras prohibidas
    for palabra in PALABRAS_PROHIBIDAS:
        # Buscar palabra completa (no como parte de otra)
        pattern = r'\b' + palabra + r'\b'
        if re.search(pattern, sql_upper):
            return False, f"Operación '{palabra}' no permitida"
    
    # Verificar que no haya múltiples statements
    if ';' in sql[:-1]:  # Permitir ; solo al final
        return False, "No se permiten múltiples sentencias SQL"
    
    # Verificar comentarios SQL que podrían ocultar código
    if '--' in sql or '/*' in sql:
        return False, "No se permiten comentarios SQL"
    
    return True, "OK"


def ejecutar_consulta_segura(sql: str, limit: int = 100) -> dict:
    """Ejecuta una consulta SQL en modo solo lectura"""
    try:
        # Añadir LIMIT si no existe
        sql_upper = sql.upper()
        if 'LIMIT' not in sql_upper:
            sql = sql.rstrip(';') + f" LIMIT {limit}"
        
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql)
            
            rows = cursor.fetchall()
            columnas = [description[0] for description in cursor.description]
            
            datos = []
            for row in rows:
                datos.append(dict(row))
            
            return {
                'success': True,
                'columnas': columnas,
                'datos': datos,
                'total': len(datos)
            }
    except sqlite3.Error as e:
        return {'success': False, 'error': f"Error SQL: {str(e)}"}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def generar_sql_con_ia(prompt: str, esquema: str, historial: list = None) -> dict:
    """Envía el prompt a OpenAI y obtiene el SQL generado"""
    import requests
    from datetime import datetime
    
    if not OPENAI_API_KEY:
        return {'success': False, 'error': "API key de OpenAI no configurada"}
    
    # Fecha y año actual para el contexto
    ahora = datetime.now()
    fecha_actual = ahora.strftime('%Y-%m-%d')
    anio_actual = ahora.year
    
    system_prompt = f"""Eres un asistente de gestión empresarial. Puedes:
1. Generar consultas SQL SELECT para obtener datos
2. Ejecutar procesos batch del sistema
3. Enviar emails

{esquema}

RELACIONES ENTRE TABLAS (usa JOIN cuando necesites datos de varias tablas):
- factura.idContacto = contactos.idContacto (cliente de la factura)
- detalle_factura.id_factura = factura.id
- detalle_factura.productoId = productos.id
- detalle_tickets.id_ticket = tickets.id
- detalle_tickets.productoId = productos.id
- facturas_proveedores.proveedor_id = proveedores.id

CONCEPTOS DE NEGOCIO:
- "Impresiones" o "copias" son líneas de venta en detalle_tickets o detalle_factura
- El nombre del producto está en concepto (ej: 'IMPRESSIO A4 COLOR', 'IMPRESSIO A4 BN')
- Para buscar impresiones A4 a color: concepto LIKE '%A4%COLOR%'
- Para buscar impresiones B/N: concepto LIKE '%BN%' OR concepto LIKE '%B/N%'
- Para contar impresiones vendidas: SUM(cantidad)
- Para filtrar por fecha: JOIN con tickets/factura y usar fecha
- IMPORTANTE: Para ventas "cobradas" o "efectivas", filtrar por estado = 'C'
- Por defecto, incluir solo cobradas (estado = 'C') a menos que se pida todo
- Ejemplos de conceptos reales: 'IMPRESSIO A4 COLOR', 'IMPRESSIO A4 BN', 'IMPRESSIO A3 COLOR'
- IMPORTANTE: La tabla productos NO tiene columna 'precio'. Usa 'total' para el precio del producto
- Para saber el precio de un producto: SELECT nombre, total FROM productos WHERE nombre LIKE '%..%'

SISTEMA DE FRANJAS (descuentos por cantidad):
- La tabla descuento_producto_franja contiene descuentos por rangos de cantidad
- Cada producto puede tener múltiples franjas con min_cantidad, max_cantidad y porcentaje_descuento
- Para calcular precio con franjas: 
  1. Buscar el producto: SELECT id, total FROM productos WHERE nombre LIKE '%..%'
  2. Buscar la franja aplicable: SELECT porcentaje_descuento FROM descuento_producto_franja 
     WHERE producto_id = X AND min_cantidad <= CANTIDAD AND max_cantidad >= CANTIDAD
  3. Calcular: precio_final = productos.total * cantidad * (1 - porcentaje_descuento/100)
- Ejemplo SQL para precio de 100 unidades de impresión A4 BN:
  SELECT p.nombre, p.total as precio_unitario, f.porcentaje_descuento,
         (p.total * 100 * (1 - COALESCE(f.porcentaje_descuento,0)/100)) as precio_total
  FROM productos p
  LEFT JOIN descuento_producto_franja f ON f.producto_id = p.id 
    AND 100 BETWEEN f.min_cantidad AND f.max_cantidad
  WHERE p.nombre LIKE 'IMPRESSIO A4 BN%'
- IMPORTANTE: Para impresiones usa patrones específicos como 'IMPRESSIO A4 BN%' o 'IMPRESSIO A4 COLOR%'
- NO uses '%B/N%' porque coincide con otros productos (tarjetas, etc)

SISTEMA DE CARTAS DE RECLAMACIÓN:
- Las cartas de reclamación se generan automáticamente para facturas vencidas (estado='V')
- Para que se ENVÍE el email, el cliente debe tener facturacion_automatica=1 en contactos
- Si facturacion_automatica=0, la carta se genera (PDF) pero NO se envía por email
- Campos relevantes en factura: carta_enviada (1=enviada, 0=no), fecha_ultima_carta
- Para saber por qué una factura no envía carta:
  SELECT f.numero, f.estado, f.carta_enviada, f.fecha_ultima_carta, c.razonsocial, c.mail, c.facturacion_automatica
  FROM factura f JOIN contactos c ON f.idContacto = c.idContacto WHERE f.numero = 'FXXXXXX'
- Si carta_enviada=0 y facturacion_automatica=0: el cliente no tiene activado el envío automático
- Si carta_enviada=0 y facturacion_automatica=1 y fecha_ultima_carta IS NULL: la factura aún no ha sido procesada

PROCESOS DISPONIBLES:
- batchFacturasVencidas: Revisar facturas vencidas y enviar recordatorios (genera cartas)
- batchTotalDia: Generar resumen del día
- batchScanFacturasRecibidas: Escanear facturas recibidas

HANDLERS DISPONIBLES (para crear nuevos procesos):
- batchFacturasVencidas, batchTotalDia, batchScanFacturasRecibidas, batchPol, batchOptimizar
- batchGenerico: Handler configurable con parámetros JSON

HANDLER GENÉRICO (batchGenerico) - Acciones disponibles:
- enviar_email: {{"accion":"enviar_email","destinatarios":["email"],"asunto":"...","mensaje":"..."}}
- ejecutar_sql: {{"accion":"ejecutar_sql","sql":"SELECT...","destinatarios":["email"],"asunto":"..."}}
- generar_reporte: {{"accion":"generar_reporte","consultas":[{{"titulo":"...","sql":"..."}}],"destinatarios":["email"]}}

FORMATOS DE RESPUESTA (usa EXACTAMENTE uno de estos):
1. Para consultas SQL: responde SOLO con el SQL (sin explicaciones)
2. Para ejecutar proceso: PROCESO:nombre_proceso
3. Para enviar email: EMAIL:destinatario|asunto|cuerpo
4. Para programar proceso: SCHEDULE:proceso|cron|dias
   - cron: expresión cron (ej: "0 9 * * *" = 9:00 cada día)
   - dias: opcional, días de semana (L,M,X,J,V,S,D)
   - Ejemplo: SCHEDULE:batchFacturasVencidas|0 9 * * *|L,M,X,J,V
5. Para crear nuevo proceso: NEWPROCESO:codigo|nombre|handler|timeout
   - Ejemplo: NEWPROCESO:miProceso|Mi Proceso Custom|batchTotalDia|300
6. Para crear proceso genérico: GENERICPROCESO:codigo|nombre|params_json
   - params_json debe ser JSON válido con accion, destinatarios, etc.
   - Ejemplo: GENERICPROCESO:reporteVentas|Reporte Ventas Diario|{{"accion":"ejecutar_sql","sql":"SELECT * FROM factura WHERE fecha=date('now')","destinatarios":["admin@empresa.com"],"asunto":"Ventas del día"}}

FECHA ACTUAL: {fecha_actual}
AÑO ACTUAL: {anio_actual}
- IMPORTANTE: El año {anio_actual} es el año EN CURSO, NO es futuro
- Todas las consultas de precios/productos deben usar los productos del año actual
- Si el usuario pregunta por precios SIN especificar año, usa el año actual ({anio_actual})

REGLAS SQL:
- Solo SELECT válido para SQLite
- Usa EXACTAMENTE los nombres de columnas del esquema
- PUEDES y DEBES usar JOIN para relacionar tablas
- Para "hoy": fecha = date('now')
- Para "ayer": fecha = date('now', '-1 day')  
- Para "este mes": strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now')
- Para "este año": strftime('%Y', fecha) = strftime('%Y', 'now')
- Para facturas pendientes: estado = 'P'
- Para facturas cobradas: estado = 'C'

Si no puedes realizar la acción: ERROR: [motivo]"""

    # Construir mensajes con historial
    messages = [{"role": "system", "content": system_prompt}]
    
    # Añadir historial de conversación si existe
    if historial:
        for msg in historial[-6:]:  # Últimos 6 mensajes para contexto
            if msg.get('role') in ['user', 'assistant']:
                messages.append({
                    "role": msg['role'],
                    "content": msg['content']
                })
    
    # Añadir mensaje actual
    messages.append({"role": "user", "content": prompt})
    
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": OPENAI_MODEL,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 500
            },
            timeout=30
        )
        
        if response.status_code != 200:
            err = response.json().get('error', {}).get('message', response.text)
            return {'success': False, 'error': f"Error OpenAI: {err}"}
        
        data = response.json()
        sql = data['choices'][0]['message']['content'].strip()
        
        # Limpiar el SQL de posibles markdown
        sql = re.sub(r'```sql\s*\n?', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'```\s*\n?', '', sql)
        sql = re.sub(r'\n?```', '', sql)
        sql = sql.strip()
        
        # Si hay múltiples líneas, unirlas y limpiar
        lines = [l.strip() for l in sql.split('\n') if l.strip()]
        sql = ' '.join(lines)
        
        if sql.upper().startswith('ERROR:'):
            return {'success': False, 'error': sql}
        
        return {'success': True, 'sql': sql}
        
    except requests.exceptions.Timeout:
        return {'success': False, 'error': "Timeout al conectar con OpenAI"}
    except Exception as e:
        logger.error(f"Error OpenAI: {e}")
        return {'success': False, 'error': str(e)}


@ia_chat_bp.route('/api/ia/chat', methods=['POST'])
@login_required
def chat_ia():
    """
    Endpoint principal del chat con IA
    Recibe un prompt y devuelve SQL + resultados
    """
    try:
        data = request.get_json()
        prompt = data.get('prompt', '').strip()
        historial = data.get('historial', [])
        ejecutar = data.get('ejecutar', False)
        
        if not prompt:
            return jsonify({'error': 'Prompt vacío'}), 400
        
        if len(prompt) > 1000:
            return jsonify({'error': 'Prompt demasiado largo (max 1000 caracteres)'}), 400
        
        # Obtener esquema de tablas
        esquema = obtener_esquema_tablas()
        if not esquema:
            return jsonify({'error': 'No se pudo obtener el esquema de la BD'}), 500
        
        # Generar respuesta con IA (pasando historial para contexto)
        resultado_ia = generar_sql_con_ia(prompt, esquema, historial)
        
        if not resultado_ia.get('success'):
            return jsonify({
                'success': False,
                'error': resultado_ia.get('error', 'Error generando respuesta'),
                'sql': None
            })
        
        respuesta_ia = resultado_ia['sql'].strip()
        
        # Detectar tipo de respuesta
        if respuesta_ia.startswith('PROCESO:'):
            # Ejecutar proceso batch
            proceso = respuesta_ia.replace('PROCESO:', '').strip()
            return jsonify({
                'success': True,
                'tipo': 'proceso',
                'proceso': proceso,
                'prompt': prompt
            })
        
        elif respuesta_ia.startswith('EMAIL:'):
            # Preparar email
            partes = respuesta_ia.replace('EMAIL:', '').strip().split('|')
            if len(partes) >= 3:
                return jsonify({
                    'success': True,
                    'tipo': 'email',
                    'destinatario': partes[0].strip(),
                    'asunto': partes[1].strip(),
                    'cuerpo': partes[2].strip(),
                    'prompt': prompt
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Formato de email incorrecto'
                })
        
        elif respuesta_ia.startswith('SCHEDULE:'):
            # Programar schedule
            partes = respuesta_ia.replace('SCHEDULE:', '').strip().split('|')
            if len(partes) >= 2:
                return jsonify({
                    'success': True,
                    'tipo': 'schedule',
                    'proceso': partes[0].strip(),
                    'cron': partes[1].strip(),
                    'dias': partes[2].strip() if len(partes) > 2 else '',
                    'prompt': prompt
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Formato de schedule incorrecto'
                })
        
        elif respuesta_ia.startswith('NEWPROCESO:'):
            # Crear nuevo proceso
            partes = respuesta_ia.replace('NEWPROCESO:', '').strip().split('|')
            if len(partes) >= 3:
                return jsonify({
                    'success': True,
                    'tipo': 'newproceso',
                    'code': partes[0].strip(),
                    'name': partes[1].strip(),
                    'handler': partes[2].strip(),
                    'timeout': int(partes[3].strip()) if len(partes) > 3 else 300,
                    'prompt': prompt
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Formato de nuevo proceso incorrecto'
                })
        
        elif respuesta_ia.startswith('GENERICPROCESO:'):
            # Crear proceso genérico con parámetros
            contenido = respuesta_ia.replace('GENERICPROCESO:', '').strip()
            # Buscar primer | y segundo |
            partes = contenido.split('|', 2)
            if len(partes) >= 3:
                try:
                    params = json.loads(partes[2].strip())
                    return jsonify({
                        'success': True,
                        'tipo': 'genericproceso',
                        'code': partes[0].strip(),
                        'name': partes[1].strip(),
                        'params': params,
                        'prompt': prompt
                    })
                except json.JSONDecodeError:
                    return jsonify({
                        'success': False,
                        'error': 'JSON de parámetros inválido'
                    })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Formato de proceso genérico incorrecto'
                })
        
        elif respuesta_ia.startswith('ERROR:'):
            return jsonify({
                'success': False,
                'error': respuesta_ia.replace('ERROR:', '').strip()
            })
        
        else:
            # Es SQL - limpiar posible prefijo "SQL:"
            sql = respuesta_ia
            if sql.upper().startswith('SQL:'):
                sql = sql[4:].strip()
            
            # Validar SQL
            es_valido, mensaje = validar_sql(sql)
            if not es_valido:
                return jsonify({
                    'success': False,
                    'error': f"SQL no válido: {mensaje}",
                    'sql': sql
                })
            
            respuesta = {
                'success': True,
                'tipo': 'sql',
                'sql': sql,
                'prompt': prompt
            }
            
            # Ejecutar si se solicita
            if ejecutar:
                resultado = ejecutar_consulta_segura(sql)
                respuesta['resultado'] = resultado
            
            return jsonify(respuesta)
        
    except Exception as e:
        logger.error(f"Error en chat IA: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@ia_chat_bp.route('/api/ia/ejecutar', methods=['POST'])
@login_required
def ejecutar_sql():
    """Ejecuta un SQL previamente validado"""
    try:
        data = request.get_json()
        sql = data.get('sql', '').strip()
        
        if not sql:
            return jsonify({'error': 'SQL vacío'}), 400
        
        # Validar SQL
        es_valido, mensaje = validar_sql(sql)
        if not es_valido:
            return jsonify({'error': f"SQL no válido: {mensaje}"}), 400
        
        # Ejecutar
        resultado = ejecutar_consulta_segura(sql)
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error ejecutando SQL: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@ia_chat_bp.route('/api/ia/esquema', methods=['GET'])
@login_required
def obtener_esquema():
    """Devuelve el esquema de tablas disponibles"""
    try:
        esquema = obtener_esquema_tablas()
        return jsonify({
            'success': True,
            'esquema': esquema,
            'tablas': TABLAS_PERMITIDAS
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ia_chat_bp.route('/api/ia/status', methods=['GET'])
def status_ia():
    """Verifica el estado de OpenAI"""
    if OPENAI_API_KEY:
        return jsonify({
            'success': True,
            'status': 'online',
            'modelo': OPENAI_MODEL,
            'provider': 'OpenAI'
        })
    return jsonify({'success': False, 'status': 'offline', 'error': 'API key no configurada'})


# ============ PROCESOS BATCH ============

PROCESOS_PERMITIDOS = {
    'batchFacturasVencidas': 'Revisar facturas vencidas y enviar recordatorios',
    'batchTotalDia': 'Generar resumen del día',
    'batchScanFacturasRecibidas': 'Escanear facturas recibidas pendientes'
}

@ia_chat_bp.route('/api/ia/procesos', methods=['GET'])
@login_required
def listar_procesos():
    """Lista los procesos batch disponibles"""
    return jsonify({
        'success': True,
        'procesos': [{'code': k, 'descripcion': v} for k, v in PROCESOS_PERMITIDOS.items()]
    })


@ia_chat_bp.route('/api/ia/ejecutar-proceso', methods=['POST'])
@login_required
def ejecutar_proceso():
    """Ejecuta un proceso batch"""
    try:
        data = request.get_json()
        proceso = data.get('proceso', '').strip()
        
        if not proceso:
            return jsonify({'error': 'Proceso no especificado'}), 400
        
        if proceso not in PROCESOS_PERMITIDOS:
            return jsonify({'error': f'Proceso no permitido: {proceso}'}), 403
        
        # Obtener empresa de la sesión
        from flask import session
        empresa_id = session.get('empresa_id')
        if not empresa_id:
            return jsonify({'error': 'No hay empresa en sesión'}), 400
        
        # Conectar a BD usuarios (donde están las tablas batch)
        import sqlite3
        from multiempresa_config import DB_USUARIOS_PATH
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        conn.row_factory = sqlite3.Row
        
        try:
            # Buscar definición del job
            job = conn.execute(
                "SELECT id FROM batch_job_definitions WHERE code = ? AND active = 1",
                (proceso,)
            ).fetchone()
            
            if not job:
                return jsonify({'error': 'Proceso no encontrado en el sistema'}), 404
            
            # Crear run
            cur = conn.execute(
                """
                INSERT INTO batch_job_runs
                (empresa_id, schedule_id, job_definition_id, trigger, status, params_snapshot)
                VALUES (?, NULL, ?, 'ia_chat', 'queued', NULL)
                """,
                (empresa_id, job['id'])
            )
            conn.commit()
            run_id = cur.lastrowid
            
            return jsonify({
                'success': True,
                'mensaje': f'Proceso {proceso} programado correctamente',
                'run_id': run_id
            })
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error ejecutando proceso: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ============ ENVÍO DE EMAILS ============

@ia_chat_bp.route('/api/ia/enviar-email', methods=['POST'])
@login_required
def enviar_email_ia():
    """Envía un email desde el chat IA"""
    try:
        data = request.get_json()
        destinatario = data.get('destinatario', '').strip()
        asunto = data.get('asunto', '').strip()
        cuerpo = data.get('cuerpo', '').strip()
        
        if not destinatario:
            return jsonify({'error': 'Destinatario requerido'}), 400
        if not asunto:
            return jsonify({'error': 'Asunto requerido'}), 400
        if not cuerpo:
            return jsonify({'error': 'Cuerpo del mensaje requerido'}), 400
        
        # Validar email básico
        import re
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', destinatario):
            return jsonify({'error': 'Email no válido'}), 400
        
        # Enviar email
        from email_utils import enviar_email_texto
        exito, mensaje = enviar_email_texto(destinatario, asunto, cuerpo)
        
        if exito:
            return jsonify({
                'success': True,
                'mensaje': f'Email enviado a {destinatario}'
            })
        else:
            return jsonify({'error': mensaje}), 500
            
    except Exception as e:
        logger.error(f"Error enviando email: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ============ PROGRAMAR SCHEDULES ============

@ia_chat_bp.route('/api/ia/crear-schedule', methods=['POST'])
@login_required
def crear_schedule():
    """Crea un nuevo schedule para un proceso"""
    try:
        data = request.get_json()
        proceso = data.get('proceso', '').strip()
        cron_expr = data.get('cron', '').strip()
        dias = data.get('dias', '')  # "L,M,X,J,V" o similar
        
        if not proceso:
            return jsonify({'error': 'Proceso no especificado'}), 400
        if not cron_expr:
            return jsonify({'error': 'Expresión cron requerida'}), 400
        
        if proceso not in PROCESOS_PERMITIDOS:
            return jsonify({'error': f'Proceso no permitido: {proceso}'}), 403
        
        from flask import session
        empresa_id = session.get('empresa_id')
        user_id = session.get('user_id')
        if not empresa_id:
            return jsonify({'error': 'No hay empresa en sesión'}), 400
        
        import sqlite3
        from multiempresa_config import DB_USUARIOS_PATH
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        conn.row_factory = sqlite3.Row
        
        try:
            job = conn.execute(
                "SELECT id FROM batch_job_definitions WHERE code = ? AND active = 1",
                (proceso,)
            ).fetchone()
            
            if not job:
                return jsonify({'error': 'Proceso no encontrado'}), 404
            
            cur = conn.execute(
                """
                INSERT INTO batch_job_schedules
                (empresa_id, job_definition_id, enabled, cron_expr, timezone, days_of_week, created_by_usuario_id, updated_by_usuario_id)
                VALUES (?, ?, 1, ?, 'Europe/Madrid', ?, ?, ?)
                """,
                (empresa_id, job['id'], cron_expr, dias, user_id, user_id)
            )
            conn.commit()
            
            return jsonify({
                'success': True,
                'mensaje': f'Schedule creado para {proceso}',
                'schedule_id': cur.lastrowid
            })
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error creando schedule: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# ============ CREAR DEFINICIONES DE PROCESOS ============

# Handlers disponibles para nuevos procesos
HANDLERS_DISPONIBLES = {
    'batchFacturasVencidas': 'Procesa facturas vencidas',
    'batchTotalDia': 'Genera resumen del día',
    'batchScanFacturasRecibidas': 'Escanea facturas recibidas',
    'batchPol': 'Proceso POL',
    'batchOptimizar': 'Optimiza base de datos',
    'batchGenerico': 'Handler genérico configurable (email, SQL, reportes)'
}

@ia_chat_bp.route('/api/ia/crear-proceso', methods=['POST'])
@login_required
def crear_proceso_definicion():
    """Crea una nueva definición de proceso batch"""
    try:
        data = request.get_json()
        code = data.get('code', '').strip()
        name = data.get('name', '').strip()
        handler = data.get('handler', '').strip()
        timeout = data.get('timeout', 300)
        
        if not code:
            return jsonify({'error': 'Código del proceso requerido'}), 400
        if not name:
            return jsonify({'error': 'Nombre del proceso requerido'}), 400
        if not handler:
            return jsonify({'error': 'Handler requerido'}), 400
        
        # Validar handler permitido
        if handler not in HANDLERS_DISPONIBLES:
            return jsonify({
                'error': f'Handler no permitido. Disponibles: {", ".join(HANDLERS_DISPONIBLES.keys())}'
            }), 403
        
        import sqlite3
        from multiempresa_config import DB_USUARIOS_PATH
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        conn.row_factory = sqlite3.Row
        
        try:
            # Verificar que no existe
            exists = conn.execute(
                "SELECT id FROM batch_job_definitions WHERE code = ?",
                (code,)
            ).fetchone()
            
            if exists:
                return jsonify({'error': f'Ya existe un proceso con código {code}'}), 409
            
            cur = conn.execute(
                """
                INSERT INTO batch_job_definitions 
                (code, name, handler, timeout_sec, concurrency_mode, active)
                VALUES (?, ?, ?, ?, 'per_empresa_single', 1)
                """,
                (code, name, handler, timeout)
            )
            conn.commit()
            
            # Añadir a procesos permitidos
            PROCESOS_PERMITIDOS[code] = name
            
            return jsonify({
                'success': True,
                'mensaje': f'Proceso "{name}" creado correctamente',
                'definition_id': cur.lastrowid
            })
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error creando definición: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@ia_chat_bp.route('/api/ia/handlers', methods=['GET'])
@login_required
def listar_handlers():
    """Lista los handlers disponibles para crear procesos"""
    return jsonify({
        'success': True,
        'handlers': [{'code': k, 'descripcion': v} for k, v in HANDLERS_DISPONIBLES.items()]
    })


@ia_chat_bp.route('/api/ia/crear-proceso-generico', methods=['POST'])
@login_required
def crear_proceso_generico():
    """Crea un proceso usando el handler genérico con parámetros personalizados"""
    try:
        data = request.get_json()
        code = data.get('code', '').strip()
        name = data.get('name', '').strip()
        params = data.get('params', {})
        
        if not code:
            return jsonify({'error': 'Código del proceso requerido'}), 400
        if not name:
            return jsonify({'error': 'Nombre del proceso requerido'}), 400
        if not params.get('accion'):
            return jsonify({'error': 'Acción requerida en params'}), 400
        
        from flask import session
        empresa_id = session.get('empresa_id')
        user_id = session.get('user_id')
        if not empresa_id:
            return jsonify({'error': 'No hay empresa en sesión'}), 400
        
        import sqlite3
        from multiempresa_config import DB_USUARIOS_PATH
        conn = sqlite3.connect(DB_USUARIOS_PATH)
        conn.row_factory = sqlite3.Row
        
        try:
            # Verificar que no existe el código
            exists = conn.execute(
                "SELECT id FROM batch_job_definitions WHERE code = ?",
                (code,)
            ).fetchone()
            
            if exists:
                return jsonify({'error': f'Ya existe un proceso con código {code}'}), 409
            
            # Crear definición del proceso
            cur = conn.execute(
                """
                INSERT INTO batch_job_definitions 
                (code, name, handler, schema_json, timeout_sec, concurrency_mode, active)
                VALUES (?, ?, 'batchGenerico', ?, 300, 'per_empresa_single', 1)
                """,
                (code, name, json.dumps(params, ensure_ascii=False))
            )
            job_id = cur.lastrowid
            
            # Crear schedule deshabilitado por defecto
            conn.execute(
                """
                INSERT INTO batch_job_schedules
                (empresa_id, job_definition_id, enabled, cron_expr, timezone, params_json, created_by_usuario_id)
                VALUES (?, ?, 0, '0 9 * * *', 'Europe/Madrid', ?, ?)
                """,
                (empresa_id, job_id, json.dumps(params, ensure_ascii=False), user_id)
            )
            conn.commit()
            
            # Añadir a procesos permitidos
            PROCESOS_PERMITIDOS[code] = name
            
            return jsonify({
                'success': True,
                'mensaje': f'Proceso genérico "{name}" creado correctamente',
                'definition_id': job_id
            })
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error creando proceso genérico: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

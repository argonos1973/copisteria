#!/usr/bin/env python3
"""
batchGenerico.py - Handler genérico configurable

Este handler ejecuta acciones basadas en parámetros JSON.
Permite crear procesos personalizados sin escribir código.

Acciones soportadas:
- enviar_email: Envía email con contenido personalizado
- ejecutar_sql: Ejecuta consulta SQL y envía resultados por email
- generar_reporte: Genera reporte basado en consulta SQL

Parámetros (JSON):
{
    "accion": "enviar_email|ejecutar_sql|generar_reporte",
    "destinatarios": ["email1@ejemplo.com"],
    "asunto": "Asunto del email",
    "mensaje": "Cuerpo del mensaje",
    "sql": "SELECT ... (solo para ejecutar_sql/generar_reporte)",
    "incluir_fecha": true/false
}
"""

import os
import sys
import json
import sqlite3
from datetime import datetime

# Añadir path del proyecto
sys.path.insert(0, '/var/www/html')

from dotenv import load_dotenv
load_dotenv('/var/www/html/.env')

from logger_config import get_logger
from email_utils import enviar_email_texto

logger = get_logger(__name__)


def get_db_path():
    """Obtiene la ruta de la BD desde variables de entorno"""
    return os.environ.get('DB_PATH', '/var/www/html/db/aleph70/aleph70.db')


def ejecutar_sql(sql: str) -> list:
    """Ejecuta una consulta SQL y devuelve resultados"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        # Convertir a lista de diccionarios
        return [dict(row) for row in rows]
    finally:
        conn.close()


def formatear_resultados_html(resultados: list, titulo: str = "Resultados") -> str:
    """Formatea resultados SQL como tabla HTML"""
    if not resultados:
        return f"<p>No hay resultados para: {titulo}</p>"
    
    columnas = resultados[0].keys()
    
    html = f"""
    <h3>{titulo}</h3>
    <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse;">
        <tr style="background-color: #f0f0f0;">
            {''.join(f'<th>{col}</th>' for col in columnas)}
        </tr>
    """
    
    for row in resultados[:100]:  # Limitar a 100 filas
        html += "<tr>"
        for col in columnas:
            val = row.get(col, '')
            if isinstance(val, float):
                val = f"{val:,.2f}"
            html += f"<td>{val}</td>"
        html += "</tr>"
    
    html += "</table>"
    
    if len(resultados) > 100:
        html += f"<p><em>Mostrando 100 de {len(resultados)} registros</em></p>"
    else:
        html += f"<p><em>Total: {len(resultados)} registros</em></p>"
    
    return html


def accion_enviar_email(params: dict) -> dict:
    """Envía un email simple"""
    destinatarios = params.get('destinatarios', [])
    asunto = params.get('asunto', 'Notificación automática')
    mensaje = params.get('mensaje', '')
    incluir_fecha = params.get('incluir_fecha', True)
    
    if not destinatarios:
        return {'success': False, 'error': 'No hay destinatarios'}
    
    if incluir_fecha:
        fecha = datetime.now().strftime('%d/%m/%Y %H:%M')
        mensaje = f"{mensaje}\n\n---\nGenerado automáticamente: {fecha}"
    
    for dest in destinatarios:
        exito, msg = enviar_email_texto(dest, asunto, mensaje)
        if not exito:
            logger.error(f"Error enviando a {dest}: {msg}")
            return {'success': False, 'error': msg}
        logger.info(f"Email enviado a {dest}")
    
    return {'success': True, 'mensaje': f'Email enviado a {len(destinatarios)} destinatarios'}


def accion_ejecutar_sql(params: dict) -> dict:
    """Ejecuta SQL y envía resultados por email"""
    sql = params.get('sql', '')
    destinatarios = params.get('destinatarios', [])
    asunto = params.get('asunto', 'Resultados de consulta')
    mensaje = params.get('mensaje', '')
    
    if not sql:
        return {'success': False, 'error': 'No hay consulta SQL'}
    if not destinatarios:
        return {'success': False, 'error': 'No hay destinatarios'}
    
    # Solo permitir SELECT
    if not sql.strip().upper().startswith('SELECT'):
        return {'success': False, 'error': 'Solo se permiten consultas SELECT'}
    
    try:
        resultados = ejecutar_sql(sql)
        html = formatear_resultados_html(resultados, asunto)
        
        cuerpo = f"{mensaje}\n\n{html}" if mensaje else html
        
        for dest in destinatarios:
            exito, msg = enviar_email_texto(dest, asunto, cuerpo, html=True)
            if not exito:
                return {'success': False, 'error': msg}
            logger.info(f"Reporte enviado a {dest}")
        
        return {'success': True, 'mensaje': f'Reporte con {len(resultados)} registros enviado'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def accion_generar_reporte(params: dict) -> dict:
    """Genera un reporte basado en múltiples consultas"""
    consultas = params.get('consultas', [])
    destinatarios = params.get('destinatarios', [])
    asunto = params.get('asunto', 'Reporte automático')
    
    if not consultas:
        return {'success': False, 'error': 'No hay consultas definidas'}
    if not destinatarios:
        return {'success': False, 'error': 'No hay destinatarios'}
    
    html_partes = []
    fecha = datetime.now().strftime('%d/%m/%Y %H:%M')
    html_partes.append(f"<h2>{asunto}</h2><p>Generado: {fecha}</p><hr>")
    
    for q in consultas:
        titulo = q.get('titulo', 'Sección')
        sql = q.get('sql', '')
        
        if not sql.strip().upper().startswith('SELECT'):
            continue
        
        try:
            resultados = ejecutar_sql(sql)
            html_partes.append(formatear_resultados_html(resultados, titulo))
        except Exception as e:
            html_partes.append(f"<p>Error en {titulo}: {e}</p>")
    
    cuerpo = "\n".join(html_partes)
    
    for dest in destinatarios:
        exito, msg = enviar_email_texto(dest, asunto, cuerpo, html=True)
        if not exito:
            return {'success': False, 'error': msg}
        logger.info(f"Reporte enviado a {dest}")
    
    return {'success': True, 'mensaje': f'Reporte enviado a {len(destinatarios)} destinatarios'}


def main():
    """Punto de entrada principal"""
    logger.info("=== batchGenerico iniciado ===")
    
    # Leer parámetros desde variable de entorno
    params_json = os.environ.get('BATCH_PARAMS_JSON', '{}')
    
    try:
        params = json.loads(params_json)
    except json.JSONDecodeError as e:
        logger.error(f"Error parseando parámetros: {e}")
        sys.exit(1)
    
    accion = params.get('accion', '')
    logger.info(f"Acción: {accion}")
    logger.info(f"Parámetros: {json.dumps(params, indent=2, ensure_ascii=False)}")
    
    # Ejecutar acción correspondiente
    if accion == 'enviar_email':
        resultado = accion_enviar_email(params)
    elif accion == 'ejecutar_sql':
        resultado = accion_ejecutar_sql(params)
    elif accion == 'generar_reporte':
        resultado = accion_generar_reporte(params)
    else:
        logger.error(f"Acción no reconocida: {accion}")
        sys.exit(1)
    
    if resultado.get('success'):
        logger.info(f"✅ {resultado.get('mensaje')}")
        sys.exit(0)
    else:
        logger.error(f"❌ {resultado.get('error')}")
        sys.exit(1)


if __name__ == '__main__':
    main()



# ============================================================================
# NOTIFICACIONES - ENDPOINT FALTANTE (HOTFIX)
# ============================================================================

@conciliacion_bp.route('/notificaciones', methods=['GET'])
@conciliacion_bp.route('/api/conciliacion/notificaciones', methods=['GET'])
def get_notificaciones_conciliacion():
    """
    Devuelve notificaciones de conciliación (pendientes, errores, etc).
    Implementación básica para evitar 404.
    """
    try:
        # Por ahora devolvemos vacío para silenciar el error en frontend
        # TODO: Implementar lógica real de notificaciones pendientes
        return jsonify({
            'success': True,
            'notificaciones': [],
            'count': 0
        })
    except Exception as e:
        logger.error(f"Error obteniendo notificaciones conciliación: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

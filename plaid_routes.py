"""
Rutas de Flask para integración con Plaid
"""

from flask import Blueprint, request, jsonify, session, g
from auth_middleware import login_required
from plaid_client import PlaidClient
import sqlite3
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)

# Crear blueprint
plaid_bp = Blueprint('plaid', __name__, url_prefix='/api/plaid')

# Inicializar cliente de Plaid
plaid_client = PlaidClient(environment='sandbox')

def get_db_path():
    """Obtener la ruta de la base de datos según el contexto"""
    # Intentar obtener de g (contexto de Flask)
    if hasattr(g, 'db_path') and g.db_path:
        return g.db_path
    
    # Intentar obtener empresa_codigo de la sesión
    empresa_codigo = session.get('empresa_codigo')
    if empresa_codigo:
        return f'/var/www/html/db/{empresa_codigo}/{empresa_codigo}.db'
    
    # Fallback a usuarios_sistema.db
    return '/var/www/html/db/usuarios_sistema.db'

@plaid_bp.route('/create-link-token', methods=['POST'])
@login_required
def create_link_token():
    """
    Crear un link token para iniciar el flujo de conexión bancaria
    """
    try:
        user_id = session.get('user_id')
        username = session.get('username')
        
        if not user_id:
            return jsonify({'error': 'Usuario no autenticado'}), 401
        
        # Obtener redirect_uri del request (opcional)
        try:
            data = request.get_json(silent=True) or {}
        except:
            data = {}
        redirect_uri = data.get('redirect_uri')
        
        # Crear link token
        result = plaid_client.create_link_token(
            user_id=user_id,
            username=username,
            redirect_uri=redirect_uri
        )
        
        logger.info(f"[PLAID] Link token creado para usuario {user_id}")
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"[PLAID] Error creando link token: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@plaid_bp.route('/exchange-token', methods=['POST'])
@login_required
def exchange_token():
    """
    Intercambiar public_token por access_token y guardar en BD
    """
    try:
        logger.info("[PLAID] Iniciando exchange_token")
        user_id = session.get('user_id')
        empresa_id = session.get('empresa_id')
        logger.info(f"[PLAID] user_id={user_id}, empresa_id={empresa_id}")
        
        if not user_id or not empresa_id:
            logger.error("[PLAID] Usuario o empresa no válidos")
            return jsonify({'error': 'Usuario o empresa no válidos'}), 401
        
        try:
            data = request.get_json(silent=True) or {}
        except Exception as e:
            logger.error(f"[PLAID] Error parseando JSON: {e}")
            data = {}
        public_token = data.get('public_token')
        logger.info(f"[PLAID] public_token recibido: {public_token[:20]}..." if public_token else "[PLAID] No public_token")
        
        if not public_token:
            logger.error("[PLAID] public_token requerido pero no recibido")
            return jsonify({'error': 'public_token requerido'}), 400
        
        # Intercambiar token
        logger.info("[PLAID] Intercambiando public_token por access_token")
        result = plaid_client.exchange_public_token(public_token)
        access_token = result['access_token']
        item_id = result['item_id']
        logger.info(f"[PLAID] Token intercambiado exitosamente. item_id={item_id}")
        
        # Obtener cuentas
        logger.info("[PLAID] Obteniendo cuentas")
        accounts = plaid_client.get_accounts(access_token)
        logger.info(f"[PLAID] {len(accounts)} cuentas obtenidas")
        
        # Guardar en base de datos
        db_path = get_db_path()
        logger.info(f"[PLAID] Usando base de datos: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Crear tabla si no existe
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plaid_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                empresa_id INTEGER NOT NULL,
                item_id TEXT NOT NULL UNIQUE,
                access_token TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_sync TIMESTAMP,
                sync_cursor TEXT,
                active INTEGER DEFAULT 1
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plaid_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT NOT NULL,
                account_id TEXT NOT NULL UNIQUE,
                name TEXT,
                official_name TEXT,
                type TEXT,
                subtype TEXT,
                mask TEXT,
                currency TEXT DEFAULT 'EUR',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insertar item
        cursor.execute('''
            INSERT OR REPLACE INTO plaid_items 
            (user_id, empresa_id, item_id, access_token, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, empresa_id, item_id, access_token, datetime.now()))
        
        # Insertar cuentas
        for account in accounts:
            # Convertir tipos de Plaid a strings para SQLite
            account_type = str(account['type']) if account.get('type') else None
            account_subtype = str(account['subtype']) if account.get('subtype') else None
            currency = str(account['balance']['currency']) if account.get('balance', {}).get('currency') else 'EUR'
            
            cursor.execute('''
                INSERT OR REPLACE INTO plaid_accounts
                (item_id, account_id, name, official_name, type, subtype, mask, currency)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item_id,
                account['account_id'],
                account['name'],
                account.get('official_name'),
                account_type,
                account_subtype,
                account.get('mask'),
                currency
            ))
        
        logger.info("[PLAID] Haciendo commit a la base de datos")
        conn.commit()
        conn.close()
        logger.info("[PLAID] Conexión a BD cerrada")
        
        logger.info(f"[PLAID] ✅ Conexión bancaria guardada exitosamente: {len(accounts)} cuentas")
        
        return jsonify({
            'success': True,
            'item_id': item_id,
            'accounts': accounts
        }), 200
        
    except Exception as e:
        logger.error(f"[PLAID] ❌ Error intercambiando token: {e}", exc_info=True)
        import traceback
        logger.error(f"[PLAID] Traceback completo:\n{traceback.format_exc()}")
        return jsonify({'error': f'Error intercambiando token: {str(e)}'}), 500

@plaid_bp.route('/accounts', methods=['GET'])
@login_required
def get_accounts():
    """
    Obtener cuentas bancarias conectadas del usuario
    """
    try:
        user_id = session.get('user_id')
        empresa_id = session.get('empresa_id')
        
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Obtener items activos
        cursor.execute('''
            SELECT item_id, access_token
            FROM plaid_items
            WHERE user_id = ? AND empresa_id = ? AND active = 1
        ''', (user_id, empresa_id))
        
        items = cursor.fetchall()
        
        all_accounts = []
        
        for item in items:
            # Obtener cuentas de la BD
            cursor.execute('''
                SELECT account_id, name, official_name, type, subtype, mask, currency
                FROM plaid_accounts
                WHERE item_id = ?
            ''', (item['item_id'],))
            
            accounts = cursor.fetchall()
            
            # Obtener balance actualizado de Plaid
            try:
                live_accounts = plaid_client.get_accounts(item['access_token'])
                balance_map = {acc['account_id']: acc['balance'] for acc in live_accounts}
            except:
                balance_map = {}
            
            for account in accounts:
                all_accounts.append({
                    'account_id': account['account_id'],
                    'name': account['name'],
                    'official_name': account['official_name'],
                    'type': account['type'],
                    'subtype': account['subtype'],
                    'mask': account['mask'],
                    'currency': account['currency'],
                    'balance': balance_map.get(account['account_id'], {
                        'current': 0,
                        'available': 0,
                        'currency': account['currency']
                    })
                })
        
        conn.close()
        
        return jsonify(all_accounts), 200
        
    except Exception as e:
        logger.error(f"[PLAID] Error obteniendo cuentas: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@plaid_bp.route('/transactions', methods=['GET'])
@login_required
def get_transactions():
    """
    Obtener transacciones bancarias
    """
    try:
        logger.info("[PLAID] Iniciando get_transactions")
        user_id = session.get('user_id')
        empresa_id = session.get('empresa_id')
        
        if not user_id or not empresa_id:
            logger.error("[PLAID] Usuario o empresa no válidos")
            return jsonify({'error': 'Usuario o empresa no válidos'}), 401
        
        # Parámetros
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        account_id = request.args.get('account_id')
        
        logger.info(f"[PLAID] Parámetros: start_date={start_date_str}, end_date={end_date_str}, account_id={account_id}")
        
        # Validar fechas
        if not start_date_str or not end_date_str:
            logger.error("[PLAID] Fechas requeridas")
            return jsonify({'error': 'start_date y end_date son requeridos'}), 400
        
        # Convertir strings a objetos date
        from datetime import date as date_type
        try:
            start_date = date_type.fromisoformat(start_date_str)
            end_date = date_type.fromisoformat(end_date_str)
            logger.info(f"[PLAID] Fechas convertidas: {start_date} - {end_date}")
        except ValueError as e:
            logger.error(f"[PLAID] Error convirtiendo fechas: {e}")
            return jsonify({'error': 'Formato de fecha inválido. Use YYYY-MM-DD'}), 400
        
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Obtener access token del item
        if account_id:
            logger.info(f"[PLAID] Buscando access_token para account_id={account_id}")
            cursor.execute('''
                SELECT i.access_token, a.item_id
                FROM plaid_accounts a
                JOIN plaid_items i ON a.item_id = i.item_id
                WHERE a.account_id = ? AND i.user_id = ? AND i.empresa_id = ? AND i.active = 1
            ''', (account_id, user_id, empresa_id))
        else:
            logger.info("[PLAID] Buscando access_token para todas las cuentas")
            cursor.execute('''
                SELECT access_token, item_id
                FROM plaid_items
                WHERE user_id = ? AND empresa_id = ? AND active = 1
                LIMIT 1
            ''', (user_id, empresa_id))
        
        item = cursor.fetchone()
        conn.close()
        
        if not item:
            logger.warning("[PLAID] No hay cuentas bancarias conectadas")
            return jsonify([]), 200  # Retornar array vacío en lugar de error
        
        logger.info(f"[PLAID] Access token encontrado para item_id={item['item_id']}")
        
        # Obtener transacciones de Plaid
        account_ids = [account_id] if account_id else None
        logger.info(f"[PLAID] Obteniendo transacciones de Plaid...")
        transactions = plaid_client.get_transactions(
            access_token=item['access_token'],
            start_date=start_date,
            end_date=end_date,
            account_ids=account_ids
        )
        
        logger.info(f"[PLAID] ✅ {len(transactions)} transacciones obtenidas")
        return jsonify(transactions), 200
        
    except Exception as e:
        logger.error(f"[PLAID] ❌ Error obteniendo transacciones: {e}", exc_info=True)
        import traceback
        logger.error(f"[PLAID] Traceback:\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@plaid_bp.route('/sync', methods=['POST'])
@login_required
def sync_transactions():
    """
    Sincronizar transacciones bancarias (método eficiente)
    """
    try:
        user_id = session.get('user_id')
        empresa_id = session.get('empresa_id')
        
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Obtener todos los items activos
        cursor.execute('''
            SELECT item_id, access_token, sync_cursor
            FROM plaid_items
            WHERE user_id = ? AND empresa_id = ? AND active = 1
        ''', (user_id, empresa_id))
        
        items = cursor.fetchall()
        
        total_added = 0
        total_modified = 0
        total_removed = 0
        
        for item in items:
            try:
                # Sincronizar transacciones
                result = plaid_client.sync_transactions(
                    access_token=item['access_token'],
                    cursor=item['sync_cursor']
                )
                
                total_added += len(result['added'])
                total_modified += len(result['modified'])
                total_removed += len(result['removed'])
                
                # Actualizar cursor
                cursor.execute('''
                    UPDATE plaid_items
                    SET sync_cursor = ?, last_sync = ?
                    WHERE item_id = ?
                ''', (result['cursor'], datetime.now(), item['item_id']))
                
                # TODO: Guardar transacciones en tu base de datos
                # Aquí deberías insertar las transacciones en tu tabla de movimientos bancarios
                
            except Exception as e:
                logger.error(f"[PLAID] Error sincronizando item {item['item_id']}: {e}")
                continue
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'added': total_added,
            'modified': total_modified,
            'removed': total_removed
        }), 200
        
    except Exception as e:
        logger.error(f"[PLAID] Error en sincronización: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@plaid_bp.route('/disconnect/<item_id>', methods=['DELETE'])
@login_required
def disconnect_bank(item_id):
    """
    Desconectar una cuenta bancaria
    """
    try:
        user_id = session.get('user_id')
        empresa_id = session.get('empresa_id')
        
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        
        # Verificar que el item pertenece al usuario
        cursor.execute('''
            UPDATE plaid_items
            SET active = 0
            WHERE item_id = ? AND user_id = ? AND empresa_id = ?
        ''', (item_id, user_id, empresa_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Item no encontrado'}), 404
        
        conn.commit()
        conn.close()
        
        logger.info(f"[PLAID] Cuenta bancaria desconectada: {item_id}")
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        logger.error(f"[PLAID] Error desconectando banco: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

"""
Sistema de suscripciones con Stripe para Aleph70
"""

from flask import Blueprint, request, jsonify, redirect, url_for, session
import stripe
import os
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging
import json

load_dotenv()

logger = logging.getLogger(__name__)

# Configuración de Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
STRIPE_PRICE_ID = os.getenv('STRIPE_PRICE_ID')  # ID del precio en Stripe (20€/mes)

# Blueprint
subscription_bp = Blueprint('subscription', __name__)

# Base de datos de suscripciones
SUBSCRIPTIONS_DB = os.path.join(os.path.dirname(__file__), 'db', 'subscriptions.db')

def init_subscriptions_db():
    """Inicializa la base de datos de suscripciones"""
    os.makedirs(os.path.dirname(SUBSCRIPTIONS_DB), exist_ok=True)
    conn = sqlite3.connect(SUBSCRIPTIONS_DB)
    cursor = conn.cursor()
    
    # Tabla de suscripciones
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id TEXT NOT NULL,
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            status TEXT DEFAULT 'inactive',
            plan TEXT DEFAULT 'premium',
            price_cents INTEGER DEFAULT 2000,
            currency TEXT DEFAULT 'eur',
            current_period_start DATETIME,
            current_period_end DATETIME,
            cancel_at_period_end INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(empresa_id)
        )
    ''')
    
    # Tabla de historial de pagos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id TEXT NOT NULL,
            stripe_payment_intent_id TEXT,
            stripe_invoice_id TEXT,
            amount_cents INTEGER,
            currency TEXT DEFAULT 'eur',
            status TEXT,
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla de eventos de webhook
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS webhook_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stripe_event_id TEXT UNIQUE,
            event_type TEXT,
            processed INTEGER DEFAULT 0,
            data TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Base de datos de suscripciones inicializada")

# Inicializar BD al cargar el módulo
init_subscriptions_db()

def get_subscription_db():
    """Obtiene conexión a la BD de suscripciones"""
    conn = sqlite3.connect(SUBSCRIPTIONS_DB)
    conn.row_factory = sqlite3.Row
    return conn

@subscription_bp.route('/api/subscription/config', methods=['GET'])
def get_stripe_config():
    """Devuelve la configuración pública de Stripe"""
    return jsonify({
        'publishableKey': STRIPE_PUBLISHABLE_KEY,
        'priceId': STRIPE_PRICE_ID,
        'price': 20.00,
        'currency': 'eur'
    })

@subscription_bp.route('/api/subscription/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """Crea una sesión de checkout de Stripe"""
    try:
        data = request.get_json()
        empresa_id = data.get('empresa_id')
        email = data.get('email')
        success_url = data.get('success_url', request.host_url + 'subscription/success')
        cancel_url = data.get('cancel_url', request.host_url + 'subscription/cancel')
        
        if not empresa_id or not email:
            return jsonify({'error': 'empresa_id y email son requeridos'}), 400
        
        # Buscar o crear cliente en Stripe
        conn = get_subscription_db()
        cursor = conn.cursor()
        cursor.execute('SELECT stripe_customer_id FROM subscriptions WHERE empresa_id = ?', (empresa_id,))
        row = cursor.fetchone()
        
        if row and row['stripe_customer_id']:
            customer_id = row['stripe_customer_id']
        else:
            # Crear nuevo cliente en Stripe
            customer = stripe.Customer.create(
                email=email,
                metadata={'empresa_id': empresa_id}
            )
            customer_id = customer.id
            
            # Guardar en BD
            cursor.execute('''
                INSERT OR REPLACE INTO subscriptions (empresa_id, stripe_customer_id, status)
                VALUES (?, ?, 'pending')
            ''', (empresa_id, customer_id))
            conn.commit()
        
        conn.close()
        
        # Crear sesión de checkout con 30 días de prueba gratuita
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': STRIPE_PRICE_ID,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=cancel_url,
            metadata={
                'empresa_id': empresa_id
            },
            subscription_data={
                'trial_period_days': 30,
                'metadata': {
                    'empresa_id': empresa_id
                }
            },
            locale='es',
            allow_promotion_codes=True,
        )
        
        logger.info(f"Checkout session creada para empresa {empresa_id}: {checkout_session.id}")
        
        return jsonify({
            'sessionId': checkout_session.id,
            'url': checkout_session.url
        })
        
    except stripe.error.StripeError as e:
        logger.error(f"Error de Stripe: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error creando checkout session: {e}")
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/api/subscription/portal', methods=['POST'])
def create_portal_session():
    """Crea una sesión del portal de cliente de Stripe para gestionar suscripción"""
    try:
        data = request.get_json()
        empresa_id = data.get('empresa_id')
        return_url = data.get('return_url', request.host_url)
        
        if not empresa_id:
            return jsonify({'error': 'empresa_id es requerido'}), 400
        
        conn = get_subscription_db()
        cursor = conn.cursor()
        cursor.execute('SELECT stripe_customer_id FROM subscriptions WHERE empresa_id = ?', (empresa_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row or not row['stripe_customer_id']:
            return jsonify({'error': 'No se encontró cliente de Stripe'}), 404
        
        portal_session = stripe.billing_portal.Session.create(
            customer=row['stripe_customer_id'],
            return_url=return_url,
        )
        
        return jsonify({'url': portal_session.url})
        
    except Exception as e:
        logger.error(f"Error creando portal session: {e}")
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/api/subscription/status/<empresa_id>', methods=['GET'])
def get_subscription_status(empresa_id):
    """Obtiene el estado de la suscripción de una empresa"""
    try:
        conn = get_subscription_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM subscriptions WHERE empresa_id = ?
        ''', (empresa_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({
                'active': False,
                'status': 'none',
                'message': 'Sin suscripción'
            })
        
        # Verificar si está activa (incluye free_trial)
        is_active = row['status'] in ['active', 'trialing', 'free_trial']
        
        # Calcular días restantes
        days_remaining = None
        if row['current_period_end']:
            end_date = datetime.fromisoformat(row['current_period_end'].replace('Z', '+00:00'))
            days_remaining = (end_date - datetime.now()).days
        
        return jsonify({
            'active': is_active,
            'status': row['status'],
            'plan': row['plan'],
            'current_period_end': row['current_period_end'],
            'days_remaining': days_remaining,
            'cancel_at_period_end': bool(row['cancel_at_period_end']),
            'stripe_subscription_id': row['stripe_subscription_id']
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo estado de suscripción: {e}")
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/api/subscription/webhook', methods=['POST'])
def stripe_webhook():
    """Webhook para recibir eventos de Stripe"""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Guardar evento en BD
    conn = get_subscription_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO webhook_events (stripe_event_id, event_type, data)
            VALUES (?, ?, ?)
        ''', (event['id'], event['type'], json.dumps(event['data'])))
        conn.commit()
    except sqlite3.IntegrityError:
        # Evento ya procesado
        conn.close()
        return jsonify({'status': 'already processed'}), 200
    
    # Procesar evento
    event_type = event['type']
    data = event['data']['object']
    
    logger.info(f"Webhook recibido: {event_type}")
    
    if event_type == 'checkout.session.completed':
        # Pago completado
        empresa_id = data.get('metadata', {}).get('empresa_id')
        subscription_id = data.get('subscription')
        customer_id = data.get('customer')
        
        if empresa_id and subscription_id:
            # Obtener detalles de la suscripción
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            cursor.execute('''
                UPDATE subscriptions SET
                    stripe_subscription_id = ?,
                    stripe_customer_id = ?,
                    status = ?,
                    current_period_start = datetime(?, 'unixepoch'),
                    current_period_end = datetime(?, 'unixepoch'),
                    updated_at = CURRENT_TIMESTAMP
                WHERE empresa_id = ?
            ''', (
                subscription_id,
                customer_id,
                subscription.status,
                subscription.current_period_start,
                subscription.current_period_end,
                empresa_id
            ))
            conn.commit()
            logger.info(f"Suscripción activada para empresa {empresa_id}")
    
    elif event_type == 'customer.subscription.updated':
        subscription_id = data.get('id')
        status = data.get('status')
        cancel_at_period_end = data.get('cancel_at_period_end', False)
        
        cursor.execute('''
            UPDATE subscriptions SET
                status = ?,
                current_period_start = datetime(?, 'unixepoch'),
                current_period_end = datetime(?, 'unixepoch'),
                cancel_at_period_end = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE stripe_subscription_id = ?
        ''', (
            status,
            data.get('current_period_start'),
            data.get('current_period_end'),
            1 if cancel_at_period_end else 0,
            subscription_id
        ))
        conn.commit()
        logger.info(f"Suscripción actualizada: {subscription_id} -> {status}")
    
    elif event_type == 'customer.subscription.deleted':
        subscription_id = data.get('id')
        
        cursor.execute('''
            UPDATE subscriptions SET
                status = 'canceled',
                updated_at = CURRENT_TIMESTAMP
            WHERE stripe_subscription_id = ?
        ''', (subscription_id,))
        conn.commit()
        logger.info(f"Suscripción cancelada: {subscription_id}")
    
    elif event_type == 'invoice.paid':
        # Registrar pago exitoso
        customer_id = data.get('customer')
        
        cursor.execute('SELECT empresa_id FROM subscriptions WHERE stripe_customer_id = ?', (customer_id,))
        row = cursor.fetchone()
        
        if row:
            cursor.execute('''
                INSERT INTO payment_history (empresa_id, stripe_invoice_id, amount_cents, currency, status, description)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                row['empresa_id'],
                data.get('id'),
                data.get('amount_paid'),
                data.get('currency'),
                'paid',
                f"Factura {data.get('number', 'N/A')}"
            ))
            conn.commit()
    
    elif event_type == 'invoice.payment_failed':
        # Pago fallido
        customer_id = data.get('customer')
        
        cursor.execute('SELECT empresa_id FROM subscriptions WHERE stripe_customer_id = ?', (customer_id,))
        row = cursor.fetchone()
        
        if row:
            cursor.execute('''
                UPDATE subscriptions SET status = 'past_due', updated_at = CURRENT_TIMESTAMP
                WHERE empresa_id = ?
            ''', (row['empresa_id'],))
            conn.commit()
            logger.warning(f"Pago fallido para empresa {row['empresa_id']}")
    
    # Marcar evento como procesado
    cursor.execute('UPDATE webhook_events SET processed = 1 WHERE stripe_event_id = ?', (event['id'],))
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success'}), 200

@subscription_bp.route('/api/subscription/cancel', methods=['POST'])
def cancel_subscription():
    """Cancela una suscripción al final del período"""
    try:
        data = request.get_json()
        empresa_id = data.get('empresa_id')
        
        if not empresa_id:
            return jsonify({'error': 'empresa_id es requerido'}), 400
        
        conn = get_subscription_db()
        cursor = conn.cursor()
        cursor.execute('SELECT stripe_subscription_id FROM subscriptions WHERE empresa_id = ?', (empresa_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row or not row['stripe_subscription_id']:
            return jsonify({'error': 'No se encontró suscripción activa'}), 404
        
        # Cancelar al final del período
        subscription = stripe.Subscription.modify(
            row['stripe_subscription_id'],
            cancel_at_period_end=True
        )
        
        return jsonify({
            'success': True,
            'message': 'Suscripción se cancelará al final del período',
            'cancel_at': subscription.current_period_end
        })
        
    except Exception as e:
        logger.error(f"Error cancelando suscripción: {e}")
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/api/subscription/reactivate', methods=['POST'])
def reactivate_subscription():
    """Reactiva una suscripción cancelada"""
    try:
        data = request.get_json()
        empresa_id = data.get('empresa_id')
        
        if not empresa_id:
            return jsonify({'error': 'empresa_id es requerido'}), 400
        
        conn = get_subscription_db()
        cursor = conn.cursor()
        cursor.execute('SELECT stripe_subscription_id FROM subscriptions WHERE empresa_id = ?', (empresa_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row or not row['stripe_subscription_id']:
            return jsonify({'error': 'No se encontró suscripción'}), 404
        
        # Reactivar
        subscription = stripe.Subscription.modify(
            row['stripe_subscription_id'],
            cancel_at_period_end=False
        )
        
        return jsonify({
            'success': True,
            'message': 'Suscripción reactivada',
            'status': subscription.status
        })
        
    except Exception as e:
        logger.error(f"Error reactivando suscripción: {e}")
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/api/subscription/start-free-trial', methods=['POST'])
def start_free_trial():
    """Inicia una prueba gratuita de 15 días SIN datos de pago"""
    try:
        data = request.get_json()
        empresa_id = data.get('empresa_id')
        email = data.get('email')
        
        if not empresa_id:
            return jsonify({'error': 'empresa_id es requerido'}), 400
        
        conn = get_subscription_db()
        cursor = conn.cursor()
        
        # Verificar si ya tiene o tuvo una prueba gratuita
        cursor.execute('SELECT * FROM subscriptions WHERE empresa_id = ?', (empresa_id,))
        existing = cursor.fetchone()
        
        if existing:
            # Si ya tiene suscripción activa o en trial
            if existing['status'] in ['active', 'trialing', 'free_trial']:
                conn.close()
                return jsonify({
                    'error': 'Ya tienes una suscripción o prueba activa',
                    'status': existing['status']
                }), 400
            
            # Si ya usó el trial gratuito (verificar si trial_used existe)
            try:
                if existing['trial_used']:
                    conn.close()
                    return jsonify({
                        'error': 'Ya has utilizado tu período de prueba gratuita',
                        'message': 'Puedes suscribirte para continuar usando Aleph70'
                    }), 400
            except (KeyError, IndexError):
                pass  # Campo no existe, continuar
        
        # Calcular fechas del trial (15 días)
        trial_start = datetime.now()
        trial_end = trial_start + timedelta(days=15)
        
        # Insertar o actualizar suscripción con trial gratuito
        cursor.execute('''
            INSERT INTO subscriptions (
                empresa_id, 
                status, 
                plan,
                current_period_start, 
                current_period_end,
                created_at,
                updated_at
            ) VALUES (?, 'free_trial', 'trial', ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(empresa_id) DO UPDATE SET
                status = 'free_trial',
                plan = 'trial',
                current_period_start = ?,
                current_period_end = ?,
                updated_at = CURRENT_TIMESTAMP
        ''', (empresa_id, trial_start.isoformat(), trial_end.isoformat(), 
              trial_start.isoformat(), trial_end.isoformat()))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Prueba gratuita de 15 días iniciada para empresa {empresa_id}")
        
        return jsonify({
            'success': True,
            'message': 'Prueba gratuita de 15 días activada',
            'trial_end': trial_end.isoformat(),
            'days_remaining': 15
        })
        
    except Exception as e:
        logger.error(f"Error iniciando prueba gratuita: {e}")
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/api/subscription/payment-history/<empresa_id>', methods=['GET'])
def get_payment_history(empresa_id):
    """Obtiene el historial de pagos de una empresa"""
    try:
        conn = get_subscription_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM payment_history 
            WHERE empresa_id = ? 
            ORDER BY created_at DESC 
            LIMIT 50
        ''', (empresa_id,))
        rows = cursor.fetchall()
        conn.close()
        
        payments = []
        for row in rows:
            payments.append({
                'id': row['id'],
                'amount': row['amount_cents'] / 100 if row['amount_cents'] else 0,
                'currency': row['currency'],
                'status': row['status'],
                'description': row['description'],
                'created_at': row['created_at']
            })
        
        return jsonify({'payments': payments})
        
    except Exception as e:
        logger.error(f"Error obteniendo historial de pagos: {e}")
        return jsonify({'error': str(e)}), 500

# Rutas de páginas
@subscription_bp.route('/subscription/success')
def subscription_success():
    """Página de éxito tras el pago"""
    session_id = request.args.get('session_id')
    return f'''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>¡Suscripción Activada! | Aleph70</title>
        <link rel="stylesheet" href="/public/css/styles.css">
        <style>
            body {{ 
                display: flex; 
                justify-content: center; 
                align-items: center; 
                min-height: 100vh; 
                background: linear-gradient(135deg, #0b1220 0%, #1a2332 100%);
                margin: 0;
                font-family: 'Inter', sans-serif;
            }}
            .success-card {{
                background: rgba(255,255,255,0.05);
                border-radius: 20px;
                padding: 3rem;
                text-align: center;
                max-width: 500px;
                border: 1px solid rgba(255,255,255,0.1);
            }}
            .success-icon {{
                font-size: 4rem;
                color: #2ecc71;
                margin-bottom: 1rem;
            }}
            h1 {{ color: #fff; margin-bottom: 1rem; }}
            p {{ color: #9ca3af; line-height: 1.6; }}
            .btn {{
                display: inline-block;
                margin-top: 2rem;
                padding: 1rem 2rem;
                background: linear-gradient(135deg, #3b82f6, #8b5cf6);
                color: #fff;
                text-decoration: none;
                border-radius: 10px;
                font-weight: 600;
                transition: transform 0.2s;
            }}
            .btn:hover {{ transform: translateY(-2px); }}
        </style>
    </head>
    <body>
        <div class="success-card">
            <div class="success-icon">✓</div>
            <h1>¡Suscripción Activada!</h1>
            <p>Tu suscripción a Aleph70 Premium se ha activado correctamente.</p>
            <p>Ya tienes acceso completo a todas las funcionalidades.</p>
            <a href="/LOGIN.html" class="btn">Acceder a Aleph70</a>
        </div>
        <script>
            // Limpiar la URL del session_id
            if (window.history.replaceState) {{
                window.history.replaceState(null, null, window.location.pathname);
            }}
        </script>
    </body>
    </html>
    '''

@subscription_bp.route('/subscription/cancel')
def subscription_cancel():
    """Página de cancelación del pago"""
    return '''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Pago Cancelado | Aleph70</title>
        <link rel="stylesheet" href="/public/css/styles.css">
        <style>
            body { 
                display: flex; 
                justify-content: center; 
                align-items: center; 
                min-height: 100vh; 
                background: linear-gradient(135deg, #0b1220 0%, #1a2332 100%);
                margin: 0;
                font-family: 'Inter', sans-serif;
            }
            .cancel-card {
                background: rgba(255,255,255,0.05);
                border-radius: 20px;
                padding: 3rem;
                text-align: center;
                max-width: 500px;
                border: 1px solid rgba(255,255,255,0.1);
            }
            .cancel-icon {
                font-size: 4rem;
                color: #f59e0b;
                margin-bottom: 1rem;
            }
            h1 { color: #fff; margin-bottom: 1rem; }
            p { color: #9ca3af; line-height: 1.6; }
            .btn {
                display: inline-block;
                margin-top: 2rem;
                padding: 1rem 2rem;
                background: rgba(255,255,255,0.1);
                color: #fff;
                text-decoration: none;
                border-radius: 10px;
                font-weight: 600;
                transition: background 0.2s;
                margin-right: 1rem;
            }
            .btn:hover { background: rgba(255,255,255,0.2); }
            .btn-primary {
                background: linear-gradient(135deg, #3b82f6, #8b5cf6);
            }
        </style>
    </head>
    <body>
        <div class="cancel-card">
            <div class="cancel-icon">⚠</div>
            <h1>Pago Cancelado</h1>
            <p>El proceso de pago ha sido cancelado.</p>
            <p>No se ha realizado ningún cargo a tu tarjeta.</p>
            <a href="/#planes" class="btn">Volver a Planes</a>
            <a href="/#contacto" class="btn btn-primary">Contactar</a>
        </div>
    </body>
    </html>
    '''

"""
Cliente de Plaid para integración bancaria
"""

import os
import plaid
from plaid.api import plaid_api
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.accounts_get_request import AccountsGetRequest
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class PlaidClient:
    """Cliente para interactuar con la API de Plaid"""
    
    def __init__(self, client_id=None, secret=None, environment='sandbox'):
        """
        Inicializar cliente de Plaid
        
        Args:
            client_id: Client ID de Plaid
            secret: Secret de Plaid
            environment: 'sandbox', 'development' o 'production'
        """
        self.client_id = client_id or os.getenv('PLAID_CLIENT_ID', '6914f270a7e39a001d912b10')
        self.secret = secret or os.getenv('PLAID_SECRET', '445a15b6c94bc17c05be8fd59822f4')
        
        # Configurar ambiente
        if environment == 'sandbox':
            host = plaid.Environment.Sandbox
        elif environment == 'development':
            host = plaid.Environment.Development
        else:
            host = plaid.Environment.Production
        
        # Crear configuración
        configuration = plaid.Configuration(
            host=host,
            api_key={
                'clientId': self.client_id,
                'secret': self.secret,
            }
        )
        
        # Crear cliente API
        api_client = plaid.ApiClient(configuration)
        self.client = plaid_api.PlaidApi(api_client)
        
        logger.info(f"[PLAID] Cliente inicializado en modo {environment}")
    
    def create_link_token(self, user_id, username, redirect_uri=None):
        """
        Crear un Link Token para iniciar el flujo de conexión bancaria
        
        Args:
            user_id: ID del usuario en tu sistema
            username: Nombre del usuario
            redirect_uri: URI de redirección (opcional)
        
        Returns:
            dict con link_token y expiration
        """
        try:
            # Preparar parámetros del request
            request_params = {
                'user': LinkTokenCreateRequestUser(
                    client_user_id=str(user_id)
                ),
                'client_name': "Aleph ERP",
                'products': [Products("transactions"), Products("auth")],
                'country_codes': [CountryCode('ES'), CountryCode('GB'), CountryCode('US')],
                'language': 'es'
            }
            
            # Solo agregar redirect_uri si se proporciona
            if redirect_uri:
                request_params['redirect_uri'] = redirect_uri
            
            request = LinkTokenCreateRequest(**request_params)
            
            response = self.client.link_token_create(request)
            
            logger.info(f"[PLAID] Link token creado para usuario {user_id}")
            
            return {
                'link_token': response['link_token'],
                'expiration': response['expiration']
            }
            
        except plaid.ApiException as e:
            logger.error(f"[PLAID] Error creando link token: {e}")
            raise Exception(f"Error creando link token: {e}")
    
    def exchange_public_token(self, public_token):
        """
        Intercambiar public_token por access_token
        
        Args:
            public_token: Token público recibido del frontend
        
        Returns:
            dict con access_token e item_id
        """
        try:
            request = ItemPublicTokenExchangeRequest(
                public_token=public_token
            )
            
            response = self.client.item_public_token_exchange(request)
            
            logger.info(f"[PLAID] Access token obtenido para item {response['item_id']}")
            
            return {
                'access_token': response['access_token'],
                'item_id': response['item_id']
            }
            
        except plaid.ApiException as e:
            logger.error(f"[PLAID] Error intercambiando token: {e}")
            raise Exception(f"Error intercambiando token: {e}")
    
    def get_accounts(self, access_token):
        """
        Obtener cuentas bancarias del usuario
        
        Args:
            access_token: Access token de Plaid
        
        Returns:
            Lista de cuentas
        """
        try:
            request = AccountsGetRequest(
                access_token=access_token
            )
            
            response = self.client.accounts_get(request)
            
            accounts = []
            for account in response['accounts']:
                accounts.append({
                    'account_id': account['account_id'],
                    'name': account['name'],
                    'official_name': account.get('official_name'),
                    'type': account['type'],
                    'subtype': account['subtype'],
                    'mask': account.get('mask'),
                    'balance': {
                        'current': account['balances']['current'],
                        'available': account['balances'].get('available'),
                        'currency': account['balances'].get('iso_currency_code', 'EUR')
                    }
                })
            
            logger.info(f"[PLAID] {len(accounts)} cuentas obtenidas")
            return accounts
            
        except plaid.ApiException as e:
            logger.error(f"[PLAID] Error obteniendo cuentas: {e}")
            raise Exception(f"Error obteniendo cuentas: {e}")
    
    def get_transactions(self, access_token, start_date=None, end_date=None, account_ids=None):
        """
        Obtener transacciones bancarias
        
        Args:
            access_token: Access token de Plaid
            start_date: Fecha de inicio (datetime o string YYYY-MM-DD)
            end_date: Fecha de fin (datetime o string YYYY-MM-DD)
            account_ids: Lista de IDs de cuentas (opcional)
        
        Returns:
            Lista de transacciones
        """
        try:
            # Fechas por defecto: últimos 30 días
            if not end_date:
                end_date = datetime.now().date()
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).date()
            
            # Convertir a string si son datetime
            if isinstance(start_date, datetime):
                start_date = start_date.date()
            if isinstance(end_date, datetime):
                end_date = end_date.date()
            
            # Preparar opciones
            options = {
                'count': 500,
                'offset': 0
            }
            
            # Solo agregar account_ids si se proporciona
            if account_ids:
                options['account_ids'] = account_ids
            
            request = TransactionsGetRequest(
                access_token=access_token,
                start_date=start_date,
                end_date=end_date,
                options=options
            )
            
            response = self.client.transactions_get(request)
            
            transactions = []
            for txn in response['transactions']:
                transactions.append({
                    'transaction_id': txn['transaction_id'],
                    'account_id': txn['account_id'],
                    'amount': txn['amount'],
                    'currency': txn.get('iso_currency_code', 'EUR'),
                    'date': str(txn['date']),
                    'name': txn['name'],
                    'merchant_name': txn.get('merchant_name'),
                    'category': txn.get('category', []),
                    'pending': txn['pending'],
                    'payment_channel': txn.get('payment_channel')
                })
            
            logger.info(f"[PLAID] {len(transactions)} transacciones obtenidas")
            return transactions
            
        except plaid.ApiException as e:
            logger.error(f"[PLAID] Error obteniendo transacciones: {e}")
            raise Exception(f"Error obteniendo transacciones: {e}")
    
    def sync_transactions(self, access_token, cursor=None):
        """
        Sincronizar transacciones usando el endpoint de sync (más eficiente)
        
        Args:
            access_token: Access token de Plaid
            cursor: Cursor de la última sincronización
        
        Returns:
            dict con transacciones añadidas, modificadas, eliminadas y nuevo cursor
        """
        try:
            from plaid.model.transactions_sync_request import TransactionsSyncRequest
            
            request = TransactionsSyncRequest(
                access_token=access_token,
                cursor=cursor
            )
            
            response = self.client.transactions_sync(request)
            
            result = {
                'added': [],
                'modified': [],
                'removed': [],
                'cursor': response['next_cursor'],
                'has_more': response['has_more']
            }
            
            # Transacciones añadidas
            for txn in response.get('added', []):
                result['added'].append({
                    'transaction_id': txn['transaction_id'],
                    'account_id': txn['account_id'],
                    'amount': txn['amount'],
                    'currency': txn.get('iso_currency_code', 'EUR'),
                    'date': str(txn['date']),
                    'name': txn['name'],
                    'merchant_name': txn.get('merchant_name'),
                    'category': txn.get('category', []),
                    'pending': txn['pending']
                })
            
            # Transacciones modificadas
            for txn in response.get('modified', []):
                result['modified'].append({
                    'transaction_id': txn['transaction_id'],
                    'account_id': txn['account_id'],
                    'amount': txn['amount'],
                    'date': str(txn['date']),
                    'pending': txn['pending']
                })
            
            # Transacciones eliminadas
            for txn in response.get('removed', []):
                result['removed'].append({
                    'transaction_id': txn['transaction_id']
                })
            
            logger.info(f"[PLAID] Sync: +{len(result['added'])} ~{len(result['modified'])} -{len(result['removed'])}")
            return result
            
        except plaid.ApiException as e:
            logger.error(f"[PLAID] Error en sync de transacciones: {e}")
            raise Exception(f"Error en sync: {e}")

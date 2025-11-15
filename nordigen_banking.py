#!/usr/bin/env python3
"""
Nordigen (GoCardless) - Conexión con bancos españoles
API gratuita PSD2 para obtener cuentas y transacciones
"""

import requests
import json
import os
from datetime import datetime, timedelta
from logger_config import get_logger

logger = get_logger(__name__)

class NordigenBanking:
    """Cliente para Nordigen API"""
    
    BASE_URL = "https://ob.nordigen.com/api/v2"
    
    def __init__(self, secret_id=None, secret_key=None):
        """
        Inicializar cliente Nordigen
        
        Obtén tus credenciales en: https://nordigen.com/en/account/login/
        1. Crear cuenta gratuita
        2. Ir a "User secrets"
        3. Copiar SECRET_ID y SECRET_KEY
        """
        self.secret_id = secret_id or os.getenv('NORDIGEN_SECRET_ID')
        self.secret_key = secret_key or os.getenv('NORDIGEN_SECRET_KEY')
        self.access_token = None
        self.refresh_token = None
        
        if not self.secret_id or not self.secret_key:
            raise ValueError("Faltan credenciales de Nordigen. Configura NORDIGEN_SECRET_ID y NORDIGEN_SECRET_KEY")
    
    def get_token(self):
        """Obtener access token"""
        url = f"{self.BASE_URL}/token/new/"
        
        data = {
            "secret_id": self.secret_id,
            "secret_key": self.secret_key
        }
        
        logger.info("Obteniendo token de Nordigen...")
        response = requests.post(url, json=data)
        
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data['access']
            self.refresh_token = token_data['refresh']
            logger.info("✅ Token obtenido correctamente")
            return token_data
        else:
            logger.error(f"❌ Error obteniendo token: {response.text}")
            raise Exception(f"Error obteniendo token: {response.text}")
    
    def get_headers(self):
        """Headers para las peticiones"""
        if not self.access_token:
            self.get_token()
        
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def list_banks(self, country="ES"):
        """
        Listar bancos disponibles
        
        Args:
            country: Código del país (ES para España)
        
        Returns:
            Lista de bancos con id, nombre, logo, etc.
        """
        url = f"{self.BASE_URL}/institutions/?country={country}"
        
        logger.info(f"Obteniendo lista de bancos de {country}...")
        response = requests.get(url, headers=self.get_headers())
        
        if response.status_code == 200:
            banks = response.json()
            logger.info(f"✅ {len(banks)} bancos disponibles")
            return banks
        else:
            logger.error(f"❌ Error obteniendo bancos: {response.text}")
            return []
    
    def create_requisition(self, bank_id, redirect_uri, reference=None):
        """
        Crear requisición (enlace de autorización para el usuario)
        
        Args:
            bank_id: ID del banco (ej: SANTANDER_SANDESMMXXX)
            redirect_uri: URL de callback (ej: http://localhost:5002/callback)
            reference: Referencia única del usuario (ej: user_123)
        
        Returns:
            dict con 'link' (URL para que el usuario autorice) y 'id' (requisition_id)
        """
        url = f"{self.BASE_URL}/requisitions/"
        
        data = {
            "redirect": redirect_uri,
            "institution_id": bank_id,
            "reference": reference or f"user_{datetime.now().timestamp()}"
        }
        
        logger.info(f"Creando requisición para banco {bank_id}...")
        response = requests.post(url, json=data, headers=self.get_headers())
        
        if response.status_code == 201:
            requisition = response.json()
            logger.info(f"✅ Requisición creada: {requisition['id']}")
            logger.info(f"🔗 Link de autorización: {requisition['link']}")
            return requisition
        else:
            logger.error(f"❌ Error creando requisición: {response.text}")
            raise Exception(f"Error creando requisición: {response.text}")
    
    def get_requisition(self, requisition_id):
        """
        Obtener estado de una requisición
        
        Args:
            requisition_id: ID de la requisición
        
        Returns:
            dict con estado, cuentas vinculadas, etc.
        """
        url = f"{self.BASE_URL}/requisitions/{requisition_id}/"
        
        response = requests.get(url, headers=self.get_headers())
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"❌ Error obteniendo requisición: {response.text}")
            return None
    
    def get_account_details(self, account_id):
        """
        Obtener detalles de una cuenta
        
        Args:
            account_id: ID de la cuenta
        
        Returns:
            dict con IBAN, nombre, tipo de cuenta, etc.
        """
        url = f"{self.BASE_URL}/accounts/{account_id}/details/"
        
        response = requests.get(url, headers=self.get_headers())
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"❌ Error obteniendo detalles de cuenta: {response.text}")
            return None
    
    def get_account_balances(self, account_id):
        """
        Obtener saldos de una cuenta
        
        Args:
            account_id: ID de la cuenta
        
        Returns:
            dict con saldos (disponible, actual, etc.)
        """
        url = f"{self.BASE_URL}/accounts/{account_id}/balances/"
        
        response = requests.get(url, headers=self.get_headers())
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"❌ Error obteniendo saldos: {response.text}")
            return None
    
    def get_account_transactions(self, account_id, date_from=None, date_to=None):
        """
        Obtener transacciones de una cuenta
        
        Args:
            account_id: ID de la cuenta
            date_from: Fecha desde (YYYY-MM-DD)
            date_to: Fecha hasta (YYYY-MM-DD)
        
        Returns:
            dict con lista de transacciones
        """
        url = f"{self.BASE_URL}/accounts/{account_id}/transactions/"
        
        params = {}
        if date_from:
            params['date_from'] = date_from
        if date_to:
            params['date_to'] = date_to
        
        response = requests.get(url, headers=self.get_headers(), params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"❌ Error obteniendo transacciones: {response.text}")
            return None


def main():
    """Ejemplo de uso"""
    print("=" * 60)
    print("  NORDIGEN - Conexión con Bancos Españoles")
    print("=" * 60)
    print()
    
    # Verificar credenciales
    secret_id = os.getenv('NORDIGEN_SECRET_ID')
    secret_key = os.getenv('NORDIGEN_SECRET_KEY')
    
    if not secret_id or not secret_key:
        print("⚠️  CONFIGURACIÓN REQUERIDA:")
        print()
        print("1. Crea una cuenta gratuita en: https://nordigen.com")
        print("2. Ve a 'User secrets' y copia tus credenciales")
        print("3. Configura las variables de entorno:")
        print()
        print("   export NORDIGEN_SECRET_ID='tu_secret_id'")
        print("   export NORDIGEN_SECRET_KEY='tu_secret_key'")
        print()
        print("O agrégalas al archivo .env")
        return
    
    try:
        # Inicializar cliente
        client = NordigenBanking()
        
        # Listar bancos españoles
        print("📋 Bancos disponibles en España:")
        print()
        banks = client.list_banks("ES")
        
        for bank in banks[:10]:  # Mostrar primeros 10
            print(f"  • {bank['name']}")
            print(f"    ID: {bank['id']}")
            print(f"    BIC: {bank.get('bic', 'N/A')}")
            print()
        
        print(f"Total: {len(banks)} bancos disponibles")
        print()
        
        # Ejemplo: Crear requisición para Santander
        print("🔗 Para conectar con un banco:")
        print()
        print("1. Ejecuta:")
        print("   python3 nordigen_banking.py create_link BANCO_ID")
        print()
        print("2. Abre el enlace generado en el navegador")
        print("3. Autoriza el acceso en tu banco")
        print("4. Obtén las transacciones")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()

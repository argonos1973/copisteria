#!/usr/bin/env python3
"""
Script interactivo para configurar Nordigen y conectar con bancos
"""

import sys
import os
from nordigen_banking import NordigenBanking

def setup_credentials():
    """Configurar credenciales de Nordigen"""
    print("=" * 60)
    print("  CONFIGURACIÓN DE NORDIGEN")
    print("=" * 60)
    print()
    print("Para obtener tus credenciales:")
    print("1. Ve a: https://nordigen.com/en/account/login/")
    print("2. Crea una cuenta gratuita (si no tienes)")
    print("3. Ve a 'User secrets'")
    print("4. Copia SECRET_ID y SECRET_KEY")
    print()
    
    secret_id = input("Introduce tu SECRET_ID: ").strip()
    secret_key = input("Introduce tu SECRET_KEY: ").strip()
    
    # Guardar en .env
    env_path = "/var/www/html/.env"
    
    # Leer .env existente
    env_lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            env_lines = f.readlines()
    
    # Actualizar o agregar credenciales
    found_id = False
    found_key = False
    
    for i, line in enumerate(env_lines):
        if line.startswith('NORDIGEN_SECRET_ID='):
            env_lines[i] = f'NORDIGEN_SECRET_ID={secret_id}\n'
            found_id = True
        elif line.startswith('NORDIGEN_SECRET_KEY='):
            env_lines[i] = f'NORDIGEN_SECRET_KEY={secret_key}\n'
            found_key = True
    
    if not found_id:
        env_lines.append(f'NORDIGEN_SECRET_ID={secret_id}\n')
    if not found_key:
        env_lines.append(f'NORDIGEN_SECRET_KEY={secret_key}\n')
    
    # Guardar
    with open(env_path, 'w') as f:
        f.writelines(env_lines)
    
    print()
    print("✅ Credenciales guardadas en .env")
    print()
    
    # Configurar en el entorno actual
    os.environ['NORDIGEN_SECRET_ID'] = secret_id
    os.environ['NORDIGEN_SECRET_KEY'] = secret_key
    
    return secret_id, secret_key


def list_banks():
    """Listar bancos disponibles"""
    try:
        client = NordigenBanking()
        banks = client.list_banks("ES")
        
        print()
        print("=" * 60)
        print("  BANCOS DISPONIBLES EN ESPAÑA")
        print("=" * 60)
        print()
        
        for i, bank in enumerate(banks, 1):
            print(f"{i}. {bank['name']}")
            print(f"   ID: {bank['id']}")
            if bank.get('bic'):
                print(f"   BIC: {bank['bic']}")
            print()
        
        return banks
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return []


def create_bank_link(bank_id=None):
    """Crear enlace de autorización para un banco"""
    try:
        client = NordigenBanking()
        
        if not bank_id:
            # Listar bancos y pedir selección
            banks = list_banks()
            if not banks:
                return
            
            print("Selecciona un banco:")
            choice = input("Número del banco: ").strip()
            
            try:
                bank_index = int(choice) - 1
                bank_id = banks[bank_index]['id']
                bank_name = banks[bank_index]['name']
            except (ValueError, IndexError):
                print("❌ Selección inválida")
                return
        else:
            bank_name = bank_id
        
        print()
        print(f"🏦 Creando enlace para: {bank_name}")
        print()
        
        # Crear requisición
        redirect_uri = "http://localhost:5002/nordigen/callback"
        reference = f"user_{int(__import__('time').time())}"
        
        requisition = client.create_requisition(bank_id, redirect_uri, reference)
        
        print("=" * 60)
        print("  ENLACE DE AUTORIZACIÓN GENERADO")
        print("=" * 60)
        print()
        print("1. Abre este enlace en tu navegador:")
        print()
        print(f"   {requisition['link']}")
        print()
        print("2. Inicia sesión en tu banco y autoriza el acceso")
        print()
        print("3. Serás redirigido a:")
        print(f"   {redirect_uri}")
        print()
        print(f"4. Guarda este ID de requisición:")
        print(f"   {requisition['id']}")
        print()
        
        # Guardar requisition_id
        with open('/tmp/nordigen_requisition_id.txt', 'w') as f:
            f.write(requisition['id'])
        
        print("💾 ID guardado en /tmp/nordigen_requisition_id.txt")
        print()
        
        return requisition
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def check_requisition():
    """Verificar estado de la requisición"""
    try:
        # Leer requisition_id
        req_id_file = '/tmp/nordigen_requisition_id.txt'
        
        if not os.path.exists(req_id_file):
            print("❌ No hay requisición guardada")
            print("Ejecuta primero: python3 setup_nordigen.py create_link")
            return
        
        with open(req_id_file, 'r') as f:
            requisition_id = f.read().strip()
        
        client = NordigenBanking()
        requisition = client.get_requisition(requisition_id)
        
        if not requisition:
            print("❌ Error obteniendo requisición")
            return
        
        print()
        print("=" * 60)
        print("  ESTADO DE LA REQUISICIÓN")
        print("=" * 60)
        print()
        print(f"ID: {requisition['id']}")
        print(f"Estado: {requisition['status']}")
        print(f"Referencia: {requisition['reference']}")
        print()
        
        if requisition['accounts']:
            print(f"✅ Cuentas vinculadas: {len(requisition['accounts'])}")
            print()
            
            for account_id in requisition['accounts']:
                print(f"📊 Cuenta: {account_id}")
                
                # Obtener detalles
                details = client.get_account_details(account_id)
                if details and 'account' in details:
                    acc = details['account']
                    print(f"   IBAN: {acc.get('iban', 'N/A')}")
                    print(f"   Nombre: {acc.get('name', 'N/A')}")
                
                # Obtener saldo
                balances = client.get_account_balances(account_id)
                if balances and 'balances' in balances:
                    for balance in balances['balances']:
                        print(f"   Saldo: {balance['balanceAmount']['amount']} {balance['balanceAmount']['currency']}")
                        print(f"   Tipo: {balance['balanceType']}")
                
                print()
        else:
            print("⚠️  No hay cuentas vinculadas aún")
            print("El usuario debe completar la autorización en el banco")
        
        return requisition
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def get_transactions():
    """Obtener transacciones de las cuentas"""
    try:
        # Leer requisition_id
        req_id_file = '/tmp/nordigen_requisition_id.txt'
        
        if not os.path.exists(req_id_file):
            print("❌ No hay requisición guardada")
            return
        
        with open(req_id_file, 'r') as f:
            requisition_id = f.read().strip()
        
        client = NordigenBanking()
        requisition = client.get_requisition(requisition_id)
        
        if not requisition or not requisition['accounts']:
            print("❌ No hay cuentas vinculadas")
            return
        
        print()
        print("=" * 60)
        print("  TRANSACCIONES")
        print("=" * 60)
        print()
        
        for account_id in requisition['accounts']:
            print(f"📊 Cuenta: {account_id}")
            print()
            
            # Obtener transacciones de los últimos 90 días
            from datetime import datetime, timedelta
            date_to = datetime.now().strftime('%Y-%m-%d')
            date_from = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
            
            transactions = client.get_account_transactions(account_id, date_from, date_to)
            
            if transactions and 'transactions' in transactions:
                booked = transactions['transactions'].get('booked', [])
                pending = transactions['transactions'].get('pending', [])
                
                print(f"   Transacciones confirmadas: {len(booked)}")
                print(f"   Transacciones pendientes: {len(pending)}")
                print()
                
                # Mostrar últimas 5 transacciones
                print("   Últimas transacciones:")
                for tx in booked[:5]:
                    date = tx.get('bookingDate', 'N/A')
                    amount = tx['transactionAmount']['amount']
                    currency = tx['transactionAmount']['currency']
                    info = tx.get('remittanceInformationUnstructured', 'N/A')
                    
                    print(f"   • {date}: {amount} {currency} - {info}")
                
                print()
        
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Menú principal"""
    if len(sys.argv) < 2:
        print("=" * 60)
        print("  NORDIGEN - Gestión de Conexiones Bancarias")
        print("=" * 60)
        print()
        print("Uso:")
        print("  python3 setup_nordigen.py setup          - Configurar credenciales")
        print("  python3 setup_nordigen.py list           - Listar bancos disponibles")
        print("  python3 setup_nordigen.py create_link    - Crear enlace de autorización")
        print("  python3 setup_nordigen.py check          - Verificar estado")
        print("  python3 setup_nordigen.py transactions   - Obtener transacciones")
        print()
        return
    
    command = sys.argv[1]
    
    if command == "setup":
        setup_credentials()
    elif command == "list":
        list_banks()
    elif command == "create_link":
        bank_id = sys.argv[2] if len(sys.argv) > 2 else None
        create_bank_link(bank_id)
    elif command == "check":
        check_requisition()
    elif command == "transactions":
        get_transactions()
    else:
        print(f"❌ Comando desconocido: {command}")


if __name__ == "__main__":
    main()

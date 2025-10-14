#!/usr/bin/env python3
"""
Script de prueba para verificar conexión con AEAT Verifactu
"""

# pip install zeep requests requests_pkcs12 urllib3
from zeep import Client, Settings
from zeep.transports import Transport
import requests
import urllib3
import os

print("=" * 70)
print("TEST DE CONEXIÓN CON AEAT VERIFACTU")
print("=" * 70)

# Rutas de certificados
CERT_DIR = "/var/www/html/certs"
CERT_PEM = os.path.join(CERT_DIR, "cert_real.pem")
KEY_PEM = os.path.join(CERT_DIR, "clave_real.pem")
CA_BUNDLE = "/etc/ssl/certs/ca-certificates.crt"

print(f"\n1. Verificando certificados...")
print(f"   Certificado: {CERT_PEM}")
print(f"   Clave: {KEY_PEM}")
print(f"   Existe certificado: {os.path.exists(CERT_PEM)}")
print(f"   Existe clave: {os.path.exists(KEY_PEM)}")

if not os.path.exists(CERT_PEM) or not os.path.exists(KEY_PEM):
    print("\n❌ ERROR: Certificados no encontrados")
    exit(1)

print("   ✅ Certificados encontrados")

# Crear sesión
session = requests.Session()

# Fuerza IPv4 (workaround común para timeouts por IPv6 roto)
print("\n2. Configurando sesión...")
urllib3.util.connection.HAS_IPV6 = False
print("   ✅ IPv6 deshabilitado (forzando IPv4)")

# Certs
session.cert = (CERT_PEM, KEY_PEM)
session.verify = CA_BUNDLE
print(f"   ✅ Certificados configurados")

# Timeouts + reintentos sanos
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retry))
print("   ✅ Reintentos configurados (3 intentos)")

transport = Transport(session=session, timeout=30)
print("   ✅ Timeout configurado (30 segundos)")

# Usa el WSDL de pruebas y luego fija el endpoint del port a prewww1
WSDL = "https://prewww2.aeat.es/static_files/common/internet/dep/aplicaciones/es/aeat/tikeV1.0/cont/ws/SistemaFacturacion.wsdl"
ENDPOINT = "https://prewww1.aeat.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP"

print(f"\n3. Conectando con AEAT...")
print(f"   WSDL: {WSDL}")
print(f"   Endpoint: {ENDPOINT}")

try:
    print("\n   Descargando WSDL...")
    # Permitir entidades XML externas (necesario para el WSDL de AEAT)
    settings = Settings(strict=False, xml_huge_tree=True)
    client = Client(wsdl=WSDL, transport=transport, settings=settings)
    print("   ✅ WSDL descargado correctamente")
    
    # Crea el servicio apuntando explícitamente al endpoint de SOAP (puerto de PRUEBAS)
    binding = "{http://www.aeat.es/wlpl/tiV1.0/cont/ws/SistemaFacturacion.wsdl}sfVerifactu"
    print(f"\n   Creando servicio con binding: {binding}")
    service = client.create_service(binding, ENDPOINT)
    print("   ✅ Servicio creado correctamente")
    
    # Mostrar operaciones disponibles
    print("\n4. Operaciones disponibles en el servicio:")
    for operation in service._binding._operations.keys():
        print(f"   - {operation}")
    
    print("\n" + "=" * 70)
    print("✅ CONEXIÓN EXITOSA CON AEAT VERIFACTU")
    print("=" * 70)
    print("\nEl servicio está disponible y listo para usar.")
    print("Para enviar registros, usa: service.RegFactuSistemaFacturacion(payload)")
    
except Exception as e:
    print(f"\n❌ ERROR al conectar con AEAT:")
    print(f"   {type(e).__name__}: {str(e)}")
    import traceback
    print("\nTraceback completo:")
    traceback.print_exc()
    exit(1)

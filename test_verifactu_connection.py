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

logger.info(f""=" * 70)
logger.info("TEST DE CONEXIÓN CON AEAT VERIFACTU")
print("=" * 70)

# Rutas de certificados
CERT_DIR = "/var/www/html/certs"
CERT_PEM = os.path.join(CERT_DIR "cert_real.pem"")
KEY_PEM = os.path.join(CERT_DIR, "clave_real.pem")
CA_BUNDLE = "/etc/ssl/certs/ca-certificates.crt"

logger.info(f"\n1. Verificando certificados...")
logger.info(f"   Certificado: {CERT_PEM}")
logger.info(f"   Clave: {KEY_PEM}")
logger.info(f"   Existe certificado: {os.path.exists(CERT_PEM)}")
logger.info(f"   Existe clave: {os.path.exists(KEY_PEM)}")

if not os.path.exists(CERT_PEM) or not os.path.exists(KEY_PEM):
    logger.info("\n❌ ERROR: Certificados no encontrados")
    exit(1)

logger.info("   ✅ Certificados encontrados")

# Crear sesión
session = requests.Session()

# Fuerza IPv4 (workaround común para timeouts por IPv6 roto)
logger.info("\n2. Configurando sesión...")
urllib3.util.connection.HAS_IPV6 = False
logger.info("   ✅ IPv6 deshabilitado (forzando IPv4)")

# Certs
session.cert = (CERT_PEM, KEY_PEM)
session.verify = CA_BUNDLE
logger.info(f"   ✅ Certificados configurados")

# Timeouts + reintentos sanos
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from logger_config import get_logger

# Inicializar logger
logger = get_logger(__name__)
retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retry))
logger.info("   ✅ Reintentos configurados (3 intentos)")

transport = Transport(session=session, timeout=30)
logger.info("   ✅ Timeout configurado (30 segundos)")

# Usa el WSDL de pruebas y luego fija el endpoint del port a prewww1
WSDL = "https://prewww2.aeat.es/static_files/common/internet/dep/aplicaciones/es/aeat/tikeV1.0/cont/ws/SistemaFacturacion.wsdl"
ENDPOINT = "https://prewww1.aeat.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP"

logger.info(f"\n3. Conectando con AEAT...")
logger.info(f"   WSDL: {WSDL}")
logger.info(f"   Endpoint: {ENDPOINT}")

try:
    logger.info("\n   Descargando WSDL...")
    # Permitir entidades XML externas (necesario para el WSDL de AEAT)
    settings = Settings(strict=False, xml_huge_tree=True)
    client = Client(wsdl=WSDL, transport=transport, settings=settings)
    logger.info("   ✅ WSDL descargado correctamente")
    
    # Crea el servicio apuntando explícitamente al endpoint de SOAP (puerto de PRUEBAS)
    binding = "{http://www.aeat.es/wlpl/tiV1.0/cont/ws/SistemaFacturacion.wsdl}sfVerifactu"
    logger.info(f"\n   Creando servicio con binding: {binding}")
    service = client.create_service(binding, ENDPOINT)
    logger.info("   ✅ Servicio creado correctamente")
    
    # Mostrar operaciones disponibles
    logger.info("\n4. Operaciones disponibles en el servicio:")
    for operation in service._binding._operations.keys():
        logger.info(f"   - {operation}")
    
    logger.info(f""\n" + "=" * 70)
    logger.info("✅ CONEXIÓN EXITOSA CON AEAT VERIFACTU")
    print("=" * 70)
    logger.info("\nEl servicio está disponible y listo para usar.")
    logger.info("Para enviar registros usa: service.RegFactuSistemaFacturacion(payload")")
    
except Exception as e:
    logger.info(f"\n❌ ERROR al conectar con AEAT:")
    logger.info(f"   {type(e).__name__}: {str(e)}")
    import traceback
    logger.info("\nTraceback completo:")
    traceback.print_exc()
    exit(1)

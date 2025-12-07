import sys
import os
import io

sys.path.append('/var/www/html')
from app import create_app
from dotenv import load_dotenv

load_dotenv('/var/www/html/.env')

app = create_app()
app.config['TESTING'] = True
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_key')

cert_path = '/var/www/html/static/certificado_prueba_23.p12'
password = '1234'
codigo_empresa = 'TEST_LOCAL'

print(f"--- Iniciando prueba local ---")
if not os.path.exists(cert_path):
    print("❌ Error: No existe el certificado de prueba")
    sys.exit(1)

with app.test_client() as client:
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['username'] = 'admin_test'
        sess['rol'] = 'admin'
        sess['empresa_id'] = 1
        sess['activo'] = True
    
    with open(cert_path, 'rb') as f:
        file_content = f.read()
        
    data = {
        'certificado': (io.BytesIO(file_content), 'local_test.p12'),
        'password': password,
        'codigo_empresa': codigo_empresa
    }
    
    print(f"📨 Enviando petición POST a /api/empresas/procesar_certificado...")
    
    try:
        resp = client.post('/api/empresas/procesar_certificado', 
                          data=data, 
                          content_type='multipart/form-data')
        
        print(f"📥 Respuesta recibida: Status {resp.status_code}")
        print(f"📥 Body: {resp.data.decode('utf-8')}")
        
        if resp.status_code == 200:
            pem_key = f"/var/www/html/certs/{codigo_empresa}_key.pem"
            pem_cert = f"/var/www/html/certs/{codigo_empresa}_cert.pem"
            if os.path.exists(pem_key) and os.path.exists(pem_cert):
                print(f"✅ Archivos PEM creados correctamente")
            else:
                print(f"⚠️ Archivos PEM NO encontrados")
            
    except Exception as e:
        print(f"❌ EXCEPCIÓN en cliente: {e}")
        import traceback
        traceback.print_exc()

print("--- Fin prueba local ---")

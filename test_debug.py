import sys
import os
import io

sys.path.append('/var/www/html')
from app import create_app

app = create_app()
app.config['TESTING'] = True
app.config['SECRET_KEY'] = 'test'

cert_path = '/tmp/test.p12'
password = '1234'

if not os.path.exists(cert_path):
    print("Certificado no encontrado")
    sys.exit(1)

with app.test_client() as client:
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['rol'] = 'admin'
    
    with open(cert_path, 'rb') as f:
        file_content = f.read()
        
    data = {
        'certificado': (io.BytesIO(file_content), 'test.p12'),
        'password': password,
        'codigo_empresa': 'TEST_CODE'
    }
    
    print("Enviando petición...")
    try:
        resp = client.post('/api/empresas/procesar_certificado', data=data, content_type='multipart/form-data')
        print(f"Status: {resp.status_code}")
        print(f"Data: {resp.data.decode('utf-8')}")
    except Exception as e:
        import traceback
        traceback.print_exc()

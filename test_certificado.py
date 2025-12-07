import sys
import os
import io

# Añadir ruta al path para importar app
sys.path.append('/var/www/html')

from app import create_app

# Crear app en modo testing
app = create_app()
app.config['TESTING'] = True
# Necesario para sesiones
app.config['SECRET_KEY'] = 'test_secret_key' 

# Ruta del certificado generado
cert_path = '/tmp/certificado_prueba.p12'
cert_pass = '1234'

if not os.path.exists(cert_path):
    print(f"Error: No existe el archivo {cert_path}")
    sys.exit(1)

with app.test_client() as client:
    # Simular sesión de usuario logueado
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['username'] = 'admin'
        sess['rol'] = 'admin'
        sess['empresa_id'] = 1 
        sess['activo'] = True
    
    # Leer el archivo
    with open(cert_path, 'rb') as f:
        file_content = f.read()
        
    # Preparar datos multipart
    data = {
        'certificado': (io.BytesIO(file_content), 'certificado_prueba.p12'),
        'password': cert_pass
    }
    
    # Enviar petición POST
    print("📨 Enviando petición al endpoint /api/empresas/procesar_certificado...")
    try:
        response = client.post(
            '/api/empresas/procesar_certificado',
            data=data,
            content_type='multipart/form-data'
        )
        
        print(f"📥 Status Code: {response.status_code}")
        try:
            json_resp = response.get_json()
            print(f"📄 Respuesta JSON: {json_resp}")
            
            if response.status_code == 200:
                print("\n✅ PRUEBA EXITOSA")
                print(f"   - Razón Social: {json_resp.get('razon_social')}")
                print(f"   - NIF: {json_resp.get('nif')}")
                print(f"   - Ruta guardada: {json_resp.get('ruta_certificado')}")
                
                # Verificar valores esperados
                if json_resp.get('nif') == 'B99999999' and 'MI EMPRESA TEST' in json_resp.get('razon_social'):
                    print("   - Datos coinciden con el certificado generado.")
                else:
                    print("   ⚠️ Los datos extraídos no coinciden exactamente con lo esperado.")
            else:
                print(f"\n❌ PRUEBA FALLIDA: {json_resp.get('error')}")
                
        except Exception as e:
            print(f"Error parseando JSON: {e}")
            print(f"Contenido raw: {response.data}")
            
    except Exception as e:
        print(f"Error ejecutando request: {e}")

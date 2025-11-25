
import sys
import os
sys.path.append('/var/www/html')
from dotenv import load_dotenv
load_dotenv('/var/www/html/.env')

try:
    from factura_ocr import extraer_datos_factura_gpt4
    print("Import successful")
    
    # Create a dummy image
    from PIL import Image
    import io
    img = Image.new('RGB', (3000, 3000), color = 'red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_bytes = img_byte_arr.getvalue()
    
    print(f"Testing with image of size: {len(img_bytes)} bytes")
    
    # We expect this to fail with API key error if not configured, 
    # OR pass if configured, 
    # BUT NOT fail with UnboundLocalError
    try:
        extraer_datos_factura_gpt4(img_bytes)
    except ValueError as e:
        # API key might be missing or other expected errors
        print(f"Caught expected error: {e}")
    except Exception as e:
        print(f"CAUGHT UNEXPECTED ERROR: {type(e).__name__}: {e}")
        raise

    print("Test finished without UnboundLocalError")

except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Top level error: {e}")

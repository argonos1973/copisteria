# 📸 Configuración de OCR para Contactos

Este sistema soporta **3 motores de OCR** con diferentes niveles de precisión y costo:

## 🎯 Motores Disponibles

### 1. **GPT-4 Vision API** (Recomendado) ⭐
- **Precisión:** ~95% incluso con diseños complejos
- **Costo:** ~$0.01 por imagen
- **Ventajas:** 
  - Entiende contexto visual
  - Funciona con tarjetas complejas, logos, fondos oscuros
  - Extrae datos estructurados directamente
- **Requiere:** API Key de OpenAI (de pago)

### 2. **EasyOCR** (Deep Learning)
- **Precisión:** ~70% con diseños simples
- **Costo:** Gratis
- **Ventajas:**
  - No requiere API key
  - Usa deep learning
  - Mejor que Tesseract
- **Limitaciones:**
  - Falla con diseños complejos
  - No soporta catalán

### 3. **Tesseract OCR** (Fallback)
- **Precisión:** ~50% con diseños simples
- **Costo:** Gratis
- **Ventajas:**
  - No requiere API key
  - Muy rápido
- **Limitaciones:**
  - Solo funciona con texto claro
  - Falla con diseños complejos

---

## 🔑 Configurar GPT-4 Vision (Recomendado)

### Paso 1: Obtener API Key de OpenAI

1. Ve a https://platform.openai.com/
2. Crea una cuenta o inicia sesión
3. Ve a https://platform.openai.com/api-keys
4. Click en "Create new secret key"
5. Copia la API key (empieza con `sk-proj-...`)
6. **IMPORTANTE:** Guarda la key en un lugar seguro, solo se muestra una vez

### Paso 2: Agregar créditos

1. Ve a https://platform.openai.com/settings/organization/billing
2. Agrega un método de pago
3. Compra créditos (mínimo $5)
4. **Costo estimado:** 
   - 100 tarjetas procesadas = ~$1.00
   - 1000 tarjetas procesadas = ~$10.00

### Paso 3: Configurar en el servidor

Opción A - Variable de entorno en `.env`:
```bash
cd /var/www/html
nano .env
```

Agregar esta línea:
```
OPENAI_API_KEY=sk-proj-tu_api_key_aqui
```

Opción B - Variable de entorno del sistema:
```bash
sudo nano /etc/environment
```

Agregar:
```
OPENAI_API_KEY="sk-proj-tu_api_key_aqui"
```

### Paso 4: Cargar variable de entorno

```bash
# Si usaste .env
source .env

# Si usaste /etc/environment
source /etc/environment
```

### Paso 5: Reiniciar servicios

```bash
sudo systemctl restart apache2
sudo kill -HUP $(ps aux | grep gunicorn | grep 'bin/gunicorn' | head -1 | awk '{print $2}')
```

### Paso 6: Verificar configuración

```bash
cd /var/www/html
source venv/bin/activate
python3 -c "import os; print('API Key configurada' if os.getenv('OPENAI_API_KEY') else 'API Key NO configurada')"
```

---

## 🧪 Probar el OCR

### Con imagen de prueba:

```bash
cd /var/www/html
source venv/bin/activate
python3 test_ocr.py /ruta/a/tu/imagen.jpg
```

### Resultado esperado con GPT-4 Vision:

```
============================================================
DATOS EXTRAÍDOS:
============================================================

  razon_social        : ASSOCIACIÓ D'AMICS DEL MUSEU MARÍTIM
  nif                 : G12345678
  direccion           : Av. de les Drassanes s/n
  cp                  : 08001
  poblacion           : Barcelona
  telefono            : 933429920
  email               : amics@mmb.cat
  nombre_contacto     : Francesc Pérez Pastor
  web                 : www.aammb.cat
  _metodo_ocr         : GPT-4 Vision

============================================================
```

---

## 💰 Gestión de Costos

### Monitorear uso:
1. Ve a https://platform.openai.com/usage
2. Revisa el consumo mensual
3. Establece límites de gasto en Settings → Billing

### Establecer límite de gasto:
1. Settings → Organization → Billing → Usage limits
2. Establece un máximo mensual (ej: $20)
3. Recibirás alertas cuando alcances el 75% y 90%

### Optimizar costos:
- Solo usa OCR para tarjetas/documentos complejos
- Para facturas simples, EasyOCR/Tesseract (gratis) funciona bien
- El sistema usa GPT-4 Vision solo si la API key está configurada

---

## 🔒 Seguridad

⚠️ **NUNCA** compartas tu API key en:
- Repositorios públicos de Git
- Código fuente
- Capturas de pantalla
- Mensajes de chat

✅ **Buenas prácticas:**
- Usa variables de entorno
- Agrega `.env` al `.gitignore`
- Rota la key periódicamente
- Establece límites de gasto

---

## ❓ Troubleshooting

### "OpenAI API Key no configurada"
- Verifica que la variable de entorno esté configurada
- Reinicia los servicios después de configurarla

### "Error 401: Invalid API Key"
- La API key es incorrecta
- Verifica que copiaste la key completa
- Genera una nueva key si es necesario

### "Error 429: Rate limit exceeded"
- Has excedido el límite de requests
- Espera unos minutos
- Considera upgrade a plan de pago con más cuota

### "Error 500: Internal Server Error"
- Verifica que tengas créditos disponibles
- Revisa los logs: `tail -f /var/www/html/logs/gunicorn-error.log`

---

## 📊 Comparativa de Resultados

| Tipo de Documento | Tesseract | EasyOCR | GPT-4 Vision |
|-------------------|-----------|---------|--------------|
| Factura simple | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Documento oficial | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Tarjeta simple | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Tarjeta compleja (MMB) | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ |
| Foto con poca luz | ⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| Texto sobre imagen | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ |

---

## 📝 Notas Adicionales

- El sistema intenta GPT-4 Vision primero (si está configurado)
- Si falla o no está disponible, usa EasyOCR
- Si EasyOCR falla, usa Tesseract
- El fallback garantiza que siempre hay un resultado
- Puedes ver qué método se usó en el campo `_metodo_ocr`

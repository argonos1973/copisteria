# ANÁLISIS: ORIGEN DE DATOS DEL EMISOR

## 📋 RESUMEN EJECUTIVO

Los datos del emisor están **HARDCODEADOS** en múltiples archivos, lo que impide el funcionamiento correcto del sistema multiempresa. Cada vez que se imprime o genera un PDF, se muestran los datos de "SAMUEL RODRIGUEZ MIQUEL" independientemente de la empresa seleccionada.

---

## 🔍 ARCHIVOS CON DATOS HARDCODEADOS

### 1. **Frontend - Impresión de Facturas**
📁 `/var/www/html/static/imprimir-factura.js`
📍 Líneas: 184-188

```javascript
// Datos del emisor (hardcodeados por ahora)
document.getElementById('emisor-nombre').textContent = 'SAMUEL RODRIGUEZ MIQUEL';
document.getElementById('emisor-direccion').textContent = 'LEGALITAT, 70';
document.getElementById('emisor-cp-ciudad').textContent = 'BARCELONA (08024), BARCELONA, España';
document.getElementById('emisor-nif').textContent = '44007535W';
document.getElementById('emisor-email').textContent = 'info@aleph70.com';
```

**Impacto**: Al imprimir facturas desde el navegador, siempre muestra estos datos.

---

### 2. **Frontend - Impresión de Tickets**
📁 `/var/www/html/static/imprimir-ticket.js`
📍 Líneas: 154-157

```javascript
// Datos del emisor en mayúsculas
document.getElementById('emisor-nombre').textContent = 'SAMUEL RODRIGUEZ MIQUEL';
document.getElementById('emisor-direccion').textContent = 'LEGALITAT, 70, BARCELONA (08024)';
document.getElementById('emisor-nif').textContent = '44007535W';
document.getElementById('emisor-email').textContent = 'info@aleph70.com';
```

**Impacto**: Al imprimir tickets desde el navegador, siempre muestra estos datos.

---

### 3. **Backend - Generación de PDFs**
📁 `/var/www/html/generar_pdf.py`
📍 Líneas: 394-407

```python
html_modificado = html_base.replace(
    '<p id="emisor-nombre"></p>',
    '<p>SAMUEL RODRIGUEZ MIQUEL</p>'
).replace(
    '<p id="emisor-direccion"></p>',
    '<p>LEGALITAT, 70</p>'
).replace(
    '<p id="emisor-cp-ciudad"></p>',
    '<p>BARCELONA (08024), BARCELONA, España</p>'
).replace(
    '<p id="emisor-nif"></p>',
    '<p>44007535W</p>'
).replace(
    '<p id="emisor-email"></p>',
    '<p>info@aleph70.com</p>'
)
```

**Impacto**: Al generar PDFs de facturas, siempre usa estos datos.

---

### 4. **Backend - Envío de Emails con Facturas**
📁 `/var/www/html/factura.py`
📍 Líneas: 1616-1684

```python
html_modificado = html_base.replace(
    '<p id="emisor-nombre"></p>',
    '<p>SAMUEL RODRIGUEZ MIQUEL</p>'
).replace(
    '<p id="emisor-direccion"></p>',
    '<p>LEGALITAT, 70</p>'
).replace(
    '<p id="emisor-cp-ciudad"></p>',
    '<p>BARCELONA (08024), BARCELONA, España</p>'
).replace(
    '<p id="emisor-nif"></p>',
    '<p>44007535W</p>'
).replace(
    '<p id="emisor-email"></p>',
    '<p>info@aleph70.com</p>'
)
```

**Impacto**: Al enviar facturas por email, siempre usa estos datos en el PDF adjunto.

También en líneas 1818-1828:
```python
"Atentamente,\n"
"COPISTERIA ALEPH 70\n"
"SAMUEL RODRIGUEZ MIQUEL\n"
```

**Impacto**: El cuerpo del email siempre firma como "SAMUEL RODRIGUEZ MIQUEL".

---

### 5. **Backend - Generación Batch de Facturas**
📁 `/var/www/html/batchFacturas.py`
📍 Líneas: 254-258

```python
replacements = {
    '<p id="emisor-nombre"></p>': '<p>SAMUEL RODRIGUEZ MIQUEL</p>',
    '<p id="emisor-direccion"></p>': '<p>LEGALITAT, 70</p>',
    '<p id="emisor-cp-ciudad"></p>': '<p>BARCELONA (08024), BARCELONA, España</p>',
    '<p id="emisor-nif"></p>': '<p>44007535W</p>',
    '<p id="emisor-email"></p>': '<p>info@aleph70.com</p>',
}
```

**Impacto**: Al generar facturas en batch (cobrar facturas vencidas), siempre usa estos datos.

---

### 6. **Backend - Batch Facturas Vencidas**
📁 `/var/www/html/batchFacturasVencidas.py`
📍 Líneas: 55-59

```python
emisor = {
    'nombre': 'SAMUEL RODRIGUEZ MIQUEL',
    'direccion': 'LEGALITAT, 70',
    'cp': '08024',
    'ciudad': 'BARCELONA',
    'email': 'INFO@ALEPH70.COM'
}
```

**Impacto**: Fallback cuando no se puede leer el JSON del emisor.

---

## 📂 SISTEMA CORRECTO EXISTENTE (NO USADO)

### Archivos JSON por Empresa

El sistema multiempresa **SÍ tiene** un mecanismo correcto:

```
/var/www/html/static/emisores/
├── ALE_emisor.json          # ALEPH70
├── MANU_emisor.json         # MANUSCOP
├── [CODIGO]_emisor.json     # Patrón para cada empresa
```

Cada archivo contiene:
```json
{
    "nombre": "NOMBRE_EMPRESA",
    "nif": "NIF_EMPRESA",
    "direccion": "DIRECCION_EMPRESA",
    "cp": "CODIGO_POSTAL",
    "ciudad": "CIUDAD",
    "provincia": "PROVINCIA",
    "pais": "ESP",
    "email": "EMAIL_EMPRESA",
    "telefono": "TELEFONO",
    "db_path": "/var/www/html/empresas/[CODIGO]/empresa.db",
    "codigo": "[CODIGO]"
}
```

### Función de Carga Existente (NO USADA en impresión)

📁 `/var/www/html/utils_emisor.py`

```python
def cargar_datos_emisor(config_path=None):
    """
    Carga los datos del emisor desde un archivo JSON de configuración.
    Por defecto busca emisor_config.json en el mismo directorio que este archivo.
    """
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), 'emisor_config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)
```

⚠️ **PROBLEMA**: Esta función busca un archivo global `emisor_config.json` que ya no existe en sistema multiempresa.

### Dónde SÍ se Usa Correctamente

✅ **empresas_api.py** (líneas 261-278):
```python
emisor_json_path = os.path.join(BASE_DIR, 'static', 'emisores', f'{codigo_empresa}_emisor.json')

if os.path.exists(emisor_json_path):
    with open(emisor_json_path, 'r', encoding='utf-8') as f:
        emisor_data = json.load(f)
    
    empresa['cif'] = emisor_data.get('nif', empresa.get('cif', ''))
    empresa['razon_social'] = emisor_data.get('nombre', empresa.get('razon_social', ''))
    # ... etc
```

✅ **VeriFactu** y otros módulos **SÍ usan** correctamente los datos del emisor desde la sesión o desde los JSON.

---

## 🎯 SOLUCIÓN REQUERIDA

### 1. Frontend (JS)

Obtener datos del emisor desde el endpoint `/api/auth/branding` que incluye toda la información de la empresa:

```javascript
// En imprimir-factura.js y imprimir-ticket.js
async function cargarDatosEmisor() {
    const response = await fetch('/api/auth/branding');
    const branding = await response.json();
    
    document.getElementById('emisor-nombre').textContent = branding.razon_social;
    document.getElementById('emisor-direccion').textContent = branding.direccion;
    document.getElementById('emisor-cp-ciudad').textContent = 
        `${branding.ciudad} (${branding.codigo_postal}), ${branding.provincia}, ${branding.pais}`;
    document.getElementById('emisor-nif').textContent = branding.cif;
    document.getElementById('emisor-email').textContent = branding.email;
}
```

### 2. Backend (Python)

Cargar datos del emisor desde el archivo JSON de la empresa en sesión:

```python
# En generar_pdf.py, factura.py, batchFacturas.py, etc.
def obtener_datos_emisor():
    """Obtiene datos del emisor desde el JSON de la empresa en sesión"""
    codigo_empresa = session.get('codigo_empresa', '')
    emisor_path = os.path.join(BASE_DIR, 'static', 'emisores', f'{codigo_empresa}_emisor.json')
    
    if os.path.exists(emisor_path):
        with open(emisor_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # Fallback: intentar desde tabla empresas
    empresa_id = session.get('empresa_id')
    conn = sqlite3.connect(DB_USUARIOS_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM empresas WHERE id = ?', (empresa_id,))
    empresa = cursor.fetchone()
    conn.close()
    
    # Convertir a dict con estructura esperada
    return {
        'nombre': empresa['razon_social'],
        'nif': empresa['cif'],
        'direccion': empresa['direccion'],
        # ... etc
    }
```

Luego usar en los replace:
```python
emisor = obtener_datos_emisor()

html_modificado = html_base.replace(
    '<p id="emisor-nombre"></p>',
    f'<p>{emisor["nombre"]}</p>'
).replace(
    '<p id="emisor-direccion"></p>',
    f'<p>{emisor["direccion"]}</p>'
)
# ... etc
```

---

## ⚠️ IMPACTO CRÍTICO

**PROBLEMA ACTUAL**:
- ❌ Todas las empresas ven datos de "SAMUEL RODRIGUEZ MIQUEL"
- ❌ Facturas impresas/enviadas con datos incorrectos
- ❌ PDFs generados con datos incorrectos
- ❌ Tickets impresos con datos incorrectos
- ❌ Sistema multiempresa NO funciona para impresión

**ARCHIVOS A MODIFICAR**:
1. `/var/www/html/static/imprimir-factura.js`
2. `/var/www/html/static/imprimir-ticket.js`
3. `/var/www/html/generar_pdf.py`
4. `/var/www/html/factura.py`
5. `/var/www/html/batchFacturas.py`
6. `/var/www/html/batchFacturasVencidas.py`

**PRIORIDAD**: 🔴 **CRÍTICA** - Afecta documentos legales

---

## 📊 RESUMEN

| Operación | Archivo | Datos Emisor |
|-----------|---------|--------------|
| Imprimir factura (web) | `imprimir-factura.js` | ❌ Hardcoded |
| Imprimir ticket (web) | `imprimir-ticket.js` | ❌ Hardcoded |
| Generar PDF factura | `generar_pdf.py` | ❌ Hardcoded |
| Enviar email factura | `factura.py` | ❌ Hardcoded |
| Batch facturas vencidas | `batchFacturas.py` | ❌ Hardcoded |
| API empresas | `empresas_api.py` | ✅ Correcto |
| VeriFactu | `verifactu/` | ✅ Correcto |

---

**Fecha**: 2025-11-08
**Servidor**: 192.168.1.23
**Sistema**: Multiempresa Aleph70

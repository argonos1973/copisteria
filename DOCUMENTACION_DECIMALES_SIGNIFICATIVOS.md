# Documentación: Sistema de Decimales Significativos en Franjas de Descuento

## Resumen Ejecutivo

Este documento describe la implementación completa del sistema de decimales significativos para las franjas de descuento de productos, garantizando precisión exacta de 5 decimales en todos los cálculos, almacenamiento y visualización.

## Especificaciones Técnicas

### Algoritmo de Descuentos

**Fórmula de Cálculo:**
- Primera franja (1-N): 0% descuento SIEMPRE
- Franjas siguientes: `descuento_inicial + ((i-1) * incremento)`
- Límite máximo: 60% de descuento
- Precisión: EXACTAMENTE 5 decimales en todos los valores

**Ejemplo de Configuración:**
```
Producto: SCANNER (ID 27)
- descuento_inicial: 3.14159%
- incremento_franja: 2.71828%
- numero_franjas: 8
- ancho_franja: 12

Resultado:
Franja 1: 1-12 = 0.00000%
Franja 2: 13-24 = 3.14159%
Franja 3: 25-36 = 5.85987%
Franja 4: 37-48 = 8.57815%
Franja 5: 49-60 = 11.29643%
Franja 6: 61-72 = 14.01471%
Franja 7: 73-84 = 16.73299%
Franja 8: 85-96 = 19.45127%
```

## Implementación Backend

### Archivo: productos.py

**Función Principal: `_generar_franjas_automaticas`**
```python
# Primera franja siempre 0%, siguientes incrementales desde descuento_inicial
if i == 0:
    pct = 0.0
else:
    # Usar valores con decimales significativos para generar progresión real
    pct = desc_inicial + ((i - 1) * incremento)

# Aplicar límites: nunca > 60%
pct = min(60.0, max(0.0, pct))

# Asegurar precisión de 5 decimales EXACTOS
pct = round(float(pct), 5)
```

**Función de Almacenamiento: `reemplazar_franjas_descuento_producto`**
```python
# Redondear a 5 decimales antes de insertar en BD
clamped_desc = round(float(clamped_desc), 5)
cur.execute(
    'INSERT INTO descuento_producto_franja (producto_id, min_cantidad, max_cantidad, porcentaje_descuento) VALUES (?,?,?,?)',
    (producto_id, min_c, max_c, clamped_desc)
)
```

### Base de Datos

**Tabla: productos**
- `descuento_inicial`: REAL - Descuento inicial con decimales significativos
- `incremento_franja`: REAL - Incremento por franja con decimales significativos
- `numero_franjas`: INTEGER - Número total de franjas a generar
- `ancho_franja`: INTEGER - Unidades por franja
- `no_generar_franjas`: INTEGER - Flag para deshabilitar generación automática

**Tabla: descuento_producto_franja**
- `porcentaje_descuento`: REAL - Almacenado con exactamente 5 decimales

## Implementación Frontend

### Archivo: static/FRANJAS_DESCUENTO.js

**Visualización con 5 Decimales:**
```javascript
// Formatear descuentos con exactamente 5 decimales
descuento: franja.porcentaje_descuento.toLocaleString('es-ES', { 
    minimumFractionDigits: 5, 
    maximumFractionDigits: 5 
})
```

### Archivo: frontend/GESTION_PRODUCTOS.html

**Campos de Configuración:**
- Descuento inicial: Input numérico con step="0.00001"
- Incremento franja: Input numérico con step="0.00001"
- Checkbox "No generar franjas" con persistencia en BD

## Funcionalidades Implementadas

### 1. Creación de Productos
- Genera franjas automáticamente con decimales significativos
- Respeta configuración de usuario (descuento_inicial, incremento_franja)
- Almacena valores con precisión de 5 decimales

### 2. Actualización de Productos
- Regenera franjas con nueva configuración
- Mantiene precisión decimal en todos los cálculos
- Actualiza campos de configuración en tabla productos

### 3. Persistencia del Checkbox "No generar franjas"
- Campo `no_generar_franjas` en tabla productos
- Estado persiste entre sesiones
- Deshabilita/habilita campos de configuración dinámicamente

### 4. API Endpoints
- `/api/productos/{id}`: Incluye configuración de franjas
- `/api/productos/{id}/franjas`: Sirve franjas con 5 decimales
- `/api/productos/{id}/franjas_config`: Configuración de franjas automáticas

## Validación y Verificación

### Script de Verificación: `scripts/verificar_decimales_franjas.py`

**Uso:**
```bash
python3 /var/www/html/scripts/verificar_decimales_franjas.py [producto_id]
```

**Funcionalidades:**
- Verifica precisión de 5 decimales en todas las franjas
- Valida fórmula de cálculo contra valores almacenados
- Cuenta franjas con decimales significativos
- Genera reporte detallado de errores si los hay

**Ejemplo de Salida:**
```
=== VERIFICACIÓN DE DECIMALES SIGNIFICATIVOS ===
Producto ID: 27
✅ Producto: SCANNER
✅ Configuración:
   - Descuento inicial: 3.14159%
   - Incremento: 2.71828%
   - Número de franjas: 8
   - Ancho de franja: 12
✅ Franjas: 8 total
✅ Con decimales significativos: 7
✅ Todas las franjas calculadas correctamente
```

## Despliegue en Producción

### Servidores Sincronizados
- **Servidor 192.168.1.55**: ✅ Configuración actualizada
- **Servidor 192.168.1.18**: ✅ Configuración actualizada

### Archivos Modificados
1. `/var/www/html/productos.py` - Lógica backend con decimales significativos
2. `/var/www/html/productos_franjas_utils.py` - Utilidades de configuración
3. `/var/www/html/static/gestion_producto.js` - Frontend con persistencia
4. `/var/www/html/frontend/GESTION_PRODUCTOS.html` - UI actualizada
5. `/var/www/html/static/FRANJAS_DESCUENTO.js` - Visualización con 5 decimales

### Migraciones de BD Aplicadas
```sql
-- Añadir columna para deshabilitar franjas automáticas
ALTER TABLE productos ADD COLUMN no_generar_franjas INTEGER DEFAULT 0;

-- Añadir columnas de configuración de franjas (si no existen)
ALTER TABLE productos ADD COLUMN calculo_automatico INTEGER DEFAULT 1;
ALTER TABLE productos ADD COLUMN franja_inicial INTEGER DEFAULT 1;
ALTER TABLE productos ADD COLUMN numero_franjas INTEGER DEFAULT 50;
ALTER TABLE productos ADD COLUMN ancho_franja INTEGER DEFAULT 10;
ALTER TABLE productos ADD COLUMN descuento_inicial REAL DEFAULT 0.0;
ALTER TABLE productos ADD COLUMN incremento_franja REAL DEFAULT 1.0;
```

## Casos de Prueba Exitosos

### 1. Creación de Producto Nuevo
```python
data = {
    "nombre": "PRODUCTO_TEST",
    "config_franjas": {
        "descuento_inicial": 2.34567,
        "incremento_franja": 1.23456,
        "numero_franjas": 5
    }
}
# Resultado: Franjas con 0.00000%, 2.34567%, 3.58023%, 4.81479%, 6.04935%
```

### 2. Actualización de Producto Existente
```python
# Producto SCANNER actualizado con decimales significativos
# Resultado: 8 franjas con valores desde 0.00000% hasta 19.45127%
```

### 3. Sincronización Entre Servidores
- Ambos servidores (.55 y .18) tienen configuración idéntica
- Franjas calculadas correctamente con 5 decimales
- Verificación exitosa con script automatizado

## Mantenimiento y Monitoreo

### Comandos de Verificación Rápida
```bash
# Verificar configuración de producto específico
python3 /var/www/html/scripts/verificar_decimales_franjas.py 27

# Verificar franjas en BD directamente
sqlite3 db/aleph70.db "SELECT min_cantidad, max_cantidad, porcentaje_descuento FROM descuento_producto_franja WHERE producto_id = 27 ORDER BY min_cantidad;"
```

### Logs de Debug
- Función `_generar_franjas_automaticas` incluye logs detallados
- Función `reemplazar_franjas_descuento_producto` registra inserciones
- Función `actualizar_producto` traza configuración recibida

## Estado del Sistema

**✅ COMPLETAMENTE OPERATIVO**

- ✅ Backend: Cálculos con decimales significativos
- ✅ Frontend: Visualización con 5 decimales
- ✅ Base de Datos: Almacenamiento con precisión exacta
- ✅ API: Endpoints funcionando correctamente
- ✅ Sincronización: Ambos servidores actualizados
- ✅ Validación: Script de verificación implementado
- ✅ Documentación: Completa y actualizada

**Fecha de Implementación:** 7 de Septiembre de 2025
**Versión:** 1.0 - Decimales Significativos
**Responsable:** Sistema Cascade

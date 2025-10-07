# 🔔 Sistema de Notificaciones - Documentación Completa

## ✅ Estado: COMPLETAMENTE IMPLEMENTADO

---

## 📊 Resumen Ejecutivo

El sistema de notificaciones está **completamente integrado** en la aplicación, permitiendo que todos los procesos automáticos (batch, scraping, conciliación) notifiquen al usuario de forma centralizada.

---

## 🎯 Fuentes de Notificaciones

### **1. Conciliación Bancaria Automática**
| Evento | Notificación | Tipo |
|--------|--------------|------|
| Conciliación automática exitosa | "Gasto de 546.21€ conciliado con FACTURA F250296" | `success` |
| Múltiples conciliaciones | "6 gastos conciliados automáticamente" | `success` |

**Frecuencia:** Cada vez que se ejecuta conciliación automática (al cargar página o cron)

---

### **2. Script batchPol.py**
| Evento | Notificación | Tipo |
|--------|--------------|------|
| Proforma actualizada | "Proforma P250123 actualizada con 45 items desde batchPol" | `success` |
| Proforma creada | "Nueva proforma P250124 creada con 32 items desde batchPol" | `success` |

**Frecuencia:** Cada vez que se ejecuta el script (típicamente diario)

---

### **3. Script batchFacturasVencidas.py**
| Evento | Notificación | Tipo |
|--------|--------------|------|
| Facturas vencidas | "3 factura(s) marcada(s) como vencida(s) (>15 días)" | `warning` |

**Frecuencia:** Cada vez que se ejecuta el script (típicamente diario)

---

### **4. Script scrapeo.py**
| Evento | Notificación | Tipo |
|--------|--------------|------|
| Movimientos importados | "5 nuevo(s) movimiento(s) bancario(s) importado(s) desde scraping" | `info` |

**Frecuencia:** Cada vez que se ejecuta el scraping bancario (típicamente 2-3 veces al día)

---

## 🏗️ Arquitectura del Sistema

### **Base de Datos**

**Tabla: `notificaciones`**
```sql
CREATE TABLE notificaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL,           -- 'success', 'warning', 'info', 'error'
    mensaje TEXT NOT NULL,
    timestamp TEXT NOT NULL,      -- ISO format
    leida INTEGER DEFAULT 0       -- 0: no leída, 1: leída
)
```

**Tabla: `conciliacion_gastos`**
```sql
-- Campo adicional para notificaciones de conciliación
notificado INTEGER DEFAULT 0     -- 0: no notificado, 1: notificado
```

---

### **Backend (Python)**

**Archivo: `notificaciones_utils.py`**
```python
def guardar_notificacion(mensaje, tipo='info', db_path=DB_NAME):
    """
    Guarda una notificación en la base de datos
    
    Args:
        mensaje: Texto de la notificación
        tipo: 'success', 'warning', 'info', 'error'
        db_path: Ruta a la base de datos
    """
```

**Endpoints API (Flask):**
```python
GET  /api/conciliacion/notificaciones           # Listar no leídas
POST /api/conciliacion/marcar-notificadas       # Marcar como leídas
GET  /api/conciliacion/contador-notificaciones  # Contador
```

---

### **Frontend (JavaScript)**

**Archivo: `index.html`**
- Icono de campana en menú lateral
- Badge rojo con contador
- Panel desplegable con lista

**Actualización automática:**
```javascript
// Cada 30 segundos
setInterval(actualizarContadorNotificaciones, 30000);
```

---

## 🎨 Interfaz de Usuario

### **Badge de Notificaciones**

```
┌─────────────────┐
│ 🔔 [3]          │  ← Badge rojo con contador
└─────────────────┘
```

**Estados:**
- Sin notificaciones: Icono gris, sin badge
- Con notificaciones: Icono activo, badge rojo con número

---

### **Panel de Notificaciones**

```
┌────────────────────────────────────────────┐
│ 🔔 Notificaciones                     [×]  │
├────────────────────────────────────────────┤
│ ✅ Proforma P250123 actualizada con 45... │
│    Hace 2 horas                            │
├────────────────────────────────────────────┤
│ ⚠️  3 facturas marcadas como vencidas     │
│    Hace 5 horas                            │
├────────────────────────────────────────────┤
│ ℹ️  5 movimientos bancarios importados    │
│    Hace 1 día                              │
└────────────────────────────────────────────┘
         [Marcar todas como leídas]
```

---

## 🔄 Flujo de Notificaciones

### **Flujo Completo**

```
1. EVENTO (Script/Proceso)
   ↓
2. guardar_notificacion()
   ↓
3. INSERT en tabla notificaciones
   ↓
4. Usuario abre aplicación
   ↓
5. GET /api/conciliacion/contador-notificaciones
   ↓
6. Badge rojo aparece 🔴
   ↓
7. Usuario click en campana
   ↓
8. GET /api/conciliacion/notificaciones
   ↓
9. Panel se despliega con lista
   ↓
10. Usuario lee notificaciones
    ↓
11. Click "Marcar como leídas"
    ↓
12. POST /api/conciliacion/marcar-notificadas
    ↓
13. Badge desaparece
```

---

## 📝 Tipos de Notificaciones

| Tipo | Icono | Color | Uso |
|------|-------|-------|-----|
| `success` | ✅ | Verde | Operaciones exitosas |
| `warning` | ⚠️ | Naranja | Alertas importantes |
| `info` | ℹ️ | Azul | Información general |
| `error` | ❌ | Rojo | Errores críticos |

---

## 🔧 Integración en Scripts

### **Patrón de Uso**

```python
from notificaciones_utils import guardar_notificacion
from constantes import DB_NAME

# Al final del proceso exitoso
if registros_procesados > 0:
    guardar_notificacion(
        f"{registros_procesados} registros procesados correctamente",
        tipo='success',
        db_path=DB_NAME
    )
```

---

### **Scripts Integrados**

| Script | Línea | Condición |
|--------|-------|-----------|
| `batchPol.py` | 393-397 | Al actualizar proforma |
| `batchPol.py` | 410-414 | Al crear proforma |
| `batchFacturasVencidas.py` | 80-85 | Si facturas_actualizadas > 0 |
| `scrapeo.py` | 179-184 | Si inserted > 0 |
| `conciliacion_auto.py` | - | Cada conciliación automática |

---

## 📊 Estadísticas de Uso

### **Frecuencia Estimada**

| Fuente | Frecuencia | Notificaciones/día |
|--------|------------|-------------------|
| Scraping | 2-3 veces/día | 2-3 |
| batchPol | 1 vez/día | 1 |
| Facturas vencidas | 1 vez/día | 0-1 |
| Conciliación | Al cargar app | 0-10 |
| **TOTAL** | - | **3-15/día** |

---

## 🎯 Casos de Uso

### **Caso 1: Scraping Bancario**
```
06:00 → Scraping ejecutado
06:01 → 5 movimientos importados
06:02 → Notificación creada
08:00 → Usuario abre app
08:01 → Ve badge 🔴 [1]
08:02 → Lee: "5 movimientos bancarios importados"
```

### **Caso 2: Conciliación Automática**
```
10:00 → Usuario abre CONCILIACION_GASTOS.html
10:01 → Conciliación automática ejecutada
10:02 → 3 gastos conciliados
10:03 → 3 notificaciones creadas
10:04 → Badge 🔴 [3] aparece
10:05 → Usuario ve lista de conciliaciones
```

### **Caso 3: Facturas Vencidas**
```
07:00 → batchFacturasVencidas ejecutado
07:01 → 2 facturas marcadas como vencidas
07:02 → Notificación warning creada
09:00 → Usuario abre app
09:01 → Ve badge 🔴 [1] con alerta naranja
09:02 → Lee: "2 facturas marcadas como vencidas"
09:03 → Toma acción (revisar facturas)
```

---

## 🚀 Configuración Recomendada

### **Cron Jobs**

```bash
# Scraping bancario (3 veces al día)
0 6,15,20 * * * /var/www/html/venv/bin/python /var/www/html/scrapeo.py

# batchPol (1 vez al día)
30 7 * * * /var/www/html/venv/bin/python /var/www/html/batchPol.py

# Facturas vencidas (1 vez al día)
0 8 * * * /var/www/html/venv/bin/python /var/www/html/batchFacturasVencidas.py

# Conciliación automática (después de scraping)
15 6,15,20 * * * /var/www/html/scraping_y_conciliacion.sh
```

---

## 📱 Características del Sistema

### **Ventajas**

✅ **Centralizado** - Todas las notificaciones en un solo lugar  
✅ **Automático** - No requiere intervención manual  
✅ **En tiempo real** - Actualización cada 30 segundos  
✅ **Persistente** - Guardado en base de datos  
✅ **Filtrable** - Por tipo, fecha, estado  
✅ **Responsive** - Funciona en móvil y desktop  

### **Funcionalidades**

- ✅ Badge con contador
- ✅ Panel desplegable
- ✅ Marcar como leídas (individual o todas)
- ✅ Timestamp relativo ("Hace 2 horas")
- ✅ Iconos por tipo
- ✅ Colores diferenciados
- ✅ Navegación a detalle (conciliaciones)

---

## 🔍 Debugging y Logs

### **Verificar Notificaciones**

```bash
# Ver notificaciones en BD
sqlite3 /var/www/html/db/aleph70.db "SELECT * FROM notificaciones ORDER BY id DESC LIMIT 10"

# Contar no leídas
sqlite3 /var/www/html/db/aleph70.db "SELECT COUNT(*) FROM notificaciones WHERE leida = 0"

# Ver por tipo
sqlite3 /var/www/html/db/aleph70.db "SELECT tipo, COUNT(*) FROM notificaciones GROUP BY tipo"
```

### **Logs de Scripts**

```bash
# batchPol
tail -f /var/www/html/logs/batchPol.log

# Conciliación
tail -f /var/www/html/logs/conciliacion_auto.log

# Scraping
tail -f /var/www/html/logs/scraping_status.log
```

---

## 📚 API Reference

### **GET /api/conciliacion/notificaciones**
Obtiene notificaciones no leídas

**Response:**
```json
{
  "success": true,
  "notificaciones": [
    {
      "id": 1,
      "tipo": "success",
      "mensaje": "Proforma P250123 actualizada...",
      "timestamp": "2025-10-07T14:30:00",
      "leida": 0
    }
  ],
  "total": 1
}
```

### **POST /api/conciliacion/marcar-notificadas**
Marca notificaciones como leídas

**Request:**
```json
{
  "ids": [1, 2, 3]
}
```

**Response:**
```json
{
  "success": true,
  "message": "3 notificaciones marcadas como leídas"
}
```

### **GET /api/conciliacion/contador-notificaciones**
Obtiene contador de no leídas

**Response:**
```json
{
  "success": true,
  "total": 5
}
```

---

## 🎉 Conclusión

El sistema de notificaciones está **completamente implementado y funcional**, proporcionando:

1. ✅ **Visibilidad completa** de todos los procesos automáticos
2. ✅ **Notificaciones en tiempo real** con actualización automática
3. ✅ **Integración total** con 4 fuentes diferentes
4. ✅ **Interfaz intuitiva** con badge y panel desplegable
5. ✅ **Persistencia** en base de datos
6. ✅ **Gestión** de estado leído/no leído

**El usuario ahora está siempre informado de todas las operaciones automáticas del sistema.**

---

*Última actualización: 2025-10-07 14:34*  
*Estado: PRODUCCIÓN (DESARROLLO)*  
*Versión: 1.0.0*

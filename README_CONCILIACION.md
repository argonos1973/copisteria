# Sistema de Conciliación Bancaria Automática

## 📋 Descripción

Sistema automático que concilia gastos bancarios (tabla `gastos`) con facturas y tickets cobrados, eliminando la necesidad de hacerlo manualmente.

## 🎯 Funcionamiento Automático

### 1. **Conciliación al cargar página**
- Al abrir `CONCILIACION_GASTOS.html`, ejecuta automáticamente
- Concilia todos los gastos pendientes con score ≥ 85%
- Notifica solo si encuentra y concilia algo

### 2. **Conciliación programada (Cron)**
```bash
# Ejecutar después del scraping bancario
0 7,16,21 * * * /var/www/html/scraping_y_conciliacion.sh
```

### 3. **Script manual**
```bash
# Ejecutar manualmente con umbral 90%
python3 /var/www/html/conciliacion_auto.py 90

# O con umbral 85%
python3 /var/www/html/conciliacion_auto.py 85
```

## 🔍 Criterios de Coincidencia

### **Búsqueda automática**
- **Importe**: ±2 céntimos de tolerancia
- **Fecha**: ±7 días de margen
- **Estado**: Solo documentos cobrados (facturas/tickets con estado 'C')
- **Duplicados**: No concilia gastos ya conciliados

### **Sistema de Scoring (0-100%)**

| Puntos | Factor | Criterio |
|--------|--------|----------|
| 50 pts | Importe | Exacto=50, ±1ct=45, ±2ct=40 |
| 30 pts | Fecha | Mismo día=30, ±1día=25, ±3días=20, ±7días=10 |
| 20 pts | Exactitud | Importe exacto=20, ±1ct=15 |

### **Umbrales de Acción**

| Score | Acción | Descripción |
|-------|--------|-------------|
| ≥ 90% | ✅ Conciliar automático | Muy confiable, concilia sin intervención |
| 85-89% | ✅ Conciliar automático | Confiable, concilia automáticamente |
| 70-84% | ⚠️ Sugerencia | Requiere revisión manual |
| < 70% | ❌ Ignorar | No procesar |

## 📊 Tabla de Base de Datos

```sql
CREATE TABLE conciliacion_gastos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gasto_id INTEGER NOT NULL,
    tipo_documento TEXT NOT NULL,        -- 'factura' o 'ticket'
    documento_id INTEGER NOT NULL,
    fecha_conciliacion TEXT NOT NULL,
    importe_gasto REAL NOT NULL,
    importe_documento REAL NOT NULL,
    diferencia REAL,
    estado TEXT DEFAULT 'conciliado',    -- 'conciliado', 'pendiente', 'rechazado'
    metodo TEXT,                         -- 'automatico' o 'manual'
    notas TEXT,
    FOREIGN KEY(gasto_id) REFERENCES gastos(id),
    UNIQUE(gasto_id, tipo_documento, documento_id)
);
```

## 🚀 Uso

### **Primera vez**
1. Acceder a: `http://192.168.1.23/frontend/CONCILIACION_GASTOS.html`
2. Clic en "Inicializar Sistema" (crea la tabla)
3. Clic en "Conciliar Automático" o esperar a que se ejecute solo

### **Uso diario**
- El sistema se ejecuta automáticamente:
  - Al abrir la página de conciliación
  - Después de cada scraping bancario (si está en cron)
  - Manualmente con el botón "Conciliar Automático"

### **Revisión manual**
- Pestaña "Pendientes": Gastos sin conciliar
- Botón "Buscar": Ver coincidencias y seleccionar manualmente
- Pestaña "Conciliados": Ver historial de conciliaciones

## 📁 Archivos del Sistema

| Archivo | Descripción |
|---------|-------------|
| `conciliacion.py` | Backend Flask con API REST |
| `conciliacion_auto.py` | Script standalone para cron |
| `scraping_y_conciliacion.sh` | Script integrado scraping + conciliación |
| `frontend/CONCILIACION_GASTOS.html` | Interfaz web |
| `static/conciliacion_gastos.js` | Lógica frontend |

## 🔧 API Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/conciliacion/inicializar` | Crear tabla |
| GET | `/api/conciliacion/buscar/<gasto_id>` | Buscar coincidencias |
| POST | `/api/conciliacion/conciliar` | Conciliar manual |
| GET | `/api/conciliacion/gastos-pendientes` | Listar pendientes |
| GET | `/api/conciliacion/conciliados` | Listar conciliados |
| DELETE | `/api/conciliacion/eliminar/<id>` | Eliminar conciliación |
| POST | `/api/conciliacion/procesar-automatico` | Procesar todos |
| GET | `/api/conciliacion/ejecutar-cron` | Endpoint para cron |

## 📈 Estadísticas

La interfaz muestra en tiempo real:
- **Gastos Pendientes**: Cantidad de gastos sin conciliar
- **Conciliados**: Cantidad de conciliaciones realizadas
- **Total Pendiente**: Suma de importes pendientes
- **Total Conciliado**: Suma de importes conciliados

## ⚙️ Configuración Avanzada

### **Ajustar umbral de conciliación**
```javascript
// En conciliacion_gastos.js, línea 365
umbral_score: 85  // Cambiar a 90 para ser más estricto, 80 para ser más permisivo
```

### **Ajustar tolerancia de importe**
```python
# En conciliacion.py, línea 27
tolerancia = 0.02  # Cambiar a 0.05 para 5 céntimos, 0.01 para 1 céntimo
```

### **Ajustar rango de fechas**
```python
# En conciliacion.py, líneas 25-26
fecha_inicio = (fecha_gasto - timedelta(days=7))  # Cambiar días
fecha_fin = (fecha_gasto + timedelta(days=7))
```

## 🔄 Flujo Automático Completo

```
1. Scraping bancario (scrapeo.py)
   ↓
2. Nuevos gastos en tabla gastos
   ↓
3. Conciliación automática (conciliacion_auto.py)
   ↓
4. Busca facturas/tickets cobrados
   ↓
5. Calcula score de coincidencia
   ↓
6. Si score ≥ 85%: Concilia automáticamente
   ↓
7. Registra en tabla conciliacion_gastos
```

## 📝 Logs

Los logs se guardan en:
```
/var/www/html/logs/conciliacion_auto.log
```

Formato:
```
========================================
Inicio: 2025-10-07 08:00:00
========================================
[1/2] Ejecutando scraping bancario...
✓ Scraping completado exitosamente
[2/2] Ejecutando conciliación automática...
Gastos pendientes encontrados: 15
  ✓ Gasto 1234 (2025-10-05, 45.50€) → FACTURA F250123 (score: 95%)
  ✓ Gasto 1235 (2025-10-06, 120.00€) → TICKET T255678 (score: 92%)
Resumen:
  - Procesados: 15
  - Conciliados: 2
  - Pendientes: 13
Fin: 2025-10-07 08:00:15
```

## ⚠️ Notas Importantes

- **Solo en desarrollo**: Este sistema está solo en 192.168.1.23
- **No desplegado en producción**: No está en 192.168.1.18 ni 192.168.1.55
- **Requiere inicialización**: Primera vez ejecutar "Inicializar Sistema"
- **Solo ingresos**: Solo concilia gastos con importe positivo (ingresos)
- **Solo cobrados**: Solo busca en facturas/tickets con estado 'C' (cobrado)

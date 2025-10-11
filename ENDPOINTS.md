# Documentación de Endpoints API

## Resumen
- **Total de endpoints:** 137
- **Archivos con endpoints:** 4 (app.py, factura.py, conciliacion.py, dashboard_routes.py)
- **Última actualización:** 2025-10-11

---

## 🔴 Problemas Identificados

### 1. Rutas Duplicadas en app.py
- `/productos/<int:id>` - 3 funciones (GET, PUT, DELETE)
- `/api/productos/<int:id>` - 3 funciones (GET, PUT, DELETE)
- `/productos` - 2 funciones (GET, POST)
- `/api/productos` - 2 funciones (GET, POST)
- `/productos/<int:producto_id>/franjas_descuento` - 2 funciones (GET, POST/PUT)
- `/api/productos/<int:producto_id>/franjas_config` - 2 funciones (GET, POST/PUT)

**Acción requerida:** Consolidar usando `request.method`

### 2. Rutas Duplicadas Entre Archivos
- `/api/ventas/total_mes` - app.py + dashboard_routes.py
- `/api/ventas/media_por_documento` - app.py + dashboard_routes.py
- `/api/clientes/ventas_mes` - app.py + dashboard_routes.py

**Acción requerida:** Eliminar de app.py, mantener en dashboard_routes.py

### 3. Inconsistencia de Prefijos
- app.py: 69 rutas con `/api/`, 35 sin `/api/`
- dashboard_routes.py: 6 con `/api/`, 2 sin `/api/`

**Acción requerida:** Estandarizar todas las rutas API con `/api/`

---

## ✅ Endpoints por Módulo

### Conciliación (19 endpoints) - ✅ Bien organizado
Todos los endpoints usan el prefijo `/api/conciliacion/`

- `POST /api/conciliacion/inicializar` - Inicializar sistema
- `GET /api/conciliacion/buscar/<int:gasto_id>` - Buscar coincidencias
- `POST /api/conciliacion/conciliar` - Conciliar gasto
- `GET /api/conciliacion/gastos-pendientes` - Listar gastos pendientes
- `GET /api/conciliacion/conciliados` - Listar conciliados
- `GET /api/conciliacion/detalles/<int:gasto_id>` - Detalles de conciliación
- `GET /api/conciliacion/liquidacion-tpv-detalles` - Detalles liquidación TPV
- `DELETE /api/conciliacion/eliminar/<int:conciliacion_id>` - Eliminar conciliación
- `POST /api/conciliacion/procesar-automatico` - Procesar automático
- `GET /api/conciliacion/ejecutar-cron` - Ejecutar cron
- `GET /api/conciliacion/notificaciones` - Obtener notificaciones
- `POST /api/notificaciones/eliminar` - Eliminar notificaciones
- `POST /api/conciliacion/marcar-notificadas` - Marcar como notificadas
- `GET /api/conciliacion/contador-notificaciones` - Contador de notificaciones
- `GET /api/conciliacion/liquidaciones-tpv` - Obtener liquidaciones TPV
- Y 4 endpoints más...

### Dashboard (14 endpoints)
Estadísticas y métricas de ventas

- `GET /estadisticas_gastos` - Estadísticas de gastos
- `GET /api/ventas/total_mes` - Totales mensuales de ventas
- `GET /ventas/total_mes` - Alias sin /api/
- `GET /api/ventas/media_por_documento` - Media por documento
- `GET /ventas/media_por_documento` - Alias sin /api/
- `GET /api/clientes/top_ventas` - Top clientes por ventas
- `GET /clientes/top_ventas` - Alias sin /api/
- `GET /api/clientes/ventas_mes` - Ventas mensuales por cliente
- `GET /clientes/ventas_mes` - Alias sin /api/
- `GET /api/productos/ventas_mes` - Ventas mensuales por producto
- `GET /productos/ventas_mes` - Alias sin /api/
- `GET /api/productos/top_ventas` - Top productos por ventas
- `GET /gastos/top_gastos` - Top gastos
- `GET /productos/top_ventas` - Alias sin /api/

### Facturas (6 endpoints) - ✅ Consolidadas
- `GET /facturas` - Listar/filtrar facturas
- `GET, POST /facturas/<int:id_factura>/detalles` - Detalles de factura (consolidado)
- `GET, POST /contactos/<int:idContacto>/facturas` - Facturas por contacto (consolidado)

### Productos (23 endpoints en app.py)
⚠️ Necesita consolidación

**Rutas principales:**
- `GET, POST /productos` - Listar y crear productos
- `GET, PUT, DELETE /productos/<int:id>` - CRUD de producto
- `GET, POST /api/productos` - Versión API
- `GET, PUT, DELETE /api/productos/<int:id>` - Versión API
- `GET /api/productos/buscar` - Buscar productos
- `GET, POST/PUT /productos/<int:producto_id>/franjas_descuento` - Franjas de descuento
- `GET, POST/PUT /api/productos/<int:producto_id>/franjas_config` - Config de franjas
- `POST /api/productos/<int:producto_id>/generar_franjas_automaticas` - Generar franjas

### Tickets (10 endpoints en app.py)
- `GET /tickets/paginado` - Listar tickets paginados
- `GET /api/tickets/paginado` - Versión API
- Y 8 endpoints más...

### Contactos (9 endpoints en app.py)
- `GET /api/contactos/paginado` - Listar contactos paginados
- `GET /contactos/paginado` - Alias sin /api/
- Y 7 endpoints más...

### Presupuestos (7 endpoints en app.py)
- `GET /api/presupuestos` - Listar presupuestos
- `POST /api/presupuestos` - Crear presupuesto
- Y 5 endpoints más...

### Proformas (6 endpoints en app.py)
- `GET /api/proformas` - Listar proformas
- `POST /api/proformas` - Crear proforma
- Y 4 endpoints más...

---

## 📊 Distribución por Prefijo

| Prefijo | Cantidad | Estado |
|---------|----------|--------|
| `/api/conciliacion` | 18 | ✅ OK |
| `/api/productos` | 13 | ⚠️ Duplicados |
| `/productos` | 10 | ⚠️ Sin /api/ |
| `/tickets` | 10 | ⚠️ Sin /api/ |
| `/api/contactos` | 9 | ✅ OK |
| `/api/facturas` | 8 | ✅ OK |
| `/facturas` | 7 | ⚠️ Duplicados |
| `/api/presupuestos` | 7 | ✅ OK |
| `/api/tickets` | 6 | ✅ OK |
| `/api/proformas` | 6 | ✅ OK |

---

## 🎯 Plan de Acción

### Prioridad Alta
1. **Eliminar duplicados entre app.py y dashboard_routes.py**
   - Eliminar: `obtener_totales_mes`, `obtener_media_por_documento`, `api_ventas_cliente_mes`
   - Mantener solo en dashboard_routes.py

2. **Consolidar rutas por método en app.py**
   - Productos: Reducir de 23 a ~12 funciones
   - Usar `request.method` para manejar múltiples métodos HTTP

3. **Estandarizar prefijo /api/**
   - Todas las rutas API deben usar `/api/`
   - Rutas sin `/api/` solo para páginas HTML

### Prioridad Media
4. **Migrar app.py a Blueprints**
   - Crear: `productos_bp`, `facturas_bp`, `tickets_bp`, `contactos_bp`
   - Separar en archivos modulares

5. **Documentar endpoints con OpenAPI/Swagger**
   - Añadir especificación OpenAPI 3.0
   - Generar documentación interactiva

### Prioridad Baja
6. **Añadir validación de parámetros**
7. **Implementar rate limiting**
8. **Añadir versionado de API (v1, v2)**

---

## 📝 Cambios Realizados

### 2025-10-11
- ✅ Consolidadas rutas duplicadas en `factura.py`:
  - `/facturas/<int:id_factura>/detalles` ahora maneja GET y POST
  - `/contactos/<int:idContacto>/facturas` ahora maneja GET y POST
  - Eliminada ruta duplicada `/facturas` (consultar_facturas_get)
- ✅ Reducidas 4 funciones duplicadas
- ✅ Código más limpio y mantenible

---

## 🔧 Uso de Endpoints

### Ejemplo: Crear Factura
```bash
POST /contactos/123/facturas
Content-Type: application/json

{
  "fecha": "2025-10-11",
  "total": 100.50,
  "detalles": [...]
}
```

### Ejemplo: Buscar Coincidencias de Conciliación
```bash
GET /api/conciliacion/buscar/456
```

### Ejemplo: Listar Productos con Filtros
```bash
GET /api/productos/buscar?nombre=papel&categoria=oficina
```

---

## 📚 Referencias
- Código fuente: `/var/www/html/`
- Blueprint de conciliación: `conciliacion.py`
- Blueprint de dashboard: `dashboard_routes.py`
- Endpoints principales: `app.py`
- Endpoints de facturas: `factura.py`

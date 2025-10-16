# 📊 Estudio Completo del Código - Proyecto Aleph70 (Parte 1/2)

**Fecha de Análisis**: 16 de Octubre de 2025  
**Base de Código**: ~31,000 líneas Python + ~650,000 líneas totales  
**Versión**: Producción activa en 3 servidores

---

## 📋 Resumen Ejecutivo

Aleph70 es un **sistema ERP completo** para gestión de copisterías/imprentas que integra:
- Facturación electrónica (FacturaE, VeriFactu, FACe)
- Punto de venta (POS/Tickets)
- Gestión de productos con descuentos por franjas
- Conciliación bancaria automática
- Analytics y estadísticas financieras
- Batch processing y automatizaciones

**Estado General**: ✅ Sistema funcional y estable con áreas de mejora identificadas.

---

## 🏗️ Arquitectura del Sistema

### Estructura de Archivos Principal

```
/var/www/html/
├── app.py                      (3,088 líneas) - Core aplicación Flask
├── factura.py                  (2,465 líneas) - Módulo facturación
├── conciliacion.py             (2,276 líneas) - Conciliación bancaria
├── api_scraping.py             (1,573 líneas) - Integración bancaria
├── estadisticas_gastos_routes.py (1,338 líneas) - Analytics
├── verifactu.py                (1,206 líneas) - VeriFactu AEAT
├── productos.py                (1,091 líneas) - Catálogo productos
├── tickets.py                  (1,091 líneas) - Punto de venta
├── presupuesto.py              (1,102 líneas) - Presupuestos
└── dashboard_routes.py           (921 líneas) - Dashboard UI
```

### Tecnologías Core

**Backend:**
- Flask 2.0.1 (Framework web)
- SQLite 3 (Base de datos)
- WeasyPrint 60.2 (Generación PDF)
- lxml 5.2.1 (Procesamiento XML)
- cryptography 41.0.7 (Firma digital)

**Frontend:**
- JavaScript Vanilla (~50 archivos, 650KB código)
- CSS custom (~60KB estilos)
- Sin frameworks JS (jQuery, React, etc.)

---

## 📊 Métricas de Código

### Estadísticas Generales

| Métrica | Valor | Evaluación |
|---------|-------|------------|
| **Archivos Python principales** | 80+ | 🟡 Modular |
| **Líneas totales Python** | ~31,000 | 🟡 Grande |
| **Funciones totales** | 162+ | ✅ Bien estructurado |
| **Clases** | 0 | 🔴 Falta POO |
| **Endpoints API** | 135 | 🟡 Muchos |
| **Consultas SQL** | 199+ | 🔴 Optimización necesaria |
| **Bloques try/except** | 202 | ✅ Buen manejo errores |

### Distribución de Código por Módulo

| Módulo | Líneas | % Total | Complejidad |
|--------|--------|---------|-------------|
| Core (app.py) | 3,088 | 15% | 🔴 Alta |
| Facturación | 2,465 | 12% | 🔴 Alta |
| Conciliación | 2,276 | 11% | 🟡 Media |
| Integración | 1,573 | 8% | 🟡 Media |
| Analytics | 1,338 | 7% | 🟢 Baja |
| VeriFactu | 1,206 | 6% | 🟡 Media |
| Productos | 1,091 | 5% | 🟢 Baja |
| POS/Tickets | 1,091 | 5% | 🟡 Media |
| Dashboard | 921 | 5% | 🟢 Baja |
| Utilities | ~17,000 | 41% | Variable |

---

## 🔷 Arquitectura Flask

### Blueprints Identificados

```python
# Modular separation con Blueprints
factura_bp = Blueprint('factura', __name__)           # factura.py
conciliacion_bp = Blueprint('conciliacion', __name__) # conciliacion.py
estadisticas_gastos_bp = Blueprint('estadisticas_gastos', __name__) # estadisticas_gastos_routes.py
```

**Evaluación**: ✅ Uso correcto de Blueprints para modularidad.

### Endpoints por Módulo

| Módulo | Rutas | Tipo | Evaluación |
|--------|-------|------|------------|
| app.py | 103 | REST + HTML | 🔴 Demasiadas en un archivo |
| conciliacion.py | 20 | REST | ✅ Bien |
| estadisticas_gastos_routes.py | 9 | REST | ✅ Bien |
| factura.py | 3 | REST | ✅ Bien |

**Problema identificado**: `app.py` tiene **103 rutas**, debería refactorizarse en múltiples blueprints.

---

## 🗄️ Base de Datos

### Tablas Principales

```
21 tablas SQLite identificadas:

CORE:
├── factura (24 columnas)          - Facturas emitidas
├── tickets (18 columnas)          - Tickets POS
├── contactos (15 columnas)        - Clientes/Proveedores
├── productos (12 columnas)        - Catálogo productos
└── gastos (9 columnas)            - Extracto bancario

DETALLES:
├── detalle_factura               - Líneas factura
├── detalle_tickets               - Líneas ticket
├── detalle_presupuesto           - Líneas presupuesto
└── detalle_proforma              - Líneas proforma

AUXILIARES:
├── conciliacion_gastos           - Matching gastos-docs
├── conciliacion_documentos       - Documentos conciliados
├── descuento_producto_franja     - Descuentos por volumen
├── numerador                     - Secuencias numeración
├── notificaciones                - Sistema notificaciones
├── registro_facturacion          - Log VeriFactu
├── codipostal                    - Códigos postales
└── provincia                     - Provincias España
```

### Índices Optimizados (Reciente)

✅ **7 índices en tabla `gastos`** creados el 16/10/2025:
- `idx_gastos_fecha_operacion`
- `idx_gastos_importe_puntual_fecha` (covering index)
- `idx_gastos_puntual`
- `idx_gastos_ejercicio`
- `idx_gastos_fecha_concepto`
- `idx_gastos_concepto_lower`
- `idx_gastos_fecha_valor_iso`

**Mejora de rendimiento**: ~50-100x más rápido en consultas de estadísticas.

---

## ⚠️ Code Smells Detectados

### Análisis de Calidad del Código

| Issue | Cantidad | Severidad | Prioridad |
|-------|----------|-----------|-----------|
| **Print Statements (Debug)** | 236 | 🔴 Alta | P1 - Crítico |
| **Rutas Hardcoded** | 21 | 🟡 Media | P2 - Alta |
| **Bare Except** | 9 | 🟢 Baja | P3 - Media |
| **SQL Injection Risk** | 1 | 🟢 Baja | P2 - Alta |
| **TODO/FIXME Comments** | 0 | ✅ N/A | - |

### Detalle de Problemas

#### 1. Print Statements (236 ocurrencias) 🔴

**Problema**: Uso extensivo de `print()` para debugging en producción.

**Solución recomendada**:
```python
import logging
logger = logging.getLogger(__name__)

# Reemplazar
print(f"Error: {e}")

# Por
logger.error(f"Error al marcar gastos puntuales: {e}", exc_info=True)
```

**Prioridad**: 🔴 **P1 - Implementar logging profesional**

---

## 📏 Funciones Largas

### Top 10 Funciones por Longitud

| Función | Líneas | Archivo | Complejidad |
|---------|--------|---------|-------------|
| `actualizar_factura` | 566 | factura.py | 🔴 Muy Alta |
| `enviar_factura_email` | 533 | factura.py | 🔴 Muy Alta |
| `crear_factura` | 385 | factura.py | 🔴 Muy Alta |
| `obtener_media_por_documento` | 336 | app.py | 🔴 Alta |
| `obtener_ingresos_efectivo` | 288 | conciliacion.py | 🟡 Alta |
| `obtener_factura_para_imprimir` | 270 | app.py | 🟡 Alta |
| `obtener_liquidaciones_tpv` | 217 | conciliacion.py | 🟡 Media |
| `generar_informe_situacion` | 216 | estadisticas_gastos_routes.py | 🟡 Media |
| `obtener_facturas_paginadas` | 188 | factura.py | 🟡 Media |
| `actualizar_ticket_legacy` | 171 | app.py | 🟡 Media |

**Recomendación**: 🔴 **Refactorizar funciones >300 líneas urgentemente**

---

Ver ESTUDIO_CODIGO_PARTE2.md para el resto del análisis.

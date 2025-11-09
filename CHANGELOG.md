# CHANGELOG - Aleph70 Sistema de Gestión

## [1.2.2] - 2025-11-09

### Corrección: Fondo de Modales Transparente
- ✅ Cambiado fondo de modales de rgba(0,0,0,0.5) a transparent
- ✅ Modificado styles.css: .modal background-color: transparent
- ✅ Modificado modales.css: .modal background-color: transparent !important
- ✅ Elimina el fondo oscuro semi-transparente de los modales
- ✅ Los modales ahora tienen fondo completamente transparente

**Archivos modificados**:
- static/styles.css (línea 837)
- static/modales.css (línea 125)

**Antes**: background-color: rgba(0, 0, 0, 0.5) - fondo oscuro semi-transparente
**Ahora**: background-color: transparent - completamente transparente

---

## [1.2.1] - 2025-11-09

### Corrección: Mayor Especificidad en Estilos de Botones
- ✅ Botón Nuevo Contacto ahora sobrescribe estilos de styles.css
- ✅ Botón Agregar Detalle con mayor especificidad (button#btn-agregar-detalle)
- ✅ Agregados selectores button.btn-icon[type="button"] para mayor especificidad
- ✅ Sobrescrito background-color y border-color con !important
- ✅ Todos los botones ahora muestran correctamente el color primario de la plantilla
- ✅ Eliminado fondo amarillo/naranja del botón Nuevo Contacto

**Problema resuelto**:
Los estilos de `styles.css` (líneas 2820-2830) que afectan a `button[type="button"]`
estaban sobrescribiendo los estilos de `.btn-icon` porque tenían `!important` y
mayor especificidad. Ahora `button.btn-icon[type="button"]` tiene mayor especificidad
y sobrescribe correctamente.

**Antes**: 
- Botón Nuevo Contacto: fondo amarillo/naranja (var(--color-button))
- Botón Agregar Detalle: fondo amarillo/naranja, tamaño 40x40px

**Ahora**: 
- Botón Nuevo Contacto: fondo transparente, color primario
- Botón Agregar Detalle: fondo transparente, color primario, ancho automático

---

## [1.2.0] - 2025-11-09

### Mejora: Botones Sin Bordes - Diseño Unificado
- ✅ Eliminados bordes de botones + en formularios (Nuevo Ticket, Contactos, etc.)
- ✅ Botón agregar detalle (#btn-agregar-detalle) ahora usa mismo estilo que btn-icon
- ✅ Todos los botones de acción ahora son sin borde, solo icono con color primario
- ✅ Botones adaptados a todas las plantillas (var(--primary-color))
- ✅ Diseño más limpio y minimalista
- ✅ Hover consistente con scale 1.1 y opacity 0.8

**Cambios específicos**:
- Botón Nuevo Ticket: sin borde, solo icono
- Botón Nuevo Contacto: sin borde, adaptado a plantilla
- Botón Nuevo Detalle: sin borde, color primario
- Todos los botones + en consultas: sin borde

**Antes**: Botones con borde 2px solid var(--primary-color)
**Ahora**: Botones sin borde, fondo transparente, solo color primario

---

## [1.1.2] - 2025-11-09

### Corrección: Ancho de Botones + en Formularios
- ✅ Agregada regla para form-group con solo btn-icon
- ✅ Evita que .form-group tenga min-width cuando solo contiene un botón
- ✅ Botón "Nuevo Ticket" ahora es compacto (mismo ancho que "Nuevo Detalle")
- ✅ Usa selector :has() para detectar form-group con solo btn-icon
- ✅ width: auto y min-width: auto para form-group con btn-icon

**Antes**: Botón + ocupaba min-width: 150px del form-group
**Ahora**: Botón + solo ocupa su ancho natural (padding + icono)

---

## [1.1.1] - 2025-11-09

### Corrección: Tamaño de Iconos en Tablas
- ✅ Separados estilos de .btn-icon: tablas vs formularios
- ✅ Iconos en tablas ahora son pequeños (16px, sin borde, sin padding)
- ✅ Iconos ✎ ⚡ ✕ ahora tienen mismo tamaño que en consulta de facturas
- ✅ Botones + en formularios mantienen estilo con borde (18px, padding, borde)
- ✅ Hover diferenciado: scale 1.2 en tablas, scale 1.1 en formularios

**Antes**: Iconos en tablas con borde y padding (parecían botones grandes)
**Ahora**: Iconos en tablas sin borde, tamaño 16px (como en facturas)

---

## [1.1.0] - 2025-11-09

### Mejora: Estilos de Botones + Centralizados en CSS
- ✅ Estilos de .btn-icon movidos a theme-consumer.css
- ✅ Eliminados estilos inline de todos los botones + en consultas
- ✅ Agregados selectores .form-group y .form-inline para btn-icon
- ✅ Botones + ahora se adaptan correctamente a plantilla Classic
- ✅ Tamaño compacto garantizado: padding 8px 12px
- ✅ Borde adaptativo: 2px solid var(--primary-color)
- ✅ Width auto y min-width auto para evitar anchos excesivos
- ✅ Mantenibilidad mejorada: estilos en un solo lugar

**Archivos modificados**:
- theme-consumer.css: Estilos centralizados para .btn-icon
- CONSULTA_CONTACTOS.html: Estilos inline eliminados
- CONSULTA_PRESUPUESTOS.html: Estilos inline eliminados
- CONSULTA_TICKETS.html: Estilos inline eliminados
- CONSULTA_PRODUCTOS.html: Estilos inline eliminados

---

## [1.0.9] - 2025-11-09

### Corrección Crítica: Fondo de Iconos en Tablas
- ✅ Agregadas excepciones en theme-consumer.css para .btn-icon
- ✅ Los iconos de acción en tablas ahora mantienen fondo transparente
- ✅ Sobrescribe reglas de .grid button y tbody button
- ✅ Fondo transparente garantizado con !important
- ✅ Color adaptativo mantenido (var(--primary-color))
- ✅ Hover con scale y opacity preservado

---

## [1.0.8] - 2025-11-09

### Corrección de Iconos de Acción en Tablas
- ✅ Iconos .btn-icon ahora usan var(--primary-color) en lugar de var(--text-color)
- ✅ Se adaptan correctamente a todas las plantillas (Classic, Porsche, etc.)
- ✅ Hover mejorado con efecto de escala (scale 1.2) y opacity
- ✅ Transición suave para todas las propiedades (all 0.2s ease)
- ✅ Corrección aplicada a iconos de consultas: ✎ ⚡ ✕

---

## [1.0.7] - 2025-11-09

### Ajuste de Botones + en Consultas
- ✅ Botones + ahora son compactos (padding: 8px 12px)
- ✅ Se adaptan a la plantilla activa (var(--primary-color))
- ✅ Borde de 2px con color primario
- ✅ Fondo transparente
- ✅ Border-radius 6px
- ✅ Tamaño de icono 18px
- ✅ Clase btn-icon agregada para consistencia

---

## [1.0.6] - 2025-11-09

### Mejoras en UI/UX Consultas
- ✅ Botones "Nuevo" reemplazados por icono + únicamente (fa-plus)
- ✅ Cambio aplicado en todas las consultas:
  - CONSULTA_CONTACTOS.html: "Nuevo Contacto" → <i class="fas fa-plus"></i>
  - CONSULTA_PRESUPUESTOS.html: "Nuevo" → <i class="fas fa-plus"></i>
  - CONSULTA_TICKETS.html: "Nuevo Ticket" → <i class="fas fa-plus"></i>
  - CONSULTA_PRODUCTOS.html: "Nuevo Producto" → <i class="fas fa-plus"></i>
- ✅ Todos los botones mantienen tooltip con texto descriptivo
- ✅ Diseño más limpio y compacto

---

## [1.0.5] - 2025-11-09

### Ajuste de Alineación
- ✅ Versión en menú lateral alineada a la izquierda (text-align: left)

---

## [1.0.4] - 2025-11-09

### Mejoras en Visualización de Versión
- ✅ Logo completo en bienvenida (igual que login: aleph_completo.png)
- ✅ Versión movida al menú lateral (abajo del todo, pequeña)
- ✅ Versión dinámica en menú: se carga desde /api/version
- ✅ Estilo discreto: v1.0.4 con icono, tamaño 10px
- ✅ Menú con flexbox para posicionar versión al final (margin-top: auto)

---

## [1.0.3] - 2025-11-09

### Mejoras en UI/UX Bienvenida
- ✅ Logo solo con símbolo ℵ (sin texto "Aleph" ni "El origen de todo...")
- ✅ Versión debajo del símbolo (layout vertical)
- ✅ Diseño minimalista: solo símbolo + versión
- ✅ Logo más compacto (300px ancho, 50vh alto)
- ✅ Fuente versión 1.5rem (equilibrada con símbolo)

---

## [1.0.2] - 2025-11-09

### Mejoras en UI/UX Bienvenida
- ✅ Logo sin texto "El origen de todo..." (imagen limpia)
- ✅ Versión mostrada al lado del logo (layout horizontal)
- ✅ Logo + versión en línea con flexbox (mejor proporción)
- ✅ Fuente más grande y ligera para versión (2rem, font-weight: 300)
- ✅ Formato "Aleph [versión]" → Logo "Aleph" + "1.0.2" al lado

---

## [1.0.1] - 2025-11-09

### Mejoras en UI/UX Login
- ✅ Logo completo de Aleph en pantalla de login (en lugar de favicon)
- ✅ Botón "Aceptar" en lugar de "Siguiente →" para mejor UX
- ✅ Logo más grande y mejor proporcionado (200px ancho)
- ✅ Eliminado título "Aleph70" (ya está en el logo)

---

## [1.0.0] - 2025-11-09

### Sistema Multiempresa
- ✅ Implementación completa del sistema multiempresa
- ✅ Gestión de usuarios por empresa
- ✅ Sistema de permisos por módulos y acciones
- ✅ Administración de empresas y usuarios

### Datos del Emisor Dinámicos
- ✅ Corrección de datos del emisor hardcodeados
- ✅ Carga dinámica desde archivos JSON por empresa
- ✅ Endpoint `/api/auth/emisor` para obtener datos completos
- ✅ Integración en facturas, tickets, presupuestos y PDFs
- ✅ Corrección de estructura de datos en frontend

### Sistema de Plantillas
- ✅ Carga dinámica de plantillas desde directorio
- ✅ Plantilla "Porsche Le Mans" con colores Gulf
- ✅ Sistema de branding adaptable
- ✅ Transparencia en loading overlay
- ✅ Iconos de botones transparentes

### Sistema de Permisos
- ✅ Control de visibilidad de botones por permisos
- ✅ Uso de `!important` para evitar sobrescritura
- ✅ Atributo `data-permiso-oculto` para tracking
- ✅ Página de estadísticas restringida a administradores

### Mejoras UI/UX
- ✅ Página de bienvenida con logo Aleph transparente
- ✅ Adaptación automática a temas
- ✅ Visualización de versión en página de bienvenida
- ✅ Modal de perfil adaptado a plantillas
- ✅ Eliminación de columna "Eliminar" en gestión de empresas

### Backend
- ✅ Funciones auxiliares para datos del emisor (`utils_emisor.py`)
- ✅ Endpoint `/api/version` para obtener versión de la aplicación
- ✅ Configuración de sesiones mejorada
- ✅ Sistema de logging estructurado

### Commits importantes
- #95: FIX - Usar datos del emisor dinámicamente desde JSON
- #96: FIX - Endpoint y estructura de datos del emisor
- #97: FEAT - Mostrar versión de la aplicación en página de bienvenida
- #98: FEAT - Formato "Aleph 1.0.0" y sistema de control de versiones

---

## Instrucciones para actualizar versión

1. **Editar versión en** `/var/www/html/app.py`:
   ```python
   APP_VERSION = '1.0.1'  # Cambiar aquí
   ```

2. **Actualizar este CHANGELOG**:
   - Agregar nueva sección con número de versión
   - Listar cambios realizados
   - Incluir fecha

3. **Reiniciar servicios**:
   ```bash
   sudo kill -HUP $(pgrep -f "gunicorn.*app:app" | head -1)
   ```

4. **Crear commit**:
   ```bash
   git add app.py CHANGELOG.md
   git commit -m "BUMP: Versión 1.0.X - Descripción de cambios"
   git push origin multiempresa
   ```

---

## Formato de versiones (Semantic Versioning)

- **MAJOR** (X.0.0): Cambios incompatibles con versiones anteriores
- **MINOR** (1.X.0): Nuevas funcionalidades compatibles
- **PATCH** (1.0.X): Correcciones de bugs y mejoras menores

---

**Versión actual**: 1.0.0
**Última actualización**: 2025-11-09

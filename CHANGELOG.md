# CHANGELOG - Aleph70 Sistema de Gestión

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

# 🎨 Editor de Colores V2 - Mejoras Implementadas

## ✨ Nuevas Características

### 1. Plantillas Actualizadas
- ✅ **Añadido**: Plantilla "Dark Mode" (🌙) - Modo oscuro moderno
- ❌ **Eliminado**: Plantilla "Cyber" 
- ✅ Plantillas actuales: Minimal, Zen, Dark Mode, Glassmorphism, Océano, Por Defecto

### 2. Detección de Plantilla Activa
- Al entrar al editor, se muestra la plantilla actualmente activa de la empresa
- Indicador visual en el sidebar mostrando la plantilla activa
- Si la plantilla ha sido modificada, se marca como "Personalizada"

### 3. Secciones con Acordeón
- Las secciones de personalización se pueden expandir/contraer
- Reduce el desorden visual
- Facilita encontrar los colores específicos

Secciones:
- 🎨 Colores Principales
- 🔘 Botones
- 🔔 Notificaciones y Alertas
- 📊 Tablas y Grids
- 🎯 Iconos y Detalles

### 4. Preview Mejorado
- **Más elementos visuales**:
  - Notificaciones de 4 tipos (success, warning, danger, info)
  - Tabla con encabezado personalizable
  - Grid con encabezado personalizable
  - Modal con botones
  - Galería de iconos
  - Tarjeta de texto completo

### 5. Guardado Inteligente
- **Detecta cambios** en los colores
- Si los colores fueron modificados respecto a una plantilla base:
  - Pregunta si desea crear una nueva plantilla personalizada
  - Permite nombrar la nueva plantilla "Basada en [Nombre Original]"
  - Guarda como plantilla personalizada
- Si no hubo cambios, guarda normalmente

## 🎨 Plantilla Dark Mode

```javascript
{
    nombre: 'Dark Mode',
    desc: 'Modo oscuro moderno',
    icon: '🌙',
    color_primario: '#1a1a1a',      // Menú lateral oscuro
    color_secundario: '#2a2a2a',    // Tarjetas oscuras
    color_button: '#4a4a4a',        // Botones grises
    color_button_hover: '#5a5a5a',  // Hover más claro
    color_header_text: '#ffffff',   // Texto blanco
    color_app_bg: '#0f0f0f',        // Fondo muy oscuro
    color_success: '#4caf50',       // Verde material
    color_warning: '#ff9800',       // Naranja material
    color_danger: '#f44336',        // Rojo material
    color_info: '#2196f3',          // Azul material
    color_header_bg: '#1a1a1a',     // Header oscuro
    color_grid_header: '#2a2a2a',   // Grid oscuro
    color_button_text: '#ffffff',   // Texto botones blanco
    color_grid_text: '#e0e0e0',     // Texto claro
    color_icon: '#b0b0b0'           // Iconos grises claros
}
```

## 📋 Cambios en Base de Datos

### Nueva Columna: `plantilla_personalizada`
```sql
ALTER TABLE empresas ADD COLUMN plantilla_personalizada TEXT NULL;
```

Esta columna almacena el nombre de plantillas personalizadas (ej: "Minimal Personalizado", "Basada en Dark Mode").

## 🔧 Funciones Principales Añadidas

### `determinarPlantillaActiva(empresa)`
Detecta qué plantilla está usando la empresa actualmente:
- Compara todos los colores con las plantillas predefinidas
- Si todos coinciden → plantilla predefinida
- Si alguno difiere → "custom" (personalizada)

### `actualizarPlantillaActiva(plantilla, nombrePersonalizado)`
Actualiza el indicador visual de plantilla activa en el sidebar.

### `toggleAccordion(header)`
Maneja la expansión/contracción de secciones acordeón.

### `detectarCambiosPlantilla()`
Compara colores actuales con la plantilla original:
- Devuelve `true` si hubo cambios
- Devuelve `false` si todo está igual

### `guardarColores()` - Mejorado
Nueva lógica:
```javascript
if (detectarCambiosPlantilla() && plantillaOriginal !== 'custom') {
    // Preguntar si desea crear plantilla personalizada
    const crear = confirm(`Has modificado la plantilla ${PLANTILLAS[plantillaOriginal].nombre}. 
    ¿Deseas guardar como nueva plantilla personalizada?`);
    
    if (crear) {
        const nombre = prompt('Nombre de la nueva plantilla:', 
                              `${PLANTILLAS[plantillaOriginal].nombre} Personalizado`);
        // Guardar con nombre personalizado
    }
}
```

## 🎯 Elementos de Preview Añadidos

### Grid con Encabezado
```html
<div class="grid-header-preview">
    <i class="fas fa-database"></i> Encabezado del Grid
</div>
```
- Color: `color_grid_header`
- Texto: `color_header_text`

### Notificaciones (4 tipos)
```html
<div class="notif-preview" id="notif-success">
    <i class="fas fa-check-circle"></i> Operación exitosa
</div>
```
- Success: `color_success`
- Warning: `color_warning`
- Danger: `color_danger`
- Info: `color_info`

### Tabla Extendida
```html
<thead>
    <tr>
        <th><i class="fas fa-box"></i> Producto</th>
        <th><i class="fas fa-euro-sign"></i> Precio</th>
        <th><i class="fas fa-warehouse"></i> Stock</th>
    </tr>
</thead>
```
- Header: `color_grid_header`
- Texto header: `color_header_text`
- Cuerpo: `color_app_bg`
- Texto cuerpo: `color_grid_text`

### Galería de Iconos
```html
<div class="icon-preview">
    <i class="fas fa-home"></i>
    <i class="fas fa-user"></i>
    <i class="fas fa-cog"></i>
    ...
</div>
```
- Color: `color_icon`

### Modal con Botones
```html
<div class="modal-preview">
    <div class="modal-preview-header">...</div>
    <div>
        <button class="modal-btn-confirm">Confirmar</button>
        <button class="modal-btn-cancel">Cancelar</button>
    </div>
</div>
```
- Header: `color_grid_header`
- Botón confirmar: `color_success`
- Botón cancelar: `color_danger`

## 📱 Estructura de Acordeón

### HTML
```html
<div class="accordion-section">
    <div class="accordion-header" onclick="toggleAccordion(this)">
        <span><i class="fas fa-palette"></i> Colores Principales</span>
        <i class="fas fa-chevron-down"></i>
    </div>
    <div class="accordion-content">
        <!-- Contenido aquí -->
    </div>
</div>
```

### CSS
```css
.accordion-section {
    border: 1px solid #ddd;
    border-radius: 8px;
    margin-bottom: 1rem;
    overflow: hidden;
}

.accordion-header {
    background: #f8f9fa;
    padding: 1rem;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.accordion-header:hover {
    background: #e9ecef;
}

.accordion-content {
    max-height: 0;
    overflow: hidden;
    transition: max-height 0.3s ease;
}

.accordion-section.active .accordion-content {
    padding: 1rem;
}
```

## 🚀 Cómo Usar

### Para el Usuario:
1. Entrar al editor de colores
2. Ver la plantilla actualmente activa en el sidebar
3. Seleccionar una nueva plantilla O personalizar colores
4. Ver cambios en tiempo real en el preview
5. Al guardar:
   - Si hay cambios → opción de crear plantilla personalizada
   - Si no hay cambios → guardar normalmente

### Para el Desarrollador:
1. Las plantillas están en `PLANTILLAS` object
2. Para añadir nueva plantilla:
   ```javascript
   PLANTILLAS.nueva = {
       nombre: 'Nombre',
       desc: 'Descripción',
       icon: '🎯',
       // ... todos los colores
   };
   ```
3. Para modificar lógica de guardado, ver función `guardarColores()`

## ✅ Estado de Implementación

- [x] Plantilla Dark Mode añadida
- [x] Plantilla Cyber eliminada
- [ ] Acordeones funcionales (pendiente CSS)
- [ ] Detección de plantilla activa (pendiente lógica)
- [ ] Elementos extendidos de preview (pendiente HTML)
- [ ] Lógica de guardado inteligente (pendiente)
- [ ] Columna `plantilla_personalizada` en BD (pendiente)

## 📝 Próximos Pasos

1. Actualizar CSS con estilos de acordeón
2. Implementar funciones de detección de cambios
3. Actualizar lógica de guardado
4. Añadir columna en base de datos
5. Actualizar HTML con nuevos elementos de preview
6. Testing completo

---

Fecha: 26 Oct 2025
Versión: 2.0 (En desarrollo)
Estado: 🚧 Parcialmente implementado

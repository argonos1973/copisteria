# Plantillas de Colores

Este directorio contiene las plantillas de colores en formato JSON para la aplicación.

## 📁 Estructura

```
/static/plantillas/
├── README.md          ← Este archivo
├── minimal.json       ← Plantilla Minimal Monocromático
├── zen.json          ← Plantilla Zen
└── [nueva].json      ← Añadir aquí nuevas plantillas
```

## 🎨 Plantillas Disponibles

### 1. Minimal Monocromático (`minimal.json`)
- **Estilo:** Negro puro, grises oscuros, alto contraste
- **Uso:** Aplicaciones corporativas, dashboards
- **Colores clave:**
  - Primario: #000000 (negro)
  - Header: #ffffff (blanco)
  - Texto header: #000000 (negro)

### 2. Zen (`zen.json`)
- **Estilo:** Ultra minimalista, gris suave, sereno
- **Uso:** Aplicaciones de productividad, bienestar
- **Colores clave:**
  - Primario: #111111 (casi negro)
  - Header: #ffffff (blanco)
  - Texto header: #111111 (gris oscuro)

## ➕ Añadir Nueva Plantilla

### Paso 1: Crear archivo JSON

Crea un nuevo archivo `mi_plantilla.json` en este directorio:

```json
{
  "nombre": "Mi Plantilla",
  "descripcion": "Descripción breve",
  "color_primario": "#xxxxxx",
  "color_secundario": "#xxxxxx",
  "color_success": "#xxxxxx",
  "color_warning": "#xxxxxx",
  "color_danger": "#xxxxxx",
  "color_info": "#xxxxxx",
  "color_button": "#xxxxxx",
  "color_button_hover": "#xxxxxx",
  "color_button_text": "#xxxxxx",
  "color_app_bg": "#xxxxxx",
  "color_header_bg": "#xxxxxx",
  "color_header_text": "#xxxxxx",
  "color_grid_header": "#xxxxxx",
  "color_grid_hover": "rgba(x,x,x,0.x)",
  "color_input_bg": "#xxxxxx",
  "color_input_text": "#xxxxxx",
  "color_input_border": "#xxxxxx",
  "color_select_bg": "#xxxxxx",
  "color_select_text": "#xxxxxx",
  "color_select_border": "#xxxxxx",
  "color_disabled_bg": "#xxxxxx",
  "color_disabled_text": "#xxxxxx",
  "color_submenu_bg": "#xxxxxx",
  "color_submenu_text": "#xxxxxx",
  "color_submenu_hover": "#xxxxxx",
  "color_grid_bg": "#xxxxxx",
  "color_grid_text": "#xxxxxx",
  "color_icon": "#xxxxxx",
  "color_modal_bg": "#xxxxxx",
  "color_modal_text": "#xxxxxx",
  "color_modal_border": "#xxxxxx",
  "color_modal_overlay": "rgba(x,x,x,0.x)",
  "color_modal_shadow": "rgba(x,x,x,0.x)",
  "color_spinner_border": "#xxxxxx"
}
```

### Paso 2: Registrar en plantillas.js

Edita `/static/plantillas.js` y añade tu plantilla:

```javascript
const plantillasDisponibles = ['minimal', 'zen', 'mi_plantilla'];
```

### Paso 3: Añadir botón (opcional)

Si quieres un botón en la UI, edita `/static/admin.js` línea ~1196 y añade:

```html
<button type="button" data-plantilla="mi_plantilla" 
        onclick="aplicarPlantillaConPreview('mi_plantilla', 'edit_'); marcarPlantillaActiva('mi_plantilla');" 
        style="padding: 20px; border: 3px solid #xxx; ...">
    <i class="fas fa-icon"></i> Mi Plantilla<br>
    <small>Descripción corta</small>
</button>
```

## 🔄 Carga de Plantillas

Las plantillas se cargan automáticamente al iniciar la página:

1. **ADMIN_PERMISOS.html** carga `plantillas.js`
2. **plantillas.js** hace fetch de todos los JSON
3. **admin.js** usa `window.plantillasColores`

## 🛠️ Propiedades de Color

| Propiedad | Descripción | Ejemplo |
|-----------|-------------|---------|
| `color_primario` | Color principal de la app | Botones, bordes |
| `color_secundario` | Color secundario | Fondos alternos |
| `color_success` | Notificaciones exitosas | Verde |
| `color_warning` | Advertencias | Naranja |
| `color_danger` | Errores | Rojo |
| `color_info` | Información | Azul |
| `color_button` | Fondo de botones | - |
| `color_button_hover` | Hover de botones | - |
| `color_button_text` | Texto de botones | - |
| `color_app_bg` | Fondo de la app | Generalmente blanco |
| `color_header_bg` | Fondo del menú | Igual a app_bg para minimalismo |
| `color_header_text` | Texto del menú | Negro para visibilidad |
| `color_grid_header` | Cabecera de tablas | - |
| `color_grid_hover` | Hover en filas | rgba() con transparencia |
| `color_input_bg` | Fondo de inputs | - |
| `color_input_text` | Texto de inputs | - |
| `color_input_border` | Borde de inputs | - |
| `color_select_bg` | Fondo de selects | - |
| `color_select_text` | Texto de selects | - |
| `color_select_border` | Borde de selects | - |
| `color_disabled_bg` | Fondo deshabilitado | - |
| `color_disabled_text` | Texto deshabilitado | - |
| `color_submenu_bg` | Fondo de submenús | Igual a app_bg |
| `color_submenu_text` | Texto de submenús | Negro |
| `color_submenu_hover` | Hover en submenús | Gris claro |
| `color_grid_bg` | Fondo de grids | - |
| `color_grid_text` | Texto de grids | - |
| `color_icon` | Color de iconos | - |
| `color_modal_bg` | Fondo de modales | Blanco |
| `color_modal_text` | Texto de modales | Negro/gris oscuro |
| `color_modal_border` | Borde de modales | Negro/gris claro |
| `color_modal_overlay` | Fondo overlay de modales | rgba() con transparencia |
| `color_modal_shadow` | Sombra de modales | rgba() con transparencia |
| `color_spinner_border` | Borde del spinner de carga | Gris |

## 📝 Notas

- Todos los colores deben estar en formato hexadecimal (#xxxxxx)
- Los colores rgba() se usan para transparencias
- Para diseño minimalista: header_bg = app_bg (mismo color)
- Para diseño minimalista: header_text = negro/gris oscuro
- Total de propiedades: **37** (actualizado: 25 Oct 2025)

## 🔍 Validación

Antes de añadir una plantilla, verifica:
- ✅ Archivo JSON válido
- ✅ Todas las 37 propiedades presentes
- ✅ Colores en formato correcto
- ✅ Nombre único (sin duplicados)

## 🐛 Troubleshooting

**Plantilla no aparece:**
1. Verifica que el JSON es válido
2. Verifica que está en `plantillasDisponibles[]`
3. Revisa la consola del navegador

**Colores no se aplican:**
1. Verifica nombres de propiedades (con guiones bajos)
2. Limpia cache (Ctrl+Shift+R)
3. Verifica permisos del archivo (644)

---

**Fecha de creación:** 25 Oct 2025  
**Autor:** Sistema de Plantillas Dinámicas  
**Versión:** 1.0

# ✅ Editor de Colores V2 - Implementación Completada Parcialmente

## Estado Actual: 70% Completado

### ✅ Completado:

1. **Base de Datos**
   - ✅ Columna `plantilla_personalizada` añadida a tabla `empresas`

2. **Plantillas**
   - ✅ Dark Mode añadido (🌙)
   - ✅ Cyber eliminado
   - ✅ Glassmorphism icono cambiado a 💎

3. **CSS**
   - ✅ Archivo `editor_colores_v2.css` creado
   - ✅ Estilos para acordeones
   - ✅ Estilos para preview mejorado
   - ✅ Estados visuales de plantilla activa/personalizada

4. **JavaScript (Parcial)**
   - ✅ Funciones de detección de plantilla activa
   - ✅ Renderizado de sidebar con indicador
   - ✅ Acordeones funcionales
   - ✅ Preview mejorado (parcial)

### 🚧 Pendiente (30%):

1. **JavaScript - Función `guardarColores()` Inteligente**
   ```javascript
   async function guardarColores() {
       const huboChange = detectarCambiosPlantilla();
       
       if (huboChange && plantillaOriginal !== 'custom') {
           const crear = confirm(`Has modificado la plantilla ${PLANTILLAS[plantillaOriginal].nombre}.\n¿Deseas guardar como plantilla personalizada?`);
           
           if (crear) {
               const nombre = prompt('Nombre:', `${PLANTILLAS[plantillaOriginal].nombre} Personalizado`);
               // Guardar con plantilla_personalizada = nombre
           }
       }
       
       // Guardar colores normalmente
   }
   ```

2. **JavaScript - Función `detectarCambiosPlantilla()`**
   ```javascript
   function detectarCambiosPlantilla() {
       if (plantillaOriginal === 'custom') return false;
       
       const plantilla = PLANTILLAS[plantillaOriginal];
       const campos = Object.keys(plantilla).filter(k => k.startsWith('color_'));
       
       return campos.some(campo => {
           const input = document.getElementById(campo);
           return input && input.value !== plantilla[campo];
       });
   }
   ```

3. **HTML - Actualizar referencias**
   ```html
   <!-- Cambiar en EDITAR_EMPRESA_COLORES.html -->
   <link rel="stylesheet" href="/static/editor_colores_v2.css">
   <script src="/static/editor_colores_v2.js"></script>
   ```

## 🚀 Cómo Completar la Implementación

### Opción A: Usar archivos v2 creados

```bash
cd /var/www/html

# 1. Copiar CSS v2 sobre el original
sudo cp static/editor_colores_v2.css static/editor_colores.css

# 2. Completar el JavaScript (añadir funciones pendientes al final)
sudo nano static/editor_colores.js
```

Añadir al final de `editor_colores.js`:

```javascript
function detectarCambiosPlantilla() {
    if (plantillaOriginal === 'custom') return false;
    
    const plantilla = PLANTILLAS[plantillaOriginal];
    const campos = Object.keys(plantilla).filter(k => k.startsWith('color_'));
    
    return campos.some(campo => {
        const input = document.getElementById(campo);
        return input && input.value !== plantilla[campo];
    });
}

async function guardarColores() {
    try {
        const huboChange = detectarCambiosPlantilla();
        let nombrePersonalizado = null;
        
        if (huboChange && plantillaOriginal !== 'custom') {
            const crear = confirm(`Has modificado los colores de la plantilla "${PLANTILLAS[plantillaOriginal].nombre}".\n\n¿Deseas guardar como plantilla personalizada?`);
            
            if (crear) {
                nombrePersonalizado = prompt(
                    'Nombre para la plantilla personalizada:', 
                    `${PLANTILLAS[plantillaOriginal].nombre} Personalizado`
                );
                
                if (!nombrePersonalizado) {
                    return; // Cancelado
                }
            }
        }
        
        const colores = {
            color_app_bg: document.getElementById('color_app_bg').value,
            color_primario: document.getElementById('color_primario').value,
            color_secundario: document.getElementById('color_secundario').value,
            color_header_text: document.getElementById('color_header_text').value,
            color_header_bg: document.getElementById('color_header_bg').value,
            color_button: document.getElementById('color_button').value,
            color_button_hover: document.getElementById('color_button_hover').value,
            color_button_text: document.getElementById('color_button_text').value,
            color_success: document.getElementById('color_success').value,
            color_warning: document.getElementById('color_warning').value,
            color_danger: document.getElementById('color_danger').value,
            color_info: document.getElementById('color_info').value,
            color_grid_header: document.getElementById('color_grid_header').value,
            color_grid_text: document.getElementById('color_grid_text').value,
            color_icon: document.getElementById('color_icon').value,
            plantilla_personalizada: nombrePersonalizado
        };
        
        const response = await fetch(`${API_URL}/empresas/${empresaId}/colores`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(colores)
        });
        
        if (response.ok) {
            alert('✅ Colores guardados correctamente');
            if (nombrePersonalizado) {
                plantillaActual = 'custom';
                plantillaOriginal = 'custom';
                actualizarPlantillaActiva('custom', nombrePersonalizado);
            }
        } else {
            alert('❌ Error al guardar colores');
        }
        
    } catch (error) {
        console.error('Error:', error);
        alert('❌ Error al guardar');
    }
}
```

### Opción B: Reiniciar Apache y Probar

```bash
sudo systemctl restart apache2
```

Luego ir a: `http://localhost:5001/frontend/EDITAR_EMPRESA_COLORES.html?id=1`

## 📋 Checklist de Verificación

- [ ] CSS v2 con acordeones se carga
- [ ] Plantilla Dark Mode aparece
- [ ] Plantilla Cyber NO aparece
- [ ] Al entrar, muestra plantilla activa
- [ ] Acordeones se expanden/contraen
- [ ] Preview actualiza en tiempo real
- [ ] Detección de cambios funciona
- [ ] Al guardar, pregunta si crear personalizada
- [ ] Guarda correctamente en BD

## 🎯 Testing Rápido

1. Entrar al editor
2. Seleccionar "Minimal"
3. Cambiar un color
4. Guardar
5. Verificar mensaje de plantilla personalizada

---

Fecha: 26 Oct 2025, 18:00
Estado: 70% - Funcional con funciones manuales pendientes

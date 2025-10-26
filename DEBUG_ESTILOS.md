# 🔍 Guía de Debugging de Estilos

## Sistema Mejorado - Versión 2.0

### ✨ Mejoras Implementadas

1. **auto_branding.js v2.0**
   - Logs detallados en consola
   - Cache deshabilitado (`cache: 'no-cache'`)
   - Credentials incluidas (`credentials: 'include'`)
   - Resumen completo de estilos aplicados

2. **Versionado forzado**
   - Todas las páginas usan `?v=2` para forzar recarga
   - 26 páginas HTML actualizadas

3. **Logs mejorados**
   - Muestra URL actual
   - Muestra colores recibidos
   - Muestra resumen de aplicación
   - Muestra errores detallados

---

## 🧪 Cómo Verificar que Funciona

### Paso 1: Limpiar Caché Completamente

**Opción A (Recomendado):**
```
1. Presiona F12 para abrir DevTools
2. Clic derecho en el botón de recarga
3. Selecciona "Vaciar caché y recargar de manera forzada"
```

**Opción B:**
```
Ctrl + Shift + Delete
→ Selecciona "Todo el tiempo"
→ Marca "Imágenes y archivos en caché"
→ Borrar datos
```

**Opción C:**
```
Cerrar sesión → Cerrar navegador → Abrir navegador → Login
```

---

### Paso 2: Abrir Consola del Navegador

```
F12 o Ctrl + Shift + I
→ Tab "Console"
```

---

### Paso 3: Navegar y Verificar Logs

Deberías ver en CADA página que cargues:

```
[AUTO-BRANDING v2.0] 🎨 Iniciando carga de estilos...
[AUTO-BRANDING] URL actual: http://localhost:5001/estadisticas.html
[AUTO-BRANDING] 📦 Branding recibido: {colores: {...}, datos: {...}}
[AUTO-BRANDING] 🎨 Colores a aplicar: {primario: "#ffffff", ...}
[AUTO-BRANDING] ✅ Estilos aplicados correctamente
[AUTO-BRANDING] 📋 Resumen de estilos aplicados:
  • Menú lateral (primario): #ffffff
  • Texto menú: #000000
  • Tarjetas (secundario): #f5f5f5
  • Texto tarjetas: #000000
  • Botones: #000000 → Texto: #ffffff
  • Iconos: #000000
[AUTO-BRANDING] ✨ Página lista con branding aplicado
```

---

### Paso 4: Si NO Ves los Logs

#### Problema 1: Script no se carga

**Verificar en tab "Network" de DevTools:**
```
Busca: auto_branding.js?v=2
Status: debe ser 200
Si es 404 → El archivo no existe
Si es 304 → Está en caché (usar Ctrl+Shift+R)
```

**Solución:**
```bash
ls -la /var/www/html/static/auto_branding.js
# Debe existir y tener permisos de lectura
```

#### Problema 2: Error de Sesión

**Si ves:**
```
[AUTO-BRANDING] ⚠️ No se pudo cargar branding: 401
```

**Significa:** No hay sesión activa

**Solución:**
```
1. Cerrar sesión
2. Login nuevamente
3. Recargar página
```

#### Problema 3: Sin Colores en Respuesta

**Si ves:**
```
[AUTO-BRANDING] ⚠️ Sin colores personalizados en respuesta
```

**Verificar en base de datos:**
```bash
sqlite3 /var/www/html/db/usuarios_sistema.db \
  "SELECT color_primario, color_header_text FROM empresas WHERE codigo = 'copisteria'"
```

**Debe mostrar:**
```
#ffffff|#000000
```

---

## 🔧 Soluciones Rápidas

### Estilos se pierden al navegar

**Causa:** Cache del navegador
**Solución:**
```
Ctrl + Shift + R en cada página
o
Cerrar completamente el navegador y volver a abrir
```

### Menú lateral no tiene color correcto

**Verificar en consola:**
```
Busca: "Menú lateral (primario):"
Debe mostrar el color esperado
```

**Si el color es incorrecto:**
```bash
# Actualizar en BD
sqlite3 /var/www/html/db/usuarios_sistema.db \
  "UPDATE empresas SET color_primario = '#ffffff', color_header_text = '#000000' WHERE codigo = 'copisteria'"

# Reiniciar Apache
sudo systemctl restart apache2

# Limpiar sesión en navegador (Cerrar sesión y volver a entrar)
```

### Texto invisible en tarjetas

**Verificar en consola:**
```
Busca: "Texto tarjetas:"
Debe ser un color con buen contraste respecto a secundario
```

**Si es incorrecto:**
```bash
sqlite3 /var/www/html/db/usuarios_sistema.db \
  "UPDATE empresas SET color_grid_text = '#000000' WHERE codigo = 'copisteria'"
```

---

## 📊 Tabla de Colores Plantilla Minimal

| Elemento | Variable | Valor | Uso |
|----------|----------|-------|-----|
| Menú lateral | `color_primario` | `#ffffff` | Fondo sidebar |
| Texto menú | `color_header_text` | `#000000` | Texto e iconos menú |
| Tarjetas | `color_secundario` | `#f5f5f5` | Fondo cards |
| Texto tarjetas | `color_grid_text` | `#000000` | Texto en cards |
| Botones | `color_button` | `#000000` | Fondo botones |
| Texto botones | calculado | `#ffffff` | Auto según luminancia |
| Iconos | `color_icon` | `#000000` | Color de iconos |

---

## 🆘 Si Nada Funciona

### Reset Completo

```bash
# 1. Actualizar colores en BD
sqlite3 /var/www/html/db/usuarios_sistema.db <<EOF
UPDATE empresas SET 
  color_primario = '#ffffff',
  color_header_text = '#000000',
  color_secundario = '#f5f5f5',
  color_grid_text = '#000000',
  color_icon = '#000000',
  color_button = '#000000',
  color_app_bg = '#ffffff',
  color_header_bg = '#ffffff'
WHERE codigo = 'copisteria';
EOF

# 2. Reiniciar Apache
sudo systemctl restart apache2

# 3. En el navegador
# - Cerrar todas las pestañas
# - Cerrar el navegador completamente
# - Abrir navegador
# - Ir a http://localhost:5001
# - Login
# - Abrir DevTools (F12)
# - Ver consola mientras navegas
```

---

## ✅ Checklist de Verificación

- [ ] auto_branding.js?v=2 se carga en Network (200 OK)
- [ ] Logs aparecen en consola al cargar página
- [ ] Logs muestran colores correctos (#ffffff para primario)
- [ ] Menú lateral es blanco con texto negro
- [ ] Tarjetas son gris claro con texto negro
- [ ] Al navegar, los logs aparecen nuevamente
- [ ] Al navegar, los estilos se mantienen
- [ ] No hay errores en consola

---

## 📞 Información de Depuración para Reportar

Si el problema persiste, proporciona:

1. **Captura de la consola completa** (F12 → Console → Screenshot)
2. **Network tab** filtrando por "auto_branding"
3. **Colores en BD:**
   ```bash
   sqlite3 /var/www/html/db/usuarios_sistema.db \
     "SELECT * FROM empresas WHERE codigo = 'copisteria'"
   ```
4. **Versión del script:**
   ```bash
   head -5 /var/www/html/static/auto_branding.js
   ```

---

Fecha: 26 Oct 2025, 17:16
Versión: auto_branding.js v2.0
Estado: ✅ Desplegado

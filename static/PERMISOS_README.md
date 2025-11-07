# Sistema de Permisos - Guía de Uso

## 📋 Descripción

Sistema automático de control de permisos por módulo y acción. Los permisos se cargan automáticamente desde el backend y se aplican a toda la aplicación.

## 🎯 Módulos Disponibles

- `facturas` - Facturas
- `facturas_emitidas` - Facturas Emitidas  
- `tickets` - Tickets
- `productos` - Productos
- `contactos` - Contactos
- `presupuestos` - Presupuestos
- `proformas` - Proformas
- `banco` - Banco
- `gastos` - Gastos

## 🔐 Acciones Disponibles

- `ver` - Ver/Consultar registros
- `crear` - Crear nuevos registros
- `editar` - Modificar registros existentes
- `eliminar` - Eliminar registros
- `anular` - Anular documentos
- `exportar` - Exportar datos

---

## 📌 Uso en HTML

### 1. Ocultar elementos sin permiso

```html
<!-- Botón de crear solo visible si tiene permiso -->
<button 
    data-modulo="facturas" 
    data-accion="crear"
    class="btn btn-primary">
    <i class="fas fa-plus"></i> Nueva Factura
</button>

<!-- Botón de eliminar solo visible si tiene permiso -->
<button 
    data-modulo="productos" 
    data-accion="eliminar"
    class="btn btn-danger">
    <i class="fas fa-trash"></i> Eliminar
</button>
```

### 2. Deshabilitar en lugar de ocultar

```html
<!-- Botón deshabilitado si no tiene permiso (visible pero no clickeable) -->
<button 
    data-modulo="contactos" 
    data-accion="editar"
    data-permiso-modo="deshabilitar"
    class="btn btn-primary">
    <i class="fas fa-edit"></i> Editar
</button>
```

---

## 📌 Uso en JavaScript

### 1. Verificar permiso simple

```javascript
// Verificar si tiene permiso antes de hacer algo
if (tienePermiso('facturas', 'crear')) {
    mostrarModalCrearFactura();
} else {
    alert('No tienes permisos para crear facturas');
}
```

### 2. Verificar con alerta automática

```javascript
// Verificar y mostrar alerta si no tiene permiso
function eliminarProducto(id) {
    if (!verificarPermisoConAlerta('productos', 'eliminar')) {
        return; // Sale si no tiene permiso
    }
    
    // Continúa con la eliminación...
    if (confirm('¿Eliminar producto?')) {
        // ...
    }
}
```

### 3. Crear botones dinámicamente

```javascript
// Crear botón solo si tiene permiso
const boton = crearBotonConPermiso({
    texto: 'Nuevo Ticket',
    icono: 'fas fa-plus',
    modulo: 'tickets',
    accion: 'crear',
    clase: 'btn btn-primary',
    onclick: () => abrirModalNuevoTicket()
});

if (boton) {
    document.getElementById('acciones').appendChild(boton);
}
```

### 4. Obtener todos los permisos de un módulo

```javascript
const permisosFacturas = obtenerPermisosModulo('facturas');

console.log(permisosFacturas);
// {
//     ver: 1,
//     crear: 1,
//     editar: 0,
//     eliminar: 0,
//     anular: 1,
//     exportar: 1
// }
```

### 5. Verificar múltiples permisos

```javascript
// Verificar que tenga TODOS los permisos
if (tienePermisosMultiples('productos', ['crear', 'editar'])) {
    // Tiene ambos permisos
    habilitarEdicionCompleta();
}
```

### 6. Renderizar tabla con botones según permisos

```javascript
function renderizarTablaProductos(productos) {
    let html = '<table><tbody>';
    
    productos.forEach(prod => {
        html += `<tr>
            <td>${prod.nombre}</td>
            <td>${prod.precio}</td>
            <td class="acciones">`;
        
        // Botón editar solo si tiene permiso
        if (tienePermiso('productos', 'editar')) {
            html += `<button onclick="editarProducto(${prod.id})">
                <i class="fas fa-edit"></i>
            </button>`;
        }
        
        // Botón eliminar solo si tiene permiso
        if (tienePermiso('productos', 'eliminar')) {
            html += `<button onclick="eliminarProducto(${prod.id})">
                <i class="fas fa-trash"></i>
            </button>`;
        }
        
        html += `</td></tr>`;
    });
    
    html += '</tbody></table>';
    document.getElementById('tabla').innerHTML = html;
}
```

---

## 🔄 Aplicar permisos después de cargar contenido dinámico

```javascript
async function cargarContenidoDinamico() {
    const response = await fetch('/api/datos');
    const datos = await response.json();
    
    // Renderizar contenido
    renderizarContenido(datos);
    
    // RE-APLICAR permisos a los nuevos elementos
    aplicarPermisosAElementos();
}
```

---

## ⚙️ Funciones Disponibles

### `tienePermiso(modulo, accion)`
Verifica si el usuario tiene un permiso específico.
- **Returns**: `boolean`

### `verificarPermisoConAlerta(modulo, accion)`
Verifica permiso y muestra alerta si no tiene acceso.
- **Returns**: `boolean`

### `obtenerPermisosModulo(modulo)`
Obtiene todos los permisos de un módulo.
- **Returns**: `object | null`

### `tienePermisosMultiples(modulo, acciones)`
Verifica si tiene TODOS los permisos especificados.
- **Returns**: `boolean`

### `crearBotonConPermiso(config)`
Crea un botón HTML solo si tiene el permiso.
- **Returns**: `HTMLElement | null`

### `aplicarPermisosAElementos()`
Re-aplica permisos a todos los elementos con `data-modulo` y `data-accion`.

---

## 🚀 Ejemplo Completo

```html
<!-- consulta_productos.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Productos</title>
</head>
<body>
    <div class="header-acciones">
        <!-- Se oculta si no tiene permiso de crear -->
        <button 
            data-modulo="productos" 
            data-accion="crear"
            onclick="nuevoProducto()"
            class="btn btn-primary">
            <i class="fas fa-plus"></i> Nuevo Producto
        </button>
        
        <!-- Se oculta si no tiene permiso de exportar -->
        <button 
            data-modulo="productos" 
            data-accion="exportar"
            onclick="exportarProductos()"
            class="btn btn-success">
            <i class="fas fa-file-excel"></i> Exportar
        </button>
    </div>
    
    <div id="tabla-productos"></div>
    
    <script>
        function nuevoProducto() {
            // Ya sabemos que tiene permiso (botón solo visible si tiene)
            abrirModalNuevo();
        }
        
        function editarProducto(id) {
            // Verificar por seguridad en el código
            if (!verificarPermisoConAlerta('productos', 'editar')) {
                return;
            }
            abrirModalEditar(id);
        }
        
        async function cargarProductos() {
            const response = await fetch('/api/productos');
            const productos = await response.json();
            
            let html = '<table>';
            productos.forEach(p => {
                html += `<tr>
                    <td>${p.nombre}</td>
                    <td>
                        <button 
                            data-modulo="productos" 
                            data-accion="editar"
                            onclick="editarProducto(${p.id})">
                            Editar
                        </button>
                        <button 
                            data-modulo="productos" 
                            data-accion="eliminar"
                            onclick="eliminarProducto(${p.id})">
                            Eliminar
                        </button>
                    </td>
                </tr>`;
            });
            html += '</table>';
            
            document.getElementById('tabla-productos').innerHTML = html;
            
            // Re-aplicar permisos después de renderizar
            aplicarPermisosAElementos();
        }
        
        // Cargar al iniciar
        cargarProductos();
    </script>
</body>
</html>
```

---

## ⚠️ Importante

1. **Los permisos se cargan automáticamente** al cargar la página
2. **No olvides llamar `aplicarPermisosAElementos()`** después de cargar contenido dinámico
3. **El backend debe validar** - el frontend solo oculta elementos, pero el backend debe validar permisos también
4. **Usa atributos `data-modulo` y `data-accion`** para control automático
5. **Los permisos están en `window.usuarioPermisos`** - accesibles desde cualquier script

---

## 🐛 Debugging

```javascript
// Ver permisos cargados
console.log(window.usuarioPermisos);

// Verificar permiso específico en consola
console.log('¿Puede crear facturas?', tienePermiso('facturas', 'crear'));

// Ver todos los permisos de un módulo
console.log('Permisos de productos:', obtenerPermisosModulo('productos'));
```

---

**Fecha**: 2025-11-07  
**Sistema**: Aleph70 Multiempresa  
**Versión**: 1.0

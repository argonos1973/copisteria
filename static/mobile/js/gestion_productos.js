let productoId = null;

document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    if(params.has('id')) {
        productoId = params.get('id');
        cargarProducto(productoId);
    }
});

async function cargarProducto(id) {
    try {
        const res = await fetch(`/api/productos/${id}`);
        if(!res.ok) throw new Error('Error al cargar');
        const data = await res.json();
        
        document.getElementById('page-title').textContent = 'Editar Producto';
        document.getElementById('nombre').value = data.nombre || '';
        document.getElementById('referencia').value = data.referencia || '';
        document.getElementById('precio_venta').value = data.precio_venta || '';
        document.getElementById('iva').value = data.iva || '21';
        document.getElementById('descripcion').value = data.descripcion || '';
    } catch(e) {
        console.error(e);
        alert('Error cargando producto');
    }
}

async function guardarProducto() {
    const payload = {
        nombre: document.getElementById('nombre').value,
        referencia: document.getElementById('referencia').value,
        precio_venta: parseFloat(document.getElementById('precio_venta').value) || 0,
        iva: parseFloat(document.getElementById('iva').value) || 21,
        descripcion: document.getElementById('descripcion').value
    };
    
    if(!payload.nombre) return alert('Nombre requerido');

    const url = productoId ?(`/api/productos/${productoId}`) : '/api/productos';
    const method = productoId ? 'PUT' : 'POST';
    
    try {
        const res = await fetch(url, {
            method: method,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        
        if(!res.ok) {
            const err = await res.json();
            throw new Error(err.error || 'Error al guardar');
        }
        
        alert('Producto guardado');
        window.location.href = '/api/auth/mobile/productos';
        
    } catch(e) {
        console.error(e);
        alert('Error: ' + e.message);
    }
}

window.guardarProducto = guardarProducto;

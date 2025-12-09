let contactoId = null;

document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    if(params.has('id')) {
        contactoId = params.get('id');
        cargarContacto(contactoId);
    }
});

async function cargarContacto(id) {
    try {
        const res = await fetch(`/api/contactos/${id}`);
        if(!res.ok) throw new Error('Error al cargar');
        const data = await res.json();
        
        document.getElementById('page-title').textContent = 'Editar Contacto';
        document.getElementById('razonsocial').value = data.razonsocial || data.nombre || '';
        document.getElementById('identificador').value = data.identificador || data.nif || '';
        document.getElementById('email').value = data.mail || data.email || '';
        document.getElementById('telefono').value = data.telefono || '';
        document.getElementById('direccion').value = data.direccion || '';
        document.getElementById('cp').value = data.cp || '';
        document.getElementById('localidad').value = data.localidad || '';
        document.getElementById('provincia').value = data.provincia || '';
    } catch(e) {
        console.error(e);
        alert('Error cargando contacto');
    }
}

async function guardarContacto() {
    const payload = {
        razonsocial: document.getElementById('razonsocial').value,
        identificador: document.getElementById('identificador').value,
        mail: document.getElementById('email').value,
        telefono: document.getElementById('telefono').value,
        direccion: document.getElementById('direccion').value,
        cp: document.getElementById('cp').value,
        localidad: document.getElementById('localidad').value,
        provincia: document.getElementById('provincia').value
    };
    
    if(!payload.razonsocial) return alert('Nombre requerido');

    const url = contactoId ?(`/api/contactos/${contactoId}`) : '/api/contactos';
    const method = contactoId ? 'PUT' : 'POST';
    
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
        
        alert('Contacto guardado');
        window.location.href = '/api/auth/mobile/contactos';
        
    } catch(e) {
        console.error(e);
        alert('Error: ' + e.message);
    }
}

window.guardarContacto = guardarContacto;

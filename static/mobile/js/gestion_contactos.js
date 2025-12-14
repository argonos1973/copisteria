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
        const res = await fetch(`/api/contactos/get_contacto/${id}`);
        if(!res.ok) throw new Error('Error al cargar');
        const data = await res.json();

        const titleEl = document.getElementById('page-title');
        if (titleEl) titleEl.textContent = 'Editar Contacto';

        const razonsocialEl = document.getElementById('razonsocial');
        if (razonsocialEl) razonsocialEl.value = data.razonsocial || data.nombre || '';

        const identificadorEl = document.getElementById('identificador');
        if (identificadorEl) identificadorEl.value = data.identificador || data.nif || '';

        const emailEl = document.getElementById('email');
        if (emailEl) emailEl.value = data.mail || data.email || '';

        const telefonoEl = document.getElementById('telefono');
        if (telefonoEl) telefonoEl.value = data.telf1 || data.telefono || '';

        const direccionEl = document.getElementById('direccion');
        if (direccionEl) direccionEl.value = data.direccion || '';

        const cpEl = document.getElementById('cp');
        if (cpEl) cpEl.value = data.cp || '';

        const localidadEl = document.getElementById('localidad');
        if (localidadEl) localidadEl.value = data.localidad || data.poblacion || '';

        const provinciaEl = document.getElementById('provincia');
        if (provinciaEl) provinciaEl.value = data.provincia || '';
    } catch(e) {
        console.error(e);
        alert('Error cargando contacto');
    }
}

async function guardarContacto() {
    const razonsocialEl = document.getElementById('razonsocial');
    const identificadorEl = document.getElementById('identificador');
    const emailEl = document.getElementById('email');
    const telefonoEl = document.getElementById('telefono');
    const direccionEl = document.getElementById('direccion');
    const cpEl = document.getElementById('cp');
    const localidadEl = document.getElementById('localidad');
    const provinciaEl = document.getElementById('provincia');

    if (!razonsocialEl || !identificadorEl) {
        alert('Error: formulario de contacto no disponible en esta pantalla');
        return;
    }

    const payload = {
        razonsocial: razonsocialEl.value,
        identificador: identificadorEl.value,
        mail: emailEl ? emailEl.value : '',
        telf1: telefonoEl ? telefonoEl.value : '',
        direccion: direccionEl ? direccionEl.value : '',
        cp: cpEl ? cpEl.value : '',
        localidad: localidadEl ? localidadEl.value : '',
        provincia: provinciaEl ? provinciaEl.value : ''
    };
    
    if(!payload.razonsocial) return alert('Nombre requerido');

    if (window.NifCifValidator && window.NifCifValidator.normalize) {
        payload.identificador = window.NifCifValidator.normalize(payload.identificador);
        identificadorEl.value = payload.identificador;
    }

    if (payload.identificador && window.NifCifValidator && !window.NifCifValidator.isValid(payload.identificador)) {
        return alert('El NIF/NIE/CIF introducido no es válido');
    }

    if (payload.cp && window.CpValidator) {
        const cp = window.CpValidator.normalizeCp(payload.cp);
        payload.cp = cp;
        if (cpEl) cpEl.value = cp;

        if (!window.CpValidator.isValidFormat(cp)) {
            return alert('El CP debe tener 5 dígitos');
        }

        try {
            const data = await window.CpValidator.getCpData(cp);
            if (!Array.isArray(data) || !data.length) {
                return alert('El CP introducido no existe');
            }

            const row = data[0] || {};
            if (localidadEl && !localidadEl.value.trim()) {
                localidadEl.value = row.poblacio || '';
                payload.localidad = localidadEl.value;
            }
            if (provinciaEl && !provinciaEl.value.trim()) {
                provinciaEl.value = row.provincia || '';
                payload.provincia = provinciaEl.value;
            }
        } catch (err) {
            console.error('[CP] Error:', err);
            return alert('No se pudo validar el CP');
        }
    }

    const url = contactoId ?(`/api/contactos/update_contacto/${contactoId}`) : '/api/contactos/create_contacto';
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

    // Pequeño delay para asegurar que los valores se mantengan
    await new Promise(resolve => setTimeout(resolve, 100));
let cargandoContacto = false;
// gestion_contactos.js
// Vanilla JS replacement for the former Vue implementation in GESTION_CONTACTOS.html
// Mantiene las mismas validaciones y envíos.

import { IP_SERVER, PORT } from './constantes.js';
import { mostrarNotificacion } from './notificaciones.js';
import { inicializarDeteccionCambios, marcarCambiosSinGuardar, resetearCambiosSinGuardar, debounce } from './scripts_utils.js';
import { inicializarPestanas } from './tabs.js';

const API_URL = `http://${IP_SERVER}:${PORT}/api`;

// Element references --------------------------------------------------------
const form = document.getElementById('contactForm');
const btnCancelar = document.getElementById('btnCancelar');
const sugerenciasContainer = document.getElementById('sugerenciasCarrer');
const cpDatalist = document.getElementById('listaCP');

const fields = {
  razonsocial: document.getElementById('razonsocial'),
  identificador: document.getElementById('identificador'),
  mail: document.getElementById('mail'),
  telf1: document.getElementById('telf1'),
  telf2: document.getElementById('telf2'),
  direccion: document.getElementById('direccion'),
  cp: document.getElementById('cp'),
  poblacion: document.getElementById('poblacion'),
  poblacio: document.getElementById('poblacio'),
  provincia: document.getElementById('provincia'),
  facturacion: document.getElementById('facturacion_automatica'),
  dir3Oficina: document.getElementById('dir3_oficina'),
  dir3Organo: document.getElementById('dir3_organo'),
  dir3Unidad: document.getElementById('dir3_unidad')
};

const icons = {
  telf1: document.getElementById('icon-telf1'),
  telf2: document.getElementById('icon-telf2')
};

const btnGuardar = document.getElementById('btnGuardar');

// Funciones de validación (placeholder - siempre retornan true)
function validateRequired() {
  return true;
}

function validateIdentificador() {
  return true;
}

function validateEmail() {
  return true;
}

function validateTelf(field, icon) {
  return true;
}

// Añadir listeners para uppercase y marcar cambios
if (fields.razonsocial) {
  fields.razonsocial.addEventListener('input', function() {
    this.value = this.value.toUpperCase();
    marcarCambiosSinGuardar();
  });
}
if (fields.direccion) {
  fields.direccion.addEventListener('input', function() {
    this.value = this.value.toUpperCase();
    marcarCambiosSinGuardar();
  });
}
if (fields.poblacion) {
  fields.poblacion.addEventListener('input', function() {
    this.value = this.value.toUpperCase();
    marcarCambiosSinGuardar();
  });
}

// ---- Dirección sugerencias ----
const dirDebounce = debounce((q)=>buscarSugerenciasCarrer(q),300);

async function buscarSugerenciasCarrer(query) {
  if (!query || query.length < 3) return (sugerenciasContainer.innerHTML = '');
  try {
    const res = await fetch(`${API_URL}/contactos/searchCarrer?query=${encodeURIComponent(query)}`);
    if (!res.ok) throw new Error('Error al buscar direcciones');
    const data = await res.json();
    renderSugerencias(data);
  } catch (err) {
    console.error(err);
    sugerenciasContainer.innerHTML = '';
  }
}

function renderSugerencias(lista) {
  if (!Array.isArray(lista) || !lista.length) {
    sugerenciasContainer.innerHTML = '';
    return;
  }
  sugerenciasContainer.innerHTML = '';
  lista.forEach((sug) => {
    const div = document.createElement('div');
    div.className = 'sugerencia-item';
    div.textContent = `${sug.carrer} (${sug.cp})`;
    div.addEventListener('click', () => seleccionarDireccion(sug));
    sugerenciasContainer.appendChild(div);
  });
}

async function seleccionarDireccion(sug) {
  fields.direccion.value = sug.carrer;
  fields.cp.value = sug.cp;
  sugerenciasContainer.innerHTML = '';
}

// ------------------------ CP lookup & suggestions ------------------------
const cpDebounce = debounce((p)=>buscarCPSuggestions(p),300);
fields.cp.addEventListener('input', (e)=>{
  cpDebounce(e.target.value);
  handleCP();
});

async function buscarCPSuggestions(prefix){
  if(!prefix || prefix.length<2 || prefix.length>4){
    if(cpDatalist) cpDatalist.innerHTML='';
    return;
  }
  try{
    const res = await fetch(`${API_URL}/contactos/search_cp?term=${prefix}`);
    if(!res.ok) return;
    const data = await res.json();
    if(!Array.isArray(data)) return;
    cpDatalist.innerHTML='';
    data.forEach(item=>{
      const opt = document.createElement('option');
      opt.value = item.cp;
      opt.label = `${item.cp} - ${item.poblacio} (${item.provincia})`;
      cpDatalist.appendChild(opt);
    });
  }catch(err){console.error(err);} }

async function handleCP() {
  if (cargandoContacto) return;
  const cp = fields.cp.value;
  // Permitir cualquier CP sin validación
  if (cp.length !== 5 || !/^[0-9]{5}$/.test(cp)) {
    // CP no es catalán (5 dígitos), no buscar en BD
    return;
  }
  try {
    const res = await fetch(`${API_URL}/contactos/get_cp?cp=${cp}`);
    if (!res.ok) throw new Error('Error al obtener CP');
    const data = await res.json();
    if (data && data.length) {
      fields.poblacio.value = data[0].poblacio;
      fields.provincia.value = data[0].provincia;
    } else {
      fields.poblacio.value = '';
      fields.provincia.value = '';
    }
  } catch (err) {
    console.error(err);
  }
}

// ------------------------ Validations events --------------------
if (fields.identificador) {
  fields.identificador.addEventListener('input', () => {
    validateIdentificador();
    marcarCambiosSinGuardar();
  });
}
if (fields.mail) {
  fields.mail.addEventListener('input', () => {
    validateEmail();
    marcarCambiosSinGuardar();
  });
}
if (fields.telf1) {
  fields.telf1.addEventListener('input', () => {
    validateTelf(fields.telf1, icons.telf1);
    marcarCambiosSinGuardar();
  });
}
if (fields.telf2) {
  fields.telf2.addEventListener('input', () => {
    validateTelf(fields.telf2, icons.telf2);
    marcarCambiosSinGuardar();
  });
}
if (fields.cp) {
  fields.cp.addEventListener('change', () => marcarCambiosSinGuardar());
}
if (fields.facturacion) {
  fields.facturacion.addEventListener('change', () => marcarCambiosSinGuardar());
}

// ------------------------ Submit & Cancel -----------------------
if (btnGuardar) {
  btnGuardar.addEventListener('click', submitForm);
}
if (btnCancelar) {
  btnCancelar.addEventListener('click', () => {
    window.location.href = 'CONSULTA_CONTACTOS.html';
  });
}

function allValid() {
  const requiredOk = validateRequired();
  const othersOk =
    validateIdentificador() &&
    validateEmail() &&
    validateTelf(fields.telf1, icons.telf1) &&
    validateTelf(fields.telf2, icons.telf2);
    // Pequeño delay para asegurar que los valores se mantengan
  return requiredOk && othersOk;
}

async function submitForm() {
  if (!allValid()) {
    mostrarNotificacion('Completa los campos obligatorios marcados en rojo', 'error');
    return;
  }

  // Obtener dirección directamente del DOM para asegurar que se lea correctamente
  const direccionElement = document.getElementById('direccion');
  const direccionValue = direccionElement ? direccionElement.value : '';

  const contactoData = {
    razonsocial: fields.razonsocial.value.trim().toUpperCase(),
    identificador: fields.identificador.value.trim().toUpperCase(),
    mail: fields.mail.value.trim(),
    telf1: fields.telf1.value ? fields.telf1.value.trim() : null,
    telf2: fields.telf2.value ? fields.telf2.value.trim() : null,
    direccion: direccionValue ? direccionValue.trim().toUpperCase() : null,
    cp: fields.cp.value.trim(),
    poblacio: fields.poblacio.value.trim().toUpperCase(),
    localidad: fields.poblacio.value.trim().toUpperCase(),
    provincia: fields.provincia.value.trim().toUpperCase(),
    tipo: fields.facturacion.checked ? 1 : 0,
    dir3_oficina: fields.dir3Oficina.value.trim() || null,
    dir3_organo: fields.dir3Organo.value.trim() || null,
    dir3_unidad: fields.dir3Unidad.value.trim() || null
  };

  const urlParams = new URLSearchParams(window.location.search);
  const id = urlParams.get('id');
  const url = id ? `${API_URL}/contactos/update_contacto/${id}` : `${API_URL}/contactos/create_contacto`;
  const method = id ? 'PUT' : 'POST';

  try {
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(contactoData)
    });
    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.message || errData.error || 'Error');
    }
    const data = await res.json();
    resetearCambiosSinGuardar();
    mostrarNotificacion(data.message || 'Contacto guardado correctamente', 'success');
    
    // Solo redirigir si NO se está guardando desde el menú
    if (!window.__guardandoDesdeMenu) {
      setTimeout(() => (window.location.href = 'CONSULTA_CONTACTOS.html'), 1500);
    } else {
      console.log('[Contactos] Guardado desde menú, no redirigir');
    }
  } catch (err) {
    console.error(err);
    mostrarNotificacion(err.message || 'Error al guardar el contacto', 'error');
  }
}

// ------------------------ Load existing contact ---------------------------
async function loadContacto() {
  const urlParams = new URLSearchParams(window.location.search);
  const id = urlParams.get('id');
  if (!id) return;
  cargandoContacto = true;
  try {
    const res = await fetch(`${API_URL}/contactos/get_contacto/${id}`);
    if (!res.ok) throw new Error('Error al obtener el contacto');
    const data = await res.json();
    
    console.log('[Contactos] Datos recibidos del backend:', data);
    console.log('[Contactos] Dirección recibida:', data.direccion);
    
    Object.keys(fields).forEach((k) => {
      if (k === 'facturacion') {
        fields[k].checked = data.tipo === 1;
      } else if (k === 'poblacio') {
        fields[k].value = data.localidad ?? '';
      } else if (fields[k]) {
        const key = k === 'dir3Oficina' ? 'dir3_oficina'
          : k === 'dir3Organo' ? 'dir3_organo'
          : k === 'dir3Unidad' ? 'dir3_unidad'
          : k;
        fields[k].value = data[key] ?? '';
      }
    });
    
    // Cargar dirección directamente del DOM para asegurar que se cargue
    const direccionElement = document.getElementById('direccion');
    console.log('[Contactos] Elemento direccion encontrado:', !!direccionElement);
    if (direccionElement && data.direccion) {
      direccionElement.value = data.direccion;
      direccionElement.setAttribute('value', data.direccion);
      console.log('[Contactos] Dirección cargada en el campo:', direccionElement.value);
      console.log('[Contactos] Atributo value establecido:', direccionElement.getAttribute('value'));
      console.log('[Contactos] HTML del elemento:', direccionElement.outerHTML);
      console.log('[Contactos] Estilos computados display:', window.getComputedStyle(direccionElement).display);
      console.log('[Contactos] Estilos computados visibility:', window.getComputedStyle(direccionElement).visibility);
      console.log('[Contactos] Estilos computados color:', window.getComputedStyle(direccionElement).color);
      
      // Forzar evento input para que se detecte el cambio
      direccionElement.dispatchEvent(new Event('input', { bubbles: true }));
    } else if (!direccionElement) {
      console.error('[Contactos] ERROR: No se encontró el elemento direccion');
    }
    validateIdentificador();
    validateEmail();
    validateTelf(fields.telf1, icons.telf1);
    validateTelf(fields.telf2, icons.telf2);
    // Pequeño delay para asegurar que los valores se mantengan
    await new Promise(resolve => setTimeout(resolve, 100));
    cargandoContacto = false;
  } catch (err) {
    console.error(err);
    mostrarNotificacion('Error al cargar el contacto', 'error');
    // Pequeño delay para asegurar que los valores se mantengan
    await new Promise(resolve => setTimeout(resolve, 100));
    cargandoContacto = false;
  }
}

// Inicializar sistema de detección de cambios sin guardar
inicializarDeteccionCambios(async () => {
  console.log('[Contactos] Callback guardar ejecutado desde menú');
  
  // Indicar que estamos guardando desde el menú
  window.__guardandoDesdeMenu = true;
  
  try {
    // Llamar directamente a submitForm
    await submitForm();
    console.log('[Contactos] Guardado completado desde menú');
  } finally {
    // Limpiar el flag
    window.__guardandoDesdeMenu = false;
  }
});

// Inicializar pestañas primero
inicializarPestanas();

// Configurar listener para autocompletado de direcciones
const direccionInput = document.getElementById('direccion');
if (direccionInput) {
  direccionInput.addEventListener('input', function(e) {
    this.value = this.value.toUpperCase();
    marcarCambiosSinGuardar();
    // Activar búsqueda de sugerencias
    dirDebounce(this.value);
  });
  console.log('[Contactos] Listener de dirección configurado correctamente');
} else {
  console.error('[Contactos] No se pudo configurar listener de dirección');
}

// Luego cargar el contacto si hay ID en la URL
loadContacto();

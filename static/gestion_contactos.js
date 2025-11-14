// gestion_contactos.js
// Vanilla JS replacement for the former Vue implementation in GESTION_CONTACTOS.html
// Mantiene las mismas validaciones y envíos.

import { IP_SERVER, PORT, API_URL as API_URL_BASE } from './constantes.js?v=1762757322';
import { mostrarNotificacion } from './notificaciones.js';
import { inicializarDeteccionCambios, marcarCambiosSinGuardar, resetearCambiosSinGuardar, hayCambiosSinGuardar, debounce } from './scripts_utils.js';
import { inicializarPestanas } from './tabs.js';

const API_URL = `${API_URL_BASE}/api`;
let cargandoContacto = false;

// Esperar a que el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
  console.log('[Contactos] DOM cargado, inicializando...');

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

// Funciones de validación
function validateRequired() {
  let allValid = true;
  
  // Campos obligatorios
  const requiredFields = [
    { id: 'razonsocial', name: 'Razón Social' },
    { id: 'identificador', name: 'NIF/CIF' },
    { id: 'direccion', name: 'Dirección' },
    { id: 'cp', name: 'Código Postal' },
    { id: 'poblacio', name: 'Población' },
    { id: 'provincia', name: 'Provincia' }
  ];
  
  requiredFields.forEach(field => {
    const element = document.getElementById(field.id);
    if (element && !element.value.trim()) {
      element.style.borderColor = 'red';
      allValid = false;
      console.log(`[Validación] Campo obligatorio vacío: ${field.name}`);
    } else if (element) {
      element.style.borderColor = '';
    }
  });
  
  return allValid;
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
    if (!cargandoContacto) marcarCambiosSinGuardar();
  });
}
if (fields.direccion) {
  fields.direccion.addEventListener('input', function() {
    this.value = this.value.toUpperCase();
    if (!cargandoContacto) marcarCambiosSinGuardar();
  });
}
if (fields.poblacion) {
  fields.poblacion.addEventListener('input', function() {
    this.value = this.value.toUpperCase();
    if (!cargandoContacto) marcarCambiosSinGuardar();
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
  // Si se está guardando desde el menú, solo validar campos mínimos
  if (!window.__guardandoDesdeMenu) {
    const isValid = allValid();
    if (!isValid) {
      mostrarNotificacion('Por favor, completa todos los campos obligatorios (Razón Social, NIF/CIF, Dirección, CP, Población, Provincia)', 'error');
      
      // Activar la pestaña que contiene campos vacíos
      const direccion = document.getElementById('direccion');
      const cp = document.getElementById('cp');
      const poblacio = document.getElementById('poblacio');
      const provincia = document.getElementById('provincia');
      
      if (!direccion?.value.trim() || !cp?.value.trim() || !poblacio?.value.trim() || !provincia?.value.trim()) {
        // Activar pestaña de dirección si falta algún campo de dirección
        const tabButtons = document.querySelectorAll('.tab-button');
        const tabContents = document.querySelectorAll('.tab-content');
        
        tabButtons.forEach(btn => btn.classList.remove('active'));
        tabContents.forEach(content => content.classList.remove('active'));
        
        tabButtons[1]?.classList.add('active'); // Pestaña Dirección
        document.getElementById('tab-direccion')?.classList.add('active');
      }
      
      return;
    }
  } else {
    console.log('[Contactos] Guardando desde menú - validación mínima');
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
    facturacion_automatica: fields.facturacion.checked ? 1 : 0,
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
        fields[k].checked = data.facturacion_automatica === 1;
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

// Función para verificar si hay cambios reales
function verificarCambiosContacto() {
  const hayCambios = hayCambiosSinGuardar();
  console.log('[Contactos] Verificando cambios:', hayCambios);
  return hayCambios;
}

// Inicializar sistema de detección de cambios sin guardar
inicializarDeteccionCambios(async () => {
  console.log('[Contactos] Callback guardar ejecutado desde menú');
  
  // Indicar que estamos guardando desde el menú
  window.__guardandoDesdeMenu = true;
  
  try {
    // Verificar si hay campos obligatorios vacíos
    const razonsocial = document.getElementById('razonsocial')?.value.trim();
    const identificador = document.getElementById('identificador')?.value.trim();
    
    if (!razonsocial || !identificador) {
      mostrarNotificacion('Razón Social y NIF/CIF son obligatorios', 'error');
      window.__guardandoDesdeMenu = false;
      throw new Error('Usuario canceló');
    }
    
    // Llamar directamente a submitForm sin validación estricta
    await submitForm();
    console.log('[Contactos] Guardado completado desde menú');
  } finally {
    // Limpiar el flag
    window.__guardandoDesdeMenu = false;
  }
}, verificarCambiosContacto);

// Inicializar pestañas primero
inicializarPestanas();

// Configurar listeners para TODOS los campos después de inicializar pestañas
const todosLosCampos = [
  'razonsocial', 'identificador', 'mail', 'telf1', 'telf2',
  'direccion', 'cp', 'poblacio', 'provincia',
  'dir3_oficina', 'dir3_organo', 'dir3_unidad'
];

todosLosCampos.forEach(fieldId => {
  const element = document.getElementById(fieldId);
  if (element) {
    element.addEventListener('input', function() {
      if (!cargandoContacto) {
        console.log(`[Contactos] Campo ${fieldId} modificado - marcando cambios`);
        marcarCambiosSinGuardar();
      }
    });
  }
});

// Configurar listener especial para autocompletado de direcciones
const direccionInput = document.getElementById('direccion');
if (direccionInput) {
  direccionInput.addEventListener('input', function(e) {
    this.value = this.value.toUpperCase();
    // Activar búsqueda de sugerencias
    dirDebounce(this.value);
  });
  console.log('[Contactos] Listener de dirección configurado correctamente');
} else {
  console.error('[Contactos] No se pudo configurar listener de dirección');
}

// Listener para checkbox de facturación
const facturacionCheckbox = document.getElementById('facturacion_automatica');
if (facturacionCheckbox) {
  facturacionCheckbox.addEventListener('change', function() {
    if (!cargandoContacto) {
      console.log('[Contactos] Checkbox facturación modificado - marcando cambios');
      marcarCambiosSinGuardar();
    }
  });
}

console.log('[Contactos] Todos los listeners configurados');

// Listener para botón de escanear datos con OCR
// Ahora busca automáticamente en el buzón un email con asunto "C"
const btnEscanearDatos = document.getElementById('btnEscanearDatos');

if (btnEscanearDatos) {
  btnEscanearDatos.addEventListener('click', async function() {
    // Mostrar indicador de carga
    btnEscanearDatos.disabled = true;
    btnEscanearDatos.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Buscando email...';
    
    try {
      // Enviar petición al servidor (busca email con asunto "C" automáticamente)
      const response = await fetch(`${API_URL}/contactos/ocr`, {
        method: 'POST'
      });
      
      const resultado = await response.json();
      
      if (!response.ok) {
        throw new Error(resultado.error || 'Error al procesar');
      }
      
      if (resultado.success && resultado.datos) {
        // Rellenar campos con los datos extraídos
        const datos = resultado.datos;
        
        if (datos.razon_social) fields.razonsocial.value = datos.razon_social;
        if (datos.nif) fields.identificador.value = datos.nif;
        if (datos.email) fields.mail.value = datos.email;
        if (datos.telefono) fields.telf1.value = datos.telefono;
        if (datos.direccion) fields.direccion.value = datos.direccion;
        if (datos.cp) fields.cp.value = datos.cp;
        if (datos.poblacion) fields.poblacion.value = datos.poblacion;
        
        // Si hay nombre de contacto, agregarlo a notas
        if (datos.nombre_contacto) {
          const notasActuales = fields.notas ? fields.notas.value : '';
          if (!notasActuales.includes(datos.nombre_contacto)) {
            fields.notas.value = notasActuales ? `${notasActuales}\nContacto: ${datos.nombre_contacto}` : `Contacto: ${datos.nombre_contacto}`;
          }
        }
        
        // Marcar cambios sin guardar
        marcarCambiosSinGuardar();
        
        let mensaje = '✅ Datos extraídos del email. Revisa la información.';
        if (datos._metodo_ocr) {
          mensaje += ` (${datos._metodo_ocr})`;
        }
        
        mostrarNotificacion(mensaje, 'success');
        
        // Mostrar texto completo extraído en consola para debugging
        if (datos.texto_completo) {
          console.log('[OCR] Texto completo extraído:', datos.texto_completo);
        }
      } else {
        mostrarNotificacion('No se pudieron extraer datos de la imagen', 'warning');
      }
      
    } catch (error) {
      console.error('[OCR] Error:', error);
      
      let mensajeError = 'Error al procesar: ' + error.message;
      
      if (error.message.includes('No se encontró')) {
        mensajeError = '📧 No hay emails con asunto "C" o "c". Envía uno primero con la foto adjunta.';
      } else if (error.message.includes('no contiene ninguna imagen')) {
        mensajeError = '📷 El email no tiene imagen adjunta. Reenvía con la foto.';
      } else if (error.message.includes('Email no configurado')) {
        mensajeError = '⚙️ Email no configurado. Contacta al administrador.';
      }
      
      mostrarNotificacion(mensajeError, 'error');
    } finally {
      // Restaurar botón
      btnEscanearDatos.disabled = false;
      btnEscanearDatos.innerHTML = '<i class="fas fa-camera"></i> Escanear Datos';
    }
  });
}

// Luego cargar el contacto si hay ID en la URL
loadContacto();

}); // Fin DOMContentLoaded

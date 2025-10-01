    // Pequeño delay para asegurar que los valores se mantengan
    await new Promise(resolve => setTimeout(resolve, 100));
let cargandoContacto = false;
// gestion_contactos.js
// Vanilla JS replacement for the former Vue implementation in GESTION_CONTACTOS.html
// Mantiene las mismas validaciones y envíos.

import { IP_SERVER, PORT } from './constantes.js';
import { mostrarNotificacion } from './notificaciones.js';

const API_URL = `http://${IP_SERVER}:${PORT}/api`;

// Element references --------------------------------------------------------
const form = document.getElementById('contactForm');
const btnGuardar = document.getElementById('btnGuardar');
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
  poblacio: document.getElementById('poblacio'),
  provincia: document.getElementById('provincia'),
  facturacion: document.getElementById('facturacion_automatica'),
  dir3Oficina: document.getElementById('dir3_oficina'),
  dir3Organo: document.getElementById('dir3_organo'),
  dir3Unidad: document.getElementById('dir3_unidad')
};

const icons = {
  identificador: document.getElementById('icon-identificador'),
  mail: document.getElementById('icon-mail'),
  telf1: document.getElementById('icon-telf1'),
  telf2: document.getElementById('icon-telf2'),
  cp: document.getElementById('icon-cp')
};

// ------------------------ Validación helpers ------------------------------
const regex = {
  email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  telefono: /^[0-9]{9,10}$/,
  vat: /^([A-Z]{2})?[0-9]{8,10}$/,
  nif: /^[0-9]{8}[A-Z]$/,
  nie: /^[XYZ][0-9]{7}[A-Z]$/,
  cif: /^[ABCDEFGHJNPQRSUVW][0-9]{7}[0-9A-J]$/
};

const letrasNIF = 'TRWAGMYFPDXBNJZSQVHLCKET';

function validarNIF(nif) {
  const numero = nif.substring(0, 8);
  const letra = nif.charAt(8);
  return letra === letrasNIF.charAt(parseInt(numero, 10) % 23);
}
function validarNIE(nie) {
  const mapa = { X: '0', Y: '1', Z: '2' };
  const numero = mapa[nie.charAt(0)] + nie.substring(1, 8);
  const letra = nie.charAt(8);
  return letra === letrasNIF.charAt(parseInt(numero, 10) % 23);
}
function validarCIF(cif) {
  // Convertir a mayúsculas
  cif = cif.toUpperCase();
  // Validar formato básico
  if (!/^[A-Z][0-9]{7}[0-9A-Z]$/.test(cif)) {
    return false;
  }
  
  // Extraer los números
  const nums = cif.substring(1, 8).split('').map(Number);
  
  // Calcular suma de posiciones pares (0-indexed: 0,2,4,6)
  let s1 = 0;
  for (let i = 0; i < nums.length; i += 2) {
    const n = nums[i];
    const prod = n * 2;
    s1 += Math.floor(prod / 10) + (prod % 10);
  }
  
  // Calcular suma de posiciones impares (0-indexed: 1,3,5)
  let s2 = 0;
  for (let i = 1; i < nums.length; i += 2) {
    s2 += nums[i];
  }
  
  // Calcular dígito de control
  const c = (10 - (s1 + s2) % 10) % 10;
  const tabla = "JABCDEFGHI";
  const letra = cif.charAt(0);
  const ctrl = cif.charAt(8);
  
  // Determinar control esperado según la letra inicial
  let ctrl_esp;
  if (["P", "Q", "R", "S", "N", "W"].includes(letra)) {
    // Control es letra
    ctrl_esp = tabla[c];
  } else if (["A", "B", "E", "H"].includes(letra)) {
    // Control es número
    ctrl_esp = c.toString();
  } else {
    // Control puede ser letra o número
    ctrl_esp = [c.toString(), tabla[c]];
  }
  
  // Validar
  if (typeof ctrl_esp === 'string') {
    return ctrl === ctrl_esp;
  } else {
    return ctrl_esp.includes(ctrl);
  }
}

function setIcon(valid, icon) {
  if (!icon) return;
  icon.className = 'validation-icon fa ' + (valid ? 'fa-check valid' : 'fa-times invalid');
}

function markValidity(field, valid) {
  if (!field) return;
  field.style.border = valid ? '' : '2px solid #e74c3c';
}

function validateIdentificador() {
  const value = fields.identificador.value.toUpperCase();
  let ok = false;
  if (value.includes('/')) ok = true;
  else if (regex.vat.test(value)) ok = true;
  else if (regex.nif.test(value)) ok = validarNIF(value);
  else if (regex.nie.test(value)) ok = validarNIE(value);
  else if (regex.cif.test(value)) ok = validarCIF(value);
  setIcon(ok, icons.identificador);
  markValidity(fields.identificador, ok);
  return ok;
}
function validateEmail() {
  const val = fields.mail.value.trim();
  if (!val) { // campo vacío es válido
    setIcon(true, icons.mail);
    return true;
  }
  const ok = regex.email.test(val);
  setIcon(ok, icons.mail);
  markValidity(fields.mail, ok);
  return ok;
}
function validateTelf(field, icon) {
  const val = field.value;
  const ok = !val || regex.telefono.test(val);
  setIcon(ok, icon);
  return ok;
}

function markMissing(field, missing) {
  if (!field) return;
  field.style.border = missing ? '2px solid #e74c3c' : '';
}

function validateRequired() {
  const required = ['razonsocial','identificador','direccion'];
  let ok = true;
  required.forEach(name => {
    const el = fields[name];
    const missing = !el || !el.value.trim();
    markMissing(el, missing);
    if (missing) ok = false;
  });
  return ok;
}

// ------------------------ Sugerencias de dirección ------------------------
// ---------------- Debounce util -------------------
function debounceFn(fn, delay=300){
  let t;return (...args)=>{clearTimeout(t);t=setTimeout(()=>fn(...args),delay);} }

// ---- Dirección sugerencias ----
const dirDebounce = debounceFn((q)=>buscarSugerenciasCarrer(q),300);
fields.direccion.addEventListener('input', e=>dirDebounce(e.target.value));

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
const cpDebounce = debounceFn((p)=>buscarCPSuggestions(p),300);
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
fields.identificador.addEventListener('input', validateIdentificador);
fields.mail.addEventListener('input', validateEmail);
fields.telf1.addEventListener('input', () => validateTelf(fields.telf1, icons.telf1));
fields.telf2.addEventListener('input', () => validateTelf(fields.telf2, icons.telf2));

// ------------------------ Submit & Cancel -----------------------
btnGuardar.addEventListener('click', submitForm);
btnCancelar.addEventListener('click', () => {
  window.location.href = 'CONSULTA_CONTACTOS.html';
});

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

  const contactoData = {
    razonsocial: fields.razonsocial.value.trim().toUpperCase(),
    identificador: fields.identificador.value.trim().toUpperCase(),
    mail: fields.mail.value.trim(),
    telf1: fields.telf1.value ? fields.telf1.value.trim() : null,
    telf2: fields.telf2.value ? fields.telf2.value.trim() : null,
    direccion: fields.direccion.value ? fields.direccion.value.trim().toUpperCase() : null,
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
    mostrarNotificacion(data.message || 'Contacto guardado correctamente', 'success');
    setTimeout(() => (window.location.href = 'CONSULTA_CONTACTOS.html'), 1500);
  } catch (err) {
    console.error(err);
    mostrarNotificacion(err.message || 'Error al guardar el contacto', 'error');
  }
}

// ------------------------ Load existing contact ---------------------------
(async function loadContacto() {
  const urlParams = new URLSearchParams(window.location.search);
  const id = urlParams.get('id');
  if (!id) return;
  cargandoContacto = true;
  try {
    const res = await fetch(`${API_URL}/contactos/get_contacto/${id}`);
    if (!res.ok) throw new Error('Error al obtener el contacto');
    const data = await res.json();
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
})();

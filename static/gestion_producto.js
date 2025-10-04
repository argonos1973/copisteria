import { IP_SERVER, PORT } from './constantes.js';
import { mostrarNotificacion, mostrarConfirmacion } from './notificaciones.js';
import { mostrarCargando, ocultarCargando, inicializarDeteccionCambios, marcarCambiosSinGuardar, resetearCambiosSinGuardar } from './scripts_utils.js';

// Utilidades de redondeo
const round5 = (v) => Number(v ?? 0).toFixed(5);
const round2 = (v) => +Number(v ?? 0).toFixed(2);

// Función para convertir comas a puntos en importes
const convertirComaAPunto = (valor) => {
  if (typeof valor === 'string') {
    return valor.replace(',', '.');
  }
  return valor;
};

document.addEventListener('DOMContentLoaded', () => {
  const API_BASE = `http://${IP_SERVER}:${PORT}/api`;

  // Elementos
  const titulo = document.getElementById('tituloFormulario');
  const form = document.getElementById('formProducto');
  const inputNombre = document.getElementById('nombre');
  const inputDescripcion = document.getElementById('descripcion');
  const inputSubtotal = document.getElementById('subtotal');
  const selectImpuestos = document.getElementById('impuestos');
  const inputTotal = document.getElementById('total');
  const btnCancelar = document.getElementById('btnCancelar');
  const btnGuardar = document.getElementById('btnGuardar');
  // Bloque resumen de franjas en edición
  const bloqueFranjasEdicion = document.getElementById('bloqueFranjasEdicion');
  const franjasResumen = document.getElementById('franjasResumen');
  const btnGestionarFranjas = document.getElementById('btnGestionarFranjas');

  // Franjas automáticas
  const fieldsetFranjas = document.getElementById('fieldsetFranjasAuto');
  const chkFranjasAuto1500 = document.getElementById('chkFranjasAuto1500');
  const chkNoGenerarFranjas = document.getElementById('chkNoGenerarFranjas');
  const inFranjaInicio = document.getElementById('franja_inicio');
  const inBandas = document.getElementById('bandas');
  const inAncho = document.getElementById('ancho');
  const inDescInicial = document.getElementById('descuento_inicial');
  const inIncremento = document.getElementById('incremento');

  // Errores
  const errNombre = document.getElementById('errorNombre');
  const errSubtotal = document.getElementById('errorSubtotal');
  const errImpuestos = document.getElementById('errorImpuestos');

  // Estado simple
  const state = {
    id: null,
    nombre: '',
    descripcion: '',
    subtotal: 0,
    impuestos: 21,
    iva: 0,
    total: 0,
    cargando: false,
    modoEdicion: false,
  };

  // Valores por defecto de franjas automáticas
  inFranjaInicio.value = 1;
  inBandas.value = 3;
  inAncho.value = 10;
  inDescInicial.value = 5;
  inIncremento.value = 5;

  // Aplicar configuración automática 1-500 (50 franjas, ancho 10, 0% -> ~60%)
  const aplicarAuto1500 = (activar) => {
    if (!inFranjaInicio || !inBandas || !inAncho || !inDescInicial || !inIncremento) return;
    if (activar) {
      inFranjaInicio.value = '1';
      inBandas.value = '50';
      inAncho.value = '10';
      inDescInicial.value = '0';
      // Reducir incremento por franja para minimizar saltos (50 franjas => 50 pasos aprox.)
      // Nota: con 60/50 la última franja queda en ~58.8% si desc_inicial=0, respetando tope 60%.
      const inc = 60 / 50;
      inIncremento.value = inc.toFixed(6);
    }
    // Habilitar/Deshabilitar controles según estado
    inBandas.disabled = activar;
    inAncho.disabled = activar;
    inDescInicial.disabled = activar;
    inIncremento.disabled = activar;
    if (inFranjaInicio) {
      inFranjaInicio.disabled = true; // siempre 1
      inFranjaInicio.title = 'La franja inicial siempre es 1';
    }
  };

  if (chkFranjasAuto1500) {
    chkFranjasAuto1500.addEventListener('change', (e) => {
      const isChecked = e.target.checked;
      console.log('Checkbox change event:', isChecked);
      aplicarAuto1500(isChecked);
      
      // Si se activa franjas automáticas, desactivar "no generar franjas"
      if (isChecked && chkNoGenerarFranjas) {
        chkNoGenerarFranjas.checked = false;
      }
    });
  }

  // Función para deshabilitar/habilitar campos de configuración de franjas
  const toggleCamposFranjas = (disabled) => {
    if (inFranjaInicio) inFranjaInicio.disabled = disabled;
    if (inBandas) inBandas.disabled = disabled;
    if (inAncho) inAncho.disabled = disabled;
    if (inDescInicial) inDescInicial.disabled = disabled;
    if (inIncremento) inIncremento.disabled = disabled;
  };

  // Checkbox para no generar franjas
  if (chkNoGenerarFranjas) {
    chkNoGenerarFranjas.addEventListener('change', (e) => {
      const isChecked = e.target.checked;
      console.log('No generar franjas checkbox:', isChecked);
      
      // Si se activa "no generar franjas", desactivar franjas automáticas y deshabilitar campos
      if (isChecked) {
        if (chkFranjasAuto1500) {
          chkFranjasAuto1500.checked = false;
          aplicarAuto1500(false);
        }
        // Deshabilitar todos los campos de configuración de franjas
        toggleCamposFranjas(true);
      } else {
        // Habilitar campos de configuración de franjas
        toggleCamposFranjas(false);
      }
    });
  }

  // Funciones de cálculo
  const recalcDesdeSubtotal = () => {
    const base = Number(convertirComaAPunto(inputSubtotal.value) || 0);
    const ivaPct = Number(selectImpuestos.value || 0);
    if (isNaN(base) || isNaN(ivaPct)) return;
    const iva = round2(base * (ivaPct / 100));
    inputTotal.value = round2(base + iva);
  };

  const recalcDesdeTotal = () => {
    const total = Number(convertirComaAPunto(inputTotal.value) || 0);
    const ivaPct = Number(selectImpuestos.value || 0);
    if (isNaN(total) || isNaN(ivaPct)) return;
    const divisor = 1 + (ivaPct / 100);
    const base = total / divisor;
    inputSubtotal.value = round5(base);
  };

  // Uppercase en tiempo real + marcar cambios
  inputNombre.addEventListener('input', () => {
    inputNombre.value = (inputNombre.value || '').toUpperCase();
    marcarCambiosSinGuardar();
  });
  inputDescripcion.addEventListener('input', () => {
    inputDescripcion.value = (inputDescripcion.value || '').toUpperCase();
    marcarCambiosSinGuardar();
  });

  // Recalcular + marcar cambios
  inputSubtotal.addEventListener('input', () => {
    recalcDesdeSubtotal();
    marcarCambiosSinGuardar();
  });
  inputTotal.addEventListener('input', () => {
    recalcDesdeTotal();
    marcarCambiosSinGuardar();
  });
  selectImpuestos.addEventListener('change', () => {
    recalcDesdeSubtotal();
    marcarCambiosSinGuardar();
  });

  // Navegación
  btnCancelar.addEventListener('click', () => {
    window.location.href = 'CONSULTA_PRODUCTOS.html';
  });

  // Cargar si hay id en URL (sanear 'null'/'undefined')
  const params = new URLSearchParams(window.location.search);
  const rawId = params.get('id');
  const id = (rawId && rawId !== 'null' && rawId !== 'undefined' && rawId.trim() !== '') ? rawId : null;
  const accion = params.get('accion');
  const confirmado = params.get('confirmado');

  const cargarProducto = async (pid) => {
    try {
      state.cargando = true;
      mostrarCargando();
      const { data } = await axios.get(`${API_BASE}/productos/${pid}`);
      console.log('Backend response for product:', JSON.stringify(data, null, 2));
      console.log('Subtotal from backend:', data.subtotal, 'Type:', typeof data.subtotal);
      state.id = data.id;
      inputNombre.value = data.nombre || '';
      inputDescripcion.value = data.descripcion || '';
      selectImpuestos.value = Number(data.impuestos ?? 21);
      // Mostrar exactamente el valor recibido desde backend sin redondear ni formatear
      inputSubtotal.value = (data.subtotal !== undefined && data.subtotal !== null) ? String(data.subtotal) : '';
      console.log('Subtotal set from backend (no rounding):', inputSubtotal.value, 'Type:', typeof inputSubtotal.value);
      recalcDesdeSubtotal();
      state.modoEdicion = true;
      titulo.textContent = 'Producto';
      // Mantener visible el bloque de franjas automáticas también en edición para poder enviar parámetros
      if (fieldsetFranjas) fieldsetFranjas.style.display = '';
      if (btnGuardar) btnGuardar.textContent = 'Guardar';

      // Cargar configuración de franjas automáticas
      try {
        const configResp = await axios.get(`${API_BASE}/productos/${pid}/franjas_config`);
        const config = configResp.data?.config || {};
        
        // Actualizar campos con la configuración guardada
        if (inFranjaInicio) inFranjaInicio.value = config.franja_inicial || 1;
        if (inBandas) inBandas.value = config.numero_franjas || 50;
        if (inAncho) inAncho.value = config.ancho_franja || 10;
        if (inDescInicial) inDescInicial.value = config.descuento_inicial || 5.0;
        if (inIncremento) inIncremento.value = config.incremento_franja || 5.0;
        
        // Actualizar checkbox según calculo_automatico
        if (chkFranjasAuto1500) {
          const esAutomatico = config.calculo_automatico === 1;
          console.log('Configuración cargada:', config);
          console.log('calculo_automatico:', config.calculo_automatico, 'tipo:', typeof config.calculo_automatico, 'esAutomatico:', esAutomatico);
          
          // Forzar la actualización del checkbox
          chkFranjasAuto1500.checked = esAutomatico;
          
          // Aplicar directamente sin disparar evento change para evitar bucle
          aplicarAuto1500(esAutomatico);
          
          console.log('Checkbox actualizado:', chkFranjasAuto1500.checked);
          console.log('Estado después del evento:', chkFranjasAuto1500.checked);
        }
        
        // Actualizar checkbox "No generar franjas" según no_generar_franjas
        if (chkNoGenerarFranjas) {
          const noGenerarFranjas = config.no_generar_franjas === 1;
          console.log('no_generar_franjas:', config.no_generar_franjas, 'tipo:', typeof config.no_generar_franjas, 'noGenerarFranjas:', noGenerarFranjas);
          
          // Actualizar checkbox
          chkNoGenerarFranjas.checked = noGenerarFranjas;
          
          // Si está activado, deshabilitar campos de configuración
          if (noGenerarFranjas) {
            toggleCamposFranjas(true);
          }
          
          console.log('Checkbox no generar franjas actualizado:', chkNoGenerarFranjas.checked);
        }
      } catch (configError) {
        console.warn('No se pudo cargar la configuración de franjas:', configError);
        // Usar valores por defecto si no hay configuración
        if (chkFranjasAuto1500) {
          chkFranjasAuto1500.checked = false;
          aplicarAuto1500(false);
        }
      }

      // Cargar y mostrar resumen de franjas del producto en edición
      try {
        mostrarCargando();
        const resFranjas = await axios.get(`${API_BASE}/productos/${pid}/franjas_descuento`);
        const lista = Array.isArray(resFranjas.data?.franjas) ? resFranjas.data.franjas : [];
        const n = lista.length;
        if (bloqueFranjasEdicion && franjasResumen) {
          bloqueFranjasEdicion.style.display = '';
          if (n === 0) {
            franjasResumen.textContent = 'Sin franjas definidas';
          } else {
            // Mostrar rango de cantidades y % mínimo-máximo
            const mins = lista.map(f => Number(f.min ?? f.min_cantidad ?? 0));
            const maxs = lista.map(f => Number(f.max ?? f.max_cantidad ?? 0));
            const descs = lista.map(f => Number(f.descuento ?? f.porcentaje_descuento ?? 0));
            const minMin = Math.min(...mins);
            const maxMax = Math.max(...maxs);
            const minDesc = Math.min(...descs);
            const maxDesc = Math.max(...descs);
            franjasResumen.textContent = `${n} franjas · unidades ${minMin}-${maxMax} · desc ${minDesc.toFixed(8)}%-${maxDesc.toFixed(8)}%`;
          }

        }
        if (btnGestionarFranjas) {
          btnGestionarFranjas.onclick = () => {
            // Abrir la pantalla dedicada con el producto preseleccionado
            window.location.href = `FRANJAS_DESCUENTO.html?producto_id=${encodeURIComponent(pid)}`;
          };
        }
      } catch (eFran) {
        if (bloqueFranjasEdicion && franjasResumen) {
          bloqueFranjasEdicion.style.display = '';
          franjasResumen.textContent = 'No se pudieron cargar las franjas';
        }
        console.warn('No se pudieron cargar las franjas:', eFran);
      } finally { ocultarCargando(); }
    } catch (e) {
      console.error('Error al cargar el producto:', e);
      const status = e?.response?.status;
      const msg = e?.response?.data?.message || e?.response?.data?.error || e?.message || 'No se pudo cargar';
      mostrarNotificacion(`Error${status ? ' '+status : ''}: ${msg}`, 'error');
    } finally {
      state.cargando = false;
      ocultarCargando();
    }
  };

  const eliminarProductoActual = async () => {
    if (!state.id) {
      mostrarNotificacion('No hay producto para eliminar', 'error');
      return;
    }
    const ok = await mostrarConfirmacion('¿Está seguro de eliminar este producto?');
    if (!ok) return;
    try {
      state.cargando = true;
      mostrarCargando();
      const { data } = await axios.delete(`${API_BASE}/productos/${state.id}`);
      if (data?.success) {
        mostrarNotificacion('Producto eliminado correctamente', 'success');
        setTimeout(() => { window.location.href = 'CONSULTA_PRODUCTOS.html'; }, 600);
      } else {
        mostrarNotificacion(data?.message || 'No se pudo eliminar el producto.', 'error');
      }
    } catch (e) {
      console.error('Error al eliminar el producto:', e);
      mostrarNotificacion(e.response?.data?.message || e.response?.data?.error || 'No se pudo eliminar el producto', 'error');
    } finally {
      state.cargando = false;
      ocultarCargando();
    }
  };

  if (id) {
    cargarProducto(id).then(async () => {
      if (accion === 'eliminar') {
        if (confirmado === '1') {
          try {
            state.cargando = true;
            mostrarCargando();
            const { data } = await axios.delete(`${API_BASE}/productos/${state.id}`);
            if (data?.success) {
              mostrarNotificacion('Producto eliminado correctamente', 'success');
              setTimeout(() => { window.location.href = 'CONSULTA_PRODUCTOS.html'; }, 600);
            } else {
              mostrarNotificacion(data?.message || 'No se pudo eliminar el producto.', 'error');
            }
          } catch (e) {
            console.error('Error al eliminar el producto (confirmado=1):', e);
            mostrarNotificacion(e.response?.data?.message || e.response?.data?.error || 'No se pudo eliminar el producto', 'error');
          } finally {
            state.cargando = false;
            ocultarCargando();
          }
        } else {
          await eliminarProductoActual();
        }
      }
    });
  } else {
    // Modo creación
    selectImpuestos.value = 21;
    titulo.textContent = 'Nuevo Producto';
    if (btnGuardar) btnGuardar.textContent = 'Crear Producto';
    // La franja inicial siempre será 1
    if (inFranjaInicio) {
      inFranjaInicio.value = '1';
      inFranjaInicio.min = '1';
      inFranjaInicio.disabled = true;
      inFranjaInicio.title = 'La franja inicial siempre es 1';
    }
    // Si el checkbox está activo al entrar, aplicar preset
    if (chkFranjasAuto1500 && chkFranjasAuto1500.checked) {
      aplicarAuto1500(true);
    }
  }

  // Validación simple
  const validar = () => {
    let ok = true;
    errNombre.style.display = 'none';
    errSubtotal.style.display = 'none';
    errImpuestos.style.display = 'none';

    if (!inputNombre.value.trim()) {
      errNombre.textContent = 'El nombre es obligatorio';
      errNombre.style.display = '';
      ok = false;
    }
    const sb = Number(inputSubtotal.value);
    if (isNaN(sb)) {
      errSubtotal.textContent = 'El precio base debe ser un número válido';
      errSubtotal.style.display = '';
      ok = false;
    } else if (sb < 0) {
      errSubtotal.textContent = 'El precio base no puede ser negativo';
      errSubtotal.style.display = '';
      ok = false;
    }
    const ivaPct = Number(selectImpuestos.value);
    if (isNaN(ivaPct)) {
      errImpuestos.textContent = 'El porcentaje de impuestos debe ser un valor válido';
      errImpuestos.style.display = '';
      ok = false;
    }
    return ok;
  };

  // Submit
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!validar()) {
      mostrarNotificacion('Por favor, corrija los errores del formulario', 'error');
      return;
    }

    const payloadBase = {
      nombre: inputNombre.value.trim().toUpperCase(),
      descripcion: (inputDescripcion.value || '').trim().toUpperCase(),
      subtotal: Number(Number(convertirComaAPunto(inputSubtotal.value) || 0).toFixed(5)),
      impuestos: Number(selectImpuestos.value || 0),
    };
    // Calcular totales coherentes en backend también, pero enviamos total estimado
    const ivaCalc = round2(payloadBase.subtotal * (payloadBase.impuestos / 100));
    const totalCalc = round2(payloadBase.subtotal + ivaCalc);
    const payload = { ...payloadBase, iva: ivaCalc, total: totalCalc };

    try {
      state.cargando = true;
      let resp;
      if (state.modoEdicion && state.id) {
        // Actualizar configuración de franjas automáticas
        const configFranjas = {
          calculo_automatico: chkFranjasAuto1500 && chkFranjasAuto1500.checked ? 1 : 0,
          no_generar_franjas: chkNoGenerarFranjas && chkNoGenerarFranjas.checked ? 1 : 0,
          franja_inicial: Number(convertirComaAPunto(inFranjaInicio.value) || 1),
          numero_franjas: Number(convertirComaAPunto(inBandas.value) || 50),
          ancho_franja: Number(convertirComaAPunto(inAncho.value) || 10),
          descuento_inicial: Number(convertirComaAPunto(inDescInicial.value) || 5.0),
          incremento_franja: Number(convertirComaAPunto(inIncremento.value) || 5.0)
        };
        
        // Añadir configuración de franjas al payload
        payload.config_franjas = configFranjas;
        
        console.log('DEBUG frontend - Enviando config_franjas (edición):', configFranjas);
        console.log('DEBUG frontend - no_generar_franjas value:', chkNoGenerarFranjas?.checked);
        
        mostrarCargando();
        console.log('payload (edición)', JSON.parse(JSON.stringify(payload)));
        resp = await axios.put(`${API_BASE}/productos/${state.id}`, payload);
      } else {
        // En creación: añadir configuración de franjas directamente al payload
        payload.calculo_automatico = chkFranjasAuto1500 && chkFranjasAuto1500.checked ? 1 : 0;
        payload.no_generar_franjas = chkNoGenerarFranjas && chkNoGenerarFranjas.checked ? 1 : 0;
        payload.franja_inicial = Number(convertirComaAPunto(inFranjaInicio.value) || 1);
        payload.numero_franjas = Number(convertirComaAPunto(inBandas.value) || 50);
        payload.ancho_franja = Number(convertirComaAPunto(inAncho.value) || 10);
        payload.descuento_inicial = Number(convertirComaAPunto(inDescInicial.value) || 5.0);
        payload.incremento_franja = Number(convertirComaAPunto(inIncremento.value) || 5.0);
        
        console.log('DEBUG frontend - calculo_automatico (creación):', payload.calculo_automatico);
        console.log('DEBUG frontend - no_generar_franjas (creación):', payload.no_generar_franjas);
        
        // Añadir franjas_auto sólo en creación
        payload.franjas_auto = {
          franja_inicio: 1,
          bandas: Number(convertirComaAPunto(inBandas.value) || 0),
          ancho: Number(convertirComaAPunto(inAncho.value) || 0),
          descuento_inicial: Number(convertirComaAPunto(inDescInicial.value) || 0),
          incremento: Number(convertirComaAPunto(inIncremento.value) || 0)
        };
        
        mostrarCargando();
        console.log('payload (creación)', JSON.parse(JSON.stringify(payload)));
        resp = await axios.post(`${API_BASE}/productos`, payload);
      }
      if (resp.data?.success) {
        // Resetear flag de cambios sin guardar
        resetearCambiosSinGuardar();
        
        if (state.modoEdicion) {
          mostrarNotificacion('Producto actualizado correctamente', 'success');
          setTimeout(() => { window.location.href = 'CONSULTA_PRODUCTOS.html'; }, 800);
        } else {
          const nuevoIdRaw = resp?.data?.id;
          const nuevoId = parseInt(nuevoIdRaw, 10);
          if (Number.isFinite(nuevoId) && nuevoId > 0) {
            mostrarNotificacion(`Producto creado (ID ${nuevoId})`, 'success');
            // Redirigir a edición del nuevo producto
            setTimeout(() => { window.location.href = `GESTION_PRODUCTOS.html?id=${nuevoId}`; }, 600);
          } else {
            // Si el backend no devolviera ID por algún motivo, volver a la lista
            mostrarNotificacion('Producto creado correctamente', 'success');
            setTimeout(() => { window.location.href = 'CONSULTA_PRODUCTOS.html'; }, 800);
          }
        }
      } else {
        mostrarNotificacion(resp.data?.message || 'Error al guardar el producto', 'error');
      }
    } catch (error) {
      console.error('Error al guardar el producto:', error);
      mostrarNotificacion(error.response?.data?.message || error.response?.data?.error || 'Error al guardar el producto', 'error');
    } finally {
      state.cargando = false;
      ocultarCargando();
    }
  });
  
  // Inicializar sistema de detección de cambios sin guardar
  inicializarDeteccionCambios(async () => {
    // Callback para guardar cuando el usuario acepta
    const formProducto = document.getElementById('formProducto');
    if (formProducto) {
      formProducto.dispatchEvent(new Event('submit'));
    }
  });
});

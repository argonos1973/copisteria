import { formatearFecha, formatearImporte, fetchConManejadorErrores, parsearImporte, buildApiUrl } from './scripts_utils.js?v=MIXED_CONTENT_FIX';
import { IP_SERVER, PORT, IS_PROD } from './constantes.js';

// ==============================
// ESTADISTICAS FACTURAS - COMPLETO
// ==============================

// ==============================
// EVENTOS INICIALES
// ==============================
// ---- Toggle visibility of card content ----
// Cache local de preferencias para evitar llamadas excesivas
let _prefsCache = null;
let _prefsCacheLoaded = false;

function setCardVisibility(card, hide) {
  if(hide) {
    // Ocultar completamente la tarjeta para que se reorganicen
    card.style.display = 'none';
  } else {
    card.style.display = '';
  }
  
  const btn = card.querySelector('.toggle-card');
  if(btn) {
    const icon = btn.querySelector('i');
    icon.classList.toggle('fa-eye', hide);
    icon.classList.toggle('fa-eye-slash', !hide);
    btn.title = hide ? 'Mostrar' : 'Ocultar';
  }
}

// Guarda preferencia de tarjeta oculta en el perfil del usuario
async function guardarPreferenciaCard(cardId, hidden) {
  try {
    const key = `statsHidden_${cardId}`;
    // Actualizar cache local
    if (!_prefsCache) _prefsCache = {};
    _prefsCache[key] = hidden ? '1' : '0';
    
    // Guardar en servidor
    await fetch('/api/auth/preferencias', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ [key]: hidden ? '1' : '0' })
    });
  } catch (e) {
    console.warn('No se pudo guardar preferencia:', e);
  }
}

// Carga preferencias del usuario desde el servidor
async function cargarPreferenciasUsuario() {
  if (_prefsCacheLoaded) return _prefsCache || {};
  try {
    const res = await fetch('/api/auth/preferencias');
    if (res.ok) {
      _prefsCache = await res.json();
      _prefsCacheLoaded = true;
      return _prefsCache;
    }
  } catch (e) {
    console.warn('No se pudieron cargar preferencias:', e);
  }
  return {};
}

// Mapa de nombres amigables para las tarjetas
const cardNames = {
  'card-tickets': 'Tickets',
  'card-facturas': 'Facturas', 
  'card-global': 'Total Global',
  'card-ingresos-gastos-totales': 'Ingresos y Gastos',
  'card-top-clientes': 'Top 10 Clientes',
  'card-top-productos': 'Top 10 Productos',
  'card-gastos-mes-solo': 'Gastos del Mes',
  'card-gastos-mes': 'Gastos Trimestre',
  'card-gastos-anio': 'Gastos Año',
  'card-top-gastos': 'Top 10 Gastos'
};

// Actualiza el menú de tarjetas ocultas
function actualizarMenuTarjetasOcultas() {
  // Buscar tarjetas realmente ocultas (display: none)
  const allCards = document.querySelectorAll('.stats-card');
  const hiddenCards = [...allCards].filter(card => {
    const style = window.getComputedStyle(card);
    return style.display === 'none';
  });
  
  const btn = document.getElementById('btn-tarjetas-ocultas');
  const countSpan = document.getElementById('hidden-count');
  const list = document.getElementById('hidden-cards-list');
  
  if (!btn || !list) return;
  
  if (hiddenCards.length === 0) {
    btn.style.display = 'none';
    return;
  }
  
  btn.style.display = 'inline-flex';
  countSpan.textContent = hiddenCards.length;
  
  list.innerHTML = '';
  hiddenCards.forEach(card => {
    const name = cardNames[card.id] || card.id;
    const item = document.createElement('div');
    item.innerHTML = `<i class="fas fa-eye" style="color:#2ecc71;"></i> ${name}`;
    item.addEventListener('click', async () => {
      const container = card.parentElement;
      container.appendChild(card);
      setCardVisibility(card, false);
      await guardarPreferenciaCard(card.id, false);
      actualizarMenuTarjetasOcultas();
      document.getElementById('hidden-cards-dropdown').style.display = 'none';
    });
    list.appendChild(item);
  });
}

// Inicializa los controles de colapso para todas las tarjetas de estadísticas
async function initCollapseControls() {
  // Cargar preferencias del usuario primero
  const prefs = await cargarPreferenciasUsuario();
  
  document.querySelectorAll('.toggle-card').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const card = btn.closest('.stats-card');
      // toggle state - ocultar
      setCardVisibility(card, true);
      await guardarPreferenciaCard(card.id, true);
      actualizarMenuTarjetasOcultas();
    });
    
    // aplicar estado guardado al cargar
    const card = btn.closest('.stats-card');
    const key = `statsHidden_${card.id}`;
    const hiddenSaved = prefs[key] === '1';
    setCardVisibility(card, hiddenSaved);
  });
  
  // Actualizar menú inicial
  actualizarMenuTarjetasOcultas();
  
  // Toggle dropdown de tarjetas ocultas
  const btnOcultas = document.getElementById('btn-tarjetas-ocultas');
  const dropdown = document.getElementById('hidden-cards-dropdown');
  if (btnOcultas && dropdown) {
    btnOcultas.addEventListener('click', (e) => {
      e.stopPropagation();
      const isHidden = dropdown.style.display === 'none' || !dropdown.style.display;
      if (isHidden) {
        // Aplicar estilos del tema al dropdown
        const bodyStyles = getComputedStyle(document.body);
        const cardBg = bodyStyles.getPropertyValue('--card-bg').trim() || 
                       bodyStyles.getPropertyValue('--bg').trim() || 
                       bodyStyles.backgroundColor || '#2d2d2d';
        const textColor = bodyStyles.getPropertyValue('--text').trim() || 
                          bodyStyles.color || '#e0e0e0';
        const borderColor = bodyStyles.getPropertyValue('--border').trim() || '#444';
        
        dropdown.style.background = cardBg;
        dropdown.style.color = textColor;
        dropdown.style.borderColor = borderColor;
        dropdown.style.display = 'block';
      } else {
        dropdown.style.display = 'none';
      }
    });
    document.addEventListener('click', () => dropdown.style.display = 'none');
  }
  
  // Inicializar drag & drop
  initDragAndDrop();
  
  // Aplicar orden guardado
  aplicarOrdenTarjetas(prefs);
}

// ============================================================================
// DRAG & DROP PARA REORGANIZAR TARJETAS
// ============================================================================
let draggedCard = null;

function initDragAndDrop() {
  document.querySelectorAll('.stats-card').forEach(card => {
    card.setAttribute('draggable', 'true');
    card.style.cursor = 'grab';
    
    card.addEventListener('dragstart', handleDragStart);
    card.addEventListener('dragend', handleDragEnd);
    card.addEventListener('dragover', handleDragOver);
    card.addEventListener('dragenter', handleDragEnter);
    card.addEventListener('dragleave', handleDragLeave);
    card.addEventListener('drop', handleDrop);
  });
}

function handleDragStart(e) {
  draggedCard = this;
  this.style.opacity = '0.4';
  this.style.cursor = 'grabbing';
  e.dataTransfer.effectAllowed = 'move';
  e.dataTransfer.setData('text/html', this.id);
}

function handleDragEnd(e) {
  this.style.opacity = '1';
  this.style.cursor = 'grab';
  document.querySelectorAll('.stats-card').forEach(card => {
    card.classList.remove('drag-over');
  });
}

function handleDragOver(e) {
  if (e.preventDefault) e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  return false;
}

function handleDragEnter(e) {
  if (this !== draggedCard) {
    this.classList.add('drag-over');
  }
}

function handleDragLeave(e) {
  this.classList.remove('drag-over');
}

function handleDrop(e) {
  if (e.stopPropagation) e.stopPropagation();
  
  if (draggedCard !== this && draggedCard && this.classList.contains('stats-card')) {
    const container = this.parentNode;
    const allCards = [...container.querySelectorAll('.stats-card')];
    const draggedIdx = allCards.indexOf(draggedCard);
    const targetIdx = allCards.indexOf(this);
    
    if (draggedIdx < targetIdx) {
      container.insertBefore(draggedCard, this.nextSibling);
    } else {
      container.insertBefore(draggedCard, this);
    }
    
    // Guardar nuevo orden
    guardarOrdenTarjetas(container);
  }
  
  this.classList.remove('drag-over');
  return false;
}

async function guardarOrdenTarjetas(container) {
  const orden = [...container.querySelectorAll('.stats-card')].map(c => c.id);
  const containerId = container.closest('.tab-content')?.id || 'ventas';
  const key = `cardOrder_${containerId}`;
  
  try {
    await fetch('/api/auth/preferencias', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ [key]: orden.join(',') })
    });
  } catch (e) {
    console.warn('No se pudo guardar orden:', e);
  }
}

function aplicarOrdenTarjetas(prefs) {
  ['tab-ventas', 'tab-gastos'].forEach(tabId => {
    const key = `cardOrder_${tabId}`;
    if (prefs[key]) {
      const orden = prefs[key].split(',');
      const container = document.querySelector(`#${tabId} .stats-container`);
      if (!container) return;
      
      orden.forEach(cardId => {
        const card = document.getElementById(cardId);
        if (card && card.parentNode === container) {
          container.appendChild(card);
        }
      });
    }
  });
}

document.addEventListener('DOMContentLoaded', async () => {
  const selectorFecha = document.getElementById('selector-fecha');
  if (selectorFecha && !selectorFecha.value) {
    const hoy = new Date();
    selectorFecha.value = hoy.toISOString().slice(0, 7);
  }

  // Recalcular estadísticas tanto al cambiar como al introducir un nuevo valor
  selectorFecha?.addEventListener('change', recargarEstadisticas);
  selectorFecha?.addEventListener('input', recargarEstadisticas);

  document.getElementById('btn-descargar-csv')?.addEventListener('click', descargarCSV);
  document.getElementById('btn-graficos')?.addEventListener('click', () => {
    // Detectar qué pestaña está activa
    const tabGastosContent = document.getElementById('tab-gastos');
    const tabVentasContent = document.getElementById('tab-ventas');
    
    if (tabGastosContent && tabGastosContent.classList.contains('active')) {
      console.log('[BTN GRAFICOS] Pestaña Gastos activa - Mostrando modal de gráficos mensuales');
      if (typeof window.abrirModalGraficosGastos === 'function') {
        window.abrirModalGraficosGastos();
      } else {
        console.error('[BTN GRAFICOS] Función abrirModalGraficosGastos no disponible');
      }
    } else if (tabVentasContent && tabVentasContent.classList.contains('active')) {
      console.log('[BTN GRAFICOS] Pestaña Ventas activa - Mostrando modal de ventas');
      abrirModalGraficos();
    } else {
      console.log('[BTN GRAFICOS] Ninguna pestaña activa detectada - Usando ventas por defecto');
      abrirModalGraficos();
    }
  });
  document.getElementById('cerrar-modal')?.addEventListener('click', (e) => {
    e.stopPropagation();
    const modal = document.getElementById('modal-graficos');
    if (modal) modal.style.display = 'none';
  });
  document.getElementById('tipo-datos')?.addEventListener('change', abrirModalGraficos);
  document.getElementById('vista-ventas')?.addEventListener('change', abrirModalGraficos);

  initModalDrag();
  initCollapseControls(); // Inicializar controles de colapso
  
  try {
    await recargarEstadisticas();
  } catch (e) {
    console.error('[estadisticas] Error inicial al recargar:', e);
  }
});
  
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
      // Al volver a la pestaña, forzamos la recarga de estadísticas
      // restableciendo la caché de mes/año para que se detecten los cambios
      ultimoMes = null;
      ultimoAnio = null;
      recargarEstadisticas();
    }
  });
  
  // ==============================
  // RELOAD GENERAL
  // ==============================
  let ultimoMes = null;
  let ultimoAnio = null;
  let ultimoDatos = null; // cache de último payload para cálculos globales
  async function recargarEstadisticas() {
    const { mes, anio } = getFechaSeleccionada();
    // Evitar llamadas innecesarias: solo si cambia mes o año
    if(mes === ultimoMes && anio === ultimoAnio) return;
    ultimoMes = mes; ultimoAnio = anio;
    safeSet('year-indicator', `(${anio})`);
    
    console.log('[RELOAD] Recargando estadísticas para:', mes, '/', anio);
    
    try {
      // Siempre recargar estadísticas de Ventas
      await Promise.all([
        cargarEstadisticas(mes, anio),
        cargarIngresosGastosTotales(mes, anio)
      ]);
      
      // Si la pestaña Gastos está activa, recargar sus datos también
      const tabGastosContent = document.getElementById('tab-gastos');
      const tabGastosBtn = document.querySelector('.tab[data-tab="gastos"]');
      
      if (tabGastosBtn && tabGastosBtn.classList.contains('active')) {
        console.log('[RELOAD] Recargando datos de pestaña Gastos (está activa)...');
        if (typeof window.cargarDatosGastos === 'function') {
          await window.cargarDatosGastos();
        } else {
          console.warn('[RELOAD] window.cargarDatosGastos no está disponible');
        }
      } else {
        console.log('[RELOAD] Pestaña Gastos no está activa, omitiendo recarga');
      }
    } catch (e) {
      console.error('[estadisticas] Fallo al cargar alguna sección:', e);
    }
  }
  
  function getFechaSeleccionada() {
    const selector = document.getElementById('selector-fecha');
    if (selector && selector.value) {
      const [anio, mes] = selector.value.split('-');
      return { mes, anio };
    }
    const hoy = new Date();
    return { mes: String(hoy.getMonth() + 1).padStart(2, '0'), anio: String(hoy.getFullYear()) };
  }
  
  // ==============================
  // HELPERS
  // ==============================

  // Asignación segura de textContent (evita errores si el elemento no existe)
  function safeSet(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }
  
  // Asignación de importe con color automático (verde/rojo)
  function safeSetAmount(id, value, rawAmount) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = value;
    // Aplicar clase de color según el valor
    el.classList.remove('amount-positive', 'amount-negative');
    if (rawAmount !== undefined && rawAmount !== null) {
      const numValue = typeof rawAmount === 'number' ? rawAmount : parsearImporte(rawAmount);
      if (numValue >= 0) {
        el.classList.add('amount-positive');
      } else {
        el.classList.add('amount-negative');
      }
    }
  }

  
  function formatearPorcentaje(valor) {
    const v = parseFloat(valor) || 0;
    return `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`;
  }
  
  function actualizarPorcentaje(id, val) {
    const el = document.getElementById(id);
    if (!el) return;
    if (val === null || val === undefined) {
      el.textContent = "N/A";
      el.className = 'stats-percentage';
      return;
    }
    el.textContent = formatearPorcentaje(val);
    el.className = 'stats-percentage ' + (val >= 0 ? 'positive' : 'negative');
  }
  
  function actualizarPorcentajeFaltaMediaMensual(valorId, porcentajeId, total, media, cardId = null) {
    const valorElem = document.getElementById(valorId);
    const porcentajeElem = document.getElementById(porcentajeId);
    if (!valorElem || !porcentajeElem) return; // si no existen salimos
    let card = cardId ? document.getElementById(cardId) : null;
    card?.classList.remove('stats-superado');
  
    if (!media || isNaN(media) || media === 0) {
      valorElem.textContent = formatearImporte(0);
      porcentajeElem.textContent = "0%";
      return;
    }
  
    const dif = media - total;
    if (dif > 0) {
      const p = (dif / media) * 100;
      valorElem.textContent = formatearImporte(dif);
      porcentajeElem.textContent = `${p.toFixed(1)}%`;
      porcentajeElem.className = 'stats-percentage negative';
    } else {
      const p = (Math.abs(dif) / media) * 100;
      valorElem.textContent = `¡Superado en ${p.toFixed(1)}%!`;
      porcentajeElem.textContent = `¡Superado en ${p.toFixed(1)}%!`;
      porcentajeElem.className = 'stats-percentage positive';
      card?.classList.add('stats-superado');
    }
  }
  
  // ==============================
  // CARGA ESTADISTICAS COMPLETAS
  // ==============================
  async function cargarEstadisticas(mes, anio) {
    const mesNum = parseInt(mes, 10); // 1-12
    const anioPrev = String(parseInt(anio, 10) - 1);
    
    const qp = new URLSearchParams({ mes, anio, t: Date.now() });
    
    // OPTIMIZACION: Carga paralela de todos los recursos necesarios al inicio
    // Esto evita el "waterfall" de peticiones y el parpadeo por actualizaciones parciales
    let datos, totalesActual, totalesAnterior;
    try {
        const [resMedia, resTotAct, resTotAnt] = await Promise.all([
            fetchConManejadorErrores(buildApiUrl('/api/ventas/media_por_documento?' + qp)).catch(() => null),
            fetchConManejadorErrores(buildApiUrl(`/api/ventas/total_mes?anio=${anio}&t=${Date.now()}`)).catch(() => null),
            fetchConManejadorErrores(buildApiUrl(`/api/ventas/total_mes?anio=${anioPrev}&t=${Date.now()}`)).catch(() => null)
        ]);
        datos = resMedia;
        totalesActual = resTotAct;
        totalesAnterior = resTotAnt;
    } catch (e) {
        console.error('[estadisticas] Error en carga paralela inicial:', e);
    }

    if (!datos) {
      console.warn('[estadisticas] Fallback: media_por_documento falló, voy a construir datos desde total_mes');
      // Pasamos los totales ya cargados
      datos = await construirDatosDesdeTotales(mes, anio, totalesActual, totalesAnterior);
    }
    // Si por cualquier motivo vino todo a 0, intentar reconstruir desde totales
    try {
      const totAct = (parsearImporte(datos?.tickets?.actual?.total) || 0) + (parsearImporte(datos?.facturas?.actual?.total) || 0);
      const esProd = IS_PROD;
      if (!esProd && (!datos || totAct === 0)) {
        console.warn('[estadisticas] Fallback 2: datos en 0, reconstruyendo desde total_mes');
        datos = await construirDatosDesdeTotales(mes, anio, totalesActual, totalesAnterior);
      }
    } catch (e) {
      console.warn('[estadisticas] Error evaluando fallback:', e);
    }

    // Simular que el mes seleccionado es el "mes actual" (aplicar SIEMPRE)
    // Ajustamos acumulados y medias usando series mensuales del backend (YTD)
    try {
      {
        // Usar datos pre-cargados si existen, si no, fetch (seguridad)
        const totales = totalesActual || await fetchConManejadorErrores(buildApiUrl(`/api/ventas/total_mes?anio=${anio}&t=${Date.now()}`));
        const totalesPrev = totalesAnterior || await fetchConManejadorErrores(buildApiUrl(`/api/ventas/total_mes?anio=${anioPrev}&t=${Date.now()}`));
        
        const keySel = String(mesNum).padStart(2, '0');
        const getCampoVal = (entry, campo) => {
          if (entry == null) return 0;
          if (typeof entry === 'number') {
            return campo === 'total' ? entry : 0;
          }
          return parsearImporte(entry?.[campo] ?? 0);
        };
        const sumHasta = (serie, campo) => {
          let s = 0;
          for (let i = 1; i <= mesNum; i++) {
            const k = String(i).padStart(2, '0');
            s += getCampoVal(serie?.[k], campo);
          }
          return s;
        };
        const valMes = (serie, campo) => getCampoVal(serie?.[keySel], campo);
        
        // Función para calcular total del trimestre del mes seleccionado
        const getTrimestreMeses = (mes, completo = false) => {
          const trimestre = Math.ceil(mes / 3);
          const inicio = (trimestre - 1) * 3 + 1;
          const fin = trimestre * 3;
          // completo=true para año anterior (trimestre completo), false para año actual (hasta mes actual)
          return { inicio, fin: completo ? fin : Math.min(fin, mes) };
        };
        const sumTrimestre = (serie, campo, completo = false) => {
          const { inicio, fin } = getTrimestreMeses(mesNum, completo);
          let s = 0;
          for (let i = inicio; i <= fin; i++) {
            const k = String(i).padStart(2, '0');
            s += getCampoVal(serie?.[k], campo);
          }
          return s;
        };

        // Tickets (año actual hasta el mes seleccionado)
        const tktTotalHasta = sumHasta(totales.tickets, 'total');
        const tktCantHasta  = sumHasta(totales.tickets, 'cantidad');
        const tktMesTotal   = valMes(totales.tickets, 'total');
        const tktMesCant    = valMes(totales.tickets, 'cantidad');
        datos.tickets.actual.total = tktTotalHasta;
        if (tktCantHasta > 0) {
          datos.tickets.actual.cantidad = tktCantHasta;
          datos.tickets.actual.media = tktTotalHasta / tktCantHasta;
        } else {
          // Mantener cantidades y media originales si no disponemos de cantidades en totales
          datos.tickets.actual.media = datos.tickets.actual.media;
        }
        datos.tickets.actual.mes_actual = {
          total: tktMesTotal,
          cantidad: (tktMesCant && tktMesCant > 0) ? tktMesCant : (datos.tickets.actual.mes_actual?.cantidad || 0)
        };
        // Tickets trimestre
        const tktTrimestreTotal = sumTrimestre(totales.tickets, 'total');
        const tktTrimestreTotalPrev = sumTrimestre(totalesPrev.tickets, 'total', true); // trimestre completo para año anterior
        datos.tickets.actual.trimestre = { total: tktTrimestreTotal };
        datos.tickets.anterior.mismo_trimestre = { total: tktTrimestreTotalPrev };
        datos.tickets.porcentaje_diferencia_trimestre = tktTrimestreTotalPrev > 0 ? ((tktTrimestreTotal - tktTrimestreTotalPrev) / tktTrimestreTotalPrev) * 100 : 0;
        // Tickets (año anterior - NO sobrescribir total anual, solo usar YTD para porcentaje)
        const tktTotalHastaPrev = sumHasta(totalesPrev.tickets, 'total');
        const tktCantHastaPrev  = sumHasta(totalesPrev.tickets, 'cantidad');
        // NO sobrescribir datos.tickets.anterior.total - mantener total ANUAL del backend
        if (tktCantHastaPrev > 0) {
          // datos.tickets.anterior.cantidad = tktCantHastaPrev; // Mantener cantidad anual
          datos.tickets.anterior.media = tktCantHastaPrev > 0 ? (tktTotalHastaPrev / tktCantHastaPrev) : (datos.tickets.anterior.media || 0);
        }
        // Porcentaje: % completado del objetivo anual (año anterior total)
        const tktTotalAnualPrev = datos.tickets.anterior?.total || tktTotalHastaPrev;
        datos.tickets.porcentaje_diferencia = tktTotalAnualPrev > 0 ? ((tktTotalHasta / tktTotalAnualPrev) * 100) - 100 : 0;
        // Media mensual año anterior (YTD hasta el mes seleccionado, excluyendo ese mes) para comparativa
        const tktMesTotalPrev = valMes(totalesPrev.tickets, 'total');
        datos.tickets.anterior.media_mensual = (mesNum - 1) > 0 ? (tktTotalHastaPrev - tktMesTotalPrev) / (mesNum - 1) : 0;

        // Facturas (año actual hasta el mes seleccionado)
        const facTotalHasta = sumHasta(totales.facturas, 'total');
        const facCantHasta  = sumHasta(totales.facturas, 'cantidad');
        const facMesTotal   = valMes(totales.facturas, 'total');
        const facMesCant    = valMes(totales.facturas, 'cantidad');
        datos.facturas.actual.total = facTotalHasta;
        if (facCantHasta > 0) {
          datos.facturas.actual.cantidad = facCantHasta;
          datos.facturas.actual.media = facTotalHasta / facCantHasta;
        } else {
          datos.facturas.actual.media = datos.facturas.actual.media;
        }
        datos.facturas.actual.mes_actual = {
          total: facMesTotal,
          cantidad: (facMesCant && facMesCant > 0) ? facMesCant : (datos.facturas.actual.mes_actual?.cantidad || 0)
        };
        // Facturas trimestre
        const facTrimestreTotal = sumTrimestre(totales.facturas, 'total');
        const facTrimestreTotalPrev = sumTrimestre(totalesPrev.facturas, 'total', true); // trimestre completo para año anterior
        datos.facturas.actual.trimestre = { total: facTrimestreTotal };
        datos.facturas.anterior.mismo_trimestre = { total: facTrimestreTotalPrev };
        datos.facturas.porcentaje_diferencia_trimestre = facTrimestreTotalPrev > 0 ? ((facTrimestreTotal - facTrimestreTotalPrev) / facTrimestreTotalPrev) * 100 : 0;
        // Facturas (año anterior - NO sobrescribir total anual, solo usar YTD para porcentaje)
        const facTotalHastaPrev = sumHasta(totalesPrev.facturas, 'total');
        const facCantHastaPrev  = sumHasta(totalesPrev.facturas, 'cantidad');
        // NO sobrescribir datos.facturas.anterior.total - mantener total ANUAL del backend
        if (facCantHastaPrev > 0) {
          // datos.facturas.anterior.cantidad = facCantHastaPrev; // Mantener cantidad anual
          datos.facturas.anterior.media = facCantHastaPrev > 0 ? (facTotalHastaPrev / facCantHastaPrev) : (datos.facturas.anterior.media || 0);
        }
        // Porcentaje: % completado del objetivo anual (año anterior total)
        const facTotalAnualPrev = datos.facturas.anterior?.total || facTotalHastaPrev;
        datos.facturas.porcentaje_diferencia = facTotalAnualPrev > 0 ? ((facTotalHasta / facTotalAnualPrev) * 100) - 100 : 0;
        // Media mensual año anterior (YTD hasta el mes seleccionado, excluyendo ese mes) para comparativa
        const facMesTotalPrev = valMes(totalesPrev.facturas, 'total');
        datos.facturas.anterior.media_mensual = (mesNum - 1) > 0 ? (facTotalHastaPrev - facMesTotalPrev) / (mesNum - 1) : 0;

        // Global: NO recalcular, usar el valor del backend (solo facturas cobradas)
        if (datos.global) {
          // Global trimestre: tickets + facturas cobradas (usar global del backend si existe)
          const globTrimestreTotal = (datos.global.actual?.trimestre?.total > 0)
            ? datos.global.actual.trimestre.total
            : (tktTrimestreTotal + facTrimestreTotal);
          const globTrimestreTotalPrev = (datos.global.anterior?.mismo_trimestre?.total > 0)
            ? datos.global.anterior.mismo_trimestre.total
            : (tktTrimestreTotalPrev + facTrimestreTotalPrev);
          datos.global.actual.trimestre = { total: globTrimestreTotal };
          datos.global.anterior.mismo_trimestre = { total: globTrimestreTotalPrev };
          datos.global.porcentaje_diferencia_trimestre = globTrimestreTotalPrev > 0 ? ((globTrimestreTotal - globTrimestreTotalPrev) / globTrimestreTotalPrev) * 100 : 0;
          // NO sobrescribir datos.global.actual.total ni datos.global.anterior.total
          // El backend ya los calcula con solo facturas cobradas
          if (datos.global.anterior?.media === undefined || datos.global.anterior?.media === 0) {
            const globCantHastaPrev = (tktCantHastaPrev || 0);
            datos.global.anterior.media = globCantHastaPrev > 0 ? (tktTotalHastaPrev / globCantHastaPrev) : 0;
          }
          // Porcentaje: usar los totales del backend (solo cobradas)
          const globTotalAnualPrev = datos.global.anterior?.total || 0;
          const globTotalActual = datos.global.actual?.total || 0;
          datos.global.porcentaje_diferencia = globTotalAnualPrev > 0 ? ((globTotalActual / globTotalAnualPrev) * 100) - 100 : 0;
          // Media mensual año anterior global
          datos.global.anterior.media_mensual = datos.global.anterior?.media_mensual || 0;
        }
      }
    } catch (e) {
      console.warn('No se pudo aplicar simulación local de mes actual en estadísticas:', e);
    }
    // --- Recalcular media mensual en el cliente ---
    function ajustarMediaMensual(obj){
      if(!obj || !obj.actual) return;
      const totalActual    = parsearImporte(obj.actual.total);
      const totalMesActual = parsearImporte(obj.actual.mes_actual?.total ?? 0);
      const mesesPrevios   = mesNum - 1;
      const totalPrevio    = totalActual - totalMesActual; // tras el ajuste local, esto ya es acumulado hasta mes-1
      obj.actual.media_mensual = mesesPrevios > 0 ? (totalPrevio / mesesPrevios) : 0;
    }
    ajustarMediaMensual(datos.tickets);
    ajustarMediaMensual(datos.facturas);
    if(datos.proformas) ajustarMediaMensual(datos.proformas);
    if(datos.global) ajustarMediaMensual(datos.global);
    // Completar cantidades del mes con la serie total_mes para garantizar media mensual correcta
    // Pasamos totalesActual para evitar fetch redundante
    await completarCantidadesMesDesdeTotales(mes, anio, datos, totalesActual);
    const global = datos.global;
    // cachear para cálculos globales de cantidad vs año pasado
    ultimoDatos = datos;
  
    actualizarStats('tickets', datos.tickets, 'card-tickets');
    actualizarStats('facturas', datos.facturas, 'card-facturas');
    // Solo actualizar proformas si la tarjeta existe
    if (document.getElementById('proformasTotal')) {
      actualizarStats('proformas', datos.proformas, 'card-proformas');
    }
    actualizarGlobal(global);
  
    // Cargar top clientes y productos desde un único endpoint del backend
    const topClientes = await fetchConManejadorErrores(buildApiUrl('/api/clientes/top_ventas?' + qp));
    actualizarTopClientes(topClientes);
    try {
      const topProductos = await fetchConManejadorErrores(buildApiUrl('/api/productos/top_ventas?' + qp));
      actualizarTopProductos(topProductos);
    } catch (errorTopProd) {
      console.warn('[estadisticas] Error cargando /productos/top_ventas, usando fallback del payload de clientes:', errorTopProd);
      if (topClientes && topClientes.productos) {
        actualizarTopProductos(topClientes);
      } else {
        const tbody = document.getElementById('topProductosBody');
        if (tbody) tbody.innerHTML = '<tr><td colspan="4">Sin datos</td></tr>';
      }
    }
    
    // Restaurar el estado de colapso de las tarjetas después de actualizar datos
    restaurarEstadoColapso();
  }

  // Construir estructura de "media_por_documento" a partir de /api/ventas/total_mes
  async function construirDatosDesdeTotales(mes, anio, totalesActualCache = null, totalesPrevCache = null) {
    const mesNum = parseInt(mes, 10);
    const anioPrev = String(parseInt(anio, 10) - 1);
    
    let totAct = totalesActualCache;
    let totPrev = totalesPrevCache;

    if (!totAct || !totPrev) {
      console.log('[estadisticas] Fetching totales en fallback (no caché)');
      const [resAct, resPrev] = await Promise.all([
        !totAct ? fetchConManejadorErrores(buildApiUrl(`/api/ventas/total_mes?anio=${anio}&t=${Date.now()}`)) : Promise.resolve(totAct),
        !totPrev ? fetchConManejadorErrores(buildApiUrl(`/api/ventas/total_mes?anio=${anioPrev}&t=${Date.now()}`)) : Promise.resolve(totPrev)
      ]);
      totAct = resAct;
      totPrev = resPrev;
    }

    const getCampoVal = (entry, campo) => {
      if (entry == null) return 0;
      if (typeof entry === 'number') return campo === 'total' ? entry : 0;
      return parsearImporte(entry?.[campo] ?? 0);
    };
    const sumHasta = (serie, campo) => {
      let s = 0, c = 0;
      for (let i = 1; i <= mesNum; i++) {
        const k = String(i).padStart(2,'0');
        const e = serie?.[k];
        s += getCampoVal(e, campo);
        if (campo === 'cantidad') c += getCampoVal(e, 'cantidad');
      }
      return campo === 'cantidad' ? (c || 0) : (s || 0);
    };
    const valMes = (serie, campo) => getCampoVal(serie?.[String(mesNum).padStart(2,'0')], campo);

    // Tickets
    const tTot = sumHasta(totAct.tickets, 'total');
    const tCnt = sumHasta(totAct.tickets, 'cantidad');
    const tMesT = valMes(totAct.tickets, 'total');
    const tMesC = valMes(totAct.tickets, 'cantidad');
    const tTotP = sumHasta(totPrev.tickets, 'total');
    const tCntP = sumHasta(totPrev.tickets, 'cantidad');

    // Facturas
    const fTot = sumHasta(totAct.facturas, 'total');
    const fCnt = sumHasta(totAct.facturas, 'cantidad');
    const fMesT = valMes(totAct.facturas, 'total');
    const fMesC = valMes(totAct.facturas, 'cantidad');
    const fTotP = sumHasta(totPrev.facturas, 'total');
    const fCntP = sumHasta(totPrev.facturas, 'cantidad');

    // Global: usar los datos del backend (solo facturas cobradas), no recalcular con facturas C+P+V
    const gTot = totAct.global ? Object.values(totAct.global).reduce((s, v) => s + (v.total || 0), 0) : tTot;
    const gTotP = totPrev.global ? Object.values(totPrev.global).reduce((s, v) => s + (v.total || 0), 0) : tTotP;

    const pct = (a, p) => p > 0 ? ((a - p) / p) * 100 : 0;

    let datos = {
      tickets: {
        actual: { total: tTot, cantidad: tCnt, media: tCnt>0? tTot/tCnt:0, mes_actual: { total: tMesT, cantidad: tMesC } },
        anterior: { total: tTotP, cantidad: tCntP, media: tCntP>0? tTotP/tCntP:0, mismo_mes: { total: valMes(totPrev.tickets,'total'), cantidad: valMes(totPrev.tickets,'cantidad') } },
        porcentaje_diferencia: pct(tTot, tTotP),
        porcentaje_diferencia_mes: pct(tMesT, valMes(totPrev.tickets,'total'))
      },
      facturas: {
        actual: { total: fTot, cantidad: fCnt, media: fCnt>0? fTot/fCnt:0, mes_actual: { total: fMesT, cantidad: fMesC } },
        anterior: { total: fTotP, cantidad: fCntP, media: fCntP>0? fTotP/fCntP:0, mismo_mes: { total: valMes(totPrev.facturas,'total'), cantidad: valMes(totPrev.facturas,'cantidad') } },
        porcentaje_diferencia: pct(fTot, fTotP),
        porcentaje_diferencia_mes: pct(fMesT, valMes(totPrev.facturas,'total'))
      },
      global: {
        actual: { total: gTot, cantidad: gCnt, media: gCnt>0? gTot/gCnt:0, mes_actual: { total: tMesT+fMesT, cantidad: tMesC+fMesC } },
        anterior: { total: gTotP, cantidad: gCntP, media: gCntP>0? gTotP/gCntP:0, mismo_mes: { total: valMes(totPrev.tickets,'total')+valMes(totPrev.facturas,'total'), cantidad: valMes(totPrev.tickets,'cantidad')+valMes(totPrev.facturas,'cantidad') } },
        porcentaje_diferencia: pct(gTot, gTotP),
        porcentaje_diferencia_mes: pct(tMesT+fMesT, valMes(totPrev.tickets,'total')+valMes(totPrev.facturas,'total'))
      }
    };
    // medias mensuales las ajustamos más adelante con ajustarMediaMensual()
    try {
      // Completar CANTIDADES desde media_por_documento si no tenemos cantidades en totales
      const md = await fetchConManejadorErrores(buildApiUrl('/api/ventas/media_por_documento?' + new URLSearchParams({ mes, anio })));
      const aplicarCant = (dst, src) => {
        if (!dst || !src) return;
        if (parsearImporte(dst.actual?.cantidad) <= 0 && parsearImporte(src.actual?.cantidad) > 0) {
          dst.actual.cantidad = src.actual.cantidad;
          dst.actual.media = parsearImporte(dst.actual.total) > 0 && parsearImporte(src.actual.cantidad) > 0
            ? parsearImporte(dst.actual.total) / parsearImporte(src.actual.cantidad)
            : dst.actual.media;
        }
        if (parsearImporte(dst.anterior?.cantidad) <= 0 && parsearImporte(src.anterior?.cantidad) > 0) {
          dst.anterior.cantidad = src.anterior.cantidad;
          dst.anterior.media = parsearImporte(dst.anterior.total) > 0 && parsearImporte(src.anterior.cantidad) > 0
            ? parsearImporte(dst.anterior.total) / parsearImporte(src.anterior.cantidad)
            : dst.anterior.media;
        }
        // Rellenar cantidad del MES si falta
        if (parsearImporte(dst.actual?.mes_actual?.cantidad) <= 0 && parsearImporte(src.actual?.mes_actual?.cantidad) > 0) {
          dst.actual.mes_actual.cantidad = src.actual.mes_actual.cantidad;
        }
        if (parsearImporte(dst.anterior?.mismo_mes?.cantidad) <= 0 && parsearImporte(src.anterior?.mismo_mes?.cantidad) > 0) {
          dst.anterior.mismo_mes.cantidad = src.anterior.mismo_mes.cantidad;
        }
      };
      aplicarCant(datos.tickets, md.tickets);
      aplicarCant(datos.facturas, md.facturas);
      // Global: NO recalcular con facturas C+P+V, el backend ya envía el global con solo cobradas
      // Solo completar cantidades si el backend no las envió
      if (!datos.global.actual.cantidad || datos.global.actual.cantidad === 0) {
        datos.global.actual.cantidad = parsearImporte(datos.tickets.actual.cantidad) || 0;
      }
      if (!datos.global.anterior.cantidad || datos.global.anterior.cantidad === 0) {
        datos.global.anterior.cantidad = parsearImporte(datos.tickets.anterior.cantidad) || 0;
      }
      datos.global.actual.media = (datos.global.actual.cantidad > 0) ? (parsearImporte(datos.global.actual.total) / datos.global.actual.cantidad) : datos.global.actual.media;
      datos.global.anterior.media = (datos.global.anterior.cantidad > 0) ? (parsearImporte(datos.global.anterior.total) / datos.global.anterior.cantidad) : datos.global.anterior.media;
      // Global: NO sobrescribir cantidades del mes con facturas C+P+V, el backend ya lo calcula con solo cobradas
    } catch (e) {
      console.warn('[estadisticas] No se pudieron completar cantidades desde media_por_documento:', e);
    }
    console.log('[estadisticas] Datos construidos desde total_mes:', datos);
    return datos;
  }
  
  // Completa las cantidades del mes seleccionado a partir de /api/ventas/total_mes
  // Esto asegura que la 'Media por Ticket/Factura' pueda calcularse como total_mes / cantidad_mes
  // incluso si el endpoint media_por_documento no envía la cantidad mensual.
  async function completarCantidadesMesDesdeTotales(mes, anio, datos, totalesActualCache = null) {
    try {
      const mesNum = parseInt(mes, 10);
      const keySel = String(mesNum).padStart(2, '0');
      
      let totales = totalesActualCache;
      if (!totales) {
          totales = await fetchConManejadorErrores(buildApiUrl(`/api/ventas/total_mes?anio=${anio}&t=${Date.now()}`));
      }
      
      const getCantidadMes = (serie) => {
        if (!serie) return 0;
        const entry = serie[keySel];
        if (entry == null) return 0;
        if (typeof entry === 'number') return 0; // cuando el backend devuelve sólo número para total
        return parsearImporte(entry.cantidad || 0);
      };
      const getTotalMes = (serie) => {
        if (!serie) return 0;
        const entry = serie[keySel];
        if (entry == null) return 0;
        if (typeof entry === 'number') return parsearImporte(entry);
        return parsearImporte(entry.total || 0);
      };
      const tMesCant = getCantidadMes(totales?.tickets);
      const fMesCant = getCantidadMes(totales?.facturas);
      const tMesTot  = getTotalMes(totales?.tickets);
      const fMesTot  = getTotalMes(totales?.facturas);
      // Asegurar estructura y aplicar sólo si hay dato positivo
      datos.tickets = datos.tickets || { actual: {} };
      datos.tickets.actual = datos.tickets.actual || {};
      datos.tickets.actual.mes_actual = datos.tickets.actual.mes_actual || {};
      // No sobrescribir con 0: si total_mes no trae cantidad, preservamos la previa (de media_por_documento)
      if (tMesCant > 0) {
        datos.tickets.actual.mes_actual.cantidad = tMesCant;
      }
      // Actualizar SIEMPRE total del mes seleccionado
      datos.tickets.actual.mes_actual.total = tMesTot;

      datos.facturas = datos.facturas || { actual: {} };
      datos.facturas.actual = datos.facturas.actual || {};
      datos.facturas.actual.mes_actual = datos.facturas.actual.mes_actual || {};
      if (fMesCant > 0) {
        datos.facturas.actual.mes_actual.cantidad = fMesCant;
      }
      datos.facturas.actual.mes_actual.total = fMesTot;

      // Global del mes seleccionado: usar el global del backend (solo facturas cobradas)
      datos.global = datos.global || { actual: {} };
      datos.global.actual = datos.global.actual || {};
      const gMesTotBackend = getTotalMes(totales?.global);
      const gMesCantBackend = getCantidadMes(totales?.global);
      datos.global.actual.mes_actual = {
        total: gMesTotBackend || ((tMesTot || 0) + (fMesTot || 0)),
        cantidad: gMesCantBackend || ((parsearImporte(datos.tickets.actual.mes_actual.cantidad)||0) + (parsearImporte(datos.facturas.actual.mes_actual.cantidad)||0))
      };
    } catch (e) {
      console.debug('[estadisticas] No se pudo completar cantidades del mes desde total_mes:', e);
    }
  }
  
  function restaurarEstadoColapso() {
    const prefs = _prefsCache || {};
    document.querySelectorAll('.stats-card').forEach(card => {
      const key = `statsHidden_${card.id}`;
      const hiddenSaved = prefs[key] === '1';
      setCardVisibility(card, hiddenSaved);
    });
    actualizarMenuTarjetasOcultas();
  }
  
  function actualizarStats(prefijo, data, cardId) {
    // Totales y medias ANUALES
    console.debug(`[stats] ${prefijo} antes de pintar`, {
      total: data?.actual?.total,
      cantidad: data?.actual?.cantidad,
      media: data?.actual?.media,
      mes_total: data?.actual?.mes_actual?.total,
      mes_cantidad: data?.actual?.mes_actual?.cantidad
    });
    safeSetAmount(`${prefijo}Total`, formatearImporte(data.actual.total), data.actual.total);
    let mediaValor = parsearImporte(data.actual.media);
    if (!mediaValor || mediaValor === 0) {
      const tot = parsearImporte(data.actual.total);
      const cant = parsearImporte(data.actual.cantidad || 0);
      if (cant > 0 && tot !== null) {
        mediaValor = tot / cant;
      } else {
        // Fallback: si no tenemos cantidad anual, usar media del mes si hay documentos en el mes
        const mesTot = parsearImporte(data.actual.mes_actual?.total || 0);
        const mesCant = parsearImporte(data.actual.mes_actual?.cantidad || 0);
        if (mesCant > 0 && mesTot !== null) mediaValor = mesTot / mesCant;
      }
    }
    safeSetAmount(`${prefijo}Media`, formatearImporte(mediaValor), mediaValor);
    // Datos del mes seleccionado
    const totalMesSeleccionado = data.actual.mes_actual?.total ?? 0;
    const cantidadMes = data.actual.mes_actual?.cantidad ?? 0;
    safeSetAmount(`${prefijo}MediaMensual`, formatearImporte(data.actual.media_mensual), data.actual.media_mensual);
    // Comparativa de medias vs año anterior
    {
      // 1) Media del mes seleccionado (coincide con el número grande mostrado) vs mismo mes año anterior
      const totMesC = parsearImporte(data.actual.mes_actual?.total || 0) || 0;
      const cantMesC = parsearImporte(data.actual.mes_actual?.cantidad || 0) || 0;
      const mediaMesActual = cantMesC > 0 ? (totMesC / cantMesC) : 0;
      const totMesAnt = parsearImporte(data.anterior?.mismo_mes?.total ?? 0) || 0;
      const cantMesAnt = parsearImporte(data.anterior?.mismo_mes?.cantidad ?? 0) || 0;
      const mediaMesAnt = cantMesAnt > 0 ? (totMesAnt / cantMesAnt) : 0;
      safeSet(`${prefijo}MediaMesAnterior`, `Mismo mes año anterior: ${formatearImporte(mediaMesAnt)}`);
      actualizarPorcentaje(`${prefijo}PorcentajeMediaMes`, (mediaMesAnt > 0 && cantMesC > 0) ? ((mediaMesActual - mediaMesAnt) / mediaMesAnt) * 100 : null);
      // 2) Media YTD (acumulado del año hasta hoy) vs año anterior hasta la misma fecha
      const mediaActualYTD = parsearImporte(data.actual?.media ?? 0);
      const mediaAntYTD = parsearImporte(data.anterior?.media ?? 0);
      safeSet(`${prefijo}MediaAnterior`, `Año anterior (hasta fecha): ${formatearImporte(mediaAntYTD)}`);
      actualizarPorcentaje(`${prefijo}PorcentajeMedia`, mediaAntYTD > 0 ? ((mediaActualYTD - mediaAntYTD) / mediaAntYTD) * 100 : null);
      // 3) Media mensual (promedio por mes) vs año anterior
      const mmActual = parsearImporte(data.actual?.media_mensual ?? 0);
      const mmAnt = parsearImporte(data.anterior?.media_mensual ?? 0);
      safeSet(`${prefijo}MediaMensualAnterior`, `Año anterior (hasta fecha): ${formatearImporte(mmAnt)}`);
      actualizarPorcentaje(`${prefijo}PorcentajeMediaMensual`, mmAnt > 0 ? ((mmActual - mmAnt) / mmAnt) * 100 : null);
    }
    // Cantidad debe ser del mes seleccionado (o 0 si no hay)
    safeSet(`${prefijo}Cantidad`, cantidadMes);
    safeSet(`${prefijo}Anterior`, `Año anterior: ${formatearImporte(data.anterior.total)}`);
    actualizarPorcentaje(`${prefijo}Porcentaje`, data.porcentaje_diferencia);
    // Año anterior hasta la misma fecha
    const anioHastaFechaTotal = data.anio_anterior_hasta_fecha?.total ?? 0;
    const anioHastaFechaDia = data.anio_anterior_hasta_fecha?.dia ?? '';
    safeSet(`${prefijo}AnioAnteriorHastaFecha`, `Año anterior (hasta fecha): ${formatearImporte(anioHastaFechaTotal)}`);
    actualizarPorcentaje(`${prefijo}PorcentajeAnioHastaFecha`, data.porcentaje_diferencia_anio_hasta_fecha);

    // Siempre actualizamos la fila del mes para evitar valores residuales
    const totalMes = totalMesSeleccionado;
    const cantMes = cantidadMes;
    // Recalcular y pintar la MEDIA: usar MES si hay datos; si no, fallback a YTD
    try {
      const totMesNum = parsearImporte(totalMes) || 0;
      const cantMesNum = parsearImporte(cantMes) || 0;
      const totAcumNum = parsearImporte(data.actual.total) || 0;
      const cantAcumNum = parsearImporte(data.actual.cantidad || 0) || 0;
      let mediaPreferida = 0;
      if (cantMesNum > 0) {
        mediaPreferida = totMesNum / cantMesNum;
      } else if (cantAcumNum > 0) {
        mediaPreferida = totAcumNum / cantAcumNum;
      }
      console.debug(`[stats] ${prefijo} media recalculada (Mes→YTD)`, { mediaPreferida, totMesNum, cantMesNum, totAcumNum, cantAcumNum });
      safeSetAmount(`${prefijo}Media`, formatearImporte(mediaPreferida), mediaPreferida);
    } catch (e) {
      console.warn(`[stats] ${prefijo} no se pudo recalcular media`, e);
    }
    safeSetAmount(`${prefijo}TotalMes`, formatearImporte(totalMes), totalMes);
    const mesAnteriorTotal = data.anterior?.mismo_mes?.total ?? 0;
    safeSet(`${prefijo}MesAnterior`, `Mismo mes año anterior: ${formatearImporte(mesAnteriorTotal)}`);
    // Mismo mes año anterior hasta el día actual
    const hastaDiaTotal = data.mismo_mes_hasta_dia?.total ?? 0;
    const hastaDiaDia = data.mismo_mes_hasta_dia?.dia ?? '';
    safeSet(`${prefijo}MesAnteriorHastaDia`, `Mismo mes año anterior (hasta día ${hastaDiaDia}): ${formatearImporte(hastaDiaTotal)}`);
    actualizarPorcentaje(`${prefijo}PorcentajeMesHastaDia`, data.porcentaje_diferencia_mes_hasta_dia);
    
    // Total Trimestre
    const totalTrimestre = data.actual?.trimestre?.total ?? 0;
    const trimestreAnteriorTotal = data.anterior?.mismo_trimestre?.total ?? 0;
    safeSetAmount(`${prefijo}TotalTrimestre`, formatearImporte(totalTrimestre), totalTrimestre);
    safeSet(`${prefijo}TrimestreAnterior`, `Mismo trimestre año anterior: ${formatearImporte(trimestreAnteriorTotal)}`);
    actualizarPorcentaje(`${prefijo}PorcentajeTrimestre`, data.porcentaje_diferencia_trimestre);

    if (cantMes) {
      safeSetAmount(`${prefijo}TotalMes`, formatearImporte(data.actual.mes_actual.total), data.actual.mes_actual.total);
      safeSet(`${prefijo}MesAnterior`, `Mismo mes año anterior: ${formatearImporte(mesAnteriorTotal)}`);
      actualizarPorcentaje(`${prefijo}PorcentajeMes`, data.porcentaje_diferencia_mes);
      actualizarPorcentajeFaltaMediaMensual(
        `${prefijo}FaltaMediaMensual`,
        `${prefijo}PorcentajeFalta`,
        parsearImporte(data.actual.mes_actual.total),
        parsearImporte(data.actual.media_mensual),
        cardId
      );
      // Porcentaje de CANTIDAD respecto al mismo mes del año pasado
      const cantMesAnterior = data.anterior?.mismo_mes?.cantidad ?? null;
      const idPct = `${prefijo}CantidadPctMes`;
      if (cantMesAnterior && cantMesAnterior > 0) {
        const pctCant = ((cantMes - cantMesAnterior) / cantMesAnterior) * 100;
        actualizarPorcentaje(idPct, pctCant);
      } else {
        const el = document.getElementById(idPct);
        if (el) { el.textContent = 'N/A'; el.className = 'stats-percentage'; }
      }
    }
  }
  
  function actualizarGlobal(global) {
    if (!global) return;
    console.debug('[stats] global antes de pintar', {
      total: global?.actual?.total,
      cantidad: global?.actual?.cantidad,
      media: global?.actual?.media,
      mes_total: global?.actual?.mes_actual?.total,
      mes_cantidad: global?.actual?.mes_actual?.cantidad
    });
    safeSetAmount('globalTotal', formatearImporte(global.actual.total), global.actual.total);
    let globalMedia = parsearImporte(global.actual.media);
    if (!globalMedia || globalMedia === 0) {
      const tot = parsearImporte(global.actual.total);
      const cant = parsearImporte(global.actual.cantidad || 0);
      if (cant > 0 && tot !== null) {
        globalMedia = tot / cant;
      } else {
        const mesTot = parsearImporte(global.actual.mes_actual?.total || 0);
        const mesCant = parsearImporte(global.actual.mes_actual?.cantidad || 0);
        if (mesCant > 0 && mesTot !== null) globalMedia = mesTot / mesCant;
      }
    }
    safeSetAmount('globalMedia', formatearImporte(globalMedia), globalMedia);
    safeSetAmount('globalMediaMensual', formatearImporte(global.actual.media_mensual), global.actual.media_mensual);
    // Comparativa de medias global vs año anterior
    {
      // 1) Media del mes seleccionado vs mismo mes año anterior
      const gTotMesC = parsearImporte(global.actual.mes_actual?.total || 0) || 0;
      const gCantMesC = parsearImporte(global.actual.mes_actual?.cantidad || 0) || 0;
      const gMediaMesAct = gCantMesC > 0 ? (gTotMesC / gCantMesC) : 0;
      const gTotMesAnt = parsearImporte(global.anterior?.mismo_mes?.total ?? 0) || 0;
      const gCantMesAnt = parsearImporte(global.anterior?.mismo_mes?.cantidad ?? 0) || 0;
      const gMediaMesAnt = gCantMesAnt > 0 ? (gTotMesAnt / gCantMesAnt) : 0;
      safeSet('globalMediaMesAnterior', `Mismo mes año anterior: ${formatearImporte(gMediaMesAnt)}`);
      actualizarPorcentaje('globalPorcentajeMediaMes', (gMediaMesAnt > 0 && gCantMesC > 0) ? ((gMediaMesAct - gMediaMesAnt) / gMediaMesAnt) * 100 : null);
      // 2) Media YTD (acumulado del año hasta hoy) vs año anterior hasta la misma fecha
      const gMediaAct = parsearImporte(global.actual?.media ?? 0);
      const gMediaAnt = parsearImporte(global.anterior?.media ?? 0);
      safeSet('globalMediaAnterior', `Año anterior (hasta fecha): ${formatearImporte(gMediaAnt)}`);
      actualizarPorcentaje('globalPorcentajeMedia', gMediaAnt > 0 ? ((gMediaAct - gMediaAnt) / gMediaAnt) * 100 : null);
      const gMMAct = parsearImporte(global.actual?.media_mensual ?? 0);
      const gMMAnt = parsearImporte(global.anterior?.media_mensual ?? 0);
      safeSet('globalMediaMensualAnterior', `Año anterior (hasta fecha): ${formatearImporte(gMMAnt)}`);
      actualizarPorcentaje('globalPorcentajeMediaMensual', gMMAnt > 0 ? ((gMMAct - gMMAnt) / gMMAnt) * 100 : null);
    }
    document.getElementById('globalCantidad').textContent = global.actual.cantidad;
    document.getElementById('globalAnterior').textContent = `Año anterior: ${formatearImporte(global.anterior.total)}`;
    actualizarPorcentaje('globalPorcentaje', global.porcentaje_diferencia);
    // Año anterior hasta la misma fecha (global)
    const globalAnioHastaFechaTotal = global.anio_anterior_hasta_fecha?.total ?? 0;
    safeSet('globalAnioAnteriorHastaFecha', `Año anterior (hasta fecha): ${formatearImporte(globalAnioHastaFechaTotal)}`);
    actualizarPorcentaje('globalPorcentajeAnioHastaFecha', global.porcentaje_diferencia_anio_hasta_fecha);
    
    // Total Trimestre Global
    const totalTrimestreGlobal = global.actual?.trimestre?.total ?? 0;
    const trimestreAnteriorGlobal = global.anterior?.mismo_trimestre?.total ?? 0;
    safeSetAmount('globalTotalTrimestre', formatearImporte(totalTrimestreGlobal), totalTrimestreGlobal);
    safeSet('globalTrimestreAnterior', `Mismo trimestre año anterior: ${formatearImporte(trimestreAnteriorGlobal)}`);
    actualizarPorcentaje('globalPorcentajeTrimestre', global.porcentaje_diferencia_trimestre);
  
    const mediaMensual = parsearImporte(global.actual.media_mensual);
    // Usar siempre el mes seleccionado para que el cálculo de previsto sea coherente con el periodo mostrado
    const { mes: mesSel, anio: anioSel } = getFechaSeleccionada();
    const mesActual = parseInt(mesSel, 10);
    const anioActual = parseInt(anioSel, 10);
    const acumulado = parsearImporte(global.actual.total);

    const now = new Date();
    const esPeriodoActual = (anioActual === now.getFullYear()) && (mesActual === (now.getMonth() + 1));

    let previsto = acumulado + (mediaMensual * (12 - mesActual));
    // Si estamos en diciembre (mes actual) el acumulado suele ser parcial: estimar el cierre de diciembre.
    // - Proyección por ritmo diario del propio diciembre (si aún no ha terminado el mes)
    // - Y como mínimo, la media de enero-noviembre
    if (esPeriodoActual && mesActual === 12) {
      const totalMes = parsearImporte(global.actual.mes_actual?.total || 0) || 0;
      const acumSinMes = (parsearImporte(acumulado) || 0) - totalMes;
      const mediaHasta11 = acumSinMes > 0 ? (acumSinMes / 11) : 0;

      const diaMes = Math.max(1, now.getDate());
      const diasMes = new Date(anioActual, 12, 0).getDate();
      let proyeccionDiciembre = totalMes;
      if (diaMes < diasMes && totalMes > 0) {
        proyeccionDiciembre = totalMes * (diasMes / diaMes);
      }
      if (mediaHasta11 > 0) {
        proyeccionDiciembre = Math.max(proyeccionDiciembre, mediaHasta11);
      }
      previsto = acumSinMes + proyeccionDiciembre;
    }
    safeSetAmount('globalTotalPrevisto', formatearImporte(previsto), previsto);
  
    // Evitar división por cero que causa NaN
    let p = 0;
    if (previsto > 0) {
        p = (acumulado / previsto) * 100;
    } else if (acumulado > 0) {
        p = 100; // Si hay acumulado pero no previsto, mostrar 100%
    }
    const diff = p >= 100 ? p - 100 : 100 - p;
    const porcentajeElem = document.getElementById('globalPorcentajePrevistoAnyo');
    if (porcentajeElem) {
        porcentajeElem.textContent = `${p >= 100 ? '+' : '-'}${diff.toFixed(1)}%`;
        porcentajeElem.className = 'stats-percentage ' + (p >= 100 ? 'positive' : 'negative');
    }
  
    // Mostrar SIEMPRE los valores del mes, aunque la cantidad sea 0
    safeSetAmount('globalTotalMes', formatearImporte(global.actual.mes_actual?.total || 0), global.actual.mes_actual?.total || 0);
    document.getElementById('globalMesAnterior').textContent = `Mismo mes año anterior: ${formatearImporte(global.anterior.mismo_mes?.total || 0)}`;
    actualizarPorcentaje('globalPorcentajeMes', global.porcentaje_diferencia_mes);
    // Mismo mes año anterior hasta el día actual (global)
    const globalHastaDiaTotal = global.mismo_mes_hasta_dia?.total ?? 0;
    const globalHastaDiaDia = global.mismo_mes_hasta_dia?.dia ?? '';
    safeSet('globalMesAnteriorHastaDia', `Mismo mes año anterior (hasta día ${globalHastaDiaDia}): ${formatearImporte(globalHastaDiaTotal)}`);
    actualizarPorcentaje('globalPorcentajeMesHastaDia', global.porcentaje_diferencia_mes_hasta_dia);
    actualizarPorcentajeFaltaMediaMensual(
      'globalFaltaMediaMensual',
      'globalPorcentajeFalta',
      parsearImporte(global.actual.mes_actual?.total || 0),
      parsearImporte(global.actual.media_mensual || 0),
      'card-global'
    );
    // Porcentaje de CANTIDAD GLOBAL respecto al año pasado (total anual)
    const idPctGlobalCant = 'globalCantidadPctAnyo';
    const cantActual = global?.actual?.cantidad ?? null;
    let cantAnterior = global?.anterior?.cantidad;
    if ((cantAnterior === undefined || cantAnterior === null) && ultimoDatos) {
      const tAnt = ultimoDatos?.tickets?.anterior?.cantidad ?? 0;
      const fAnt = ultimoDatos?.facturas?.anterior?.cantidad ?? 0;
      cantAnterior = tAnt + fAnt;
    }
    if (cantActual !== null && cantAnterior && cantAnterior > 0) {
      const pct = ((cantActual - cantAnterior) / cantAnterior) * 100;
      actualizarPorcentaje(idPctGlobalCant, pct);
    } else {
      const el = document.getElementById(idPctGlobalCant);
      if (el) { el.textContent = 'N/A'; el.className = 'stats-percentage'; }
    }
  }
  
  // ==============================
  // TOPS
  // ==============================
  function actualizarTopClientes(datos) {
    const tbody = document.getElementById('topClientesBody');
    if(!tbody) return;
    tbody.innerHTML = '';
    datos.clientes.forEach(c => {
      const tr = document.createElement('tr');
      tr.classList.add('top-cliente-row');
      const clienteId   = c.id ?? c.cliente_id ?? c.clienteID ?? '';
      tr.dataset.id     = clienteId;
      tr.dataset.nombre = c.nombre;
      tr.innerHTML = `<td title="${c.nombre}">${c.nombre.slice(0,15)}${c.nombre.length>15?'...':''}</td>
        <td>${formatearImporte(c.total_actual)}</td>
        <td class="${c.porcentaje_diferencia>=0?'positive':'negative'}">${formatearPorcentaje(c.porcentaje_diferencia)}</td>`;
      tr.style.cursor = 'pointer';
      tr.addEventListener('click', () => abrirGraficoCliente(clienteId, c.nombre));
      tbody.appendChild(tr);
    });
  }
  
  function actualizarTopProductos(datos) {
    const tbody = document.getElementById('topProductosBody');
    if(!tbody) return;
    tbody.innerHTML = '';
    datos.productos.forEach(p => {
      const tr = document.createElement('tr');
      tr.classList.add('top-producto-row');
      const prodId = p.id ?? p.producto_id ?? '';
      tr.dataset.id = prodId;
      tr.dataset.nombre = p.nombre;
      const cantFmt = Number(p.cantidad_actual || 0).toLocaleString('es-ES');
      tr.innerHTML = `<td title="${p.nombre}">${p.nombre.slice(0,28)}${p.nombre.length>28?'...':''}</td>
        <td title="${cantFmt}" style="white-space:nowrap;">${cantFmt}</td>
        <td>${formatearImporte(p.total_actual)}</td>
        <td class="${p.porcentaje_diferencia>=0?'positive':'negative'}">${formatearPorcentaje(p.porcentaje_diferencia)}</td>`;
      tr.style.cursor = 'pointer';
      tr.addEventListener('click', () => {
        console.log('[TOP PRODUCTOS] Click en producto:', prodId, p.nombre);
        abrirGraficoProducto(prodId, p.nombre);
      });
      tbody.appendChild(tr);
    });
  }
  
  // ==============================
  // INGRESOS & GASTOS TOTALES
  // ==============================
  async function cargarIngresosGastosTotales(mes, anio){
    if (mes === undefined || anio === undefined) {
      const fecha = getFechaSeleccionada();
      mes = fecha.mes;
      anio = fecha.anio;
    }
    const gastoEmpresa = window.getGastoEmpresaParam ? window.getGastoEmpresaParam() : '1';
    const data = await fetchConManejadorErrores(buildApiUrl(`/api/ingresos_gastos_totales?anio=${anio}&mes=${mes}&gasto_empresa=${gastoEmpresa}&t=${Date.now()}`));
    const ingresos = data.ingresos;
    const gastos   = data.gastos;
    const ingresosEl = document.getElementById('ig-total-ingresos');
    const gastosEl   = document.getElementById('ig-total-gastos');
    if(ingresosEl) {
      ingresosEl.textContent = formatearImporte(ingresos.total_actual);
      ingresosEl.classList.remove('amount-positive', 'amount-negative');
      ingresosEl.classList.add('amount-positive');
    }
    if(gastosEl) {
      gastosEl.textContent = formatearImporte(Math.abs(gastos.total_actual));
      gastosEl.classList.remove('amount-positive', 'amount-negative');
      gastosEl.classList.add('amount-negative');
    }
    
    // Mostrar la última actualización con fecha y hora
    const ultimaActualizacionEl = document.getElementById('ig-ultima-actualizacion');
    if(ultimaActualizacionEl && data.ultima_actualizacion) {
      if(data.ultima_actualizacion_completa) {
        // Si tenemos la fecha y hora completa, la mostramos directamente
        ultimaActualizacionEl.textContent = data.ultima_actualizacion_completa;
      } else {
        // Mantener compatibilidad con el formato anterior DD/MM/AAAA
        const fechaPartes = data.ultima_actualizacion.split('/');
        if(fechaPartes.length === 3) {
          const fechaObj = new Date(`${fechaPartes[2]}-${fechaPartes[1]}-${fechaPartes[0]}T00:00:00`);
          ultimaActualizacionEl.textContent = formatearFecha(fechaObj);
        } else {
          ultimaActualizacionEl.textContent = data.ultima_actualizacion;
        }
      }
    } else if(ultimaActualizacionEl) {
      ultimaActualizacionEl.textContent = 'No hay datos';
    }

    // ---- Balance ----
    const balanceValor = ingresos.total_actual - Math.abs(gastos.total_actual);

    const balanceEl = document.getElementById('kpi-balance-mes-actual');
    if(balanceEl){
      balanceEl.textContent = formatearImporte(balanceValor);
      balanceEl.classList.remove('amount-positive','amount-negative');
      balanceEl.classList.add(balanceValor>=0 ? 'amount-positive' : 'amount-negative');
    }

    const balTotalEl = document.getElementById('ig-total-balance');
    if(balTotalEl){
      balTotalEl.textContent = formatearImporte(balanceValor);
      balTotalEl.classList.remove('amount-positive','amount-negative');
      balTotalEl.classList.add(balanceValor>=0 ? 'amount-positive' : 'amount-negative');
    }

    // Porcentajes
    actualizarPorcentaje('ig-pct-ingresos', ingresos.porcentaje_diferencia);
    actualizarPorcentaje('ig-pct-gastos',   -gastos.porcentaje_diferencia); // gastos mayores => negativo
  }

  // ==============================
  // GRAFICO CLIENTE
  async function abrirGraficoCliente(clienteId, nombre){
    if(!clienteId) return;
    await asegurarChartJs();
    const { anio } = getFechaSeleccionada();
    // Ocultar selector tipo-datos para gráfico por cliente
    const cc = document.querySelector('.chart-controls');
    if(cc) cc.style.display = 'none';
    const modal = document.getElementById('modal-graficos');
    if(modal) modal.style.display = 'block';
    // Obtener datos mensuales del cliente
    const datos = await fetchConManejadorErrores(buildApiUrl(`/api/clientes/ventas_mes?cliente_id=${clienteId}&anio=${anio}`));
    const meses = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
    const valores = meses.map((_, i) => parsearImporte(datos[String(i+1).padStart(2,'0')]));

    const datasets = [{ label: `${nombre} ${anio}`, data: valores, backgroundColor: '#3498db' }];
    if(chartEstadisticas) { chartEstadisticas.destroy(); chartEstadisticas = null; }
    if(chartCliente) chartCliente.destroy();
    if(chartProducto) { chartProducto.destroy(); chartProducto = null; }

    chartCliente = new Chart(document.getElementById('chart-estadisticas').getContext('2d'), {
      type: 'bar',
      data: { labels: meses, datasets },
      options: {
        responsive: true,
        scales: {
          y: { beginAtZero: true },
          // Eje secundario para cantidades
          y2: {
            beginAtZero: true,
            position: 'right',
            grid: { drawOnChartArea: false },
            ticks: { stepSize: 1 }
          }
        },
        plugins: {
          barLabelsCounts: { counts: countsForBars }
        }
      },
      plugins: [barLabelsPlugin]
    });
    // Asegurar redimensionado tras mostrar el modal
    setTimeout(() => { try { chartCliente.resize(); } catch(e){} }, 50);
  }

  // ==============================
  // GRAFICO PRODUCTO
  async function abrirGraficoProducto(productoId, nombre){
    console.log('[GRAFICO PRODUCTO] Abriendo gráfico para:', productoId, nombre);
    if(!productoId) { console.log('[GRAFICO PRODUCTO] productoId vacío, saliendo'); return; }
    await asegurarChartJs();
    const { anio } = getFechaSeleccionada();
    const cc = document.querySelector('.chart-controls');
    if(cc) cc.style.display = 'none';
    const modal = document.getElementById('modal-graficos');
    if(modal) modal.style.display = 'block';

    const datos = await fetchConManejadorErrores(buildApiUrl(`/api/productos/ventas_mes?producto_id=${productoId}&anio=${anio}`));
    const meses = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
    const valores = meses.map((_, i) => parsearImporte(datos[String(i+1).padStart(2,'0')]));

    if(chartEstadisticas) { chartEstadisticas.destroy(); chartEstadisticas = null; }
    if(chartCliente) { chartCliente.destroy(); chartCliente = null; }
    if(chartProducto) chartProducto.destroy();

    // Preparar datasets para cantidades y euros
    const cantidades = meses.map((_, i) => parsearImporte((datos.cantidad||{})[String(i+1).padStart(2,'0')]));
    const eurosVals  = meses.map((_, i) => parsearImporte((datos.euros||{})[String(i+1).padStart(2,'0')]));

    chartProducto = new Chart(document.getElementById('chart-estadisticas').getContext('2d'), {
      type: 'bar',
      data: { labels: meses, datasets: [
          { label: 'Cantidad', data: cantidades, backgroundColor: '#f1c40f', yAxisID: 'y' },
          { label: 'Euros (€)', data: eurosVals, backgroundColor: '#2ecc71', yAxisID: 'y1' }
        ] },
      options: {
        responsive: true,
        scales: {
          y: { beginAtZero: true },
          y1: { beginAtZero: true, position: 'right', grid: { drawOnChartArea: false } }
        }
      }
    });
    setTimeout(() => { try { chartProducto.resize(); } catch(e){} }, 50);
  }

  // ==============================
  // TOP GASTOS
  // ==============================
  async function cargarTopGastos(anio) {
    const datos = await fetchConManejadorErrores(buildApiUrl(`/api/gastos/top_gastos?anio=${anio}&t=${Date.now()}`));
    actualizarTopGastos(datos);
  }
  
  function actualizarTopGastos(datos) {
    const tbody = document.getElementById('topGastosBody');
    if (!tbody) return;
    tbody.innerHTML = '';
    datos.gastos.forEach(g => {
      tbody.innerHTML += `<tr><td title="${g.concepto}">${g.concepto.slice(0,25)}${g.concepto.length>25?'...':''}</td>
        <td>${formatearImporte(g.total_actual)}</td>
        <td class="${g.porcentaje_diferencia>=0?'positive':'negative'}">${formatearPorcentaje(g.porcentaje_diferencia)}</td></tr>`;
    });
  }
  
  // ==============================
  // EXTRACTO BANCO (ELIMINADO)
  // ==============================
  /* async function cargarKpiGastos(mes, anio) {
    const data = await fetchConManejadorErrores(buildApiUrl(`/api/estadisticas_gastos?mes=${mes}&anio=${anio}&t=${Date.now()}`));
    // Función auxiliar para aplicar formato y clases a los importes
    function actualizarImporteKpi(idElemento, valor) {
      const elemento = document.getElementById(idElemento);
      if (elemento) {
        elemento.textContent = formatearImporte(valor);
        elemento.className = ''; // Limpiar clases existentes
        if (parsearImporte(valor) >= 0) {
          elemento.classList.add('amount-positive');
        } else {
          elemento.classList.add('amount-negative');
        }
      }
    }

    actualizarImporteKpi('kpi-ingresos-mes-actual', data.ingresos_mes_actual);
    actualizarImporteKpi('kpi-gastos-mes-actual', data.gastos_mes_actual);
    actualizarImporteKpi('kpi-balance-mes-actual', data.balance_mes_actual);
    
    // El saldo puede ser 'No disponible' o similar, por eso lo manejamos aparte si es necesario, o lo incluimos en la función si el valor siempre es numérico.
    // Para simplificar, asumimos que saldo_mes_actual siempre es numérico o null/undefined
    actualizarImporteKpi('kpi-saldo-mes-actual', data.saldo_mes_actual); 
    const actualizacion = document.getElementById('kpi-ultima-actualizacion');
    actualizacion.innerHTML = `<strong>${formatearFecha(data.ultima_actualizacion) || 'No disponible'}</strong>`;
  } */
  
  // ==============================
  // CSV
  // ==============================
  async function descargarCSV() {
    const { anio, mes } = getFechaSeleccionada();
    const meses = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
    const datos = await fetchConManejadorErrores(buildApiUrl(`/api/ventas/total_mes?anio=${anio}`));
    const SEP = ';';
    const fila = (tipo, arr) => [tipo, ...arr.map(n => n.toFixed(2).replace('.', ',')), arr.reduce((a,b) => a+b,0).toFixed(2).replace('.', ',')].join(SEP);
    const get = t => meses.map((_,i) => parsearImporte(datos[t][String(i+1).padStart(2,'0')]));
  
    const csv = [`Año${SEP}${anio}`, `Generado${SEP}${new Date().toLocaleString('es-ES')}`,
      '', `Concepto${SEP}${meses.join(SEP)}${SEP}Total`,
      fila('Tickets', get('tickets')),
      fila('Facturas', get('facturas')),
      fila('Global', get('global'))].join('\n');
  
    const link = document.createElement('a');
    link.href = URL.createObjectURL(new Blob([csv], {type:'text/csv'}));
    link.download = `estadisticas_${anio}.csv`;
    link.click();
  }
  
  // ==============================
  // MODAL DRAG
  // ==============================
  function initModalDrag(){
    const dialog = document.querySelector('#modal-graficos .modal-content');
    if(!dialog) return;
    let isDragging = false, startX, startY, initialLeft, initialTop;
  
    dialog.addEventListener('mousedown', e => {
      // SOLO iniciar drag si se clickea directamente en modal-content (no en hijos)
      if(e.target !== dialog) return;
      isDragging = true;
      startX = e.clientX; startY = e.clientY;
      const rect = dialog.getBoundingClientRect();
      initialLeft = rect.left; initialTop = rect.top;
      dialog.style.transform = 'none';
      dialog.style.left = `${initialLeft}px`;
      dialog.style.top = `${initialTop}px`;
      document.body.style.userSelect = 'none';
    });
  
    document.addEventListener('mousemove', e => {
      if(!isDragging) return;
      dialog.style.left = `${initialLeft + e.clientX - startX}px`;
      dialog.style.top = `${initialTop + e.clientY - startY}px`;
    });
  
    document.addEventListener('mouseup', () => {
      isDragging = false;
      document.body.style.userSelect = '';
    });
  }
  
  // ==============================
  // MODAL GRAFICOS
  // ==============================
  let chartEstadisticas = null;
  let chartCliente = null;
  let chartProducto = null;
  // Hoisted to avoid ReferenceError in abrirGraficoCliente when referenced in options
  let countsForBars = null;
  
  // Plugin global para dibujar etiquetas con CANTIDAD sobre cada barra
  // Lee counts desde options.plugins.barLabelsCounts.counts
  const barLabelsPlugin = {
    id: 'barLabelsCounts',
    afterDatasetsDraw(chart, args, pluginOptions){
      const cfg = chart.options.plugins?.barLabelsCounts;
      const counts = cfg?.counts;
      if (!counts || !Array.isArray(counts)) return;
      const { ctx } = chart;
      ctx.save();
      ctx.textAlign = 'center';
      ctx.textBaseline = 'bottom';
      ctx.fillStyle = '#333';
      ctx.font = '10px sans-serif';
      const meta = chart.getDatasetMeta(0);
      meta.data.forEach((bar, i) => {
        const val = counts[i];
        if (val === null || val === undefined) return;
        const txt = String(val);
        const pos = bar.tooltipPosition();
        ctx.fillText(txt, pos.x, pos.y - 4);
      });
      ctx.restore();
    }
  };
  
  async function abrirModalGraficos() {
    // Limpiar duplicados del modal si existen (bug de DOM corrupto)
    const allModals = document.querySelectorAll('#modal-graficos');
    if (allModals.length > 1) {
      console.warn(`[MODAL] Detectados ${allModals.length} modales duplicados, limpiando...`);
      for (let i = 1; i < allModals.length; i++) {
        allModals[i].remove();
      }
    }
    
    // Si existe gráfico de cliente, destruirlo antes de crear el general
    if (chartCliente) { chartCliente.destroy(); chartCliente = null; }
    if (chartProducto) { chartProducto.destroy(); chartProducto = null; }
    // Mostrar controles al abrir gráfico general
    const cc2 = document.querySelector('.chart-controls');
    if(cc2) cc2.style.display = 'block';
    await asegurarChartJs();
    const { anio, mes } = getFechaSeleccionada();
    const tipo = document.getElementById('tipo-datos').value;
    const vista = document.getElementById('vista-ventas')?.value || 'mensual';
    const anioAnterior = anio - 1;

    // === Vista por Semanas (líneas, comparativa con año anterior) ===
    if (vista === 'semanal') {
      const datosSem = await fetchConManejadorErrores(buildApiUrl(`/api/ventas/total_semana?anio=${anio}`));
      const semHasta = datosSem.semana_hasta;
      const semAnterior = datosSem.semanas_anio_anterior;
      const semAnteriorHastaFecha = datosSem.semana_hasta_anterior ?? semAnterior;
      const totalAnteriorHastaFecha = datosSem.global_anterior_hasta_fecha?.total ?? 0;
      const maxSem = Math.max(semHasta, semAnterior);
      const semLabels = Array.from({length: maxSem}, (_, i) => `S${i + 1}`);

      let serieActual, serieAnterior, labelActual, labelAnterior, colorActual, colorAnterior;
      if (tipo === 'tickets') {
        serieActual = datosSem.tickets.actual;
        serieAnterior = datosSem.tickets.anterior;
        labelActual = `Tickets ${anio}`;
        labelAnterior = `Tickets ${anioAnterior}`;
        colorActual = '#2ecc71'; colorAnterior = '#a9dfbf';
      } else if (tipo === 'facturas') {
        serieActual = datosSem.facturas.actual;
        serieAnterior = datosSem.facturas.anterior;
        labelActual = `Facturas ${anio}`;
        labelAnterior = `Facturas ${anioAnterior}`;
        colorActual = '#f1c40f'; colorAnterior = '#e5a100';
      } else {
        serieActual = datosSem.global.actual;
        serieAnterior = datosSem.global.anterior;
        labelActual = `Global ${anio}`;
        labelAnterior = `Global ${anioAnterior}`;
        colorActual = '#3498db'; colorAnterior = '#9b59b6';
      }

      // Totales por semana (no acumulados)
      const semActualVals = semLabels.map((_, i) => {
        const s = i + 1;
        return s <= semHasta ? (serieActual[String(s)]?.total ?? 0) : null;
      });
      const semAnteriorVals = semLabels.map((_, i) => {
        const s = i + 1;
        return s <= semAnterior ? (serieAnterior[String(s)]?.total ?? 0) : null;
      });

      // Acumulados semana a semana
      let acumActual = 0, acumAnterior = 0;
      const valActual = semLabels.map((_, i) => {
        const s = i + 1;
        if (s <= semHasta) acumActual += serieActual[String(s)]?.total ?? 0;
        return s <= semHasta ? acumActual : null;
      });
      const valAnterior = semLabels.map((_, i) => {
        const s = i + 1;
        if (s > semAnteriorHastaFecha) return null;
        if (s < semAnteriorHastaFecha) {
          acumAnterior += serieAnterior[String(s)]?.total ?? 0;
          return acumAnterior;
        }
        // En la semana que contiene la fecha de corte exacta, usar el acumulado exacto del dashboard
        return totalAnteriorHastaFecha;
      });

      const datasets = [
        {
          label: `${labelAnterior} (semana)`,
          data: semAnteriorVals,
          borderColor: colorAnterior,
          backgroundColor: colorAnterior + '33',
          borderWidth: 1,
          borderDash: [4, 4],
          tension: 0.3,
          pointRadius: 1,
          fill: false,
          spanGaps: false,
          yAxisID: 'y1'
        },
        {
          label: `${labelActual} (semana)`,
          data: semActualVals,
          borderColor: colorActual,
          backgroundColor: colorActual + '33',
          borderWidth: 1,
          borderDash: [4, 4],
          tension: 0.3,
          pointRadius: 1,
          fill: false,
          spanGaps: false,
          yAxisID: 'y1'
        },
        {
          label: `${labelAnterior} (acum.)`,
          data: valAnterior,
          borderColor: colorAnterior,
          backgroundColor: colorAnterior + '33',
          borderWidth: 2,
          tension: 0.3,
          pointRadius: 1,
          fill: false,
          spanGaps: false
        },
        {
          label: `${labelActual} (acum.)`,
          data: valActual,
          borderColor: colorActual,
          backgroundColor: colorActual + '33',
          borderWidth: 2,
          tension: 0.3,
          pointRadius: 2,
          fill: false,
          spanGaps: false
        }
      ];

      if (chartEstadisticas) chartEstadisticas.destroy();
      chartEstadisticas = new Chart(document.getElementById('chart-estadisticas').getContext('2d'), {
        type: 'line',
        data: { labels: semLabels, datasets },
        options: {
          responsive: true,
          interaction: { mode: 'index', intersect: false },
          scales: {
            x: { title: { display: true, text: 'Semana del año' } },
            y: { beginAtZero: true, title: { display: true, text: 'Acumulado (€)' } },
            y1: { beginAtZero: true, position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'Semana (€)' } }
          }
        }
      });
      document.getElementById('modal-graficos').style.display = 'block';
      chartCliente = null;
      return;
    }

    // === Vista por Días del Mes (líneas) ===
    if (vista === 'dia_semana') {
      const datosDia = await fetchConManejadorErrores(buildApiUrl(`/api/ventas/total_dia_semana?anio=${anio}&mes=${mes}`));
      const diaHasta = datosDia.dia_hasta;
      const diasMesAnterior = datosDia.dias_mes_anterior;
      const maxDias = Math.max(diaHasta, diasMesAnterior);
      const diasLabels = Array.from({length: maxDias}, (_, i) => String(i + 1));
      const mesesNombres = ['','Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
      const mesNombre = mesesNombres[parseInt(mes, 10)] || '';

      let serieActual, serieAnterior, labelActual, labelAnterior, colorActual, colorAnterior;
      if (tipo === 'tickets') {
        serieActual = datosDia.tickets.actual;
        serieAnterior = datosDia.tickets.anterior;
        labelActual = `Tickets ${mesNombre} ${anio}`;
        labelAnterior = `Tickets ${mesNombre} ${anioAnterior}`;
        colorActual = '#2ecc71'; colorAnterior = '#a9dfbf';
      } else if (tipo === 'facturas') {
        serieActual = datosDia.facturas.actual;
        serieAnterior = datosDia.facturas.anterior;
        labelActual = `Facturas ${mesNombre} ${anio}`;
        labelAnterior = `Facturas ${mesNombre} ${anioAnterior}`;
        colorActual = '#f1c40f'; colorAnterior = '#e5a100';
      } else {
        serieActual = datosDia.global.actual;
        serieAnterior = datosDia.global.anterior;
        labelActual = `Global ${mesNombre} ${anio}`;
        labelAnterior = `Global ${mesNombre} ${anioAnterior}`;
        colorActual = '#3498db'; colorAnterior = '#9b59b6';
      }

      // Totales diarios (no acumulados)
      const diaActualVals = diasLabels.map((_, i) => {
        const d = i + 1;
        return d <= diaHasta ? (serieActual[String(d)]?.total ?? 0) : null;
      });
      const diaAnteriorVals = diasLabels.map((_, i) => {
        const d = i + 1;
        return d <= diasMesAnterior ? (serieAnterior[String(d)]?.total ?? 0) : null;
      });

      // Acumulados día a día
      let acumActual = 0, acumAnterior = 0;
      const valActual = diasLabels.map((_, i) => {
        const d = i + 1;
        if (d <= diaHasta) acumActual += serieActual[String(d)]?.total ?? 0;
        return d <= diaHasta ? acumActual : null;
      });
      const valAnterior = diasLabels.map((_, i) => {
        const d = i + 1;
        if (d <= diasMesAnterior) acumAnterior += serieAnterior[String(d)]?.total ?? 0;
        return d <= diasMesAnterior ? acumAnterior : null;
      });

      const datasets = [
        {
          label: `${labelAnterior} (día)`,
          data: diaAnteriorVals,
          borderColor: colorAnterior,
          backgroundColor: colorAnterior + '33',
          borderWidth: 1,
          borderDash: [4, 4],
          tension: 0.3,
          pointRadius: 1,
          fill: false,
          spanGaps: false,
          yAxisID: 'y1'
        },
        {
          label: `${labelActual} (día)`,
          data: diaActualVals,
          borderColor: colorActual,
          backgroundColor: colorActual + '33',
          borderWidth: 1,
          borderDash: [4, 4],
          tension: 0.3,
          pointRadius: 1,
          fill: false,
          spanGaps: false,
          yAxisID: 'y1'
        },
        {
          label: `${labelAnterior} (acum.)`,
          data: valAnterior,
          borderColor: colorAnterior,
          backgroundColor: colorAnterior + '33',
          borderWidth: 2,
          tension: 0.3,
          pointRadius: 1,
          fill: false,
          spanGaps: false
        },
        {
          label: `${labelActual} (acum.)`,
          data: valActual,
          borderColor: colorActual,
          backgroundColor: colorActual + '33',
          borderWidth: 2,
          tension: 0.3,
          pointRadius: 2,
          fill: false,
          spanGaps: false
        }
      ];

      if (chartEstadisticas) chartEstadisticas.destroy();
      chartEstadisticas = new Chart(document.getElementById('chart-estadisticas').getContext('2d'), {
        type: 'line',
        data: { labels: diasLabels, datasets },
        options: {
          responsive: true,
          interaction: { mode: 'index', intersect: false },
          scales: {
            x: { title: { display: true, text: 'Día del mes' } },
            y: { beginAtZero: true, title: { display: true, text: 'Acumulado (€)' } },
            y1: { beginAtZero: true, position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'Día (€)' } }
          }
        }
      });
      document.getElementById('modal-graficos').style.display = 'block';
      chartCliente = null;
      return;
    }

    const [datosActual, datosAnterior] = await Promise.all([
      fetchConManejadorErrores(buildApiUrl(`/api/ventas/total_mes?anio=${anio}`)),
      fetchConManejadorErrores(buildApiUrl(`/api/ventas/total_mes?anio=${anioAnterior}`))
    ]);
    // Serie de CANTIDADES por mes (si el endpoint existe). Fallback seguro a null.
    let cantidadesActual = null;
    try {
      cantidadesActual = await fetchConManejadorErrores(buildApiUrl(`/api/ventas/cantidad_mes?anio=${anio}`));
    } catch(e) {
      cantidadesActual = null;
    }
  
    // Función para agrupar datos mensuales en trimestres
    const agruparPorTrimestre = (datosMensuales) => {
      const trimestres = [0, 0, 0, 0];
      for (let i = 0; i < 12; i++) {
        const mes = String(i + 1).padStart(2, '0');
        const valor = parseFloat(datosMensuales[mes]) || 0;
        trimestres[Math.floor(i / 3)] += valor;
      }
      return trimestres;
    };

    const meses = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
    const trimestresLabels = ['T1 (Ene-Mar)', 'T2 (Abr-Jun)', 'T3 (Jul-Sep)', 'T4 (Oct-Dic)'];
    const labels = vista === 'trimestral' ? trimestresLabels : meses;
    const datasets = [];
    // Valores mensuales según el tipo seleccionado
    let valoresAnioActual = []; let ingresosData = null; let gastosData = null;

    if (tipo === 'global') {
      if (vista === 'trimestral') {
        valoresAnioActual = agruparPorTrimestre(datosActual.global);
        datasets.push({ label: `Global ${anioAnterior}`, data: agruparPorTrimestre(datosAnterior.global), backgroundColor: '#9b59b6' });
      } else {
        valoresAnioActual = meses.map((_, i) => datosActual.global[String(i+1).padStart(2,'0')]);
        datasets.push({ label: `Global ${anioAnterior}`, data: meses.map((_, i) => datosAnterior.global[String(i+1).padStart(2,'0')]), backgroundColor: '#9b59b6' });
      }
      datasets.push({ label: `Global ${anio}`, data: valoresAnioActual, backgroundColor: '#3498db' });
    } else if (tipo === 'tickets') {
      if (vista === 'trimestral') {
        valoresAnioActual = agruparPorTrimestre(datosActual.tickets);
      } else {
        valoresAnioActual = meses.map((_, i) => datosActual.tickets[String(i+1).padStart(2,'0')]);
      }
      datasets.push({ label: `Tickets ${anio}`, data: valoresAnioActual, backgroundColor: '#2ecc71' });
    } else if (tipo === 'ingresos_gastos') {
      const [datosIG, datosIGAnterior] = await Promise.all([
        fetchConManejadorErrores(buildApiUrl(`/api/ingresos_gastos_mes?anio=${anio}`)),
        fetchConManejadorErrores(buildApiUrl(`/api/ingresos_gastos_mes?anio=${anioAnterior}`))
      ]);
      const ingresosDataMes = meses.map((_, i) => parsearImporte(datosIG.ingresos[String(i+1).padStart(2,'0')]));
      const gastosDataMes = meses.map((_, i) => Math.abs(parsearImporte(datosIG.gastos[String(i+1).padStart(2,'0')] )));
      const ingresosPrevDataMes = meses.map((_, i) => parsearImporte(datosIGAnterior.ingresos[String(i+1).padStart(2,'0')]));
      const gastosPrevDataMes = meses.map((_, i) => Math.abs(parsearImporte(datosIGAnterior.gastos[String(i+1).padStart(2,'0')] )));
      
      // Agrupar por trimestre si es necesario
      const agruparArrayTrimestre = (arr) => {
        const t = [0, 0, 0, 0];
        for (let i = 0; i < 12; i++) t[Math.floor(i / 3)] += arr[i] || 0;
        return t;
      };
      
      if (vista === 'trimestral') {
        ingresosData = agruparArrayTrimestre(ingresosDataMes);
        gastosData = agruparArrayTrimestre(gastosDataMes);
        datasets.push({ label: `Ingresos ${anioAnterior}`, data: agruparArrayTrimestre(ingresosPrevDataMes), backgroundColor: '#a9dfbf' });
        datasets.push({ label: `Gastos ${anioAnterior}`, data: agruparArrayTrimestre(gastosPrevDataMes), backgroundColor: '#f5b7b1' });
      } else {
        ingresosData = ingresosDataMes;
        gastosData = gastosDataMes;
        datasets.push({ label: `Ingresos ${anioAnterior}`, data: ingresosPrevDataMes, backgroundColor: '#a9dfbf' });
        datasets.push({ label: `Gastos ${anioAnterior}`, data: gastosPrevDataMes, backgroundColor: '#f5b7b1' });
      }
      // Año actual
      datasets.push({ label: `Ingresos ${anio}`, data: ingresosData, backgroundColor: '#2ecc71' });
      datasets.push({ label: `Gastos ${anio}`, data: gastosData, backgroundColor: '#e74c3c' });
      // Líneas de media (solo en vista mensual)
      if (vista === 'mensual') {
        const monthSelNum = parseInt(mes, 10);
        let ingresosConsiderados = ingresosData.slice(0, monthSelNum - 1).filter(v => v !== 0);
        const mediaIngresos = ingresosConsiderados.length ? ingresosConsiderados.reduce((a,b)=>a+b,0)/ingresosConsiderados.length : 0;
        let gastosConsiderados = gastosData.slice(0, monthSelNum - 1).filter(v => v !== 0);
        const mediaGastos = gastosConsiderados.length ? gastosConsiderados.reduce((a,b)=>a+b,0)/gastosConsiderados.length : 0;
        datasets.push({
          label: `Media ingresos (${formatearImporte(mediaIngresos)})`,
          type: 'line',
          data: Array(12).fill(mediaIngresos),
          borderColor: '#27ae60',
          backgroundColor: 'rgba(46,204,113,0.15)',
          borderWidth: 2,
          tension: 0.1,
          pointRadius: 0,
          fill: false
        });
        datasets.push({
          label: `Media gastos (${formatearImporte(mediaGastos)})`,
          type: 'line',
          data: Array(12).fill(mediaGastos),
          borderColor: '#c0392b',
          backgroundColor: 'rgba(192,57,43,0.15)',
          borderWidth: 2,
          tension: 0.1,
          pointRadius: 0,
          fill: false
        });
      }
    } else {
      if (vista === 'trimestral') {
        valoresAnioActual = agruparPorTrimestre(datosActual.facturas);
      } else {
        valoresAnioActual = meses.map((_, i) => datosActual.facturas[String(i+1).padStart(2,'0')]);
      }
      datasets.push({ label: `Facturas ${anio}`, data: valoresAnioActual, backgroundColor: '#f1c40f' });
    }

    if (tipo !== 'ingresos_gastos') {
      // --- Media mensual (exactamente igual que en las tarjetas) ---
      // 1. Traer los datos agregados para recalcular la media con la misma fórmula
      const datosMedia = await fetchConManejadorErrores(buildApiUrl('/api/ventas/media_por_documento?' + new URLSearchParams({ mes, anio })));
      const mesNumGraf = parseInt(mes, 10);
      const ajustar = obj => {
        if(!obj || !obj.actual) return;
        const totalActual      = parsearImporte(obj.actual.total);
        const totalMesActual   = parsearImporte(obj.actual.mes_actual?.total ?? 0);
        const mesesPrevios     = mesNumGraf - 1;
        const totalPrevio      = totalActual - totalMesActual;
        obj.actual.media_mensual = mesesPrevios > 0 ? (totalPrevio / mesesPrevios) : 0;
      };
      ajustar(datosMedia.tickets);
      ajustar(datosMedia.facturas);
      ajustar(datosMedia.global);

      const mediaTickets  = parsearImporte(datosMedia.tickets.actual.media_mensual);
      const mediaFacturas = parsearImporte(datosMedia.facturas.actual.media_mensual);
      const mediaGlobal   = parsearImporte(datosMedia.global.actual.media_mensual);

      // Calcular medias de CANTIDAD (igual criterio que en tarjetas)
      const monthSelNumCnt = parseInt(mes, 10);
      const totalCantTickets   = Number(datosMedia.tickets?.actual?.cantidad ?? 0);
      const cantMesTickets     = Number(datosMedia.tickets?.actual?.mes_actual?.cantidad ?? 0);
      const totalCantFacturas  = Number(datosMedia.facturas?.actual?.cantidad ?? 0);
      const cantMesFacturas    = Number(datosMedia.facturas?.actual?.mes_actual?.cantidad ?? 0);
      const mesesPrevCnt = Math.max(0, monthSelNumCnt - 1);
      const mediaCantTickets  = mesesPrevCnt > 0 ? (totalCantTickets  - cantMesTickets)  / mesesPrevCnt : 0;
      const mediaCantFacturas = mesesPrevCnt > 0 ? (totalCantFacturas - cantMesFacturas) / mesesPrevCnt : 0;

      if (tipo === 'tickets') {
        const mediaLabel = `Media mensual (${formatearImporte(mediaTickets)})`;
        datasets.push({
          label: mediaLabel,
          type: 'line',
          data: Array(12).fill(mediaTickets),
          borderColor: '#e74c3c',
          backgroundColor: 'rgba(231,76,60,0.15)',
          borderWidth: 2,
          tension: 0.1,
          pointRadius: 0,
          fill: false
        });
        // Línea de MEDIA de CANTIDAD de tickets
        datasets.push({
          label: `Media cantidad tickets (${mediaCantTickets.toFixed(1)})`,
          type: 'line',
          data: Array(12).fill(mediaCantTickets),
          borderColor: '#16a085',
          backgroundColor: 'rgba(22,160,133,0.12)',
          borderWidth: 2,
          tension: 0.1,
          pointRadius: 0,
          yAxisID: 'y2',
          fill: false
        });
      } else if (tipo === 'facturas') {
        const mediaLabel = `Media mensual (${formatearImporte(mediaFacturas)})`;
        datasets.push({
          label: mediaLabel,
          type: 'line',
          data: Array(12).fill(mediaFacturas),
          borderColor: '#e67e22',
          backgroundColor: 'rgba(230,126,34,0.15)',
          borderWidth: 2,
          tension: 0.1,
          pointRadius: 0,
          fill: false
        });
        // Línea de MEDIA de CANTIDAD de facturas
        datasets.push({
          label: `Media cantidad facturas (${mediaCantFacturas.toFixed(1)})`,
          type: 'line',
          data: Array(12).fill(mediaCantFacturas),
          borderColor: '#8e44ad',
          backgroundColor: 'rgba(142,68,173,0.12)',
          borderWidth: 2,
          tension: 0.1,
          pointRadius: 0,
          yAxisID: 'y2',
          fill: false
        });
      } else {
        // tipo === 'global' -> solo media del TOTAL GLOBAL
        datasets.push({
          label: `Media Global (${formatearImporte(mediaGlobal)})`,
          type: 'line',
          data: Array(12).fill(mediaGlobal),
          borderColor: '#9b59b6',
          backgroundColor: 'rgba(155,89,182,0.12)',
          borderWidth: 2,
          tension: 0.1,
          pointRadius: 0,
          fill: false
        });
      }
    }

    // Construir arreglo de cantidades por mes para etiquetas si disponible
    let countsForBars = null;
    if (cantidadesActual) {
      if (tipo === 'tickets') {
        countsForBars = meses.map((_, i)=> cantidadesActual?.tickets?.[String(i+1).padStart(2,'0')] ?? null);
      } else if (tipo === 'facturas') {
        countsForBars = meses.map((_, i)=> cantidadesActual?.facturas?.[String(i+1).padStart(2,'0')] ?? null);
      }
    }

    if (chartEstadisticas) chartEstadisticas.destroy();
    chartEstadisticas = new Chart(document.getElementById('chart-estadisticas').getContext('2d'), {
      type: 'bar',
      data: { labels: labels, datasets },
      options: {
        responsive: true,
        scales: {
          y: { beginAtZero: true },
          y2: { beginAtZero: true, position: 'right', grid: { drawOnChartArea: false }, ticks: { stepSize: 1 } }
        },
        plugins: {
          barLabelsCounts: { counts: countsForBars }
        }
      },
      plugins: [barLabelsPlugin]
    });
  
    document.getElementById('modal-graficos').style.display = 'block';
    // Al mostrar gráfico general eliminar referencia chartCliente si existía
    chartCliente = null;
  }
  
  async function asegurarChartJs() {
    if (typeof Chart !== 'undefined') return;
    return new Promise((res, rej) => {
      const s = document.createElement('script');
      s.src = 'https://cdn.jsdelivr.net/npm/chart.js';
      s.onload = res; s.onerror = rej;
      document.head.appendChild(s);
    });
  }
  
  window.addEventListener('click', e => {
    const modal = document.getElementById('modal-graficos');
    if (e.target === modal) {
      modal.style.display = 'none';
    }
  }, true);
  
  // ==============================
  // FETCH WRAPPER
  // ==============================

  // Exponer funciones globales necesarias para los scripts inline de HTML
  window.abrirModalGraficos = abrirModalGraficos;
  window.abrirGraficoCliente = abrirGraficoCliente;
  window.abrirGraficoProducto = abrirGraficoProducto;
  window.recargarEstadisticas = recargarEstadisticas;
  window.cargarIngresosGastosTotales = cargarIngresosGastosTotales;
  window.descargarCSV = descargarCSV;

  
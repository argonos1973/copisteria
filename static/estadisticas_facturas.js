import { formatearFecha, formatearImporte, fetchConManejadorErrores, parsearImporte } from './scripts_utils.js';

// ==============================
// ESTADISTICAS FACTURAS - COMPLETO
// ==============================

// ==============================
// EVENTOS INICIALES
// ==============================
// ---- Toggle visibility of card content ----
function setCardVisibility(card, hide) {
  const content = card.querySelector('.stats-content');
  // Limpiar cualquier .hidden residual de versiones previas
  if(content) content.classList.remove('hidden');
  
  if(hide) {
    card.classList.add('collapsed');
    // Añadir un indicador visual para tarjetas colapsadas
    card.style.opacity = '0.85';
    card.style.borderLeft = '4px solid #ccc';
  } else {
    card.classList.remove('collapsed');
    card.style.opacity = '1';
    card.style.borderLeft = '';
  }
  
  const btn = card.querySelector('.toggle-card');
  if(btn) {
    const icon = btn.querySelector('i');
    icon.classList.toggle('fa-eye', hide);
    icon.classList.toggle('fa-eye-slash', !hide);
    btn.title = hide ? 'Mostrar' : 'Ocultar';
  }
}

// Inicializa los controles de colapso para todas las tarjetas de estadísticas
function initCollapseControls() {
  document.querySelectorAll('.toggle-card').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const card = btn.closest('.stats-card');
      // toggle state
      const currentlyHidden = sessionStorage.getItem('statsHidden_'+card.id) === '1';
      const newHidden = !currentlyHidden;
      setCardVisibility(card, newHidden);
      sessionStorage.setItem('statsHidden_'+card.id, newHidden ? '1' : '0');
    });
    
    // aplicar estado guardado al cargar
    const card = btn.closest('.stats-card');
    const hiddenSaved = sessionStorage.getItem('statsHidden_'+card.id) === '1';
    setCardVisibility(card, hiddenSaved);
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

  document.getElementById('btn-descargar-csv')?.addEventListener('click', descargarCSV);
  document.getElementById('btn-graficos')?.addEventListener('click', abrirModalGraficos);
  document.getElementById('cerrar-modal')?.addEventListener('click', () => {
    document.getElementById('modal-graficos').style.display = 'none';
  });
  document.getElementById('tipo-datos')?.addEventListener('change', abrirModalGraficos);

  initModalDrag();
  initCollapseControls(); // Inicializar controles de colapso
  
  await recargarEstadisticas();
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
    await Promise.all([
      cargarEstadisticas(mes, anio),
      cargarIngresosGastosTotales(mes, anio)
    ]);
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
    
    const qp = new URLSearchParams({ mes, anio, t: Date.now() });
    const datos = await fetchConManejadorErrores('/api/ventas/media_por_documento?' + qp);
    // --- Recalcular media mensual en el cliente ---
    function ajustarMediaMensual(obj){
      if(!obj || !obj.actual) return;
      const totalActual = parsearImporte(obj.actual.total);
      const totalMesActual = parsearImporte(obj.actual.mes_actual?.total ?? 0);
      const mesesPrevios = mesNum - 1;
      const totalPrevio = totalActual - totalMesActual;
      obj.actual.media_mensual = mesesPrevios > 0 ? (totalPrevio / mesesPrevios) : 0;
    }
    ajustarMediaMensual(datos.tickets);
    ajustarMediaMensual(datos.facturas);
    if(datos.proformas) ajustarMediaMensual(datos.proformas);
    if(datos.global) ajustarMediaMensual(datos.global);
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
  
    actualizarTopClientes(await fetchConManejadorErrores('/api/clientes/top_ventas?' + qp));
    actualizarTopProductos(await fetchConManejadorErrores('/api/productos/top_ventas?' + qp));
    
    // Restaurar el estado de colapso de las tarjetas después de actualizar datos
    restaurarEstadoColapso();
  }
  
  function restaurarEstadoColapso() {
    document.querySelectorAll('.stats-card').forEach(card => {
      const hiddenSaved = sessionStorage.getItem('statsHidden_'+card.id) === '1';
      setCardVisibility(card, hiddenSaved);
    });
  }
  
  function actualizarStats(prefijo, data, cardId) {
    // Totales y medias ANUALES
    safeSet(`${prefijo}Total`, formatearImporte(data.actual.total));
    safeSet(`${prefijo}Media`, formatearImporte(data.actual.media));
    // Datos del mes seleccionado
    const totalMesSeleccionado = data.actual.mes_actual?.total ?? 0;
    const cantidadMes = data.actual.mes_actual?.cantidad ?? 0;
    safeSet(`${prefijo}MediaMensual`, formatearImporte(data.actual.media_mensual));
    // Cantidad debe ser del mes seleccionado (o 0 si no hay)
    safeSet(`${prefijo}Cantidad`, cantidadMes);
    safeSet(`${prefijo}Anterior`, `Año anterior: ${formatearImporte(data.anterior.total)}`);
    actualizarPorcentaje(`${prefijo}Porcentaje`, data.porcentaje_diferencia);
  
    // Siempre actualizamos la fila del mes para evitar valores residuales
    const totalMes = totalMesSeleccionado;
    const cantMes = cantidadMes;
    safeSet(`${prefijo}TotalMes`, formatearImporte(totalMes));
    const mesAnteriorTotal = data.anterior?.mismo_mes?.total ?? 0;
    safeSet(`${prefijo}MesAnterior`, `Mismo mes año anterior: ${formatearImporte(mesAnteriorTotal)}`);

    if (cantMes) {
      safeSet(`${prefijo}TotalMes`, formatearImporte(data.actual.mes_actual.total));
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
    document.getElementById('globalTotal').textContent = formatearImporte(global.actual.total);
    document.getElementById('globalMedia').textContent = formatearImporte(global.actual.media);
    document.getElementById('globalMediaMensual').textContent = formatearImporte(global.actual.media_mensual);
    document.getElementById('globalCantidad').textContent = global.actual.cantidad;
    document.getElementById('globalAnterior').textContent = `Año anterior: ${formatearImporte(global.anterior.total)}`;
    actualizarPorcentaje('globalPorcentaje', global.porcentaje_diferencia);
  
    const mediaMensual = parsearImporte(global.actual.media_mensual);
    const mesActual = new Date().getMonth() + 1;
    const acumulado = parsearImporte(global.actual.total);
    const previsto = acumulado + (mediaMensual * (12 - mesActual));
    document.getElementById('globalTotalPrevisto').textContent = formatearImporte(previsto);
  
    const p = (acumulado / previsto) * 100;
    const diff = p >= 100 ? p - 100 : 100 - p;
    document.getElementById('globalPorcentajePrevistoAnyo').textContent = `${p >= 100 ? '+' : '-'}${diff.toFixed(1)}%`;
    document.getElementById('globalPorcentajePrevistoAnyo').className = 'stats-percentage ' + (p >= 100 ? 'positive' : 'negative');
  
    if (global.actual.mes_actual?.cantidad) {
      document.getElementById('globalTotalMes').textContent = formatearImporte(global.actual.mes_actual.total);
      document.getElementById('globalMesAnterior').textContent = `Mismo mes año anterior: ${formatearImporte(global.anterior.mismo_mes.total)}`;
      actualizarPorcentaje('globalPorcentajeMes', global.porcentaje_diferencia_mes);
      actualizarPorcentajeFaltaMediaMensual(
        'globalFaltaMediaMensual',
        'globalPorcentajeFalta',
        parsearImporte(global.actual.mes_actual.total),
        parsearImporte(global.actual.media_mensual),
        'card-global'
      );
    }
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
      tr.innerHTML = `<td title="${p.nombre}">${p.nombre.slice(0,12)}${p.nombre.length>12?'...':''}</td>
        <td>${p.cantidad_actual}</td>
        <td>${formatearImporte(p.total_actual)}</td>
        <td class="${p.porcentaje_diferencia>=0?'positive':'negative'}">${formatearPorcentaje(p.porcentaje_diferencia)}</td>`;
      tr.style.cursor = 'pointer';
      tr.addEventListener('click', () => abrirGraficoProducto(prodId, p.nombre));
      tbody.appendChild(tr);
    });
  }
  
  // ==============================
  // INGRESOS & GASTOS TOTALES
  // ==============================
  async function cargarIngresosGastosTotales(mes, anio){
    const data = await fetchConManejadorErrores(`/api/ingresos_gastos_totales?anio=${anio}&mes=${mes}&t=${Date.now()}`);
    const ingresos = data.ingresos;
    const gastos   = data.gastos;
    const ingresosEl = document.getElementById('ig-total-ingresos');
    const gastosEl   = document.getElementById('ig-total-gastos');
    if(ingresosEl) ingresosEl.textContent = formatearImporte(ingresos.total_actual);
    if(gastosEl)   gastosEl.textContent   = formatearImporte(Math.abs(gastos.total_actual));
    
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
      balanceEl.classList.remove('importe-positivo','importe-negativo');
      balanceEl.classList.add(balanceValor>=0 ? 'importe-positivo' : 'importe-negativo');
    }

    const balTotalEl = document.getElementById('ig-total-balance');
    if(balTotalEl){
      balTotalEl.textContent = formatearImporte(balanceValor);
      balTotalEl.classList.remove('importe-positivo','importe-negativo');
      balTotalEl.classList.add(balanceValor>=0 ? 'importe-positivo' : 'importe-negativo');
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
    const datos = await fetchConManejadorErrores(`/api/clientes/ventas_mes?cliente_id=${clienteId}&anio=${anio}`);
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
    if(!productoId) return;
    await asegurarChartJs();
    const { anio } = getFechaSeleccionada();
    const cc = document.querySelector('.chart-controls');
    if(cc) cc.style.display = 'none';
    const modal = document.getElementById('modal-graficos');
    if(modal) modal.style.display = 'block';

    const datos = await fetchConManejadorErrores(`/api/productos/ventas_mes?producto_id=${productoId}&anio=${anio}`);
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
    const datos = await fetchConManejadorErrores(`/api/gastos/top_gastos?anio=${anio}&t=${Date.now()}`);
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
    const data = await fetchConManejadorErrores(`/api/estadisticas_gastos?mes=${mes}&anio=${anio}&t=${Date.now()}`);
    // Función auxiliar para aplicar formato y clases a los importes
    function actualizarImporteKpi(idElemento, valor) {
      const elemento = document.getElementById(idElemento);
      if (elemento) {
        elemento.textContent = formatearImporte(valor);
        elemento.className = ''; // Limpiar clases existentes
        if (parsearImporte(valor) >= 0) {
          elemento.classList.add('importe-positivo');
        } else {
          elemento.classList.add('importe-negativo');
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
    const datos = await fetchConManejadorErrores(`/api/ventas/total_mes?anio=${anio}`);
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
      if(e.target.classList.contains('cerrar-modal')) return;
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
    // Si existe gráfico de cliente, destruirlo antes de crear el general
    if (chartCliente) { chartCliente.destroy(); chartCliente = null; }
    if (chartProducto) { chartProducto.destroy(); chartProducto = null; }
    // Mostrar controles al abrir gráfico general
    const cc2 = document.querySelector('.chart-controls');
    if(cc2) cc2.style.display = 'block';
    await asegurarChartJs();
    const { anio, mes } = getFechaSeleccionada();
    const tipo = document.getElementById('tipo-datos').value;
    const anioAnterior = anio - 1;
    const [datosActual, datosAnterior] = await Promise.all([
      fetchConManejadorErrores(`/api/ventas/total_mes?anio=${anio}`),
      fetchConManejadorErrores(`/api/ventas/total_mes?anio=${anioAnterior}`)
    ]);
    // Serie de CANTIDADES por mes (si el endpoint existe). Fallback seguro a null.
    let cantidadesActual = null;
    try {
      cantidadesActual = await fetchConManejadorErrores(`/api/ventas/cantidad_mes?anio=${anio}`);
    } catch(e) {
      cantidadesActual = null;
    }
  
    const meses = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
    const datasets = [];
    // Valores mensuales según el tipo seleccionado
    let valoresAnioActual = []; let ingresosData = null; let gastosData = null;

    if (tipo === 'global') {
      valoresAnioActual = meses.map((_, i) => datosActual.global[String(i+1).padStart(2,'0')]);
      datasets.push({ label: `Global ${anioAnterior}`, data: meses.map((_, i) => datosAnterior.global[String(i+1).padStart(2,'0')]), backgroundColor: '#9b59b6' });
      datasets.push({ label: `Global ${anio}`, data: valoresAnioActual, backgroundColor: '#3498db' });
    } else if (tipo === 'tickets') {
      valoresAnioActual = meses.map((_, i) => datosActual.tickets[String(i+1).padStart(2,'0')]);
      datasets.push({ label: `Tickets ${anio}`, data: valoresAnioActual, backgroundColor: '#2ecc71' });
    } else if (tipo === 'ingresos_gastos') {
      const [datosIG, datosIGAnterior] = await Promise.all([
        fetchConManejadorErrores(`/api/ingresos_gastos_mes?anio=${anio}`),
        fetchConManejadorErrores(`/api/ingresos_gastos_mes?anio=${anioAnterior}`)
      ]);
      ingresosData = meses.map((_, i) => parsearImporte(datosIG.ingresos[String(i+1).padStart(2,'0')]));
      gastosData = meses.map((_, i) => Math.abs(parsearImporte(datosIG.gastos[String(i+1).padStart(2,'0')] )));
      const ingresosPrevData = meses.map((_, i) => parsearImporte(datosIGAnterior.ingresos[String(i+1).padStart(2,'0')]));
      const gastosPrevData = meses.map((_, i) => Math.abs(parsearImporte(datosIGAnterior.gastos[String(i+1).padStart(2,'0')] )));
      // Año anterior primero para que quede detrás en la superposición
      datasets.push({ label: `Ingresos ${anioAnterior}`, data: ingresosPrevData, backgroundColor: '#a9dfbf' });
      datasets.push({ label: `Gastos ${anioAnterior}`, data: gastosPrevData, backgroundColor: '#f5b7b1' });
      // Año actual
      datasets.push({ label: `Ingresos ${anio}`, data: ingresosData, backgroundColor: '#2ecc71' });
      datasets.push({ label: `Gastos ${anio}`, data: gastosData, backgroundColor: '#e74c3c' });
      // Líneas de media para ingresos y gastos
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
    } else {
      valoresAnioActual = meses.map((_, i) => datosActual.facturas[String(i+1).padStart(2,'0')]);
      datasets.push({ label: `Facturas ${anio}`, data: valoresAnioActual, backgroundColor: '#f1c40f' });
    }

    if (tipo !== 'ingresos_gastos') {
      // --- Media mensual (exactamente igual que en las tarjetas) ---
      // 1. Traer los datos agregados para recalcular la media con la misma fórmula
      const datosMedia = await fetchConManejadorErrores('/api/ventas/media_por_documento?' + new URLSearchParams({ mes, anio }));
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
      data: { labels: meses, datasets },
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
    if (e.target === document.getElementById('modal-graficos')) document.getElementById('modal-graficos').style.display = 'none';
  });
  
  // ==============================
  // FETCH WRAPPER
  // ==============================

  // Exponer funciones globales necesarias para los scripts inline de HTML
  window.abrirModalGraficos = abrirModalGraficos;
  window.abrirGraficoCliente = abrirGraficoCliente;
  window.abrirGraficoProducto = abrirGraficoProducto;
  window.recargarEstadisticas = recargarEstadisticas;
  window.descargarCSV = descargarCSV;

  
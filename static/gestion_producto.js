import { IP_SERVER, PORT } from './constantes.js';
import { mostrarNotificacion, mostrarConfirmacion } from './notificaciones.js';

const { createApp, ref, reactive, computed, onMounted, nextTick } = Vue;

createApp({
  setup() {
    // Base API con prefijo /api
    const API_BASE = `http://${IP_SERVER}:${PORT}/api`;

    // Estado del producto
    const producto = reactive({
      id: null,
      nombre: '',
      descripcion: '',
      subtotal: 0,
      impuestos: 21,
      iva: 0,
      total: 0
    });

    // Estado del formulario
    const modoEdicion = ref(false);
    const errores = reactive({});
    const cargando = ref(false);
    const nombreInput = ref(null);

    // Obtener ID de URL
    const getIdFromUrl = () => {
      const params = new URLSearchParams(window.location.search);
      return params.get('id');
    };

    // Formateo de precio
    const formatearPrecio = (precio) => {
      return precio !== undefined && precio !== null
        ? `${Number(precio).toFixed(2)} €`
        : '0.00 €';
    };

    // Helpers redondeo
    const round4 = (v) => +Number(v ?? 0).toFixed(4);
    const round2 = (v) => +Number(v ?? 0).toFixed(2);

    // Cálculo de totales desde subtotal -> total
    const calcularTotales = () => {
      const base = Number(producto.subtotal ?? 0);
      const ivaPct = Number(producto.impuestos ?? 0);
      if (isNaN(base) || isNaN(ivaPct)) return;
      producto.subtotal = round4(base);
      producto.iva = round2(base * (ivaPct / 100));
      producto.total = round2(base + producto.iva);
    };

    // Cálculo inverso desde total -> subtotal
    const calcularDesdeTotal = () => {
      const total = Number(producto.total ?? 0);
      const ivaPct = Number(producto.impuestos ?? 0);
      if (isNaN(total) || isNaN(ivaPct)) return;
      const divisor = 1 + (ivaPct / 100);
      const base = total / divisor;
      producto.subtotal = round4(base);
      producto.iva = round2(total - producto.subtotal);
      producto.total = round2(total);
    };

    // Handlers de inputs
    const onSubtotalInput = () => {
      calcularTotales();
    };

    const onTotalInput = () => {
      calcularDesdeTotal();
    };

    const onImpuestosChange = () => {
      // Recalcular en función del último campo editado; por simplicidad, desde subtotal
      calcularTotales();
    };

    // Mayúsculas en tiempo real
    const onNombreInput = () => {
      if (typeof producto.nombre === 'string') {
        producto.nombre = producto.nombre.toUpperCase();
      }
    };

    const onDescripcionInput = () => {
      if (typeof producto.descripcion === 'string') {
        producto.descripcion = producto.descripcion.toUpperCase();
      }
    };

    // Flag para ejecutar eliminación tras cargar
    let eliminarTrasCargar = false;

    // Cargar producto por ID
    const cargarProducto = async (id) => {
      try {
        cargando.value = true;
        const response = await fetch(`${API_BASE}/productos/${id}`);
        if (!response.ok) throw new Error(`Error al cargar producto: ${response.statusText}`);
        const data = await response.json();
        Object.keys(producto).forEach((k) => {
          if (data.hasOwnProperty(k)) producto[k] = data[k];
        });
        modoEdicion.value = true;
        // Si venimos con accion=eliminar, ejecutar ahora que ya tenemos el producto cargado
        if (eliminarTrasCargar) {
          console.debug('[GESTION_PRODUCTOS] ejecutando eliminación tras carga');
          await eliminarProductoActual();
          eliminarTrasCargar = false;
        }
      } catch (error) {
        console.error('Error al cargar el producto:', error);
        mostrarNotificacion(`Error: ${error.message}`, 'error');
      } finally {
        cargando.value = false;
      }
    };

    // Eliminar producto actual (confirmación y borrado)
    const eliminarProductoActual = async () => {
      if (!producto.id) {
        mostrarNotificacion('No hay producto para eliminar', 'error');
        return;
      }
      const confirmado = (typeof mostrarConfirmacion === 'function')
        ? await mostrarConfirmacion('¿Está seguro de eliminar este producto?')
        : window.confirm('¿Está seguro de eliminar este producto?');
      if (!confirmado) return;
      try {
        cargando.value = true;
        const response = await axios.delete(`${API_BASE}/productos/${producto.id}`);
        if (response.data?.success) {
          mostrarNotificacion('Producto eliminado correctamente', 'success');
          setTimeout(() => { window.location.href = 'CONSULTA_PRODUCTOS.html'; }, 600);
        } else {
          mostrarNotificacion(response.data?.message || 'No se pudo eliminar el producto.', 'error');
        }
      } catch (error) {
        console.error('Error al eliminar el producto:', error);
        mostrarNotificacion(error.response?.data?.message || error.response?.data?.error || 'No se pudo eliminar el producto', 'error');
      } finally {
        cargando.value = false;
      }
    };

    // Validación
    const validarFormulario = () => {
      errores.nombre = '';
      errores.subtotal = '';
      errores.impuestos = '';

      if (!producto.nombre.trim()) {
        errores.nombre = 'El nombre es obligatorio';
        return false;
      }
      if (producto.subtotal === null || producto.subtotal === undefined || isNaN(producto.subtotal)) {
        errores.subtotal = 'El precio base debe ser un número válido';
        return false;
      }
      if (producto.subtotal < 0) {
        errores.subtotal = 'El precio base no puede ser negativo';
        return false;
      }
      if (producto.impuestos === null || producto.impuestos === undefined || isNaN(producto.impuestos)) {
        errores.impuestos = 'El porcentaje de impuestos debe ser un valor válido';
        return false;
      }
      return true;
    };

    // Guardar/Actualizar
    const guardarProducto = async () => {
      // Normalizar campos texto a MAYÚSCULAS
      if (typeof producto.nombre === 'string') producto.nombre = producto.nombre.trim().toUpperCase();
      if (typeof producto.descripcion === 'string') producto.descripcion = producto.descripcion.trim().toUpperCase();
      calcularTotales();
      if (!validarFormulario()) {
        mostrarNotificacion('Por favor, corrija los errores del formulario', 'error');
        return;
      }
      try {
        cargando.value = true;
        let response;
        if (modoEdicion.value) {
          response = await axios.put(`${API_BASE}/productos/${producto.id}`, producto);
        } else {
          response = await axios.post(`${API_BASE}/productos`, producto);
        }
        if (response.data.success) {
          mostrarNotificacion(modoEdicion.value ? 'Producto actualizado correctamente' : 'Producto creado correctamente', 'success');
          setTimeout(() => { window.location.href = 'CONSULTA_PRODUCTOS.html'; }, 800);
        } else {
          mostrarNotificacion(response.data.message || 'Error al guardar el producto', 'error');
        }
      } catch (error) {
        console.error('Error al guardar el producto:', error);
        mostrarNotificacion(error.response?.data?.message || error.response?.data?.error || 'Error al guardar el producto', 'error');
      } finally {
        cargando.value = false;
      }
    };

    // Volver
    const volver = () => { window.location.href = 'CONSULTA_PRODUCTOS.html'; };

    // onMounted
    onMounted(async () => {
      if (producto.impuestos == null) producto.impuestos = 21; // por defecto 21%
      calcularTotales();
      const params = new URLSearchParams(window.location.search);
      const id = params.get('id');
      const accion = params.get('accion');
      const confirmado = params.get('confirmado');
      console.debug('[GESTION_PRODUCTOS] params', { id, accion });
      // Si viene con accion=eliminar, marcar para ejecutar tras cargar y preasignar id
      if (accion === 'eliminar' && id) {
        eliminarTrasCargar = true;
        // Preasignar id por si la carga falla, para permitir eliminar igualmente
        producto.id = Number(id);
      }
      if (id) await cargarProducto(id);
      // Fallback: si aún está marcado, ejecutar eliminación ahora
      if (eliminarTrasCargar) {
        console.debug('[GESTION_PRODUCTOS] fallback: eliminación tras onMounted');
        // Si confirmado=1, no pedir confirmación de nuevo
        if (confirmado === '1') {
          cargando.value = true;
          try {
            const response = await axios.delete(`${API_BASE}/productos/${producto.id}`);
            if (response.data?.success) {
              mostrarNotificacion('Producto eliminado correctamente', 'success');
              setTimeout(() => { window.location.href = 'CONSULTA_PRODUCTOS.html'; }, 600);
            } else {
              mostrarNotificacion(response.data?.message || 'No se pudo eliminar el producto.', 'error');
            }
          } catch (error) {
            console.error('Error al eliminar el producto (confirmado=1):', error);
            mostrarNotificacion(error.response?.data?.message || error.response?.data?.error || 'No se pudo eliminar el producto', 'error');
          } finally {
            cargando.value = false;
          }
        } else {
          await eliminarProductoActual();
        }
        eliminarTrasCargar = false;
      }
      nextTick(() => { if (nombreInput.value) nombreInput.value.focus(); });
    });

    return {
      producto,
      modoEdicion,
      errores,
      cargando,
      nombreInput,
      formatearPrecio,
      calcularTotales,
      onSubtotalInput,
      onTotalInput,
      onImpuestosChange,
      onNombreInput,
      onDescripcionInput,
      guardarProducto,
      eliminarProductoActual,
      volver
    };
  }
}).mount('#app');

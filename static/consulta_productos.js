import { API_URL_PRIMARY, API_URL_FALLBACK } from './constantes.js?v=1762757322';
import { mostrarNotificacion, mostrarConfirmacion } from './notificaciones.js';

const { createApp, ref, reactive, onMounted, watch, nextTick } = Vue;

createApp({
  setup() {
    const filters = reactive({
      nombre: ''
    });

    const productos = ref([]);
    const loading = ref(false);
    const page = ref(1);
    const MAX_PAGE_SIZE = 100;
    const pageSize = ref(10);
    const total = ref(0);
    const totalPages = ref(1);

    const guardarFiltros = () => {
      sessionStorage.setItem('filtrosProductos', JSON.stringify({
        nombre: filters.nombre
      }));
    };

    const restaurarFiltros = () => {
      const filtrosGuardados = sessionStorage.getItem('filtrosProductos');
      if (filtrosGuardados) {
        const filtrosParseados = JSON.parse(filtrosGuardados);
        filters.nombre = filtrosParseados.nombre || '';
      } else {
        filters.nombre = '';
        guardarFiltros();
      }
      fetchProductos();
    };

    const formatearPrecio = (precio) => {
      const n = Number(precio);
      if (isNaN(n)) return '0,00 €';
      return `${n.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €`;
    };

    const fetchProductos = async () => {
      try {
        loading.value = true;
        const queryParams = new URLSearchParams();
        if (filters.nombre) queryParams.append('nombre', filters.nombre);
        queryParams.append('page', String(page.value));
        // Normalizar pageSize en rango 1..MAX_PAGE_SIZE
        if (!Number.isFinite(pageSize.value)) pageSize.value = 20;
        pageSize.value = Math.max(1, Math.min(MAX_PAGE_SIZE, Number(pageSize.value)));
        queryParams.append('page_size', String(pageSize.value));
        queryParams.append('sort', 'nombre');
        queryParams.append('order', 'ASC');

        const endpointPrimary = `${API_URL_PRIMARY}/api/productos/paginado?${queryParams.toString()}`;
        const endpointFallback = `${API_URL_FALLBACK}/api/productos/paginado?${queryParams.toString()}`;

        let response;
        try {
          response = await fetch(endpointPrimary, {
              credentials: 'include'  // Incluir cookies en la petición
          });
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
        } catch (e) {
          // Fallback al mismo origen (Apache)
          response = await fetch(endpointFallback, {
              credentials: 'include'  // Incluir cookies en la petición
          });
        }
        const responseText = await response.text();

        let data;
        try {
          data = JSON.parse(responseText);
          if (data.error) {
            throw new Error(data.message || data.error);
          }
          productos.value = Array.isArray(data) ? data : (data.items || []);
          total.value = Number(data.total || 0);
          page.value = Number(data.page || 1);
          pageSize.value = Math.max(1, Math.min(MAX_PAGE_SIZE, Number(data.page_size || pageSize.value)));
          totalPages.value = Number(data.total_pages || 1);
        } catch (jsonError) {
          console.error('Error al parsear JSON:', jsonError);
          throw new Error('Error en el formato de datos recibidos');
        }
      } catch (error) {
        console.error('Error:', error);
        productos.value = [];
        mostrarNotificacion(`Error al cargar los productos: ${error.message || 'Inténtelo de nuevo'}`, 'error');
      } finally {
        loading.value = false;
      }
    };

    const goToPage = async (p) => {
      const np = Math.max(1, Math.min(Number(p) || 1, totalPages.value));
      if (np === page.value) return;
      page.value = np;
      await fetchProductos();
    };

    const nextPage = async () => {
      if (page.value < totalPages.value) {
        page.value += 1;
        await fetchProductos();
      }
    };

    const prevPage = async () => {
      if (page.value > 1) {
        page.value -= 1;
        await fetchProductos();
      }
    };

    const handlePageSizeChange = () => {
      // Validar valor permitido
      if (![10, 20, 50, 100].includes(pageSize.value)) {
        pageSize.value = 10;
      }
      page.value = 1; // Volver a primera página
      guardarFiltros();
      fetchProductos();
    };

    const changePageSize = () => {
      handlePageSizeChange();
    };

    const eliminarProducto = async (id) => {
      console.debug('[eliminarProducto] ID recibido:', id, 'tipo:', typeof id);
      
      // Verificar permiso de eliminar productos
      if (typeof verificarPermisoConAlerta !== 'undefined') {
        if (!verificarPermisoConAlerta('productos', 'eliminar')) {
          return;
        }
      }
      
      const confirmado = await mostrarConfirmacion('¿Está seguro de eliminar este producto?');
      if (!confirmado) return;
      // Validación adicional del ID para evitar peticiones /null
      let pid = id;
      if (typeof pid !== 'number') {
        pid = parseInt(pid, 10);
      }
      console.debug('[eliminarProducto] ID parseado:', pid);
      if (!Number.isInteger(pid) || pid <= 0) {
        console.warn('[eliminarProducto] ID inválido, abortando eliminación');
        mostrarNotificacion('ID de producto inválido. No se puede eliminar.', 'error');
        return;
      }
      guardarFiltros();
      try {
        const urlPrimary = `${API_URL_PRIMARY}/api/productos/${pid}`;
        const urlFallback = `${API_URL_FALLBACK}/api/productos/${pid}`;
        console.debug('[eliminarProducto] DELETE URL primary:', urlPrimary);
        let response;
        try {
          response = await axios.delete(urlPrimary);
        } catch (e) {
          console.debug('[eliminarProducto] Fallback DELETE URL:', urlFallback);
          response = await axios.delete(urlFallback);
        }
        if (response.status >= 200 && response.status < 300 && (response.data?.success ?? true)) {
          mostrarNotificacion('Producto eliminado correctamente', 'success');
          await fetchProductos();
        } else {
          throw new Error(response.data?.message || 'No se pudo eliminar el producto');
        }
      } catch (error) {
        console.error('Error al eliminar producto:', error);
        const msg = error.response?.data?.message || error.response?.data?.error || error.message || 'No se pudo eliminar el producto';
        mostrarNotificacion(msg, 'error');
      }
    };

    const verProducto = (id) => {
      guardarFiltros();
      window.location.href = `GESTION_PRODUCTOS.html?id=${id}`;
    };

    const nuevoProducto = () => {
      // Verificar permiso de crear productos
      if (typeof verificarPermisoConAlerta !== 'undefined') {
        if (!verificarPermisoConAlerta('productos', 'crear')) {
          return;
        }
      }
      guardarFiltros();
      window.location.href = 'GESTION_PRODUCTOS.html';
    };

    let debounceTimer = null;
    const handleSearch = () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        page.value = 1;
        guardarFiltros();
        fetchProductos();
      }, 300);
    };

    // --- Importar CSV ---
    const importando = ref(false);
    
    const abrirImportarCSV = () => {
      if (typeof verificarPermisoConAlerta !== 'undefined') {
        if (!verificarPermisoConAlerta('productos', 'crear')) {
          return;
        }
      }
      document.getElementById('modal-importar-csv').style.display = 'flex';
      document.getElementById('csv-file-input').value = '';
      document.getElementById('import-result').innerHTML = '';
    };
    
    const cerrarImportarCSV = () => {
      document.getElementById('modal-importar-csv').style.display = 'none';
    };
    
    const importarCSV = async () => {
      const fileInput = document.getElementById('csv-file-input');
      const resultDiv = document.getElementById('import-result');
      
      if (!fileInput.files || !fileInput.files[0]) {
        resultDiv.innerHTML = '<span style="color:red;">Seleccione un archivo CSV</span>';
        return;
      }
      
      const file = fileInput.files[0];
      const formData = new FormData();
      formData.append('file', file);
      
      importando.value = true;
      resultDiv.innerHTML = '<span style="color:#666;">Importando...</span>';
      
      try {
        const response = await fetch('/api/productos/importar-csv', {
          method: 'POST',
          credentials: 'include',
          body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
          let msg = `<span style="color:green;">✓ Creados: ${data.productos_creados}, Actualizados: ${data.productos_actualizados}</span>`;
          if (data.errores && data.errores.length > 0) {
            msg += `<br><span style="color:orange;">Errores: ${data.errores.join(', ')}</span>`;
          }
          resultDiv.innerHTML = msg;
          mostrarNotificacion(`Importación completada: ${data.productos_creados} creados, ${data.productos_actualizados} actualizados`, 'success');
          await fetchProductos();
        } else {
          resultDiv.innerHTML = `<span style="color:red;">Error: ${data.error}</span>`;
          mostrarNotificacion(data.error || 'Error en la importación', 'error');
        }
      } catch (error) {
        console.error('Error importando CSV:', error);
        resultDiv.innerHTML = `<span style="color:red;">Error: ${error.message}</span>`;
        mostrarNotificacion('Error al importar CSV', 'error');
      } finally {
        importando.value = false;
      }
    };

    // Exportar productos a CSV
    const exportarProductosCSV = async () => {
      if (productos.value.length === 0) {
        mostrarNotificacion('No hay productos para exportar', 'warning');
        return;
      }
      
      const año = new Date().getFullYear();
      
      // Generar CSV con cabecera
      let csv = 'Nombre;Subtotal;IVA %;Total;Descripcion\n';
      
      for (const p of productos.value) {
        const nombre = (p.nombre || '').replace(/;/g, ',');
        const subtotal = Number(p.subtotal || 0).toFixed(2).replace('.', ',');
        const ivaPct = Number(p.impuestos || 0);
        const total = Number(p.total || 0).toFixed(2).replace('.', ',');
        const descripcion = (p.descripcion || '').replace(/;/g, ',').replace(/\n/g, ' ');
        
        csv += `${nombre};${subtotal};${ivaPct};${total};${descripcion}\n`;
      }
      
      // Crear y descargar archivo
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `productos_${año}.csv`;
      link.click();
      URL.revokeObjectURL(link.href);
      
      mostrarNotificacion(`Exportados ${productos.value.length} productos`, 'success');
    };

    onMounted(async () => {
      restaurarFiltros();
      // Aplicar permisos al cargar la página
      await nextTick();
      if (typeof aplicarPermisosAElementos !== 'undefined') {
        aplicarPermisosAElementos();
      }
    });

    // Re-aplicar permisos cada vez que cambian los productos
    watch(productos, async () => {
      await nextTick();
      if (typeof aplicarPermisosAElementos !== 'undefined') {
        aplicarPermisosAElementos();
      }
    });

    return {
      filters,
      productos,
      loading,
      page,
      pageSize,
      total,
      totalPages,
      eliminarProducto,
      handleSearch,
      verProducto,
      nuevoProducto,
      formatearPrecio,
      nextPage,
      prevPage,
      goToPage,
      changePageSize,
      importando,
      abrirImportarCSV,
      cerrarImportarCSV,
      importarCSV,
      exportarProductosCSV
    };
  }
}).mount('#app');

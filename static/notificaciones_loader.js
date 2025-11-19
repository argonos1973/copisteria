// notificaciones_loader.js - Carga las funciones de notificaciones al scope global

import { mostrarConfirmacion, mostrarNotificacion } from '/static/notificaciones.js';

// Exportar al scope global para que estén disponibles en todos los archivos
window.mostrarConfirmacion = mostrarConfirmacion;
window.mostrarNotificacion = mostrarNotificacion;

import { mostrarNotificacion } from './notificaciones.js';
import { fetchConManejadorErrores } from './scripts_utils.js';

// Exponer en global para compatibilidad con scripts antiguos
window.mostrarNotificacion = mostrarNotificacion;
window.fetchConManejadorErrores = fetchConManejadorErrores;







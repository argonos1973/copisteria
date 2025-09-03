// constants.js
export const IP_SERVER = window.location.hostname || 'localhost';
// Primario: puerto 5001
export const PORT_PRIMARY = '5001';
export const API_URL_PRIMARY = `${window.location.protocol}//${IP_SERVER}:${PORT_PRIMARY}`;

// Fallback: mismo origen donde se sirve el frontend (Apache)
const currentPort = window.location.port ? `:${window.location.port}` : '';
export const API_URL_FALLBACK = `${window.location.protocol}//${IP_SERVER}${currentPort}`;

// Compatibilidad hacia atrás
export const PORT = PORT_PRIMARY;
export const API_URL = API_URL_PRIMARY;

// Configuración del sistema
export const VERIFACTU_HABILITADO = true; // Controla la generación de XML Facturae y envío a AEAT

// Rutas API (siempre en plural) - primario (5001) y fallback (origen)
export const API_PRODUCTOS = `${API_URL_PRIMARY}/productos`;
export const API_PRODUCTOS_FALLBACK = `${API_URL_FALLBACK}/productos`;

export const API_CONTACTOS = `${API_URL_PRIMARY}/contactos`;
export const API_CONTACTOS_FALLBACK = `${API_URL_FALLBACK}/contactos`;

export const API_FACTURAS = `${API_URL_PRIMARY}/facturas`;
export const API_FACTURAS_FALLBACK = `${API_URL_FALLBACK}/facturas`;

export const API_PROFORMAS = `${API_URL_PRIMARY}/proformas`;
export const API_PROFORMAS_FALLBACK = `${API_URL_FALLBACK}/proformas`;

export const API_TICKETS = `${API_URL_PRIMARY}/tickets`;
export const API_TICKETS_FALLBACK = `${API_URL_FALLBACK}/tickets`;
export const API_GASTOS = `${API_URL_PRIMARY}/api/gastos`;
export const API_GASTOS_FALLBACK = `${API_URL_FALLBACK}/api/gastos`;

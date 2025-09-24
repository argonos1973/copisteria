// constants.js
const host = (typeof window !== 'undefined' && window.location && window.location.hostname) ? window.location.hostname : '';
// Nunca usar loopback para API: si el navegador está en localhost/127.0.0.1, forzar IP del servidor local
// Ajusta esta IP si tu servidor local cambia
const DEFAULT_LOCAL_SERVER_IP = '192.168.1.18';
export const IP_SERVER = (!host || host === '127.0.0.1' || host === 'localhost') ? DEFAULT_LOCAL_SERVER_IP : host;
export const PORT = 5001;
export const API_URL = `http://${IP_SERVER}:${PORT}`;
export const API_URL_PRIMARY = `http://${IP_SERVER}:${PORT}`;
export const API_URL_FALLBACK = `http://${IP_SERVER}:${PORT}`;
export const API_GASTOS = `http://${IP_SERVER}:${PORT}/api/gastos`;

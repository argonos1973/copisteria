// constantes.js
// Resolución automática de IP/hostname para APIs
const DEFAULT_LOCAL_SERVER_IP = window.location.hostname || '127.0.0.1';

function getOverrideIp() {
  try {
    // Prioridad 1: query param ?api_ip=1.2.3.4 (útil para depurar rápidamente)
    if (typeof window !== 'undefined' && window.location && window.location.search) {
      const qp = new URLSearchParams(window.location.search);
      const ip = qp.get('api_ip');
      if (ip && ip.length >= 7) return ip;
    }
    // Prioridad 2: localStorage API_IP (persistente entre recargas)
    if (typeof window !== 'undefined' && window.localStorage) {
      const ip = window.localStorage.getItem('API_IP');
      if (ip && ip.length >= 7) return ip;
    }
  } catch (_) { /* no-op */ }
  return null;
}

const overrideIp = getOverrideIp();

// Regla definitiva: siempre usar override si existe; si no, usar DEFAULT_LOCAL_SERVER_IP.
// Para producción, cambia DEFAULT_LOCAL_SERVER_IP a la IP de producción y rehace build/deploy.
export const IP_SERVER = overrideIp || DEFAULT_LOCAL_SERVER_IP;
export const PORT = 5001;
export const API_URL = `http://${IP_SERVER}:${PORT}`;
export const API_URL_PRIMARY = `http://${IP_SERVER}:${PORT}`;
export const API_URL_FALLBACK = `http://${IP_SERVER}:${PORT}`;
export const API_GASTOS = `http://${IP_SERVER}:${PORT}/api/gastos`;

// Conveniencia: flag de entorno de producción (basado en hostname)
// Se considera producción si NO es localhost ni 127.0.0.1
export const IS_PROD = (IP_SERVER !== 'localhost' && IP_SERVER !== '127.0.0.1');

// constantes.js
// Resolución automática de IP/hostname para APIs
const DEFAULT_LOCAL_SERVER_IP = window.location.hostname || '127.0.0.1';
const DEFAULT_LOCAL_SERVER_HOST = window.location.host || DEFAULT_LOCAL_SERVER_IP;

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

function getOverridePort() {
  try {
    if (typeof window !== 'undefined' && window.location && window.location.search) {
      const qp = new URLSearchParams(window.location.search);
      const p = qp.get('api_port');
      if (p && /^\d+$/.test(p)) return p;
    }
    if (typeof window !== 'undefined' && window.localStorage) {
      const p = window.localStorage.getItem('API_PORT');
      if (p && /^\d+$/.test(p)) return p;
    }
  } catch (_) { /* no-op */ }
  return null;
}

const overrideIp = getOverrideIp();
const overridePort = getOverridePort();

// Regla definitiva: siempre usar override si existe; si no, usar DEFAULT_LOCAL_SERVER_IP.
// Para producción, cambia DEFAULT_LOCAL_SERVER_IP a la IP de producción y rehace build/deploy.
export const IP_SERVER = overrideIp || DEFAULT_LOCAL_SERVER_IP;
// Por defecto, usar el puerto actual (si está explícito). Si no, asumir 80/443.
const PORT_STR = overridePort || (window.location.port || '');
export const PORT = PORT_STR ? parseInt(PORT_STR, 10) : ((window.location.protocol === 'https:') ? 443 : 80);

// Detectar protocolo automáticamente - IMPORTANTE para Cloudflare
const RAW_PROTOCOL = window.location.protocol || 'http:';
const IS_CLOUDFLARE = window.location.hostname.includes('cloudflare');

// Si es Cloudflare, forzar HTTPS siempre
const PROTOCOL = (IS_CLOUDFLARE) ? 'https:' : RAW_PROTOCOL;
// Si no hay puerto explícito, usar el default (80/443) y NO añadirlo a la URL.
const USE_PORT = (PROTOCOL === 'https:' && !overridePort) ? '' : (PORT_STR ? `:${PORT_STR}` : '');

// Usar protocolo y puerto correctos según el contexto
const BASE_HOST = (overrideIp || overridePort) ? `${IP_SERVER}${USE_PORT}` : DEFAULT_LOCAL_SERVER_HOST;
export const API_URL = `${PROTOCOL}//${BASE_HOST}`;
export const API_URL_PRIMARY = `${PROTOCOL}//${BASE_HOST}`;
export const API_URL_FALLBACK = `${PROTOCOL}//${BASE_HOST}`;
export const API_GASTOS = `${PROTOCOL}//${BASE_HOST}/api/gastos`;

// Conveniencia: flag de entorno de producción (basado en hostname)
// Se considera producción si NO es localhost ni 127.0.0.1
export const IS_PROD = (IP_SERVER !== 'localhost' && IP_SERVER !== '127.0.0.1');

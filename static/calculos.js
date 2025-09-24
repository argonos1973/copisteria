// Funciones de cálculo unificadas para toda la aplicación
export function redondear(valor) {
  return Math.round(Number(valor) * 100) / 100;
}

export function calcularIVA(subtotal, porcentajeIVA) {
  return redondear(subtotal * porcentajeIVA / 100);
}

export function calcularTotal(subtotal, iva) {
  return redondear(subtotal + iva);
}

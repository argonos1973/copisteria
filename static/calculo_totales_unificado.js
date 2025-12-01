/**
 * MÓDULO DE CÁLCULO DE TOTALES UNIFICADO
 * 
 * Este módulo centraliza todos los cálculos de totales para garantizar
 * consistencia absoluta entre gestión, impresión y PDF en:
 * - Tickets, Facturas, Proformas, Presupuestos
 * 
 * REGLA FUNDAMENTAL: 
 * - IVA se redondea POR LÍNEA a 2 decimales antes de sumar
 * - Total de línea = subtotal + IVA_redondeado
 * - Total documento = suma de totales de línea
 */

import { parsearImporte } from './scripts_utils.js';
import { redondearImporte } from './scripts_utils.js';

/**
 * Calcula el total de una línea de detalle con redondeo correcto
 * @param {number|string} precio - Precio unitario
 * @param {number|string} cantidad - Cantidad
 * @param {number|string} iva - Porcentaje de IVA (ej: 21 para 21%)
 * @returns {Object} { subtotal, iva_importe, total }
 */
export function calcularLinea(precio, cantidad, iva) {
  const p = parsearImporte(precio) || 0;
  const c = parsearImporte(cantidad) || 0;
  const iv = parsearImporte(iva) || 0;

  // Subtotal sin redondear (precio * cantidad)
  const subtotal = p * c;

  // Regla fundamental: IVA se redondea por línea a 2 decimales ANTES de sumar
  const iva_importe = redondearImporte(subtotal * (iv / 100));

  // Total de línea = subtotal + IVA_redondeado
  const total = subtotal + (iva_importe || 0);

  return { subtotal, iva_importe, total };
}

/**
 * Calcula los totales del documento (suma de líneas), aplicando la regla:
 * - Total documento = suma(total de línea)
 * - IVA documento = suma(IVA_redondeado por línea)
 * - Importe bruto = suma(subtotales sin IVA)
 * @param {Array} detalles - Lista de líneas con {precio, cantidad, impuestos}
 * @returns {Object} { importe_bruto, iva, total, lineas: Array<{subtotal, iva_importe, total}> }
 */
export function calcularDocumento(detalles = []) {
  const lineas = [];
  let importe_bruto = 0; // suma de subtotales sin IVA
  let iva_total = 0;     // suma de IVA redondeado por línea
  let total = 0;         // suma de total por línea

  for (const d of (detalles || [])) {
    const res = calcularLinea(d?.precio, d?.cantidad, d?.impuestos ?? d?.iva ?? 21);
    lineas.push(res);
    importe_bruto += res.subtotal || 0;
    iva_total += res.iva_importe || 0;
    total += res.total || 0;
  }

  return {
    importe_bruto,
    iva: iva_total,
    total,
    lineas,
  };
}

/**
 * Helper para recalcular totales del documento devolviendo solo las 3 cifras
 * @param {Array} detalles
 * @returns {{importe_bruto:number, iva:number, total:number}}
 */
export function recalcularTotales(detalles = []) {
  const { importe_bruto, iva, total } = calcularDocumento(detalles);
  return { importe_bruto, iva, total };
}

/**
 * Suma totales de varios documentos ya calculados
 * @param {Array<{importe_bruto:number, iva:number, total:number}>} docs
 * @returns {{importe_bruto:number, iva:number, total:number}}
 */
export function sumarTotales(docs = []) {
  return (docs || []).reduce((acc, d) => {
    acc.importe_bruto += parsearImporte(d?.importe_bruto) || 0;
    acc.iva += parsearImporte(d?.iva) || 0;
    acc.total += parsearImporte(d?.total) || 0;
    return acc;
  }, { importe_bruto: 0, iva: 0, total: 0 });
}
export function calcularTotalLinea(precio, cantidad, iva) {
    const precioNum = typeof precio === 'number' ? precio : parsearImporte(precio);
    const cantidadNum = typeof cantidad === 'number' ? cantidad : parsearImporte(cantidad);
    const ivaNum = typeof iva === 'number' ? iva : parsearImporte(iva);
    
    // Subtotal SIN redondear (precisión completa para cálculos intermedios)
    const subtotalRaw = precioNum * cantidadNum;
    
    // IVA redondeado a 2 decimales
    const iva_importe = redondearImporte(subtotalRaw * (ivaNum / 100));
    
    // Subtotal redondeado a 2 decimales (Base Imponible de la línea)
    const subtotal = redondearImporte(subtotalRaw);
    
    // Total de línea = Base redondeada + IVA redondeado
    // Esto garantiza que Base + IVA = Total visualmente
    const total = redondearImporte(subtotal + iva_importe);
    
    return {
        subtotal: subtotal,
        iva_importe: iva_importe,
        total: total
    };
}

/**
 * Calcula los totales de un documento completo
 * @param {Array} detalles - Array de detalles con {precio, cantidad, impuestos}
 * @returns {Object} { subtotal_total, iva_total, total_final }
 */
export function calcularTotalesDocumento(detalles) {
    let subtotal_total = 0;
    let iva_total = 0;
    
    detalles.forEach(detalle => {
        const linea = calcularTotalLinea(
            detalle.precio, 
            detalle.cantidad, 
            detalle.impuestos || detalle.iva || 0
        );
        
        subtotal_total += linea.subtotal;
        iva_total += linea.iva_importe;
    });
    
    // Redondear acumuladores finales
    subtotal_total = redondearImporte(subtotal_total);
    iva_total = redondearImporte(iva_total);
    
    // Total final = Suma de bases + Suma de cuotas
    // Esto garantiza que el total del documento cuadre con el desglose
    const total_final = redondearImporte(subtotal_total + iva_total);
    
    return {
        subtotal_total: subtotal_total,
        iva_total: iva_total,
        total_final: total_final
    };
}

/**
 * Actualiza un detalle con su total calculado correctamente
 * @param {Object} detalle - Detalle a actualizar
 * @returns {Object} Detalle actualizado con total correcto
 */
export function actualizarDetalleConTotal(detalle) {
    const linea = calcularTotalLinea(
        detalle.precio, 
        detalle.cantidad, 
        detalle.impuestos || detalle.iva || 0
    );
    
    return {
        ...detalle,
        total: linea.total
    };
}

/**
 * Función específica para tickets - mantiene compatibilidad
 * @param {Array} detalles - Array de detalles del ticket
 * @returns {number} Total del ticket
 */
export function calcularTotalTicket(detalles) {
    return calcularTotalesDocumento(detalles).total_final;
}

/**
 * Función específica para facturas - mantiene compatibilidad
 * @param {Array} detalles - Array de detalles de la factura
 * @returns {number} Total de la factura
 */
export function calcularTotalFactura(detalles) {
    return calcularTotalesDocumento(detalles).total_final;
}

/**
 * Función específica para proformas - mantiene compatibilidad
 * @param {Array} detalles - Array de detalles de la proforma
 * @returns {number} Total de la proforma
 */
export function calcularTotalProforma(detalles) {
    return calcularTotalesDocumento(detalles).total_final;
}

/**
 * Función específica para presupuestos - mantiene compatibilidad
 * @param {Array} detalles - Array de detalles del presupuesto
 * @returns {number} Total del presupuesto
 */
export function calcularTotalPresupuesto(detalles) {
    return calcularTotalesDocumento(detalles).total_final;
}

/**
 * Calcula el precio unitario (sin IVA) a partir del total de la línea (con IVA),
 * la cantidad e IVA%. Devuelve el precio con 5 decimales.
 * Nota: aproximación práctica invirtiendo el factor de IVA y redondeando el subtotal a 2 decimales.
 * @param {number|string} totalLinea
 * @param {number|string} cantidad
 * @param {number|string} iva
 * @returns {number}
 */
export function calcularPrecioDesdeTotal(totalLinea, cantidad, iva) {
    const t = typeof totalLinea === 'number' ? totalLinea : parsearImporte(totalLinea);
    const c = typeof cantidad === 'number' ? cantidad : parsearImporte(cantidad);
    const iv = typeof iva === 'number' ? iva : parsearImporte(iva);
    if (!c || c <= 0) return 0;
    const factor = 1 + (Number(iv) / 100);
    // Estimar subtotal (sin IVA) redondeado a 2 decimales
    const subtotalAprox = Number((Number(t) / factor).toFixed(2));
    const precio = subtotalAprox / Number(c);
    return Number(precio.toFixed(5));
}

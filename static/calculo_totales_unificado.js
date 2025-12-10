/**
 * MÓDULO DE CÁLCULO DE TOTALES UNIFICADO
 * 
 * Este módulo centraliza todos los cálculos de totales para garantizar
 * consistencia absoluta entre gestión, impresión y PDF en:
 * - Tickets, Facturas, Proformas, Presupuestos
 * 
 * REGLA FUNDAMENTAL (Solicitada por usuario): 
 * 1) Subtotal línea = ROUND(precio * cantidad, 2)
 * 2) Base Imponible = SUMA(Subtotales línea redondeados)
 * 3) IVA = ROUND(Base Imponible * %IVA, 2) (Cálculo global, no por línea)
 * 4) Total = Base Imponible + IVA
 */

import { parsearImporte, redondearImporte } from './scripts_utils.js';

/**
 * Calcula el total de una línea de detalle con redondeo correcto
 * @param {number|string} precio - Precio unitario
 * @param {number|string} cantidad - Cantidad
 * @param {number|string} iva - Porcentaje de IVA (ej: 21 para 21%)
 * @returns {Object} { subtotal, iva_importe, total }
 */
export function calcularTotalLinea(precio, cantidad, iva) {
    const precioNum = typeof precio === 'number' ? precio : parsearImporte(precio);
    const cantidadNum = typeof cantidad === 'number' ? cantidad : parsearImporte(cantidad);
    const ivaNum = typeof iva === 'number' ? iva : parsearImporte(iva);
    
    // 1) Subtotal línea = ROUND(precio * cantidad, 2)
    const subtotalRaw = precioNum * cantidadNum;
    const subtotal = redondearImporte(subtotalRaw);
    
    // IVA de la línea (informativo, para visualización en línea)
    // Nota: El IVA total del documento NO será la suma de estos valores
    const iva_importe = redondearImporte(subtotal * (ivaNum / 100));
    
    // Total de línea (informativo)
    const total = redondearImporte(subtotal + iva_importe);
    
    return {
        subtotal: subtotal,
        iva_importe: iva_importe,
        total: total
    };
}

/**
 * Mantiene compatibilidad con código antiguo que usaba calcularLinea
 */
export const calcularLinea = calcularTotalLinea;

/**
 * Calcula los totales de un documento completo aplicando la regla de IVA global
 * @param {Array} detalles - Array de detalles con {precio, cantidad, impuestos}
 * @returns {Object} { subtotal_total, iva_total, total_final }
 */
export function calcularTotalesDocumento(detalles) {
    let subtotal_total = 0; // Base Imponible Total
    const bases_por_iva = {}; // Acumulador de bases por tipo de IVA
    
    // 1) y 2) Calcular subtotales redondeados y acumular bases
    (detalles || []).forEach(detalle => {
        const precio = typeof detalle.precio === 'number' ? detalle.precio : parsearImporte(detalle.precio);
        const cantidad = typeof detalle.cantidad === 'number' ? detalle.cantidad : parsearImporte(detalle.cantidad);
        // Detectar campo de impuesto (impuestos o iva)
        const ivaPerc = typeof detalle.impuestos !== 'undefined' ? detalle.impuestos : (detalle.iva || 0);
        const iva = typeof ivaPerc === 'number' ? ivaPerc : parsearImporte(ivaPerc);
        
        // Subtotal de línea redondeado
        const subtotalLinea = redondearImporte(precio * cantidad);
        
        // Acumular al total de base imponible
        subtotal_total += subtotalLinea;
        
        // Acumular base por tipo de IVA
        if (!bases_por_iva[iva]) bases_por_iva[iva] = 0;
        bases_por_iva[iva] += subtotalLinea;
    });
    
    // 3) Calcular IVA global sobre las bases acumuladas
    let iva_total = 0;
    for (const [ivaPerc, base] of Object.entries(bases_por_iva)) {
        // IVA = ROUND(Base * %IVA, 2)
        const cuota = redondearImporte(base * (parseFloat(ivaPerc) / 100));
        iva_total += cuota;
    }
    
    // Redondear finales (aunque ya deberían estarlo al sumar redondeados, precaución)
    subtotal_total = redondearImporte(subtotal_total);
    iva_total = redondearImporte(iva_total);
    
    // 4) Total = Base Imponible + IVA
    const total_final = redondearImporte(subtotal_total + iva_total);
    
    return {
        subtotal_total: subtotal_total,   // Base Imponible
        iva_total: iva_total,             // Cuota IVA Total
        total_final: total_final          // Total Documento
    };
}

/**
 * Mantiene compatibilidad con código antiguo que usaba calcularDocumento
 */
export function calcularDocumento(detalles) {
    const tot = calcularTotalesDocumento(detalles);
    // Adaptar formato de retorno antiguo si es necesario
    // El antiguo devolvía { importe_bruto, iva, total, lineas }
    // Recalculamos lineas para devolverlas
    const lineas = (detalles || []).map(d => {
        const iva = typeof d.impuestos !== 'undefined' ? d.impuestos : (d.iva || 21);
        return calcularTotalLinea(d.precio, d.cantidad, iva);
    });
    
    return {
        importe_bruto: tot.subtotal_total,
        iva: tot.iva_total,
        total: tot.total_final,
        lineas
    };
}

/**
 * Helper para recalcular totales del documento
 */
export function recalcularTotales(detalles = []) {
  const { subtotal_total, iva_total, total_final } = calcularTotalesDocumento(detalles);
  return { 
      importe_bruto: subtotal_total, 
      iva: iva_total, 
      total: total_final 
  };
}

/**
 * Suma totales de varios documentos
 */
export function sumarTotales(docs = []) {
  return (docs || []).reduce((acc, d) => {
    acc.importe_bruto += parsearImporte(d?.importe_bruto) || 0;
    acc.iva += parsearImporte(d?.iva) || 0;
    acc.total += parsearImporte(d?.total) || 0;
    return acc;
  }, { importe_bruto: 0, iva: 0, total: 0 });
}

export function actualizarDetalleConTotal(detalle) {
    const iva = typeof detalle.impuestos !== 'undefined' ? detalle.impuestos : (detalle.iva || 0);
    const linea = calcularTotalLinea(
        detalle.precio, 
        detalle.cantidad, 
        iva
    );
    
    return {
        ...detalle,
        total: linea.total
    };
}

// Funciones específicas de compatibilidad
export function calcularTotalTicket(detalles) {
    return calcularTotalesDocumento(detalles).total_final;
}

export function calcularTotalFactura(detalles) {
    return calcularTotalesDocumento(detalles).total_final;
}

export function calcularTotalProforma(detalles) {
    return calcularTotalesDocumento(detalles).total_final;
}

export function calcularTotalPresupuesto(detalles) {
    return calcularTotalesDocumento(detalles).total_final;
}

/**
 * Calcula el precio unitario (sin IVA) a partir del total de la línea (con IVA)
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

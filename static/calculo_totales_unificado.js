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
    
    const subtotal = precioNum * cantidadNum;
    
    // CRÍTICO: Redondear IVA por línea a 2 decimales
    const iva_importe = Number((subtotal * (ivaNum / 100)).toFixed(2));
    
    // Total de línea = subtotal + IVA redondeado
    const total = Number((subtotal + iva_importe).toFixed(2));
    
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
    let total_final = 0;
    
    detalles.forEach(detalle => {
        const linea = calcularTotalLinea(
            detalle.precio, 
            detalle.cantidad, 
            detalle.impuestos || detalle.iva || 0
        );
        
        subtotal_total += linea.subtotal;
        iva_total += linea.iva_importe;
        total_final += linea.total;
    });
    
    // Redondear totales finales para evitar errores de precisión flotante
    return {
        subtotal_total: Number(subtotal_total.toFixed(2)),
        iva_total: Number(iva_total.toFixed(2)),
        total_final: Number(total_final.toFixed(2))
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

/**
 * imprimir.js
 * 
 * Este script maneja la acción de imprimir desde la página principal.
 */

/**
 * Función para imprimir el ticket.
 * @param {string} idTicket - El ID del ticket a imprimir.
 */
function imprimirFactura(idTicket) {
   
    // Construir la URL para la página de impresión con el parámetro 'ticketId'
    const urlImprimir = `/api/imprimir-ticket.html?ticketId=${encodeURIComponent(idTicket)}`;

    // Abrir una nueva ventana con la página de impresión
    window.open(urlImprimir, '_blank', 'width=800,height=600');
}


export function calcularImportes(cantidad, precio, impuestos) {
    const subtotal = cantidad * precio;
    const iva = Math.round(subtotal * (impuestos / 100) * 100) / 100;
    const total = Math.round((subtotal + iva) * 100) / 100;
    return { subtotal, iva, total };
}

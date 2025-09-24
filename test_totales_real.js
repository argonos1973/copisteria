// Función para simular el problema real de cálculo de totales
function testCalculoTotalesReal() {
  console.log('=== TEST DE CÁLCULO DE TOTALES REAL ===');
  
  // Simular cómo se hace en gestion_facturas.js
  console.log('\n--- Simulando gestión de facturas ---');
  
  // Supongamos que tenemos una tabla con detalles
  const detallesEjemplo = [
    { totalTexto: '999,50 €' },
    { totalTexto: '1.000,50 €' },
    { totalTexto: '1.234,56 €' }
  ];
  
  let total_factura = 0;
  
  detallesEjemplo.forEach((detalle, index) => {
    const totalTexto = detalle.totalTexto.trim().replace('€', '').replace(',', '.').trim();
    const total = parseFloat(totalTexto) || 0;
    
    total_factura += total;
    console.log(`Detalle ${index + 1}: ${detalle.totalTexto} -> ${totalTexto} -> ${total}`);
  });
  
  console.log(`Total factura: ${total_factura}`);
  
  // Formatear el total como se hace en gestion_facturas.js
  const totalFormateado = total_factura.toLocaleString('es-ES', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    useGrouping: true
  }) + ' €';
  
  console.log(`Total formateado: ${totalFormateado}`);
  
  // Ahora veamos qué pasa si intentamos parsear este total formateado
  console.log('\n--- Probando parseo del total formateado ---');
  const totalTextoFormateado = totalFormateado.trim().replace('€', '').replace(',', '.').trim();
  const totalParseado = parseFloat(totalTextoFormateado) || 0;
  console.log(`Total formateado: ${totalFormateado} -> ${totalTextoFormateado} -> ${totalParseado}`);
  
  console.log('\n=== PROBLEMA IDENTIFICADO ===');
  console.log('El problema está en el reemplazo:');
  console.log('1. Se reemplaza "€" por ""');
  console.log('2. Se reemplaza "," por "."');
  console.log('3. Pero NO se reemplaza "." por ""');
  console.log('');
  console.log('Cuando tenemos "1.236,89 €":');
  console.log('- Después de quitar €: "1.236,89"');
  console.log('- Después de reemplazar , por .: "1.236.89"');
  console.log('- parseFloat de "1.236.89" da: 1.236 (se pierde la parte decimal)');
  
  // Demostración del problema
  console.log('\n=== DEMOSTRACIÓN DEL PROBLEMA ===');
  const ejemploProblematico = '1.236,89 €';
  console.log(`Ejemplo: ${ejemploProblematico}`);
  
  const paso1 = ejemploProblematico.trim().replace('€', '');
  console.log(`Paso 1 (quitar €): "${paso1}"`);
  
  const paso2 = paso1.trim().replace(',', '.');
  console.log(`Paso 2 (reemplazar , por .): "${paso2}"`);
  
  const paso3 = parseFloat(paso2) || 0;
  console.log(`Paso 3 (parseFloat): ${paso3}`);
  
  console.log('\n¡ERROR! Debería ser 1236.89, pero es 1.236');
  
  // Solución correcta
  console.log('\n=== SOLUCIÓN CORRECTA ===');
  const solucionCorrecta = ejemploProblematico.trim().replace(/\./g, '').replace(',', '.').replace('€', '').trim();
  const numeroCorrecto = parseFloat(solucionCorrecta) || 0;
  console.log(`Solución correcta: "${solucionCorrecta}" -> ${numeroCorrecto}`);
}

testCalculoTotalesReal();

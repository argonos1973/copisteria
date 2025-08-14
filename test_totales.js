// Función para simular el problema de cálculo de totales
function testCalculoTotales() {
  // Simular el problema con números mayores que 999
  console.log('=== TEST DE CÁLCULO DE TOTALES ===');
  
  // Caso 1: Importe menor que 1000 (sin separador de miles)
  const importe1 = '999,50 €';
  const limpio1 = importe1.replace(/\./g, '').replace(',', '.').replace(' €', '').trim();
  const numero1 = parseFloat(limpio1) || 0;
  console.log(`Importe 1: ${importe1} -> Limpio: ${limpio1} -> Número: ${numero1}`);
  
  // Caso 2: Importe mayor que 1000 (con separador de miles)
  const importe2 = '1.000,50 €';
  const limpio2 = importe2.replace(/\./g, '').replace(',', '.').replace(' €', '').trim();
  const numero2 = parseFloat(limpio2) || 0;
  console.log(`Importe 2: ${importe2} -> Limpio: ${limpio2} -> Número: ${numero2}`);
  
  // Caso 3: Importe mayor que 1000 (con múltiples separadores de miles)
  const importe3 = '1.234.567,89 €';
  const limpio3 = importe3.replace(/\./g, '').replace(',', '.').replace(' €', '').trim();
  const numero3 = parseFloat(limpio3) || 0;
  console.log(`Importe 3: ${importe3} -> Limpio: ${limpio3} -> Número: ${numero3}`);
  
  // Mostrar el problema
  console.log('\n=== PROBLEMA IDENTIFICADO ===');
  console.log('Cuando hay separadores de miles (puntos), se eliminan todos los puntos');
  console.log('Esto convierte "1.000,50" en "1000,50" y luego en "1000.50"');
  console.log('El resultado es correcto en este caso.');
  
  // Pero veamos qué pasa con el formateo
  const total = numero1 + numero2 + numero3;
  console.log(`\nTotal sin formatear: ${total}`);
  
  // Formatear como se hace en formatearImporte
  const totalFormateado = total.toLocaleString('es-ES', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    useGrouping: true
  }) + ' €';
  
  console.log(`Total formateado: ${totalFormateado}`);
  
  // Ahora probemos el proceso inverso
  console.log('\n=== PROCESO INVERSO ===');
  const importeParaParsear = totalFormateado;
  const limpio = importeParaParsear.replace(/\./g, '').replace(',', '.').replace(' €', '').trim();
  const numero = parseFloat(limpio) || 0;
  console.log(`Importe formateado: ${importeParaParsear} -> Limpio: ${limpio} -> Número: ${numero}`);
  
  console.log('\n=== CONCLUSIÓN ===');
  console.log('El problema NO está en el reemplazo de puntos por comas,');
  console.log('sino en cómo se manejan los números grandes en el cálculo.');
}

testCalculoTotales();

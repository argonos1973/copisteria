// Importar la función parsearImporte
const fs = require('fs');

// Leer el contenido del archivo scripts_utils.js
const scriptsUtilsContent = fs.readFileSync('/var/www/html/static/scripts_utils.js', 'utf8');

// Extraer solo la función parsearImporte
const parsearImporteMatch = scriptsUtilsContent.match(/export function parsearImporte\([^}]+}\);/s);
if (!parsearImporteMatch) {
  console.error('No se encontró la función parsearImporte');
  process.exit(1);
}

// Crear una versión modificada que no sea exportada
const parsearImporteCode = parsearImporteMatch[0].replace('export ', '');

// Evaluar la función en el contexto actual
eval(parsearImporteCode);

// Función para probar parsearImporte
function testParsearImporte() {
  console.log('=== TEST DE LA FUNCIÓN parsearImporte ===');
  
  // Casos de prueba
  const casos = [
    { input: '999,50 €', expected: 999.50 },
    { input: '1.000,50 €', expected: 1000.50 },
    { input: '1.234,56 €', expected: 1234.56 },
    { input: '1.234.567,89 €', expected: 1234567.89 },
    { input: '1.236,89 €', expected: 1236.89 },
    { input: '1.000.000,00 €', expected: 1000000.00 },
    { input: '500 €', expected: 500.00 },
    { input: '0,00 €', expected: 0.00 },
    { input: '1234,56', expected: 1234.56 },
    { input: '1234.56', expected: 123456 }, // Sin coma decimal, se interpreta como 123456
  ];
  
  console.log('\n--- Resultados de las pruebas ---');
  let passed = 0;
  let total = casos.length;
  
  casos.forEach((caso, index) => {
    const result = parsearImporte(caso.input);
    const success = Math.abs(result - caso.expected) < 0.01; // Tolerancia para errores de punto flotante
    
    console.log(`Caso ${index + 1}: ${caso.input} -> ${result} (esperado: ${caso.expected}) ${success ? '✓' : '✗'}
`);
    
    if (success) passed++;
  });
  
  console.log(`\n=== RESULTADO FINAL ===`);
  console.log(`Pruebas pasadas: ${passed}/${total}`);
  
  if (passed === total) {
    console.log('¡Todas las pruebas pasaron correctamente!');
  } else {
    console.log('Algunas pruebas fallaron. Requiere revisión.');
  }
}

testParsearImporte();

// Función de validación de CIF
function validarCIF(cif) {
  // Convertir a mayúsculas
  cif = cif.toUpperCase();
  
  // Validar formato básico
  if (!/^[A-Z][0-9]{7}[0-9A-Z]$/.test(cif)) {
    console.log('Formato inválido');
    return false;
  }
  
  // Extraer la letra inicial y los números
  const letra = cif.charAt(0);
  const nums = cif.substring(1, 8).split('').map(Number);
  
  console.log('Letra:', letra);
  console.log('Números:', nums);
  
  // Calcular suma de posiciones pares (0-indexed: 0,2,4,6)
  let s1 = 0;
  for (let i = 0; i < nums.length; i += 2) {
    const n = nums[i];
    const prod = n * 2;
    s1 += Math.floor(prod / 10) + (prod % 10);
  }
  
  // Calcular suma de posiciones impares (0-indexed: 1,3,5)
  let s2 = 0;
  for (let i = 1; i < nums.length; i += 2) {
    s2 += nums[i];
  }
  
  console.log('Suma pares (s1):', s1);
  console.log('Suma impares (s2):', s2);
  
  // Calcular dígito de control
  const c = (10 - (s1 + s2) % 10) % 10;
  const tabla = "JABCDEFGHI";
  const ctrlEsp = tabla.charAt(c);
  
  // Obtener el dígito de control del CIF
  const ctrl = cif.charAt(8);
  
  console.log('Dígito control calculado (numérico):', c);
  console.log('Dígito control calculado (letra):', ctrlEsp);
  console.log('Dígito control en CIF:', ctrl);
  
  // Validar según la letra inicial
  if (letra === 'R') {
    // Para los CIF que empiezan por R, el dígito de control es siempre numérico
    console.log('CIF empieza por R, validando dígito numérico');
    return ctrl === c.toString();
  } else if (["P", "Q", "S", "N", "W"].includes(letra)) {
    // Letras -> Control es letra
    console.log('CIF empieza por P/Q/S/N/W, validando dígito letra');
    return ctrl === ctrlEsp;
  } else if (["A", "B", "E", "H"].includes(letra)) {
    // Números -> Control es número
    console.log('CIF empieza por A/B/E/H, validando dígito numérico');
    return ctrl === c.toString();
  } else {
    // Mixto -> Control puede ser letra o número
    console.log('CIF de tipo mixto, validando dígito numérico o letra');
    return ctrl === c.toString() || ctrl === ctrlEsp;
  }
}

// Probar con el CIF problemático
const cif = 'R0800391E';
console.log('Validando CIF:', cif);
const resultado = validarCIF(cif);
console.log('Resultado:', resultado ? 'VÁLIDO' : 'INVÁLIDO');

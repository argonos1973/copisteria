// Función de validación de CIF (implementación corregida)
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
  const numeros = cif.substring(1, 8);
  const control = cif.charAt(8);
  
  console.log('Letra:', letra);
  console.log('Números:', numeros);
  console.log('Control:', control);
  
  // Sumar los dígitos pares (posiciones 1, 3, 5 en substring)
  let sumaPares = 0;
  for (let i = 1; i < 7; i += 2) {
    sumaPares += parseInt(numeros.charAt(i), 10);
    console.log('Sumando dígito par en posición', i, ':', parseInt(numeros.charAt(i), 10));
  }
  
  console.log('Suma pares:', sumaPares);
  
  // Sumar los dígitos impares después de multiplicarlos por 2 (posiciones 0, 2, 4, 6 en substring)
  let sumaImpares = 0;
  for (let i = 0; i < 7; i += 2) {
    let temp = parseInt(numeros.charAt(i), 10) * 2;
    sumaImpares += Math.floor(temp / 10) + (temp % 10);
    console.log('Sumando dígito impar en posición', i, ':', parseInt(numeros.charAt(i), 10), '->', temp, '->', Math.floor(temp / 10), '+', (temp % 10));
  }
  
  console.log('Suma impares:', sumaImpares);
  
  const sumaTotal = sumaPares + sumaImpares;
  const unidad = sumaTotal % 10;
  const controlNumero = (unidad === 0) ? 0 : 10 - unidad;
  
  console.log('Suma total:', sumaTotal);
  console.log('Unidad:', unidad);
  console.log('Control numérico:', controlNumero);
  
  // Letras de control para CIF
  const letrasControl = "JABCDEFGHI";
  const controlLetraEsperada = letrasControl.charAt(controlNumero);
  
  console.log('Control letra esperada:', controlLetraEsperada);
  
  // Determinar si el control es un dígito o una letra
  if (/[PQSKW]/.test(letra)) {
    // Control debe ser una letra
    console.log('CIF empieza por P/Q/S/K/W, validando dígito letra');
    return control === controlLetraEsperada;
  } else {
    // Control debe ser un dígito
    console.log('CIF empieza por otra letra, validando dígito numérico');
    return control === controlNumero.toString();
  }
}

// Probar con el CIF problemático
const cif = 'R0800391E';
console.log('Validando CIF:', cif);
const resultado = validarCIF(cif);
console.log('Resultado:', resultado ? 'VÁLIDO' : 'INVÁLIDO');

// Función de validación de CIF (implementación corregida)
function validarCIF(cif) {
  // Convertir a mayúsculas
  cif = cif.toUpperCase();
  
  // Validar formato básico
  if (!/^[A-Z][0-9]{7}[0-9A-Z]$/.test(cif)) {
    console.log('Formato inválido');
    return false;
  }
  
  // Extraer los números
  const nums = cif.substring(1, 8).split('').map(Number);
  
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
  
  console.log('Números:', nums);
  console.log('Suma pares (s1):', s1);
  console.log('Suma impares (s2):', s2);
  
  // Calcular dígito de control
  const c = (10 - (s1 + s2) % 10) % 10;
  const tabla = "JABCDEFGHI";
  const letra = cif.charAt(0);
  const ctrl = cif.charAt(8);
  
  console.log('Dígito control calculado (c):', c);
  console.log('Letra:', letra);
  console.log('Control en CIF:', ctrl);
  
  // Determinar control esperado según la letra inicial
  let ctrl_esp;
  if (["P", "Q", "R", "S", "N", "W"].includes(letra)) {
    // Control es letra
    ctrl_esp = tabla[c];
    console.log('Control esperado (letra):', ctrl_esp);
  } else if (["A", "B", "E", "H"].includes(letra)) {
    // Control es número
    ctrl_esp = c.toString();
    console.log('Control esperado (número):', ctrl_esp);
  } else {
    // Control puede ser letra o número
    ctrl_esp = [c.toString(), tabla[c]];
    console.log('Control esperado (ambos):', ctrl_esp);
  }
  
  // Validar
  let resultado;
  if (typeof ctrl_esp === 'string') {
    resultado = ctrl === ctrl_esp;
    console.log('Comparando', ctrl, 'con', ctrl_esp, ':', resultado);
  } else {
    resultado = ctrl_esp.includes(ctrl);
    console.log('Verificando si', ctrl, 'está en', ctrl_esp, ':', resultado);
  }
  
  return resultado;
}

// Probar con el CIF problemático
const cif = 'R0800391E';
console.log('Validando CIF:', cif);
const resultado = validarCIF(cif);
console.log('Resultado:', resultado ? 'VÁLIDO' : 'INVÁLIDO');

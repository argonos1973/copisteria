import { IP_SERVER, PORT } from './constantes.js';
import { mostrarNotificacion } from './notificaciones.js';

const { createApp, ref, reactive, watch, onMounted } = Vue;

createApp({
  setup() {
    
    const API_URL = `http://${IP_SERVER}:${PORT}/api/contactos`; // Ajusta tu endpoint

    // Estado del formulario
    const contacto = reactive({
      razonsocial: '',
      identificador: '',
      mail: '',
      telf1: '',
      telf2: '',
      direccion: '',
      cp: '',
      poblacio: '',
      provincia: ''
    });

    // Estado de las validaciones
    const valid = reactive({
      identificador: false,
      mail: false,
      telf1: true,
      telf2: true,
      cp: false
    });

    // Mensajes de error o éxito
    const message = reactive({
      text: '',
      type: '' // 'success' o 'error'
    });

    // Modo edición
    const isEditMode = ref(false);

    // Obtener el ID de contacto de la URL
    const getParametroId = () => {
      const urlParams = new URLSearchParams(window.location.search);
      return urlParams.get('id');
    };
    const idContacto = getParametroId();

    // Cargar datos del contacto (modo edición)
    const cargarContacto = async () => {
      if (!idContacto) return;
      isEditMode.value = true;

      try {
        const response = await axios.get(`${API_URL}/get_contacto/${idContacto}`);
        if (response.status === 200) {
          Object.assign(contacto, response.data);
          console.log(contacto.cp);
        } else {
          console.error("Error al cargar contacto:", response.data);
        }
      } catch (error) {
        console.error('Error al cargar el contacto:', error);
      }
    };

    // Manejar entrada del CP (sin lista desplegable)
    const handleCP = async (nuevoCP) => {
      // Si no son 5 dígitos, limpiamos población y provincia
      valid.cp = false;
      
      if (nuevoCP.trim().length < 5) {
        contacto.poblacio = '';
        contacto.provincia = '';
        return;
      }

      // Si son 5 dígitos, buscamos en la BD
      if (nuevoCP.trim().length === 5) {
        try {
          const response = await axios.get(`${API_URL}/get_cp`, {
            params: { cp: nuevoCP.trim() }
          });
          
          if (Array.isArray(response.data) && response.data.length > 0) {
            // Asumimos que el primer resultado es el correcto
            const resultado = response.data[0];
            contacto.poblacio = resultado.poblacio;
            contacto.provincia = resultado.provincia;
            valid.cp = true;
          } else {
            // Si no hay resultados, limpiamos
            contacto.poblacio = '';
            contacto.provincia = '';
          }
        } catch (error) {
          // Si da 404 u otro error, limpiamos
          contacto.poblacio = '';
          contacto.provincia = '';
        }
      }
    };

    // Validación de identificador
    const validateIdentificador = () => {
      const identificador = contacto.identificador.toUpperCase();

      if (identificador.indexOf('/') !== -1) {
        valid.identificador = true;
        return true;
      }

      const nifPattern = /^[0-9]{8}[A-Z]$/;
      const niePattern = /^[XYZ][0-9]{7}[A-Z]$/;
      const cifPattern = /^[ABCDEFGHJNPQRSUVW][0-9]{7}[0-9A-J]$/;

      valid.identificador = false;

      // Tabla de letras para NIF y NIE
      const letrasNIF = "TRWAGMYFPDXBNJZSQVHLCKET";

      // Función para validar NIF
      const validarNIF = (nif) => {
        const numero = nif.substring(0, 8);
        const letra = nif.charAt(8);
        const indice = parseInt(numero, 10) % 23;
        const letraEsperada = letrasNIF.charAt(indice);
        return letra === letraEsperada;
      };

      // Función para validar NIE
      const validarNIE = (nie) => {
        const primeraLetra = nie.charAt(0);
        let numero;
        switch (primeraLetra) {
          case 'X':
            numero = '0' + nie.substring(1, 8);
            break;
          case 'Y':
            numero = '1' + nie.substring(1, 8);
            break;
          case 'Z':
            numero = '2' + nie.substring(1, 8);
            break;
          default:
            return false;
        }
        const letra = nie.charAt(8);
        const indice = parseInt(numero, 10) % 23;
        const letraEsperada = letrasNIF.charAt(indice);
        return letra === letraEsperada;
      };

      // Función para validar CIF
      const validarCIF = (cif) => {
        const letraInicial = cif.charAt(0);
        const numeros = cif.substring(1, 8);
        const control = cif.charAt(8);

        // Sumar los dígitos pares
        let sumaPares = 0;
        for (let i = 1; i < 7; i += 2) {
          sumaPares += parseInt(numeros.charAt(i), 10);
        }

        // Sumar los dígitos impares después de multiplicarlos por 2
        let sumaImpares = 0;
        for (let i = 0; i < 7; i += 2) {
          let temp = parseInt(numeros.charAt(i), 10) * 2;
          sumaImpares += Math.floor(temp / 10) + (temp % 10);
        }

        const sumaTotal = sumaPares + sumaImpares;
        const unidad = sumaTotal % 10;
        const controlNumero = (unidad === 0) ? 0 : 10 - unidad;

        // Letras de control para CIF
        const letrasControl = "JABCDEFGHI";
        const controlLetraEsperada = letrasControl.charAt(controlNumero);

        // Determinar si el control es un dígito o una letra
        if (/[PQSKW]/.test(letraInicial)) {
          // Control debe ser una letra
          return control === controlLetraEsperada;
        } else {
          // Control debe ser un dígito
          return control === controlNumero.toString();
        }
      };

      // Validación según el tipo de identificador
      if (nifPattern.test(identificador)) {
        valid.identificador = validarNIF(identificador);
      } else if (niePattern.test(identificador)) {
        valid.identificador = validarNIE(identificador);
      } else if (cifPattern.test(identificador)) {
        valid.identificador = validarCIF(identificador);
      }
    };

    // Validación de correo electrónico
    const validateEmail = () => {
      const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      valid.mail = emailPattern.test(contacto.mail.trim());
    };

    // Validación de teléfono 1
    const validateTelf1 = () => {
      const telfPattern = /^[0-9]{9,10}$/;
      // Campo opcional (si está vacío, se toma como válido)
      valid.telf1 =
        contacto.telf1.trim() === '' || telfPattern.test(contacto.telf1.trim());
    };

    // Validación de teléfono 2
    const validateTelf2 = () => {
      const telfPattern = /^[0-9]{9,10}$/;
      // Campo opcional (si está vacío, se toma como válido)
      valid.telf2 =
        contacto.telf2.trim() === '' || telfPattern.test(contacto.telf2.trim());
    };

    // Validación del CP
    const validateCP = () => {
      const cpPattern = /^[0-9]{5}$/;
      // Comprobamos que el CP cumple el patrón y que poblacio y provincia no están vacíos
      valid.cp =
        cpPattern.test(contacto.cp.trim()) &&
        contacto.poblacio !== '' &&
        contacto.provincia !== '';
    };

    const handleSubmit = async () => {
      validateIdentificador();
      validateEmail();
      validateTelf1();
      validateTelf2();
      validateCP();

      const isValid =
        valid.identificador && valid.mail && valid.telf1 && valid.telf2;

      if (!isValid) {
        message.text = 'Por favor, corrige los errores en el formulario.';
        message.type = 'error';
        // Mostrar notificación de error
        mostrarNotificacion(message.text, 'error');
        return;
      }

      // Datos a enviar (con transformaciones)
      const contactData = {
        razonsocial: contacto.razonsocial.trim().toUpperCase(),
        identificador: contacto.identificador.trim().toUpperCase(),
        mail: contacto.mail.trim(),
        telf1: contacto.telf1.trim(),
        telf2: contacto.telf2.trim(),
        direccion: contacto.direccion?.trim() || '',
        cp: contacto.cp,
        localidad: contacto.poblacio.trim(),
        provincia: contacto.provincia.trim(),
        tipo: ''
      };

      try {
        let response;
        if (isEditMode.value) {
          response = await axios.put(`${API_URL}/update_contacto/${idContacto}`, contactData);
        } else {
          response = await axios.post(`${API_URL}/create_contacto`, contactData);
        }
        
        // Determinar la acción basada en el modo
        const accion = isEditMode.value ? 'actualizado' : 'creado';
        
        if (response.status === 200 || response.status === 201) {
          // Mostrar notificación de éxito
          mostrarNotificacion(`Contacto ${accion} exitosamente.`);
          // Si no estamos en modo edición, reseteamos formulario
          if (!isEditMode.value) resetForm();
        } else {
          // Mostrar notificación de error si el status no es 200/201
          mostrarNotificacion('Error al guardar el contacto.', 'error');
        }
      } catch (error) {
        if (error.response) {
          // La respuesta fue hecha y el servidor respondió con un código de estado fuera del rango 2xx
          console.error('Datos de error:', error.response.data);
          console.error('Estado de error:', error.response.status);
          console.error('Headers de error:', error.response.headers);
          const errorMsg = error.response.data.message || 'Error al guardar el contacto.';
          message.text = errorMsg;
          message.type = 'error';
          mostrarNotificacion(errorMsg, 'error');
        } else {
          // Manejo de otros tipos de errores (opcional)
          const errorMsg = 'Ocurrió un error inesperado.';
          message.text = errorMsg;
          message.type = 'error';
          mostrarNotificacion(errorMsg, 'error');
        }

        // Limpiar mensaje tras 5 segundos
        setTimeout(() => {
          message.text = '';
          message.type = '';
        }, 5000);
      }
    };

    // Resetear el formulario
    const resetForm = () => {
      Object.keys(contacto).forEach((key) => {
        contacto[key] = '';
      });
      Object.keys(valid).forEach((key) => {
        valid[key] = false;
      });
      message.text = '';
      message.type = '';
    };

    // Volver a la consulta de contactos
    const volverAConsulta = () => {
      window.location.href = 'CONSULTA_CONTACTOS.html';
    };

    // Watchers
    watch(() => contacto.identificador, validateIdentificador);
    watch(() => contacto.mail, validateEmail);
    watch(() => contacto.telf1, validateTelf1);
    watch(() => contacto.telf2, validateTelf2);
    watch(() => contacto.cp, (nuevoCP) => {
      handleCP(nuevoCP);
    });

    // Métodos y variables añadidas para autocompletado
    // Reactive variables for direccion suggestions
    const direccionSuggestions = ref([]);
    const showSuggestions = ref(false);
    let debounceTimeout = null; // Declaración única

    // Método para obtener sugerencias de dirección con debounce
    const fetchDireccionSuggestions = () => {
      const query = contacto.direccion.trim();

      // Limita las búsquedas a cadenas con al menos 2 caracteres
      if (query.length < 2) {
        direccionSuggestions.value = [];
        showSuggestions.value = false;
        return;
      }

      // Implementa un debounce de 300ms para evitar llamadas excesivas
      clearTimeout(debounceTimeout);
      debounceTimeout = setTimeout(async () => {
        try {
          const response = await axios.get(`${API_URL}/searchCarrer`, { params: { q: query } });
          direccionSuggestions.value = response.data.slice(0, 10);
          showSuggestions.value = true;
        } catch (error) {
          console.error('Error fetching direccion suggestions:', error);
          direccionSuggestions.value = [];
          showSuggestions.value = false;
        }
      }, 300);
    };

    // Método para seleccionar una sugerencia de dirección
    const selectDireccion = (suggestion) => {
      contacto.direccion = suggestion.carrer.toUpperCase();
      contacto.cp = suggestion.cp;
      direccionSuggestions.value = [];
      showSuggestions.value = false;

      // Opcional: Actualizar población y provincia automáticamente
      handleCP(contacto.cp);
    };

    // Método para ocultar las sugerencias al perder el foco
    const hideSuggestions = () => {
      // Oculta las sugerencias después de un breve retraso para permitir el clic
      setTimeout(() => {
        showSuggestions.value = false;
      }, 100);
    };

    // Cargar datos del contacto al montar el componente
    onMounted(() => {
      cargarContacto();
    });

    return {
      contacto,
      valid,
      message,
      isEditMode,
      handleSubmit,
      volverAConsulta,
      handleCP,
      direccionSuggestions,      // Añadido
      showSuggestions,          // Añadido
      fetchDireccionSuggestions, // Añadido
      selectDireccion,          // Añadido
      hideSuggestions           // Añadido
    };
  }
}).mount('#app');

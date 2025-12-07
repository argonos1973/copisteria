// crear_empresa.js - Gestión de creación de empresa

// Preview del logo
document.getElementById('logoInput').addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    // Validar tamaño (5MB)
    if (file.size > 5 * 1024 * 1024) {
        mostrarAlerta('El logo no puede superar 5MB', 'danger');
        this.value = '';
        return;
    }
    
    // Validar tipo
    const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp'];
    if (!validTypes.includes(file.type)) {
        mostrarAlerta('Formato no válido. Use PNG, JPG, JPEG, GIF o WEBP', 'danger');
        this.value = '';
        return;
    }
    
    // Mostrar preview
    const reader = new FileReader();
    reader.onload = function(e) {
        const preview = document.getElementById('logoPreview');
        preview.innerHTML = `<img src="${e.target.result}" alt="Logo preview">`;
        document.getElementById('removeLogo').style.display = 'inline-block';
    };
    reader.readAsDataURL(file);
});

// Función para quitar el logo
window.removeLogoPreview = function() {
    document.getElementById('logoInput').value = '';
    document.getElementById('logoPreview').innerHTML = `
        <i class="fas fa-building" style="font-size: 48px; color: #ccc;"></i>
        <p style="margin-top: 10px; color: #999;">Sin logo</p>
    `;
    document.getElementById('removeLogo').style.display = 'none';
};

// Enviar formulario
document.getElementById('createCompanyForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const submitBtn = e.target.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creando empresa...';
    
    // Usar FormData para el endpoint existente
    const formData = new FormData();
    const nombreEmpresa = document.getElementById('nombreEmpresa').value.trim();
    
    // Validar que el nombre no esté vacío
    if (!nombreEmpresa) {
        mostrarAlerta('El nombre de la empresa es obligatorio', 'danger');
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-check-circle"></i> Crear Empresa y Empezar';
        return;
    }

    const nif = document.getElementById('nif').value.trim();
    if (!nif) {
        mostrarAlerta('El NIF/CIF es obligatorio', 'danger');
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-check-circle"></i> Crear Empresa y Empezar';
        return;
    }

    if (!validarNifEspanol(nif)) {
        mostrarAlerta('El NIF/CIF introducido no es válido', 'danger');
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-check-circle"></i> Crear Empresa y Empezar';
        return;
    }
    
    formData.append('nombre', nombreEmpresa);
    formData.append('razon_social', nombreEmpresa);
    formData.append('cif', nif);
    formData.append('direccion', document.getElementById('direccion').value.trim());
    formData.append('codigo_postal', document.getElementById('codigoPostal').value.trim());
    formData.append('ciudad', document.getElementById('ciudad').value.trim());
    formData.append('provincia', document.getElementById('provincia').value.trim());
    formData.append('telefono', document.getElementById('telefono').value.trim());
    formData.append('email', document.getElementById('email').value.trim());
    formData.append('web', document.getElementById('web').value.trim());
    
    // Agregar logo si se seleccionó
    const logoInput = document.getElementById('logoInput');
    if (logoInput.files.length > 0) {
        formData.append('logo', logoInput.files[0]);
    }

    // Agregar certificado si se seleccionó
    const certInput = document.getElementById('certificadoFile');
    // Si hay archivo seleccionado, tiene prioridad
    if (certInput && certInput.files.length > 0) {
        const certPass = document.getElementById('certificadoPass').value;
        if (!certPass) {
             mostrarAlerta('Si sube un certificado, la contraseña es obligatoria', 'danger');
             submitBtn.disabled = false;
             submitBtn.innerHTML = '<i class="fas fa-check-circle"></i> Crear Empresa y Empezar';
             return;
        }
        formData.append('certificado', certInput.files[0]);
        formData.append('password_certificado', certPass);
    } else {
        // Si no hay archivo pero hay ruta validada
        const rutaCert = document.getElementById('rutaCertificadoHidden').value;
        if (rutaCert) {
            formData.append('ruta_certificado', rutaCert);
            // También enviamos la password si está rellenada, por si acaso el backend la necesita para algo más
            formData.append('password_certificado', document.getElementById('certificadoPass').value);
        }
    }
    
    // Debug: mostrar datos que se envían
    console.log('[CREAR EMPRESA] Datos a enviar:');
    for (let [key, value] of formData.entries()) {
        console.log(`  ${key}:`, value instanceof File ? `File(${value.name})` : value);
    }
    
    try {
        const response = await fetch('/api/empresas', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok && result.success) {
            // Mostrar mensaje de éxito
            document.getElementById('formContainer').style.display = 'none';
            const successDiv = document.getElementById('successMessage');
            successDiv.innerHTML = `
                <i class="fas fa-check-circle" style="font-size: 60px; color: var(--success-color, #28a745); margin-bottom: 20px;"></i>
                <h3>¡Empresa Creada Exitosamente!</h3>
                <p>${result.mensaje}</p>
                <div class="alert alert-success mt-3">
                    <strong><i class="fas fa-building"></i> Empresa:</strong> ${result.nombre}<br>
                    <strong><i class="fas fa-code"></i> Código:</strong> ${result.codigo}<br>
                    <strong><i class="fas fa-user"></i> Usuario:</strong> ${result.usuario}
                </div>
                <p class="mt-3">Redirigiendo al Panel de Control...</p>
                <div class="spinner-border text-primary mt-3" role="status">
                    <span class="sr-only">Cargando...</span>
                </div>
            `;
            successDiv.style.display = 'block';
            
            console.log('[CREAR EMPRESA] Redirigiendo en 1.5s...');
            
            // Recargar la aplicación después de 1.5 segundos para que vea su nueva empresa
            setTimeout(() => {
                console.log('[CREAR EMPRESA] Ejecutando redirección a /');
                // Forzar redirección al root evitando caché usando window.top (más seguro)
                window.top.location.href = '/?t=' + new Date().getTime();
            }, 1500);
        } else {
            mostrarAlerta(result.error || 'Error al crear la empresa', 'danger');
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-check-circle"></i> Crear Empresa y Empezar';
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarAlerta('Error al crear la empresa', 'danger');
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-check-circle"></i> Crear Empresa y Empezar';
    }
});

function mostrarAlerta(mensaje, tipo) {
    const mapaTipos = {
        'danger': 'error',
        'success': 'success',
        'warning': 'warning',
        'info': 'info'
    };
    const tipoNotificacion = mapaTipos[tipo] || 'info';
    
    if (window.mostrarNotificacion) {
        window.mostrarNotificacion(mensaje, tipoNotificacion);
    } else {
        console.warn('Sistema de notificaciones no disponible, usando alert');
        alert(mensaje);
    }
}

// Validar certificado
async function validarCertificado() {
    const fileInput = document.getElementById('certificadoFile');
    const passInput = document.getElementById('certificadoPass');
    
    if (!fileInput.files || !fileInput.files[0]) {
        mostrarAlerta('Seleccione un certificado primero', 'warning');
        return;
    }
    
    if (!passInput.value) {
        mostrarAlerta('Ingrese la contraseña del certificado', 'warning');
        return;
    }
    
    const btn = document.getElementById('btnValidarCert');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    
    const formData = new FormData();
    formData.append('certificado', fileInput.files[0]);
    formData.append('password', passInput.value);
    
    try {
        const response = await fetch('/api/empresas/procesar_certificado', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            mostrarAlerta('Certificado válido. Datos extraídos.', 'success');
            
            // Autocompletar campos
            if (data.razon_social) {
                const nombreInput = document.getElementById('nombreEmpresa');
                nombreInput.value = data.razon_social;
                // Disparar evento change si fuera necesario (aunque no hay listeners aquí)
            }
            if (data.nif) {
                document.getElementById('nif').value = data.nif;
            }
            if (data.ruta_certificado) {
                document.getElementById('rutaCertificadoHidden').value = data.ruta_certificado;
            }
            
            // Marcar visualmente
            passInput.style.borderColor = '#28a745';
            passInput.style.backgroundColor = '#e8f5e9';
        } else {
            mostrarAlerta(data.error || 'Error validando certificado', 'danger');
            passInput.style.borderColor = '#dc3545';
            passInput.style.backgroundColor = '#fff';
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarAlerta('Error de conexión al validar', 'danger');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}
window.validarCertificado = validarCertificado;

function validarNifEspanol(nif) {
    if (!nif) return false;
    nif = nif.toUpperCase().replace(/\s/g, '').replace(/-/g, '');
    
    // DNI/NIE
    if (/^[XYZ]?[0-9]{7,8}[A-Z]$/.test(nif)) {
        let nie = nif;
        if (nie.startsWith('X')) nie = nie.replace('X', '0');
        else if (nie.startsWith('Y')) nie = nie.replace('Y', '1');
        else if (nie.startsWith('Z')) nie = nie.replace('Z', '2');
        
        // Si tiene 7 dígitos + letra, añadir un 0 al principio (algunos casos antiguos)
        // Pero la expresión regular ya valida 7 u 8.
        
        const numero = nie.substr(0, nie.length - 1);
        const letra = nie.substr(nie.length - 1);
        const letras = "TRWAGMYFPDXBNJZSQVHLCKE";
        const letraCorrecta = letras.charAt(parseInt(numero) % 23);
        
        return letra === letraCorrecta;
    }
    
    // CIF
    if (/^[ABCDEFGHJKLMNPQRSUVW][0-9]{7}[0-9A-J]$/.test(nif)) {
        let sum = 0;
        for (let i = 0; i < 7; i++) {
            let n = parseInt(nif.charAt(i + 1));
            if (i % 2 === 0) { // Posiciones impares del número (índices 0, 2, 4...)
                n *= 2;
                if (n > 9) n = parseInt(n / 10) + (n % 10);
            }
            sum += n;
        }
        
        const controlDigit = (10 - (sum % 10)) % 10;
        const controlLetter = "JABCDEFGHI".charAt(controlDigit);
        
        const lastChar = nif.charAt(nif.length - 1);
        const isDigit = !isNaN(parseInt(lastChar));
        
        if (isDigit) {
            return parseInt(lastChar) === controlDigit;
        } else {
            return lastChar === controlLetter;
        }
    }
    
    return false;
}
window.validarNifEspanol = validarNifEspanol;

// Inicialización de event listeners para eliminar onclicks inline
document.addEventListener('DOMContentLoaded', () => {
    // Validar Certificado
    const btnValidar = document.getElementById('btnValidarCert');
    if (btnValidar) {
        btnValidar.addEventListener('click', validarCertificado);
    }
    
    // Select Logo
    const btnSelectLogo = document.getElementById('btnSelectLogo');
    if (btnSelectLogo) {
        btnSelectLogo.addEventListener('click', () => {
            const logoInput = document.getElementById('logoInput');
            if (logoInput) logoInput.click();
        });
    }
    
    // Remove Logo
    const btnRemoveLogo = document.getElementById('removeLogo');
    if (btnRemoveLogo) {
        btnRemoveLogo.addEventListener('click', () => {
             if (window.removeLogoPreview) window.removeLogoPreview();
        });
    }
});

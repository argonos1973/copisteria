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
    
    formData.append('nombre', nombreEmpresa);
    formData.append('razon_social', nombreEmpresa);
    formData.append('cif', document.getElementById('nif').value.trim());
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
            // Mostrar mensaje de éxito con información del usuario admin
            document.getElementById('formContainer').style.display = 'none';
            const successDiv = document.getElementById('successMessage');
            successDiv.innerHTML = `
                <i class="fas fa-check-circle" style="font-size: 60px; color: var(--success-color, #28a745); margin-bottom: 20px;"></i>
                <h3>¡Empresa Creada Exitosamente!</h3>
                <p>${result.mensaje}</p>
                <div class="alert alert-info mt-3">
                    <strong>Usuario Admin:</strong> ${result.usuario_admin}<br>
                    <strong>Contraseña:</strong> ${result.password_admin}<br>
                    <small>Guarda estos datos, los necesitarás para el primer acceso.</small>
                </div>
                <p>Redirigiendo al login...</p>
                <div class="spinner-border text-primary mt-3" role="status">
                    <span class="sr-only">Cargando...</span>
                </div>
            `;
            successDiv.style.display = 'block';
            
            // Cerrar sesión actual y redirigir al login después de 5 segundos
            setTimeout(async () => {
                // Cerrar sesión actual
                await fetch('/api/auth/logout', { method: 'POST' });
                // Redirigir al login
                window.parent.location.href = '/frontend/LOGIN.html';
            }, 5000);
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
    const container = document.getElementById('alertContainer');
    container.innerHTML = `
        <div class="alert alert-${tipo}">
            ${mensaje}
            <button type="button" class="close" onclick="this.parentElement.remove()">
                <span>&times;</span>
            </button>
        </div>
    `;
    
    setTimeout(() => {
        container.innerHTML = '';
    }, 5000);
}

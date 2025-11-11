// crear_empresa.js - Gestión de creación de empresa

// Enviar formulario
document.getElementById('createCompanyForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const submitBtn = e.target.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creando empresa...';
    
    // Usar FormData para el endpoint existente
    const formData = new FormData();
    formData.append('nombre', document.getElementById('nombreEmpresa').value.trim());
    formData.append('razon_social', document.getElementById('nombreEmpresa').value.trim());
    formData.append('cif', document.getElementById('nif').value.trim());
    formData.append('sector', document.getElementById('sector').value.trim());
    formData.append('direccion', document.getElementById('direccion').value.trim());
    formData.append('codigo_postal', document.getElementById('codigoPostal').value.trim());
    formData.append('ciudad', document.getElementById('ciudad').value.trim());
    formData.append('provincia', document.getElementById('provincia').value.trim());
    formData.append('telefono', document.getElementById('telefono').value.trim());
    formData.append('email', document.getElementById('email').value.trim());
    formData.append('web', document.getElementById('web').value.trim());
    
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

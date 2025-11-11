// cambiar_password.js - Gestión de cambio de contraseña

const form = document.getElementById('changePasswordForm');
const newPassword = document.getElementById('newPassword');
const confirmPassword = document.getElementById('confirmPassword');

// Validación en tiempo real
newPassword.addEventListener('input', validatePassword);
confirmPassword.addEventListener('input', validatePassword);

function validatePassword() {
    // Validar longitud
    const lengthReq = document.getElementById('req-length');
    if (newPassword.value.length >= 6) {
        lengthReq.classList.add('met');
        lengthReq.innerHTML = '<i class="fas fa-check-circle"></i> Mínimo 6 caracteres';
    } else {
        lengthReq.classList.remove('met');
        lengthReq.innerHTML = '<i class="fas fa-times-circle"></i> Mínimo 6 caracteres';
    }
    
    // Validar coincidencia
    const matchReq = document.getElementById('req-match');
    if (confirmPassword.value && newPassword.value === confirmPassword.value) {
        matchReq.classList.add('met');
        matchReq.innerHTML = '<i class="fas fa-check-circle"></i> Las contraseñas coinciden';
    } else {
        matchReq.classList.remove('met');
        matchReq.innerHTML = '<i class="fas fa-times-circle"></i> Las contraseñas coinciden';
    }
}

// Enviar formulario
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    if (newPassword.value !== confirmPassword.value) {
        mostrarAlerta('Las contraseñas no coinciden', 'danger');
        return;
    }
    
    if (newPassword.value.length < 6) {
        mostrarAlerta('La contraseña debe tener al menos 6 caracteres', 'danger');
        return;
    }
    
    try {
        const response = await fetch('/api/auth/change-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                current_password: document.getElementById('currentPassword').value,
                new_password: newPassword.value
            })
        });
        
        if (response.ok) {
            mostrarAlerta('Contraseña cambiada exitosamente', 'success');
            form.reset();
            validatePassword();
        } else {
            const error = await response.json();
            mostrarAlerta(error.error || 'Error al cambiar la contraseña', 'danger');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarAlerta('Error al cambiar la contraseña', 'danger');
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

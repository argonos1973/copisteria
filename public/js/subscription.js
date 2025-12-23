/**
 * Sistema de suscripciones Stripe para Aleph70
 */

let stripeConfig = null;
let stripe = null;

// Inicializar Stripe
async function initStripe() {
    try {
        const response = await fetch('/api/subscription/config');
        stripeConfig = await response.json();
        
        if (stripeConfig.publishableKey) {
            stripe = Stripe(stripeConfig.publishableKey);
            console.log('[Stripe] Inicializado correctamente');
        } else {
            console.warn('[Stripe] No hay clave pública configurada');
        }
    } catch (error) {
        console.error('[Stripe] Error inicializando:', error);
    }
}

// Iniciar proceso de suscripción
async function startSubscription(empresaId, email) {
    if (!stripe) {
        showNotification('Error: Sistema de pagos no disponible', 'error');
        return;
    }
    
    try {
        showLoadingButton(true);
        
        const response = await fetch('/api/subscription/create-checkout-session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                empresa_id: empresaId,
                email: email,
                success_url: window.location.origin + '/subscription/success',
                cancel_url: window.location.origin + '/subscription/cancel'
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            showNotification(data.error, 'error');
            showLoadingButton(false);
            return;
        }
        
        // Redirigir a Stripe Checkout
        if (data.url) {
            window.location.href = data.url;
        } else {
            const result = await stripe.redirectToCheckout({
                sessionId: data.sessionId
            });
            
            if (result.error) {
                showNotification(result.error.message, 'error');
            }
        }
        
    } catch (error) {
        console.error('[Stripe] Error:', error);
        showNotification('Error al procesar el pago', 'error');
        showLoadingButton(false);
    }
}

// Verificar estado de suscripción
async function checkSubscriptionStatus(empresaId) {
    try {
        const response = await fetch(`/api/subscription/status/${empresaId}`);
        return await response.json();
    } catch (error) {
        console.error('[Subscription] Error verificando estado:', error);
        return { active: false, status: 'error' };
    }
}

// Abrir portal de gestión de suscripción
async function openSubscriptionPortal(empresaId) {
    try {
        const response = await fetch('/api/subscription/portal', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                empresa_id: empresaId,
                return_url: window.location.href
            })
        });
        
        const data = await response.json();
        
        if (data.url) {
            window.location.href = data.url;
        } else if (data.error) {
            showNotification(data.error, 'error');
        }
        
    } catch (error) {
        console.error('[Subscription] Error abriendo portal:', error);
        showNotification('Error al abrir el portal de gestión', 'error');
    }
}

// Cancelar suscripción
async function cancelSubscription(empresaId) {
    if (!confirm('¿Estás seguro de que quieres cancelar tu suscripción?\n\nPodrás seguir usando el servicio hasta el final del período actual.')) {
        return;
    }
    
    try {
        const response = await fetch('/api/subscription/cancel', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ empresa_id: empresaId })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Suscripción cancelada. Podrás usar el servicio hasta el final del período.', 'success');
        } else {
            showNotification(data.error || 'Error al cancelar', 'error');
        }
        
    } catch (error) {
        console.error('[Subscription] Error cancelando:', error);
        showNotification('Error al cancelar la suscripción', 'error');
    }
}

// Reactivar suscripción
async function reactivateSubscription(empresaId) {
    try {
        const response = await fetch('/api/subscription/reactivate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ empresa_id: empresaId })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('¡Suscripción reactivada!', 'success');
            location.reload();
        } else {
            showNotification(data.error || 'Error al reactivar', 'error');
        }
        
    } catch (error) {
        console.error('[Subscription] Error reactivando:', error);
        showNotification('Error al reactivar la suscripción', 'error');
    }
}

// Obtener historial de pagos
async function getPaymentHistory(empresaId) {
    try {
        const response = await fetch(`/api/subscription/payment-history/${empresaId}`);
        return await response.json();
    } catch (error) {
        console.error('[Subscription] Error obteniendo historial:', error);
        return { payments: [] };
    }
}

// Mostrar estado de carga en botón
function showLoadingButton(loading) {
    const btn = document.querySelector('.btn-subscribe');
    if (btn) {
        if (loading) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';
        } else {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-credit-card"></i> Suscribirse - 20€/mes';
        }
    }
}

// Mostrar notificación
function showNotification(message, type = 'info') {
    // Crear elemento de notificación
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <span>${message}</span>
        <button onclick="this.parentElement.remove()">&times;</button>
    `;
    
    // Estilos inline para la notificación
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        background: ${type === 'error' ? '#ef4444' : type === 'success' ? '#22c55e' : '#3b82f6'};
        color: white;
        font-weight: 500;
        z-index: 10000;
        display: flex;
        align-items: center;
        gap: 1rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    // Auto-eliminar después de 5 segundos
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// Modal de suscripción
function openSubscribeModal() {
    // Verificar si ya existe el modal
    let modal = document.getElementById('subscribe-modal');
    if (!modal) {
        modal = createSubscribeModal();
        document.body.appendChild(modal);
    }
    modal.style.display = 'flex';
}

function closeSubscribeModal() {
    const modal = document.getElementById('subscribe-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function createSubscribeModal() {
    const modal = document.createElement('div');
    modal.id = 'subscribe-modal';
    modal.className = 'modal';
    modal.style.cssText = `
        display: none;
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.8);
        justify-content: center;
        align-items: center;
        z-index: 9999;
    `;
    
    modal.innerHTML = `
        <div class="modal-content" style="
            background: linear-gradient(135deg, #1a2332 0%, #0b1220 100%);
            border-radius: 20px;
            padding: 2.5rem;
            max-width: 450px;
            width: 90%;
            border: 1px solid rgba(255,255,255,0.1);
            position: relative;
        ">
            <button onclick="closeSubscribeModal()" style="
                position: absolute;
                top: 1rem;
                right: 1rem;
                background: none;
                border: none;
                color: #9ca3af;
                font-size: 1.5rem;
                cursor: pointer;
            ">&times;</button>
            
            <div style="text-align: center; margin-bottom: 2rem;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">🎁</div>
                <h2 style="color: #fff; margin: 0 0 0.5rem 0;">30 días GRATIS</h2>
                <p style="color: #2ecc71; font-weight: 600; margin: 0 0 0.5rem 0;">Prueba sin compromiso</p>
                <p style="color: #9ca3af; margin: 0;">Después 20€/mes + IVA • Cancela cuando quieras</p>
            </div>
            
            <form id="subscribe-form" onsubmit="handleSubscribeSubmit(event)">
                <div style="margin-bottom: 1.5rem;">
                    <label style="display: block; color: #9ca3af; margin-bottom: 0.5rem; font-size: 0.9rem;">
                        Nombre de empresa
                    </label>
                    <input type="text" id="sub-empresa" required style="
                        width: 100%;
                        padding: 0.8rem 1rem;
                        border-radius: 10px;
                        border: 1px solid rgba(255,255,255,0.1);
                        background: rgba(255,255,255,0.05);
                        color: #fff;
                        font-size: 1rem;
                        box-sizing: border-box;
                    " placeholder="Mi Empresa S.L.">
                </div>
                
                <div style="margin-bottom: 1.5rem;">
                    <label style="display: block; color: #9ca3af; margin-bottom: 0.5rem; font-size: 0.9rem;">
                        Email de facturación
                    </label>
                    <input type="email" id="sub-email" required style="
                        width: 100%;
                        padding: 0.8rem 1rem;
                        border-radius: 10px;
                        border: 1px solid rgba(255,255,255,0.1);
                        background: rgba(255,255,255,0.05);
                        color: #fff;
                        font-size: 1rem;
                        box-sizing: border-box;
                    " placeholder="facturacion@empresa.com">
                </div>
                
                <div style="
                    background: rgba(46, 204, 113, 0.1);
                    border: 1px solid rgba(46, 204, 113, 0.3);
                    border-radius: 10px;
                    padding: 1rem;
                    margin-bottom: 1.5rem;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: #2ecc71; font-weight: 600;">🎁 Primeros 30 días</span>
                        <span style="color: #2ecc71; font-weight: 700;">GRATIS</span>
                    </div>
                    <hr style="border: none; border-top: 1px solid rgba(255,255,255,0.1); margin: 0.8rem 0;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: #9ca3af;">Después: Plan Premium</span>
                        <span style="color: #fff;">20,00 €/mes</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.3rem;">
                        <span style="color: #9ca3af;">+ IVA (21%)</span>
                        <span style="color: #9ca3af;">4,20 €</span>
                    </div>
                    <div style="text-align: center; margin-top: 0.8rem; padding-top: 0.8rem; border-top: 1px solid rgba(255,255,255,0.1);">
                        <span style="color: #6b7280; font-size: 0.85rem;">Hoy pagas: <strong style="color: #2ecc71;">0,00 €</strong></span>
                    </div>
                </div>
                
                <button type="submit" class="btn-subscribe" style="
                    width: 100%;
                    padding: 1rem;
                    background: linear-gradient(135deg, #2ecc71, #27ae60);
                    color: #fff;
                    border: none;
                    border-radius: 10px;
                    font-size: 1rem;
                    font-weight: 600;
                    cursor: pointer;
                    transition: transform 0.2s, box-shadow 0.2s;
                ">
                    <i class="fas fa-rocket"></i> Empezar 30 días gratis
                </button>
                
                <p style="text-align: center; color: #6b7280; font-size: 0.8rem; margin-top: 1rem;">
                    <i class="fas fa-shield-alt"></i> Sin cargos durante el periodo de prueba • Cancela cuando quieras
                </p>
            </form>
        </div>
    `;
    
    // Cerrar al hacer clic fuera
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeSubscribeModal();
        }
    });
    
    return modal;
}

// Manejar envío del formulario de suscripción
async function handleSubscribeSubmit(event) {
    event.preventDefault();
    
    const empresa = document.getElementById('sub-empresa').value.trim();
    const email = document.getElementById('sub-email').value.trim();
    
    if (!empresa || !email) {
        showNotification('Por favor completa todos los campos', 'error');
        return;
    }
    
    // Crear ID de empresa a partir del nombre (slug)
    const empresaId = empresa.toLowerCase()
        .replace(/[áàäâ]/g, 'a')
        .replace(/[éèëê]/g, 'e')
        .replace(/[íìïî]/g, 'i')
        .replace(/[óòöô]/g, 'o')
        .replace(/[úùüû]/g, 'u')
        .replace(/[ñ]/g, 'n')
        .replace(/[^a-z0-9]/g, '_')
        .replace(/_+/g, '_')
        .replace(/^_|_$/g, '');
    
    await startSubscription(empresaId, email);
}

// Añadir estilos de animación
const styleSheet = document.createElement('style');
styleSheet.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(styleSheet);

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', initStripe);

document.addEventListener('DOMContentLoaded', () => {
    const toggleBtn = document.getElementById('sidebar-toggle');
    const mobileToggleBtn = document.getElementById('mobile-toggle');
    const layout = document.querySelector('.layout-container');
    const menu = document.querySelector('.menu');

    // Función para detectar móvil
    const isMobile = () => window.innerWidth <= 768;

    // Restaurar estado en escritorio
    if (!isMobile()) {
        const isHidden = localStorage.getItem('sidebarHidden') === 'true';
        if (isHidden) {
            layout.classList.add('sidebar-hidden');
        }
    }

    if (toggleBtn) {
        toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            
            if (isMobile()) {
                // Móvil: Cerrar menú (el botón interno actúa como cierre)
                menu.classList.remove('mobile-active');
            } else {
                // Escritorio: toggle clase para colapsar
                layout.classList.toggle('sidebar-hidden');
                localStorage.setItem('sidebarHidden', layout.classList.contains('sidebar-hidden'));
            }
        });
    }
    
    if (mobileToggleBtn) {
        mobileToggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            // Móvil: Abrir menú
            menu.classList.add('mobile-active');
        });
    }

    // Cerrar menú móvil al hacer click fuera
    document.addEventListener('click', (e) => {
        if (isMobile() && menu && menu.classList.contains('mobile-active')) {
            // Si click fuera del menú y no en los botones
            if (!menu.contains(e.target) && 
                e.target !== toggleBtn && !toggleBtn?.contains(e.target) &&
                e.target !== mobileToggleBtn && !mobileToggleBtn?.contains(e.target)) {
                menu.classList.remove('mobile-active');
            }
        }
    });
    
    // Ajustar al redimensionar ventana
    window.addEventListener('resize', () => {
        if (!isMobile() && menu.classList.contains('mobile-active')) {
            menu.classList.remove('mobile-active');
        }
    });
});

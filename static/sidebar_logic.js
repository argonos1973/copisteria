document.addEventListener('DOMContentLoaded', () => {
    const toggleBtn = document.getElementById('sidebar-toggle');
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

    // Cerrar menú móvil al hacer click fuera
    document.addEventListener('click', (e) => {
        if (isMobile() && menu && menu.classList.contains('mobile-active')) {
            // Si click fuera del menú y no en el botón toggle
            if (!menu.contains(e.target) && 
                e.target !== toggleBtn && !toggleBtn?.contains(e.target)) {
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

    // === MODAL Z-INDEX FIX ===
    // Observar cambios en el DOM para detectar modales abiertos
    const ajustarZIndexMenu = () => {
        const modalesVisibles = document.querySelectorAll('.modal.show, .modal.active, .modal[style*="display: block"], .modal[style*="display:block"], .modal-perfil[style*="display: block"]');
        if (modalesVisibles.length > 0) {
            menu.style.zIndex = '1';
        } else {
            menu.style.zIndex = '';
        }
    };

    // MutationObserver para detectar cambios en modales
    const observer = new MutationObserver((mutations) => {
        ajustarZIndexMenu();
    });

    // Observar todo el body para cambios en atributos style y class
    observer.observe(document.body, {
        attributes: true,
        attributeFilter: ['style', 'class'],
        subtree: true,
        childList: true
    });

    // También verificar periódicamente (backup)
    setInterval(ajustarZIndexMenu, 500);
});

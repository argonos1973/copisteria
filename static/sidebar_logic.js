document.addEventListener('DOMContentLoaded', () => {
    const toggleBtn = document.getElementById('sidebar-toggle');
    const layout = document.querySelector('.layout-container');
    const menu = document.querySelector('.menu');
    
    // Elementos móviles
    const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
    const mobileOverlay = document.getElementById('mobile-overlay');
    const mobileNotifBtn = document.getElementById('mobile-notif-btn');
    const mobileLogo = document.getElementById('mobile-logo');

    // Función para detectar móvil
    const isMobile = () => window.innerWidth <= 768;
    
    // ============================================================================
    // MENÚ MÓVIL
    // ============================================================================
    
    // Función para abrir menú móvil
    const openMobileMenu = () => {
        menu.classList.add('mobile-open');
        mobileOverlay?.classList.add('active');
        document.body.style.overflow = 'hidden';
    };
    
    // Función para cerrar menú móvil
    const closeMobileMenu = () => {
        menu.classList.remove('mobile-open');
        mobileOverlay?.classList.remove('active');
        document.body.style.overflow = '';
    };
    
    // Toggle menú móvil con hamburger
    if (mobileMenuToggle) {
        mobileMenuToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            if (menu.classList.contains('mobile-open')) {
                closeMobileMenu();
            } else {
                openMobileMenu();
            }
        });
    }
    
    // Cerrar menú al click en overlay
    if (mobileOverlay) {
        mobileOverlay.addEventListener('click', closeMobileMenu);
    }
    
    // Cerrar menú al seleccionar opción del menú
    menu?.querySelectorAll('.menu-link, .submenu-item').forEach(link => {
        link.addEventListener('click', () => {
            if (isMobile()) {
                closeMobileMenu();
            }
        });
    });
    
    // Sincronizar logo móvil con logo del menú
    const syncMobileLogo = () => {
        const logoEmpresa = document.getElementById('logo-empresa');
        if (logoEmpresa && mobileLogo && logoEmpresa.src) {
            mobileLogo.src = logoEmpresa.src;
            mobileLogo.style.display = logoEmpresa.style.display;
        }
    };
    
    // Observar cambios en el logo
    const logoEmpresa = document.getElementById('logo-empresa');
    if (logoEmpresa) {
        const logoObserver = new MutationObserver(syncMobileLogo);
        logoObserver.observe(logoEmpresa, { attributes: true, attributeFilter: ['src', 'style'] });
    }
    syncMobileLogo();
    
    // Sincronizar badge de notificaciones móvil
    const syncMobileNotifBadge = () => {
        const desktopBadge = document.getElementById('notificaciones-badge');
        const mobileBadge = document.getElementById('mobile-notif-badge');
        if (desktopBadge && mobileBadge) {
            mobileBadge.textContent = desktopBadge.textContent;
            mobileBadge.style.display = desktopBadge.style.display;
        }
    };
    
    // Notificaciones móvil
    if (mobileNotifBtn) {
        mobileNotifBtn.addEventListener('click', () => {
            const notifIcon = document.getElementById('notificaciones-icon');
            notifIcon?.click();
        });
    }
    
    // Observar badge de notificaciones
    const desktopBadge = document.getElementById('notificaciones-badge');
    if (desktopBadge) {
        const badgeObserver = new MutationObserver(syncMobileNotifBadge);
        badgeObserver.observe(desktopBadge, { attributes: true, childList: true, characterData: true });
    }
    syncMobileNotifBadge();

    // ============================================================================
    // SIDEBAR DESKTOP
    // ============================================================================

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
                closeMobileMenu();
            } else {
                // Escritorio: toggle clase para colapsar
                layout.classList.toggle('sidebar-hidden');
                localStorage.setItem('sidebarHidden', layout.classList.contains('sidebar-hidden'));
            }
        });
    }

    // Cerrar menú móvil al hacer click fuera
    document.addEventListener('click', (e) => {
        if (isMobile() && menu && menu.classList.contains('mobile-open')) {
            if (!menu.contains(e.target) && 
                e.target !== mobileMenuToggle && !mobileMenuToggle?.contains(e.target)) {
                closeMobileMenu();
            }
        }
    });
    
    // Ajustar al redimensionar ventana
    window.addEventListener('resize', () => {
        if (!isMobile()) {
            closeMobileMenu();
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

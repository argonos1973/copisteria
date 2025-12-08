document.addEventListener('DOMContentLoaded', () => {
    console.log('Mobile App Loaded');

    // Gestión básica de navegación activa
    const navItems = document.querySelectorAll('.bottom-nav .nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            // Aquí iría la lógica de navegación (o dejar que sea enlace normal)
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');
        });
    });
});

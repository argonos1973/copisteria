// Pre-configuración de branding para crear empresa
(function() {
    // Si no hay tema seleccionado, usar 'minimal' por defecto para esta página
    if (!localStorage.getItem('plantillaSeleccionada')) {
        localStorage.setItem('plantillaSeleccionada', 'minimal');
    }
})();

// Navegación del editor de colores
document.addEventListener('DOMContentLoaded', function() {
    const btnEmpresas = document.querySelector('.btn-back[data-target="empresas"]');
    const btnInicio = document.querySelector('.btn-back[data-target="inicio"]');
    
    if (btnEmpresas) {
        btnEmpresas.addEventListener('click', function() {
            window.location.href = 'ADMIN_EMPRESAS.html';
        });
    }
    
    if (btnInicio) {
        btnInicio.addEventListener('click', function() {
            window.location.href = 'inicio.html';
        });
    }
});

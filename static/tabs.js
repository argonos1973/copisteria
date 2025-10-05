// Sistema de pestañas
export function inicializarPestanas() {
  const tabButtons = document.querySelectorAll('.tab-button');
  const tabContents = document.querySelectorAll('.tab-content');

  tabButtons.forEach((button, index) => {
    button.addEventListener('click', () => {
      // Remover active de todos los botones y contenidos
      tabButtons.forEach(btn => btn.classList.remove('active'));
      tabContents.forEach(content => content.classList.remove('active'));

      // Añadir active al botón y contenido clickeado
      button.classList.add('active');
      tabContents[index].classList.add('active');
    });
  });

  // Activar la primera pestaña por defecto
  if (tabButtons.length > 0) {
    tabButtons[0].classList.add('active');
    tabContents[0].classList.add('active');
  }
}

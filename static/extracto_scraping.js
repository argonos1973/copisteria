/**
 * Script para manejar la actualización del extracto bancario mediante scraping
 */

import { mostrarNotificacion } from './notificaciones.js';

// Variables globales
let iconoActualizar;

document.addEventListener('DOMContentLoaded', function() {
    // Obtener referencia al icono
    iconoActualizar = document.getElementById('btn-actualizar-extracto');
    
    if (!iconoActualizar) {
        console.error("No se encontró el botón de actualización del extracto");
        return;
    }
    
    console.log("Inicializando módulo de extracto bancario");
    
    // Verificar si hay un proceso en ejecución al cargar la página
    verificarEstadoScrapingInicial();
    
    // Añadir el evento de click al icono
    iconoActualizar.addEventListener('click', function() {
        console.log("Click en botón actualizar extracto");
        if(!iconoActualizar.classList.contains('disabled')) {
            iniciarActualizacion();
        }
    });
    
    /**
     * Verifica el estado inicial del scraping al cargar la página
     */
    function verificarEstadoScrapingInicial() {
        fetch('/api/scraping/estado_scraping', { credentials: 'include' })
            .then(response => response.json())
            .then(data => {
                if (data.exito && data.en_ejecucion) {
                    deshabilitarBoton("Actualizando...");
                    iniciarVerificacionPeriodica();
                }
            })
            .catch(error => {
                console.error('Error al verificar el estado inicial del scraping:', error);
            });
    }
    
    /**
     * Inicia el proceso de actualización del extracto bancario
     */
    function iniciarActualizacion() {
        // Deshabilitar el botón
        deshabilitarBoton();
        
        console.log("Iniciando actualización del extracto bancario...");
        
        // Mostrar notificación
        mostrarNotificacion("Iniciando actualización de datos bancarios...", "info");
        
        // Verificar si hay un proceso en ejecución antes de iniciar
        fetch('/api/scraping/estado_scraping', { credentials: 'include' })
            .then(response => response.json())
            .then(estadoData => {
                if (estadoData.exito && estadoData.en_ejecucion) {
                    // Ya hay un proceso en ejecución
                    mostrarNotificacion("Ya hay un proceso de actualización en curso. Espere a que termine.", "warning");
                    iniciarVerificacionPeriodica(); // Monitorear el proceso existente
                    return;
                }
                
                // No hay proceso en ejecución, iniciar uno nuevo
                fetch('/api/scraping/ejecutar_scrapeo', { credentials: 'include' }, {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.exito) {
                        console.log("Actualización iniciada correctamente");
                        mostrarNotificacion("Actualización iniciada correctamente. Este proceso puede tardar unos minutos...", "success");
                        // Iniciar verificación periódica del estado
                        iniciarVerificacionPeriodica();
                    } else {
                        console.error("Error al iniciar actualización:", data.error);
                        habilitarBoton();
                        mostrarNotificacion(`Error al iniciar la actualización: ${data.error}`, "error");
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    habilitarBoton();
                    mostrarNotificacion("Error de conexión al iniciar la actualización", "error");
                });
            })
            .catch(error => {
                console.error('Error al verificar estado:', error);
                // Intentar iniciar de todos modos
                fetch('/api/scraping/ejecutar_scrapeo', { credentials: 'include' }, { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        if (data.exito) {
                            iniciarVerificacionPeriodica();
                        } else {
                            habilitarBoton();
                            mostrarNotificacion("Error al iniciar la actualización", "error");
                        }
                    })
                    .catch(() => {
                        habilitarBoton();
                        mostrarNotificacion("Error de conexión", "error");
                    });
            });
    }
    
    /**
     * Inicia verificación periódica del estado del scraping
     */
    function iniciarVerificacionPeriodica() {
        let intentos = 0;
        const maxIntentos = 60; // 5 minutos máximo (5 segundos * 60)
        
        console.log("Iniciando monitoreo del proceso de scraping...");
        iconoActualizar.setAttribute('title', 'Actualizando extracto bancario...');
        
        const interval = setInterval(function() {
            console.log(`Verificando estado del proceso (intento ${intentos + 1})...`);
            
            fetch('/api/scraping/estado_scraping', { credentials: 'include' })
                .then(response => response.json())
                .then(data => {
                    console.log('Estado del scraping:', data);
                    
                    if (data.exito) {
                        // Actualizar el título del botón con información del estado
                        if (data.en_ejecucion) {
                            iconoActualizar.setAttribute('title', `Actualizando: ${data.mensaje || 'En proceso...'}`);
                        }
                        
                        if (!data.en_ejecucion || data.estado === "completado" || data.estado === "completado_recientemente") {
                            // El proceso terminó
                            clearInterval(interval);
                            habilitarBoton();
                            mostrarNotificacion("Actualización completada. Recargando página para mostrar datos actualizados...", "success");
                            
                            // Forzar recarga completa de la página para actualizar todos los datos
                            console.log("Forzando recarga de la página para mostrar datos actualizados...");
                            setTimeout(() => {
                                // Usamos recarga completa de la página para garantizar que se muestren los datos actualizados
                                window.location.reload(true); // true para forzar recarga desde el servidor y no desde caché
                            }, 2000); // Esperamos 2 segundos para que el usuario vea la notificación
                        } else if (intentos >= maxIntentos) {
                            // Demasiados intentos, asumimos que algo falló
                            clearInterval(interval);
                            habilitarBoton();
                            mostrarNotificacion("El proceso está tardando demasiado tiempo. Por favor, inténtelo de nuevo más tarde.", "warning");
                        }
                    } else {
                        // Error en la respuesta
                        clearInterval(interval);
                        habilitarBoton();
                        mostrarNotificacion(`Error al verificar el estado: ${data.error || 'Error desconocido'}`, "error");
                    }
                    
                    intentos++;
                })
                .catch(error => {
                    console.error('Error al verificar estado del scraping:', error);
                    intentos++;
                    
                    if (intentos >= maxIntentos) {
                        clearInterval(interval);
                        habilitarBoton();
                        mostrarNotificacion("Error al verificar el estado del proceso. Por favor, inténtelo de nuevo.", "error");
                    }
                });
        }, 5000); // Verificar cada 5 segundos
    }
    
    /**
     * Deshabilita el icono y muestra la animación de carga
     */
    function deshabilitarBoton() {
        iconoActualizar.classList.add('disabled');
        iconoActualizar.classList.add('icono-actualizar-girar');
        iconoActualizar.dataset.originalTitle = iconoActualizar.getAttribute('title');
        iconoActualizar.setAttribute('title', 'Actualizando...');
    }
    
    /**
     * Habilita el icono y detiene la animación de carga
     */
    function habilitarBoton() {
        iconoActualizar.classList.remove('disabled');
        iconoActualizar.classList.remove('icono-actualizar-girar');
        if (iconoActualizar.dataset.originalTitle) {
            iconoActualizar.setAttribute('title', iconoActualizar.dataset.originalTitle);
            delete iconoActualizar.dataset.originalTitle;
        }
    }
    
    // Usamos la función mostrarNotificacion importada de utils.js
});

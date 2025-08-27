// Crear la aplicación de Vue
const { createApp } = Vue;

createApp({
    data() {
        return {
            windows: [],
            activeWindow: null,
            isStartMenuOpen: false,
            menuOptions: [
                { id: 1, title: 'Contactos', icon: 'person', url: '/frontend/CONSULTA_CONTACTOS.html' },
                { id: 2, title: 'Facturas', icon: 'receipt', url: '/frontend/CONSULTA_FACTURAS.html' },
                { id: 3, title: 'Proformas', icon: 'description', url: '/frontend/CONSULTA_PROFORMAS.html' },
                { id: 4, title: 'Tickets', icon: 'local_activity', url: '/frontend/CONSULTA_TICKETS.html' },
                { id: 5, title: 'Gastos', icon: 'payments', url: '/frontend/CONSULTA_GASTOS.html' },
                { id: 6, title: 'Productos', icon: 'inventory_2', url: '/frontend/CONSULTA_PRODUCTOS.html' },
                { id: 7, title: 'Exportar', icon: 'file_download', url: '/frontend/EXPORTAR.html' },
                { id: 8, title: 'Estadísticas', icon: 'analytics', url: '/frontend/estadisticas.html' },
                { id: 9, title: 'Franjas Descuento', icon: 'percent', url: '/frontend/FRANJAS_DESCUENTO.html' }
            ],
            nextId: 1,
            nextZIndex: 1,
            dragInfo: {
                isDragging: false,
                window: null,
                offsetX: 0,
                offsetY: 0
            }
        };
    },
    computed: {
        taskbarItems() {
            return this.windows.map(window => ({
                id: window.id,
                title: window.title,
                icon: window.icon
            }));
        }
    },
    methods: {
        toggleStartMenu() {
            this.isStartMenuOpen = !this.isStartMenuOpen;
        },
        
        openWindow(option) {
            // Cerrar el menú de inicio
            this.isStartMenuOpen = false;
            
            // Verificar si la ventana ya está abierta
            const existingWindow = this.windows.find(w => w.url === option.url);
            
            if (existingWindow) {
                // Si está minimizada, restaurarla
                if (existingWindow.isMinimized) {
                    existingWindow.isMinimized = false;
                }
                this.bringToFront(existingWindow);
                return;
            }
            
            // Crear nueva ventana
            const window = {
                id: this.nextId++,
                title: option.title,
                icon: option.icon,
                url: option.url,
                x: 50 + (this.windows.length * 20),
                y: 50 + (this.windows.length * 20),
                width: 800,
                height: 600,
                content: `<iframe src="${option.url}" style="width: 100%; height: 100%; border: none;"></iframe>`,
                isMaximized: false,
                isMinimized: false,
                zIndex: this.nextZIndex++
            };
            
            this.windows.push(window);
            this.activeWindow = window.id;
        },
        
        minimizeWindow(id) {
            const window = this.windows.find(w => w.id === id);
            if (window) {
                window.isMinimized = !window.isMinimized;
                if (!window.isMinimized) {
                    this.bringToFront(window);
                }
            }
        },
        
        maximizeWindow(id) {
            const window = this.windows.find(w => w.id === id);
            if (window) {
                window.isMaximized = !window.isMaximized;
                this.bringToFront(window);
            }
        },
        
        closeWindow(id) {
            this.windows = this.windows.filter(w => w.id !== id);
        },
        
        startDrag(event, window) {
            // Solo iniciar arrastre si no está maximizada
            if (window.isMaximized) return;
            
            this.dragInfo = {
                isDragging: true,
                window: window,
                offsetX: event.clientX - window.x,
                offsetY: event.clientY - window.y
            };
            
            // Traer ventana al frente
            this.bringToFront(window);
            
            // Agregar event listeners para el arrastre
            document.addEventListener('mousemove', this.onDrag);
            document.addEventListener('mouseup', this.stopDrag);
        },
        
        onDrag(event) {
            if (this.dragInfo.isDragging) {
                const window = this.dragInfo.window;
                
                // Calcular nueva posición
                window.x = event.clientX - this.dragInfo.offsetX;
                window.y = event.clientY - this.dragInfo.offsetY;
                
                // Asegurar que la ventana no se salga del área visible
                window.x = Math.max(0, window.x);
                window.y = Math.max(0, window.y);
                window.x = Math.min(window.x, document.body.clientWidth - 100);
                window.y = Math.min(window.y, document.body.clientHeight - 100);
            }
        },
        
        stopDrag() {
            this.dragInfo.isDragging = false;
            document.removeEventListener('mousemove', this.onDrag);
            document.removeEventListener('mouseup', this.stopDrag);
        },
        
        bringToFront(window) {
            this.activeWindow = window.id;
            window.zIndex = this.nextZIndex++;
        }
    },
    
    mounted() {
        // Inicializar el escritorio
        document.addEventListener('click', (event) => {
            // Cerrar el menú de inicio si se hace clic fuera de él
            if (this.isStartMenuOpen && !event.target.closest('.start-menu') && !event.target.closest('.start-button')) {
                this.isStartMenuOpen = false;
            }
        });
    }
}).mount('#desktop');

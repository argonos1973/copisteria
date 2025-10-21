# 🏢 Sistema Multiempresa Aleph70

## 📋 Estado Actual

**Rama:** `multiempresa`  
**Fecha Inicio:** 21 octubre 2025  
**Estado:** 🚧 En desarrollo - Base implementada

---

## ✅ Implementado

### 1. Base de Datos Central (`db/init_multiempresa.sql`)

- ✅ Tabla `empresas` - Gestión de múltiples empresas
- ✅ Tabla `usuarios` - Usuarios del sistema
- ✅ Tabla `usuario_empresa` - Relación usuarios-empresas
- ✅ Tabla `modulos` - Módulos del sistema
- ✅ Tabla `permisos_usuario_modulo` - Permisos granulares
- ✅ Tabla `configuracion_empresa` - Configuración flexible por empresa
- ✅ Tabla `auditoria` - Log de acciones
- ✅ Datos iniciales (empresa copistería + admin)
- ✅ Índices optimizados

### 2. Sistema de Configuración (`multiempresa_config.py`)

- ✅ Rutas de BD centralizadas
- ✅ Configuración de sesiones
- ✅ Políticas de seguridad
- ✅ Rutas públicas/admin
- ✅ Branding por defecto
- ✅ Definición de módulos
- ✅ Plantillas de permisos
- ✅ Función `obtener_db_empresa()`
- ✅ Auto-inicialización de BD

### 3. Middleware de Autenticación (`auth_middleware.py`)

- ✅ Hash de contraseñas (SHA256)
- ✅ Decorador `@login_required`
- ✅ Decorador `@require_admin`
- ✅ Decorador `@require_permission(modulo, accion)`
- ✅ Función `autenticar_usuario()`
- ✅ Control de intentos fallidos
- ✅ Bloqueo por seguridad
- ✅ Registro de auditoría
- ✅ Gestión de sesiones

### 4. Rutas de Autenticación (`auth_routes.py`)

- ✅ `POST /api/auth/login` - Login con empresa
- ✅ `POST /api/auth/logout` - Cerrar sesión
- ✅ `GET /api/auth/empresas/<username>` - Obtener empresas del usuario
- ✅ `GET /api/auth/session` - Información de sesión actual
- ✅ `GET /api/auth/menu` - Menú según permisos
- ✅ `GET /api/auth/branding` - Branding de empresa activa
- ✅ `POST /api/auth/cambiar-password` - Cambiar contraseña

### 5. Interfaz de Login (`frontend/LOGIN.html`)

- ✅ Diseño moderno y responsive
- ✅ Paso 1: Credenciales
- ✅ Paso 2: Selector de empresa (si tiene varias)
- ✅ Auto-login si solo tiene 1 empresa
- ✅ Manejo de errores
- ✅ Loading states
- ✅ Validación de campos

---

## 🔧 Credenciales Por Defecto

**Usuario:** `admin`  
**Contraseña:** `admin123` ⚠️ **CAMBIAR EN PRODUCCIÓN**  
**Empresa:** `copisteria`

---

## 📊 Estructura de Archivos

```
/var/www/html/
├── db/
│   ├── init_multiempresa.sql       ← Script de creación BD
│   └── usuarios_sistema.db         ← BD central (se crea auto)
├── multiempresa_config.py          ← Configuración general
├── auth_middleware.py              ← Middleware de autenticación
├── auth_routes.py                  ← Endpoints de auth
└── frontend/
    └── LOGIN.html                  ← Pantalla de login
```

---

## 🚀 Próximos Pasos

### Fase 2: Integración con Aplicación Existente
- [ ] Integrar `auth_routes.py` en `app.py`
- [ ] Modificar todas las conexiones BD para usar `get_empresa_db()`
- [ ] Añadir middleware de autenticación a todas las rutas
- [ ] Actualizar menú lateral para usar `/api/auth/menu`
- [ ] Aplicar branding dinámico en todas las páginas

### Fase 3: Administración
- [ ] Pantalla `ADMIN_PERMISOS.html`
- [ ] Gestión de usuarios (crear/editar/desactivar)
- [ ] Gestión de empresas
- [ ] Matriz de permisos editable
- [ ] Gestión de módulos
- [ ] Plantillas de permisos rápidas

### Fase 4: Configuración por Empresa
- [ ] Pantalla `ADMIN_CONFIG_EMPRESA.html`
- [ ] Configuración de tarjetas estadísticas
- [ ] Orden de tarjetas drag & drop
- [ ] Widgets personalizados
- [ ] Preview en vivo
- [ ] API de configuración

### Fase 5: Branding
- [ ] Upload de logos
- [ ] Selector de colores
- [ ] Aplicación automática de branding
- [ ] PDFs con logo de empresa
- [ ] CSS dinámico según colores

### Fase 6: Testing y Optimización
- [ ] Tests de autenticación
- [ ] Tests de permisos
- [ ] Tests de configuración
- [ ] Optimización de consultas
- [ ] Documentación completa

---

## 🔐 Seguridad Implementada

- ✅ Contraseñas hasheadas (SHA256)
- ✅ Control de intentos fallidos (5 max)
- ✅ Bloqueo automático tras intentos
- ✅ Sesiones seguras (HttpOnly, SameSite)
- ✅ Timeout de sesión (8 horas)
- ✅ Log de auditoría completo
- ✅ Verificación de permisos por módulo/acción
- ✅ Rutas públicas/privadas separadas

---

## 📈 Estadísticas del Sistema

- **Tablas creadas:** 7
- **Índices optimizados:** 8
- **Módulos definidos:** 9
- **Permisos granulares:** 6 tipos
- **Plantillas permisos:** 4
- **Archivos Python:** 3
- **Endpoints API:** 7
- **Líneas de código:** ~1,200

---

## 🎯 Compatibilidad

El sistema está diseñado para ser **100% compatible** con el código existente:

- Función `get_empresa_db()` retorna BD según sesión
- Decoradores aplicables a rutas existentes
- Sin cambios en lógica de negocio
- Migración gradual posible

---

## 📝 Notas de Desarrollo

### Inicialización Automática
La BD central se crea automáticamente al importar `multiempresa_config.py` si no existe.

### Logging
Todos los módulos usan `logger_config.py` para logging consistente.

### Sesiones Flask
Usar configuración de `SESSION_CONFIG` en `app.py`.

### Rutas Protegidas
Aplicar decoradores a rutas:
```python
@app.route('/api/facturas')
@login_required
@require_permission('facturas', 'ver')
def obtener_facturas():
    # ...
```

---

## 🔄 Comandos Útiles

### Crear BD desde cero
```bash
cd /var/www/html
rm db/usuarios_sistema.db
python3 -c "import multiempresa_config"
```

### Verificar BD
```bash
sqlite3 db/usuarios_sistema.db ".tables"
sqlite3 db/usuarios_sistema.db "SELECT * FROM usuarios"
```

### Test de login
```bash
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123","empresa":"copisteria"}'
```

---

## 🎨 Siguiente Sesión de Trabajo

1. Integrar auth_routes en app.py
2. Modificar conexiones BD existentes
3. Añadir middleware a rutas principales
4. Crear directorio /static/logos/
5. Probar login completo

---

**Última actualización:** 21 octubre 2025  
**Autor:** Cascade AI + Sami  
**Versión:** 0.1.0 (Base)

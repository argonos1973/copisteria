# 🧪 Guía Completa de Pruebas - Sistema Multiempresa

## 📋 Resumen Rápido

**URL:** http://localhost:5001/  
**Usuario:** `admin`  
**Password:** `admin123`  
**Empresa:** `Copistería Aleph70` (automático)

---

## 🎯 Qué Verás en Cada Pantalla

### 1️⃣ Pantalla de Login

**URL:** `http://localhost:5001/` o `http://localhost:5001/LOGIN.html`

**Apariencia:**
```
┌─────────────────────────────────────────┐
│                                         │
│          🔐 Aleph70                     │
│       Sistema Multiempresa              │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ Usuario                         │   │
│  │ [                              ]│   │
│  │                                 │   │
│  │ Contraseña                      │   │
│  │ [                              ]│   │
│  │                                 │   │
│  │     [ Siguiente → ]             │   │
│  └─────────────────────────────────┘   │
│                                         │
│     v1.0.0 - Sistema Multiempresa       │
│          © 2025 Aleph70                 │
└─────────────────────────────────────────┘
```

**Características:**
- Fondo con gradiente morado (#667eea a #764ba2)
- Tarjeta blanca centrada
- Campos con borde que cambia al hacer focus
- Botón con efecto hover

**Acciones:**
1. Introduce `admin` en Usuario
2. Introduce `admin123` en Contraseña
3. Clic en "Siguiente →"
4. → Redirige a DASHBOARD.html

---

### 2️⃣ Dashboard Principal

**URL:** `http://localhost:5001/DASHBOARD.html` (requiere login)

**Apariencia:**
```
┌─────────────────────────────────────────────────────────────┐
│ [Logo] Copistería Aleph70          Administrador Sistema  │
│        copisteria                   admin       [🚪 Salir] │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 👋 Bienvenido al Sistema                                    │
│ Hola Administrador Sistema, bienvenido a Copistería...     │
└─────────────────────────────────────────────────────────────┘

┌──────────────┬──────────────┬──────────────────────────────┐
│   Módulos    │   Permisos   │      Rol del usuario        │
│   disponibles│   activos    │                             │
│       9      │      54      │          ADMIN              │
└──────────────┴──────────────┴──────────────────────────────┘

MÓDULOS DISPONIBLES:

┌──────────┬──────────┬──────────┬──────────┐
│    📋    │    🧾    │    📄    │    📝    │
│ Facturas │ Tickets  │Proformas │Presuptos │
│ [badges] │ [badges] │ [badges] │ [badges] │
└──────────┴──────────┴──────────┴──────────┘

┌──────────┬──────────┬──────────┬──────────┐
│    📦    │    👥    │    💳    │    ✅    │
│Productos │Contactos │  Gastos  │Concil.   │
│ [badges] │ [badges] │ [badges] │ [badges] │
└──────────┴──────────┴──────────┴──────────┘

┌──────────┐
│    📊    │
│Estadíst. │
│ [badges] │
└──────────┘
```

**Características:**
- Header con logo y branding dinámico
- Stats cards con números grandes
- 9 tarjetas de módulos clicables
- Cada módulo muestra sus permisos activos
- Efecto hover en las tarjetas
- Colores personalizados por empresa

**Badges de Permisos (por módulo):**
```
[ver] [crear] [editar] [eliminar] [anular] [exportar]
```
- Verde = activo
- Gris = inactivo

**Acciones:**
- Clic en cualquier módulo → Va a su página
- Clic en "🚪 Salir" → Logout y vuelve a login

---

### 3️⃣ Pantalla Admin de Permisos

**URL:** `http://localhost:5001/ADMIN_PERMISOS.html` (requiere ser admin)

**Apariencia:**
```
┌─────────────────────────────────────────────────────────────┐
│ ⚙️ Administración de Permisos        [← Volver al Dashboard]│
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 🔐 Sistema de Permisos Multiempresa                         │
│                                                              │
│ Estado Actual:                                               │
│ El sistema multiempresa está en desarrollo...               │
│                                                              │
│ ⚠️ Nota: Para modificar permisos actualmente, se debe      │
│    hacer directamente en la base de datos                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 📊 Estadísticas del Sistema                                 │
│                                                              │
│  ┌─────────┬─────────┬─────────┬─────────────────┐        │
│  │    1    │    1    │    9    │       54        │        │
│  │Usuarios │Empresas │ Módulos │Permisos Config. │        │
│  └─────────┴─────────┴─────────┴─────────────────┘        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ ✅ Funcionalidades Implementadas                            │
│                                                              │
│  ✓ Sistema de autenticación multiempresa                   │
│  ✓ Gestión de sesiones seguras                             │
│  ✓ Base de datos central de usuarios                       │
│  ✓ Sistema de permisos granulares                          │
│  ✓ Menú dinámico según permisos                            │
│  ✓ Auditoría de acciones                                   │
│  ✓ Branding por empresa                                    │
│  ⏳ Interfaz de gestión de usuarios                        │
│  ⏳ Matriz de permisos editable                            │
│  ⏳ Gestión de empresas desde UI                           │
└─────────────────────────────────────────────────────────────┘
```

**Características:**
- Solo accesible para admins (@require_admin)
- Info del estado del sistema
- Estadísticas actualizadas
- Lista de funcionalidades
- Comandos SQL para gestión manual

**Acciones:**
- Clic en "← Volver al Dashboard" → Regresa al dashboard

---

## 🔍 Pruebas desde Terminal

### Test 1: Ver si Flask está corriendo
```bash
ps aux | grep flask
```

**Resultado esperado:**
```
sami  3009507  flask run --host=0.0.0.0 --port=5001
```

---

### Test 2: Probar API de Login
```bash
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123","empresa":"copisteria"}' \
  -c /tmp/cookies.txt
```

**Resultado esperado:**
```json
{
  "success": true,
  "usuario": "Administrador Sistema",
  "empresa": "Copistería Aleph70",
  "rol": "admin",
  "es_admin": 1
}
```

---

### Test 3: Ver sesión activa
```bash
curl http://localhost:5001/api/auth/session -b /tmp/cookies.txt
```

**Resultado esperado:**
```json
{
  "usuario": "Administrador Sistema",
  "username": "admin",
  "empresa": "Copistería Aleph70",
  "empresa_codigo": "copisteria",
  "rol": "admin",
  "es_admin": true,
  "es_superadmin": true
}
```

---

### Test 4: Ver módulos disponibles
```bash
curl http://localhost:5001/api/auth/menu -b /tmp/cookies.txt | jq .
```

**Resultado esperado:**
Array con 9 módulos, cada uno con:
- código
- nombre
- ruta
- icono
- permisos (6 tipos)

---

### Test 5: Ver branding de empresa
```bash
curl http://localhost:5001/api/auth/branding -b /tmp/cookies.txt | jq .
```

**Resultado esperado:**
```json
{
  "logo_header": "/static/logos/default_header.png",
  "logo_factura": "/static/logos/default_factura.png",
  "colores": {
    "primario": "#2c3e50",
    "secundario": "#3498db"
  },
  "datos": {
    "nombre": "Copistería Aleph70",
    "cif": "B12345678",
    "direccion": "Calle Principal 123",
    "telefono": "912345678",
    "email": "info@copisteria.com"
  }
}
```

---

## 📊 Verificar Base de Datos

```bash
sqlite3 /var/www/html/db/usuarios_sistema.db
```

### Consultas útiles:

```sql
-- Ver usuarios
SELECT * FROM usuarios;

-- Ver empresas
SELECT * FROM empresas;

-- Ver módulos
SELECT * FROM modulos;

-- Ver permisos del usuario admin
SELECT u.username, e.nombre, m.nombre, p.*
FROM permisos_usuario_modulo p
JOIN usuarios u ON p.usuario_id = u.id
JOIN empresas e ON p.empresa_id = e.id
JOIN modulos m ON p.modulo_codigo = m.codigo
WHERE u.username = 'admin';

-- Ver auditoría (últimas 10 acciones)
SELECT * FROM auditoria 
ORDER BY fecha DESC 
LIMIT 10;
```

---

## ✅ Checklist de Pruebas

Marca lo que has probado:

- [ ] Acceder a http://localhost:5001/
- [ ] Ver pantalla de login
- [ ] Hacer login con admin/admin123
- [ ] Ver dashboard con 9 módulos
- [ ] Verificar que aparece tu usuario y empresa
- [ ] Ver las 3 stats cards con números
- [ ] Hacer clic en un módulo (ej: Facturas)
- [ ] Volver al dashboard
- [ ] Acceder a /ADMIN_PERMISOS.html
- [ ] Ver estadísticas del sistema
- [ ] Hacer clic en "Volver al Dashboard"
- [ ] Hacer logout (botón "Salir")
- [ ] Verificar que vuelve a login
- [ ] Intentar acceder a /DASHBOARD.html sin login (debe redirigir)

---

## 🐛 Solución de Problemas

### Problema: No carga la página

**Verificar:**
```bash
# ¿Está Flask corriendo?
ps aux | grep flask

# ¿Puerto 5001 disponible?
netstat -tulpn | grep 5001

# ¿Hay errores en Flask?
# Ver en la terminal donde corre Flask
```

**Solución:**
```bash
# Reiniciar Flask
killall python3
cd /var/www/html
python3 app.py
```

---

### Problema: Error 404 al acceder

**Verificar rutas:**
```bash
cd /var/www/html
python3 test_routes.py | grep DASHBOARD
```

**Debe mostrar:**
```
servir_dashboard    GET    /DASHBOARD.html
```

---

### Problema: Login no funciona

**Verificar BD:**
```bash
sqlite3 /var/www/html/db/usuarios_sistema.db "SELECT * FROM usuarios"
```

**Debe existir usuario `admin`**

**Probar desde terminal:**
```bash
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123","empresa":"copisteria"}'
```

---

## 🎯 Script de Prueba Rápida

Ejecuta:
```bash
cd /var/www/html
./test_manual.sh
```

Este script prueba automáticamente todos los endpoints.

---

## 📞 Información Adicional

**Archivos importantes:**
- `/var/www/html/db/usuarios_sistema.db` - BD central
- `/var/www/html/db/aleph70.db` - BD de copistería
- `/var/www/html/frontend/DASHBOARD.html` - Dashboard
- `/var/www/html/frontend/ADMIN_PERMISOS.html` - Admin panel
- `/var/www/html/app.py` - Servidor Flask

**Logs:**
- Ver terminal donde corre Flask
- Ver `logs/aleph70.log`
- Ver `logs/errors.log`

---

## 🎊 ¡Listo!

Ahora tienes todo para probar el sistema multiempresa completo.

**Disfruta explorando el sistema! 🚀**

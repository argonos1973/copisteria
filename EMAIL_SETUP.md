# 📧 Configuración de Procesamiento Automático por Email

Sistema que monitorea un buzón de correo y procesa automáticamente fotos de contactos enviadas por email.

## 🎯 Flujo de Trabajo

```
1. Hacer foto de tarjeta con el móvil
2. Enviar email a: contactos@tu-dominio.com
   Asunto: NUEVO CONTACTO
   Adjunto: foto.jpg
3. Sistema procesa automáticamente cada 2 minutos
4. Contacto creado en base de datos
5. Recibes email de confirmación
```

---

## ⚙️ Configuración

### Paso 1: Decidir qué email usar

**Opción A - Gmail (Recomendado para pruebas)**
- Fácil de configurar
- Requiere "App Password"

**Opción B - Email corporativo**
- Tu propio dominio
- Más profesional

**Opción C - Email específico**
- Crear nuevo email solo para esto
- Ejemplo: contactos@tu-empresa.com

---

### Paso 2: Configurar Gmail (si usas Gmail)

1. **Habilitar verificación en 2 pasos:**
   - Ve a: https://myaccount.google.com/security
   - Activar "Verificación en 2 pasos"

2. **Crear App Password:**
   - Ve a: https://myaccount.google.com/apppasswords
   - Selecciona "Correo" y "Otro dispositivo"
   - Nombre: "Sistema Contactos"
   - Click "Generar"
   - **Copia la contraseña** (16 caracteres sin espacios)

---

### Paso 3: Agregar configuración al .env

Editar `/var/www/html/.env`:

```bash
# Email para procesamiento automático de contactos
EMAIL_USER=tu-email@gmail.com
EMAIL_PASSWORD=xxxx xxxx xxxx xxxx    # App Password de Gmail

# Configuración IMAP (Gmail)
EMAIL_IMAP_HOST=imap.gmail.com
EMAIL_IMAP_PORT=993

# Configuración SMTP (para enviar confirmaciones)
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587

# Asunto a buscar en emails
EMAIL_ASUNTO_CONTACTO=NUEVO CONTACTO
```

**Para otros servicios de email:**

**Outlook/Hotmail:**
```bash
EMAIL_IMAP_HOST=outlook.office365.com
EMAIL_IMAP_PORT=993
EMAIL_SMTP_HOST=smtp.office365.com
EMAIL_SMTP_PORT=587
```

**Yahoo:**
```bash
EMAIL_IMAP_HOST=imap.mail.yahoo.com
EMAIL_IMAP_PORT=993
EMAIL_SMTP_HOST=smtp.mail.yahoo.com
EMAIL_SMTP_PORT=587
```

---

### Paso 4: Instalar dependencias (si es necesario)

```bash
cd /var/www/html
source venv/bin/activate
# imaplib y smtplib ya vienen con Python
```

---

### Paso 5: Configurar Cron Job

El cron job ejecutará el script cada 2 minutos.

```bash
# Editar crontab
crontab -e

# Agregar esta línea al final:
*/2 * * * * cd /var/www/html && /var/www/html/venv/bin/python3 /var/www/html/procesar_emails_contactos.py >> /var/www/html/logs/email_processor.log 2>&1
```

Esto significa:
- `*/2 * * * *` = Cada 2 minutos
- Ejecuta el script Python
- Guarda logs en `logs/email_processor.log`

**Para verificar que el cron está activo:**
```bash
crontab -l
```

---

### Paso 6: Crear directorio de logs

```bash
mkdir -p /var/www/html/logs
sudo chown -R www-data:www-data /var/www/html/logs
```

---

### Paso 7: Probar manualmente

```bash
cd /var/www/html
source venv/bin/activate

# Cargar variables de entorno
source .env

# Ejecutar script manualmente
python3 procesar_emails_contactos.py
```

---

## 🧪 Prueba Completa

1. **Enviar email de prueba:**
   ```
   Para: tu-email@gmail.com (el configurado)
   Asunto: NUEVO CONTACTO
   Adjunto: foto_tarjeta.jpg
   ```

2. **Ejecutar script manualmente:**
   ```bash
   cd /var/www/html
   source venv/bin/activate
   source .env
   python3 procesar_emails_contactos.py
   ```

3. **Verificar logs:**
   ```bash
   tail -f /var/www/html/logs/email_processor.log
   ```

4. **Verificar base de datos:**
   ```bash
   sqlite3 /var/www/html/gestion_copisteria.db "SELECT * FROM contactos ORDER BY id DESC LIMIT 1;"
   ```

5. **Deberías recibir email de confirmación:**
   ```
   ✅ Contacto procesado automáticamente
   
   Datos extraídos:
   - Empresa: ...
   - NIF: ...
   - Teléfono: ...
   etc.
   ```

---

## 📊 Monitoreo

### Ver logs en tiempo real:
```bash
tail -f /var/www/html/logs/email_processor.log
```

### Ver últimos contactos creados:
```bash
sqlite3 /var/www/html/gestion_copisteria.db "SELECT id, razon_social, email, fecha_alta FROM contactos ORDER BY id DESC LIMIT 10;"
```

### Verificar cron job:
```bash
grep CRON /var/log/syslog | tail -20
```

---

## 🎯 Uso Diario

### Desde el móvil:

1. **Hacer foto a tarjeta de visita**

2. **Abrir app de email**

3. **Nuevo email:**
   - **Para:** contactos@tu-dominio.com
   - **Asunto:** NUEVO CONTACTO (o lo que configuraste)
   - **Adjuntar:** foto recién tomada

4. **Enviar**

5. **Esperar 2 minutos máximo**

6. **Recibirás confirmación:**
   ```
   ✅ Contacto procesado exitosamente
   ID: 123
   Empresa: ...
   ```

7. **¡Listo!** El contacto ya está en tu sistema

---

## ⚡ Configuración Avanzada

### Cambiar frecuencia de procesamiento:

**Cada 1 minuto (más rápido):**
```bash
*/1 * * * * cd /var/www/html && ...
```

**Cada 5 minutos (más ahorro):**
```bash
*/5 * * * * cd /var/www/html && ...
```

**Solo horario laboral (9am-6pm):**
```bash
*/2 9-18 * * 1-5 cd /var/www/html && ...
```

### Cambiar asunto del email:

En `.env`:
```bash
EMAIL_ASUNTO_CONTACTO=CONTACTO NUEVO
# o
EMAIL_ASUNTO_CONTACTO=TARJETA
# o lo que prefieras
```

### Procesar múltiples buzones:

Crear múltiples cron jobs con diferentes configs.

---

## 🔒 Seguridad

✅ **Usa App Password, NO tu contraseña real**
✅ **No compartas credenciales de email**
✅ **Email en .env, NO en código**
✅ **.env en .gitignore**
✅ **Permisos 640 en .env**

---

## ❌ Troubleshooting

### "Error: Invalid credentials"
- Verifica EMAIL_USER y EMAIL_PASSWORD
- Si Gmail: usa App Password, no contraseña normal
- Activa IMAP en configuración de Gmail

### "Error: Cannot connect to IMAP server"
- Verifica EMAIL_IMAP_HOST y EMAIL_IMAP_PORT
- Firewall podría estar bloqueando puerto 993

### "Email procesado pero no se crea contacto"
- Revisa logs: `tail -f logs/email_processor.log`
- Verifica que GPT-4 Vision esté configurado (OPENAI_API_KEY)
- Verifica que la imagen sea legible

### "No se envía email de confirmación"
- Verifica EMAIL_SMTP_HOST y EMAIL_SMTP_PORT
- Gmail: revisa que App Password tenga permisos de SMTP

### "Cron no ejecuta el script"
- Verifica: `crontab -l`
- Revisa logs de cron: `grep CRON /var/log/syslog`
- Asegúrate que el path del script sea absoluto

---

## 💰 Costos

**Gmail:** Gratis (con límites)
- Límite: ~10,000 emails/día
- Suficiente para uso normal

**GPT-4 Vision:**
- ~$0.01 por imagen procesada
- Si procesas 100 tarjetas/mes = ~$1.00/mes

**Total:** Prácticamente gratis para uso moderado

---

## 📱 Apps de Email Recomendadas (móvil)

**Android:**
- Gmail (oficial)
- Outlook
- K-9 Mail

**iOS:**
- Mail (nativo)
- Gmail
- Outlook

**Tip:** Configura acceso rápido para enviar fotos directamente desde la cámara.

---

## 🎯 Comparativa de Métodos

| Método | Tiempo | Pasos | Comodidad |
|--------|--------|-------|-----------|
| **Email automático** | 2 min | 3 | ⭐⭐⭐⭐⭐ |
| Web desde móvil | 30 seg | 6 | ⭐⭐⭐⭐ |
| Web desde PC | 2 min | 8 | ⭐⭐⭐ |
| Manual | 5 min | 10 | ⭐⭐ |

**Mejor método:** Depende de tu flujo de trabajo
- **Si estás en el mostrador:** Web desde móvil (más rápido)
- **Si estás fuera o múltiples tarjetas:** Email automático (más cómodo)

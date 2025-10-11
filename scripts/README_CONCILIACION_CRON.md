# Conciliación Automática por Cron

Sistema de conciliación automática que se ejecuta periódicamente mediante cron.

## 📁 Archivos

- **`ejecutar_conciliacion_automatica.py`**: Script principal que ejecuta la conciliación
- **`instalar_cron_conciliacion.sh`**: Script de instalación de la tarea cron
- **`README_CONCILIACION_CRON.md`**: Este archivo

## 🚀 Instalación

### 1. Instalar la tarea cron

```bash
cd /var/www/html/scripts
./instalar_cron_conciliacion.sh
```

### 2. Verificar instalación

```bash
crontab -l
```

Deberías ver una línea como:
```
0 8-20 * * 1-5 /usr/bin/python3 /var/www/html/scripts/ejecutar_conciliacion_automatica.py >> /var/www/html/logs/conciliacion_cron.log 2>&1
```

## ⏰ Horario de Ejecución

**Por defecto:** Cada hora de 8:00 a 20:00, de lunes a viernes

Para modificar el horario, edita el archivo `instalar_cron_conciliacion.sh` y cambia la línea:
```bash
CRON_ENTRY="0 8-20 * * 1-5 ..."
```

### Ejemplos de horarios:

- **Cada 30 minutos (8:00-20:00):** `*/30 8-20 * * 1-5`
- **Cada 2 horas (todo el día):** `0 */2 * * *`
- **A las 9:00, 12:00 y 18:00:** `0 9,12,18 * * 1-5`
- **Cada hora (24/7):** `0 * * * *`

## 📊 Funcionamiento

El script realiza las siguientes acciones:

1. **Obtiene gastos pendientes** con importe positivo (ingresos/cobros)
2. **Busca coincidencias** para cada gasto:
   - Por número de factura en el concepto
   - Por fecha e importe
3. **Concilia automáticamente** cuando:
   - Hay coincidencia exacta (diferencia < 0.01€)
   - Hay combinación de documentos que suma el importe (diferencia < 1€)
4. **Marca facturas como cobradas** si:
   - Estado pendiente (P) o vencido (V)
   - Número de factura en concepto del gasto
   - Importe exacto

## 📝 Logs

### Ver log en tiempo real:
```bash
tail -f /var/www/html/logs/conciliacion_cron.log
```

### Ver últimas 50 líneas:
```bash
tail -50 /var/www/html/logs/conciliacion_cron.log
```

### Ver resumen de ejecuciones:
```bash
grep "CONCILIACIÓN COMPLETADA" /var/www/html/logs/conciliacion_cron.log
```

### Ver solo conciliaciones exitosas:
```bash
grep "✅ CONCILIADO" /var/www/html/logs/conciliacion_cron.log
```

## 🔧 Ejecución Manual

Para ejecutar manualmente (sin esperar al cron):

```bash
cd /var/www/html
python3 scripts/ejecutar_conciliacion_automatica.py
```

## 🛑 Desinstalar

Para eliminar la tarea cron:

```bash
crontab -l | grep -v "ejecutar_conciliacion_automatica.py" | crontab -
```

## 📋 Ejemplo de Salida

```
[2025-10-11 12:29:08] ================================================================================
[2025-10-11 12:29:08] 🚀 INICIANDO CONCILIACIÓN AUTOMÁTICA
[2025-10-11 12:29:08] ================================================================================
[2025-10-11 12:29:08] 📋 Gastos pendientes encontrados: 120
[2025-10-11 12:29:08] 📊 Gastos a procesar (importe > 0): 106
[2025-10-11 12:29:08] 
--- Procesando gasto 18261 (93.14€) ---
[2025-10-11 12:29:08]     Concepto: Transferencia De Getnet Europe...
[2025-10-11 12:29:08]     ✓ 1 coincidencias encontradas
[2025-10-11 12:29:08]     ✅ CONCILIADO con factura F250321 (diferencia: 0.00€)
...
[2025-10-11 12:29:08] ================================================================================
[2025-10-11 12:29:08] ✅ CONCILIACIÓN COMPLETADA
[2025-10-11 12:29:08]    Total procesados: 106
[2025-10-11 12:29:08]    Total conciliados: 38
[2025-10-11 12:29:08]    Pendientes: 68
[2025-10-11 12:29:08] ================================================================================
```

## 🔍 Troubleshooting

### El cron no se ejecuta

1. Verificar que el cron está instalado:
   ```bash
   crontab -l
   ```

2. Verificar permisos del script:
   ```bash
   ls -la /var/www/html/scripts/ejecutar_conciliacion_automatica.py
   ```

3. Verificar logs del sistema:
   ```bash
   grep CRON /var/log/syslog | tail -20
   ```

### Errores en el log

1. Verificar que Flask está corriendo:
   ```bash
   curl http://localhost:5001/api/conciliacion/gastos-pendientes
   ```

2. Verificar permisos de escritura en logs:
   ```bash
   ls -la /var/www/html/logs/
   ```

3. Ejecutar manualmente para ver errores:
   ```bash
   python3 /var/www/html/scripts/ejecutar_conciliacion_automatica.py
   ```

## 📞 Soporte

Para más información, consulta:
- `/var/www/html/conciliacion.py` - Lógica de conciliación
- `/var/www/html/static/conciliacion_gastos.js` - Frontend de conciliación

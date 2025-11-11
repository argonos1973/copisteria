# Configuración de Permisos

## Directorios que requieren permisos de escritura para www-data

Los siguientes directorios necesitan permisos `775` y propietario `www-data:www-data`:

```bash
/var/www/html/static/avatars    # Subida de avatares de usuario
/var/www/html/static/emisores   # Archivos JSON de emisores
/var/www/html/static/logos      # Logos de empresas
/var/www/html/db                # Bases de datos
```

## Script de corrección rápida

```bash
#\!/bin/bash
DIRS=(
    "/var/www/html/static/avatars"
    "/var/www/html/static/emisores"
    "/var/www/html/static/logos"
    "/var/www/html/db"
)

for dir in "${DIRS[@]}"; do
    sudo chown -R www-data:www-data "$dir"
    sudo chmod 775 "$dir"
done
```

## Verificación

```bash
ls -ld /var/www/html/static/{avatars,emisores,logos} /var/www/html/db
```

Todos deben mostrar: `drwxrwxr-x ... www-data www-data ...`

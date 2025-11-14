#!/bin/bash

# Script para copiar avatares desde servidor SMB
# Uso: ./copiar_avatares.sh [usuario] [contraseña]

SMB_SERVER="//mac-mini-de-sami.local/swapbatch/"
DESTINO="/var/www/html/static/avatares/"
USUARIO="${1:-}"
PASSWORD="${2:-}"

echo "🔄 Copiando avatares desde $SMB_SERVER"
echo "📁 Destino: $DESTINO"

# Crear directorio si no existe
sudo mkdir -p "$DESTINO"

# Montar temporalmente el recurso SMB
MOUNT_POINT="/tmp/smb_avatares_$$"
mkdir -p "$MOUNT_POINT"

if [ -n "$USUARIO" ] && [ -n "$PASSWORD" ]; then
    echo "🔐 Usando credenciales proporcionadas..."
    sudo mount -t cifs "$SMB_SERVER" "$MOUNT_POINT" -o username="$USUARIO",password="$PASSWORD"
else
    echo "🔓 Intentando conexión sin credenciales..."
    sudo mount -t cifs "$SMB_SERVER" "$MOUNT_POINT" -o guest
fi

if [ $? -eq 0 ]; then
    echo "✅ Montaje exitoso"
    
    # Copiar archivos que empiecen con "avatar"
    echo "📋 Copiando archivos avatar*..."
    sudo cp -v "$MOUNT_POINT"/avatar* "$DESTINO/" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "✅ Avatares copiados exitosamente"
        
        # Ajustar permisos
        sudo chown -R www-data:www-data "$DESTINO"
        sudo chmod -R 644 "$DESTINO"/*
        
        # Contar archivos
        COUNT=$(ls -1 "$DESTINO"/avatar* 2>/dev/null | wc -l)
        echo "📊 Total de avatares: $COUNT"
    else
        echo "⚠️  No se encontraron archivos avatar* en el servidor"
    fi
    
    # Desmontar
    sudo umount "$MOUNT_POINT"
    rmdir "$MOUNT_POINT"
    echo "✅ Desmontado correctamente"
else
    echo "❌ Error al montar el recurso SMB"
    echo "💡 Uso: $0 [usuario] [contraseña]"
    rmdir "$MOUNT_POINT"
    exit 1
fi

echo "🎉 Proceso completado"

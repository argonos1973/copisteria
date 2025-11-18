# Configuración de Datos del Emisor

Este directorio contiene los archivos JSON con los datos del emisor para cada empresa del sistema.

## Estructura de archivos

Cada empresa debe tener un archivo con el formato: `{codigo_empresa}_emisor.json`

Por ejemplo:
- `caca_emisor.json` para la empresa con código "caca"
- `CHAPA_emisor.json` para la empresa con código "CHAPA"

## Formato del archivo JSON

```json
{
    "nombre": "NOMBRE DE LA EMPRESA",
    "nif": "B12345678",
    "direccion": "Calle Principal 123",
    "cp": "28001",
    "ciudad": "MADRID",
    "provincia": "MADRID",
    "pais": "ESP",
    "email": "info@empresa.com",
    "telefono": "912345678",
    "registro_mercantil": "Madrid, Tomo 12345, Folio 67, Hoja M-123456",
    "logo": "/static/logos/empresa_logo.png"
}
```

## Campos obligatorios

- **nombre**: Razón social de la empresa
- **nif**: NIF/CIF de la empresa
- **direccion**: Dirección fiscal
- **cp**: Código postal
- **ciudad**: Ciudad
- **provincia**: Provincia
- **pais**: Código de país (por defecto "ESP")

## Campos opcionales

- **email**: Email de contacto
- **telefono**: Teléfono de contacto
- **registro_mercantil**: Datos del registro mercantil
- **logo**: Ruta al logo de la empresa

## Permisos

Los archivos deben tener permisos de lectura para el usuario www-data:

```bash
sudo chown www-data:www-data *.json
sudo chmod 644 *.json
```

## Uso

Estos datos se utilizan automáticamente en:
- Impresión de facturas
- Impresión de tickets
- Generación de documentos PDF
- Facturación electrónica

## Notas importantes

1. El código de empresa debe coincidir exactamente con el código en la base de datos
2. Los archivos JSON deben ser UTF-8 válido
3. Si no existe el archivo para una empresa, se usarán datos vacíos por defecto

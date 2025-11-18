# Changelog de Base de Datos

## 2025-11-18 - Consolidación de Proveedores Duplicados

### Problema
Había 3 registros duplicados de "UNIÓN PAPELERA" con diferentes NIFs:
- ID 180: NIF A50561132 (1 factura)
- ID 182: NIF A-08182976 (1 factura)  
- ID 184: NIF A50046029 (1 factura)

### Solución
Consolidados en un solo registro (ID 180) con todas las facturas:

```sql
-- Migrar facturas al proveedor principal
UPDATE facturas_proveedores SET proveedor_id = 180 WHERE proveedor_id = 182;
UPDATE facturas_proveedores SET proveedor_id = 180 WHERE proveedor_id = 184;

-- Eliminar duplicados
DELETE FROM proveedores WHERE id = 182;
DELETE FROM proveedores WHERE id = 184;
```

### Resultado
- **Proveedor consolidado:** UNIÓN PAPELERA (ID 180)
- **NIF:** A50561132
- **Email:** ventas@unionpapelera.es
- **Facturas:** 3 (55015171, 55016481, 55020478)
- **Total:** 608,77€

### Base de datos afectada
- `db/caca/caca.db`
- Tablas: `proveedores`, `facturas_proveedores`

# 🎯 SISTEMA DE PAGOS PARCIALES PARA PROFORMAS

## 📋 PROBLEMA ACTUAL

**Situación:**
- Los clientes pagan proformas de forma parcial (efectivo/tarjeta)
- Cuando completan el pago o lo solicitan → Se convierte en factura
- Actualmente solo existe el campo `importe_cobrado` que acumula el total
- **NO hay registro de cada pago individual** (fecha, método, importe)
- **NO se puede conciliar con TPV** ni caja diaria

**Ejemplo Real:**
```
Proforma P250047:
- Total: 288.99€
- Pagado: 69.93€  ← ¿Cuándo? ¿Cómo? ¿Cuántos pagos?
- Pendiente: 219.06€
```

---

## ✅ SOLUCIÓN PROPUESTA

### **1. Nueva Tabla: pagos_proforma**

```sql
CREATE TABLE pagos_proforma (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_proforma INTEGER NOT NULL,
    fecha TEXT NOT NULL,                    -- Fecha del pago
    importe REAL NOT NULL,                  -- Cantidad pagada
    metodo_pago TEXT NOT NULL,              -- 'E' (Efectivo), 'T' (Tarjeta), 'R' (Transferencia)
    referencia TEXT,                        -- Nº operación tarjeta, nº transferencia, etc.
    notas TEXT,                             -- Observaciones
    usuario TEXT,                           -- Usuario que registra el pago
    timestamp TEXT NOT NULL,                -- Fecha/hora registro
    conciliado INTEGER DEFAULT 0,           -- 0=No conciliado, 1=Conciliado
    id_liquidacion INTEGER,                 -- FK a liquidaciones_tpv si es tarjeta
    FOREIGN KEY(id_proforma) REFERENCES proforma(id)
);

CREATE INDEX idx_pagos_proforma_id ON pagos_proforma(id_proforma);
CREATE INDEX idx_pagos_proforma_fecha ON pagos_proforma(fecha);
CREATE INDEX idx_pagos_proforma_metodo ON pagos_proforma(metodo_pago);
CREATE INDEX idx_pagos_proforma_conciliado ON pagos_proforma(conciliado);
```

---

### **2. Backend: Endpoints API**

#### **A) Registrar Pago**
```python
@app.route('/api/proformas/<int:id_proforma>/pagos', methods=['POST'])
def registrar_pago_proforma(id_proforma):
    """
    Registra un pago parcial de una proforma
    
    Body JSON:
    {
        "importe": 50.00,
        "metodo_pago": "T",  // E=Efectivo, T=Tarjeta, R=Transferencia
        "referencia": "OPE-123456",
        "notas": "Primer pago de 3"
    }
    """
```

**Lógica:**
1. Validar que la proforma existe y está activa (estado='A')
2. Validar que el importe > 0
3. Validar que importe_cobrado + nuevo_pago <= total
4. Insertar en `pagos_proforma`
5. Actualizar `proforma.importe_cobrado += importe`
6. Si `importe_cobrado >= total` → **Avisar** que está completamente pagada
7. Devolver saldo pendiente

#### **B) Listar Pagos de una Proforma**
```python
@app.route('/api/proformas/<int:id_proforma>/pagos', methods=['GET'])
def listar_pagos_proforma(id_proforma):
    """Devuelve todos los pagos de una proforma"""
```

#### **C) Obtener Resumen de Proforma con Pagos**
```python
@app.route('/api/proformas/<int:id_proforma>/resumen', methods=['GET'])
def resumen_proforma(id_proforma):
    """
    Devuelve:
    {
        "proforma": {...},
        "total": 288.99,
        "pagado": 69.93,
        "pendiente": 219.06,
        "pagos": [
            {
                "id": 1,
                "fecha": "2025-10-02",
                "importe": 30.00,
                "metodo_pago": "E",
                "conciliado": 1
            },
            {
                "id": 2,
                "fecha": "2025-10-10",
                "importe": 39.93,
                "metodo_pago": "T",
                "referencia": "OPE-789456",
                "conciliado": 0
            }
        ]
    }
    """
```

#### **D) Eliminar/Anular Pago**
```python
@app.route('/api/proformas/pagos/<int:id_pago>', methods=['DELETE'])
def anular_pago_proforma(id_pago):
    """
    Anula un pago y resta del importe_cobrado
    Solo si NO está conciliado
    """
```

---

### **3. Frontend: Interfaz de Gestión**

#### **A) Modal de Pagos en Proformas**
```html
<!-- En consulta_proforma.html -->
<button onclick="verPagosProforma(idProforma)">
    💰 Ver Pagos (3)
</button>
```

#### **B) Formulario Registrar Pago**
```
┌─────────────────────────────────────────────┐
│  💳 Registrar Pago - Proforma P250047       │
├─────────────────────────────────────────────┤
│  Total: 288.99€                             │
│  Pagado: 69.93€                             │
│  Pendiente: 219.06€                         │
├─────────────────────────────────────────────┤
│  Importe: [________] €                      │
│  Método:  (•) Efectivo  ( ) Tarjeta         │
│            ( ) Transferencia                │
│  Referencia: [_______________________]      │
│  Notas: [__________________________]        │
│                                             │
│  [Cancelar]  [Registrar Pago]              │
└─────────────────────────────────────────────┘
```

#### **C) Historial de Pagos**
```
┌───────────────────────────────────────────────────┐
│  📜 Historial de Pagos - P250047                  │
├────────┬─────────┬────────┬────────────┬─────────┤
│ Fecha  │ Importe │ Método │ Referencia │ Estado  │
├────────┼─────────┼────────┼────────────┼─────────┤
│ 02/10  │  30.00€ │ Efec.  │ -          │ ✅ Conc.│
│ 10/10  │  39.93€ │ Tarjeta│ OPE-789456 │ ⏳ Pend.│
├────────┴─────────┴────────┴────────────┴─────────┤
│ TOTAL PAGADO: 69.93€                              │
│ PENDIENTE: 219.06€                                │
└───────────────────────────────────────────────────┘
```

---

### **4. Conciliación con TPV**

#### **Opción 1: Manual (Más Simple)**
```python
# Marcar pago como conciliado manualmente
@app.route('/api/proformas/pagos/<int:id_pago>/conciliar', methods=['POST'])
def conciliar_pago_manual(id_pago):
    """Marca un pago como conciliado manualmente"""
```

#### **Opción 2: Automática (Avanzada)**
```python
# Vincular pago con liquidación TPV
@app.route('/api/conciliacion/vincular_pago_proforma', methods=['POST'])
def vincular_pago_liquidacion():
    """
    Body:
    {
        "id_pago": 123,
        "id_liquidacion": 456
    }
    
    Vincula un pago de proforma con una liquidación del TPV
    """
```

---

### **5. Reportes y Consultas**

#### **A) Proformas con Saldo Pendiente**
```sql
SELECT 
    p.numero,
    p.fecha,
    c.nombre,
    p.total,
    COALESCE(p.importe_cobrado, 0) as pagado,
    (p.total - COALESCE(p.importe_cobrado, 0)) as pendiente,
    COUNT(pp.id) as num_pagos
FROM proforma p
LEFT JOIN pagos_proforma pp ON p.id = pp.id_proforma
LEFT JOIN contactos c ON p.idContacto = c.id
WHERE p.estado = 'A' 
  AND p.total > COALESCE(p.importe_cobrado, 0)
GROUP BY p.id
ORDER BY p.fecha DESC;
```

#### **B) Pagos Sin Conciliar**
```sql
SELECT 
    pp.fecha,
    p.numero,
    pp.importe,
    pp.metodo_pago,
    pp.referencia
FROM pagos_proforma pp
INNER JOIN proforma p ON pp.id_proforma = p.id
WHERE pp.conciliado = 0
  AND pp.metodo_pago = 'T'  -- Solo tarjetas
ORDER BY pp.fecha DESC;
```

---

## 📊 BENEFICIOS

| Antes | Después |
|-------|---------|
| ❌ Solo total acumulado | ✅ Historial completo de pagos |
| ❌ Sin fecha de cada pago | ✅ Fecha y hora de cada pago |
| ❌ Sin método de pago | ✅ Efectivo, Tarjeta, Transferencia |
| ❌ Sin conciliación TPV | ✅ Vinculación con liquidaciones |
| ❌ Sin trazabilidad | ✅ Auditoría completa |
| ❌ No se puede anular | ✅ Anulación de pagos |

---

## 🚀 IMPLEMENTACIÓN POR FASES

### **FASE 1: Base de Datos (15 min)**
1. Crear tabla `pagos_proforma`
2. Crear índices
3. Migrar datos existentes (opcional)

### **FASE 2: Backend API (45 min)**
1. Endpoint registrar pago
2. Endpoint listar pagos
3. Endpoint resumen proforma
4. Endpoint anular pago

### **FASE 3: Frontend Básico (1h)**
1. Modal de pagos en proformas
2. Formulario registrar pago
3. Lista de pagos
4. Indicador visual de saldo

### **FASE 4: Conciliación (1h)**
1. Marcar pagos como conciliados
2. Reportes de pagos pendientes
3. Dashboard de proformas

### **FASE 5: Avanzado (Opcional)**
1. Vincular con liquidaciones TPV
2. Conciliación automática
3. Alertas de proformas vencidas

---

## 💡 EJEMPLOS DE USO

### **Caso 1: Cliente Paga en 3 Cuotas**
```
1. Proforma P250047: 288.99€
2. Pago 1 (02/10): 100€ efectivo → importe_cobrado = 100€
3. Pago 2 (10/10): 100€ tarjeta → importe_cobrado = 200€
4. Pago 3 (20/10): 88.99€ efectivo → importe_cobrado = 288.99€
5. Cliente solicita factura → Convertir a factura
```

### **Caso 2: Conciliar con TPV**
```
1. Liquidación TPV 15/10: 150€
2. Buscar pagos de proformas con tarjeta: 
   - P250047: 100€ (10/10) ← Coincide
   - P250050: 50€ (15/10) ← Coincide
3. Total: 150€ ✅ Cuadra
4. Marcar ambos pagos como conciliados
```

---

## ❓ DECISIONES PENDIENTES

1. **¿Permitir pagos superiores al total?** (anticipo)
2. **¿Generar recibo de pago?** (PDF)
3. **¿Enviar email al registrar pago?**
4. **¿Integrar con caja diaria?** (efectivo)
5. **¿Permitir pagos negativos?** (devoluciones)
6. **¿Control de permisos?** (quién puede registrar pagos)

---

## 📝 NOTAS TÉCNICAS

- Usar **TRANSACCIONES** para garantizar consistencia
- Validar siempre que `importe_cobrado <= total`
- Bloquear conversión a factura si hay pagos sin conciliar (opcional)
- Guardar usuario que registra cada pago
- Log de todas las operaciones

---

¿Procedemos con la implementación? ¿Qué fase quieres empezar?

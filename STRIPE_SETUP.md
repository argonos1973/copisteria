# Configuración de Stripe para Aleph70

## Requisitos Previos

1. Crear cuenta en [Stripe Dashboard](https://dashboard.stripe.com)
2. Obtener las claves API (test y producción)

## Variables de Entorno

Añadir al archivo `.env`:

```bash
# Stripe - Modo TEST
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxxx
STRIPE_PRICE_ID=price_xxxxxxxxxxxxxxxxxxxxx

# Stripe - Modo PRODUCCIÓN (cuando esté listo)
# STRIPE_SECRET_KEY=sk_live_xxxxxxxxxxxxxxxxxxxxx
# STRIPE_PUBLISHABLE_KEY=pk_live_xxxxxxxxxxxxxxxxxxxxx
# STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxxx
# STRIPE_PRICE_ID=price_xxxxxxxxxxxxxxxxxxxxx
```

## Crear Producto y Precio en Stripe

### 1. Crear el Producto

En Stripe Dashboard > Products > Add Product:
- **Nombre:** Aleph70 Premium
- **Descripción:** Acceso completo al sistema de gestión empresarial
- **Imagen:** Logo de Aleph70

### 2. Crear el Precio

- **Tipo:** Recurring (Recurrente)
- **Precio:** 20.00 EUR
- **Período:** Mensual
- **ID del precio:** Copiar el `price_xxx` generado y añadirlo a `STRIPE_PRICE_ID`

## Configurar Webhook

En Stripe Dashboard > Developers > Webhooks > Add endpoint:

- **URL:** `https://tu-dominio.com/api/subscription/webhook`
- **Eventos a escuchar:**
  - `checkout.session.completed`
  - `customer.subscription.created`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
  - `invoice.paid`
  - `invoice.payment_failed`

Copiar el **Signing secret** y añadirlo a `STRIPE_WEBHOOK_SECRET`

## Probar en Modo Test

### Tarjetas de Prueba

| Número | Resultado |
|--------|-----------|
| 4242 4242 4242 4242 | Pago exitoso |
| 4000 0000 0000 0002 | Tarjeta rechazada |
| 4000 0000 0000 3220 | Requiere autenticación 3D Secure |

- **Fecha:** Cualquier fecha futura
- **CVC:** Cualquier 3 dígitos
- **ZIP:** Cualquier código postal

### Probar Webhook Localmente

Usar Stripe CLI:

```bash
# Instalar Stripe CLI
brew install stripe/stripe-cli/stripe

# Login
stripe login

# Escuchar eventos y reenviar al servidor local
stripe listen --forward-to localhost:5000/api/subscription/webhook
```

## Endpoints Disponibles

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/subscription/config` | Configuración pública de Stripe |
| POST | `/api/subscription/create-checkout-session` | Crear sesión de pago |
| POST | `/api/subscription/portal` | Portal de gestión del cliente |
| GET | `/api/subscription/status/<empresa_id>` | Estado de suscripción |
| POST | `/api/subscription/cancel` | Cancelar suscripción |
| POST | `/api/subscription/reactivate` | Reactivar suscripción |
| GET | `/api/subscription/payment-history/<empresa_id>` | Historial de pagos |
| POST | `/api/subscription/webhook` | Webhook de Stripe |

## Base de Datos

Se crea automáticamente en `/var/www/html/db/subscriptions.db`:

- **subscriptions:** Estado de suscripciones por empresa
- **payment_history:** Historial de pagos
- **webhook_events:** Registro de eventos de Stripe

## Flujo de Suscripción

```
1. Usuario hace clic en "Suscribirse"
           ↓
2. Se abre modal con formulario (empresa, email)
           ↓
3. POST /api/subscription/create-checkout-session
           ↓
4. Stripe crea sesión de checkout
           ↓
5. Usuario redirigido a Stripe Checkout
           ↓
6. Usuario completa pago
           ↓
7. Stripe envía webhook checkout.session.completed
           ↓
8. Sistema actualiza estado de suscripción
           ↓
9. Usuario redirigido a /subscription/success
```

## Producción

Antes de pasar a producción:

1. ✅ Cambiar claves de test a live
2. ✅ Verificar webhook con URL de producción
3. ✅ Crear precio en modo live (mismo precio que test)
4. ✅ Configurar impuestos si es necesario (Stripe Tax)
5. ✅ Revisar política de cancelación y reembolsos

## Soporte

- [Documentación de Stripe](https://stripe.com/docs)
- [API Reference](https://stripe.com/docs/api)
- [Testing](https://stripe.com/docs/testing)

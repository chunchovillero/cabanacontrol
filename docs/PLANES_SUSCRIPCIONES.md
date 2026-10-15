# Planes y suscripciones locales — 11D.1

Implementación autorizada con «sigue» después de la propuesta comercial y sus
decisiones confirmadas. Esta entrega es local/manual: no realiza cobros, contrata
servicios ni declara superada la puerta P. No incluye 11D.2 ni 11D.3.

## Pantalla

Con sesión de propietario y empresa seleccionada, abrir **Plan y uso** (`/plan`).
En este equipo: http://localhost:15173/plan. Muestra plan, plazas utilizadas,
habilitación de límites, fin del trial y catálogo con precios visuales de referencia.
Estos precios se comparten con la página de presentación; no crean contratos ni
modifican el API de suscripción. Lectura solo para
propietarios; administradores de plataforma no obtienen acceso operativo implícito.
Se actualiza al cargar, recuperar foco y cada minuto mientras está abierta.

| Modalidad | Cabañas activas | Membresías activas |
| --- | ---: | ---: |
| Trial, 14 días | 1 | 1 |
| Inicial | 3 | 2 |
| Crecimiento | 8 | 5 |
| Operador | 20 | 10 |

El propietario ocupa una plaza. Invitaciones pendientes no reservan plazas.
Al aceptar, el backend comprueba capacidad; si falla, no crea cuenta/membresía
parciales. Al vencer la prueba conserva capacidad 1/1, con aviso y sin suspender
reservas, edición, pagos de huéspedes, consulta o exportaciones autorizadas.

`Asignación manual` no significa mensualidad pagada. No hay precio cero implícito,
tarjetas, periodos de cobro, facturas o renovaciones automáticas. Tras 11D.1 se
definieron precios de referencia y Mercado Pago como objetivo futuro; no hay
integración activa. IA/WhatsApp conservan sus flags, autorizaciones y cuotas.

## Migración y habilitación separadas

Las migraciones crean tres tablas, sus restricciones y un trigger PostgreSQL que
impide modificar/borrar versiones de planes. No insertan suscripciones, asignan
planes, inician trials ni habilitan límites de empresas existentes.

La habilitación es **por empresa**, tras revisar su uso y asignarle un plan. No hay
un interruptor global que afecte inadvertidamente empresas sin revisar. Este es el
detalle técnico elegido para ejecutar la transición manual confirmada. Para dar
por habilitado todo el módulo en un entorno, revisar y completar todas las empresas
activas del inventario. Las nuevas altas siguen sin asignación hasta revisión manual;
el registro no se convierte en autoservicio comercial en esta entrega.

Dentro de la raíz, con Docker iniciado:

```powershell
docker compose exec backend python manage.py migrate --noinput
# Inventario de IDs y uso; sin correos, nombres ni documentos de huéspedes.
docker compose exec backend python manage.py manage_subscription review
docker compose exec backend python manage.py manage_subscription review --tenant-id UUID
```

Asignación/habilitación requieren una cuenta activa de administrador de plataforma
y acceso a la consola del servidor. Un propietario común no puede concederse otro
plan. Si no existe administrador de plataforma, crearlo de forma interactiva con
`docker compose exec backend python manage.py createsuperuser`; no convierte al
propietario existente ni concede membresías de empresas.

Ejemplos con identificadores/correo ficticios para sustituir expresamente:

```powershell
docker compose exec backend python manage.py manage_subscription assign --tenant-id UUID --actor-email plataforma@example.invalid --plan initial --reason "Uso revisado y capacidad acordada"
# Revisar nuevamente antes de habilitar; asignar no habilita por sí solo.
docker compose exec backend python manage.py manage_subscription review --tenant-id UUID
docker compose exec backend python manage.py manage_subscription enable --tenant-id UUID --actor-email plataforma@example.invalid --reason "Uso revisado antes de habilitar"
```

Planes admitidos: `initial`, `growth`, `operator`, `trial`. No poner datos personales
en `--reason`. El motivo se conserva en SubscriptionEvent; la auditoría general
registra IDs/acción/plan, sin duplicar contactos ni motivos. Las versiones se crean
al asignarlas por primera vez, desde catálogo fijo; no se editan contratos previos.

Para una nueva empresa sin trial previo, `assign --plan trial` inicia los 14 días
desde esa acción UTC; `enable` activa el control de plazas. No se inicia prueba
retroactiva para empresas existentes: asignarles el plan comercial revisado.
Una empresa con uso superior a 1/1 no puede entrar en trial. Una prueba utilizada
no puede reiniciarse, tampoco tras pasar a un plan comercial. Cambiar de plan es
una acción manual auditada, efectiva inmediatamente y sin cargos/prorrateo.

`enable` rechaza empresas sin asignación o con uso superior a su capacidad. Si no
hay un plan que cubra el uso, resolver antes de habilitar; no borrar ni desactivar
recursos automáticamente. Una reducción posterior de plan mantiene recursos e
historial y bloquea únicamente altas/reactivaciones que aumenten el recurso lleno.
No existe un comando para desactivar silenciosamente límites ya habilitados.

## Garantías y límites técnicos

- Bloqueo Tenant → Property o Membership. Asignaciones, aceptaciones y altas de
  capacidad se serializan por empresa; la comprobación y escritura son atómicas.
- Se cubren creación/reactivación de cabañas, aceptación de invitaciones nuevas o
  existentes, reactivación de colaboradores y `add_membership` por consola.
- Crear una empresa/propietario nuevo no inicia trial ni habilita límites. El
  primer vínculo owner forma parte del alta actual, antes de asignación comercial.
- Se cuentan Membership.active, aunque la cuenta global esté deshabilitada: su
  acceso debe desactivarse en la empresa para liberar plaza. Inactivos conservan
  historial y no ocupan plaza; el rol owner está protegido por el flujo existente.
- Trial con inicio/fin conscientes de zona y fin exclusivo. El estado se calcula
  al consultar, sin cron ni renovación por login. Los datos se conservan al vencer.
- La consola y ORM son herramientas administrativas: las escrituras de aplicación
  deben pasar por servicios. No se expone administración genérica de estos modelos.
- Sin gateway, secretos nuevos, dependencias adicionales ni env vars comerciales.
  SMTP, verificación de correo y despliegue real conservan sus pendientes propios.

## API y archivos

`GET /api/v1/billing/plan/`: sesión owner, empresa activa; X-Tenant-Context opcional
para lectura y validado si se envía. Devuelve `subscription` y `catalog`.
Suscripción: status `unassigned/manual/trial/expired`, enforced, plan o null, usage,
trial_ends_at y over_capacity. Catálogo de tres planes, sin importes.
No hay escritura comercial desde API. Contexto cambiado o capacidad agotada: 409;
acceso no autorizado: 403; métodos de escritura owner: 405.

Archivos principales: backend/apps/billing (modelos, servicios, API, migraciones y
manage_subscription), integración en properties/services y tenants/member_services/
add_membership; frontend/features/billing/PlanPage y navegación. Pruebas en
tests/test_billing.py, Plan.test.tsx y e2e/billing.spec.ts. Los fixtures comerciales
solo se ejecutan en la base `cabanacontrol_e2e`, nunca en desarrollo principal.

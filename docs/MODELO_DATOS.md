# Modelo de datos — Fase 0

## Extensión WhatsApp 9B

Connection: UUID, tenant OneToOne PROTECT, business_id y phone_number_id únicos,
display_phone, access_token_ciphertext, enabled=false y revision. Cifrado autenticado
versionado con contexto de tenant/conexión; no existe clave de cifrado en estas tablas.

Conversation: conexión/contacto únicos, último inbound, revisión y vencimiento del
hilo. Message: dirección, texto, estado, fecha/vencimiento propios; evento e Inquiry
OneToOne opcionales. WebhookEvent: identificador externo/tipo/status únicos por
conexión, mínimos normalizados, intentos y lease recuperable, sin payload crudo.

OutboxJob: Message OneToOne, request_id único por conexión, fingerprint, plantilla
y snapshot, revisiones de conexión/conversación, actor y estado/intentos/lease.
Revisión nula en una tarea anterior bloquea envío, sin backfill que atribuya revisión.
SendUsageDaily: unique conexión+fecha local, máximo50 autorizaciones nuevas/día.
ConsentRecord: historial de permiso/finalidad/origen; actor humano o null para baja
recibida por webhook. Template: catálogo estático propio, cuenta/nombre/idioma únicos,
texto, verificación y habilitación; ningún registro supone aprobación remota de Meta.

inquiries/0002 añade canal whatsapp_api y permite created_by=null solo para origen
externo en el flujo implementado. La creación/edición humana sigue pasando actor
real por servicio; conversión a reserva mantiene su actor humano y validaciones.
Migraciones aditivas whatsapp/0001–0003, sin purga ni modificación de datos de negocio.
El historial siguiente describe las fases anteriores en su momento de entrega.

No hay modelos de negocio ni migraciones de aplicación todavía.
PostgreSQL queda preparado con un volumen persistente.
No se instala el modelo auth.User estándar de Django.

Antes de cualquier migración de identidad, la Fase 1 debe definir el usuario
personalizado y AUTH_USER_MODEL, Tenant y Membership según el plan aprobado.
Las demás entidades se incorporarán exclusivamente en sus fases autorizadas.

## Fase 1 — Modelo implementado

| Entidad | Campos principales | Restricciones |
| --- | --- | --- |
| User | UUID, email, first_name, last_name, password hash, is_active, last_login, is_platform_admin | Email único incluso con distintas mayúsculas |
| Tenant | UUID, name, legal_name, contacto opcional, timezone, currency, active, timestamps | Validación IANA y moneda de tres letras |
| Membership | UUID, user, tenant, role, active, created_at | unique(user,tenant), role owner/manager/staff |
| AuditEvent | actor, tenant opcional, entity, entity_id, action, timestamp | FK PROTECT, índice tenant+timestamp |
| AuthThrottleBucket | clave HMAC, count, expires_at | Clave única, índice de expiración, actualización con bloqueo |

Membresías protegen usuario y empresa con PROTECT. Desactivación revoca acceso en
la siguiente solicitud. No hay borrados HTTP ni cascadas de datos de negocio.
El usuario hereda grupos/permisos estándar Django, pero esos permisos globales no
sustituyen roles ni consultas filtradas por empresa.

Migraciones versionadas: accounts/0001_initial (incluye usuario), tenants/0001_initial
y audit/0001_initial, más las migraciones estándar de auth/contenttypes/sessions.
La tabla estándar auth_user no se crea porque AUTH_USER_MODEL está configurado.
RUT de empresa y modelos de las demás fases todavía no se almacenan.

## Fase 2 — Alojamientos

- Property: UUID, tenant PROTECT, name, code, description, capacity, address,
  base_rate numeric(14,2), check_in_time, check_out_time, active, created_by PROTECT
  y timestamps. Código único por tenant; capacidad positiva y tarifa no negativa
  también restringidas en PostgreSQL. Índice tenant+active+name.
- PropertyPhoto: UUID, property PROTECT, file privado, alt, order, active,
  content_type validado y created_at. Índice property+active+order. Archivo con
  nombre UUID bajo ruta de empresa/propiedad; no URL pública.
- AuditEvent suma before/after JSON con valores mínimos de capacidad, tarifa,
  horarios y estado. No se duplican textos libres/contactos ni fotos.
- Migraciones: properties/0001_initial y audit/0002_auditevent_after_auditevent_before.
  Ambas aditivas, sin eliminar tablas, filas, columnas existentes ni archivos.

Desactivación no elimina nada. Futuras reservas/pagos deberán usar relaciones
PROTECT/RESTRICT hacia Property cuando se autoricen esas fases.

## Fase 3 — Guest

UUID, tenant y created_by PROTECT; first_name/last_name (150), document_type
(rut/passport/other), document_number (40), phone (32) y email opcionales,
notes opcionales (2000), active, created_at y updated_at.

Índices tenant+active+last_name+first_name y tenant+document_type+document_number.
Restricciones PostgreSQL: tipo de documento permitido, número no vacío, formato
canónico de RUT y unicidad parcial tenant+document_number cuando tipo=rut.
Pasaporte/otro admiten duplicados según decisión explícita del propietario.

Migración aditiva guests/0001_initial. No elimina/modifica datos de otras apps.
Desactivar conserva fila/documento/notas; futuras reservas deberán referenciar
Guest con PROTECT/RESTRICT, sin borrar historial. Retención/borrado formal requieren
una política aprobada antes de implementarlos.

Auditoría de Guest: UUID, acción, actor y tenant; after conserva solo estado y nombres
de campos modificados. Sin datos personales en before/after ni representaciones de modelo.
## Fase 4 — Extensión aditiva

Reservation: UUID, tenant/property/primary_guest/created_by con PROTECT,
check_in/check_out date (salida exclusiva), adults/children, status, hold_until
timestamp consciente de zona nullable, total_amount numeric(14,2), currency,
source, notes/cancel_reason y timestamps. Índices tenant+property+fechas y
tenant+status+entrada. Restricciones de fechas ordenadas, adulto >= 1, importe
no negativo, valores de estados/orígenes y retención no nula para pending.

AvailabilityBlock: UUID, tenant/property/created_by PROTECT, start_date/end_date
exclusiva, reason, notes, active, timestamps. Índice tenant+property+active+inicio;
restricciones fechas ordenadas y motivo permitido. Se libera con active=false,
sin eliminación física. Migración reservations/0001_initial crea ambas tablas.

Las relaciones conservan huéspedes y cabañas usados en reservas/bloqueos. No hay
Payment ni ReservationGuest en esta fase; tampoco datos de acompañantes. Auditoría
guarda cambios operativos sin copiar nombres/documentos/notas/motivos.

## Fase 5 — Pagos

Payment: UUID; tenant/reservation/recorded_by/voided_by con PROTECT; request_id UUID
único por tenant; amount numeric(14,2) positivo; currency congelada desde reserva;
paid_at, method, reference, status recorded/voided; receipt_file privado opcional,
receipt_content_type; void_reason/voided_at y timestamps. Índices tenant+reservation+
status y tenant+paid_at. Restricciones de importe positivo, métodos/estados válidos
y coherencia de autor/fecha/motivo de anulación. No hay borrados ni edición de pagos.

received_amount y balance se calculan mediante suma de pagos recorded, no se guardan
como columnas ni se acumulan con floats. El saldo a favor no crea automáticamente
un reembolso. Migraciones payments/0001_initial y 0002_alter_payment_receipt_file.

## Fases 6 y 7 — Consultas operativas y reportes

apps/insights no agrega entidades ni columnas. Ocupación, ingresos y saldos se
calculan en snapshots de lectura con Decimal y unión de intervalos por cabaña.
Reportes y CSV reutilizan Reservation, Payment, Property y sus índices existentes.
Exportar agrega un AuditEvent report.export con actor/empresa/filtros/conteo,
fuera del snapshot READ ONLY. No almacena contenido del CSV ni datos personales
de huéspedes. No requiere migraciones nuevas ni elimina registros/archivos.

## Fase 8 — HousekeepingTask

operations/0001_initial crea tareas UUID con tenant/property/reservation/assigned_to/
created_by PROTECT; reservation opcional de origen y assigned_to Membership propia.
Source manual/checkout, status pending/in_progress/completed/cancelled, due_at UTC,
cuatro booleanos de checklist, notes/cancel_reason, completed_at y timestamps.
Índices tenant+status+due_at y tenant+assigned_to+status. Restricción única condicional
checkout/reservation y restricciones de source/status, checklist/completed_at y
motivo de cancelación. Reserva/tarea se crean en la misma transacción al finalizar;
no hay backfill de reservas históricas ni cambios en datos existentes.
Task abierta no retiene inventario; AvailabilityBlock conserva mantenimiento.


## Entrega 11A local — Invitaciones y accesos

Invitation: UUID, empresa PROTECT, correo normalizado, rol manager/staff,
SHA256 de token único (sin valor original), estado pending/accepted/revoked/expired,
creador, vencimiento, aceptación y revocación con actor/fecha, membresía vinculada.
Invitación pendiente única por empresa/correo; checks de rol/estado/metadatos de
aceptación. La caducidad se calcula en lecturas y se materializa al reemplazar una
pendiente vencida. Índice empresa/estado/vencimiento. Migración tenants.0002_invitation
crea tabla/índices/checks sin modificar filas existentes de User o Membership.

La cuenta es global; la membresía determina acceso por empresa. Desactivar una
membresía conserva User, pagos, reservas y otras membresías. Propietarios protegidos
frente a cambios por esta API; sin purgas ni transferencia de propiedad. Aceptación,
revocación y cambios serializados por fila Tenant, con transacciones atómicas.
Registro de auditoría almacena IDs/rol/active, sin correo, enlace, token ni contraseña.

## Suscripciones SaaS locales — 11D.1

SubscriptionPlan: código/versión únicos, nombre y límites positivos. Versiones
inmutables mediante trigger PostgreSQL, distintas de pagos de huéspedes.
TenantSubscription: OneToOne PROTECT a Tenant, plan PROTECT, enforced separado de
asignación, trial_used persistente, inicio/fin UTC conscientes de zona y restricciones
de fechas completas/ordenadas. No hay importes, cargos ni contrato de pasarela.
SubscriptionEvent: tenant/actor/plan protegidos, acción, motivo administrativo
sin datos personales y fecha. Auditoría general conserva IDs/acción/plan.

Tres migraciones aditivas en billing: tablas, protección de versiones y refuerzo
de nulabilidad de fechas. Sin asignaciones/backfill ni activación por migración.
Trials manuales 14 días, capacidad 1/1, sin reinicio tras cambio de plan. Los estados
unassigned/manual/trial/expired se calculan; no hay estado financiero «pagado»
deducido de una asignación. Detalles en PLANES_SUSCRIPCIONES.md.

## Contratación simulada — 11D.2

SimulationCompany marca explícitamente empresas ficticias por administrador.
PlanPrice vincula plan/version y precio CLP positivo, inmutable en PostgreSQL.
SimulatedContract guarda precio vigente/próximo, revisión, anclaje/periodo UTC,
cancelación diferida, finalización y actor/fecha/versión de consentimiento.
CheckoutAttempt conserva precio destino/anterior, importe calculado, cotización y
vencimiento, revisión de contrato y asignación operativa observadas, términos,
actor, clave idempotente, estado, periodo y contador de reintento de renovación.
Un único intento pending/uncertain por empresa y clave idempotente única por empresa.
SimulatedProviderEvent deduplica UUID de escenario, referencia intento y resultado
aplicado/ignorado/revisión. SaaSCharge OneToOne a intento conserva únicamente cargos
simulados positivos; cambios de importe cero no crean un cargo ficticio.

FK PROTECT e historia de intentos/cargos independiente de Payment. Migraciones
0004–0007 aditivas, sin precios/asignaciones/contratos/activación automáticos. Todas
las operaciones se cierran bajo lock Tenant antes de contrato/intento/recurso.
Periodo inicial y precio anterior se conservan en el intento para auditar subidas
después de renovaciones. Ver SIMULACION_COMERCIAL.md.

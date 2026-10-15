# API — Fase 0

`GET /health/` público, solo lectura y sin datos de empresa.

- 200: `{"status":"ok","database":"ok"}` después de ejecutar SELECT 1 en PostgreSQL.
- 503: `{"status":"unavailable","database":"unavailable"}` ante fallo de base de datos.
- 405: métodos de escritura rechazados.

Frontend consulta `/health/` mediante proxy Vite, con timeout de cinco segundos.
El servidor limita a tres segundos el intento de conexión a PostgreSQL.
En Fase 0 no había endpoints de negocio, login, admin ni schema de dominio.

## Identidad y multiempresa — Fase 1

Todas las rutas llevan barra final. Autenticación por cookie de sesión. Antes de
cualquier POST, obtener `/api/v1/auth/csrf/` y enviar csrf_token como X-CSRFToken,
con las cookies del mismo origen. El token rota al iniciar sesión; pedir uno nuevo.

| Método | Ruta | Acceso y respuesta |
| --- | --- | --- |
| GET | /api/v1/auth/csrf/ | Público; csrf_token enmascarado |
| POST | /api/v1/auth/login/ | CSRF obligatorio; email y password; usuario y contexto |
| POST | /api/v1/auth/google/ | CSRF; credencial GIS y company_name solo para alta nueva |
| POST | /api/v1/auth/logout/ | Sesión + CSRF; 204 |
| GET | /api/v1/auth/me/ | Sesión; id, email, name, is_platform_admin, active_tenant |
| POST | /api/v1/auth/password-reset/ | CSRF; email; respuesta genérica 200 |
| POST | /api/v1/auth/password-reset/confirm/ | CSRF; uid, token, password; mensaje 200 |
| GET | /api/v1/tenants/ | Empresas de membresías activas, paginadas de 25 en 25 |
| GET | /api/v1/tenants/{uuid}/ | Empresa autorizada; ajena/inactiva = 404 |
| POST | /api/v1/tenants/{uuid}/select/ | Sesión + CSRF; valida membresía y guarda contexto |
| GET | /api/v1/context/ | Empresa activa validada en backend; sin selección = 403 |
| GET | /api/v1/tenants/{uuid}/memberships/ | Solo owner de esa empresa activa; paginado |
| GET | /api/v1/schema/ | OpenAPI, solo usuario autenticado; ?format=json para JSON |

Tenant serializado: id, name, timezone, currency, role. No expone información de
contacto innecesaria. Miembros: id, user_id, name, role, active; sin correos ni claves.
Rol/contexto no se reciben del cliente. No se aceptan escrituras CRUD de empresas.

Errores:

```json
{"error":{"code":"permission_denied","details":{"detail":"Mensaje en español"}}}
```

details también puede contener campos con listas de mensajes de validación.
403: sesión ausente, permiso insuficiente o CSRF; 404: ID no autorizado; 400:
validación/token inválido; 429: límite de intentos con Retry-After. No se diferencia
correo desconocido de contraseña incorrecta. Todos los endpoints API usan no-store.

Regenerar schema y validarlo:

```powershell
docker compose exec backend python manage.py spectacular --validate --fail-on-warn --file /tmp/schema.yaml
```

Al cerrar Fase 1 no existían properties, guests, reservations, payments ni assistant.

## Cabañas y fotografías — Fase 2

Sesión y empresa activa obligatorias. owner/manager pueden escribir; staff puede
consultar. Para POST/PATCH, obtener CSRF y enviar X-CSRFToken y X-Tenant-Context
(UUID esperado de la empresa activa). Este último no concede permisos ni selecciona
empresa: su ausencia/desacuerdo devuelve 409 tenant_context_changed.

| Método | Ruta | Uso |
| --- | --- | --- |
| GET | /api/v1/properties/ | Listado por empresa, paginado |
| POST | /api/v1/properties/ | Crear alojamiento con autor/empresa resueltos en servidor |
| GET | /api/v1/properties/{uuid}/ | Ficha, incluidas cabañas inactivas |
| PATCH | /api/v1/properties/{uuid}/ | Editar o cambiar active; sin borrado |
| GET | /api/v1/properties/{uuid}/photos/ | Fotos activas; array, máximo diez |
| POST | /api/v1/properties/{uuid}/photos/ | Multipart: file, alt y order opcional |
| PATCH | /api/v1/properties/{uuid}/photos/{photo_uuid}/ | alt, order o active; ocultar/reactivar |
| GET | /api/v1/properties/{uuid}/photos/{photo_uuid}/file/ | Imagen privada de foto activa |

Crear requiere name, code, capacity, base_rate (texto decimal), check_in_time y
check_out_time. Opcionales description, address, active. Código A–Z/0–9/guion/guion
bajo, máximo 30; name 150; description 5000; address 300. Horarios HH:MM o HH:MM:SS
locales. Empresa, autor, IDs, currency y photos no se aceptan en el payload de cabaña.

```json
{"name":"Cabaña de ejemplo","code":"CAB-01","capacity":5,"base_rate":"50000.10","check_in_time":"15:00","check_out_time":"11:00"}
```

Es un ejemplo ficticio, no un valor predeterminado del negocio. Para desactivar:
PATCH con `{"active":false}`. Para reactivar: `{"active":true}`.

GET lista admite search (nombre/código), active=true/false, page y ordering por
name, code, capacity, base_rate o created_at. Sin filtro active devuelve ambos estados.
Respuesta: count, next, previous, results. Nunca acepta tenant arbitrario del cliente.

Importes serializados como strings exactos; currency proviene de Tenant. Fotos se
serializan como id, url privada, alt, order y active. Solo fotos activas aparecen
en respuestas de cabaña y listado; ocultas permanecen registradas y recuperables
por PATCH si se conoce su UUID. No se exponen rutas del filesystem ni nombre original.

Uploads: 5 MB, 4096 px por lado, diez activas; JPG/PNG/WebP estáticos reales. Archivos
corruptos/tipos no permitidos = 400. Lectura anónima = 403; ID de empresa ajena,
foto de otra cabaña, foto oculta o archivo inexistente = 404. DELETE no está permitido.
El OpenAPI generado incluye header de contexto, multipart binario y MIME de imágenes.

Al cerrar Fase 2 no existían guests, reservations, payments ni assistant.

## Huéspedes — Fase 3

Sesión y empresa activa obligatorias. GET y búsqueda permitidos a miembros activos;
owner/manager pueden escribir. POST/PATCH requieren X-CSRFToken y X-Tenant-Context.
Staff solo consulta datos básicos; nunca obtiene documento completo ni notas.

| Método | Ruta | Respuesta |
| --- | --- | --- |
| GET | /api/v1/guests/ | Listado mínimo paginado; active y document_type opcionales |
| POST | /api/v1/guests/ | Crear; 201 con ficha autorizada |
| GET | /api/v1/guests/{uuid}/ | Ficha según rol; 404 para ID ajeno |
| PATCH | /api/v1/guests/{uuid}/ | Editar o cambiar active, sin borrado |
| POST | /api/v1/guests/search/ | Búsqueda privada de solo lectura en cuerpo JSON |

Payload de escritura: first_name, last_name, document_type (rut/passport/other),
document_number y opcionales phone, email, notes, active. Identificador, tenant,
autor y timestamps son controlados por el servidor y no se aceptan en el payload.
Contactos/notas ausentes se almacenan como texto vacío; null no es válido.

Búsqueda: `{"query":"texto de búsqueda","active":true,"page":1}`. query vacío
lista huéspedes; active omitido incluye ambos estados. Nombres admiten fragmentos
y palabras combinadas; documentos deben ser completos y se normalizan antes de
comparar. No hay búsqueda por fragmentos de documento, notas, teléfono o email.
Respuesta: count, page, has_next, has_previous, results. Los resultados no incluyen
document_number, contactos ni notes; solo document_masked y datos mínimos de ficha.

Las búsquedas no deben enviarse como query string. El frontend siempre usa JSON.
Es una operación de lectura aunque utiliza POST, con CSRF y contexto también para staff.

En ficha, owner/manager reciben documento completo y notes; staff recibe ambos null,
con contacto básico y documento enmascarado. Respuestas no-store. Abrir ficha completa
deja auditoría minimizada de acceso.

RUT se valida con módulo 11 y se guarda sin puntos, con guion y DV en mayúscula.
Pasaporte/otro no requieren RUT ni se bloquean automáticamente por duplicidad.
409 duplicate_document para RUT ya registrado, incluyendo inactivos:

```json
{"error":{"code":"duplicate_document","details":{"document_number":"Este RUT ya está registrado en la empresa. Reutiliza la ficha existente.","existing_guest_id":"UUID-DE-LA-FICHA-PROPIA"}}}
```

El UUID permite abrir la ficha autorizada para reutilizarla. Nunca referencia otra
empresa. 400 para RUT/DV/entradas inválidas; 403 para rol/CSRF; 409 para contexto
desactualizado; DELETE no permitido. Desactivar con PATCH `{"active":false}`;
reactivar con `{"active":true}`, sin eliminar datos ni auditoría.

Al cerrar la Fase 3 todavía no existían reservas ni disponibilidad; se añaden en Fase 4.

## Fase 4 — Reservas y disponibilidad

Todos los miembros activos pueden operar reservas. Bloqueos: lectura para todos;
escritura solo owner/manager. Escrituras requieren CSRF y X-Tenant-Context; todos
los IDs de cabañas, huéspedes y reservas se validan contra la empresa de la sesión.

| Método | Ruta /api/v1/ | Función |
| --- | --- | --- |
| GET / POST | reservations/ | Listar / crear reserva |
| GET / PATCH | reservations/{uuid}/ | Consultar / editar campos permitidos |
| POST | reservations/{uuid}/confirm/ | Confirmar, body {} |
| POST | reservations/{uuid}/cancel/ | Cancelar con {reason} obligatorio |
| POST | reservations/{uuid}/status/ | Transición con {status, reason?, hold_until?} |
| GET | availability/ | Consultar from, to, guests?, property_id?, page? |
| GET / POST | availability-blocks/ | Listar / crear bloqueo |
| GET / PATCH | availability-blocks/{uuid}/ | Consultar / editar o liberar bloqueo |

Alta de reserva: property_id, primary_guest_id, check_in/check_out ISO date,
adults >= 1, children >= 0, total_amount como texto decimal, source
direct/phone/whatsapp/other, status draft/pending/confirmed, notes opcional.
Currency viene de empresa y no se acepta como entrada. Solo CLP por ahora.
Pending exige hold_until futuro ISO 8601 con Z u offset, por ejemplo
2026-12-01T18:00:00-03:00. Debe ser una hora elegida por el operador.

PATCH admite los mismos campos de negocio salvo status. La transición se solicita
por una acción y valida estado actual, fechas, capacidad y disponibilidad. No hay
reapertura de reservas cerradas. Cancelar/ausencia exigen motivo; el motivo no se
incluye en auditoría. No se modifica inventario basándose solo en la consulta previa.

Listado paginado count/next/previous/results; filtros property_id, status,
from_date (check_out > fecha), to_date (check_in < fecha). Ficha agrega notes y
cancel_reason. Todas incluyen guest mínimo (UUID, nombres, tipo y documento
enmascarado), nunca notas de huésped ni documento completo. hold_active es una
evaluación al tiempo de respuesta, no una promesa de disponibilidad posterior.

Disponibilidad: from y to obligatorios, to exclusiva y posterior; from desde hoy
en zona de empresa; guests opcional positivo. Respuesta paginada con property_id,
property_name, capacity, available. Una cabaña insuficiente también devuelve
available=false. Se consultan cabañas activas; un ID ajeno/inactivo devuelve 404.
Es solo lectura y no retiene fechas. Las reservas confirmadas/en estadía, pending
vigente y bloqueos activos determinan disponibilidad.

Bloqueo: property_id, start_date, end_date exclusiva, reason
maintenance/owner_use/other, notes opcional, active opcional. Filtros property_id,
active, reason. PATCH {active:false} libera conservando fila y auditoría; reactivar
vuelve a comprobar conflictos. Los bloqueos solapados se rechazan.

409 availability_conflict ante solapamiento; 400 ante reglas/datos/transiciones
inválidos; 403 rol/CSRF; 409 tenant_context_changed; 404 referencias ajenas.
DELETE no permitido. Al cierre de Fase 4, pagos y saldos quedaban pendientes de su fase.

## Fase 5 — Pagos y saldos

Todos los miembros activos, incluido staff, pueden consultar, registrar, anular y
adjuntar/descargar comprobantes dentro de su empresa. Escrituras con CSRF y
X-Tenant-Context. Referencias ajenas responden 404, roles/contextos revocados 403.

| Método | Ruta /api/v1/ | Función |
| --- | --- | --- |
| GET / POST | reservations/{uuid}/payments/ | Historial paginado / registrar abono |
| POST | payments/{uuid}/void/ | Anular con {reason} obligatorio |
| GET / POST | payments/{uuid}/receipt/ | Descargar privado / adjuntar imagen multipart file |

Alta: request_id UUID de operación, amount como texto decimal positivo de hasta
dos decimales, paid_at ISO 8601 con Z/offset y sin fecha futura, method
cash/transfer/card/other, reference opcional hasta 150 caracteres. No se acepta
tenant, currency, reservation, status ni autores del cliente. CLP de la reserva.
No hay campos de datos de tarjetas ni cargos online.

201 para nueva operación; 200 para reintento idéntico de request_id; 409
payment_conflict si cambian reserva/importe/fecha/método/referencia con la misma
clave. Cliente debe conservar clave y datos al reintentar y revisar el historial
antes de iniciar otra operación tras una conexión incierta. No hay PATCH/DELETE.

Solo pending/confirmed/checked_in/checked_out admiten abonos nuevos. Sobrepagos
permitidos; registro no cambia estado ni vencimiento. Anular excluye el pago de
la suma sin borrar fila/comprobante; mismo motivo repetido es idempotente, otro
motivo devuelve 409. Pagos anulados continúan en el historial.

Listado/ficha de reserva añaden received_amount, balance como textos decimales
y payment_state unpaid/partial/paid/credit. balance puede ser negativo. GET
reservations/?debt=true filtra estados cobrables con saldo > 0; false excluye esas
reservas. Cancelación conserva saldo aritmético/pagos y deja de aparecer como deuda.

Historial paginado count/next/previous/results; cada pago incluye UUID de reserva,
request_id, importe/moneda/fecha/método/referencia/estado, recorded_by_id,
voided_by_id/void_reason/voided_at, timestamps y receipt_url privada o null.
No incluye ruta interna de almacenamiento ni información completa del huésped.

Comprobantes: solo JPG/PNG/WebP estáticos, 5 MB y 4096 px por lado, contenido
verificado y metadatos retirados. POST separado no altera el registro del importe.
Un solo comprobante por pago, sin reemplazo; no se adjunta a pagos anulados.
GET es descarga attachment no-store/nosniff, también tras anular. PDF no admitido.
400 ante importe/fecha/archivo inválido, 409 si ya tiene archivo o está anulado.
Calendario, dashboard, reembolsos y asistente permanecen en sus fases.

## Fases 6 y 7 — Calendario, dashboard y reportes

GET `/api/v1/calendar/` y `/api/v1/dashboard/`: parámetros obligatorios `from` y
`to` ISO date, fin exclusivo, rango positivo de hasta 366 días; `property_id` UUID
opcional de la empresa activa (incluidas inactivas). Membresía requerida. Contexto
X-Tenant-Context, si se envía, debe coincidir; contexto incompatible 409, propiedad
ajena/inexistente 404, parámetros desconocidos o inválidos 400.

Calendar devuelve timezone y events (reservas de todos los estados y bloqueos
activos). Campos UUID, cabaña, start/end exclusivos, estado, blocks_inventory y
enlace interno. Sin información personal de huéspedes. Dashboard devuelve fechas,
hoy local, noches, ocupación y money por moneda; dinero en textos decimales.
Definiciones operativas: DECISIONES.md, Fase 6.

GET `/api/v1/reports/`:

- `from`, `to`, `property_id` con las mismas reglas.
- `kind`: summary (predeterminado), reservations, payments.
- `status`: solo para reservations, un estado válido de Reservation.
- `page`: entero desde 1, predeterminado 1; summary solo admite 1.

summary: campos del dashboard más cancelled_count (entrada en periodo), property_id
nullable y property_name (selección o Todas las cabañas). reservations/payments:
count, page, next/previous booleanos, results, 25 filas por página; página inexistente
404. El frontend calcula la siguiente página, no sigue URLs remotas.

reservations: entrada dentro del periodo, todos los estados salvo filtro. ID,
property_id/name/active, check_in/out, status/label, currency, total_amount,
received_amount y balance actuales como textos decimales. payments: solo recorded
por paid_at local, incluso de canceladas; IDs de pago/reserva/cabaña, nombre de
cabaña, timestamp ISO con desplazamiento local, currency/amount y method/label.
No incluyen datos personales de huéspedes ni referencias/notas de pagos.

GET `/api/v1/reports/export/`: mismos filtros salvo page, que se rechaza. Requiere
X-Tenant-Context coincidente con empresa activa. Todos los roles de empresa pueden
descargar. CSV attachment text/csv; charset=utf-8, UTF-8 BOM, ; y celdas citadas,
prefijos de fórmulas neutralizados. Exporta todas las páginas, máximo 5.000 filas;
exceso 400, sin truncamiento. Resumen una fila por moneda. Fechas/decimales ISO,
sin separadores de miles. Cache-Control no-store y X-Content-Type-Options nosniff.
Descarga auditada sin contenido del CSV ni datos personales. 403 sin membresía;
404 ante propiedad ajena; 409 ante contexto ausente o incompatible.

No hay POST/PATCH/DELETE de reportes ni archivos públicos. El esquema definitivo
se genera en docs/openapi.yaml con validate/fail-on-warn.

## Fase 8 — Operación diaria y limpieza

GET `/api/v1/operations/day/`: date ISO opcional (hoy de empresa), property_id
opcional propio, kind arrivals/departures/overdue_stays/expired_holds/maintenance/
cleaning (default arrivals), page desde 1. Retorna date/timezone/kind, counts por
categoría, count/page/next/previous booleanos y results paginados de 25 filas.
Cada fila contiene ID, nombre/estado de cabaña, fechas/estado y enlace interno;
sin información personal de huéspedes. Alertas según estado actual, sin escritura.

GET/POST `/api/v1/housekeeping/`; GET/PATCH `/api/v1/housekeeping/{uuid}/`.
Todos los miembros activos pueden operar. GET lista: status/property_id/assigned_to_id,
page, paginación DRF count/next/previous/results. Filtros ajenos se rechazan 404.
POST requiere property_id propio activo y due_at ISO con zona explícita. Opcionales:
assigned_to_id (UUID de Membership activa propia o null), notes, checklist bathroom/
kitchen/bedrooms/inventory; status inicial solo pending. PATCH admite mismos campos,
status y cancel_reason. No se puede escribir tenant/source/reservation/autor/fechas
de auditoría. Cabaña de tarea checkout no se cambia. Motivo solo para cancelled.

Respuesta incluye UUIDs, cabaña, asignación/nombre, source/status/due_at, checklist,
notes/cancel_reason y timestamps; sin PII de huéspedes. Completadas requieren cuatro
checks; cerradas no admiten edición. No DELETE. Tarea automática única por check-out.

GET `/api/v1/housekeeping/assignees/`: listado paginado de UUID de Membership y
nombre de integrantes activos de empresa, sin email/credenciales/roles de plataforma.
Cambios con CSRF y X-Tenant-Context coincidente; contexto ausente/incompatible 409,
sin CSRF 403, propiedad/tarea/responsable ajenos 404, validación/estado cerrado 400.

GET `/api/v1/reservations/{uuid}/whatsapp-draft/`: propio y autenticado, retorna
phone/message. Estado/fechas reales, sin nombres/documentos/importes/notas privadas.
No genera envío ni consulta Meta; auditado sin teléfono/texto. La apertura externa
es voluntaria desde frontend, después de revisar el borrador y el teléfono.
# Asistente y consultas — Fases 9.1–9.3

## WhatsApp — 9B.1–9B.3, activación real pendiente

API interna /api/v1/whatsapp/ con sesión, empresa, membresía y CSRF/contexto en POST/PATCH:

| Ruta | Método | Función |
| --- | --- | --- |
| capabilities/ | GET | ready/enabled/simulated, sin secretos |
| connection/ | GET/PATCH | Solo owner/manager; metadata y token de entrada write-only |
| conversations/ | GET | Paginado, archived=true/false |
| conversations/{id}/ | GET | Contacto propio, permiso/revisión/última entrada |
| conversations/{id}/messages/ | GET | Página + snapshot coherente de conversación; archivo opcional |
| consent/ | POST | conversation_id, revision, granted, source; historial conservado |
| messages/prepare/ | POST | conversation_id; respuesta genérica local, sin IA ni envío |
| messages/send/ | POST | conversation_id, revision, text, request_id, reviewed=true, template_id opcional |
| templates/ | GET/POST | Catálogo propio; escritura administrativa con reviewed=true |
| jobs/ | GET | Estados de tareas propias, sin credentials/fingerprints/leases |

Send devuelve 202 con tarea local; no prueba entrega. Retry idéntico retorna la misma
tarea, contenido distinto 409. UUID ajeno 404; revisión/contexto 409; límites 429.
Texto ≤4000; permiso vigente y ventana 24 h o plantilla estática verificada.
Revisión de conversación/conexión, actor y permiso se vuelven a comprobar en worker.
Mensajes y revisión de conversación se leen en snapshot PostgreSQL de solo lectura.
Archivo no elimina filas; views archivadas conservan lectura autorizada.

Webhook público /webhooks/whatsapp/: GET challenge/token; POST firma HMAC-SHA256
sobre bytes crudos antes de JSON, hasta 1 MB y 100 eventos por lote. La excepción
CSRF corresponde solo al webhook firmado. Enruta por cuenta/número registrados,
no por tenant/texto/cookies recibidos. Persistencia normalizada y deduplicada antes
de 200; no conserva payload completo ni contactos/nombres adicionales de Meta.
Tipos no textuales quedan fuera. No llama IA ni operaciones de reservas/pagos.
Una entrada oficial produce Inquiry.channel=whatsapp_api y created_by=null.
La API manual no puede crear una consulta fingiendo esa procedencia.

Estados de envío incierto quedan para revisión humana, sin retry automático.
Plantillas no se aprueban remotamente desde esta API: el administrador registra
verificación previa y contenido exacto. Real adapter requiere configuración y
activación separadas; los resultados locales se verificaron con mocks/E2E.

Todas las rutas requieren sesión/membresía vigente. Escrituras exigen CSRF y
X-Tenant-Context coincidente. No hay endpoints de envío de WhatsApp o confirmación IA.

| Método/ruta /api/v1/ | Función |
| --- | --- |
| GET assistant/capabilities/ | ready/enabled/voice_enabled/simulated y límites, sin claves |
| GET/PATCH assistant/settings/ | Configuración propia; PATCH owner/manager |
| POST assistant/messages/ | text ≤4000, reviewed=true, context firmado opcional |
| POST assistant/whatsapp/ | Selección humana property_id/check_in/check_out/guests; revalida sin llamar al proveedor |
| POST assistant/transcriptions/ | multipart audio ≤5 MB/60 s, reviewed=true |
| GET/POST inquiries/ | Lista paginada/registro manual explícito |
| GET/PATCH inquiries/{id}/ | Ficha/edición con revision obligatoria |
| POST inquiries/{id}/analyze/ | text revisado, reviewed=true y revision actual |
| POST inquiries/{id}/convert/ | Campos ReservationWrite + revision/reviewed, draft exclusivamente |
| GET inquiries/stats/ | Conteos por canal/estado; from/to opcionales juntos, fin exclusivo |
| GET inquiries/assignees/ | Integrantes activos propios, solo nombres/rol, paginados |

Messages devuelve results[{tool,data}] y contexto firmado ligado a actor/empresa
con caducidad 30 minutos. Cada tarjeta lleva verified_at; hechos calculados por Django.
Listado máximo 25/página con total/page/has_more. Cobros se agrupan por moneda y
paid_at local; saldos solo actuales. Fechas sin año piden aclaración; hoy/mañana/
pasado mañana y este mes/mes pasado se resuelven respecto del servidor/empresa.
Un seguimiento siempre vuelve a consultar. No incluye precios automáticos.

Inquiries usa archived=true/false y status opcional; las expiradas se excluyen de
la vista activa sin eliminación. Campos originales/revisados/respuesta hasta4000;
channel whatsapp_manual/phone/other. Cambios exigen revision; analyze invalida una
respuesta obsoleta si la consulta cambia durante la llamada. Expires_at es fijo90d.
Conversión exige huésped/cabaña propios activos y precio manual; UUID ajeno404,
conflicto/revisión409. Reintento idéntico retorna la reserva ya creada, nunca otra.
Quota429 con Retry-After; proveedor/configuración/rechazo503 con alternativa manual.
No se aceptan estado/retención ni herramientas de escritura del proveedor.


## 11A — Colaboradores e invitaciones (local)

Solo owner de la empresa activa administra equipo e invitaciones. Se conserva el
contrato mínimo del listado histórico /tenants/{id}/memberships/; el nuevo listado
/team/memberships/ incluye correo únicamente para administración autorizada.
Todas las escrituras internas exigen sesión, CSRF y X-Tenant-Context. No se permite
modificar owner, el propio acceso, credenciales globales ni membresías de otra empresa.

| Método | Ruta /api/v1/ | Comportamiento |
|---|---|---|
| GET | team/memberships/ | Equipo paginado de la empresa activa, incluidos inactivos |
| PATCH | team/memberships/{id}/ | role manager/staff, active, expected_role, expected_active |
| GET | team/invitations/ | Historial paginado sin token/hash/enlace |
| POST | team/invitations/ | email y role; 201 con invitation y link mostrado una vez |
| POST | team/invitations/{id}/revoke/ | Revoca pendiente, idempotente si ya revocada/vencida |
| POST | invitations/preview/ | Público con CSRF; token en JSON, empresa/rol/correo enmascarado |
| POST | invitations/accept/ | Público con CSRF; token y mode existing/new |

Aceptar existing exige sesión activa del correo invitado y no admite nombres/contraseña.
Aceptar new exige first_name, password y opcional last_name; valida contraseña y crea
cuenta normal/membresía en una transacción. Cuenta existente requiere login; nunca se
sobrescribe su contraseña. Vencida/revocada/reutilizada o token inválido: 400 genérico.
Campos ajenos: 400; IDs de otra empresa: 404; estado observado obsoleto/contexto: 409;
propietarios protegidos/actor no autorizado: 403; cuotas: 429 con Retry-After.

72 horas, 256 bits aleatorios, solo SHA256 en BD. URL /invitacion#token=…; frontend
retira fragmento y no usa localStorage/query cache para tokens. No crea cuenta al
consultar/abrir un enlace. 10 creaciones por propietario/hora, 50 por empresa/día y
25 pendientes vigentes; preview/accept sujetos a límite por IP. Revocación y aceptación
se serializan con lock de empresa. Revocar un acceso invalida también sus invitaciones
pendientes de reactivación; no altera el User global ni accesos a otras empresas.

## Alta inicial local (11B)

`GET /api/v1/auth/register/`: `{enabled, google_enabled, google_client_id}`. `POST` con CSRF: email,
first_name, last_name opcional (admite vacío), company_name y password. Responde
201 con detail, sin sesión automática. Crea usuario normal, empresa CLP/Santiago,
membresía owner y auditoría atómicamente. Campos adicionales/datos inválidos/correo
existente: 400; sesión ya autenticada o registro deshabilitado: 403. Cinco intentos
por IP/diez minutos: 429 con Retry-After. Solo DEBUG y LOCAL_ONBOARDING_ENABLED;
producción fuerza false. Sin verificación de correo en esta entrega local.
Véase [alcance](ALTA_PROPIETARIO_WEB.md).

Google Identity Services queda disponible cuando `GOOGLE_OAUTH_CLIENT_ID` está
configurado. `POST /api/v1/auth/google/` recibe `credential`; Django valida firma
RS256 con las claves públicas de Google, audiencia, emisor, vencimiento y correo
verificado. Una cuenta existente inicia sesión por correo. Para una cuenta nueva,
la primera respuesta solicita `company_name`; el segundo POST crea usuario sin
contraseña utilizable, empresa CLP/Santiago y membresía owner, y abre la sesión.
Los ID tokens no se persisten ni se incluyen en auditoría.

## Perfil y empresa (11C)

GET/PATCH `auth/profile/`: cuenta de sesión, nombre y apellido, correo solo lectura;
PATCH requiere expected_first_name/expected_last_name. GET/PATCH `company-settings/`:
solo propietario de empresa activa; name, legal_name, contact_email y contact_phone;
PATCH requiere expected_updated_at y X-Tenant-Context. CSRF en ambas escrituras.
Datos obsoletos/contexto cambiado: 409; campos extra/incorrectos: 400; acceso no
autorizado: 403. Moneda, zona horaria, correo de login y permisos no son editables.
[Contrato completo](PERFIL_EMPRESA.md).

## Plan y uso (11D.1 local)

Contratación simulada 11D.2: GET `billing/simulation/`, POST `quotes/`,
`attempts/{id}/accept/`, `attempts/{id}/result/` e `intents/` bajo esa raíz.
Sesión owner/contexto/CSRF, DEBUG + flag local + empresa ficticia marcada + límites
revisados. Respuesta de estado identifica habilitación, precios backend, contrato
y últimos 20 intentos. Sin aceptación no hay cargo; query string no activa planes.
Consulte [SIMULACION_COMERCIAL.md](SIMULACION_COMERCIAL.md) y OpenAPI para campos,
resultados ficticios, 409 de revisión/idempotencia y condiciones de renovación.
Esta API no es un webhook de Mercado Pago ni confirma dinero real.

GET `billing/plan/`: solo owner con empresa activa. X-Tenant-Context validado si se
envía. Devuelve subscription (status unassigned/manual/trial/expired, enforced,
plan o null, usage properties/members, trial_ends_at, over_capacity) y catalog
de tres planes por capacidad, sin importes. Sin escritura API ni acceso implícito
del administrador de plataforma. 403 por permisos, 409 por contexto distinto.

Altas/reactivaciones de propiedades y membresías pueden responder 409
plan_capacity_exceeded cuando los límites de la empresa están habilitados.
Aceptar invitación sin plaza revierte también cualquier cuenta creada durante
ese intento. Trial vencido conserva capacidad 1/1 y operación; no contrata ni cobra.
[Comandos internos y reglas](PLANES_SUSCRIPCIONES.md).

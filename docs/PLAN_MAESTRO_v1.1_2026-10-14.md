# CabañaControl — Plan maestro de implementación para Codex

Versión: 1.1 | Proyecto: SaaS de gestión de cabañas y alojamientos turísticos | Idioma de interfaz: español de Chile | Moneda predeterminada: CLP | Zona horaria predeterminada: America/Santiago

## 0. Instrucciones obligatorias para Codex

Actúa como arquitecto y desarrollador senior full-stack. Lee este documento completo antes de modificar archivos. Trabaja por fases; **no implementes una fase posterior sin aprobación explícita**. Antes de cada fase presenta: objetivo, archivos a crear/modificar, migraciones, riesgos y comandos. Después de cada fase entrega: resumen, instrucciones de ejecución, pruebas realizadas y pendientes. No afirmes que una prueba pasó si no la ejecutaste. No introduzcas datos reales de huéspedes en fixtures, commits ni logs. No ejecutes operaciones destructivas sobre datos existentes sin confirmación. Si falta una decisión funcional, plantea opciones y espera respuesta; utiliza supuestos solo cuando estén etiquetados como tales. Prioriza código mantenible, tipado, validación de entradas, accesibilidad y seguridad multiempresa. Mantén un archivo `docs/DECISIONES.md` con decisiones y supuestos y `docs/PROGRESO.md` con estado de fases.

## 1. Problema y objetivo

Propietarios de cabañas gestionan disponibilidad, nombres, RUT, fechas, abonos y saldos mediante cuadernos, WhatsApp y hojas de cálculo. Esto provoca doble reserva, confusión de pagos y pérdida de información. Construir una web responsive que centralice operaciones diarias y, posteriormente, pueda venderse a múltiples empresas independientes.

**Usuarios iniciales:** propietarios familiares y sus colaboradores. **Usuarios futuros:** pequeños operadores de 1–20 alojamientos. **MVP:** crear cabañas, registrar huéspedes, reservar sin solapamientos, recibir abonos, ver calendario y saldos. **Fuera de MVP:** channel manager Airbnb/Booking, emisión tributaria electrónica, cobro online, envío automático de WhatsApp, pricing dinámico, aplicación móvil nativa y facturación SaaS. El asistente IA de consultas se incorpora como fase posterior al motor de disponibilidad y pagos.

## 2. Stack y convenciones

- Backend: Python 3.12+, Django 5.2 LTS, Django REST Framework, django-filter, django-cors-headers solo si se requiere separación de orígenes, psycopg, pytest + pytest-django, Ruff.
- Frontend: React, TypeScript en modo estricto, Vite, React Router, TanStack Query, React Hook Form + Zod, Tailwind CSS, shadcn/ui, FullCalendar (revisar licencias de funcionalidades antes de usar), Vitest + React Testing Library, Playwright.
- Datos: PostgreSQL. Importes monetarios con `Decimal` en Python y `numeric(14,2)` en BD; nunca floats para dinero. Moneda CLP predeterminada; contemplar otras monedas a futuro sin mezclarlas en reportes.
- Infra: Docker Compose (db, backend, frontend; Redis y worker solo cuando corresponda), variables `.env` sin secretos versionados, Nginx y HTTPS en producción, backups automatizados.
- API: `/api/v1/`, JSON, fechas ISO 8601, campos y errores consistentes, paginación y filtros. API schema OpenAPI generado y documentación.
- Idioma: es-CL; zona horaria de cada propiedad, por defecto America/Santiago. Fechas de estancia `date` (sin zona horaria), timestamps de auditoría en UTC.

## 3. Arquitectura multiempresa

**Modelo inicial:** base de datos compartida con `tenant_id` en entidades de negocio. Cada usuario puede pertenecer a una o varias empresas mediante `Membership`, con rol por empresa. Todas las consultas de entidades de negocio deben filtrarse por tenant resuelto en backend, nunca confiar en un `tenant_id` arbitrario del cliente. Implementar permisos de objeto y comprobaciones explícitas en servicios y endpoints. El superadmin de plataforma es un rol separado, con acceso auditado. No confiar exclusivamente en filtros del frontend.

Roles: `platform_admin` (gestión de plataforma); `owner` (todo dentro de su empresa); `manager` (operación, tarifas, reportes); `staff` (reservas y limpieza según permisos). El usuario selecciona empresa activa cuando pertenece a varias. Resolverla mediante una ruta/contexto autenticado y validar membresía en cada solicitud. Probar intentos de acceso cruzado con IDs conocidos, consultas, exports y archivos.

**Autenticación:** para frontend y API del mismo origen usar sesiones Django y cookies HttpOnly, Secure en producción, SameSite adecuado y protección CSRF; evitar almacenar tokens sensibles en localStorage. Implementar login, logout, recuperación de contraseña y protección anti fuerza bruta. En desarrollo configurar proxy Vite o reverse proxy para mismo origen. Definir flujo CSRF probado con formularios y API.

## 4. Modelo de datos inicial (propuesta revisable)

- `User`: modelo personalizado desde primera migración, email único, nombre, estado, último acceso.
- `Tenant`: nombre comercial, razón social opcional, RUT empresa opcional, contacto, zona horaria, moneda, estado.
- `Membership`: user, tenant, role, active, unique(user, tenant).
- `Property`: tenant, nombre, código único por tenant, descripción, capacidad máxima, dirección opcional, tarifa base, hora check-in/out, active.
- `PropertyPhoto`: property, archivo, orden, alt.
- `Guest`: tenant, nombres, apellidos, tipo_documento (RUT/pasaporte/otro), numero_documento normalizado, teléfono, email opcional, notas restringidas, timestamps. Índice y política de unicidad tenant+tipo+documento cuando corresponda. Evitar exigir RUT a extranjeros.
- `Reservation`: tenant, property, primary_guest, check_in (date), check_out (date, exclusiva), adults, children, status (`draft`, `pending`, `confirmed`, `checked_in`, `checked_out`, `cancelled`, `no_show`), total_amount Decimal, currency, source (`direct`, `phone`, `whatsapp`, `other`), notes, created_by, timestamps, cancel_reason. `check_out > check_in`.
- `ReservationGuest`: reservation, guest (opcional para acompañantes), nombre/documento cuando sea estrictamente necesario y permitido; no almacenar información adicional innecesaria.
- `Payment`: tenant, reservation, amount Decimal >0, paid_at, method (`cash`, `transfer`, `card`, `other`), reference, status (`recorded`, `voided`), receipt_file opcional, recorded_by, void_reason, timestamps. No borrar pagos históricos; anular con trazabilidad. El monto recibido se calcula con pagos válidos.
- `AvailabilityBlock`: tenant, property, start_date, end_date exclusiva, reason (`maintenance`, `owner_use`, `other`), notes, created_by.
- `HousekeepingTask` (fase posterior): tenant, property, reservation opcional, assigned_to opcional, status, due_at, completed_at.
- `AuditEvent`: tenant opcional, actor, entity, entity_id, action, before/after minimizados y sin secretos, timestamp, ip limitada cuando sea necesaria.
- `SubscriptionPlan`/`TenantSubscription` (fase SaaS): límites de propiedades/usuarios, estado, periodo, proveedor de pagos; no activar cobro hasta validación comercial.

Definir índices compuestos por tenant, property, fechas y estados. Las migraciones deben ser reversibles cuando sea razonable. No utilizar `CASCADE` para eliminar accidentalmente reservas/pagos: preferir desactivación de propiedades y políticas `PROTECT`/`RESTRICT`.

## 5. Reglas críticas de negocio

1. Las estancias son intervalos **[check_in, check_out)**: salida el mismo día que otra entrada está permitida.
2. No se pueden confirmar reservas superpuestas de una misma propiedad. Estados que bloquean inventario: `pending` solo si tiene retención vigente (configurable), `confirmed`, `checked_in`; establecer política exacta en fase de reservas. `draft`, `cancelled`, `no_show`, `checked_out` no bloquean por sí solos, pero una reserva finalizada conserva historial. Validar coherencia de transiciones.
3. Bloqueos de mantenimiento/uso propietario también impiden nuevas reservas confirmadas.
4. Prevenir condiciones de carrera: ejecutar creación/confirmación en transacción, bloqueo de propiedad y comprobación de solapamiento; preferir restricción PostgreSQL `EXCLUDE USING gist` con `daterange` y condición por estado cuando el diseño esté estabilizado. Incluir test concurrente.
5. `total_amount` es precio pactado congelado en la reserva; cambios requieren auditoría. `balance = total_amount - SUM(valid_payments)`; definir política para sobrepagos, reembolsos y cancelaciones antes de implementarlos. No usar float.
6. No registrar pagos negativos como reembolsos; modelar reembolsos como transacciones diferenciadas en una fase posterior.
7. El RUT chileno debe normalizarse y validarse con módulo 11 en backend, con pruebas para K, 0, puntos y guion. Pasaporte/otro documento sigue su propia validación.
8. No revelar datos de huéspedes entre tenants ni en URLs públicas. El portal de huéspedes (futuro) usa tokens aleatorios de alta entropía, caducidad y acceso limitado.
9. Definir capacidad máxima de ocupación y verificar adultos+niños, con excepción administrativa auditada solo si se acuerda.
10. No almacenar datos de tarjetas; usar proveedor de pagos externo cuando se integre.

## 6. Pantallas y experiencia de usuario

**MVP responsive:** login; selector de empresa; dashboard (ocupadas hoy, disponibles hoy, check-ins/check-outs, cobros pendientes); lista y formulario de cabañas; lista y ficha de huéspedes; calendario mensual/semanal por cabaña con colores por estado; crear/editar/ver reserva; registrar abono; historial de pagos; listado filtrable y export CSV; perfil/configuración básica.

**UX clave:** crear reserva en pocos pasos: seleccionar cabaña y rango de fechas → validar disponibilidad → huésped existente o nuevo → precio total → guardar. Mostrar estado de cobro independientemente del estado de reserva. Confirmaciones antes de cancelación/anulación. Diseño móvil primero, estados de carga, mensajes de error claros, navegación con teclado, contraste y etiquetas accesibles.

## 7. API propuesta

- `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/me` (ajustar a flujo de sesión/CSRF).
- `GET /api/v1/tenants`, `GET /api/v1/tenants/{id}` para tenants autorizados.
- `GET/POST /api/v1/properties`, `GET/PATCH /api/v1/properties/{id}`.
- `GET/POST /api/v1/guests`, `GET/PATCH /api/v1/guests/{id}`.
- `GET/POST /api/v1/reservations`, `GET/PATCH /api/v1/reservations/{id}`, `POST /api/v1/reservations/{id}/confirm`, `POST /api/v1/reservations/{id}/cancel`.
- `GET /api/v1/availability?property_id=&from=&to=`.
- `GET/POST /api/v1/reservations/{id}/payments`, `POST /api/v1/payments/{id}/void`.
- `GET /api/v1/calendar?from=&to=&property_id=`.
- `GET /api/v1/dashboard?from=&to=`.

Todos los endpoints: autorización por tenant, validación servidor, filtros, paginación cuando corresponda, serialización segura, OpenAPI, respuestas de error predecibles. Evitar exponer RUT completo en listados que no lo necesiten.

## 8. Fases de implementación y criterios de aceptación

### Fase 0 — Descubrimiento y preparación
- Confirmar cantidad de cabañas, reglas de arriendo (por noche/día), política de anticipos, anulaciones, tarifas variables, horarios y fuentes de reserva.
- Crear repositorio, README, `.env.example`, Docker Compose, backend Django, frontend React/Vite, PostgreSQL, linters y estructura `docs/`.
- Healthchecks, comandos de arranque y test mínimo. **Aceptación:** `docker compose up --build` inicia servicios; frontend carga y API responde `/health/`.

### Fase 1 — Identidad y multiempresa
- Custom User, Tenant, Membership, login/logout, recuperación, selección de empresa, roles, middleware/contexto y permisos.
- Tests de acceso entre empresas y CSRF. **Aceptación:** usuarios de dos tenants no pueden consultar datos ajenos, incluso alterando IDs en la API.

### Fase 2 — Cabañas
- CRUD de propiedades, capacidad, tarifa base, horarios, estado, imágenes con límites de tamaño/tipo, búsqueda y desactivación.
- **Aceptación:** propietario gestiona solo sus cabañas y desactivar no borra historial.

### Fase 3 — Huéspedes
- CRUD, RUT módulo 11, tipos alternativos de documento, búsqueda, reutilización de huéspedes, manejo de duplicados, privacidad.
- **Aceptación:** RUT inválido rechazado, extranjero permitido con documento alternativo, datos aislados por tenant.

### Fase 4 — Reservas y motor de disponibilidad
- Crear/editar/cancelar, estados, intervalos exclusivos, reglas de capacidad, bloqueos y servicio transaccional anti-solapamiento.
- **Aceptación:** reserva solapada rechazada; salida y entrada mismo día permitidas; pruebas de concurrencia y bloqueos aprobadas.

### Fase 5 — Pagos y abonos
- Registrar múltiples abonos, métodos, comprobantes, saldos, anulación auditada, filtros de deuda.
- **Aceptación:** sumas exactas con Decimal, anulación recalcula saldo, no se borran pagos, permisos correctos.

### Fase 6 — Calendario y dashboard
- FullCalendar por propiedad, filtros y navegación; indicadores de ocupación, ingresos cobrados, ingresos pactados y saldos, con definiciones distintas.
- **Aceptación:** calendario coincide con API y bloqueos; cifras concilian con reservas/pagos; responsive.

### Fase 7 — Reportes y exportación
- Reportes por periodo/cabaña, ocupación, cobros, reservas canceladas, export CSV seguro contra formula injection; PDF opcional.
- **Aceptación:** cifras correctas con datos de prueba y export restringido al tenant.

### Fase 8 — Operación diaria
- Limpieza, mantenimiento, check-in/out, checklist simple, alertas internas; enlaces de WhatsApp generados por el usuario, sin envío automático.
- **Aceptación:** mantenimiento bloquea fechas y los cambios quedan auditados.

### Fase 9 — Asistente IA de consultas (solo lectura)
- Crear un chat integrado al panel, usable en móvil, con historial corto por sesión y contexto de empresa activa resuelto exclusivamente en backend.
- Casos de uso: "¿Hay una cabaña para 5 personas del 15 al 20 de enero?", "¿Quién llega mañana?", "¿Qué reservas tienen saldo pendiente?", "¿Cuánto cobramos este mes?", "¿Y el fin de semana siguiente?" y "Prepara un mensaje de WhatsApp con las opciones".
- Usar un proveedor de LLM configurable mediante variables de entorno, con API de herramientas/function calling y salida estructurada validada (por ejemplo Pydantic). Nunca permitir que el modelo genere o ejecute SQL, ni que decida el tenant o permisos.
- Herramientas de backend de **solo lectura** y argumentos tipados: `search_available_properties(check_in, check_out, guests)`, `list_arrivals(date)`, `list_outstanding_balances(as_of_date)`, `summarize_collections(start_date, end_date)` y `prepare_whatsapp_message(property_id, check_in, check_out, guests)`.
- Todas las herramientas llaman a servicios de dominio ya existentes; aplican tenant y permisos en servidor; verifican capacidad, bloqueos, estados y fechas con check-out exclusivo. Los importes provienen del motor de tarifas y pagos, jamás de cálculos inventados por el LLM.
- Si faltan datos (año, fechas ambiguas, cantidad de huéspedes), pedir aclaración. Resolver "mañana", "este mes" y fechas relativas según la zona horaria del alojamiento/empresa, nunca según la zona del servidor. Confirmar qué año corresponde cuando no sea inequívoco.
- Responder con datos reales y referencias internas navegables a las reservas/cabañas autorizadas. Si no existe disponibilidad, decirlo claramente. Si el proveedor falla, ofrecer búsqueda tradicional; nunca presentar resultados ficticios como reales.
- Generar borradores de mensajes de WhatsApp para revisión y copia manual. No enviar mensajes ni crear, modificar, bloquear o cancelar reservas automáticamente. Revalidar disponibilidad y tarifas antes de confirmar una reserva fuera del chat.
- Privacidad: minimizar datos personales enviados al proveedor; no incluir RUT ni datos de contacto completos salvo necesidad justificada; no incluir claves ni comprobantes; documentar consentimiento/información sobre terceros y retención; limitar registros del chat y evitar PII en logs.
- Seguridad/costos: rate limiting por usuario y tenant, límite de tokens y presupuesto configurable, timeouts, manejo de errores, defensa frente a prompt injection, auditoría de herramientas invocadas sin registrar información sensible. Clave API solo en backend.
- Endpoints sugeridos: `POST /api/v1/assistant/messages/` y `GET /api/v1/assistant/capabilities/`; permitir desactivar IA por empresa. No almacenar conversación permanente en la primera versión salvo necesidad validada.
- **Aceptación:** pruebas con dos tenants verifican que no se filtran reservas ajenas; fechas y ocupación coinciden con el motor de disponibilidad; saldos coinciden con pagos válidos; preguntas ambiguas solicitan precisión; el modelo no puede ejecutar escrituras ni SQL; falla de proveedor no rompe el panel; tests con proveedor simulado y sin API key real.

### Fase 10 — Portal de huésped y notificaciones
- Enlace privado y temporal a reserva, consulta limitada de estado/saldo, emails transaccionales con consentimiento y plantillas.
- **Aceptación:** token vencido/revocado no da acceso; no hay exposición de información de otros huéspedes.

### Fase 11 — SaaS comercial
- Planes, límites, trial, onboarding de tenants, suscripciones y pasarela según mercado elegido. Superadmin con auditoría. No asumir integración fiscal ni cobro sin revisar proveedor y requisitos.
- **Aceptación:** límites se aplican en backend, suscripciones no afectan aislamiento, webhooks idempotentes y verificados.

### Fase 12 — Hardening y producción
- Seguridad, rate limiting, políticas de archivos, logs estructurados sin PII, monitoreo, backups cifrados, restauración probada, HTTPS, variables de entorno, migraciones, despliegue documentado.
- **Aceptación:** pipeline CI pasa, pruebas E2E críticas, backup/restauración ensayados, checklist de producción completo.

## 9. Pruebas obligatorias

Asistente IA: pruebas de herramientas con proveedor simulado, aislamiento multiempresa, manejo de fechas ambiguas, respuestas sin datos inventados y bloqueo de operaciones de escritura. Backend: unitarias de RUT, intervalos, saldos y transiciones; integración API y permisos; aislamiento entre tenants; carrera concurrente; archivos y acceso. Frontend: formularios, errores, calendario y estados. E2E: login → crear cabaña → crear huésped → reservar → abonar → consultar saldo → ver calendario → cancelar. Verificar zona horaria y cambios de horario de verano sin alterar fechas de estadía. Crear fixtures ficticios únicamente.

## 10. Seguridad, privacidad y cumplimiento

Aplicar principio de mínimo privilegio, minimización de datos personales, cifrado en tránsito, control de acceso a archivos, políticas de retención y eliminación, respaldos, consentimiento/comunicaciones conforme a normativa aplicable en Chile y revisión legal antes de lanzar comercialmente. RUT y teléfonos son datos personales: limitar exposición y registrar acceso administrativo sensible cuando proceda. Nunca subir `.env`, credenciales ni comprobantes reales a repositorios públicos. Para pagos externos, verificar webhooks criptográficamente y manejar idempotencia.

## 11. Estructura sugerida

```text
cabanacontrol/
  backend/
    config/
    apps/
      accounts/
      tenants/
      properties/
      guests/
      reservations/
      payments/
      reporting/
      audit/
    tests/
    pyproject.toml
  frontend/
    src/
      app/
      components/
      features/
        auth/
        properties/
        guests/
        reservations/
        payments/
        calendar/
        dashboard/
      lib/
    package.json
  infra/
    nginx/
  docs/
    DECISIONES.md
    PROGRESO.md
    API.md
    MODELO_DATOS.md
  compose.yaml
  .env.example
  README.md
```

## 12. Reglas de calidad y entrega

- Backend: separar vistas/serializers de servicios de dominio y consultas; transacciones donde corresponda. Tipado progresivo y Ruff.
- Frontend: componentes reutilizables, TypeScript estricto, hooks para datos, evitar lógica monetaria crítica solo en cliente.
- Migraciones versionadas; seed de demostración sin PII; CI con tests y linters.
- No crear complejidad prematura: Redis, Celery, automatizaciones autónomas, cobros online y channel manager solo cuando exista una necesidad validada. El asistente IA de solo lectura sí está planificado en la Fase 9.
- Mantener documentación de decisiones, endpoints, variables, despliegue y procedimientos de respaldo.

## 13. Preguntas de descubrimiento para el propietario

1. ¿Cuántas cabañas hay y cuál es su capacidad?
2. ¿Se arriendan por noche, día, semana o temporada?
3. ¿Se cobra tarifa fija o cambia según fechas y cantidad de huéspedes?
4. ¿Qué porcentaje o monto de abono confirma la reserva?
5. ¿Cuánto tiempo se bloquea una fecha sin abono?
6. ¿Qué ocurre ante cancelaciones, cambios de fecha y devoluciones?
7. ¿Quién registra reservas y pagos?
8. ¿Cómo llegan las reservas (teléfono, WhatsApp, Booking, Airbnb, presencial)?
9. ¿Qué reportes necesitan hoy?
10. ¿Requieren uso desde celular, con internet intermitente o por varios administradores simultáneamente?

## 14. Primer prompt para Codex

> Lee íntegramente `PLAN_FULL_CODEX_CABANACONTROL.md`. No programes todavía. Primero inspecciona el repositorio y prepara un resumen de arquitectura, decisiones pendientes y plan de Fase 0. Pregúntame las decisiones de negocio imprescindibles. Una vez respondidas y aprobada la Fase 0, implementa solamente esa fase con Docker Compose, Django, React + TypeScript, PostgreSQL, configuración segura y healthchecks. Ejecuta pruebas y documenta los resultados. No avances a Fase 1 sin mi autorización.

## 15. Prompts de continuación

**Implementar fase:** `Revisa PLAN_FULL_CODEX_CABANACONTROL.md, docs/DECISIONES.md y docs/PROGRESO.md. Propón la implementación detallada de la Fase N con archivos, migraciones, endpoints, pruebas y riesgos. Espera mi aprobación antes de modificar código.`

**Revisar fase:** `Audita la Fase N contra sus criterios de aceptación. Ejecuta tests y linters disponibles, detecta fallos de seguridad multiempresa, de concurrencia y de datos personales. Corrige lo que esté dentro del alcance aprobado y documenta resultados sin inventarlos.`

**Cerrar fase:** `Actualiza docs/PROGRESO.md con tareas terminadas, pendientes, comandos probados, decisiones tomadas y siguiente fase sugerida. No implementes la siguiente fase.`

## 16. Definición de terminado del MVP

Un propietario inicia sesión, registra varias cabañas y huéspedes, crea reservas sin duplicaciones ni solapamientos, registra abonos, ve saldo real, calendario y dashboard desde celular; los datos de otra empresa son inaccesibles; los flujos principales tienen pruebas; la aplicación se levanta con Docker y existe un procedimiento documentado de backup/restauración. **El MVP operativo inicial no requiere planes SaaS ni IA; el asistente de consultas se entrega como una fase adicional explícita antes de la comercialización.**

## 17. Prompt específico para implementar el asistente IA

> Lee el plan maestro, `docs/DECISIONES.md` y `docs/PROGRESO.md`. Propón la implementación de la Fase 9 (Asistente IA) sin modificar código todavía. Diseña herramientas de solo lectura reutilizando los servicios reales de disponibilidad, tarifas, reservas y pagos; define esquemas de entrada/salida, controles de tenant, permisos, pruebas, privacidad, límites de costos y manejo de fallos. Incluye ejemplos de consultas en español de Chile y borradores de WhatsApp. No uses SQL generado por IA ni permitas escrituras. Espera mi aprobación antes de implementar.

## 18. Decisión aprobada: WhatsApp opción C (13-10-2026)

**Estrategia:** primero asistencia manual para mensajes y llamadas; después automatización mediante WhatsApp Business Platform / Cloud API oficial, condicionada a requisitos, consentimiento, costes y validación con usuarios. No conectar clientes mediante scraping, WhatsApp Web no oficial ni automatización de cuentas personales.

### Fase 9A — Atención asistida (antes de automatizar)

- Bandeja de consultas internas: `inquiries` con `tenant_id`, canal (`whatsapp_manual`, `phone`, `other`), texto original, fechas, estado, usuario responsable, `guest_id` opcional y trazabilidad. No almacenar más datos personales de los necesarios.
- Formulario para pegar un mensaje de WhatsApp y acción para dictar una nota tras una llamada (transcripción voluntaria; solicitar permiso de micrófono, no grabar llamadas de terceros).
- Extracción estructurada de intención, fechas con año, cantidad de huéspedes, preferencias y datos faltantes. Ante ambigüedad, solicitar aclaración y no asumir el año ni el horario.
- La disponibilidad y tarifa se calculan exclusivamente en servicios Django existentes con aislamiento de tenant, zonas horarias, reglas de solapamiento, bloqueos, capacidad y tarifas vigentes; la IA no escribe SQL ni inventa valores.
- Respuesta en español de Chile, editable, con alternativas verificadas y vigencia de la cotización. Botones Copiar y Abrir WhatsApp mediante enlace `wa.me` cuando se dispone de teléfono válido; el envío es humano.
- Conversión de consulta a borrador de reserva con revisión y confirmación explícita. Revalidar disponibilidad en transacción antes de guardar; la respuesta no constituye una reserva.
- Consulta por voz: transcripción y formulario precargado con revisión humana, mostrando campos inciertos.
- Historial y estados: nueva, respondida, esperando cliente, convertida, descartada; filtros y estadísticas básicas.
- Límites por tenant, logs sin texto sensible, retención configurable, control de permisos, protección contra instrucciones maliciosas incluidas en mensajes externos.

**Criterios de aceptación 9A:** pegar consulta para 5 personas entre fechas concretas devuelve solo opciones verificadas; si no hay cupos ofrece alternativas reales o informa indisponibilidad; el texto se puede editar/copiar; una llamada dictada produce borrador sin crear reserva; se bloquea acceso entre empresas; errores de IA no rompen la consulta manual; tests de extracción, permisos, disponibilidad y concurrencia.

### Fase 9B — Integración oficial de WhatsApp (posterior al MVP)

- Estudiar elegibilidad de cuenta, número, plantillas, ventanas de conversación, políticas de Meta, consentimiento, opt-out y precios vigentes antes de implementar.
- Configuración por empresa de credenciales en secretos cifrados y webhook verificado; nunca exponer tokens al frontend.
- Procesamiento asíncrono e idempotente de webhooks, deduplicación por identificador de mensaje, cola de reintentos y trazabilidad.
- Bandeja omnicanal y traspaso a humano; horario de atención y opción de desactivar respuestas automáticas.
- Respuesta automática solo para consultas autorizadas de disponibilidad/precios con información verificada. Si hay ambigüedad, errores o baja confianza, solicitar datos o derivar a humano.
- Ninguna reserva, cancelación, devolución ni modificación de pago sin confirmación humana y controles de autorización.
- Métricas de tiempo de respuesta, consultas convertidas, coste por conversación y satisfacción.

**Criterios de aceptación 9B:** webhook autenticado, mensajes duplicados sin efectos repetidos, aislamiento entre tenants, límites de envío, derivación humana, respeto a políticas y privacidad, tests de fallos de proveedor y auditoría.

### Orden de entrega actualizado

Primero completar cabañas, huéspedes, motor de disponibilidad, reservas y pagos. Luego implementar **9A** para validar el flujo real de los padres y captar primeras ventas. Incorporar **9B** solo después de comprobar demanda y costes; no bloquear el lanzamiento por esta integración.

### Prompt para Codex — módulo de WhatsApp

> Lee `PLAN_FULL_CODEX_CABANACONTROL.md`, especialmente la sección 18. Prepara un diseño técnico de Fase 9A con modelos, migraciones, endpoints DRF, servicios de extracción IA, UI React, pruebas, privacidad y criterios de aceptación. No programes hasta que apruebe la propuesta. Mantén la Fase 9B como diseño futuro basado únicamente en la API oficial de WhatsApp Business; no implementes automatización todavía.

# CabañaControl — Plan maestro de implementación

Versión: 1.2 consolidada | Actualización: 14-10-2026 | SaaS multiempresa para alojamientos turísticos | Español de Chile | CLP | America/Santiago

Este documento define el alcance y las reglas vigentes. La versión anterior se conserva en [docs/PLAN_MAESTRO_v1.1_2026-10-14.md](docs/PLAN_MAESTRO_v1.1_2026-10-14.md). La consolidación no cambia código, datos, migraciones ni autorizaciones de implementación.

## 0. Reglas de trabajo y autorizaciones

Actúa como arquitecto y desarrollador Full Stack experto en Python, Django REST Framework, React, TypeScript, PostgreSQL y Docker. Lee el plan y el estado vigente antes de modificar código.

- Trabaja exclusivamente dentro de la fase o propuesta autorizada. No avances a otra fase por iniciativa propia.
- Antes de implementar una fase nueva presenta objetivo, alcance, archivos, migraciones, decisiones pendientes, riesgos y verificaciones. Una propuesta aprobada autoriza todo su alcance; no vuelvas a pedir la misma aprobación al reanudarla.
- Interpreta «sigue», «go» o «sigamos» según el contexto: reanudar el trabajo activo, aprobar una propuesta concreta presentada o continuar con la siguiente tarea propuesta. Ante ambigüedad material, explicita la interpretación; una reanudación no amplía por sí sola el alcance a otra fase.
- Si falta una regla funcional que afecta al comportamiento, presenta opciones y espera la decisión. Resuelve detalles técnicos rutinarios dentro del alcance autorizado y documenta los supuestos.
- Verifica en etapas pequeñas. Al cerrar entrega cambios, comandos, pruebas realmente ejecutadas, problemas y siguientes pasos. No atribuyas a una fase pruebas de otra ni declares aprobaciones que no existen.
- No elimines archivos ni datos existentes sin autorización. Cambios de política de borrado o retención física requieren aprobación específica. Los temporales nuevos solo se descartan cuando su tratamiento efímero forme parte del flujo aprobado.
- No uses datos reales de huéspedes en fixtures, tests, capturas, commits ni logs. No publiques secretos, .env ni comprobantes reales.
- Mantén código tipado, accesible, mantenible, validado en servidor y aislado por empresa. Conserva decisiones en docs/DECISIONES.md y resultados/estado en docs/PROGRESO.md.

### Documentos y precedencia

Las instrucciones expresas del propietario prevalecen. Este plan consolida las reglas de producto; docs/DECISIONES.md conserva decisiones y su contexto histórico; docs/PROGRESO.md informa qué se completó y verificó; docs/API.md, docs/MODELO_DATOS.md y OpenAPI describen contratos implementados. Una propuesta pendiente no equivale a código existente ni a una aprobación.

Cuando una decisión posterior aprobada todavía no esté consolidada aquí, respétala y registra la discrepancia. Las notas históricas de fases anteriores no sustituyen el estado actual.

## 1. Producto y etapas de entrega

Propietarios y colaboradores gestionan cabañas, huéspedes, fechas, pagos y disponibilidad desde una interfaz responsive. El objetivo inicial es resolver la operación cotidiana; la arquitectura multiempresa permite ofrecer después el producto a operadores independientes de 1–20 alojamientos.

- **MVP operativo:** cabañas, huéspedes, reservas sin solapamientos, abonos, calendario, saldos y dashboard. Corresponde al núcleo de Fases 0–6.
- **Piloto:** agrega reportes y operación diaria de Fases 7–8 y exige superar la puerta de producción P antes de usar datos reales en un entorno desplegado. IA no es requisito del MVP ni del piloto operativo; se valida como ampliación de Fase 9.
- **SaaS comercial:** añade onboarding, gestión de miembros, límites, suscripciones y cobro de Fase 11 después de validar demanda y preparar producción. Tener aislamiento multiempresa no implica que la facturación SaaS ya esté implementada.

Fuera del núcleo: channel manager Airbnb/Booking, emisión tributaria electrónica, pricing dinámico, cobro online, aplicación móvil nativa y envíos automáticos de WhatsApp. Solo se incorporan mediante alcance aprobado. PDF es opcional; no bloquea reportes CSV.

## 2. Stack y convenciones

- Backend: Python 3.12+, Django 5.2 LTS, Django REST Framework, psycopg, django-filter; pytest/pytest-django y Ruff. Usuario personalizado desde la primera migración de identidad.
- Frontend: React, TypeScript estricto, Vite, React Router, TanStack Query, React Hook Form/Zod, Tailwind CSS, shadcn/ui y FullCalendar Standard. Vitest/React Testing Library y Playwright.
- Base de datos: PostgreSQL. Importes Decimal en Python y numeric(14,2) para importes persistidos. API con textos decimales; nunca floats para cálculos monetarios de negocio.
- Infraestructura: Docker Compose para db/backend/frontend, secretos por entorno, dependencias fijadas. Redis/workers solo si una necesidad aprobada los justifica. Servidores de desarrollo no se usan como despliegue de producción.
- API REST bajo /api/v1/, JSON, fechas ISO, barras finales, errores consistentes, paginación/filtros, validaciones servidor y OpenAPI. Los contratos implementados se consultan en docs/API.md y docs/openapi.yaml.
- Español de Chile, CLP para operación actual. Los reportes agrupan por moneda y no hacen conversiones; otras monedas de escritura requieren alcance aprobado.
- **Zona horaria por empresa**, heredada por sus cabañas; por defecto America/Santiago. Estadías como date, sin conversión de zona; timestamps conscientes de zona y almacenados en UTC. Operar propiedades de una empresa en zonas distintas requiere diseño y aprobación adicional.
- FullCalendar Standard con licencia revisada. Plugins Premium de recursos no están incluidos; su incorporación requiere justificar funcionalidad/licencia.

## 3. Multiempresa, autenticación y permisos

Base compartida con tenant_id en entidades de negocio. Cada usuario puede tener varias Membership. El backend resuelve la empresa activa desde una sesión autenticada y comprueba membresía, estado y referencias propias. No confía en un tenant_id del cliente ni solo en filtros de frontend.

Sesiones Django, cookies HttpOnly, CSRF, mismo origen mediante proxy en desarrollo; Secure/HTTPS en producción. No almacenar tokens sensibles en localStorage. Login/logout, recuperación y protección de intentos forman parte de identidad. X-Tenant-Context protege operaciones contra cambios de empresa entre pantallas; comprobar contratos de cada endpoint.

Roles owner/manager/staff por empresa. platform_admin es independiente y no obtiene acceso implícito a empresas ajenas; cualquier acceso autorizado debe ser auditado.

| Operación | Propietario/administrador | Colaborador |
| --- | --- | --- |
| Cabañas y fotos | Gestionar | Consultar |
| Huéspedes | Gestionar | Consultar datos básicos; sin notas restringidas ni documento completo |
| Reservas y estados permitidos | Gestionar | Gestionar |
| Pagos | Consultar, registrar, anular con motivo | Igual |
| Calendario, dashboard, reportes y CSV | Consultar/exportar | Igual |
| Bloqueos de disponibilidad/mantenimiento | Gestionar | Consultar |
| Tareas de limpieza | Gestionar todas | Igual |
| Consultas asistidas y conversión humana a draft | Acceso completo propuesto para Fase 9 | Confirmado, conservando permisos de huéspedes |
| Activar/configurar IA por empresa | Propuesto para owner/manager en diseño pendiente | Sin administración propuesta |

Las filas futuras de IA no indican que la funcionalidad esté implementada. Las altas de usuarios/empresas y membresías actualmente se provisionan mediante CLI; la interfaz de invitaciones/roles se detalla en Fase 11, sin atribuirla retroactivamente a Fase 1. Las políticas del propietario se preservan durante esa ampliación.

## 4. Entidades y separación de responsabilidades

Entidades existentes, descritas en docs/MODELO_DATOS.md:

- User personalizado; Tenant; Membership única por usuario/empresa.
- Property y PropertyPhoto: capacidad, tarifa base informativa, horarios, estado e imágenes privadas con límites.
- Guest: tipo/documento normalizado, contactos y notas restringidas. RUT válido y único por empresa; pasaporte/otro sin bloqueo automático por duplicados.
- Reservation: empresa, cabaña, huésped principal, entrada/salida exclusiva, adultos/niños, status, hold_until, precio/moneda, origen, notas, autor y auditoría.
- Payment: reserva, importe positivo, moneda, paid_at, método, referencia, status recorded/voided, autor, request_id idempotente, comprobante privado opcional y datos de anulación.
- AvailabilityBlock: cabaña, fechas exclusivas, reason, notes y active.
- HousekeepingTask: cabaña, reserva de origen opcional, responsable Membership opcional, vencimiento, checklist, source, status, completed_at y trazabilidad.
- AuditEvent: actor/empresa/entidad/acción y cambios minimizados, sin secretos ni duplicación de contenido privado.

ReservationGuest y datos personales de acompañantes no forman parte del núcleo implementado. Solo se incorporan con necesidad y alcance aprobados. SubscriptionPlan/TenantSubscription pertenecen a Fase 11. Inquiry/configuración/cuotas IA están propuestos, no implementados; ver propuesta de Fase 9.

Índices por empresa, estado, propiedad y fechas; relaciones históricas PROTECT/RESTRICT y desactivación en lugar de borrado. Consultas, validadores, servicios transaccionales, serializers y vistas separados. No usar ORM/SQL directo como una vía alternativa para escribir inventario de producción.

## 5. Reglas de negocio vigentes

### Estadías y disponibilidad

1. Se arrienda por noches, con intervalos [check_in, check_out). Salida y entrada el mismo día están permitidas.
2. Capacidad máxima estricta, sin excepciones aprobadas; al menos un adulto, niños no negativos. Creaciones y nuevas confirmaciones/retenciones con entrada desde hoy local.
3. pending exige hold_until futuro al crear/renovar y retiene solo mientras hold_until > now. Vencer libera inventario sin borrar fila ni cambiar automáticamente su estado. Confirmar una pendiente vencida revalida disponibilidad y no tiene prioridad sobre otro bloqueo o reserva.
4. confirmed y checked_in bloquean sus intervalos; draft/cancelled/no_show/checked_out no. Bloqueos activos también impiden disponibilidad. Borradores normales pueden coincidir sin retener fechas.
5. Escrituras de reservas y bloqueos usan transaction.atomic, locks y comprobación común por cabaña, con orden estable al cambiar propiedad. Una exclusión PostgreSQL entre reservas, si se incorpora, no sustituye el control de cruce con bloqueos y expiración de pendientes; requiere diseño específico.
6. Alta en draft/pending/confirmed. Transiciones: draft → pending/confirmed/cancelled; pending → draft/confirmed/cancelled; confirmed → checked_in/no_show/cancelled; checked_in → checked_out. Estados cerrados no se editan/reabren. Cancelación/ausencia exigen motivo.
7. Check-in dentro de las fechas reservadas; check-out desde la fecha de salida; ausencia desde entrada. Durante una estadía iniciada no se cambian cabaña/fechas/ocupación con el flujo actual. Salida atrasada genera alerta: la política de prolongaciones y su efecto en disponibilidad está pendiente y no se inventará al implementar IA.

### Precio, pagos y saldos

8. Precio pactado manual en CLP, conservado salvo cambio explícito auditado. Tarifa base no equivale a un motor de cotización; no se supone base_rate × noches, temporadas, descuentos o precio confirmado para IA.
9. Pagos positivos en pending/confirmed/checked_in/checked_out. No se registran nuevos en draft/cancelled/no_show. Abonar no confirma ni renueva retenciones.
10. Recibido = suma de recorded; saldo = precio - recibido. Sobrepagos y reducción de precio por debajo de lo recibido están permitidos; saldo negativo se muestra a favor. Deuda y crédito no se compensan entre reservas.
11. Anular exige motivo, conserva pago/comprobante/historial y recalcula saldo. No equivale a un reembolso. No borrar pagos ni registrar importes negativos como devolución.
12. Cancelar conserva precio/pagos y excluye de deuda; no genera devolución. Reembolsos, conciliación bancaria, cargos online y facturación tributaria necesitan fases propias aprobadas. No guardar datos de tarjetas.

### Indicadores y privacidad

13. Pactado del periodo: entradas de confirmed/checked_in/checked_out. Cobrado: pagos recorded recibidos dentro del periodo local, incluso de canceladas. Fin exclusivo.
14. Deuda/crédito del periodo: reservas con entrada en el periodo; deuda solo en estados cobrables con saldo positivo; crédito conservado también en canceladas/ausencias. Son saldos actuales, no balances históricos al cierre.
15. Ocupación: noches de confirmadas/en estadía/finalizadas sobre noches de cabañas actualmente activas. Recortar/unir intervalos por cabaña. Retenciones/bloqueos aparte, sin descontar bloqueos del denominador. Historial de inactivas permanece visible.
16. RUT con módulo 11 y normalización; único por empresa. Extranjeros con documento alternativo sin bloqueo automático de duplicados. No exponer documentos completos, contactos o notas privadas innecesariamente.
17. Limpieza automática única al check-out, dentro de la misma transacción, sin backfill de reservas antiguas. Vence a las 23:59:59 del día efectivo local. Completar exige baño/cocina/dormitorios/inventario revisados; cancelar exige motivo. Alertas de tareas abiertas vencidas o del día no bloquean reservas.
18. Preparar WhatsApp no envía mensajes: texto/destinatario revisables, apertura humana de wa.me y envío humano. No incluir RUT, saldos o notas privadas por defecto; no modificar el teléfono del huésped desde el borrador.

## 6. Experiencia de uso

Responsive y usable con teclado: login, selección de empresa, dashboard, cabañas, huéspedes, reservas/disponibilidad, pagos, calendario mensual/semanal, reportes CSV, operación diaria y limpieza. Estados de carga/error/vacío, etiquetas, contraste, importes separados por estado de pago y confirmaciones de cancelación/anulación.

Crear reserva: cabaña/fechas → disponibilidad → huésped permitido → adultos/niños → precio manual → revisión → guardar. El backend revalida; la consulta previa no retiene fechas.

Configuración/perfil/invitaciones pendientes se identifican en su fase correspondiente; una pantalla mencionada en la visión no se considera entregada sin criterio y verificación. Borradores de IA/voz muestran incertidumbres y requieren revisión humana.

## 7. Contratos API

Contratos implementados en docs/API.md y docs/openapi.yaml: auth, tenants, properties, guests, reservations/availability/blocks, payments, calendar/dashboard, reports/export y operations/housekeeping/whatsapp-draft.

Mantener aislamiento por empresa, permisos de objeto, validación servidor, paginación cuando corresponde y manejo uniforme de errores. CSV con escape y neutralización de fórmulas, descarga autenticada y sin PII innecesaria; archivos privados sin URL pública.

Endpoints assistant/inquiries se detallan en la propuesta pendiente. No son contratos ya desplegados. Fechas de reportes no implican soporte de balances históricos.

## 8. Fases y criterios de aceptación

Fases 0–8 completadas según docs/PROGRESO.md. Se conserva su numeración e historial; no se rehacen ni se redefinen como trabajo pendiente. Fases 9.1–9.3, P y ampliaciones posteriores requieren el alcance/aprobación correspondiente.

### Fase 0 — Descubrimiento y entorno

Docker Compose, Django/React/TypeScript/PostgreSQL, .env.example, README, estructura, linters y healthchecks. Aceptación: servicios arrancan, frontend carga, /health/ comprueba BD. Identidad usa su usuario personalizado antes de las primeras migraciones de auth; no se rehace la base existente.

### Fase 1 — Identidad y multiempresa

Usuario/Tenant/Membership, sesiones, recuperación, empresa activa, roles, CSRF e intentos. Aceptación: aislamiento aun alterando IDs y pruebas de autenticación/contexto. Provisionamiento actual por CLI; interfaz de gestión de miembros en Fase 11.

### Fase 2 — Cabañas

Gestionar cabañas/fotos, capacidad, tarifa base, horarios, búsqueda/desactivación. Aceptación: objetos/archivos propios, límites de imagen e historial intacto.

### Fase 3 — Huéspedes

Gestión, documentos, RUT, búsqueda/reutilización y privacidad. Aceptación: validación, unicidad RUT por empresa, extranjero permitido y permisos vigentes de staff.

### Fase 4 — Reservas y disponibilidad

Estados, edición/cancelación, retenciones, capacidad, intervalos y bloques transaccionales. Aceptación: solapamiento rechazado, recambio permitido, concurrencia/capacidad/contexto probados.

### Fase 5 — Pagos

Abonos, comprobantes, sumas Decimal, sobrepagos, anulaciones y deuda. Aceptación: importes exactos, historial conservado, idempotencia/locks/permisos/archivos privados probados.

### Fase 6 — Calendario y dashboard

FullCalendar Standard, filtros/navegación e indicadores definidos en sección 5. Aceptación: calendario coincide con inventario y cifras concilian con datos propios; responsive.

### Fase 7 — Reportes y CSV

Periodo/cabaña, ocupación/cobros/canceladas y CSV protegido, sin PDF obligatorio. Aceptación: cifras, filtros, export completo dentro de límites e aislamiento comprobados.

### Fase 8 — Operación diaria

Panel, limpieza/checklist, mantenimiento, check-in/out y contacto manual. Aceptación: mantenimiento bloquea fechas, cambios auditados, limpieza/check-out atómicos y sin duplicados, roles correctos y sin envío automático.

### Fase 9.1 — Asistente de consultas de lectura

Chat móvil/escritorio y herramientas tipadas: disponibilidad/capacidad, entradas, saldos actuales, cobros por periodo y respuestas manuales. Contexto resuelto en servidor, fechas relativas locales, aclaración de año/datos faltantes. OpenAI configurable, permisos/cuotas, fallos con alternativa manual y sin resultados ficticios.

El modelo interpreta; Django determina disponibilidad/importes y referencias autorizadas. Nunca SQL generado, tenant elegido por modelo, comandos, precios inventados o herramientas de escritura. No existe balance histórico; una consulta a una fecha pasada debe informar la limitación. Historial breve de chat, sin persistir conversación completa por defecto.

Aceptación: datos reales del motor, dinero exacto, dos empresas, prompt injection, ambigüedades, proveedor simulado y fallos/cuotas sin afectar operación normal.

### Fase 9.2 — Bandeja y borradores humanos (antes Fase 9A, texto)

Inquiry propia con whatsapp_manual/phone/other, original/revisión/extracción/respuesta, responsable, estado y trazabilidad mínimos. Pegar mensaje, analizar y revisar, preparar respuesta editable, copiar/abrir WhatsApp manual y estadísticas básicas.

Estados: nueva/respondida/esperando cliente/convertida/descartada. Conservación operativa confirmada de 90 días con aviso/archivo; no purga automática. Archivo no equivale a eliminación física: esa política sigue pendiente.

Conversión exclusivamente por una acción humana separada del modelo. Validar revisión, huésped propio activo, adultos/niños, precio manual y cabaña; revalidar disponibilidad en transacción y crear draft sin retener inventario. Staff puede convertir, pero no adquiere permiso para registrar huéspedes nuevos; owner/manager usa el flujo existente cuando haga falta.

Aceptación: propuestas revisables, incertidumbres claras, bloqueo de IDs ajenos, doble conversión idempotente, carrera con otra reserva resuelta y cero confirmaciones/envíos autónomos.

### Fase 9.3 — Dictado voluntario (antes Fase 9A, voz)

Operador dicta una nota, con permiso de micrófono e inicio/parada visibles; transcripción editable y formulario precargado. No grabar llamadas ni conversaciones de terceros. Audio temporal, tamaño/duración/tipo limitados y revisión antes de compartir con proveedor; alternativa de escribir/pegar texto.

Usa el flujo de 9.2; transcribir no crea huésped ni reserva. Aceptación: audio inválido rechazado, error recuperable, revisión humana, privacidad, pruebas simuladas y responsive.

### Puerta P — Preparación de producción antes de piloto con datos reales

No se aplaza toda la seguridad hasta el final. Antes de exponer el producto desplegado con datos reales, verificar:

- Despliegue de producción, HTTPS/cookies/secretos y configuración segura.
- Aislamiento/permisos/CSRF, intentos, archivos privados y logs sin PII.
- Backups protegidos y restauración ensayada; plan de migración/recuperación.
- Monitoreo básico, errores/cuotas, correos operativos o alternativa de recuperación validada.
- Responsables de altas/roles y políticas de privacidad/retención, incluida información sobre terceros si IA se habilita.
- Reglas operativas pendientes relevantes, como prolongaciones de estadía, resueltas o limitación explícitamente aceptada para el piloto.

Aceptación: checklist con evidencia y aprobación del despliegue. La existencia de Docker de desarrollo y tests no acredita esta puerta. No se marca cumplida en esta consolidación.

### Fase 9B — Integración oficial de WhatsApp, futura y opcional

Después de validar demanda, alcance y costes: WhatsApp Business Platform/Cloud API oficial, cuenta/número/plantillas/ventanas y consentimiento; secretos protegidos por empresa, webhook verificado, deduplicación/colas/reintentos y traspaso humano. Sin scraping, WhatsApp Web no oficial ni automatización de cuentas personales.

Automatización limitada a consultas aprobadas con datos verificados; nunca confirmar/cancelar/cobrar por instrucciones del texto recibido. Aceptación: verificación de webhooks, aislamiento, idempotencia, límites, baja confianza/fallos y control humano. No bloquea MVP ni piloto y necesita propuesta/aprobación independiente.

### Fase 10 — Portal de huésped y notificaciones, ampliación opcional

Tokens privados aleatorios, caducidad/revocación y consulta limitada; comunicaciones con consentimiento. Aceptación: token inválido/ajeno no expone datos y notificaciones respetan alcance/permisos.

### Fase 11 — SaaS comercial y gestión de cuenta

Onboarding, gestión autorizada de miembros/invitaciones/roles y perfil/configuración pendientes; planes, límites, trial, suscripciones y pasarela elegida. Superadmin con accesos auditados. No asumir integración fiscal ni cobro sin propuesta específica.

Depende de puerta P y validación comercial; aceptación: límites backend, roles/invitaciones sin acceso cruzado, revocaciones, webhooks/idempotencia y estado de suscripción sin vulnerar aislamiento. Puede dividirse en gestión de cuenta y monetización, cada alcance verificable.

### Fase 12 — Hardening continuo y escala

Fortalecer observabilidad, restauración/continuidad, rendimiento, retención, tareas asíncronas justificadas y despliegue repetible. Amplía los controles mínimos ya exigidos por P; no es la primera ocasión de preparar producción. Aceptación: evidencias, carga/recuperación y procedimientos actualizados.

Orden vigente: núcleo 0–8 cerrado → diseño/aprobación de 9.1–9.3 → implementación autorizada en etapas. P antes de piloto con datos reales; IA es opcional para dicho piloto. 9B/10/11 se priorizan por demanda aprobada; 12 acompaña producción/escala. No hay autorización implícita por esta lista.

## 9. Verificación obligatoria

Backend: RUT, intervalos, dinero, transiciones, CSRF/contexto, permisos/IDs cruzados, concurrencia, auditoría y archivos. Frontend: formularios, errores, fechas/zonas, estados y accesibilidad. E2E: login → cabaña → huésped → reserva → abono → saldo/calendario → cancelación, además de reportes/operación.

IA: proveedor simulado, dos empresas, contexto cambiado, prompt injection, argumentos extra, fechas ambiguas, importes verificados, falta de proveedor y bloqueo de herramientas de escritura. Conversión humana concurrente e idempotente; voz con revisión y fallos. No usar claves reales o datos de huéspedes en tests ni afirmar llamadas facturables de prueba sin autorización.

Pruebas con PostgreSQL para comportamiento dependiente de BD, migraciones aplicadas, schema OpenAPI validado y checks relevantes. No repetir suites sin motivo; ampliar cuando un cambio/fallo justifique hacerlo.

## 10. Privacidad y operación segura

Minimizar PII y exposición, acceso privado a archivos, separación por empresa, secretos protegidos y auditabilidad sin replicar datos sensibles. Definir retención física/eliminación y copias de seguridad antes de producción, con revisión legal cuando corresponda; no asumir que archivo lógico cumple un plazo de borrado.

Para IA informar de proveedor, límites de retención y revisión del material enviado. No prometer que una configuración de almacenamiento elimina todos los registros del tercero. Presupuestos/cuotas y modelos configurables; detalles concretos en propuesta aprobada, no en respuestas inventadas del modelo.

## 11. Organización del repositorio

Conservar módulos existentes: backend/apps/accounts, tenants, properties, guests, reservations, payments, insights, operations y audit; frontend/features/auth, properties, guests, reservations, payments, calendar, dashboard, reports y operations.

assistant e inquiries son módulos previstos. No reorganizar migraciones o mover archivos solo para ajustarse a una estructura sugerida. Configuración en config/, tests backend/frontend, Compose/.env.example y documentos de contratos/decisiones/progreso.

## 12. Calidad y mantenimiento

Separar consultas, servicios de dominio, validadores, serializers y vistas. TypeScript estricto, componentes reutilizables, cálculos críticos en servidor, migraciones aditivas cuando sea posible y dependencias fijadas. Documentar cambios, comandos, pruebas y límites; CI y despliegue con configuración de producción validada.

Sin complejidad prematura: workers, Redis, channel manager, pricing dinámico o infraestructura adicional solo por necesidad y alcance aprobados. No eliminar fixtures/volúmenes o desactivar protecciones para hacer pasar pruebas.

## 13. Decisiones todavía abiertas

- Cantidad real de alojamientos/usuarios y volumen esperado de operación.
- Política de prolongaciones/salidas atrasadas y efecto en inventario con estadía iniciada.
- Retención física, borrado/anonimización y tratamiento de backups; 90 días de archivo operativo no resuelve esto.
- Prioridad comercial de portal, notificaciones, integración oficial y suscripciones.
- Reglas de tarifas/cotizaciones automáticas, reembolsos y otras monedas, si se solicitan.
- Modelo/cuotas/presupuesto reales de OpenAI y validación de puerta P antes de habilitar IA con datos reales.

No presentar como pendientes las reglas ya aprobadas de noches, capacidad, retenciones, pagos, permisos, ocupación o conservación operativa. Nuevas reglas no se deducen de ejemplos del modelo.

## 14. Inicio de un proyecto nuevo

Este apartado sirve solo como referencia histórica/metodológica. Para un proyecto nuevo: revisar especificación, distinguir decisiones imprescindibles, presentar Fase 0 y ejecutar el alcance autorizado. En CabañaControl no reiniciar Fase 0 ni recrear identidad/BD al leer este apartado.

## 15. Continuación, revisión y cierre

Una sola regla de aprobación es la de sección 0. Para una fase nueva: presentar propuesta concreta y esperar autorización. Para trabajo aprobado: reanudar sin pedir la misma confirmación. Para revisión: contrastar aceptación, ejecutar checks relevantes, corregir dentro del alcance. Para cierre: actualizar PROGRESO con evidencia y siguiente fase sugerida, sin iniciarla automáticamente.

## 16. Definición de terminado

MVP operativo: propietario registra cabañas/huéspedes, reserva sin conflictos, recibe abonos y consulta saldo/calendario/dashboard desde móvil, con datos ajenos inaccesibles y flujos probados. Piloto real: además supera P, cuenta con procedimientos de respaldo/restauración y limitaciones operativas aceptadas. SaaS comercial: incorpora gestión de cuenta/límites/cobro del alcance aprobado de 11.

IA, WhatsApp oficial, portal y facturación SaaS no son requisitos del MVP operativo. Las ampliaciones se aceptan por sus propios criterios, sin retrasar innecesariamente un piloto seguro del núcleo.

## 17. Propuesta vigente de IA y compatibilidad de nombres

[docs/PROPUESTA_FASE_9_9A.md](docs/PROPUESTA_FASE_9_9A.md) detalla el diseño pendiente. Su nombre se conserva para no romper referencias históricas. La antigua Fase 9 corresponde a 9.1; 9A texto/borradores corresponde a 9.2; 9A voz a 9.3. Las tareas de infraestructura/chat internas de esa propuesta pertenecen a 9.1, sin duplicar fases.

Confirmados proveedor OpenAI con clave solo backend, staff con gestión/conversión humana y 90 días operativos con aviso/archivo. La aprobación de esas decisiones y de esta consolidación no aprueba automáticamente la implementación de la propuesta. Falta autorizar su alcance concreto; no se ha implementado IA ni se autoriza 9B.

## 18. Historial de la consolidación

Versión 1.1 preservada íntegramente como copia documental. Versión 1.2 reúne decisiones de fases completadas, centraliza aprobaciones, unifica 9/9A, distingue MVP/piloto/comercial y coloca preparación de producción antes de datos reales. Corrige las presuposiciones de motor de tarifas, balance histórico y zona por propiedad.

No introduce cambios funcionales en código ni nuevas excepciones de capacidad, permisos o pagos. Los pendientes de sección 13 y propuestas futuras requieren decisión/aprobación antes de implementarlos.

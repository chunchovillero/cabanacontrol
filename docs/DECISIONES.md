# Decisiones técnicas y asuntos pendientes

Fecha: 13-10-2026. Especificación: PLAN_FULL_CODEX_CABANACONTROL.md, leída íntegramente.

## Alcance autorizado

La solicitud actual autoriza implementar solamente la Fase 0 y prevalece sobre el
prompt de ejemplo de la sección 14 que indica esperar aprobación antes de programar.
El repositorio inicialmente contenía únicamente el plan; no se modificó ni eliminó.

Actualización: el mensaje «sigue» autoriza avanzar a Fase 1. Se presentó el alcance
antes de implementar. La Fase 2 permanece pendiente de autorización.

Segunda actualización: el siguiente «sigue» autoriza Fase 2. Se presentó alcance,
archivos, migraciones, riesgos y verificaciones antes de implementar. Fase 3 pendiente.

Tercera actualización: el siguiente «sigue» autoriza Fase 3. Se presentaron alcance,
archivos, migración y verificaciones. El propietario respondió expresamente las
decisiones de permisos y duplicados indicadas más abajo. Al cerrar Fase 3,
la Fase 4 aún no estaba autorizada; se autorizó posteriormente.

## Arquitectura

Cuarta actualización: el nuevo «sigue» autoriza la Fase 4, reservas y motor de
disponibilidad. Se presentó alcance, archivos, migración aditiva, riesgos y
verificaciones. Antes de implementar políticas se solicitaron tres decisiones:
retención de pendientes, permisos de staff y capacidad/fechas retroactivas.
La autorización de esta fase no incluye pagos, calendario ni dashboard.

Diseño técnico de Fase 4: todas las escrituras de reservas y bloqueos adquirirán
el mismo bloqueo de fila de Property dentro de transaction.atomic. Cambios de
cabaña bloquearán las propiedades en orden estable para evitar interbloqueos.
La comprobación incluirá reservas bloqueantes y bloqueos activos con intervalos
[entrada, salida). No se considera suficiente una comprobación de frontend.
Una exclusión PostgreSQL parcial entre reservas no cubre conflictos con otra
tabla ni vencimientos temporales; no sustituirá el bloqueo común del servicio.
Los estados y sus permisos finales quedan pendientes de las respuestas anteriores.

- Monorepo: backend Django 5.2 LTS / DRF, frontend React / TypeScript estricto / Vite,
  PostgreSQL 17 y Docker Compose. Python 3.12 y Node 22.
- Supuesto técnico de desarrollo: puertos 8000 y 5173, publicados solo en loopback.
  PostgreSQL no publica puerto; usa un volumen persistente.
- Proxy Vite para `/health/` y `/api/`: navegador y API comparten origen. Sin CORS.
  Sesiones y CSRF autenticados se implementarán y probarán en Fase 1.
- `/health/` realiza SELECT 1; falla con 503 sin revelar excepciones ni credenciales.
- Idioma es-cl, zona America/Santiago, USE_TZ para timestamps conscientes de zona.
  Moneda CLP informativa por ahora; ningún cálculo monetario en Fase 0.
- Tailwind 4 mediante plugin Vite y base shadcn/ui (aliases, tokens, Button y Radix).
- Dockerfiles de desarrollo con usuarios sin privilegios. Runserver/Vite son
  servidores de desarrollo; producción pertenece a Fase 12.
- Dependencias frontend resueltas en package-lock.json; backend fijado con hashes
  en requirements-dev.lock. Docker instala esos locks.

## Contradicciones y decisiones diferidas

1. Custom User desde la primera migración versus identidad en Fase 1: no instalar
   auth/admin/contenttypes/sessions ni ejecutar migrate en Fase 0. Así no se crea
   auth_user. Fase 1 debe definir AUTH_USER_MODEL y accounts/0001_initial antes de
   migrar. No hay migraciones de dominio en esta fase.
   Referencia: https://docs.djangoproject.com/en/5.2/topics/auth/customizing/
2. Fase 9 solo lectura versus 9A con consultas persistentes y conversión a borrador:
   mantener herramientas LLM de consulta sin escrituras; futura acción humana
   autorizada guardará el borrador. Diseño concreto pendiente de aprobación 9A.
3. La sección 18 pide 9A tras disponibilidad y pagos, pero no precisa si antes o
   después de 6–8. Confirmar el orden cuando esas fases estén listas.
4. Retenciones pending: falta plazo y expiración. Una EXCLUDE con predicado temporal
   no resuelve por sí sola expiración dinámica ni conflictos entre tablas de reservas
   y bloqueos. Diseñar mecanismo común y bloqueo transaccional en Fase 4.
5. checked_out deja de bloquear: decidir tratamiento de reservas retroactivas para
   preservar coherencia histórica y reportes.
6. API propuesta usa rutas sin barra final; acordar convención en Fase 1. Solo
   `/health/` está implementado. OpenAPI y endpoints de negocio aún no existen.
7. Revisar licencia de calendario por recursos antes de Fase 6, no instalar ahora.

## Descubrimiento pendiente de respuesta

Cantidad/capacidades; noches versus días; tarifas y temporadas; anticipos; plazo sin
abono; cancelaciones, cambios, sobrepagos y reembolsos; horarios; operadores y roles;
canales; reportes prioritarios; uso móvil e internet intermitente. Se solicitó esta
información sin asumir reglas ni implementar funciones dependientes.

Referencia Tailwind: https://tailwindcss.com/docs/installation/using-vite

## Fase 1 — Decisiones aplicadas

- UUID para usuarios, empresas y membresías. Correo como identificador de login,
  normalizado a minúsculas; restricción única adicional sobre Lower(email) en BD.
- AUTH_USER_MODEL=accounts.User desde accounts/0001_initial. Se comprobó que la
  base de desarrollo no tenía tablas antes de migrar. No se creó auth_user.
- Sesiones Django de 12 horas, cookies HttpOnly y SameSite=Lax; cookies Secure
  fuera de DEBUG. No usar localStorage para credenciales o contexto de seguridad.
- La API usa barra final. El endpoint CSRF retorna un token enmascarado; el cliente
  pide uno fresco antes de cada POST. Login y ambos endpoints anónimos de
  recuperación llevan csrf_protect explícito: DRF SessionAuthentication solo
  aplica CSRF al usuario autenticado.
- Empresa activa: UUID en sesión, revalidado con usuario activo, empresa activa y
  Membership activa en cada solicitud. Rutas tenant/{uuid} también se filtran por
  membresías autorizadas. IDs, parámetros y headers del cliente no otorgan acceso.
- Rol siempre viene de Membership y se reconsulta; owner puede leer miembros de
  su empresa activa, manager/staff no. Empresas/membresías se provisionan por CLI.
  No hay endpoint público de registro, edición de roles ni altas comerciales.
- is_platform_admin es independiente de la membresía: tampoco is_superuser otorga
  acceso tenant implícito. Accesos de plataforma a contexto/listados/detalles se
  auditan sin texto sensible. Funciones comerciales del superadmin siguen en Fase 11.
- Auditoría mínima de identidad: actor/tenant, entidad, UUID, acción y timestamp.
  No incluye IP, correos, contraseñas, tokens ni datos personales en payloads.
- Límite compartido en PostgreSQL con bloqueos transaccionales: cinco solicitudes
  por cuenta y treinta por IP en diez minutos, separados por operación de login y
  recuperación. Se cuentan intentos exitosos también; un éxito no reinicia límites.
  Identificadores almacenados como HMAC con SECRET_KEY, sin correo/IP en claro.
  Respuesta 429 con Retry-After. No confiar en X-Forwarded-For arbitrario.
- En desarrollo, Vite es el peer de red del backend; el límite IP se comparte entre
  clientes del proxy. En producción será necesario configurar proxies de confianza
  y retención/limpieza de buckets en Fase 12, antes de exposición pública.
- Recuperación: tokens Django con vencimiento de una hora y un solo uso. Cambio de
  contraseña invalida sesiones anteriores mediante el hash de autenticación.
  Token en fragmento de URL, retirado al abrir formulario; nunca en query ni logs.
  Respuesta genérica también para usuario inexistente, desactivado o fallo SMTP.
  El padding de hash no garantiza latencias idénticas de entrega SMTP.
- Desarrollo usa backend de email a archivos temporales privados, configurable
  por SMTP; no se realizaron envíos reales. SMTP real queda pendiente de configurar.
- RUT empresa es opcional en la propuesta: se difiere su almacenamiento hasta
  incorporar la validación chilena reutilizable en Fase 3; no aceptar RUT sin validar.
- Frontend usa React Router, TanStack Query, React Hook Form y Zod. Limpia datos de
  otras empresas al cambiar contexto y datos de sesión al salir, conservando el
  observador de sesión para que la UI se actualice correctamente.
- Endpoints protegidos con respuestas no-store y errores JSON consistentes.
  OpenAPI generado con drf-spectacular, visible solamente tras autenticación.
- Pruebas E2E en un proyecto Compose separado: cabanacontrol-e2e, BD
  cabanacontrol_e2e, puertos 18001/15174, red/volúmenes propios. Seed se niega a
  correr sin flag explícito y nombre de BD de prueba. No se borran volúmenes.
- El backend aplica migraciones al iniciar únicamente en este entorno de desarrollo.

Referencias oficiales:
https://www.django-rest-framework.org/api-guide/authentication/
https://docs.djangoproject.com/en/5.2/ref/models/constraints/
https://docs.djangoproject.com/en/5.2/topics/auth/default/

## Fase 2 — Cabañas

- Property y PropertyPhoto con UUID, FK PROTECT, índice tenant+active+name y código
  único por tenant. Código normalizado a mayúsculas, reservado incluso al desactivar.
  No hay borrado HTTP ni cascadas de cabañas/fotos.
- owner/manager gestionan alojamientos y fotografías; staff solo consulta. Cada
  queryset parte de la empresa activa del servidor, y servicios de escritura
  revalidan membresía. Se rechazan tenant/id/autor/moneda enviados por el cliente.
- X-Tenant-Context es una precondición de escritura, no una fuente de identidad:
  debe coincidir con el UUID resuelto en sesión o se devuelve 409. Lecturas del
  cliente React también lo envían; archivos usan su ruta privada y sesión. Previene
  guardar bajo otra empresa cuando una pestaña cambia el contexto compartido.
- Capacidad entera positiva y hasta 32767 (límite técnico del campo smallint).
  Tarifa base no negativa con Decimal/numeric(14,2), dos decimales; JSON con float
  rechazado. Frontend conserva dinero como string y usa BigInt para presentación.
  La tarifa no define unidad de arriendo, temporada, anticipos ni precio final.
- Nombre/código/capacidad/tarifa/horarios se ingresan explícitamente; no hay
  valores funcionales inventados. Horarios locales heredan la zona de la empresa.
  Si los alojamientos de una empresa usan distintas zonas, acordar una anulación
  por propiedad antes de implementar el motor de fechas/ocupación en Fase 4.
- Descripción y dirección opcionales con límites técnicos 5000/300 caracteres.
- Auditoría de cambios agrega before/after únicamente para capacidad, tarifa,
  horarios y estado; no duplica descripción, dirección, nombres ni contenido de fotos.
  Desactivar conserva fila, fotos y auditoría. Reservas/pagos aún no existen, por lo
  que sus relaciones/historial se probarán en sus fases correspondientes.
- Límite técnico de fotos: diez activas, 5 MB y 4096 px por lado. Se admiten JPG,
  PNG y WebP estáticos; Pillow usa solo esos decodificadores, verifica, carga y
  reencodea píxeles limpios, corrigiendo orientación y retirando EXIF/GPS/ICC/texto.
  El tipo declarado por el cliente y el nombre original no deciden el formato.
- Handler acota la lectura de archivos antes de completar la carga. Se bloquean
  SVG/GIF, contenido corrupto, animaciones y dimensiones excesivas. Nombres UUID
  generados por servidor; almacenamiento privado fuera del repo con permisos 600/700.
- Fotos servidas por FileResponse autenticado y filtrado, con no-store/nosniff.
  Ocultar cambia active=False, impide lectura del archivo y conserva bytes y fila.
  Edición/orden y reactivación son posibles por API; no hay DELETE físico.
- Conteo de fotos y edición de cabaña con transacción/bloqueo de propiedad. Carrera
  de código resuelta por UniqueConstraint y error de validación, no 500.
- Escrituras de archivo y BD no son una transacción distribuida: un fallo extremo
  de commit después de escribir podría dejar un archivo huérfano privado. No se
  borra automáticamente; auditoría/conciliación y política de retención serán parte
  del hardening. El flujo normal no reemplaza ni elimina archivos existentes.
- Volumen Compose private_media persistente, separado por proyecto en E2E. Seed
  ficticio por dispositivo para no compartir límites de autenticación entre pruebas.
- Consultas paginadas, búsqueda nombre/código, filtro active y orden controlado.
  Fotos incluidas/listadas solo si activas, también en la respuesta de PATCH.

Referencias oficiales para archivos e imágenes:
https://docs.djangoproject.com/en/5.2/ref/files/storage/
https://pillow.readthedocs.io/en/stable/handbook/security.html

## Fase 3 — Huéspedes y RUT

Decisiones del propietario:

- Staff: «Solo consultar datos básicos». owner/manager registran, editan y gestionan
  fichas; staff no puede crear, editar, desactivar ni leer notas/documentos completos.
  Contacto básico en ficha: teléfono/email; listados no incluyen esos contactos.
- «RUT único; documentos extranjeros sin bloqueo automático». La unicidad de RUT
  es por empresa e incluye inactivos. Pasaporte/otro pueden repetirse; no se
  fusionan registros ni se presupone país emisor. Búsqueda y selección manual.

Decisiones técnicas:

- Guest con UUID, tenant/created_by PROTECT, nombres/apellidos, tipo/documento,
  contacto opcional, notas restringidas, active y timestamps. Sin fechas de nacimiento,
  dirección, imágenes de documentos ni datos adicionales de acompañantes.
- Documento obligatorio; RUT canónico cuerpo-DV, sin puntos, DV en mayúscula y
  cuerpo positivo de hasta ocho dígitos. Se normalizan ceros iniciales equivalentes;
  se aceptan formatos con/sin puntos y guion correctamente agrupados, K/k y DV 0.
  Formatos mal agrupados, símbolos, cuerpo 0 o DV incorrecto se rechazan.
- Validación módulo 11 en backend y feedback frontend; no verifica identidad,
  asignación ni existencia del RUT en registros externos. No se hacen consultas a SII.
- UniqueConstraint PostgreSQL parcial para RUT y formato canónico; validación de DV
  en servicio/modelo. Registro concurrente produce una ficha y conflicto 409 con UUID
  de la ficha propia, sin datos de otra empresa. La UI ofrece abrir esa ficha.
- Pasaporte/otro: normalización Unicode NFKC, mayúsculas y espacios; hasta 40 caracteres
  alfanuméricos con separadores espacio/punto/guion/barra. Es validación sintáctica;
  no certifica documento extranjero ni aplica suposiciones sobre nacionalidad.
- Teléfono opcional: siete a quince dígitos con prefijo + opcional; retira espacios,
  guiones/paréntesis sin agregar automáticamente +56. Email opcional validado.
  Nombres/apellidos obligatorios hasta 150 caracteres; notas hasta 2000.
- Desactivación/reanudación sin borrado. Código RUT sigue reservado para reutilizar
  la misma ficha. Reservas/historial de estancias aún no se implementan.
- Listados/búsqueda: solo UUID, nombres, tipo, documento enmascarado y estado. Ficha
  staff recibe document_number=null y notes=null; no se cargan notas desde BD para
  esa consulta. Documentos cortos se enmascaran completamente.
- Auditoría con UUID/actor/tenant/acción y campos modificados, sin RUT, nombre,
  contacto, notas ni snapshots de PII. Lectura de ficha completa por owner/manager
  registra guest_sensitive_viewed. __str__ del modelo usa UUID, no nombres.
- Búsqueda por nombres o documento exacto mediante POST /guests/search/, con CSRF
  y contexto. Evita PII en URLs e historial de navegación; página/filtros en JSON.
  Respuesta count/page/has_next/has_previous/results, sin enlaces con búsqueda.
- Servicios revalidan roles/membresía, rechazan tenant/autor/ID del cliente y validan
  también llamadas internas. Campos compartidos estrictos y guard/contexto tenant
  se extrajeron para reutilización, manteniendo los permisos existentes de cabañas.
- Datos de pruebas y capturas son ficticios y están exclusivamente en BD de pruebas.
  No hubo envíos de correos, mensajes ni consultas externas sobre huéspedes.
- RUT de empresa sigue sin almacenarse: reutilizar el validador al autorizar esa
  configuración, sin agregar endpoints ajenos a esta fase.

Referencia oficial sobre dígito verificador: https://www.sii.cl/preguntas_frecuentes/preguntas_generales/001_430_5071.htm

## Fase 4 — Reservas y disponibilidad

Decisiones expresas del propietario:

- Pending retiene inventario hasta una fecha y hora indicada al crearla.
- Staff puede crear, editar, confirmar y cancelar reservas. La gestión de bloqueos
  corresponde a owner/manager; staff puede consultarlos.
- Capacidad estricta sin excepciones, al menos un adulto, niños no negativos y
  entrada desde hoy. Estadías por noches [entrada, salida), precio pactado manual
  en CLP; sin automatización de tarifas ni pagos.

Aplicación técnica:

- Fecha de hoy y horas de retención en la zona IANA de la empresa, heredada por
  sus cabañas. Por defecto America/Santiago. No hay anulación por propiedad en esta
  fase; antes de operar cabañas en distintas zonas habrá que acordar esa configuración.
- La API exige zona explícita en timestamps de retención. UI convierte la hora local
  usando la zona de empresa y rechaza horas inexistentes/ambiguas de cambio de hora.
  Fechas de estadía son date y nunca se convierten a medianoche UTC.
- Pending exige hold_until futuro al crear/renovar. Solo bloquea si hold_until > now.
  Al vencer conserva estado e historial, pero libera inventario sin tareas periódicas.
  Confirmar una retención vencida vuelve a validar disponibilidad; no tiene prioridad
  sobre una reserva o bloqueo posterior. Cambiar a borrador también libera fechas.
- Confirmada y en estadía bloquean; borrador, cancelada, ausencia y finalizada no.
  Los borradores pueden coincidir, pero deben respetar capacidad y entradas actuales.
- Todas las escrituras pasan por servicios de dominio: bloqueo de reserva/bloqueo
  y después filas de cabaña en orden estable dentro de transaction.atomic. Ambos
  tipos consultan reservas y bloqueos; dos operaciones concurrentes sobre una cabaña
  no pueden adjudicarse el mismo intervalo. Crear bloqueos solapados también se rechaza.
- Restricciones BD para fechas, importe no negativo, adulto obligatorio, valores de
  estados/orígenes/motivos y retención obligatoria en pending. El bloqueo compartido
  del servicio cubre también el cruce entre tablas. Escritura ORM/SQL directa de
  inventario no está soportada: debe usar los servicios; EXCLUDE común queda para
  un diseño unificado si se requieren otros escritores en el futuro.
- Reducción de capacidad de cabaña rechazada si deja incompatibles reservas futuras
  abiertas o una estadía iniciada, bajo el mismo bloqueo transaccional.
- Alta solo draft/pending/confirmed. PATCH no modifica estado; acciones explícitas:
  draft → pending/confirmed/cancelled; pending → draft/confirmed/cancelled;
  confirmed → checked_in/no_show/cancelled; checked_in → checked_out.
  Inicio dentro de fechas de estadía; salida desde fecha pactada; ausencia desde
  entrada. Cancelación/ausencia requieren motivo. Cerradas no se editan/reabren.
  Checklists y operación de limpieza siguen en Fase 8.
- Confirmación/retención nueva requieren cabaña/huésped activos y entrada actual.
  Edición conserva entrada original si ya pasó; no permite cambiarla por otra
  fecha pasada. Durante estadía no cambia cabaña/fechas/ocupación. Cancelar no
  requiere alterar esas fechas ni realiza devoluciones.
- Precio pactado numeric(14,2), validado sin floats; conserva valor si no se edita.
  CLP exclusivamente en esta fase, sin conversión ni cálculo automático por noche.
  Cambios de precio/fechas/personas/estado se auditan; notas y motivos no se duplican
  en auditoría. Notas operativas de reserva son visibles a operadores; notas
  restringidas de Guest y documento completo no se incluyen en reservas.
- Todas las referencias y consultas filtradas por empresa activa, CSRF y contexto.
  No hay DELETE, pagos, saldos, calendario, dashboard, acompañantes con datos
  personales adicionales, emails ni mensajes externos en esta fase.
- UI incluye listado/filtros/paginación, formulario con huéspedes existentes,
  consulta de disponibilidad y gestión de bloqueos. Pantallas cargadas bajo demanda.
- En Docker se activa sondeo de archivos Vite cada 500 ms mediante
  VITE_USE_POLLING=true: los eventos de cambios de Windows no invalidaban algunos
  módulos servidos. Ejecución local mantiene eventos normales salvo flag explícito.

Referencias oficiales de transacciones y bloqueo de filas:
https://docs.djangoproject.com/en/5.2/ref/models/querysets/#select-for-update
https://www.postgresql.org/docs/17/explicit-locking.html
https://vite.dev/config/server-options#server-watch

## Fase 5 — Pagos y abonos (14-10-2026)

El siguiente «sigue» autoriza exclusivamente esta fase. Decisiones expresas:
staff puede consultar, registrar y anular con motivo; se permiten sobrepagos y
reducciones de precio por debajo de lo recibido, mostrando saldo a favor.
Pendientes/confirmadas/en estadía/finalizadas reciben pagos. Borradores, canceladas
y ausencias no reciben pagos nuevos. Registrar no confirma ni renueva retenciones.
Cancelar conserva importe/pagos y excluye la reserva de deuda; no hay devoluciones.

- Payment con UUID y FK PROTECT, importe positivo numeric(14,2), CLP de la reserva,
  paid_at con zona explícita y no futuro, método, referencia opcional, autor y timestamps.
  Pagos inmutables: para corregirlos se anulan con motivo y se registra un nuevo abono.
- Anulación conserva fila, importe, comprobante, autor, motivo y fecha. Todos los
  roles de empresa autorizados pueden anular; no representa un reembolso.
- Recibido = suma de recorded; saldo = total pactado - recibido. Sumas con Decimal
  y consultas agregadas PostgreSQL; saldo negativo se presenta como saldo a favor.
  Estado unpaid/partial/paid/credit independiente del estado de reserva. Deuda solo
  en estados que reciben pagos con balance > 0. Canceladas no se cobran automáticamente.
- Bloqueo de fila Reservation para registro, anulación y comprobantes, compatible
  con edición de precio/cancelación de Fase 4. Validación de membresía y tenant en
  API y servicios, CSRF/contexto y ausencia de acceso implícito de plataforma.
- request_id UUID generado por UI y único por empresa evita duplicados al reintentar.
  Primera solicitud 201, repetición idéntica 200; contenido diferente con misma clave
  produce 409. Un reintento idéntico también conserva un pago posteriormente anulado.
  Anulación repetida con el mismo motivo devuelve el registro sin duplicar auditoría.
- Comprobantes opcionales JPG/PNG/WebP estáticos, 5 MB/4096 px, validación real de
  contenido y reencodeado sin EXIF/GPS/texto. Se reutiliza la política de imágenes
  existente. PDF no admitido en esta versión. Descarga autenticada como attachment,
  no-store/nosniff, almacenamiento privado con nombres UUID y rutas hasta 255 caracteres.
  No se reemplazan ni eliminan archivos; comprobantes de pagos anulados siguen accesibles
  a miembros autorizados. Adjuntar es independiente de registrar: fallo de archivo
  no duplica ni revierte el abono válido y la UI permite adjuntarlo desde el historial.
- Auditoría registra importes/métodos/fechas/UUID, sin referencias, motivos, nombres,
  documentos ni contenido de comprobantes; acceso a comprobantes también auditado.
- BD y almacenamiento no son una transacción distribuida: un fallo extremo de commit
  puede dejar un archivo huérfano privado. Conciliación, backups y retención se mantienen
  para hardening, sin eliminar automáticamente archivos existentes.
- Migraciones payments/0001_initial y 0002_alter_payment_receipt_file aditivas;
  el segundo cambio amplía la ruta privada después de detectar el límite por defecto.
- No hay cobro online, datos de tarjeta, reembolsos, conciliación bancaria, facturación,
  calendario ni dashboard en esta fase. Fase 6 requiere autorización separada.

## Fase 6 — Completada (14-10-2026)

Autorizada mediante el siguiente «sigue». El propietario confirmó expresamente:

- Pactado por entrada de reservas confirmed/checked_in/checked_out dentro del periodo.
- Cobrado por paid_at local de pagos recorded dentro del periodo, incluso si la
  reserva está cancelada. Anulaciones se reflejan según el estado actual del pago.
- Deuda y saldo a favor separados, sin compensar reservas entre sí.
- Ocupación = noches de confirmed/checked_in/checked_out / noches de cabañas
  actualmente activas. Pendientes y bloqueos aparte. Historial de inactivas en calendario.

Diseño implementado y verificado con PostgreSQL y navegadores:

- apps/insights sin modelos ni migraciones; GET calendar/ y dashboard/ con contexto
  y membresía revalidados. Fechas from/to, to exclusiva, máximo técnico de 366 días;
  property_id opcional solo de empresa autorizada, también para cabañas inactivas.
- Calendar devuelve reservas de todos los estados y bloqueos activos, con UUID,
  cabaña, fechas exclusivas, estado, vigencia de retención y enlaces internos.
  No devuelve nombres/documentos/contactos/notas del huésped ni notas de bloqueo.
- Dashboard distingue indicadores de hoy de indicadores del periodo. Disponible
  hoy excluye unión de confirmadas/en estadía, retenciones vigentes y bloqueos;
  salida el mismo día no ocupa inventario de hoy. Fechas locales de empresa.
- Noches del periodo recortadas al rango y unidas por cabaña para evitar doble
  conteo de intervalos históricos; bloqueos no se descuentan del denominador elegido.
  No hay reconstrucción de inventario histórico: el denominador usa cabañas activas hoy.
- Importes agrupados por moneda, Decimal sin floats. Saldos del periodo corresponden
  a reservas con entrada en ese periodo: deuda solo cobrables; créditos se conservan
  también en canceladas/ausencias cuando existen. No son balances históricos al cierre.
- Consultas de varias tablas en transacción REPEATABLE READ y READ ONLY para coherencia.
  Servicios snapshot se invocan desde vistas fuera de una transacción de escritura;
  las pruebas de integración utilizan transacciones reales para comprobarlo.
- /panel React con filtros, resumen de hoy, ocupación e importes; carga bajo demanda.
  /calendario implementado con navegación mensual/semanal, filtros de cabaña y tipo
  de evento, títulos/colores por estado y lista accesible. Refresco de lectura cada
  30 segundos; claves de caché por empresa y remount al cambiar empresa.
- FullCalendar Standard 7.1.2 MIT con filtro por cabaña. Sin plugins Premium
  de recursos ni licencias comerciales; temporal-polyfill 1.x requerido por v7.
  Props v7 color/contrastColor, clases mediante hooks públicos y fechas allDay sin
  conversiones horarias; UTC solo como marco del calendario y hoy de zona de empresa.
  No hay arrastre ni escritura directa. Referencias:
  https://fullcalendar.io/license y https://fullcalendar.io/docs/react.

Bloqueo previo de herramientas: consulta npm no ejecutada porque la revisión automática
de aprobación informó límite de uso. No fue una evaluación de acción insegura y no
se eludió ese control. Acceso restablecido al continuar: instalación, npm ci y
comprobaciones Docker completadas. npm informó cero vulnerabilidades.
La Fase 6 está cerrada y no autoriza la Fase 7.

## Fase 7 — Reportes y CSV (14-10-2026)

Autorizada mediante «sigue» tras cerrar la Fase 6. El propietario confirmó que
staff puede consultar reportes y descargar CSV; owner/manager conservan acceso.
No hay acceso implícito de plataforma ni empresas elegidas arbitrariamente.

- Reportes de lectura en apps/insights, reutilizando las consultas de dashboard y
  pagos; frontend features/reports en /reportes. Sin modelos ni migraciones nuevas,
  sin nuevas dependencias, sin PDF opcional ni funcionalidades de Fase 8.
- Resumen usa las definiciones aprobadas en Fase 6. Incluye conteo de canceladas
  con check_in en [from,to), no por instante de cancelación. Misma cohorte para
  detalle de reservas de cualquier estado; filtro status opcional. Esto mantiene
  el criterio de entrada ya elegido para pactado y saldos.
- Cobros: pagos recorded con paid_at en límites de medianoche local de la empresa;
  no se excluyen canceladas ni se incluyen anulados. No se mezclan monedas.
  Datos actuales, no reconstrucciones contables a una fecha pasada.
- Todas las consultas filtran tenant en servidor y validan propiedad propia,
  incluida inactiva. Periodo positivo hasta 366 días; snapshots REPEATABLE READ/
  READ ONLY. Resumen y detalle paginado tienen formas OpenAPI explícitas.
- Detalle de 25 filas ordenadas por fecha y UUID para desempate. CSV exporta todas
  las filas del filtro, no la página actual. Límite técnico de 5.000 filas: superar
  el límite produce 400, no un archivo incompleto. Resumen exporta una fila por
  moneda y conserva identificación de la cabaña seleccionada.
- Export exige X-Tenant-Context incluso siendo GET; cliente pasa contexto activo,
  recibe Blob solo con Content-Type CSV y no sigue enlaces externos. Se cancela
  al cambiar filtros/empresa o desmontar la pantalla. Cookie de sesión same-origin;
  sin URLs públicas ni archivos persistidos por el servidor.
- Descarga attachment UTF-8 BOM, delimitador ;, todas las celdas entre comillas,
  escaping de comillas por csv.writer; importes exactos como texto decimal con
  punto. Prefijo apóstrofo ante fórmulas =,+,-,@, variantes de ancho completo y
  prefijos de espacios/control/BOM. Incluye tests de delimitadores, saltos de línea
  y comillas maliciosas. Los saldos negativos quedan como texto protegido.
- Referencia primaria de defensa CSV: https://community.owasp.org/attacks/CSV_Injection.
  La protección aplica al archivo original: hojas de cálculo pueden alterar el
  escaping al guardar/reabrir. No se afirma protección universal sobre archivos
  transformados; consumidores deben preservar el tratamiento como texto.
- Exportaciones sin nombres/documentos/contactos/notas de huéspedes, ni referencias,
  motivos o comprobantes de pagos. Auditoría report.export conserva filtros,
  UUID de propiedad, tipo y cantidad de filas; sin contenido del archivo ni PII.
  Respuesta no-store/nosniff; middleware mantiene no-store para todo /api/v1/.
- Consultar/exportar no modifica reservas ni pagos. Los precios/saldos del detalle
  de todos los estados no se deben sumar sin las reglas del resumen.
- No hay contradicciones nuevas con la especificación; la estructura reporting/
  era sugerida, se mantiene insights para compartir definiciones y evitar duplicación.
  La Fase 8 requiere una autorización nueva.

## Fase 8 — Operación diaria (14-10-2026)

Autorizada con «go» y retomada con «sigue» tras una interrupción. Confirmado:
staff gestiona todas las tareas; check-out crea limpieza para ese día con checklist
fijo; limpieza alerta sin bloquear; WhatsApp prepara mensaje editable de envío humano.

- Nuevo módulo operations con HousekeepingTask; migración 0001 aditiva, FK PROTECT,
  UUID, empresa/cabaña, reserva de origen opcional, responsable Membership opcional,
  source manual/checkout, pending/in_progress/completed/cancelled, due_at UTC,
  checklist booleano, completed_at, autor y timestamps. Notas operativas y motivo
  de cancelación limitados a 1.000 caracteres, no copiados en auditoría.
- Todos los miembros activos pueden consultar, crear, asignar y actualizar tareas.
  Propiedad y responsable deben ser de la empresa; asignar requiere membresía y
  usuario activos. Nuevas tareas solo para cabañas activas; se conserva historial
  de inactivas. Creación manual sin reserva; referencia de reserva solo automática.
- Check-out llama al servicio de limpieza dentro de la transacción existente con
  bloqueo de reserva. Restricción única condicional de tarea checkout/reserva y
  get_or_create impiden duplicados. Si falla crear/auditar tarea, se revierte también
  el check-out. No se cambia la disponibilidad por tareas de limpieza.
- Vence a las 23:59:59 del día local efectivo al registrar check-out, incluso si se
  registra tarde. No usa una fecha programada pasada. No se migran tareas históricas
  de reservas ya finalizadas, ni se asigna responsable automáticamente.
- Checklist fijo baño/cocina/dormitorios/inventario. Completar requiere los cuatro
  true y timestamp; restricción DB de coherencia. Cancelar exige motivo no vacío.
  Completadas/canceladas quedan cerradas y no se borran/reabren; correcciones mediante
  otra tarea. Actualizaciones con bloqueo de fila y auditoría de estado/checklist/IDs.
- Panel diario por día local, propiedad y categoría; 25 registros paginados y
  conteos coherentes en snapshot READ ONLY/REPEATABLE READ. Entradas confirmadas/
  en estadía; salidas confirmadas/en estadía/finalizadas; salidas vencidas en estadía;
  pendientes con retención vencida al momento; mantenimiento activo ese día;
  limpieza pending/in_progress que vence ese día o antes. Son estados actuales,
  no una reconstrucción histórica, ni cambios automáticos de estado.
- Mantenimiento reutiliza AvailabilityBlock, intervalos exclusivos y locks anti
  solapamiento. Permisos owner/manager existentes. Auditoría ampliada conserva
  propiedad/fechas/motivo operativo antes y después, sin notas privadas.
- WhatsApp: endpoint autenticado de borrador por reserva, devuelve solo teléfono
  propio y texto con cabaña/fechas/estado. Auditoría de acceso solo UUID. Consulta
  usa only() para no leer documentos/notas/importes del huésped/reserva. UI editable,
  exige prefijo internacional explícito, no deduce país de números ambiguos.
  Enlace https://wa.me con dígitos y texto codificado; apertura voluntaria,
  target=_blank, noopener/noreferrer. No guarda borrador ni cambio de teléfono.
  Usuario revisa destinatario/texto y decide enviar; nada sale hacia WhatsApp al
  preparar el borrador. Referencia: https://faq.whatsapp.com/5913398998672934.
- Sin dependencias nuevas, workers, notificaciones externas ni APIs de Meta.
  Automatización oficial e IA mantienen sus fases 9A/9B y requieren autorización.
- OpenAPI fija enums distintos de reservas, pagos y limpieza para evitar colisiones.
  No hay decisiones funcionales pendientes dentro del alcance aprobado de Fase 8.

## Fases 9 y 9A — Diseño pendiente de aprobación (14-10-2026)

Propuesta concreta: [PROPUESTA_FASE_9_9A.md](PROPUESTA_FASE_9_9A.md).
Confirmados OpenAI (clave solo backend), gestión/conversión humana de consultas por
staff y 90 días operativos con aviso y archivo, sin eliminación automática.
Las secciones 17 y 18 del plan exigen aprobar propuesta antes de programar; el
«sigue» inició esta preparación, aún no se ha aprobado el documento resultante.

Se proponen tools de lectura y renderizado de hechos en Django, no SQL/precios
generados por IA; precio por confirmar hasta ingreso humano, y no saldos históricos
inventados. Crear un draft de consulta revalida disponibilidad bajo lock sin retener
inventario; requiere huésped existente o registro administrativo por el flujo actual.
El permiso de staff para reservas no amplía el permiso para crear huéspedes.
Archivo a 90 días no equivale a borrado físico: esa retención necesita política y
autorización aparte. Voz breve, voluntaria, revisable y sin grabación de llamadas.
No se prometen retención cero del proveedor ni facturación exacta por medidor local.

Límites técnicos, modelo configurable y dependencias figuran como propuestas, no
como configuración ya activa. Se propone verificar el desarrollo mediante proveedor simulado
antes de habilitar conexión real. Nada de 9B, Cloud API o envíos autónomos se autoriza.

## Consolidación 1.2 — 14-10-2026

El propietario indicó «sigamos» tras la revisión del plan y propuesta de consolidar
1.2. Se autorizó esta actualización documental; no la implementación IA pendiente.
Versión 1.1 preservada íntegramente en PLAN_MAESTRO_v1.1_2026-10-14.md.

La versión 1.2 centraliza aprobación por alcance (secciones 0/15), conserva las fases
0–8 y las reglas aprobadas, unifica 9/9A como 9.1 consultas, 9.2 bandeja/borradores,
9.3 voz y mantiene 9B futura. Una reanudación no requiere repetir aprobación vigente,
ni autoriza por sí sola otro alcance. Se incorpora puerta P de preparación de
producción antes de piloto real, sin marcarla cumplida o implementada.

Se explicitan zona por empresa, precio manual sin motor supuesto, saldos actuales,
permisos de huéspedes para conversión, diferencia entre archivo y borrado, y alcance
de MVP/piloto/SaaS. La política de prolongaciones y otros pendientes requiere acuerdo.
Las menciones anteriores a secciones 17/18 corresponden a 1.1; la aprobación de
propuesta IA sigue requerida por 1.2, sin nueva aprobación concedida en este paso.
# Fases 9.1–9.3: límites de confianza del asistente

## WhatsApp 9B.1–9B.3

Propuesta independiente aprobada mediante «sigue». Cuenta/número exclusivos por
empresa, onboarding manual, Cloud API con host fijo/versión configurable; real off.
Fernet con keyring backend dedicado y contexto cifrado de tenant/conexión evita
reutilizar ciphertext entre empresas. El verify token del GET no se imprime en logs.

Colas PostgreSQL y worker Django sin Redis/Celery. Eventos durables normalizados,
dedup por conexión/ID/tipo/estado; procesamiento recuperable por lease/token y locks.
Outbox único por request_id. Un crash del sender pasa a unknown: no se asume que
falló antes de enviar ni se reintenta. Un receipt positivo tardío puede conciliar
la misma tarea sin una nueva petición; eventos de entrega no retroceden estados.
429 se reintenta acotadamente; timeout/5xx ambiguo conserva incertidumbre.

Autorización humana con revisiones, permiso y ventana/plantilla; actor/contexto
revalidados antes de red y red fuera de locks. Nuevas entradas invalidan intenciones
pendientes. La UI conserva texto y retira revisión cuando cambia la conversación;
mensajes y revisión se reciben en snapshot coherente, evitando una carrera de polls.
No se edita durante preparación/envío para evitar sobrescribir texto revisado.

Recepción externa no representa acción del propietario: Inquiry.created_by nullable,
solo el flujo externo usa null; channel whatsapp_api no disponible para creación
manual. Cada entrada única tiene consulta separada vinculada, sin sobreescribir
ediciones anteriores. Hilo puede reactivarse con entrada nueva, pero no renueva
plazos de mensajes/consultas. Archivo90d lógico y sin purga física.

Política oficial consultada 14-10-2026: 24 h, plantillas fuera de ventana y opt-in/bajas,
https://whatsappbusiness.com/policy/ . Documentación Graph técnica no recuperable;
permisos/versión/catálogos/precios se verificarán antes de activación real autorizada.

El alcance de PROPUESTA_FASE_9_9A.md fue aprobado mediante «sigue» tras el plan 1.2.
SDK OpenAI/Pydantic fijados con hashes; adapter de interpretación con function
calling estricto. Django valida argumentos, permisos y hechos. No se vuelve a
enviar resultados/huéspedes al proveedor ni se renderiza texto factual libre del modelo.
Contexto firmado de 30 minutos ligado a actor/empresa, sin conversación persistida.
Cuotas por empresa con locks y red fuera de transacciones; consumo desconocido
no libera reservas. Desglose conocido permite conciliar el coste estimado Decimal.
El SDK async se ejecuta bajo un deadline de 25 segundos para la llamada completa,
además de límites de I/O; no hay reintentos automáticos. La respuesta WhatsApp
también se prepara por selección humana explícita, revalidando desde Django sin
una llamada al proveedor ni conocer UUID mediante lenguaje natural.

Inquiry separado del chat; original persistido solo por acción explícita, revisión
optimista y conversión idempotente bajo locks. Se revalida disponibilidad incluso
para draft; nunca se usa draft como retención. Archivo calculado al vencer 90 días,
sin purga física ni retroactividad. Voz valida contenedor/pistas/duración con ffprobe,
incluyendo WebM de MediaRecorder sin duración global mediante timestamps de paquetes.
Temporales nuevos privados descartados al terminar; no se elimina información existente.

Proveedor simulado únicamente con E2E_TEST_MODE y base cabanacontrol_e2e, marcado
en UI. E2E usa --noreload para evitar fallos transitorios durante modificaciones
del código compartido. Desarrollo mantiene autorecarga. IA real permanece apagada;
clave/modelos/tarifas deben configurarse privadamente y comprobarse antes de uso real.


## Puerta P local (14-10-2026)

Autorizadas P.1–P.3, sin despliegue ni proveedores reales. Compose independiente,
Gunicorn/Nginx/TLS local, imágenes base por digest, lock runtime separado del dev.
Rol PostgreSQL de aplicación sin privilegios de clúster; administrador distinto
no expuesto al backend/worker. Inicialización solo en volúmenes nuevos, sin alterar
roles o datos existentes. Migraciones explícitas antes de abrir servicios.
Copia coordinada con escritores detenidos, cifrado Fernet y clave fuera del snapshot;
restauración solo en otra base/media vacíos, sin --clean ni sobrescritura. Herramientas
limitadas al ensayo ficticio; el cifrado en memoria no es solución de backup a escala.
Health con BD, heartbeat de worker y probe con exit no saludable. Logs de aplicación
reducidos a marcadores para evitar PII; esto limita diagnóstico. HSTS de una hora,
sin includeSubDomains/preload local, con W005/W021 documentadas, no silenciadas.
Procedimientos y requisitos reales pendientes en PRODUCCION.md. P no cumplida
para un piloto real; no implica autorización de hosting, SMTP, WhatsApp o fases 10/11.

## 11A local — Invitaciones y usuarios web

Alcance explícitamente elegido por el usuario: propietario invita y asigna permisos.
Se adelanta gestión de colaboradores solo en desarrollo local; despliegue sigue
condicionado a P. Registro público, primer propietario web, transferencia de propiedad,
planes/cobros y cuentas comerciales no se incluyen. Ver ALCANCE_USUARIOS_WEB.md.
Token 256 bits, SHA256, 72 h, de un solo uso, link manual en fragmento y mostrado una
vez. No email/WhatsApp automático ni credenciales definidas por el propietario.
Cuenta existente exige autenticación del correo invitado; no se cambia su contraseña.
Nueva cuenta se crea junto a membresía/aceptación en una transacción. Locks de empresa
serializan aceptación/revocación y cambios; estado observado protege edición obsoleta.
Desactivar invalida invitaciones pendientes para evitar reactivación con enlaces viejos.
No cambia accesos de otras empresas ni revierte operaciones previamente admitidas.
El listado histórico de miembros conserva su contrato mínimo; el nuevo listado de
gestión contiene correo solo para el propietario de la empresa activa.

## 11D — Decisiones comerciales confirmadas (15-10-2026)

El usuario confirmó tres planes con 3/8/20 cabañas activas y 2/5/10 usuarios activos
por empresa; trial de 14 días, una sola vez por empresa, sin tarjeta ni contratación
automática; avisos y revisión manual ante vencimientos/impagos, sin bloqueo
automático inicialmente. No se aplicará la alternativa de gracia de siete días y
solo consulta. Suscripciones SaaS separadas de pagos de huéspedes.

Se actualizó PROPUESTA_COMERCIAL.md. Los precios, capacidad del trial/continuidad,
transición de empresas existentes y pasarela no están confirmados. La elección
autoriza consolidar el diseño, no implementar 11D.1–11D.3, activar cobros ni desplegar.

Actualización: el usuario fijó el trial en 1 cabaña activa y 1 usuario activo
(propietario incluido) y eligió asignar manualmente planes a las empresas existentes
al habilitar el módulo, revisando su uso. No se usa trial de un plan comercial
3/2, 8/5 o 20/10. Vencimiento conserva capacidad 1/1 y aviso hasta revisión manual,
coherente con la política confirmada de no bloqueo automático. Esquema aditivo y
habilitación/asignación comercial serán acciones separadas; no backfill automático
ni trial retroactivo. Propuesta 11D.1 concreta preparada, pendiente autorización.

### Implementación local 11D.1 autorizada (15-10-2026)

El «sigue» posterior autoriza 11D.1: modelos billing, tres planes, trial 1/1 por
14 días, capacidad, comando de asignación y pantalla Plan y uso. No incluye cobros
ni 11D.2/11D.3. Migraciones aditivas sin asignar o habilitar empresas actuales.
La habilitación se implementa por empresa tras revisión/asignación explícitas;
para habilitar todo un entorno hay que completar el inventario de empresas activas.
Esto ejecuta la transición manual sin un flag global que afecte empresas sin revisar.
Las nuevas altas tampoco reciben trial automático: asignación manual en esta fase.

Lock de Tenant antes de Property/Membership y verificación/escritura atómicas.
El mismo lock se usa en asignación de plan y activación de límites. Se cubren
reactivaciones e invitaciones/CLI, no solo formularios. Sobreuso tras downgrade
conserva recursos y bloquea únicamente aumentos. El vencimiento conserva trial 1/1.
Estado «manual» evita afirmar pagos inexistentes; no hay ciclos de cobro todavía.
Versiones de planes protegidas en PostgreSQL contra UPDATE/DELETE. Trial de un
solo uso y constraint de fechas completas/ordenadas, incluso con valores nulos.
Documentación operativa: PLANES_SUSCRIPCIONES.md. No se activan flags de proveedores.

## Definición de contratación simulada — elecciones (15-10-2026)

El usuario eligió Mercado Pago, sustituyendo la recomendación inicial de Flow,
y renovación mensual automática solo tras contratación y consentimiento explícitos.
El trial termina sin contratar/cobrar automáticamente. La primera implementación
propuesta sigue siendo simulador local, sin llamadas ni credenciales externas.

Se recibió «4500» como precio: se registra como valor de referencia 4.500 CLP,
sin atribuirlo a un plan ni asumir impuestos. Se solicitó aclarar los tres precios
y su presentación total/neta. Ningún precio se modifica en código o contratos.
Pendientes alcance definitivo, periodos/cambios y autorización de implementación.

Aclaración posterior: «inicial» confirma 4.500 CLP mensuales para Inicial.
Crecimiento y Operador siguen sin precio; presentación final/neta pendiente para
los tres planes. Se registra en propuestas, sin modificar catálogo implementado
ni inferir impuestos. Se solicitó únicamente completar esos datos faltantes.

El usuario delegó fijar los precios restantes («pon tu precios acordes»). Se
conserva Inicial 4.500 y se definen Crecimiento 9.900 y Operador 19.900 CLP/mes.
Para simulación: importes finales, sin recargos en checkout ni desglose tributario
inventado. Revisión fiscal/comercial antes de publicación y venta real. Criterio:
escalado desde el precio Inicial y menor coste por cabaña a mayor capacidad;
referencias públicas consultadas en PROPUESTA_CONTRATACION_SIMULADA.md.
Solo documentación: no cambia catálogo persistido ni se autoriza 11D.2.

## Página de presentación autorizada

La solicitud expresa de página con funcionamiento y precios autoriza mostrar los
valores de referencia en el frontend local: 4.500/9.900/19.900 CLP por mes. No se
activa contratación ni se modifica catálogo de contratos persistido. Compartidos
en planPresentation.ts para presentación y Plan y uso; importes futuros de checkout
serán siempre calculados/versionados en servidor. Página `/conocer` y raíz anónima;
raíz autenticada sigue como Empresas. Documentado en PAGINA_PRESENTACION.md.

## Alcance final de contratación simulada — reglas confirmadas

Tras elegir preparar el alcance final, el usuario confirmó subidas inmediatas y
bajadas al renovar, y cancelación al final del periodo sin reembolsos automáticos,
conservando datos/operación para revisión manual. Las subidas requieren resultado
aprobado antes de ampliar capacidad. Falta confirmar fórmula de prorrateo: se
propuso diferencia mensual × tiempo restante, redondeada al peso, sin cambiar
renovación; salir de trial iniciaría un mes completo. No se programa todavía.

Confirmación posterior del usuario: aplicar diferencia mensual × fracción de
tiempo restante, Decimal y redondeo al peso ROUND_HALF_UP, conservando renovación.
Ejemplo Inicial→Crecimiento con medio periodo: 2.700 CLP; renovación 9.900.
Salir del trial inicia un mes completo del plan elegido. Se cierra la definición
de prorrateo; alcance concreto de sección 9 de PROPUESTA_CONTRATACION_SIMULADA.md
listo para autorizar implementación local. No se autoriza automáticamente código,
conexión a Mercado Pago o cargos reales al confirmar esta regla.

## 11D.2 local implementada tras autorización

El «SIGAMOS» posterior al cierre de alcance autoriza implementar sección 9 de la
propuesta. Cotización/consentimiento, estado simulado, periodos mensuales UTC,
subidas prorrateadas, bajadas a renovación y cancelación diferida. Cargos simulados
aislados de Payment y de reportes de huéspedes. Versión de precio anterior y fechas
de periodo en intentos para preservar trazabilidad de prorrateo tras renovar.

Defensas: DEBUG y BILLING_SIMULATION_ENABLED (default false, producción fuerza false),
marca explícita de empresa ficticia y límites revisados previamente. No se habilita
la empresa principal ni se cargan precios por migración. Nueva demo E2E por arranque,
sin borrar contratos anteriores. No SDK ni llamadas externas. Precios inmutables,
intentos idempotentes y revisiones observadas, consentimiento de renovación vinculado
a precio/plan. Renovación mediante comando local; reintento de rechazo solo explícito,
con intento previo conservado. Sin cobros retroactivos si ya pasó otro periodo.

Se deja demo aislada disponible al cierre, con credenciales ficticias documentadas
en SIMULACION_COMERCIAL.md. 11D.3 y puerta P para piloto real siguen pendientes.

## Registro e inicio de sesión con Google (15-10-2026)

Autorizado expresamente por el propietario. Se usa Google Identity Services con
cliente web y respuesta JavaScript, sin client secret ni URI de redirección. Django
valida el ID token contra claves públicas oficiales y exige firma RS256, audiencia,
emisor, vencimiento y correo verificado. El token no se almacena. Un correo existente
puede iniciar sesión; uno nuevo debe indicar empresa y crea usuario sin contraseña,
empresa CLP/Santiago y membresía owner atómicamente. El registro local con contraseña
sigue desactivado en producción. Sesión Django, CSRF y límites por IP se conservan.

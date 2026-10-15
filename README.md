# CabañaControl

La preparación local de producción P.1–P.3 usa configuración independiente de
desarrollo: [procedimientos y checklist](docs/PRODUCCION.md). Incluye Gunicorn,
frontend compilado/Nginx, TLS ficticio, copia cifrada y restauración aislada.
La puerta P exige además decisiones y evidencia del entorno real antes del piloto.

Base de desarrollo SaaS multiempresa para alojamientos turísticos. Fases 0 a 8.
Especificación: [plan maestro](PLAN_FULL_CODEX_CABANACONTROL.md).

## Iniciar con Docker

Página de presentación con funcionamiento, demostración y precios: `/conocer`
(en este equipo, http://localhost:15173/conocer). También aparece en `/` sin sesión.
Con sesión, el inicio conserva las empresas. [Alcance de la página](docs/PAGINA_PRESENTACION.md).

Alta inicial local desde la web: abrir `/registrarse` (en este equipo,
http://localhost:15173/registrarse), crear la cuenta y empresa e iniciar sesión.
Después, seleccionar la empresa y usar **Usuarios** para invitar colaboradores.
[Alcance y limitaciones del alta local](docs/ALTA_PROPIETARIO_WEB.md).
En producción este registro permanece deshabilitado.

Requisitos: Docker Desktop iniciado en modo contenedores Linux, Docker Compose v2.
Desde la raíz, en PowerShell:

```powershell
# Solo si todavía no existe .env:
Copy-Item .env.example .env
# Editar .env: sustituir DJANGO_SECRET_KEY y POSTGRES_PASSWORD por valores aleatorios.
# Ajustar FRONTEND_URL y DJANGO_CSRF_TRUSTED_ORIGINS al puerto del frontend.
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

La configuración local `.env` creada durante la preparación contiene valores
aleatorios y está ignorada por Git. No imprimirla ni versionarla.

- Frontend: http://localhost:5173
- Backend: http://localhost:8000/health/
- Salud por proxy frontend: http://localhost:5173/health/
- PostgreSQL: `db:5432`, accesible solo dentro de Compose.

En este equipo los puertos predeterminados estaban ocupados. El `.env` local usa
backend http://localhost:18000 y frontend http://localhost:15173. Para las consultas
de ejemplo siguientes, sustituir 8000 por 18000 y 5173 por 15173.

```powershell
Invoke-RestMethod http://localhost:8000/health/
Invoke-RestMethod http://localhost:5173/health/
'SELECT 1 AS connection_check;' | docker compose exec -T db psql -U cabanacontrol -d cabanacontrol
docker compose logs --tail 100 backend frontend db
docker compose stop
```

Al cambiar package-lock.json con un volumen de dependencias existente:

```powershell
docker compose exec frontend npm ci
docker compose restart frontend
```

Si el acceso a la configuración global Docker está restringido, usar
`docker --config .docker-local --host npipe:////./pipe/dockerDesktopLinuxEngine compose ...`
con los mismos argumentos (Docker Desktop Linux en Windows).
Los datos persisten al detener servicios. No ejecutar `down -v` sobre datos existentes.
El ejemplo psql usa el nombre de usuario/base predeterminados; ajustar si se cambian.
El backend de desarrollo aplica las migraciones versionadas antes de iniciar.
No hay datos de demostración ni usuarios predeterminados en la base de desarrollo.

## Crear una cuenta y su primera empresa

Contratación simulada local: `/contratacion-simulada`, enlazada desde Plan y uso.
Solo funciona en empresas ficticias habilitadas expresamente; por defecto está
desactivada en desarrollo principal y producción. No conecta Mercado Pago ni cobra.
[Demo aislada, comandos y condiciones](docs/SIMULACION_COMERCIAL.md).

Como propietario, **Plan y uso** (`/plan`; http://localhost:15173/plan en este
equipo) muestra capacidad, uso y trial. Planes locales 3/2, 8/5, 20/10 y prueba
de 14 días con 1 cabaña/1 usuario. Asignación y habilitación manuales separadas;
migrar no activa límites. [Comandos y alcance comercial local](docs/PLANES_SUSCRIPCIONES.md).
No se realizan cobros ni se inicia trial automáticamente al registrarse.

Después de ingresar, **Perfil y empresa** permite editar tu nombre y apellido.
El propietario puede editar también nombre comercial, razón social y contactos
de la empresa seleccionada. En este equipo: http://localhost:15173/configuracion.
[Permisos y contrato de configuración](docs/PERFIL_EMPRESA.md).

Desde la web local, abrir `/registrarse`. Como alternativa por consola,
desde la raíz y con servicios iniciados (los correos siguientes son ejemplos):

```powershell
docker compose exec backend python manage.py create_account --email propietario@example.invalid --first-name Propietario
# La contraseña se solicita interactivamente y no se muestra ni se pasa por argumentos.
docker compose exec backend python manage.py create_tenant --name "Mi empresa" --owner-email propietario@example.invalid
```

Abrir `/ingresar`, iniciar sesión y seleccionar la empresa. Para agregar una
membresía a una cuenta existente, usar el UUID impreso por create_tenant:

```powershell
docker compose exec backend python manage.py add_membership --user-email colaborador@example.invalid --tenant-id UUID-DE-LA-EMPRESA --role staff
```

Roles: owner, manager y staff por empresa. `createsuperuser` es exclusivamente
para administrador de plataforma y no concede acceso automático a ninguna empresa.
El primer propietario y la empresa pueden crearse desde la web local. Los propietarios
pueden gestionar colaboradores desde [Usuarios](http://localhost:15173/usuarios):
crear una invitación, copiar su enlace privado y compartirlo personalmente.
El invitado define su contraseña al aceptar; si ya tiene cuenta, inicia sesión
con el correo invitado. El enlace vence en 72 horas y puede revocarse.
El registro permanece deshabilitado en producción; no hay gestión comercial ni
facturación SaaS en esta entrega.

Desde Usuarios se cambian roles administrador/colaborador y se desactiva/reactiva
el acceso a esta empresa, con revisión explícita. Los propietarios están protegidos.
La desactivación no borra la cuenta, no cambia contraseñas ni afecta otras empresas.
El enlace solo se muestra al crearlo; si se pierde, revocar la invitación y crear otra.
No se envía correo/WhatsApp automáticamente. Alcance: [11A local](docs/ALCANCE_USUARIOS_WEB.md).

## Administrar cabañas

Iniciar sesión, seleccionar una empresa y abrir `/cabanas`. Propietarios y
administradores pueden crear/editar, subir fotos y desactivar/reactivar; colaboradores
pueden consultar. El formulario requiere nombre, código, capacidad, tarifa base y
horarios de entrada/salida. No se presuponen tarifas ni horarios del negocio.

Tarifas se transmiten como texto decimal y se guardan con Decimal/numeric(14,2).
El formulario permite coma decimal, sin separadores de miles. La moneda se toma de
la empresa, CLP por defecto. No se define todavía una unidad de arriendo o temporadas.

La búsqueda usa nombre/código y filtro Activas/Inactivas/Todas. La desactivación
requiere confirmación y conserva registro, fotos y auditoría; no hay DELETE físico.
Los códigos se reservan también para cabañas inactivas.

Fotos: JPG/PNG/WebP estáticos, hasta 5 MB, 4096 píxeles por lado y diez activas por
cabaña. El servidor valida el contenido, reencodea y retira metadatos. Permite
editar descripción/orden y ocultar conservando el archivo. Archivos privados en
el volumen `private_media`, servidos por endpoints autenticados y filtrados por
empresa; no existe directorio `/media/` público.

El volumen de archivos persiste al reiniciar/reconstruir. Antes de un piloto con
datos reales, la puerta P exige respaldar coordinadamente PostgreSQL y este
volumen y ensayar su restauración. La Fase 12 amplía estos controles.
Ver [propuesta de preparación local](docs/PROPUESTA_P.md).

## Administrar huéspedes

Con una empresa seleccionada, abrir `/huespedes`. Propietarios y administradores
pueden registrar/editar/desactivar/reactivar fichas y consultar notas restringidas.
Los colaboradores solo consultan nombres, documento enmascarado y datos básicos
de contacto: no pueden escribir ni obtener notas o documentos completos.

Nombres, apellidos, tipo y número de documento son obligatorios. Teléfono, correo
y notas son opcionales. RUT se normaliza a cuerpo-DV, sin puntos, y se valida con
módulo 11. Se admite K/k, DV 0, puntos y guion. La verificación es matemática y
no consulta identidad o existencia ante el SII.

RUT único por empresa, también en fichas inactivas. Ante duplicado, la interfaz
ofrece abrir y reutilizar la ficha existente. Pasaporte/otro no exigen RUT y,
según la decisión del propietario, no tienen bloqueo automático de duplicados.

La búsqueda por nombres/documento completo usa POST con cuerpo JSON para que
los datos personales no queden en URLs. Los resultados son paginados y muestran
documentos enmascarados, sin contactos ni notas. Abrir documentos completos por
owner/manager deja una auditoría de acceso sin copiar su contenido.

Desactivar requiere confirmación y conserva registro/documento/notas y auditoría;
no hay borrado físico. La aplicación no envía mensajes ni correos a huéspedes.

## Recuperación de contraseña

En desarrollo Django guarda correos privados en `/tmp/cabanacontrol-emails` dentro
del backend. No se envían emails reales ni se imprimen enlaces en logs. Un operador
local puede copiar los archivos para abrirlos en privado:

```powershell
docker compose cp backend:/tmp/cabanacontrol-emails .local-emails
```

Ese directorio está ignorado por Git; no compartir ni versionar su contenido.
Es temporal y se pierde al recrear el contenedor. Para envío real configurar SMTP
mediante las variables de .env.example. FRONTEND_URL determina el enlace y debe
coincidir con el origen configurado para CSRF. Los enlaces vencen en una hora,
son de un solo uso y un cambio de contraseña invalida sesiones existentes.

## Verificaciones

```powershell
docker compose exec backend python manage.py check
docker compose exec backend ruff check .
docker compose exec backend ruff format --check .
docker compose exec backend pytest
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec backend python manage.py spectacular --validate --fail-on-warn --file /tmp/schema.yaml
docker compose exec frontend npm run lint
docker compose exec frontend npm run format:check
docker compose exec frontend npm test
docker compose exec frontend npm run build
```

pytest crea una base de pruebas separada; nunca usar credenciales de producción.
El test de integración de salud necesita PostgreSQL y comprueba una conexión real.

## Pruebas de navegador en entorno aislado

Docker Compose 2.24.4+ (usa `!override`), Node 22.12+. Nunca omitir el nombre de
proyecto: este entorno usa su propia red y volúmenes, y solo datos ficticios.

```powershell
docker compose -p cabanacontrol-e2e -f compose.yaml -f compose.e2e.yaml up --build -d
cd frontend
npm ci
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Resolve-Path ..) '.tools\playwright'
npx playwright install chromium
npm run test:e2e
cd ..
docker compose -p cabanacontrol-e2e -f compose.yaml -f compose.e2e.yaml stop
```

Prueba escritorio y móvil en Chromium: login, selector, persistencia, logout,
CSRF, IDs ajenos, permisos, recuperación genérica, crear/editar/fotografiar/desactivar
cabañas y registrar/editar/reutilizar huéspedes, documentos extranjeros y privacidad
de colaboradores. El flujo completo de tokens
también se verifica en las pruebas backend. Repeticiones frecuentes dentro de diez
minutos pueden activar el límite de intentos; esperar el tiempo indicado por 429.
No se elimina el volumen de prueba al detenerlo.

## Frontend sin Docker

Node 22.12+:

```powershell
cd frontend
npm ci
npm run lint
npm test
npm run build
npm run dev
```

El proxy local apunta a `http://127.0.0.1:8000`. Sin backend activo, la pantalla
informa conexión fallida; cargar HTML no demuestra que PostgreSQL funcione.

## Documentación

- [Decisiones y contradicciones](docs/DECISIONES.md)
- [Progreso y resultados reales](docs/PROGRESO.md)
- [API](docs/API.md)
- [Modelo de datos](docs/MODELO_DATOS.md)

Fases 1 a 8 autorizadas e implementadas. Fase 9 requiere nueva autorización.
Calendario, dashboard operativo, IA e integración WhatsApp quedan para sus fases.

## Reservas y disponibilidad (Fase 4)

Con sesión iniciada y empresa activa, abrir `/reservas`: registrar borrador,
pendiente con fecha/hora de retención o confirmada. Seleccionar cabaña activa,
huésped existente, fechas de entrada/salida, adultos/niños y precio total pactado
manualmente. El precio es CLP exacto, sin cálculo de tarifas ni registro de pagos.

Todos los miembros, incluidos colaboradores, gestionan reservas. Staff reutiliza
huéspedes existentes; solo owner/manager registran huéspedes nuevos y gestionan
bloqueos de fechas. Los documentos permanecen enmascarados en las reservas.

Pendientes retienen hasta la hora indicada en la zona de empresa; al vencer liberan
disponibilidad conservando historial. Confirmadas/en estadía y bloqueos activos
impiden reservas solapadas. La salida puede coincidir con una entrada posterior.
Capacidad estricta, al menos un adulto y nuevas entradas desde hoy; cancelación
con motivo y confirmación, sin borrado ni devoluciones automáticas.

`/reservas/disponibilidad` consulta por fechas/personas; `/reservas/bloqueos`
permite mantenimiento/uso propietario/otros motivos. Liberar conserva el bloqueo.
La consulta no adjudica fechas: cada escritura vuelve a validar bajo transacción.

En Docker se activa `VITE_USE_POLLING=true` para detectar cambios desde Windows.
Puede desactivarse cuando el sistema transmite correctamente eventos de archivos.
Las pantallas de reservas se cargan bajo demanda.

## Pagos y abonos (Fase 5)

Abrir la ficha de reserva en `/reservas/{uuid}` y usar **Registrar abono**. Todos
los miembros, incluido staff, pueden registrar y anular con motivo. Indicar importe
positivo, fecha/hora recibida en zona de empresa, método y referencia opcional.
Importes enviados como texto decimal; se admite coma en el formulario.

La ficha muestra recibido válido, saldo y estado de pago independiente de la reserva.
Se permiten sobrepagos y ajustes de precio que generan saldo a favor. Cancelar
conserva importe/pagos, excluye de deuda y no genera devoluciones. Borradores,
canceladas y ausencias no admiten pagos nuevos. Abonar no confirma ni renueva retención.
El listado de reservas tiene filtro **Solo reservas con deuda**.

Comprobante opcional JPG/PNG/WebP estático, hasta 5 MB/4096 px; no PDF. Archivo
privado con descarga autenticada, sin metadatos del original. Se conserva tras
anular y no se reemplaza. Si falla adjuntarlo, el abono permanece y el historial
permite intentar adjuntar después. No hay pagos negativos ni reembolsos en esta fase.
Se conservan registros y archivos; no se realizan cobros online ni envíos externos.

## Calendario y dashboard — Fase 6

Calendario en `/calendario`: FullCalendar Standard 7.1.2, vistas mensual/semanal,
navegación, búsqueda y filtro por cabaña (incluye inactivas), filtros de reservas,
bloqueos e inventario retenido. Colores y títulos por estado; enlaces a fichas y
lista accesible de eventos. Fechas de salida exclusivas, sin desplazarlas por zona
horaria. No permite arrastrar ni modificar reservas desde el calendario.

Panel en `/panel`: situación de hoy en la zona de la empresa, ocupación e importes
por periodo/cabaña, agrupados por moneda. Pactado por entrada de confirmadas/en
estadía/finalizadas; cobrado por fecha de pagos válidos, incluso de canceladas.
Deuda y saldo a favor de reservas con entrada en el periodo se presentan separados.
Son saldos actuales, no reconstrucciones históricas al cierre del periodo.
Ocupación usa noches reservadas sobre noches de cabañas actualmente activas;
retenciones y bloqueos se distinguen y no suman ocupación. Fin del periodo exclusivo.

Endpoints de lectura: `/api/v1/calendar/` y `/api/v1/dashboard/`, con `from`, `to`
y `property_id` opcional. Rango positivo de hasta 366 días. Contexto y membresía
validados en servidor; ninguna consulta admite cabañas ajenas. Sin migraciones nuevas.
Resultados y comandos de verificación: [progreso](docs/PROGRESO.md).
Fase 7 (reportes/exportaciones) se implementó tras el siguiente «sigue».

## Reportes y exportaciones — Fase 7

En `/reportes`, propietarios, administradores y colaboradores pueden consultar y
descargar CSV de tres reportes, por periodo y cabaña (incluidas inactivas):

- **Resumen y ocupación:** mismas cifras que el dashboard, canceladas con entrada
  en el periodo, importes por moneda, deuda y saldo a favor separados.
- **Reservas por entrada:** todos los estados o uno elegido, incluidas canceladas;
  precio, recibido válido y saldo actuales. Consulta paginada de 25 filas.
- **Cobros por fecha de pago:** solo pagos válidos recibidos dentro del periodo local,
  incluso de reservas canceladas. Los anulados quedan fuera.

Aplica el periodo con **Aplicar periodo**; cambiar cabaña/reporte/estado aplica ese
filtro inmediatamente. **Actualizar reporte** consulta el estado actual.
**Descargar CSV** incluye todas las páginas del filtro, hasta 5.000 filas, sin
truncarlas silenciosamente. Si se supera el límite, reduce el periodo o filtra cabaña.

CSV UTF-8 con BOM, separador punto y coma, fechas ISO e importes decimales con punto,
sin separadores de miles. Los campos peligrosos se neutralizan como texto y las
comillas/separadores se escapan; conserva esa protección si procesas el archivo.
No incluye documentos, teléfonos, correo, notas ni motivos privados. Descargas
autenticadas, con contexto de empresa validado y auditoría mínima de filtros/conteo.

Los totales del resumen tienen reglas por estado; sumar sin filtros los precios o
saldos aritméticos del detalle de todos los estados no reproduce esos totales.
La cancelación conserva precio/pagos y queda fuera de deuda. Las cifras representan
el estado actual, no un corte contable histórico. La cantidad de canceladas se
agrupa por entrada, no por fecha en que se cancelaron. No hay PDF en esta entrega.

API: `GET /api/v1/reports/` y `GET /api/v1/reports/export/`.
Consultar [contrato API](docs/API.md) y [resultados de pruebas](docs/PROGRESO.md).
No requiere migraciones ni nuevas dependencias. La Fase 8 se autorizó posteriormente.

## Operación diaria — Fase 8

En `/operacion` consulta entradas, salidas, estadías con salida pendiente,
retenciones vencidas, mantenimiento y limpieza pendiente, por fecha/cabaña.
Las alertas se calculan desde el estado actual; no cambian reservas automáticamente.
Desde cada registro puedes abrir la ficha y registrar check-in/out con las reglas
de fechas existentes. Mantenimiento reutiliza los bloqueos de disponibilidad:
solo propietarios/administradores pueden crearlos, editarlos o liberar fechas.

En `/limpieza`, todos los integrantes de la empresa pueden crear, asignar y gestionar
tareas. El check-out crea una tarea sin asignar, con vencimiento a las 23:59:59 del
día efectivo del check-out en la zona de la empresa. Reserva y tarea se guardan
en la misma transacción; no se duplica la tarea de una reserva. La migración no
crea tareas retroactivas para reservas finalizadas anteriormente.

Checklist fijo de **baño, cocina, dormitorios e inventario**. Para completar deben
estar los cuatro revisados. Cancelar requiere motivo. Tareas cerradas conservan
historial y no se editan ni eliminan; para corregirlas crea otra tarea. El panel
alerta sobre tareas abiertas con vencimiento ese día o anterior, sin bloquear reservas.
Puedes asignarlas a integrantes activos de esa misma empresa. Fechas/horas se
ingresan en zona de empresa; horas ambiguas o inexistentes requieren otro horario.

La ficha de reserva incluye **Preparar WhatsApp**: destinatario y mensaje editables,
con prefijo internacional explícito (`+` y código de país), copiar y abrir `wa.me`.
El borrador no incluye RUT, contactos adicionales, importes ni notas privadas.
Abrir el enlace comparte destinatario/texto con WhatsApp y requiere acción del usuario;
el envío lo hace la persona. Ajustar el teléfono no modifica la ficha del huésped.
No hay integración con Cloud API, automatización de envíos ni IA en esta fase.

Migración aditiva `operations/0001_initial`. Docker la aplica al iniciar backend;
para un servicio que ya estaba activo:

```powershell
docker compose exec backend python manage.py migrate
```

Resultados, comandos y limitaciones en [PROGRESO](docs/PROGRESO.md).
La propuesta de las fases 9.1–9.3 se autorizó posteriormente.

El diseño de las Fases 9.1–9.3 (antes 9/9A) está preparado en
[PROPUESTA_FASE_9_9A.md](docs/PROPUESTA_FASE_9_9A.md), con las decisiones confirmadas
de proveedor, permisos y conservación de consultas. Fue aprobada mediante «sigue»
después de consolidar el plan. Las pruebas usan proveedores simulados, sin llamadas
facturables ni claves reales.

El plan maestro está consolidado como versión **1.2**. Conserva las fases entregadas
y denomina el bloque de IA **9.1 consultas**, **9.2 bandeja/borradores** y
**9.3 voz** (antes 9/9A). La propuesta conserva su nombre de archivo por compatibilidad;
la regla de aprobación vigente está centralizada en las secciones 0/15 del plan.
La versión anterior está respaldada en [plan 1.1](docs/PLAN_MAESTRO_v1.1_2026-10-14.md).
La puerta P de producción debe verificarse antes del piloto desplegado con datos
reales. Esta consolidación documental no implementa IA ni declara listo el despliegue.

## Asistente, consultas y dictado — Fases 9.1–9.3

En `/asistente`, consulta disponibilidad, llegadas, saldos actuales y cobros por
periodo. Django valida los argumentos y obtiene los hechos: el proveedor no accede
a SQL, huéspedes, notas ni herramientas de escritura. Precio por confirmar, sin
calcular tarifas. Se exige revisar el texto antes de enviarlo a OpenAI.

En `/consultas`, registra manualmente texto de WhatsApp o un resumen de llamada,
asigna responsable y gestiona estados/respuestas. El original solo se envía si
lo copias explícitamente al campo de revisión. Las consultas vencen 90 días después
de crearse; aparecen en archivo y no se eliminan ni renuevan al editarlas.
La conversión exige un huésped existente, fechas, ocupación y precio manual:
crea un único borrador, revalida disponibilidad bajo locks y no retiene fechas.
Staff puede gestionar consultas y convertirlas; conserva su acceso de lectura
a huéspedes. Owner/manager pueden registrar huéspedes por el flujo existente.

El dictado es voluntario, hasta 60 segundos/5 MB, con revisión del audio antes de
transcribir y corrección posterior del texto. Sin grabación de llamadas ni audio
permanente. Docker incorpora ffprobe para validar el archivo real; fuera de Docker
también se requiere ese ejecutable. Si falla la IA o el micrófono, continúa manualmente.

La IA real está **desactivada por defecto**. Configura privadamente en el backend:
`AI_ENABLED`, `OPENAI_API_KEY`, `OPENAI_TEXT_MODEL`, las dos tarifas verificadas por
millón de tokens y, para voz, `OPENAI_TRANSCRIPTION_MODEL` y tarifa por minuto.
Consulta los nombres completos en `.env.example`. No uses prefijo VITE para claves.
Después habilita IA/dictado por empresa desde `/asistente` como owner/manager.
El presupuesto USD es estimado: no sustituye límites ni facturación de OpenAI.
Verifica tarifas/compatibilidad del modelo elegido antes de habilitarlo.

Límites iniciales: 6 solicitudes/usuario/minuto, 15/empresa/minuto, 50/día,
100.000 tokens/día, 600 segundos de voz/día y USD 1 estimado/día. Reservas
conservadoras antes de la red; consumo conocido concilia tokens y coste cuando
hay desglose de uso. Fallos con consumo incierto conservan la cuota reservada.
Modelos sin configurar devuelven 503 y no ejecutan llamadas. OpenAI Responses usa
`store=false`, que no promete retención cero del proveedor.

Migraciones aditivas `assistant/0001_initial` e `inquiries/0001_initial`.
Inicio/actualización: `docker compose up --build -d`; migraciones automáticas al
arrancar backend. E2E usa `compose.e2e.yaml` y `AI_TEST_PROVIDER` protegido por
modo explícito y nombre exacto de la base E2E; nunca habilitarlo en desarrollo/piloto.
Resultados ejecutados en [PROGRESO](docs/PROGRESO.md). No incluye Fase 9B ni despliegue.

## WhatsApp oficial — Fase 9B.1–9B.3

En `/whatsapp` consulta conversaciones propias y mensajes de texto recibidos mediante
webhook autenticado. Cada entrada abre una consulta enlazada, sin activar IA ni
crear huéspedes/reservas. La respuesta se prepara, edita, revisa y autoriza manualmente.
Owner/manager configuran la conexión y el catálogo de plantillas; staff gestiona
conversaciones, permisos/bajas y respuestas. La conversión a draft usa la ficha de
consulta existente y sus validaciones, siempre con intervención humana.

Cuenta/número exclusivos por empresa y credenciales cifradas con Fernet y clave
dedicada versionada fuera de BD. Las respuestas API nunca devuelven tokens ni
ciphertext. El token de verificación del webhook se omite de los logs de desarrollo.
El worker `whatsapp-worker` procesa una cola PostgreSQL durable separada, con leases,
deduplicación y locks breves; no mantiene transacciones durante HTTP.

Se exige permiso registrado. El servidor comprueba la ventana de atención de 24 h;
fuera de ella se selecciona una plantilla estática verificada para la cuenta/idioma.
No se gestionan aprobaciones remotas ni plantillas con parámetros/componentes adicionales.
La política vigente se verificó en [WhatsApp Business Messaging Policy](https://whatsappbusiness.com/policy/).
Las bajas reconocidas se registran automáticamente; las demás solicitudes requieren
revisión humana. La entrada nueva invalida los envíos pendientes basados en otra
revisión. Desactivar/rotar conexión o revocar permiso bloquea tareas pendientes;
una petición ya en curso puede completarse.

Estados separados: en cola, aceptado por proveedor, enviado, entregado, leído,
fallido, bloqueado e incierto. Un timeout, 5xx ambiguo o crash del sender no provoca
reenvío ciego. El mismo request_id devuelve el mismo intento. Cambiar texto crea
una intención nueva: revisa los resultados inciertos antes de repetir un mensaje.
Solo rechazos 429 explícitos se reintentan, hasta 3 intentos y con backoff. Estados
recibidos fuera de orden no hacen retroceder una entrega ya acreditada.

Archivo lógico a los 90 días, sin eliminación física. Una entrada nueva puede
reactivar el hilo y abrir una consulta nueva; no renueva mensajes/consultas antiguos.
Hay vistas de archivo para conversaciones y mensajes. Solo se procesa texto;
medios/audio entrante, campañas y respuestas automáticas quedan fuera.

**WhatsApp real permanece apagado.** `.env.example` contiene nombres de variables,
sin secretos. La clave de cifrado no puede reutilizar DJANGO_SECRET_KEY. Conservar
claves anteriores permite leer credenciales cifradas con versiones anteriores;
actualizar el token vuelve a cifrarlo con la versión activa. No cambiar cuenta/número
de una conexión con historial mediante el formulario actual.

Activación real es una tarea separada: cuenta/número/app, permisos, versión Graph,
plantillas reales, consentimiento, precios/presupuesto, dominio HTTPS y puerta P
de producción necesitan comprobación y autorización. La documentación técnica de
Meta devolvió errores de acceso: los tests HTTP mock no acreditan compatibilidad
de una cuenta/modelo de plantillas o versión Graph reales. No hubo llamadas a Meta
ni mensajes facturables. E2E contiene claves/IDs explícitamente ficticios y el
adapter está protegido por modo E2E y nombre exacto de su BD.

```powershell
docker compose up --build -d
docker compose logs --tail 30 whatsapp-worker
docker compose exec backend python manage.py whatsapp_worker --once
```

Migraciones `whatsapp/0001–0003` e `inquiries/0002`, sin backfill. Las consultas
externas tienen created_by nulo para no atribuir recepción automática al propietario;
las operaciones humanas conservan su actor real. Comandos/pruebas en PROGRESO.

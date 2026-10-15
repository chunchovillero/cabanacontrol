# Progreso — 14-10-2026

Estado actual: Fases 0 a 8 completadas y verificadas. Las fases 1 a 8 fueron autorizadas
mediante sus respectivos «sigue». Políticas de Fases 4 y 5 confirmadas expresamente
por el propietario. Métricas de Fase 6 y permisos de Fase 7 confirmados expresamente;
Fase 8 completada con sus reglas confirmadas. Fases 9.1–9.3 (antes 9/9A) con diseño preparado;
implementación pendiente de aprobación de la propuesta.

Actualización: Fase 7 completada con reportes y CSV por periodo/cabaña, protección
contra fórmulas, descargas de staff auditadas y aislamiento multiempresa verificado.
El bloqueo histórico de revisión automática de Fase 6 se había restablecido.

Actualización final: Fase 8 con limpieza/check-out/checklist, alertas y WhatsApp
manual. 20 casos E2E aprobados entre la corrida completa (19) y reejecución del
último caso móvil (1) tras vencer la ventana login. Sin desactivar controles ni
borrar contadores. Backend 293 y frontend 85 pruebas aprobadas.

## Fase 0

Preparación técnica completada y verificada. Al cerrar esta fase, el descubrimiento
seguía pendiente y la Fase 1 aún no estaba autorizada; se autorizó posteriormente.

### Archivos creados

- Raíz: compose.yaml, .env.example, .gitignore y README.md; repositorio Git local
  inicializado sin commits. .env local con secretos aleatorios, ignorado por Git.
- Backend: Dockerfile, .dockerignore, pyproject.toml, requirements-dev.lock,
  manage.py, config/{settings,urls,health,wsgi,__init__}.py, apps/__init__.py,
  tests/test_health.py. Sin modelos de dominio ni migraciones en esta fase.
- Frontend: Dockerfile, .dockerignore, package.json, package-lock.json, index.html,
  tsconfig.json, vite.config.ts, eslint.config.js, components.json, src/main.tsx,
  src/index.css, src/app/{App.tsx,App.test.tsx}, src/components/ui/button.tsx,
  src/lib/utils.ts y src/test/setup.ts.
- Documentación: DECISIONES.md, PROGRESO.md, API.md y MODELO_DATOS.md.
- Herramientas locales ignoradas: Python descargado en .tools y backend/.venv.

### Resultados ejecutados

| Verificación | Resultado |
| --- | --- |
| Docker Compose config --quiet | Correcto |
| Docker Compose up --build -d | Construcción y arranque correctos |
| Compose ps | db, backend y frontend healthy |
| Django manage.py check | Sin problemas |
| Ruff check / format --check | Correctos; 8 archivos formateados |
| pytest en contenedor con PostgreSQL | 3 pruebas aprobadas |
| Frontend ESLint en contenedor | Correcto |
| Frontend Vitest en contenedor | 3 pruebas aprobadas |
| TypeScript estricto + Vite build en contenedor | Correctos |
| npm ci / auditoría final | 0 vulnerabilidades reportadas |
| HTTP localhost:18000/health/ | 200, status ok y database ok |
| HTTP localhost:15173/health/ | 200, proxy hacia backend correcto |
| HTTP localhost:15173 | 200; HTML UTF-8, título y módulo React verificados |
| PostgreSQL SELECT 1 AS connection_check | Resultado 1 |
| Git check-ignore .env | Archivo excluido |

Comandos Docker ejecutados con configuración local y host explícito por
restricciones de acceso al perfil global:

```powershell
docker --config .docker-local --host npipe:////./pipe/dockerDesktopLinuxEngine compose up --build -d
docker --config .docker-local --host npipe:////./pipe/dockerDesktopLinuxEngine compose ps
docker --config .docker-local --host npipe:////./pipe/dockerDesktopLinuxEngine compose exec backend pytest
docker --config .docker-local --host npipe:////./pipe/dockerDesktopLinuxEngine compose exec frontend npm test
docker --config .docker-local --host npipe:////./pipe/dockerDesktopLinuxEngine compose exec frontend npm run build
```

Los servicios quedan activos: frontend http://localhost:15173 y backend
http://localhost:18000/health/. Puertos internos: frontend 5173, backend 8000, db 5432.

### Problemas encontrados y solución

- Python del PATH era un alias inaccesible: instalación local Python 3.12 mediante uv.
- Red restringida en sandbox: descargas realizadas con escalaciones aprobadas.
- Motor Docker inicialmente desconectado: Docker Desktop iniciado en segundo plano;
  acceso por dockerDesktopLinuxEngine y configuración aislada.
- Puertos 8000/5173 ocupados por otro proyecto: .env local usa 18000/15173; no se
  detuvieron ni alteraron servicios de ese proyecto.
- Alertas iniciales Vitest/Vite: actualización a Vitest 5.0.4 y Vite 8.3.4 con
  plugin React compatible. Auditoría final sin vulnerabilidades.
- Una ejecución inicial Vitest falló mientras se actualizaba node_modules; las
  ejecuciones finales secuenciales locales y del contenedor pasaron.
- Lock backend inicial omitió typing-extensions al resolverse para otra versión
  de Python: regenerado universal para Python 3.12; construcción con hashes pasó.
- Aviso de permisos para caché pytest compartida Windows/Linux: caché deshabilitada;
  ejecución final 3 passed sin ese aviso.
- Una consulta HTML con decodificación automática de PowerShell no reconoció la ñ;
  comprobación explícita UTF-8 confirmó título correcto.
- Git bajo identidad escalada detecta propietario diferente al sandbox. No se
  modificó safe.directory global; usar Git con identidad del entorno original.
- npm informa dependencias obsoletas ESLint 9 y whatwg-encoding transitorio. Lint,
  tests y build pasan; no hay alertas de seguridad en auditoría final.

### Pendientes y siguiente paso

- Confirmar descubrimiento y asuntos del plan registrados en DECISIONES.md.
- Revisión visual en navegador real / móvil pendiente; React fue probado con
  Testing Library y jsdom, no con E2E de navegador.
- Aprobar explícitamente la propuesta de Fase 1 antes de crear usuario personalizado,
  tenants, membresías, sesiones, CSRF autenticado y sus migraciones/tests de aislamiento.
- Calendario, RUT, reservas, pagos, IA y WhatsApp permanecen en sus fases futuras.

## Fase 1 — Identidad y multiempresa

Implementada y verificada, sin funciones de Fase 2. Se revisó nuevamente el plan
completo, las decisiones y el progreso antes de programar. Se presentó alcance,
archivos, migraciones, riesgos y comandos. No se modificó el plan maestro.

### Entregables

- apps/accounts: usuario personalizado con correo único, sesiones, CSRF explícito,
  recuperación, validación de contraseñas, servicios, serializadores, errores JSON,
  throttling compartido y comando create_account.
- apps/tenants: Tenant y Membership, consultas filtradas, contexto/middleware,
  permisos por rol, selector, endpoints paginados y comandos create_tenant y
  add_membership. Cuenta, empresa y membresía inactivas revocan acceso.
- apps/audit: eventos mínimos de identidad/contexto y acceso de plataforma.
- Migraciones iniciales versionadas en accounts, tenants y audit. Aplicadas junto
  a las migraciones estándar. AUTH_USER_MODEL configurado antes de migrar.
- Frontend: cliente API con sesión/CSRF, proveedor de autenticación, login,
  recuperación, nueva contraseña, empresas y logout; formularios accesibles,
  validación Zod, React Hook Form, React Router y TanStack Query.
- Página técnica de salud conservada en /estado, sin reemplazar el flujo de acceso.
- OpenAPI generado en docs/openapi.yaml y protegido en /api/v1/schema/.
- Pruebas backend en test_identity.py y test_auth_security.py; frontend Identity y
  api; Playwright en frontend/e2e, playwright.config.ts; entorno compose.e2e.yaml
  con seed restringido a una base de prueba.
- Prettier y flujo CI GitHub Actions backend/frontend/E2E. Variables de email y URL
  documentadas en .env.example. Docker aplica migraciones al iniciar en desarrollo.
- Capturas revisadas visualmente: docs/screenshots/fase1-login-desktop.png y
  fase1-login-mobile.png, sin credenciales ni datos personales.
- README, API, MODELO_DATOS y DECISIONES actualizados con comandos y límites.

### Resultados reales

| Verificación ejecutada | Resultado |
| --- | --- |
| Base inicial antes de migrar | 0 tablas públicas |
| Migraciones accounts/tenants/audit y estándar | Aplicadas correctamente |
| manage.py check | Sin problemas |
| makemigrations --check --dry-run | Sin cambios pendientes |
| Ruff check / format --check en contenedor final | Correctos, 49 archivos |
| pytest con PostgreSQL | 48 aprobadas |
| ESLint + Prettier en contenedor final | Correctos |
| Vitest en contenedor final | 17 aprobadas |
| TypeScript estricto + Vite build final | Correctos |
| Playwright Chromium escritorio y móvil | 6 E2E aprobadas |
| spectacular --validate --fail-on-warn | Correcto, sin advertencias |
| npm ci y auditoría de dependencias finales | 0 vulnerabilidades reportadas |
| Compose reconstruido y reiniciado | db, backend y frontend healthy |
| Base de desarrollo tras pruebas | 0 usuarios: no recibió fixtures E2E |
| Capturas de login escritorio/móvil | Generadas y revisadas |
| Archivo CI | Estructura YAML validada localmente; ejecución remota no realizada |

Pruebas cubren acceso cruzado en ambas direcciones con IDs conocidos y parámetros,
contexto de sesión manipulado, múltiples empresas, roles owner/manager/staff,
revocación inmediata, aislamiento de platform_admin, auditoría, CSRF anónimo y
autenticado, origen ajeno, rotación de cookie/session key, invalidación por cambio
de contraseña, tokens inválidos/vencidos/reutilizados, fallo de SMTP sin secretos,
límites compartidos concurrentes y aprovisionamiento CLI.

Las E2E usan una BD cabanacontrol_e2e en el volumen de proyecto
cabanacontrol-e2e; los contenedores de prueba se detuvieron sin borrar volúmenes.
Los tres contenedores de desarrollo permanecen activos en puertos 18000 y 15173.

### Incidencias corregidas

- Una prueba de recuperación construía un token con last_login anterior al login:
  se corrigió el fixture para usar el estado real persistido de usuario.
- Una prueba de rol inválido usaba una cadena más larga que el campo y comprobaba
  un error diferente: ahora verifica directamente la restricción de rol.
- Borrar toda la caché TanStack retiraba el observador activo de sesión e impedía
  actualizar login/logout: se conservó esa consulta y se cancelan/retiran las demás.
- Creación de migraciones local sin PostgreSQL accesible informó una advertencia de
  DNS; generación, aplicación y comprobación posteriores en Docker fueron correctas.
- Captura inicial por stdin PowerShell alteró un selector con acento: se usó un
  selector estructural y las capturas finales se generaron correctamente.
- Primera descarga Chromium usó la ruta global por un error al resolver Parent;
  las pruebas finales usan una instalación explícita en .tools/playwright del
  proyecto. No se borraron archivos globales.
- npm mantiene avisos de obsolescencia ESLint 9 / whatwg-encoding, sin alertas de
  seguridad reportadas ni fallos de linters/tests/build.

### Límites y próximos pasos

- No hay usuarios predeterminados en desarrollo: crear una cuenta interactiva y
  su empresa con los comandos documentados en README. No se eligieron credenciales
  reales por el propietario.
- Recuperación funciona con correos privados de desarrollo; SMTP real pendiente de
  proveedor y configuración. No hubo envíos externos.
- CI está preparado pero no publicado ni ejecutado remotamente; no se afirma que
  un pipeline GitHub haya pasado.
- Hardening de producción, proxies confiables, retención de eventos/buckets y
  despliegue continúan en sus fases correspondientes.
- La revisión visual de acceso escritorio/móvil y las E2E de identidad ya se
  realizaron; el E2E del MVP completo corresponde a fases posteriores.
- Completar preguntas de negocio pendientes y autorizar Fase 2 antes del CRUD de
  cabañas, capacidad, tarifas, imágenes y desactivación con historial protegido.

## Fase 2 — Cabañas

Autorizada por el segundo «sigue», implementada y verificada. Sin funcionalidad de
Fase 3. Se releyó íntegro el plan y se revisó estructura/decisiones/progreso. Se
presentó el alcance antes de implementar. El plan maestro permanece sin cambios.

### Archivos y cambios

- backend/apps/properties: apps.py, models.py, queries.py, permissions.py,
  serializers.py, services.py, images.py, uploads.py, views.py, urls.py e inicializadores.
- Migración properties/0001_initial con Property/PropertyPhoto, índices y restricciones.
  audit/0002_auditevent_after_auditevent_before agrega JSON mínimos de cambios.
- AuditEvent y record_event admiten snapshots seguros de capacidad/tarifa/horarios/estado.
- settings/urls: app, storage privado, límites/handler de archivos y rutas; Dockerfile,
  compose.yaml y .env.example: volumen privado persistente y configuración.
- Pillow fijado con hashes en requirements-dev.lock y declarado en pyproject.toml.
- frontend/src/features/properties: api.ts, PropertyAccess.tsx, PropertyList.tsx,
  PropertyForm.tsx, PropertyDetail.tsx, PhotoManager.tsx y Properties.test.tsx.
- Cliente API admite PATCH, multipart y precondición de contexto. Navegación/selector
  dan acceso a /cabanas; guard protege sesión/empresa/rol y reinicia formularios al
  cambiar empresa.
- backend/tests/test_properties.py y test_property_concurrency.py; seed E2E con
  usuarios ficticios independientes por dispositivo; frontend/e2e/properties.spec.ts
  y adaptación de identity.spec.ts para evitar compartir cuotas de login.
- README, DECISIONES, API, MODELO_DATOS, PROGRESO y OpenAPI regenerado.
- Capturas QA con datos ficticios: fase2-cabanas-{desktop,mobile}.png y
  fase2-formulario-{desktop,mobile}.png en docs/screenshots, revisadas visualmente.

### Verificaciones ejecutadas

| Verificación | Resultado |
| --- | --- |
| Construcción y arranque Compose | Correctos |
| Migraciones properties/0001 y audit/0002 | Aplicadas sin borrar datos |
| manage.py check | Sin problemas |
| makemigrations --check --dry-run | Sin cambios pendientes |
| Ruff check / format --check | Correctos |
| pytest con PostgreSQL, regresión completa | 94 aprobadas |
| ESLint + Prettier | Correctos |
| Vitest en contenedor | 26 aprobadas |
| TypeScript estricto + Vite build | Correctos |
| E2E completas Chromium escritorio/móvil | 8 aprobadas en ejecución final |
| spectacular --validate --fail-on-warn | Sin errores/advertencias; OpenAPI exportado |
| Archivos privados reales en E2E | Carga/lectura correctas; empresa ajena = 404 |
| Deactivación y recarga E2E | Conserva ficha y fotografía |
| Capturas escritorio/móvil | Revisadas; formulario y navegación responsive |
| Consulta final de desarrollo | 0 usuarios y 0 cabañas: sin fixtures E2E |
| /health/ directo y por proxy | status/database ok |

Pruebas nuevas cubren tenant en URLs/query/headers, campos inmutables rechazados,
precondición de contexto/CSRF, staff solo lectura, owner/manager edición, código
duplicado incluyendo inactivas, validación capacidad y dinero exacto, search/active,
rechazo de DELETE, auditoría antes/después, permisos de servicios y archivos privados.
Pruebas de fotos validan PNG/JPEG/WebP reales, metadata retirada, SVG/GIF/corruptos/
tamaño/dimensiones rechazados, límite y orden, ocultamiento sin borrar y no reaparición
de fotos ocultas al editar/desactivar la propiedad. Pruebas concurrentes comprueban
unicidad de código y máximo de fotografías con PostgreSQL real.

### Incidencias resueltas

- Una prueba cerraba manualmente FileResponse y activaba el cierre de conexiones de
  Django dentro de la transacción de pytest: se consume el stream con el wrapper
  del cliente de pruebas, sin cambiar el comportamiento de producción.
- La primera E2E consultaba antes de terminar el cambio de empresa. Se espera la
  confirmación visible antes de verificar aislamiento; comprobación final = 404.
- Repeticiones E2E activaron correctamente el límite de login en una cuenta compartida:
  fixtures por dispositivo/caso separan contadores sin desactivar protección.
- Revisión detectó que un PATCH con instancia nueva podía serializar fotos ocultas:
  filtrado explícito de fotos activas en toda respuesta y regresión automatizada.
- Generación local de migraciones informó la advertencia conocida de DNS db fuera
  de Docker; aplicación y revisión con PostgreSQL en Compose fueron correctas.

### Próximos pasos y límites

- Crear cuenta/empresa propias con los comandos README si todavía no existen. Las
  pruebas escribieron exclusivamente fixtures en BD de pytest/E2E, no en desarrollo.
- Dar de alta las cabañas reales: cantidad/capacidad, tarifa y horarios se ingresan
  por el propietario; no se usaron reglas de negocio supuestas.
- Confirmar reglas pendientes antes de reservas/pagos y eventual zona por propiedad.
- No hay todavía huéspedes, reservas, pagos o calendario. La conservación de sus
  futuros historiales se verificará al implementar sus relaciones PROTECT/RESTRICT.
- Retención/conciliación de archivos y backups BD+media quedan para hardening;
  no se eliminan registros ni archivos automáticamente. No hay envíos externos.
- CI remoto y SMTP real siguen pendientes de publicación/configuración.
- Fase 3 sugerida: huéspedes y validación de RUT. Requiere nueva autorización.


## Fase 3: huéspedes

Completada dentro del alcance autorizado. El propietario confirmó que staff solo
consulta datos básicos y que los documentos extranjeros no bloquean duplicados.

### Cambios y archivos

- Backend: apps/guests con modelo, validadores, permisos, consultas, servicios,
  serializers, vistas, rutas y migración 0001_initial; tests/test_guests.py y
  tests/test_rut.py. Aislamiento por empresa y restricciones compartidas de contexto.
- Frontend: features/guests con listado, búsqueda, ficha, formulario, API y pruebas;
  acceso común TenantAccess, rutas /huespedes y navegación responsive.
- Pruebas de navegador y fixtures ficticias en la base E2E independiente.
- README, DECISIONES, API, MODELO_DATOS, OpenAPI y capturas en docs/screenshots.

RUT normalizado y dígito verificador validados en frontend y backend; unicidad por
empresa protegida también por PostgreSQL, incluidos registros inactivos. Pasaporte
y otros documentos permiten coincidencias. Propietarios/administradores gestionan
las fichas; staff consulta nombres, contacto y documento enmascarado, sin documento
completo ni notas. Se puede desactivar/reactivar sin eliminar registros.

Búsqueda mediante POST con JSON para evitar datos personales en URL. Auditoría
sin valores personales y registro de consultas a información restringida. No hay
reservas, pagos, IA ni envíos externos implementados en esta fase.

### Verificaciones

| Verificación | Resultado |
| --- | --- |
| Backend pytest con PostgreSQL | 163 aprobadas |
| Frontend Vitest | 43 aprobadas |
| Playwright escritorio y móvil | 10 aprobadas |
| Ruff, ESLint y formato | Correctos |
| TypeScript y Vite build | Correctos |
| Django check / migraciones pendientes | Sin problemas / ninguna |
| OpenAPI validate --fail-on-warn | Correcto |
| Migración guests 0001_initial | Aplicada |
| Base de desarrollo: usuarios, propiedades, huéspedes | 0, 0, 0; sin fixtures |

### Problemas resueltos y límites

- Validación del servicio fortalecida para rechazar campos nulos antes de llegar
  a restricciones de la base de datos.
- Corregida colisión de componentes OpenAPI entre paginación de listado y búsqueda;
  una prueba comprueba el contrato real de búsqueda con page/has_next/has_previous.
- Advertencia de DNS db al revisar migraciones fuera de Docker: revisión y ejecución
  definitivas realizadas dentro de Compose con PostgreSQL.
- El cálculo del RUT verifica formato y dígito; no acredita existencia o identidad.
- No se eliminaron datos ni archivos existentes. El entorno E2E se detiene conservando
  sus volúmenes. CI remoto y SMTP real siguen pendientes de configuración.

### Próximos pasos

Usar las instrucciones README para crear la cuenta y empresa propias y abrir
/huespedes con una empresa activa. Fase 4: reservas y disponibilidad, únicamente
tras nueva autorización y definición de reglas pendientes de reservas/cancelación.

## Fase 4 — Reservas y disponibilidad

Implementación terminada dentro del alcance autorizado. Retención de pendientes
hasta fecha y hora indicadas por el operador; staff gestiona reservas completas;
bloqueos solo owner/manager; capacidad estricta, al menos un adulto y nuevas entradas
desde hoy en zona de empresa. Precio total manual en CLP, sin pagos ni tarifas automáticas.

### Archivos creados y modificados

- Backend: apps/reservations/{apps,models,intervals,queries,permissions,serializers,
  services,views,urls}.py y migración 0001_initial; tests/test_reservations.py y
  test_reservation_intervals.py. Registro en config/settings.py y config/urls.py.
- Servicio de cabañas valida reducciones de capacidad frente a reservas abiertas.
- Frontend: features/reservations con API tipada/Zod, fechas por zona, validación,
  listado, formulario, ficha, disponibilidad, bloqueos y Reservations.test.tsx.
  Rutas /reservas y navegación en IdentityApp; pantallas cargadas bajo demanda.
- E2E: reservations.spec.ts y cuentas ficticias por dispositivo/rol en e2e_seed.py;
  capturas de reserva/disponibilidad en docs/screenshots.
- compose.yaml, .env.example y vite.config.ts: detección de cambios desde Windows.
- README, DECISIONES, API, MODELO_DATOS, PROGRESO y docs/openapi.yaml actualizados.

### Resultados finales ejecutados

| Verificación | Resultado |
| --- | --- |
| Backend pytest completo, PostgreSQL | 209 aprobadas |
| Frontend Vitest completo, local y Docker | 62 aprobadas |
| Playwright regresión de identidad/cabañas/huéspedes | 10 aprobadas |
| Playwright reservas/disponibilidad escritorio y móvil | 2 aprobadas |
| Ruff check / format | Correctos |
| ESLint / Prettier | Correctos en Docker |
| TypeScript estricto + Vite build | Correctos en Docker, sin advertencia de tamaño |
| Django check | Sin problemas |
| makemigrations --check --dry-run | No hay cambios pendientes |
| reservations/0001_initial | Aplicada en desarrollo y E2E |
| OpenAPI validate --fail-on-warn | Correcto |
| Base de desarrollo: usuarios/cabañas/huéspedes/reservas/bloqueos | 0/0/0/0/0; sin fixtures |
| HTTP backend y proxy /health/ | 200, status ok y database ok |
| HTTP frontend /reservas | 200; flujo autenticado verificado por Playwright |

Pruebas cubren intervalos exclusivos, capacidad, retenciones vigentes/vencidas,
confirmación que revalida, transiciones, cancelación, Decimal, preservación de
historial, bloqueos, aislamiento y CSRF/contexto. Carreras sincronizadas con dos
hilos verifican reserva contra reserva/retención/bloqueo y confirmación de borradores.
Pruebas de zona local y cambios de hora no alteran fechas de estadía.

### Problemas encontrados y resueltos

- Colisión OpenAPI de estados iniciales/completos: conjuntos explícitos con nombres
  separados; validación final sin advertencias.
- Selectores con texto de opciones dentro de sus etiquetas: labels explícitos y
  ayudas separadas, verificadas con navegador y formularios.
- Vite conservaba módulos anteriores al cambiar archivos desde Windows/Docker;
  sondeo configurable cada 500 ms y reinicio del frontend solucionan la detección.
- Primera compilación excedía 500 kB: carga de pantallas bajo demanda, bundle
  inicial final 497,44 kB (150,17 kB gzip), sin aumentar artificialmente el límite.
- La retención caduca sin cambiar automáticamente el estado pending. El backend
  calcula vigencia al consultar/escribir; UI refresca fichas/listado/disponibilidad
  cada 30 segundos mientras visibles. La consulta nunca garantiza una reserva.

### Ejecución y siguientes pasos

Desde la raíz: docker compose up --build -d. Con sesión y empresa activa abrir
/reservas, /reservas/disponibilidad o /reservas/bloqueos. README documenta alta de
cuenta/empresa propias; no se crean credenciales compartidas ni fixtures en desarrollo.
No se eliminaron archivos, registros ni volúmenes. El plan maestro permanece intacto.
Entorno E2E detenido conservando sus volúmenes; servicios de desarrollo saludables.

La Fase 5 (pagos/abonos) requiere autorización y políticas de abonos, sobrepagos,
anulación y devoluciones antes de implementarlas. CI remoto, SMTP real y hardening
siguen pendientes de sus configuraciones/fases. No se adelantaron calendario,
dashboard operativo, reportes, IA ni WhatsApp.

## Fase 5 — Pagos y abonos

Completada dentro del alcance autorizado. Staff consulta, registra y anula con motivo;
sobrepagos muestran saldo a favor. Abonar no confirma ni extiende retención. Cancelar
conserva precio/pagos y excluye de deuda, sin devoluciones automáticas. Reembolsos,
calendario y dashboard no se implementaron.

### Archivos creados y modificados

- Backend: apps/payments/{apps,models,queries,services,serializers,views,urls}.py,
  migraciones 0001_initial y 0002_alter_payment_receipt_file, tests/test_payments.py.
- Configuración y rutas registran payments; consultas/serializers/filtros de reservas
  agregan recibido, saldo, estado de cobro y filtro debt, sin guardar acumulados.
- Frontend: features/payments/{api,validation,PaymentPanel,Payments.test}.ts/tsx;
  ficha de reserva integra historial/formulario/anulación/comprobantes. Listado
  muestra estado de pago y filtro de deuda. Tipos y pruebas de reservas actualizados.
- E2E: payments.spec.ts, fixtures nuevas por dispositivo/rol en e2e_seed.py y
  capturas docs/screenshots/fase5-pagos-{chromium,mobile}.png.
- README, DECISIONES, API, MODELO_DATOS, PROGRESO y OpenAPI actualizados.

### Verificaciones ejecutadas

| Verificación | Resultado |
| --- | --- |
| Backend pytest completo con PostgreSQL | 242 aprobadas |
| Frontend Vitest completo | 74 aprobadas |
| Playwright pagos escritorio/móvil | 2 aprobadas |
| Playwright regresión fases anteriores | 12 aprobadas |
| Ruff / ESLint / Prettier | Correctos |
| TypeScript estricto y Vite build | Correctos en Docker |
| Django check | Sin problemas |
| makemigrations --check --dry-run | Sin cambios pendientes |
| Migraciones payments 0001 y 0002 | Aplicadas en desarrollo y E2E |
| OpenAPI --validate --fail-on-warn | Correcto, exportado |
| HTTP backend y proxy /health/ | 200; status ok y database ok |

Pruebas cubren suma Decimal exacta, sobrepagos, reducción de precio, anulaciones
idempotentes y simultáneas, historial intacto, deuda tras cancelar, timestamps,
permisos de staff, CSRF/contexto, accesos ajenos y archivos privados tras anular.
También verifican reintentos de pago sin duplicado y fallo de comprobante sin
repetir el abono. Concurrencia sincronizada con barrera y dos hilos en PostgreSQL.

### Problemas encontrados y límites

- Ruta de comprobante excedía el límite de FileField por defecto: ampliada a 255
  caracteres mediante segunda migración aditiva, sin eliminar ni reemplazar archivos.
- Fixture API enviaba Decimal como número JSON: corregida a texto decimal; la API
  mantiene rechazo de floats. Registro de fixture importada corregido en pytest.
- Ajustado último aviso de Prettier usando la versión del entorno Docker.
- Comprobantes solo JPG/PNG/WebP, 5 MB/4096 px; PDF no admitido. Se quitan metadatos
  y se conservan píxeles. Almacenamiento privado existente, sin dependencias nuevas.
- Escritura de BD/archivo no constituye transacción distribuida; conciliación de
  posibles archivos huérfanos, backups/retención y límites operativos quedan para
  hardening. No hay limpieza ni borrado automático de archivos.

### Datos, ejecución y siguientes pasos

Las fixtures se escribieron exclusivamente en BD de pytest/E2E. Al cerrar se
detectaron datos introducidos por el usuario en desarrollo: una cuenta, una reserva
y tres pagos; se conservaron sin modificarlos. Plan maestro intacto (SHA256 igual
al inicial). Entorno E2E detenido conservando volúmenes; servicios principales activos.

Iniciar: docker compose up --build -d. Abrir /reservas, seleccionar ficha y usar
Registrar abono; filtro Solo reservas con deuda en listado. README incluye formatos,
permisos y reglas. Fase 6 (calendario/dashboard) queda pendiente de autorización.
No se adelantaron reportes, reembolsos, IA ni WhatsApp. CI remoto y SMTP real siguen
pendientes de publicación/configuración.

## Fase 6 — Registro inicial

Notas históricas anteriores a esta continuación. El cierre verificado que sigue
reemplaza los pendientes de este registro.

- Backend apps/insights: consultas, snapshots de lectura, serializers, vistas,
  rutas y unión de intervalos; sin modelos/migraciones nuevas.
- Tests test_insights_intervals.py y test_insights.py; integración preparada pero
  no ejecutada todavía con PostgreSQL.
- Frontend features/dashboard con API, pantalla /panel y pruebas; cliente de
  calendario preparado. FullCalendar no instalado ni pantalla de calendario terminada.
- Verificaciones locales ejecutadas con dependencias existentes: 8 tests Python
  de intervalos aprobados; 76 tests frontend aprobados; Ruff, Django check,
  TypeScript y Vite build correctos. No equivalen a verificación de consultas PostgreSQL.
- OpenAPI preliminar validado sin advertencias: docs/openapi-phase6-draft.yaml.
  docs/openapi.yaml conserva el contrato verificado de Fase 5 hasta cerrar Fase 6.
- Pendientes: dependencia FullCalendar, pantalla mensual/semanal, pruebas de
  integración de calendarios/cifras/multiempresa y E2E responsive; revisión final
  y export OpenAPI definitivo. No se eliminaron datos/archivos ni se inició Fase 7.
- La revisión automática de aprobación falló por límite de uso al consultar npm;
  no se ejecutó el comando. Se necesita restablecer ese acceso para continuar
  instalación y verificaciones que requieren revisión. No se eludió la aprobación.

## Fase 6 — Completada y verificada (14-10-2026)

### Entrega

- Backend apps/insights: intervalos, consultas coherentes de solo lectura, permisos,
  serializers, endpoints calendar/dashboard y OpenAPI. Sin modelos ni migraciones.
- Frontend features/calendar y features/dashboard: APIs Zod, FullCalendar Standard
  mensual/semanal por cabaña, filtros, colores, enlaces y lista accesible; panel con
  ocupación, cobros, pactado, deuda y crédito separados. Rutas /calendario y /panel.
- Tests backend de intervalos/cifras/fechas/permisos; tests frontend; E2E insights
  escritorio/móvil y cuentas ficticias guardadas exclusivamente en BD E2E.
- package.json y lock actualizados con FullCalendar 7.1.2 y temporal-polyfill.
  README, DECISIONES y docs/openapi.yaml actualizados; capturas ficticias en screenshots.

### Verificaciones ejecutadas

| Verificación | Resultado |
| --- | --- |
| pytest completo con PostgreSQL en Docker | 257 aprobadas |
| Vitest completo | 78 aprobadas |
| Playwright Fase 6, escritorio y móvil | 2 aprobadas, incluidos colores reales |
| Playwright regresiones Fases 1–5 | 13 aprobadas; 1 falló por paginación de fixtures |
| Reejecución de esa regresión móvil tras corregir prueba | 1 aprobada |
| Ruff check y format --check | Correctos, 116 archivos |
| ESLint y Prettier frontend completos | Correctos |
| TypeScript y build Vite final | Correctos, calendario cargado bajo demanda |
| Django check / makemigrations --check --dry-run / migrate --check | Correctos; sin cambios ni migraciones pendientes |
| OpenAPI --validate --fail-on-warn | Correcto; contrato definitivo exportado |
| npm install y npm ci en servicios frontend | Correctos; cero vulnerabilidades informadas |
| Compose principal y /health/ backend/proxy | Tres servicios healthy; HTTP 200, database ok |

Los 16 casos E2E quedaron aprobados entre las ejecuciones indicadas, no en una
única corrida. El caso fallido ya esperaba que su fixture estuviera en la primera
página; ahora recorre las páginas sin borrar datos ni desactivar protecciones.
Se inspeccionaron capturas reales de escritorio/móvil; sin overflow horizontal.
FullCalendar 7 cambió buttonText, colores y clases respecto de APIs anteriores;
adaptado a locale, color/contrastColor, clases públicas y controles accesibles.

Pruebas de cifras concilian Decimal, pagos anulados/canceladas, monedas separadas,
noches recortadas/unidas, retención vencida, hoy local, salida exclusiva e historial
de inactivas. Endpoints rechazan empresa/cabaña ajena y contexto inconsistente.

### Comandos y estado final

```powershell
docker compose up --build -d
docker compose exec backend pytest -q
docker compose exec frontend npm run test
docker compose exec frontend npm run lint
docker compose exec frontend npm run build
```

En esta máquina se usó además --config .docker-local y
--host npipe:////./pipe/dockerDesktopLinuxEngine para acceso a Docker Desktop.
Playwright usa compose.e2e.yaml con proyecto cabanacontrol-e2e, puertos 18001/15174,
semilla protegida tests/e2e_seed.py y navegador instalado en .tools/playwright.
Comandos: npm run test:e2e -- insights.spec.ts; regresiones con
--grep-invert 'calendario mensual/semanal'; reejecución reservations.spec.ts --project=mobile.

Servicios principales activos: http://localhost:15173/calendario y /panel.
Datos de desarrollo conservados: 1 usuario, 1 reserva y 3 pagos, comprobados por
conteos sin leer datos personales. Plan maestro intacto, SHA256 sin cambios.
Entorno E2E detenido conservando sus volúmenes. No se eliminaron archivos ni datos.
Siguiente fase sugerida: 7, reportes/exportaciones, únicamente tras autorización.

## Fase 7 — Completada y verificada (14-10-2026)

Autorizada mediante el siguiente «sigue». El propietario confirmó expresamente:
staff puede consultar reportes y descargar CSV. Owner/manager tienen acceso completo.

### Archivos y entrega

- backend/apps/insights/reports.py: consultas de resumen/reservas/cobros, snapshots
  coherentes, paginación y generador CSV con neutralización de prefijos de fórmulas.
- report_serializers.py y report_views.py: validaciones, contratos OpenAPI,
  permisos de membresía/contexto y exportación auditada. urls.py agrega reports/
  y reports/export/. No hay modelos ni migraciones nuevas.
- frontend/src/features/reports: api.ts, PropertyFilter.tsx, ReportSummary.tsx,
  ReportsPage.tsx y pruebas; ruta lazy /reportes y navegación en IdentityApp.
  Dashboard comparte su schema Zod. No hay dependencias nuevas.
- backend/tests/test_reports.py y test_report_csv.py; e2e/reports.spec.ts;
  cuentas ficticias report-owner/report-staff añadidas a semilla E2E protegida.
- README, DECISIONES, API, MODELO_DATOS y contrato docs/openapi.yaml actualizados.
  Capturas ficticias phase7-reports-chromium/mobile en docs/screenshots.

Reportes usan las definiciones aprobadas de Fase 6. Reservas/canceladas por entrada,
cobros recorded por fecha local de pago; monedas, deuda y crédito separados. Todos
los filtros y exports se restringen a la empresa resuelta en servidor. Datos
actuales, sin reconstrucciones históricas. Cabañas inactivas mantienen historial.
Detalles paginados de 25 filas; export completo hasta 5.000 filas, sin truncamiento.
Resumen conserva identificación de cabaña y una fila por moneda. Sin PII de huéspedes.
CSV UTF-8 BOM/; con celdas citadas y prefijos peligrosos convertidos en texto.

### Verificaciones ejecutadas

| Verificación | Resultado |
| --- | --- |
| pytest completo con PostgreSQL en Docker | 281 aprobadas |
| Tests de reportes/CSV tras añadir metadatos al resumen | 24 aprobadas |
| Vitest completo, ejecución final en Docker | 83 aprobadas |
| Playwright completo, escritorio y móvil | 18 aprobadas en una corrida |
| E2E específico de reportes/descargas | 2 aprobadas; también incluidos en corrida completa |
| Ruff check y format --check | Correctos, 121 archivos |
| ESLint, Prettier completos | Correctos |
| TypeScript y build Vite final | Correctos; /reportes cargado bajo demanda |
| Django check, makemigrations --check --dry-run, migrate --check | Correctos, sin cambios ni migraciones pendientes |
| OpenAPI --validate --fail-on-warn | Correcto, contrato definitivo exportado |
| Compose principal y health backend/proxy | Tres servicios healthy; HTTP 200 con database ok |

Tests verifican conciliación con dashboard, Decimal, canceladas con pagos, anulados
excluidos, medianoches locales y extremos exclusivos, filtros, todas las páginas,
límites, 403/404/409, acceso staff/manager/owner y auditoría sin contenido sensible.
CSV con =,+,-,@, variantes de ancho completo, controles/BOM/espacios, separadores,
comillas y saltos de línea. E2E descargó archivos reales con cuenta staff, 27 reservas
desde la segunda página, canceladas y cobros; rechazó exportación ajena. Capturas
de móvil/escritorio inspeccionadas, sin overflow horizontal ni estados de carga.

### Problemas corregidos y límites

- Ajustada fixture de pago anulado a las restricciones existentes de autor/fecha/
  motivo; middleware impone no-store y las pruebas verifican ese contrato efectivo.
- Corregido registro de fixture importada para evitar shadowing en Ruff.
- Dos archivos de tests formateados con la versión Prettier de Docker.
- Mensaje de límite CSV admite detalles DRF en lista y orienta a reducir filtros.
- No se implementó PDF opcional. No hay archivos públicos ni persistencia de CSV
  en servidor. Protección de CSV original no garantiza conservar escaping al
  transformarlo/guardar/reabrirlo en otras herramientas; referencia OWASP en DECISIONES.
- Automatización remota CI/SMTP y hardening de producción conservan su alcance
  futuro. No se adelantó operación diaria, IA, WhatsApp ni fases posteriores.

### Ejecutar y próximos pasos

```powershell
docker compose up --build -d
docker compose exec backend pytest -q
docker compose exec frontend npm run test
docker compose exec frontend npm run lint
docker compose exec frontend npm run format:check
docker compose exec frontend npm run build
```

Abrir http://localhost:15173/reportes. Aplicar periodo, seleccionar cabaña y tipo,
consultar o usar Descargar CSV. Las fechas mostradas como periodo aplicado son
las usadas por la descarga, aunque se esté editando el formulario de fechas.
Comando específico E2E: npm run test:e2e -- reports.spec.ts; completo:
npm run test:e2e -- --output=test-results-phase7-full, con entorno compose.e2e.yaml.
En esta máquina Docker usó --config .docker-local y
--host npipe:////./pipe/dockerDesktopLinuxEngine; navegadores en .tools/playwright.

Datos principales conservados: 1 usuario, 1 reserva y 3 pagos. Se comprobaron solo
conteos, sin leer PII. Fixtures exclusivamente en BD de pytest/E2E. Plan maestro
intacto (SHA256 igual al inicial). Servicios principales activos; E2E detenido
conservando volúmenes. No se eliminaron archivos ni datos existentes.
Fase 8 (operación diaria) queda pendiente de autorización explícita.

## Fase 8 — Completada y verificada (14-10-2026)

Autorizada con «go» y continuada con «sigue». El propietario confirmó staff con
gestión completa de tareas; limpieza automática al check-out con checklist fijo;
alertas sin bloqueo y WhatsApp editable con apertura/envío humanos.

### Archivos y entrega

- backend/apps/operations: models, services, serializers/views/urls, day y
  day_serializers, whatsapp, apps y migración 0001_initial; nuevo HousekeepingTask.
- reservations/services integra creación automática en la transacción de check-out
  y mejora auditoría antes/después de bloqueos. models/settings fija enums OpenAPI.
- frontend/features/operations: panel diario, APIs Zod, lista/formulario/ficha de
  limpieza, borrador WhatsApp y tests. Rutas /operacion y /limpieza en IdentityApp;
  ReservationDetail incorpora contacto manual y actualización inmediata de alertas.
- tests/test_operations_day.py, test_housekeeping.py, E2E operations.spec.ts;
  semilla protegida añade cuentas/estadías ficticias exclusivamente en base E2E.
- README, DECISIONES, API, MODELO_DATOS y OpenAPI actualizados; screenshots
  phase8-cleaning/operations escritorio y móvil. Sin dependencias nuevas.

### Verificaciones ejecutadas

| Verificación | Resultado |
| --- | --- |
| pytest completo con PostgreSQL | 293 aprobadas |
| Tests nuevos de Fase 8 | 12 aprobadas; incluye concurrencia de dos check-outs y rollback |
| Vitest final en Docker | 85 aprobadas |
| E2E específico de Fase 8 | 2 aprobadas, escritorio/móvil |
| E2E regresión completa | 19 aprobadas; 1 falló en login por límite IP tras corridas repetidas |
| Reejecución solo reservations.spec.ts --project=mobile tras expirar límite | 1 aprobada; 20 casos E2E aprobados entre las ejecuciones |
| Ruff check y format --check | Correctos, 135 archivos |
| ESLint y Prettier | Correctos |
| TypeScript y Vite build final | Correctos; aviso de chunk principal 504,39 kB (151,74 kB gzip) |
| Django check / makemigrations --check --dry-run / migrate --check | Correctos |
| operations/0001_initial | Aplicada en desarrollo y E2E, sin backfill ni cambios a registros existentes |
| OpenAPI --validate --fail-on-warn | Correcto, definitivo exportado |
| Compose principal, backend/proxy health | Tres servicios healthy; HTTP 200 y database ok |

Backend comprueba tarea única por reserva, atomicidad con check-out, responsable
propio activo, acceso staff completo, CSRF/contexto, IDs ajenos, checklist obligatorio,
cancelación con motivo, cierre irreversible conservando fila, alertas retiradas al
completar, mantenimiento y salida exclusiva. Borrador WhatsApp auditado, consulta
mínima y sin documentos/importes/notas privadas. No se envió ningún mensaje externo.
Browser completa checklist, genera enlace de texto editable, crea/cancela tarea manual,
comprueba navegación, ausencia de controles de mantenimiento para staff
y responsive sin overflow. Capturas ficticias inspeccionadas.

### Problemas encontrados y límites

- Corregida prueba que consultaba tarea antes de terminar check-out: espera cierre
  del diálogo/transición, y usa UUID de reserva para distinguir historial acumulado.
  Fixtures conservadas; no se vació base ni se eliminaron tareas de intentos anteriores.
- Enum source/status colisionaba entre dominios: nombres explícitos para reservas
  y limpieza; contrato OpenAPI validado sin advertencias.
- Un archivo se ajustó con Prettier de Docker tras aviso del formatter local.
- Corridas repetidas activaron LOGIN_IP_LIMIT del entorno E2E; se respetó su ventana
  y se reejecutó únicamente el caso afectado (aprobado), sin alterar controles de seguridad.
- Vite informa chunk principal algo mayor a 500 kB; no impide build ni funcionamiento.
  Nuevas pantallas se cargan bajo demanda; optimización adicional en hardening.
- Tareas automáticas vencen al fin del día efectivo de check-out; no se crean
  retroactivamente para reservas ya finalizadas antes de esta migración.
- WhatsApp prepara/copia/abre por acción humana; no guarda cambios del teléfono
  ni consulta APIs Meta. El usuario revisa datos antes de compartirlos externamente.
  No hay IA, voz, Cloud API ni automatización de fases 9A/9B.

### Ejecución y datos

```powershell
docker compose up --build -d
docker compose exec backend python manage.py migrate
docker compose exec backend pytest -q
docker compose exec frontend npm run test
docker compose exec frontend npm run lint
docker compose exec frontend npm run format:check
docker compose exec frontend npm run build
```

Abrir http://localhost:15173/operacion y /limpieza; Preparar WhatsApp en ficha de
reserva. Docker de esta máquina usa --config .docker-local y
--host npipe:////./pipe/dockerDesktopLinuxEngine. E2E con proyecto cabanacontrol-e2e
y compose.e2e.yaml; semilla explícitamente protegida y navegador en .tools/playwright.
Comandos: npm run test:e2e -- operations.spec.ts y npm run test:e2e completo.

Desarrollo conservado: 1 usuario, 1 reserva, 3 pagos y 0 tareas preexistentes/retroactivas;
comprobados solo por conteos, sin leer PII. Plan maestro intacto, SHA256 sin cambios.
Nuevas fixtures únicamente en pytest/E2E. No se eliminaron archivos ni datos.
Servicios principales activos. E2E detenido conservando sus volúmenes e historial.
Fase 9/9A requiere nueva autorización; no se adelantó ninguna funcionalidad de IA.

## Fases 9 y 9A — Propuesta preparada (14-10-2026)

El siguiente «sigue» inició el diseño requerido por secciones 17/18 del plan.
Archivo creado: [PROPUESTA_FASE_9_9A.md](PROPUESTA_FASE_9_9A.md).
El propietario confirmó OpenAI con clave solo backend, staff con gestión/conversión
humana completa y consultas con 90 días operativos/aviso/archivo, sin purga automática.

La propuesta cubre arquitectura, etapas, modelos/migraciones, endpoints, herramientas
de lectura, cuotas, voz voluntaria, revisión humana, privacidad, fallos y pruebas.
Resuelve falta de motor tarifario con precio por confirmar/manual, revalidación
transaccional de draft, ausencia de balances históricos y permisos de huéspedes
existentes. API/modelos/dependencias de IA todavía no implementados.

Se verificó documentación oficial OpenAI de function calling, Structured Outputs,
retención y transcripción usando la habilidad openai-docs. No se instaló SDK, no se
leyeron claves reales, no hubo llamadas a la API ni gastos ni modificaciones de BD.
Solo cambios documentales; no se ejecutaron tests nuevos por no haber cambio de código.
El plan maestro conserva SHA256 inicial. Resultados de Fase 8 siguen registrados
como verificaciones de esa fase, no del asistente. Fase 9B no iniciada.

Pendiente: aprobación del diseño completo para implementar 9/9A; posteriormente
configuración privada de clave/modelos/presupuesto para uso real. Tests se diseñan
sin claves reales mediante proveedor simulado y fixtures ficticias.

## Consolidación del plan maestro a 1.2 — 14-10-2026

Autorizada con «sigamos» tras la revisión documental y recomendación de publicar
una versión 1.2. Alcance: documentación; no implica aprobar la implementación IA.

- Copia íntegra de 1.1: docs/PLAN_MAESTRO_v1.1_2026-10-14.md. Conserva el SHA256
  original 3D5EDAD555267A9CE23A9EB8B808C8B5536280CDE9D4796D65E846166FEBFCDC.
- PLAN_FULL_CODEX_CABANACONTROL.md actualizado a 1.2: reglas confirmadas integradas,
  aprobación única por alcance, fases 0–8 históricas, IA 9.1/9.2/9.3 y 9B futura,
  MVP/piloto/comercial diferenciados y puerta P antes de datos reales desplegados.
- Precio manual/precio por confirmar, saldos actuales, zona por empresa y permisos
  de huéspedes explícitos. Prolongaciones, retención física y ampliaciones opcionales
  permanecen como decisiones pendientes; no se inventaron reglas.
- Propuesta IA mantiene su archivo y contenido funcional con equivalencias de nombres;
  README y DECISIONES actualizados. Su aprobación de implementación sigue pendiente.
- No se modificó código, BD, configuración real o migraciones ni se ejecutaron
  tests de aplicación por este cambio documental. No se eliminaron archivos/datos.
  Las notas anteriores de hash intacto describen el cierre de esas fases; desde
  esta consolidación el maestro cambia de forma autorizada y la copia conserva 1.1.

## Fases 9.1–9.3 — Implementación autorizada en curso

El «sigue» posterior a la consolidación aprueba la propuesta completa
PROPUESTA_FASE_9_9A.md. Se implementan herramientas de lectura, chat, consultas,
conversión humana a borrador y dictado voluntario; 9B y fases posteriores quedan fuera.
OpenAI permanece desactivado por defecto. No se cambió .env real ni se hicieron
llamadas facturables. Las migraciones son aditivas, sin backfill ni borrados.

Primeras verificaciones ejecutadas: 53 tests de herramientas/autenticación/reservas,
24 tests de herramientas/conversión/audio y 85 tests de frontend aprobados.
Son resultados parciales; el cierre y las comprobaciones integrales siguen pendientes.

## Fases 9.1–9.3 — Cierre verificado (14-10-2026)

Alcance aprobado completado: herramientas de lectura/chat, bandeja manual,
conversión humana idempotente a draft y dictado voluntario. No se implementó 9B.

Archivos creados: backend/apps/assistant y backend/apps/inquiries, sus migraciones
0001_initial, tests/test_assistant*.py y test_inquiries.py; frontend/features/assistant,
frontend/features/inquiries y e2e/assistant.spec.ts. Se actualizaron configuración,
.env.example, dependencias Python/lock con hashes, Docker backend con ffprobe,
rutas/navegación, consulta reutilizable de disponibilidad y documentación.

- Backend final: **327 passed**, suite completa pytest, 60,29 s. Incluye aislamiento,
  CSRF/contexto, argumentos no permitidos, privacidad, cuotas concurrentes,
  conciliación Decimal, deadline total del proveedor, audio real/inválido y
  conversión simultánea con rollback ante conflicto. Ninguna llamada externa.
- Frontend final: **88 passed** (14 archivos), con --maxWorkers=2. Lint,
  format:check, TypeScript y build aprobados. Ruff check y format:check aprobados
  para los 165 archivos Python. OpenAPI validate --fail-on-warn y Django check OK;
  makemigrations --check --dry-run: no cambios pendientes.
- E2E: **22 casos distintos verificados**, escritorio/móvil. Suite integral:
  21 aprobados y un fallo inicial de escritorio por arrancar antes del backend.
  Asistente móvil volvió a pasar con respuesta WhatsApp manual y dictado; escritorio
  pasó en su repetición final (8,3 s) después de esperar salud y confirmación de
  empresa. El micrófono, los datos y el proveedor de estas pruebas son ficticios.
  No se presenta la suite integral inicial como una ejecución de 22/22 sin fallos.
- Se corrigieron interferencias de autorecarga y secuencias E2E, sin desactivar
  límites de autenticación. Un timeout de lazy route en tests frontend bajo carga
  se resolvió con espera asíncrona de 3 s y concurrencia acotada; la suite final pasó.
- Build conserva la advertencia de chunk principal **505,51 kB** (151,95 kB gzip).
  Asistente y bandeja se cargan de forma diferida. No se ocultó la advertencia.

Temporizador del proveedor: SDK async bajo asyncio.timeout(25), sin reintentos;
ffprobe hasta 5 s y frontend 35 s. Cancelación local no promete cancelar facturación
del proveedor. Cuota reservada antes de red; uso conocido concilia tokens/coste,
fallos de consumo incierto conservan reservas. API key solo backend, sin .env real
modificado. Falta configurar y comprobar modelos/tarifas/clave para uso real;
la conexión facturable no formó parte de las pruebas autorizadas.

Verificación actual tras encontrar Docker Desktop detenido y restablecerlo:
servicios principales saludables, health backend database=ok y frontend HTTP200.
Solo conteos, sin consultar PII: **1 usuario, 1 reserva, 3 pagos y 0 consultas**.
AI_ENABLED=false y AI_TEST_PROVIDER=false en desarrollo. Migraciones aditivas
aplicadas; ningún backfill, borrado de archivos/datos o modificación de registros
de negocio preexistentes. E2E se detiene conservando volúmenes/historial.
Plan maestro 1.2 conserva SHA256
983BAF00646EBF9B2E833FAC9B3BC44081BB073F32166825CEED52C81A4DED4B;
la copia 1.1 conserva el SHA256 original registrado arriba.

Comandos reproducibles desde la raíz (en esta máquina añadir --config .docker-local
y --host npipe:////./pipe/dockerDesktopLinuxEngine entre docker y compose):

```powershell
docker compose up --build -d
docker compose exec backend pytest -q
docker compose exec backend python manage.py check
docker compose exec backend python manage.py spectacular --validate --fail-on-warn --file /tmp/schema-phase9.yaml
docker compose exec frontend npm run test -- --maxWorkers=2
docker compose exec frontend npm run lint
docker compose exec frontend npm run format:check
docker compose exec frontend npm run build
```

Abrir http://localhost:15173/asistente y /consultas. E2E usa proyecto
cabanacontrol-e2e con compose.e2e.yaml, navegador en .tools/playwright y comando
npm run test:e2e desde frontend; ver configuración/fixtures protegidas existentes.
Próximos pasos: configurar IA real privadamente si se desea, comprobar puerta P
antes de un piloto desplegado y revisar/aprobar separadamente la propuesta 9B.
No se inició ninguna fase posterior.

## Fase 9B — Propuesta preparada (14-10-2026)

El «sigue» posterior al cierre 9.1–9.3 se interpreta como preparar la propuesta
independiente exigida por el plan. Archivo: PROPUESTA_FASE_9B.md. Define recepción
de texto, configuración protegida, worker/outbox PostgreSQL, revisión humana,
consentimiento, aislamiento, límites, fallos inciertos y pruebas simuladas.
No se implementó código ni migraciones, no se conectó Meta ni se enviaron mensajes.
No hubo cambios en datos existentes. No corresponde ejecutar tests de aplicación
por este cambio documental. Documentación actual de Meta pendiente de verificación;
solo se recuperó documentación primaria del SDK oficial antiguo.
Pendiente aprobación del alcance concreto; activación real/despliegue separados.

## Fase 9B — Implementación autorizada en curso (14-10-2026)

El «sigue» posterior a PROPUESTA_FASE_9B.md aprueba 9B.1–9B.3 con pruebas simuladas,
sin conexión real ni envíos/gastos. Cifrado autenticado, webhook firmado, aislamiento,
cola PostgreSQL, revisión humana y conversión existente. Se verificó la política
oficial vigente (23-09-2026): ventana 24 h, plantillas y consentimiento/bajas.
Graph API técnica/versiones/precios siguen pendientes para activación real por
errores de acceso de documentación; no se inventa versión ni tarifa.
Primera suite nueva: 11 pruebas backend aprobadas, sin llamadas a Meta/OpenAI.
Verificaciones integrales, interfaz, documentación y cierre aún pendientes.

## Fase 9B.1–9B.3 — Cierre verificado (14-10-2026)

Alcance aprobado completado: webhook firmado de texto, bandeja por empresa,
credenciales cifradas solo en backend, consentimiento/bajas, plantillas estáticas,
revisión humana explícita y worker/outbox PostgreSQL. Los eventos entrantes crean
consultas sin atribuirlas a un usuario ni ejecutar IA o crear reservas automáticamente.
La conversión a borrador conserva el flujo humano existente.

Archivos creados: backend/apps/whatsapp (modelos, cifrado, proveedor, servicios,
webhook, worker, API y comando whatsapp_worker), sus migraciones 0001–0003,
cuatro archivos test_whatsapp*.py; frontend/src/features/whatsapp y
frontend/e2e/whatsapp.spec.ts. Se actualizaron consultas y su migración 0002,
configuración, dependencias/lock, Compose principal/E2E, fixtures, rutas,
.env.example, README, API, modelo de datos y decisiones técnicas.

- Backend: **350 passed**, suite completa en 92,33 s, sin llamadas externas.
- Frontend: **90 passed**, 15 archivos; lint, formato, TypeScript y build aprobados.
- E2E: **24 casos distintos verificados**. La suite completa aprobó 23 y falló
  únicamente el caso móvil WhatsApp por un selector que coincidía con mensajes
  BAJA históricos. Se corrigió para comprobar el consentimiento de la conversación
  actual. La primera repetición quedó limitada por autenticación; tras su vencimiento
  natural, la repetición móvil final aprobó en 15,9 s. No se desactivaron ni limpiaron
  límites. No se declara una ejecución integral de 24/24 sin fallos.
- Django check, OpenAPI validate --fail-on-warn y migraciones sin cambios pendientes.
  Ruff check y format --check aprobados para 189 archivos Python.
- Build conserva advertencia de chunk principal **505,98 kB** (152,01 kB gzip).
  WhatsApp se carga de forma diferida; la advertencia no se ocultó.

Se corrigieron carreras entre preparación y edición del mensaje, actualización
asíncrona de conversación/consentimiento y revisión de una versión anterior.
El listado de mensajes devuelve conversación y mensajes en una misma instantánea
PostgreSQL; el envío vuelve a validar permisos, revisión, ventana y consentimiento.
Los estados de entrega no retroceden. Un resultado incierto no se reenvía a ciegas;
las credenciales nunca aparecen en respuestas, auditoría ni logs de verificación.

Servicios principales backend/frontend/db saludables y worker activo. Conteos de
negocio conservados: 1 usuario, 1 reserva, 3 pagos, 0 consultas y 0 conexiones,
mensajes o trabajos WhatsApp. WHATSAPP_REAL_ENABLED=false y proveedor simulado
false en desarrollo. No se modificó .env real, no hubo mensajes reales, llamadas
facturables, borrados ni alteraciones de registros de negocio existentes.
Las pruebas usan empresas, números, secretos y mensajes ficticios en otra base.
Se conservan capturas/resultados y volúmenes E2E al detener sus servicios.
El plan maestro mantiene SHA256
983BAF00646EBF9B2E833FAC9B3BC44081BB073F32166825CEED52C81A4DED4B.

Inicio: `docker compose up --build -d`; abrir http://localhost:15173/whatsapp.
Comandos de verificación: los del cierre anterior, cambiando el archivo temporal
OpenAPI a /tmp/schema-phase9b.yaml. En esta máquina usar las opciones Docker
--config .docker-local y --host npipe:////./pipe/dockerDesktopLinuxEngine.

Se verificó la [política oficial vigente de WhatsApp](https://whatsappbusiness.com/policy/)
para consentimiento/bajas, ventana de 24 horas y plantillas. La documentación técnica
actual de Graph devolvió errores de acceso: versión, permisos, contrato de mensajes,
onboarding y costes deben verificarse antes de activar una cuenta real. No se fijó
una versión ni se inventaron tarifas. El catálogo local no aprueba plantillas en Meta.
Activación real 9B.4 y puerta P/despliegue requieren autorización independiente.
No se iniciaron fases 10/11 ni automatización de respuestas.

## Puerta P — Propuesta local preparada (14-10-2026)

El «seguimos» posterior al cierre 9B inicia la preparación del siguiente alcance,
sin configurar cuentas reales ni publicar servicios. Se revisaron Compose,
Dockerfiles, settings, CI y las exigencias de P del plan. Se creó PROPUESTA_P.md
con P.1 contenedores/configuración, P.2 restauración aislada y P.3 operación mínima.
Se corrigió la referencia del README que aplazaba backups/restauración a Fase 12:
el plan exige esos controles antes del piloto. Las notas históricas de fases
anteriores no sustituyen esta exigencia vigente.

Solo cambios documentales: no se ejecutaron nuevas pruebas de aplicación ni se
atribuyen resultados previos a P. No se modificaron servicios, secretos o datos.
Pendiente aprobación de P.1–P.3 locales según la propuesta; puerta P no cumplida,
despliegue y activación real WhatsApp continúan separados.

## P.1–P.3 — Preparación local verificada (14-10-2026)

El usuario autorizó expresamente la propuesta con «autorizo». Se completaron las
etapas locales con datos ficticios; no se acredita ni se autoriza despliegue real.

Archivos nuevos: compose.production.yaml, .env.production.example, Dockerfiles
production de backend/frontend, config/production.py, gunicorn.py y logging seguro;
frontend/deploy con Nginx; deploy/postgres con inicialización de rol dedicado;
lock runtime requirements.lock; comandos/fixtures seed_p_rehearsal y test_production.py;
scripts prepare_p_rehearsal, p_snapshot, p_smoke, p_monitor, p_failure_drill,
p_verify_data y p_ci; configuración Playwright production y sus tests;
docs/PRODUCCION.md. Actualizados lock dev, worker (heartbeat), CI, package.json,
.gitignore, README, propuesta P y decisiones. No se añadieron migraciones de dominio.

- Backend completo: **361 passed**, 54,91 s (350 existentes y 11 casos nuevos).
  Verifica rechazo de configuración insegura, logs sin datos de petición,
  heartbeat solo tras éxito y guard del fixture fuera de la base ficticia.
- Frontend: **90 passed**, 15 archivos, 11,86 s; lint y formato aprobados.
- E2E de frontend compilado bajo HTTPS: **2 passed**, escritorio y móvil, 7,7 s.
  Primer intento falló por esperar una región de la pantalla Empresas en Cabañas;
  corregida la aserción para comprobar empresa/cabaña tras recarga y cookies.
  Los 24 E2E de fases anteriores no se presentan como reejecutados en esta fase.
- Imágenes de producción construidas con bases fijadas por digest; TypeScript y
  build aprobados. Conserva advertencia de chunk principal 505,98 kB (152,03 kB gzip).
- OpenAPI --validate --fail-on-warn, migraciones sin cambios pendientes, Ruff check
  y format --check aprobados (203 archivos Python de backend/scripts).
- check --deploy: W005 y W021 documentadas, sin silenciarlas. No se activa HSTS
  para subdominios ni preload de un dominio que todavía no existe para el piloto.

Ensayo inicial: backup cifrado en 2,83 s, restauración 8,50 s. Se reforzaron guards
para no depender de assert en operaciones de restauración. Repeticiones en destinos
nuevos: 8,59 y 8,75 s. Se verificó rechazo de un destino no vacío, sin sobrescribirlo.
La configuración final separa administrador PostgreSQL y aplicación sin superusuario;
el administrador no aparece en el entorno del backend/worker. Sobre proyecto nuevo
pcheck-secure pasaron migraciones completas, fixture, HTTPS, CSRF, aislamiento,
archivos y validación de roles. Backup final **2,69 s**; restauración independiente
prestore-proof **8,97 s**. Se comprobaron 2 empresas/usuarios/cabañas/reservas/pagos/fotos,
importe pactado 200000,00 CLP y cobrado 50000,00 CLP, relaciones por empresa y hashes
idénticos de las fotos. Estos tiempos son de fixtures pequeños, no RPO/RTO de producción.
La restauración final también pasó recuperación de acceso con correo local ficticio,
confirmación, login y rechazo de reuso del token. No hubo conexión SMTP real.

Problemas corregidos: logging root inicial de Gunicorn impedía arrancar; duplicación
nosniff entre proxy/Django; scripts de pruebas HTTPS necesitaban Origin y el contrato
real de fotos devuelve una lista; selector E2E de empresa tras recarga; espera de
salud tras caída de DB antes de que se actualizara el estado Docker. No se desactivaron
CSRF ni límites de autenticación. Se conservaron capturas/resultados fallidos.

La simulación de caída de BD verificó 503 sin detalles privados, worker unhealthy,
recuperación healthy y ausencia de un marcador sensible en logs de aplicación/proxy.
La configuración CI production-rehearsal conserva artefactos/volúmenes y no sube
claves; ejecución remota de GitHub Actions no verificada. Ensayos no prueban SMTP,
TLS público, Meta/OpenAI reales, carga ni custodia externa de backups.

Entorno principal conservado: health database=ok, 1 usuario, 1 reserva, 3 pagos,
0 consultas/conexiones/mensajes/jobs WhatsApp; AI_ENABLED=false y WhatsApp real=false.
No se modificó .env real ni registros de negocio preexistentes. Ningún borrado,
ningún envío externo ni gasto. Configuración/secretos ficticios de ensayo están
ignorados en .local-production. El plan maestro conserva SHA256
983BAF00646EBF9B2E833FAC9B3BC44081BB073F32166825CEED52C81A4DED4B.

Comandos, límites y checklist: PRODUCCION.md. Pendientes antes del piloto: hosting,
dominio/certificados, SMTP, custodia externa/frecuencia/retención/RPO/RTO, responsables,
privacidad/terceros, aceptación o resolución de prolongaciones y aprobación concreta
del despliegue. El archivo lógico de 90 días no acredita eliminación física.
P.1–P.3 locales completadas; **puerta P para piloto real permanece pendiente**.
No se iniciaron fases 10/11 ni activación real 9B.4.

Comprobación final: simulación de caída repetida sobre prestore-proof con rol no
superusuario, 503/worker unhealthy/recuperación healthy y marcador sensible ausente.
Probe y verificación de importes/archivos/roles aprobados después de recuperar.
Los seis proyectos de ensayo quedaron detenidos con stop, sin borrar contenedores,
backups, claves ni volúmenes. Desarrollo principal sigue activo. Instrucciones para
reabrir el último destino en PRODUCCION.md. El control de logs ensayado corresponde
a aplicación/proxy/worker; logs de PostgreSQL/hosting requieren revisión operativa
antes del piloto. Ejemplos no activan IA/WhatsApp, fijados false en este Compose.

## 11A local — Gestión de colaboradores autorizada (14-10-2026)

Tras aclarar el siguiente alcance, el usuario eligió «Usuarios web: propietario
invita colaboradores y asigna permisos». Autoriza solo gestión de cuenta local,
no la Fase 11 comercial completa ni el despliegue. Excepción de orden documentada
en ALCANCE_USUARIOS_WEB.md; la puerta P sigue pendiente para piloto real.
Invitaciones manuales de 72 h, hash de token, aceptación con contraseña propia o
sesión de la cuenta invitada; roles manager/staff y revocación por empresa.
La entrega protege propietarios, mantiene otros accesos y no envía correos reales.
Migración tenants.0002_invitation aditiva; se aplicó sin cambiar membresías existentes.
Verificaciones integrales en curso. Se conservan resultados iniciales fallidos;
el cierre final registrará las correcciones y las repeticiones necesarias.

## 11A local — Cierre verificado (15-10-2026)

Entrega autorizada completada: pantalla Usuarios solo para propietario, invitación
manual de manager/staff, aceptación con contraseña propia o sesión existente,
cambios de rol, desactivación/reactivación y revocación de enlaces. Propietarios
protegidos; no hay registro público ni primer propietario web, planes/cobros o
transferencia de propiedad. No se implementó la Fase 11 comercial completa.

Archivos nuevos: tenants/invitation_models.py, member_services.py, member_serializers.py,
member_views.py, migración 0002_invitation y tests/test_team.py; frontend/features/team
(API, gestión, aceptación y tests), e2e/team.spec.ts y helper e2e/login.ts;
docs/ALCANCE_USUARIOS_WEB.md. Actualizados rutas/navegación, enums OpenAPI, fixtures
E2E, fechas de pruebas de calendario/reportes, README/API/modelo/decisiones.

Verificaciones finales:
- Backend completo: **382 passed**, 88,28 s. Incluye 21 nuevos casos de invitaciones,
  privacidad, CSRF/contexto/roles, cuotas, caducidad/revocación/reuso, contraseñas,
  cuentas existentes y carreras aceptación/aceptación y aceptación/revocación.
- Frontend completo: **95 passed**, 16 archivos, 32,73 s. Tras ajustes finales de
  presentación/accesibilidad volvieron a pasar los 5 casos específicos del equipo.
- Django check, OpenAPI --validate --fail-on-warn, migraciones sin cambios pendientes,
  Ruff check/format --check (209 archivos Python backend/scripts), lint/Prettier,
  TypeScript y build aprobados. Usuarios y aceptación se cargan de forma diferida.
- E2E: **26 casos distintos verificados** mediante suite inicial y repeticiones.
  Suite inicial: 19 aprobados y 7 fallos. Calendario/reportes de escritorio y móvil
  consultaban fecha UTC, excluyendo pagos que en Chile aún correspondían al día
  anterior: se corrigió el periodo de las pruebas a la fecha chilena del pago,
  reutilizando localHold, sin cambiar cálculos ni reglas de negocio.
  Reservas/equipo/WhatsApp móviles alcanzaron el límite real por IP de autenticación.
  El helper ahora respeta Retry-After y amplía únicamente el timeout de la prueba;
  no borra buckets, suplanta IP ni modifica límites del backend.
  Las repeticiones verificaron los 7 casos fallidos; también el equipo en escritorio
  con la API de gestión definitiva. No se declara una única ejecución de 26/26 sin fallos.
  Se ensaya un 429 ficticio de un segundo en el flujo de equipo para verificar la espera;
  luego se autentica contra Django real del entorno E2E, conservando sus límites.

Se corrigió una regresión detectada por la suite original: el listado histórico de
miembros debía excluir correos. Ese contrato se conserva; la nueva API de gestión
/team/memberships/ los incluye solo para el propietario y la empresa activa.
El primer validador de campos extra se ajustó para retornar 400, no un error interno.
Un ensayo del helper 429 retiraba la ruta mock antes de responder; se corrigió usando
una sola interceptación, sin tocar la aplicación. Capturas y resultados se conservan.
La UI móvil evita desborde con correos largos y exige revisar cada cambio de acceso.

La migración solo añadió la tabla Invitation y sus índices/checks. Conteos principales
conservados: **1 usuario, 0 invitaciones, 1 reserva, 3 pagos, 0 conexiones WhatsApp**;
IA y WhatsApp reales desactivados. No se modificó .env real, no hubo correos/WhatsApp
externos, gastos, borrados ni cambios en cuentas/membresías de negocio existentes.
Las altas/cambios/revocaciones de prueba usaron exclusivamente la base E2E separada.
El plan maestro conserva SHA256
983BAF00646EBF9B2E833FAC9B3BC44081BB073F32166825CEED52C81A4DED4B.

Uso: http://localhost:15173/usuarios, con sesión de propietario y empresa seleccionada.
Crear invitación, copiar y compartir manualmente el enlace; el invitado acepta y
selecciona la empresa al iniciar sesión. Primer propietario/empresa siguen por consola.
Límites/contratos en ALCANCE_USUARIOS_WEB.md y API.md. Puerta P real continúa pendiente;
hosting/SMTP, piloto desplegado, activación real de proveedores y ampliaciones SaaS
requieren sus decisiones/autorizaciones independientes. No se inició Fase 10 ni cobro.

Último cierre de UI/E2E (15-10-2026): 2 casos de equipo aprobados en 38,8 s,
escritorio y móvil, con prueba de Retry-After, API definitiva y presentación final.
Una repetición adicional encontró nombres ficticios repetidos en el historial;
el selector ahora identifica la tarjeta por el correo único del caso, sin borrar
usuarios anteriores. Se volvieron a aprobar altas, cambio manager/staff, revocación,
403 posterior, sesión global conservada y enlace de un solo uso. Capturas nuevas:
screenshots/phase11a-users-chromium.png y phase11a-users-mobile.png, sin enlace/token.
Los 5 tests específicos de frontend volvieron a pasar tras ajustar etiquetas visibles
manteniendo nombres accesibles de controles. Build final: chunk principal 350,15 kB
(106,21 kB gzip) y compartido button 156,50 kB (47,08 kB gzip); sin atribuir una mejora
de carga no medida. Artefactos de todos los intentos se conservan. E2E se detiene
con stop, conservando sus volúmenes; desarrollo principal permanece saludable.

## 11B — Alta inicial web local (15-10-2026)

Autorizada por elección explícita «Alta inicial desde la web: propietario y primera
empresa». Completada en `/registrarse`, con enlace desde login. Usuario normal,
empresa CLP/America/Santiago, membresía owner y auditoría en una transacción.
CSRF, validación de contraseña, campos permitidos, unicidad de correo y cuota propia
de cinco intentos/IP/diez minutos. No modifica cuentas existentes ni inicia sesión
automáticamente. Apellido opcional. Sin migraciones nuevas ni cambios de datos
preexistentes. Desarrollo habilitado; producción fuerza deshabilitado: falta
verificación de correo y decisiones del piloto antes de cualquier registro público.
Detalle: [alta web](ALTA_PROPIETARIO_WEB.md). Este cierre actualiza la limitación
histórica de 11A: el primer propietario ya puede crearse por web en desarrollo.

Validación: suite backend completa 397 aprobados antes del ajuste de apellido;
suite específica final 16 aprobados (incluye la nueva regresión de apellido vacío).
Frontend 95 aprobados; TypeScript/build, ESLint, Prettier, Ruff y OpenAPI sin errores.
E2E final: dos aprobados, escritorio y móvil, 31,5 s; alta con apellido vacío,
confirmación de contraseña, login real, única empresa visible, acceso owner a
Usuarios, sin persistencia local ni desbordamiento horizontal. Primer intento
detectó rechazo del apellido vacío en backend; corregido con allow_blank y regresión.
Artefactos de ambos intentos conservados en frontend/test-results-onboarding*.
No se ejecutó nuevamente toda la suite E2E histórica. Datos ficticios solo en E2E;
ningún correo/proveedor real activado ni archivos o datos eliminados.

## 11C — Perfil y datos de empresa (15-10-2026)

Autorizado por elección explícita «Perfil y empresa: editar nombre y datos de
contacto». Entrega completada en `/configuracion`, accesible desde navegación.
Cualquier usuario activo edita su propio nombre/apellido; propietario de empresa
activa edita nombre comercial, razón social, correo y teléfono de contacto.
No cambia correo de acceso, contraseña, moneda, zona horaria, permisos ni estado.
Contrato y decisiones: [Perfil y empresa](PERFIL_EMPRESA.md).

Backend con lista explícita de campos, CSRF, comprobación de contexto en empresa,
bloqueo de filas y control de edición obsoleta (409). Empresa usa el mismo bloqueo
que gestión de accesos y revalida owner. Auditoría con IDs/acciones y nombres de
campos, sin copiar valores personales o contactos. Frontend refresca sesión y
empresas, separa estado por cuenta/empresa y recarga valores ante conflicto sin
reintentar escrituras. No hay migraciones nuevas ni cambios de `.env`.

Validación final: 417 pruebas backend aprobadas (19 nuevas de esta entrega),
98 frontend aprobadas (3 nuevas); TypeScript/build, ESLint, Prettier, Ruff,
OpenAPI y makemigrations --check aprobados. Maestro conservado (SHA256 983BAF00…).
E2E final: 2 aprobados, escritorio y móvil, 13,9 s; edición de perfil/contactos,
persistencia tras recargar, nombres actualizados en lista de empresas y ausencia
de desbordamiento horizontal. El primer intento móvil no conservó el nombre
esperado tras recargar; no se determinó su causa. Se reforzó la prueba verificando
payload y respuesta PATCH, y pasaron la repetición móvil y el cierre de ambos
tamaños. Artefactos de todos los intentos conservados en test-results-settings*.
La suite E2E histórica no se repitió completa. Salud principal: status/database ok,
ruta frontend 200; registros ficticios solo en E2E. No se eliminaron archivos ni
datos existentes ni se activaron proveedores reales. Este cierre no autoriza
otros alcances de Fase 11 ni despliegue del piloto.

## 11D — Definición comercial preparada (15-10-2026)

El usuario eligió «Planes y suscripciones: definir alcance comercial». Se creó
[PROPUESTA_COMERCIAL.md](PROPUESTA_COMERCIAL.md), exclusivamente documental.
Propone catálogo/capacidad por empresa, separación de pagos de huéspedes, estados,
trial, control concurrente de plazas, transición de empresas existentes, modelos
versionados y entregas 11D.1 local/manual, 11D.2 simulación y 11D.3 activación real.
Incluye archivos/migraciones previstos, riesgos y criterios de aceptación.

Pendientes de respuesta: tres planes 3/8/20 cabañas y 2/5/10 usuarios o plan único;
14/30 días de prueba o alta manual; avisos sin bloqueo o restricción tras gracia.
Son alternativas propuestas, no decisiones aprobadas. Precios, capacidad del trial,
transición comercial y pasarela siguen abiertos. No se inició implementación ni se
activaron límites, caducidades, cobros, contratos o registro público. La puerta P
real continúa pendiente; el maestro no se modificó. Se revisaron referencias locales
de la propuesta; no se ejecutaron suites de aplicación para este cambio documental.

Actualización 15-10-2026: recibidas las tres respuestas. Confirmados planes 3/8/20
cabañas y 2/5/10 usuarios, trial de 14 días y avisos/revisión manual sin bloqueo
automático. Sustituyen las alternativas pendientes del párrafo anterior. Propuesta
y DECISIONES actualizados; no se implementa todavía. Faltan capacidad/continuidad
del trial y transición de empresas existentes para cerrar la primera subentrega;
precios y pasarela siguen pendientes para contratación real.

Segunda actualización 15-10-2026: trial confirmado 1 cabaña/1 usuario; el propietario
ocupa la plaza. Empresas existentes: revisar uso y asignar plan manualmente al
habilitar el módulo. Propuesta actualizada, con separación entre migración y
habilitación; no se inicia trial retroactivo. Capacidad y transición ya no figuran
como pendientes. 11D.1 queda lista para autorización de implementación local sin
importes ni proveedor; 11D.2/11D.3 y activación real siguen fuera del alcance.
Solo documentación actualizada; no se modifican código, datos, límites o cobros.

## 11D.1 — Planes, capacidad y suscripción manual local (15-10-2026)

Autorizada mediante el «sigue» posterior a la propuesta concreta. Implementada
pantalla owner `/plan`, catálogo Inicial 3/2, Crecimiento 8/5, Operador 20/10,
trial manual 14 días 1/1 y uso de cabañas/membresías activas. Sin precio ni cobro.
Migraciones billing 0001–0003 aplicadas: tres modelos, versiones inmutables por
trigger PostgreSQL y constraint de fechas de trial. No backfill de empresas.
Comando manage_subscription review/assign/enable; asignación y habilitación son
pasos distintos, por empresa revisada. Consulta API solo owner/empresa activa.

Control en creación/reactivación de cabañas, aceptación de invitaciones,
reactivación de colaboradores y CLI add_membership. Locks Tenant antes de recurso;
sin exceder última plaza con concurrencia. Sin cuentas parciales al rechazar
invitación, sin segunda prueba, sin suspensión automática al vencer. Auditoría
comercial separada de pagos de huéspedes; no activación de IA ni WhatsApp.

Validación final: 431 pruebas backend aprobadas en 63,18 s (14 nuevas comerciales);
101 frontend aprobadas (3 nuevas). Se volvió a aprobar la suite comercial, 14/14,
tras añadir verificación del inventario CLI final. E2E: 2 aprobados en 9,7 s,
escritorio/móvil, prueba vencida, capacidad 1/1, rechazo de segunda cabaña con 409,
consulta operativa conservada y sin desbordamiento. No se ejecutó toda la suite E2E.
TypeScript/build, ESLint, Prettier, Ruff, OpenAPI y makemigrations --check aprobados.
Primer arranque E2E falló por import local de timedelta que ocultaba al global;
se corrigió conservando un único import y se completó el arranque. La revisión
reforzó la restricción para rechazar fin de trial nulo; prueba PostgreSQL añadida.

Verificación principal solo por conteos: 1 usuario, 1 empresa, 1 reserva, 3 pagos;
0 suscripciones, eventos comerciales o versiones de planes. Flags reales AI y
WhatsApp false. Salud backend/BD ok y frontend /plan 200; maestro sin cambios.
Por tanto, la empresa actual sigue sin asignación/límites hasta revisión manual;
no se creó un administrador de plataforma ni se modificaron sus accesos.
Datos ficticios comerciales únicamente en E2E; volúmenes/resultados conservados.
Comandos/archivos y límites: [PLANES_SUSCRIPCIONES.md](PLANES_SUSCRIPCIONES.md).
Pendientes: revisar/asignar empresas para habilitar, precios, pasarela y posterior
alcance 11D.2/11D.3 con autorización. Puerta P real permanece pendiente.

## Definición de precios y pasarela — propuesta preparada (15-10-2026)

Tras 11D.1 el usuario eligió «Definir precios y pasarela para contratación simulada».
Se creó PROPUESTA_CONTRATACION_SIMULADA.md: tabla de capacidad/precios pendientes,
comparación técnica acotada de Flow y Mercado Pago mediante documentación oficial,
distinción entre simulador local/sandbox externo/producción, flujos y verificaciones
previstos. Recomendación técnica Flow todavía sin elegir; sin afirmar comisiones,
elegibilidad ni contrato. Se solicitaron precios y presentación, pasarela objetivo
y renovación automática consentida o mensualidades manuales.

Pendientes respuestas y política final de periodos/cambios antes de aprobar la
implementación. Solo definición documental: ningún modelo, migración, endpoint,
precio real, credencial, proveedor o cobro modificado. No se ejecutaron suites de
aplicación para este cambio documental; se contrastaron referencias oficiales y
coherencia con planes/trial/política de vencimiento vigentes.

Actualización: confirmados Mercado Pago y renovación automática únicamente tras
contratación/consentimiento explícitos. Se recibió «4500» sin detalle de plan o
impuestos; se pidió aclaración y se mantiene pendiente la tabla de precios. Propuestas
y DECISIONES actualizados. No se inició 11D.2, no se modificaron importes/modelos
ni se realizaron conexiones, registros en proveedores o cobros.

Aclaración posterior: el precio de 4.500 CLP mensuales corresponde a Inicial.
Propuestas actualizadas; solicitados precios de Crecimiento/Operador y presentación
final o neta de los tres. No se modifican código, importes persistidos ni cobros.

Precios completados por delegación posterior: Inicial 4.500, Crecimiento 9.900 y
Operador 19.900 CLP mensuales. Totales finales para simulación, sin recargos ni
desglose fiscal supuesto. Mercado Pago y renovación consentida se mantienen.
Se revisaron referencias públicas oficiales de ofertas de HostManager/HeyAndes;
la decisión es propia y no promete rentabilidad. Propuestas y DECISIONES actualizados,
sin cambiar código, datos o activar servicios. Precios ya no están pendientes para
la simulación; falta cerrar políticas temporales/cambios y autorizar implementación.

## Página de presentación con funciones y precios (15-10-2026)

Solicitud explícita de página con todo el funcionamiento y precios. Implementada
en `/conocer` y como inicio `/` sin sesión. Inicio autenticado sigue en Empresas;
enlace desde navegación y regreso a cuenta conservan la empresa seleccionada.
Diseño responsive verde/crema, portada, demostración interactiva con datos ficticios,
funciones del núcleo, recorrido reserva→pago→salida/limpieza, IA/voz/WhatsApp con sus
condiciones, tres planes, trial 1/1 manual, FAQ y accesos de cuenta. Sin testimonios,
cifras reales, contacto inventado o dependencias/activos externos.

Catálogo visual compartido en planPresentation.ts: 4.500/9.900/19.900 CLP/mes,
mostrados como referencia de simulación en presentación y Plan y uso. Esta nueva
solicitud autoriza mostrarlos, sin crear precio/contrato persistido ni checkout.
La contratación, cobro real y conexión Mercado Pago siguen pendientes. Los botones
de planes explican cómo empezar; registro conserva su validación local y no inicia
trial automáticamente. Sin cambios backend, migraciones, dependencias o `.env`.

Archivos y condiciones: [PAGINA_PRESENTACION.md](PAGINA_PRESENTACION.md).
Validación final: 101 pruebas frontend aprobadas (18 archivos), TypeScript/build,
ESLint y Prettier aprobados. E2E público en desarrollo principal, sin sesión y
comprobando cero POST/PATCH/PUT/DELETE: 2 aprobados escritorio/móvil, 8,2 s; precios,
vistas de demostración, FAQ, ancla de precios, ingreso y raíz anónima. Primer intento
falló por selector exacto del texto del checklist junto a su estado, se corrigió
el selector y se conservaron artefactos. Capturas revisadas en screenshots/landing-*.
E2E aislado adicional: identidad 2 aprobados en 16,9 s (ida/vuelta, empresa activa,
logout y privacidad), billing 2 aprobados en 10,1 s (precios y trial vencido con
límites). Se verificaron 6 casos en tres ejecuciones, no la suite E2E completa.
No se repitieron pruebas backend porque no cambió código de servidor. No hay
despliegue externo, cobros ni activaciones comerciales. Datos/artefactos conservados;
E2E se detiene con stop y desarrollo principal permanece disponible.

## 11D.2 — Alcance final preparado, pendiente (15-10-2026)

El usuario eligió «Contratación simulada: preparar alcance final». Propuesta de
contratación actualizada con frontera local, precios/periodos, cotización 15 min,
consentimiento e idempotencia, resultados simulados, renovaciones por comando,
aislamiento, migraciones/archivos y orden de implementación/verificaciones.
Confirmadas subidas inmediatas, bajadas al renovar y cancelación al final del
periodo; solicitado confirmar fórmula de prorrateo. Solo definición documental;
11D.2 no implementada ni autorizada todavía. Sin código, datos, cargos o conexiones.

Confirmación posterior: prorrateo aprobado, diferencia mensual por tiempo restante,
redondeo al peso con mitades hacia arriba y mismo anclaje; trial→plan inicia mes
completo. Propuesta y decisiones actualizadas. Definición cerrada y alcance 11D.2
local listo para autorizar implementación según sección 9. Solo documentación;
sin cambios de código, migraciones, datos, cobros o conexiones externas.

## 11D.2 local — Contratación simulada completada (15-10-2026)

Autorización: «SIGAMOS» posterior al cierre de la propuesta con prorrateo confirmado.
Implementada ruta owner `/contratacion-simulada`, desde Plan y uso: cotización backend
15 minutos, revisión de total y renovación consentida, clave idempotente, escenarios
aprobado/rechazado/pendiente/incierto y conciliación, compra, subida prorrateada,
bajada al renovar, cancelación al final y reactivación con consentimiento.

Guardas DEBUG + BILLING_SIMULATION_ENABLED + marca explícita de empresa ficticia +
plan/límites revisados. Main conserva flag false; producción fuerza false. Sin SDK,
credenciales o conexión Mercado Pago. Comando billing_simulation prepare/renew y
reintento explícito tras rechazo. Locks por Tenant y revisión de contrato/asignación
observada evitan duplicados y eventos obsoletos. Precios Decimal versionados e
inmutables; periodos calendario UTC con anclaje original, fin exclusivo y fecha
local en UI. 60 cotizaciones/usuario/hora. Cargos simulados separados de Payment.

Seis modelos nuevos, consentimiento con actor/fecha/condiciones; migraciones
0004–0007 aplicadas, aditivas y sin cargar catálogo, marcar o contratar empresas
existentes. Los intentos conservan periodos y precio anterior para auditar prorrateo
tras futuras renovaciones. Se impide reasignación manual sobre contrato simulado
vigente; modificaciones de intención requieren revisión actual y no se sustituyen
en silencio. Sin devoluciones ni bloqueo automático al vencer/cancelar.

Verificaciones finales:
- Backend: 450 aprobadas en 77,92 s; incluye 19 nuevas de simulación. Redondeo,
  medio periodo 2.700 CLP, cargo cero, fin de mes/bisiesto, consentimiento, vencimiento,
  intento ajeno, clave reutilizada con otra cotización, eventos repetidos/tardíos,
  reintento tras rechazo y concurrencia con un solo cargo/contrato.
- Frontend: 104 aprobadas, 19 archivos (3 nuevas); build/TypeScript, ESLint y
  Prettier aprobados. Ruff, OpenAPI versionado/UTF-8 y check de migraciones aprobados.
- E2E final: 2 aprobados en 25,2 s, escritorio/móvil, compra consentida, conciliación
  de incierto, subida inmediata, bajada programada, cancelación y persistencia tras
  recargar, sin overflow ni almacenamiento local. Se conservaron ejecuciones previas;
  no se repitió completa la suite E2E histórica. Renovación/finalización se verifican
  con reloj controlado en pruebas backend; el navegador no altera la hora del servidor.

Problemas corregidos: creación de PlanPrice con str comparado con Decimal antes de
recargar instancia; ahora se crea como Decimal. Un test nuevo tenía un import
faltante (449 aprobados/1 fallido en esa corrida); corregido y suite final 450/450.
Al reforzar trazabilidad se agregó prior_price sin inventar valores para historia
anterior; nuevos intentos preservan el precio de origen y periodos.

Lectura principal por conteos: flag false; 0 empresas marcadas, precios, contratos,
intentos y cargos simulados; 1 usuario, 1 reserva y 3 pagos conservados. Salud de
backend/BD ok en principal y E2E; ruta de simulación 200; maestro sin cambios.
Demo aislada queda encendida para revisión en localhost:15174, con cuentas ficticias
documentadas en [SIMULACION_COMERCIAL.md](SIMULACION_COMERCIAL.md). Cada reinicio
del backend E2E agrega un caso ficticio nuevo sin borrar contratos previos.
No se eliminaron datos/archivos ni se activaron proveedores reales. 11D.3, adaptación
real a Mercado Pago, producción/piloto y verificación de correo siguen pendientes.

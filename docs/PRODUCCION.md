# Puerta P: preparación y operación

P.1–P.3 locales autorizadas el 14-10-2026. Este procedimiento no autoriza despliegue.
Los ensayos usan cabanacontrol_pcheck, proyectos/volúmenes separados y datos ficticios.
IA, WhatsApp real, SMTP externo y gastos siguen desactivados.

## Arquitectura y configuración

compose.production.yaml es independiente: no combinarlo con compose.yaml.
Gunicorn sirve WSGI con 2 workers y 2 threads; timeout 60 s, cierre 30 s.
Las imágenes base de producción están fijadas por digest y dependencias Python por
hash en requirements.lock; development conserva su lock con herramientas de tests.
Nginx sirve dist, termina TLS y enruta API/webhook/health. Solo el proxy publica
puertos, ligados a 127.0.0.1. PostgreSQL/backend/worker comparten una red interna
sin salida a Internet. Una futura habilitación de SMTP/IA/Meta exige decidir una
política de salida y autorizarla; esta configuración no acredita esa conectividad.
Compose fija los flags de IA/WhatsApp reales y proveedores de prueba en false:
cambiar un flag en el ejemplo no activa estos servicios. Su activación es separada.
No hay montaje de código ni endpoint público de media; los archivos pasan por
las vistas autenticadas y filtradas por empresa. No se necesita collectstatic:
no se usa django.contrib.staticfiles, admin o renderer navegable en este proyecto.

La imagen PostgreSQL inicializa, solo sobre volumen nuevo, un administrador separado
y un rol de aplicación NOSUPERUSER/NOCREATEDB/NOCREATEROLE/NOREPLICATION, dueño del
schema public para ejecutar migraciones. La credencial administrativa no llega a los
contenedores de aplicación/worker. El mismo rol de aplicación migra en este escenario;
separar también un rol de migración y limitar DDL en runtime es un endurecimiento futuro.
No aplicar esta inicialización como actualización de un volumen existente: conserva
sus roles, exige revisión explícita y no se modifica automáticamente.

El proxy reemplaza Host/protocolo/IP y elimina cabeceras Forwarded alternativas.
La confianza de Gunicorn/Django en el proxy depende de no publicar el backend y
mantener aislada su red. TLS externo delante de este proxy necesita otra revisión;
no confiar en cabeceras de un cliente. Sin acceso HTTP a sesiones; cookies Secure,
HttpOnly para sesión, CSRF y SameSite Lax. DEBUG=false y validaciones al arrancar.

HSTS es de 3600 s en el ensayo. check --deploy muestra W005 y W021 sin silenciarlas:
includeSubDomains y preload permanecen false porque no se ha elegido un dominio
ni comprobado que todos sus subdominios admiten HTTPS. No solicitar preload ni
ampliar HSTS sin verificar dominio/certificados. Esto es una limitación documentada,
no evidencia de HTTPS público. El certificado ficticio vence en 7 días, no se instala
en el sistema y p_smoke verifica su firma/nombre mediante un almacén local explícito.
Solo Playwright de producción permite ese certificado local; E2E habitual no cambia.

Configuración de ejemplo: .env.production.example. Archivo real dedicado ignorado
por Git; permisos del host restringidos al operador. No incluir claves en imagen,
repositorio, capturas, informes o salida de compose config. Docker/administrador del
host pueden leer variables: acceso al daemon equivale a acceso privilegiado.
Antes del piloto definir custodia/rotación con secretos por archivo o servicio
del hosting y la clave independiente de cifrado WhatsApp, fuera de la base.

Fuentes primarias usadas: [checklist Django 5.2](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/),
[cabeceras del proxy Nginx](https://nginx.org/en/docs/http/ngx_http_proxy_module.html),
[TLS Nginx](https://nginx.org/en/docs/http/ngx_http_ssl_module.html) y
[configuración Gunicorn](https://gunicorn.org/reference/settings/).

## Inicio del ensayo local

Requiere Docker Compose v2, Python 3.12 con requirements-dev.lock y npm/Playwright.
Desde la raíz; en Windows puede usarse backend/.venv/Scripts/python.exe.
En esta máquina añadir `--config .docker-local --host npipe:////./pipe/dockerDesktopLinuxEngine`
entre docker y compose. Los scripts aceptan --docker-config y --docker-host.

```powershell
python scripts/prepare_p_rehearsal.py
docker compose --env-file .local-production/rehearsal.env -p cabanacontrol-pcheck -f compose.production.yaml build
docker compose --env-file .local-production/rehearsal.env -p cabanacontrol-pcheck -f compose.production.yaml up -d --wait db
docker compose --env-file .local-production/rehearsal.env -p cabanacontrol-pcheck -f compose.production.yaml run --no-deps -T migrate
docker compose --env-file .local-production/rehearsal.env -p cabanacontrol-pcheck -f compose.production.yaml run --no-deps -T backend python manage.py seed_p_rehearsal
docker compose --env-file .local-production/rehearsal.env -p cabanacontrol-pcheck -f compose.production.yaml up -d --wait backend whatsapp-worker proxy
python scripts/p_smoke.py
python scripts/p_monitor.py --project cabanacontrol-pcheck
```

El preparador rechaza sobrescribir configuración/certificados; seed rechaza base con
usuarios/empresas. No repetirlos sobre un ensayo existente. Para repetir desde cero,
conservar el ensayo anterior y usar nueva configuración/proyecto expresamente preparado;
no borrar volúmenes. Usuario ficticio p-owner-a@example.invalid (también b), contraseña
P-fictional-passphrase-2026!; solo sirve en esta base, nunca es credencial real.
https://localhost:25443 muestra aviso de certificado local en el navegador.
Pedir --reset-mail cambia la contraseña ficticia de a a P-new-fictional-passphrase-2026!.

## Migración y recuperación

Construir imágenes inmutables y registrar su digest, configuración y versión del esquema
antes de un cambio. Pausar proxy/escrituras y worker, esperar su cierre y crear copia.
Ejecutar migrate una sola vez, comprobar migrate --check/check --deploy y iniciar
aplicación/worker/proxy. El CMD de producción no migra automáticamente.
Probar el cambio en una restauración antes de aplicarlo al piloto real.
Rollback de código solo si el esquema sigue compatible. Restauración exige entorno
nuevo y validación; no hacer rollback destructivo ni reemplazar una base existente.
No cambiar claves de cifrado sin conservar las versiones necesarias para descifrar.

## Copia cifrada y restauración

scripts/p_snapshot.py está limitado a proyectos pcheck/prestore, P_REHEARSAL=true,
base exacta cabanacontrol_pcheck y todos los proveedores desactivados. No usarlo con
datos reales: usa memoria para pg_dump/tar/cifrado, adecuado solo a este ensayo pequeño.
Antes de producción se debe validar tamaño, almacenamiento externo y proceso de streaming.
La copia detiene proxy/backend/worker y espera cierre: no hay escrituras de aplicación
entre dump PostgreSQL y tar de media. No ejecutar comandos de escritura administrativos
durante la ventana; no se bloquea a un administrador de PostgreSQL.

Cada ejecución crea directorio nuevo, cifra ambos artefactos con Fernet y escribe
manifest con hashes de contenido y cifrado. La clave queda en un directorio distinto
fuera del backup, protegido por permisos del host; no es custodia externa ni redundancia.
No copiar la clave junto al backup a un destino público. También custodiar los secretos
de Django, BD y el keyring WhatsApp separados; los secretos no forman parte del snapshot.

```powershell
python scripts/p_snapshot.py backup --project cabanacontrol-pcheck
# Usar las rutas nuevas que devuelve el comando; no son secretos.
python scripts/p_snapshot.py restore --project cabanacontrol-prestore --snapshot RUTA_SNAPSHOT --key-file RUTA_CLAVE
docker compose --env-file .local-production/rehearsal.env -p cabanacontrol-prestore -f compose.production.yaml up -d --wait backend whatsapp-worker proxy
python scripts/p_smoke.py --project cabanacontrol-prestore
```

Backup conserva escritores detenidos, incluso ante error; se reabren solo después de
validar la copia. Antes de iniciar el destino, detener el proxy del origen para liberar
los puertos. Restore verifica cifrado/hashes, exige otra base vacía y media vacío,
pg_restore --single-transaction --exit-on-error sin --clean; rechaza links en tar y
usa filtro data. Ante fallo no abrir servicios ni intentar sobreescribir: usar otro
destino nuevo. Archivos, contenedores auxiliares y volúmenes quedan conservados.
Ver [pg_restore oficial PostgreSQL 17](https://www.postgresql.org/docs/17/app-pgrestore.html).

Al restaurar una cola, jobs working con lease vencido pasan a unknown; no reenviarlos.
Los pending/retry requieren revisar negocio, consentimiento y credenciales actuales
antes de reabrir worker/envíos. No regenerar request_id para forzar reintentos inciertos.
El ensayo no envía mensajes y su cola está vacía; la lógica de leases se prueba en pytest.
Frecuencia, RPO/RTO, retención/custodia externa y responsables siguen pendientes.

## Monitoreo e incidentes

/health/ comprueba BD y devuelve 503 sin detalles de excepción ante fallo; no prueba
SMTP, Meta, OpenAI ni todas las migraciones. Nginx y backend tienen healthcheck.
Worker escribe heartbeat solo tras un ciclo exitoso, con umbral 90 s y 3 fallos de
sondeo cada 15 s. Un proceso detenido o errores persistentes dejan de renovarlo.
Compose restart no reinicia solo por unhealthy: hace falta supervisión/alerta externa.

p_monitor informa estados de los cuatro servicios y conteos globales de cola sin
teléfonos, textos o claves; exit 1 señala estado no saludable. Poner un sondeo al menos
cada minuto y acordar destinatario/SLA antes del piloto. Revisar unknown, failed,
retry y eventos sin procesar. Cuotas locales no acreditan presupuesto del proveedor.
El probe está limitado al ensayo; el operador deberá adaptar destinos tras aprobación.

Logs de aplicación en producción son marcadores JSON sin URL/query, headers, IP, texto ni traceback.
Nginx no guarda access logs ni errores con líneas de petición; su salud detecta fallos.
Esta reducción limita diagnóstico: relacionar estado/horario/versiones y reproducir
con datos ficticios. No habilitar logs completos en producción para investigar PII.
Ante sospecha de fuga: desactivar conexión/proveedor, pausar entradas, preservar evidencia
sin copiar datos sensibles, rotar secretos comprometidos y avisar a responsables acordados.

scripts/p_failure_drill.py detiene únicamente DB del proyecto restaurado ficticio,
comprueba 503, worker unhealthy, recuperación y ausencia de marcador sensible en logs.
No usar interrupciones de este tipo en un piloto activo sin ventana acordada.

Correo del ensayo se escribe en /tmp del contenedor y no se envía. p_smoke --reset-mail
verifica solicitud, enlace, cambio de contraseña, login y token de un solo uso.
Antes del piloto probar SMTP real, remitente/dominio, entrega y recuperación con operador;
no tomar este resultado como prueba de entregabilidad real.

## Checklist de autorización del piloto

| Requisito | Estado actual | Evidencia o decisión pendiente |
|---|---|---|
| Gunicorn/frontend compilado/proxy | Ensayado localmente | Imágenes y HTTPS ficticio |
| Cookies/CSRF/aislamiento/media | Ensayado localmente | p_smoke y pruebas backend |
| Backup y restauración BD+media | Ensayado localmente | Snapshot cifrado y destino independiente |
| Supervisión/errores/worker | Ensayado localmente | Probe y simulación de caída; falta alerta externa |
| Recuperación de contraseña | Ensayado localmente | Correo ficticio; SMTP real pendiente |
| HTTPS público y hosting | Pendiente | Dominio, proveedor, certificados/renovación y responsables |
| Secretos y continuidad | Pendiente | Custodia externa, rotación, frecuencia, RPO/RTO y retención |
| Altas/roles/soporte | Pendiente | Responsables y procedimiento aprobado |
| Privacidad/retención/terceros | Pendiente | Política física y copias; archivo lógico no es borrado |
| Prolongaciones de estadía | Pendiente | Regla o limitación del piloto aceptada expresamente |
| IA/WhatsApp reales | Desactivados | Activación y pruebas de costes/cuenta independientes |
| Despliegue del piloto | No autorizado | Evidencia externa y aprobación final concreta |

No prolongar estadías mediante escrituras SQL ni convertir drafts en retención.
La limitación de prolongaciones debe aceptarse o resolverse antes del piloto; no se
implementa una regla comercial nueva dentro de P. Fases 10/11 continúan fuera.
CI incluye production-rehearsal; su configuración no equivale a ejecución remota.

Cierre local: ensayos detenidos conservando contenedores, backups/claves y volúmenes.
El último destino completo es cabanacontrol-prestore-proof. Para revisarlo, desde
la raíz y con las opciones Docker de esta máquina si corresponden:

```powershell
docker compose --env-file .local-production/rehearsal.env -p cabanacontrol-prestore-proof -f compose.production.yaml up -d --wait backend whatsapp-worker proxy
```

No repetir seed sobre este destino. Usuario b conserva la contraseña ficticia inicial;
a usa la contraseña ficticia nueva tras el ensayo de correo. Detener luego con stop.
Antes del piloto revisar también los logs del servidor PostgreSQL y del proveedor de
hosting: las garantías y prueba de marcadores anteriores son de aplicación/proxy/worker,
no de todos los servicios de una infraestructura externa aún sin definir.

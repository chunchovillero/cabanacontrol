# Propuesta puerta P — Preparación local de producción

Fecha: 14-10-2026. Estado: P.1–P.3 locales autorizadas mediante «autorizo»;
implementación y verificaciones registradas en PROGRESO.md y PRODUCCION.md.

La puerta P del plan exige evidencia antes de un piloto desplegado con datos reales.
Esta propuesta prepara y prueba los componentes localmente con datos ficticios.
No acredita por sí sola HTTPS público, operación del alojamiento ni aprobación del piloto.

## Diagnóstico del repositorio

- Compose principal ejecuta Django runserver y Vite dev, con código montado. Es desarrollo.
- Las cookies Secure dependen de DEBUG; hay configuración de hosts y CSRF, pero falta
  comprobar configuración de producción, proxy y HTTPS con evidencia.
- Existe CI de tests, lint, build y E2E. No hay evidencia de ejecución remota de CI
  en esta revisión, ni prueba reproducible de restauración de BD y archivos privados.
- Hay volumen privado de archivos. Backup solo de PostgreSQL sería incompleto.
- IA y WhatsApp real están desactivados; permanecen así durante estas etapas.
- Archivo lógico a 90 días no elimina datos físicos ni copias. Falta política operativa.

## Alcance que se propone autorizar

### P.1 — Configuración y contenedores de producción

Crear configuración independiente de desarrollo: servidor WSGI de producción,
frontend compilado servido por proxy, rutas REST/webhook del mismo origen,
contenedores sin montajes de código y variables de ejemplo sin secretos reales.
No publicar puertos de PostgreSQL ni servir archivos privados directamente.
Migraciones como operación explícita única, antes de iniciar aplicaciones/worker.
Comprobar hosts, DEBUG, cookies, CSRF y encabezados; documentar cómo se termina TLS.
Ensayar proxy/TLS con certificados locales ficticios, sin modificar Compose de desarrollo.
Validar documentación oficial vigente y fijar las nuevas dependencias al implementar.

Aceptación: imágenes construidas, frontend/API accesibles en proyecto aislado,
check --deploy sin advertencias ignoradas sin explicación, sesión/CSRF/aislamiento
comprobados a través del proxy. Certificado local no acredita dominio público.

### P.2 — Copia y restauración ensayadas

Procedimiento consistente para PostgreSQL y archivos privados, junto con instrucciones
de custodia separada de secretos y claves de cifrado. Nunca imprimir claves ni incluirlas
en el informe. Bloquear escrituras y detener procesamiento durante la copia coordinada;
documentar recuperación de leases/outbox sin provocar reenvíos inciertos.
Restaurar exclusivamente en base/volúmenes nuevos de un proyecto de pruebas,
con datos ficticios, y validar relaciones, archivos y disponibilidad del sistema.
No copiar datos reales ni sobreescribir o borrar volúmenes existentes.

Aceptación: evidencia reproducible de backup/restauración, integridad y tiempos medidos.
Frecuencia, almacenamiento externo cifrado, retención y objetivos RPO/RTO de operación
quedan por acordar; el ensayo local no garantiza continuidad en un proveedor real.

### P.3 — Operación mínima y expediente del piloto

Comprobar health/readiness, supervisión del worker y procedimientos de alertas,
errores, cuotas, incidentes, migración/rollback y recuperación de acceso.
Ensayar recuperación por correo con transporte local ficticio; no enviar correos reales.
Inventariar responsables y políticas pendientes de privacidad, retención física y
terceros; documentar limitaciones de prolongación de estadías sin inventar reglas.
Entregar checklist con estado y evidencia por requisito, sin marcar cumplidos requisitos
que dependen de dominio, SMTP, hosting, responsables o decisiones del negocio.

Aceptación: pruebas relevantes y documentación reproducible, limitaciones explícitas,
lista concreta de requisitos externos y procedimiento de aprobación del despliegue.

## Fuera del alcance

Contratar hosting/dominio, publicar servicios, cambiar DNS, configurar cuentas reales,
modificar .env real, enviar mensajes/correos o efectuar gastos. Tampoco autoriza
Fases 10/11, purgas de datos, funciones comerciales ni automatización de WhatsApp.

## Decisiones que requiere el piloto real

Hosting/dominio y responsable técnico; proveedor SMTP y remitente; responsables de
altas y soporte; custodia de backups/claves y RPO/RTO; política de privacidad/retención;
tratamiento permitido de prolongaciones de estadía. Se pueden preparar P.1–P.3 sin
elegir servicios pagados, usando un único host Compose como escenario de ensayo.
El despliegue real requiere resolver estas decisiones y aprobar un resultado concreto.

## Aprobación

La autorización recibida aprueba exclusivamente P.1–P.3 locales,
en etapas verificables, con datos ficticios y sin acciones externas. No autoriza
despliegue ni activación real 9B.4. La puerta P permanecerá pendiente hasta reunir
la evidencia externa y aprobar el despliegue.

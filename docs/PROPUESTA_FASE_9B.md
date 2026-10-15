# Propuesta Fase 9B — WhatsApp oficial (14-10-2026)

Estado: propuesta aprobada mediante «sigue» tras su presentación; implementación
9B.1–9B.3 completada y verificada. Activación real y despliegue permanecen fuera del alcance.
El «sigue» tras cerrar 9.1–9.3 inicia esta propuesta independiente conforme a
secciones 0/15 del plan. Aprobarla autoriza las etapas siguientes con pruebas
simuladas; no autoriza despliegue, mensajes reales ni gastos de Meta/OpenAI.

## Objetivo y alcance

Recibir consultas de texto mediante WhatsApp Business Platform/Cloud API oficial,
incorporarlas a la bandeja existente y preparar respuestas que una persona revisa
y envía explícitamente. Conservar el flujo manual cuando no haya conexión.

Propuesta inicial: una conexión/número por empresa, configuración solo owner/manager;
staff consulta, gestiona y prepara/envía respuestas revisadas. Nada de respuestas
automáticas en esta entrega. Sin campañas, medios/audio entrante, grupos, scraping,
WhatsApp Web, alta automática de huéspedes, confirmaciones, cancelaciones o pagos.
La conversión a draft conserva el endpoint y las reglas actuales.

## Etapas verificables

1. **9B.1 configuración y recepción simulada:** modelos aditivos, adapter, secretos,
   webhook autenticado, aislamiento, eventos persistidos y deduplicación.
2. **9B.2 procesamiento y bandeja:** worker independiente, consultas por conversación,
   estados de entrega, asignación y revisión humana. Texto recibido no se envía
   automáticamente a OpenAI; análisis existente requiere revisión explícita.
3. **9B.3 envío manual simulado:** outbox, validación de ventana/plantilla, límites,
   consentimiento, autorización humana e indicadores de resultado incierto.
4. **Activación real separada:** comprobar cuenta, número, plantillas, costes, dominio
   HTTPS y puerta P; presentar el envío de prueba concreto y solicitar autorización.

## Arquitectura y garantías

- App de Meta administrada por la plataforma y una conexión propia por empresa.
  Onboarding manual administrativo inicial; Embedded Signup queda fuera.
- Credenciales solo backend, cifrado autenticado con clave dedicada fuera de BD,
  identificador de versión para rotación y sin devolver tokens a React/logs/auditoría.
  Nueva dependencia de cifrado con lock/hash; sin inventar criptografía propia.
- GET webhook valida token y challenge. POST verifica HMAC-SHA256 del cuerpo crudo
  con el secreto de la app antes de interpretar JSON. Exención CSRF limitada al
  webhook autenticado por firma; las operaciones internas conservan sesión/CSRF.
- Resolver tenant desde identificadores de cuenta/número registrados, nunca desde
  texto recibido o un tenant aportado por cliente. Rechazar rutas cruzadas. Una
  firma válida no convierte instrucciones del mensaje en operaciones autorizadas.
- Persistir eventos normalizados mínimos antes de reconocer recepción. Evitar
  guardar payloads completos, headers o secretos. Identificador externo único por
  conexión/tipo; procesar duplicados y estados fuera de orden sin efectos repetidos.
- Cola inicial durable PostgreSQL y worker Django separado en Compose; sin Redis
  ni Celery. Reclamar jobs con locks/leases breves, SKIP LOCKED y backoff acotado;
  red fuera de transacciones. Recuperar workers caídos y limitar concurrencia.
- Outbox único por request_id propio. Idempotencia local no garantiza entrega única
  en Meta: timeout tras aceptar un envío implica estado unknown y revisión humana;
  no reenviar ciegamente. Fallos definitivos y transitorios se clasifican según el
  contrato vigente del proveedor. Nunca presentar accepted como delivered/read.

## Modelo y API propuestos

Módulo backend/apps/whatsapp y migración 0001 aditiva, sin backfill/borrados:
WhatsAppConnection (tenant PROTECT, cuenta/número únicos, secretos cifrados, enabled
false), Conversation (conexión/contacto propio, última entrada válida), WebhookEvent
(ID/tipo/estado mínimos), Message (entrada/salida, texto limitado, estados externos),
OutboxJob (request_id, revisión, intentos/lease/next_attempt_at) y ConsentRecord
(origen, fecha, finalidad, revocación). Inquiry se vincula a conversación sin
confundir mensajes nuevos con duplicados; revisión optimista conserva ediciones.

API /api/v1/whatsapp/: connection GET/PATCH administrativo, conversations GET,
messages GET, messages/prepare POST y messages/send POST con revisión/request_id,
consent POST y jobs GET. Webhook público separado /webhooks/whatsapp/.
Datos y destinatarios propios; 404 ajenos, 409 contexto/revisión, 429 límites,
503 proveedor/configuración. URL Graph API fija y versión configurada/validada;
el cliente no elige host, cuenta ni endpoint remoto.

Frontend: configuración, bandeja/conversación, respuesta editable, revisión de
destinatario/contenido y botón explícito de envío; sin envío al guardar o analizar.
No incluir RUT, saldos, notas privadas ni datos de fichas en respuestas preparadas.
Mostrar ventanas/plantillas, errores y traspaso humano; desactivar conexión detiene
nuevos envíos y evita que jobs pendientes se ejecuten sin verificar el estado actual.

## Políticas propuestas y decisiones de activación

- Aplicar ventana vigente de atención de Meta; fuera de ella solo una plantilla
  aprobada, finalidad válida y consentimiento aplicable. No asumir que disponer
  del teléfono equivale a permiso para iniciar una conversación.
- Plantillas seleccionadas de un catálogo autorizado; no crear/aprobar plantillas
  remotamente ni gestionar facturación en esta entrega.
- Consultas conservan los 90 días operativos; historial/eventos relacionados se
  archivan lógicamente a los 90 días. No purga física sin política/autorización.
  Una entrada nueva puede abrir una nueva consulta; no renueva la antigua.
- Valores iniciales propuestos: texto hasta 4000 caracteres y, si el límite del
  tipo de mensaje de Meta es menor, ese límite; webhook hasta 1 MB; 6 envíos por
  usuario/minuto, 15 por empresa/minuto y 50 por empresa/día. Validar el límite
  del proveedor al implementar. Límites de IA existentes siguen independientes.
- Costes no estimados con tarifas inventadas. Antes de uso real confirmar cuenta
  Meta, propiedad/uso del número, requisitos de la app, región/categorías/precios,
  presupuesto, responsables y política de consentimiento. No solicitar secretos
  por chat ni modificar .env real durante desarrollo.

## Verificaciones y riesgos

Tests sin cuentas reales: firma/challenge, tampering/cuerpo excesivo, dos empresas,
ID ajeno, permisos/CSRF, webhook duplicado, eventos desordenados, crash/lease,
concurrencia/doble click, ventana/plantilla/consentimiento revocado, timeout incierto,
desconexión con jobs pendientes y prompt injection sin cambios de reservas.
E2E móvil/escritorio con adapter simulado protegido como en Fase 9. Migraciones,
pytest, Ruff, frontend tests/lint/build y OpenAPI obligatorios. No atribuir aquí
los resultados de fases anteriores ni declarar entrega real sin evidencia.

Riesgos: cambios del contrato/políticas de Meta, onboarding/app review, restricciones
del número y resultados inciertos de envío. Mitigación: adapter/versionado, revisión
humana, outbox conservador y activación real separada tras puerta P.

Documentación primaria consultada: [webhooks del SDK oficial de Meta](https://whatsapp.github.io/WhatsApp-Nodejs-SDK/api-reference/webhooks/start/)
(challenge y firma). Este SDK antiguo no se propone como dependencia Python.
La página actual de documentación de Meta no pudo recuperarse en esta revisión;
ventanas, permisos, versión Graph, límites y precios quedan pendientes de verificar
contra documentación oficial vigente antes de implementar sus reglas concretas.

## Aprobación

La propuesta concreta lista 9B.1–9B.3 con recepción de texto y envíos exclusivamente
humanos, permisos/límites/archivo anteriores y pruebas simuladas. El «sigue» tras
revisarla aprobó ese alcance; ver cierre y resultados en PROGRESO.md. Activación real, despliegue y automatización de
respuestas requieren autorización independiente y no forman parte de esta propuesta.

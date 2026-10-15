# Contratación simulada — definición previa a 11D.2

Fecha: 15-10-2026. Estado: **11D.2 local autorizada e implementada**.

El «SIGAMOS» posterior a presentar el cierre autoriza la implementación local de
sección 9. Contrato implementado, límites y comandos en
[SIMULACION_COMERCIAL.md](SIMULACION_COMERCIAL.md). Las propuestas de conexión real
siguen fuera del alcance. Ninguna simulación acredita integración Mercado Pago.

El usuario eligió «Definir precios y pasarela para contratación simulada» después
del cierre de 11D.1. Se autoriza preparar esta definición, no programar checkout,
crear cuentas en proveedores, introducir credenciales ni realizar cargos reales.
Posteriormente se autorizó implementar exclusivamente el simulador local de sección 9.

## 1. Reglas ya confirmadas que se conservan

| Modalidad | Cabañas activas | Usuarios activos, propietario incluido | Precio mensual CLP |
| --- | ---: | ---: | --- |
| Trial, 14 días | 1 | 1 | Sin cobro ni contratación automática |
| Inicial | 3 | 2 | 4.500 |
| Crecimiento | 8 | 5 | 9.900 |
| Operador | 20 | 10 | 19.900 |

Trial una vez por empresa. Vencimiento/impago con avisos y revisión manual, sin
bloqueo automático. Empresas existentes con revisión de uso, asignación y
habilitación manual. Suscripciones y cargos SaaS separados de abonos de huéspedes.
La cuenta de cada empresa operadora paga a CabañaControl: las empresas no aportan
sus propias credenciales de pasarela para este cobro de servicio.

## 2. Decisiones confirmadas y precios definidos por delegación

- Pasarela objetivo elegida por el usuario: **Mercado Pago**. Primero simulador
  local independiente; esta elección no crea una cuenta ni autoriza conexiones.
- Renovación mensual **automática solo tras contratación y consentimiento
  explícitos**. Terminar el trial nunca autoriza una renovación ni un cargo.
- Precio confirmado por aclaración expresa: **Inicial, 4.500 CLP mensuales**.
  El usuario delegó completar precios («pon tu precios acordes»): **Crecimiento,
  9.900 CLP; Operador, 19.900 CLP mensuales**. Para la simulación se usarán como
  **totales finales**, sin agregar recargos tributarios al confirmar. La solicitud
  posterior de página pública autoriza mostrarlos en la presentación local, sin
  contratación ni cobros. No se afirma un tratamiento fiscal concreto.

El desglose tributario y documentos fiscales quedan fuera de la simulación y se
validarán antes de venta real. No aplicar una tasa asumida ni afirmar exención.

### Criterio de precios

Se conserva el precio de entrada fijado por el usuario y se reduce el coste por
cabaña al aumentar capacidad: 1.500 CLP en Inicial, 1.237,50 en Crecimiento y 995 en
Operador, calculados con ocupación máxima del plan. Son precios iniciales para
validar demanda, no una conclusión de rentabilidad ni una tarifa media de mercado.
Mantienen el núcleo actual y las cuotas/autorizaciones separadas de IA/WhatsApp.

Se revisaron como orientación las ofertas públicas de
[HostManager](https://www.hostmanager.cl/) y [HeyAndes](https://www.heyandes.com/)
el 15-10-2026. Sus alcances comerciales deben compararse antes de usar sus tarifas
como equivalencia; estos importes son una decisión propia sobre la base de 4.500
del usuario. Comisiones, soporte e infraestructura se validarán antes del lanzamiento.

## 3. Comparación técnica acotada

Consulta de documentación oficial el 15-10-2026. No se compararon comisiones,
liquidaciones, contratos ni elegibilidad de una cuenta particular; no se afirma
que una opción sea más barata ni esté contratada.

| Alternativa | Evidencia oficial | Implicación para el diseño |
| --- | --- | --- |
| Flow | API de suscripciones/cobros recurrentes y endpoints separados de sandbox/producción | Candidato para un adaptador futuro orientado a suscripciones |
| Mercado Pago | Documentación chilena de planes de suscripción, valor/periodicidad y cobro recurrente | Objetivo elegido; falta validar el contrato exacto de integración |
| Simulador local | Componente propio por desarrollar, sin proveedor externo | Permite probar el dominio sin cuentas, red ni cargos |

La recomendación inicial de Flow quedó sustituida por la elección expresa de
**Mercado Pago**. La comparación no certifica costes, contratación ni compatibilidad
completa. Sandbox externo y simulador local son etapas distintas: esta propuesta
no autoriza llamadas siquiera a un entorno de pruebas externo.

Fuentes oficiales:

- [Flow: primeros pasos, credenciales y entornos](https://developers.flow.cl/docs/intro).
- [Flow: referencia API, suscripciones y seguridad](https://developers.flow.cl/api).
- [Mercado Pago Chile: planes de suscripción](https://www.mercadopago.cl/developers/es/docs/subscription-plans/overview).
- [Mercado Pago Chile: crear plan](https://www.mercadopago.cl/developers/es/docs/subscription-plans/create-subscription-plan).

No reutilizar sin revisión el firmado de peticiones salientes como si acreditara
un webhook entrante. El contrato de notificación y consulta de estado se verificará
en documentación oficial del proveedor elegido antes de escribir su adaptador.

## 4. Flujo propuesto para implementar después de aprobar

1. Propietario con empresa seleccionada consulta plan, uso y precio versionado.
2. Revisa importe total, moneda, periodicidad y renovación; acepta expresamente
   las condiciones aplicables. No puede iniciar compras como staff/manager.
3. Backend crea intento idempotente con precio y capacidades calculados en servidor.
   El cliente no puede sustituir empresa, importe, plan ni periodicidad del intento.
4. Simulador local permite ejecutar escenarios de resultado aprobado, rechazado,
   pendiente o incierto. Todo el recorrido lleva rótulo visible de simulación.
5. Retorno de navegador solo muestra seguimiento. La suscripción cambia únicamente
   tras verificar un resultado confiable del adaptador y reconciliar referencias,
   moneda, importe y empresa del intento; no por parámetros de URL.
6. Registrar cargos/eventos SaaS simulados, sin mezclarlos con Payment de huéspedes,
   sin mostrarlos como dinero realmente recibido ni habilitar APIs reales.

La simulación quedaría restringida a desarrollo/pruebas y expresamente deshabilitada
en configuración de producción. Sus eventos nunca se aceptarían como confirmación
de un proveedor real. Ningún campo de tarjeta, ni siquiera ficticio, será necesario
para el simulador propio. No instalar un SDK antes de elegir y aprobar integración.

## 5. Renovación, cancelación y cambios: decisiones y prorrateo

La renovación elegida en sección 2 se aplicará solo a una contratación posterior al
trial, con acción humana explícita. Una aceptación antigua del trial no sirve como
consentimiento de cobros recurrentes. Se conservará versión de condiciones/importe
y fecha de aceptación, sin copiar datos personales innecesarios.

El usuario confirmó: **subidas inmediatas, bajadas al renovar y cancelación al
final del periodo**. La subida solo concede capacidad tras confirmar el cargo
simulado. La bajada solicitada muestra fecha/precio/capacidad futuros; no reduce
la capacidad vigente antes de renovar. Cancelar retira la renovación siguiente,
conserva el periodo vigente y no genera reembolsos automáticos.

Prorrateo confirmado expresamente por el usuario: diferencia entre precios mensuales
versionados × segundos restantes / segundos totales del periodo vigente,
calculado en Decimal y redondeado una sola vez al peso CLP más cercano con
ROUND_HALF_UP. Mantener el anclaje de renovación. Ejemplo con medio periodo
exactamente restante: Inicial→Crecimiento, (9.900−4.500)/2 = 2.700 CLP; siguiente
renovación 9.900. Una subida con importe calculado cero conserva cotización,
aceptación y evento de cambio, sin inventar un cargo positivo.

También confirmado: salir del trial inicia un mes completo del plan elegido.
Para una asignación manual sin periodo contratado se propone el mismo tratamiento:
mes completo y anclaje nuevo; no se
prorratea una prueba gratuita como si hubiera sido pagada. No hay anual, cupones
ni descuentos en esta entrega. No usar importes de frontend para ningún cálculo.

Convención propuesta para el simulador: meses calendario anclados al instante del
primer resultado aprobado, en UTC; conservar día/hora de anclaje originales. Si el
día no existe, usar el último día del mes, recuperando el anclaje original en el
siguiente (31 enero → fin febrero → 31 marzo). Intervalos [inicio, fin), mostrados
en America/Santiago. No son periodos fijos de 30 días. Probar febrero y cambios de
hora; la eventual integración Mercado Pago tendrá que validar su compatibilidad,
sin asumir que esta convención reproduce automáticamente la API externa.

Un resultado rechazado o incierto no crea un periodo ni concede capacidad.
Un evento tardío no se reasigna al periodo actual: se concilia contra su intento
original o se deriva a revisión manual si ya quedó obsoleto.

Al cancelar o fallar renovación se conservan datos y accesos conforme a la política
ya confirmada de revisión manual sin suspensión automática. No se generan
reembolsos, notas tributarias ni cargos negativos como atajo. La conciliación de un
reverso futuro necesitará política propia, no modificar pagos de huéspedes.

## 6. Datos y archivos previstos, no existentes todavía

PlanPrice versionado separado de SubscriptionPlan, cuyas versiones ya son
inmutables en PostgreSQL. El precio futuro no se agregará modificando contratos
de capacidad previos. Moneda explícita, Decimal/numeric y API con texto decimal.
No se rellenarán precios ni se contratará para empresas actuales al migrar.

CheckoutAttempt: tenant, precio versionado, importe, modo simulado/proveedor,
estado, clave idempotente, caducidad y referencia externa mínima.
ProviderEvent: origen, identificador único, comprobación y resultado de aplicación.
SaaSCharge/periodos: independientes de payments, con origen simulado visible.
Guardar referencia/motivo mínimo, nunca payloads completos ni secretos en logs.

Archivos previstos: billing/models, services, adapters/simulated, API/rutas,
migraciones aditivas; frontend/features/billing para revisión y seguimiento;
settings de simulación exclusivamente local, pruebas backend/frontend/E2E y docs.
No se crea una cola o servicio nuevo sin demostrar necesidad. El diseño exacto
de campos y estados se cerrará con las decisiones de renovación/periodos.

## 7. Verificaciones requeridas para la futura implementación

- Precios versionados exactos, moneda, campos manipulados y empresa ajena.
- Sesión/CSRF/contexto; solo propietario contrata para su empresa.
- Doble clic, reintento, caducidad de intento, evento duplicado/desordenado,
  confirmación tardía y timeout incierto sin repetir cargos o conceder dos periodos.
- Retorno falsificado nunca activa plan; importes/referencias ajenas se rechazan.
- Trial una sola vez y sin contratación automática; política de impago conservada.
- Renovación/cancelación mensual y bordes temporales, incluida capacidad excedida
  al cambiar plan, sin borrar ni desactivar recursos existentes.
- Simulador bloqueado en producción; cero conexiones, credenciales o cargos reales.
- Datos/planes previos preservados al migrar; regresiones del núcleo y concurrencia.
- UI responsive con identificación de simulación, importes y fecha efectiva claros.

## 8. Condiciones para cerrar esta definición

Precios totales de simulación definidos por delegación; pasarela, renovación,
momento de cambios, cancelación y fórmula de prorrateo confirmados. El alcance
concreto de sección 9 se autorizó posteriormente y está implementado localmente.
La activación comercial real continúa en 11D.3, condicionada
a puerta P, contrato del proveedor, condiciones económicas y autorización expresa.

## 9. Alcance final propuesto de 11D.2 local

### Objetivo y frontera

Recorrer contratación, renovación, cambio de plan y cancelación con importes
versionados y resultados ficticios, de extremo a extremo. No habrá SDK, cuenta,
credenciales, red, checkout alojado ni notificaciones reales de Mercado Pago.
El simulador propio no se presentará como homologación de ese proveedor.

Activación explícita en desarrollo/pruebas; producción fuerza deshabilitado.
Además, marcar empresas ficticias habilitadas para simulación mediante comando
administrativo auditado. Empresas existentes no se marcan por migración. Sin esa
marca, ninguna operación simulada puede alterar capacidad o suscripciones.
Las pruebas usan exclusivamente empresas ficticias en pytest/E2E, sin habilitar
la empresa principal automáticamente. La interfaz siempre identifica simulación.

La revisión/asignación/habilitación manual previa de 11D.1 se mantiene. La compra
simulada no sustituye esa revisión ni habilita por sí sola límites de una empresa
sin revisar. Una nueva empresa tampoco recibe trial ni contrato automáticamente.

### Operaciones incluidas

- Catálogo con precios backend versionados (4.500/9.900/19.900 CLP) y condiciones.
  Datos monetarios Decimal/numeric y textos decimales en API; sin impuestos supuestos.
- Cotización de compra o subida, identificador UUID, vigencia de 15 minutos e
  importe calculado usando el instante cotizado. La cotización conserva referencia
  de revisión del contrato; cambios del contrato la invalidan, sin cargos ocultos.
  Después de vencer exige otra revisión; el tiempo de espera dentro de su vigencia
  no recalcula silenciosamente el importe aceptado.
- Confirmación owner con CSRF/contexto y aceptación explícita del total, precio,
  renovación y versión de condiciones. Solo lectura de catálogo para contratación
  autorizada; los colaboradores no obtienen permisos comerciales por su rol operativo.
- Intento idempotente y un único intento sin resolver por empresa. Misma clave y
  mismo contenido devuelve intento existente; misma clave/datos distintos: 409.
  Un timeout incierto se concilia antes de abrir otro intento equivalente.
- Resultados del simulador: aprobado, rechazado, pendiente e incierto; reentrega y
  conciliación controladas. Cambiar la URL/retorno no modifica estados de dominio.
- Primera compra aprobada inicia periodo y capacidad elegida; compra fallida
  conserva contrato/capacidad anterior. Origen simulado persistente y visible.
- Renovación automática consentida modelada mediante comando de simulación que
  procesa vencimientos en empresas ficticias, sin daemon ni cargos externos. Un
  intento por contrato/periodo, incluso si se repite el comando. Solo aprobación
  verificada aplica el siguiente periodo/capacidad; fallos conservan operación y
  aviso de revisión manual, sin repetir el trial.
- Subida inmediata con fórmula confirmada de sección 5; sin cambiar anclaje.
  Bajada programada aplicada únicamente al aprobar la renovación de su nuevo precio.
  Sobreuso conserva recursos; el límite bloquea únicamente aumentos posteriores.
- Cancelar al final del periodo desactiva renovación futura; al vencer marca
  finalizado sin borrar datos ni suspender automáticamente operación. Permite
  retirar cancelación antes del fin mediante consentimiento explícito renovado.
- Toda modificación de intención se confirma con versión observada: un evento
  antiguo no revoca una cancelación, sustituye otro cambio ni modifica un contrato
  nuevo. Conflictos de intención se muestran para revisión, sin resolverlos en silencio.

### Datos, archivos y migraciones

Extender billing con PlanPrice inmutable, contrato/períodos simulados,
CheckoutAttempt, eventos del adaptador y cargos SaaS; conservar origen/referencias,
estado de conciliación y revisión. TenantSubscription conserva la proyección de
capacidad operativa y las reglas de 11D.1; no se reescribe SubscriptionPlan.
Los cargos simulados nunca se suman como dinero cobrado en reportes de huéspedes.

Migraciones aditivas de estructura, sin asignar precios a contratos previos,
contratar, marcar empresas o activar simulación. Comando explícito para preparar
catálogo de prueba/versiones según límites existentes; no modificar planes inmutables.

Archivos: backend/apps/billing/models, services de contratación/periodos/precios,
adapters/simulated, serializers/views/urls, migrations y comandos; config/settings
y production; frontend/features/billing para revisión/resultado/gestión de contrato,
lib/planPresentation para enlazar información pública con el catálogo aprobado;
tests backend/frontend/E2E y README/API/MODELO_DATOS/DECISIONES/PROGRESO.

### Orden verificable dentro del alcance

1. Precios y dominio temporal: esquema, migraciones y pruebas unitarias/PostgreSQL.
2. Cotización, consentimiento, intento y resultado simulado: API y pantalla, E2E
   de compra aprobada/rechazada y retorno falso sin efectos.
3. Subida prorrateada, renovación, bajada y cancelación: comandos deterministas,
   concurrencia, eventos repetidos/desordenados y UI con fechas efectivas.
4. Regresiones, esquema OpenAPI, documentación y cierre. No avanzar a 11D.3.

### Riesgos y aceptación adicionales

- Los locks deben conservar orden Tenant → contrato/intento → recurso, coordinados
  con 11D.1. Confirmar dos veces no duplica periodo, cambio de capacidad ni cargo.
- Prorrateos sobre un periodo de duración real, redondeo al peso, importe cero,
  subida sucesiva y cotización vencida; ninguna diferencia calculada en float.
- Primera contratación desde trial vigente/vencido o asignación manual, sin
  consumir otra prueba ni alterar datos de la empresa no autorizada para simulación.
- Anclaje original, fin exclusivo, febrero/año bisiesto y visualización chilena.
- Cancelación a la vez que renovación: decisión coherente por fecha efectiva y
  revisión, con resultado trazable. No ocultar cargos/estados inciertos.
- Eventos falsos, referencias cruzadas y origen simulado frente a origen real:
  rechazados sin conceder acceso ni crear movimientos de pagos de huéspedes.
- Ningún test usa tarjetas, credenciales reales, datos personales o llamadas externas.

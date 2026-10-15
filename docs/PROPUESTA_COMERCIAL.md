# Planes y suscripciones — propuesta de alcance 11D

Fecha: 15-10-2026. Estado: **11D.1 autorizada e implementada localmente; 11D.2/11D.3 pendientes**.

El «sigue» posterior a la propuesta concreta autorizó 11D.1. Contrato implementado
y comandos en [PLANES_SUSCRIPCIONES.md](PLANES_SUSCRIPCIONES.md); los apartados
posteriores conservan el diseño comercial futuro, no implican cobros habilitados.

Solicitud autorizada: «Planes y suscripciones: definir alcance comercial».
Este documento define una propuesta, no contratos implementados ni precios de venta.
El plan maestro se conserva. 11A (colaboradores), 11B (alta local) y 11C (perfil)
están cerradas; la puerta P para piloto real continúa pendiente.

## 1. Objetivo comercial

Cobrar una suscripción a cada empresa operadora por usar CabañaControl. Una cuenta
con varias empresas tendría una suscripción independiente por empresa; sus roles
no se comparten. La suscripción nunca concede acceso a otra empresa.

Los abonos de huéspedes y saldos de reservas siguen en el módulo payments.
La facturación del SaaS tendrá modelos y conciliación separados. No se registrará
una mensualidad SaaS como pago de una reserva ni se compensarán ambos saldos.

## 2. Catálogo por capacidad confirmado

El usuario eligió tres planes por capacidad. Los nombres siguen siendo provisionales:

| Plan | Cabañas activas | Membresías activas, incluido propietario | Precio mensual CLP |
| --- | ---: | ---: | --- |
| Inicial | 3 | 2 | 4.500 |
| Crecimiento | 8 | 5 | 9.900 |
| Operador | 20 | 10 | 19.900 |

La alternativa de plan único no se incorpora. Precios de simulación completados
por delegación del usuario: importes mensuales finales, sin recargos en el checkout
simulado. Se muestran en la página local expresamente solicitada; despliegue
comercial, desglose tributario y cobros reales continúan pendientes.

Propuesta funcional para todos los planes: núcleo operativo actual, calendario,
pagos de huéspedes, reportes/CSV, limpieza y gestión de colaboradores. Evitar
limitar el historial o cobrar por cada reserva en esta primera versión. Esto no
promete reservas, archivos ni capacidad de procesamiento infinitos: se mantienen
las validaciones, cuotas técnicas y límites existentes.

IA, voz y WhatsApp oficial no se ofrecerían como consumos ilimitados incluidos.
Su activación, proveedor, presupuesto y posibles cargos adicionales requieren
alcance separado. Tener un plan superior no habilita flags globales ni conexiones
reales. El plan comercial no reemplaza permisos, consentimiento ni cuotas de IA.

Impuestos aplicables, descuentos, periodicidad anual y complementos siguen fuera
del alcance aprobado. Mercado Pago es la pasarela objetivo elegida; la simulación
será local. Se autorizó después su presentación informativa local; los cobros
reales y el despliegue comercial requieren autorización independiente.

## 3. Decisiones de negocio confirmadas

1. Tres planes: 3/8/20 cabañas activas y 2/5/10 usuarios activos por empresa.
2. Trial de 14 días, una vez por empresa, sin tarjeta ni contratación automática.
3. Vencimiento e impago: avisos y revisión manual, sin bloqueo automático inicial.
4. Capacidad de trial: **1 cabaña activa y 1 usuario activo**, incluido propietario.
   Es una modalidad de prueba separada de los tres planes comerciales. No permite
   activar colaboradores adicionales mientras la plaza esté ocupada por el propietario.
5. Empresas existentes: asignarles un plan manualmente al habilitar el módulo,
   revisando previamente su uso. No asignar un plan por defecto mediante migración.

Confirmación expresa del usuario el 15-10-2026. Estas decisiones fijan el diseño;
11D.1 se autorizó después; esto no autoriza implementar toda la propuesta.

La prueba dura 14 días con capacidad 1/1, sin tarjeta, contratación ni cobro
automáticos al terminar. Empieza al activar expresamente
la prueba, no al visitar una página ni al crear un colaborador. Instantes UTC y
fin exclusivo; en pantalla fecha y hora en la zona de la empresa. Una duración en
días de prueba no redefine la duración de una mensualidad comercial.

Al vencer, se mantiene la capacidad 1/1 hasta revisión manual, siguiendo la política
confirmada de no suspender automáticamente la operación; no se convierte en plan
pagado ni reinicia la prueba. Las condiciones económicas continúan pendientes.
Crear otra empresa para repetir pruebas necesita una política
de abuso/comercial antes de habilitar autoservicio público.

## 4. Límites de capacidad y degradaciones propuestas

- Cabañas: contar Property.active de la empresa. Crear activas o reactivar consume
  capacidad; editar una activa existente no consume otra plaza. Inactivas conservan
  historial. El límite no modifica las reglas actuales de desactivación o reservas.
- Usuarios: contar Membership.active por empresa, incluido cada propietario. Una
  misma persona ocupa una plaza en cada empresa. Deshabilitar una cuenta global no
  libera por sí solo la membresía: el propietario debe desactivar ese acceso.
- Invitaciones: no reservar plaza al emitir el enlace; comprobar capacidad al
  aceptarlo/reactivar la membresía. El invitado verá un error claro si entretanto
  se agotó la capacidad. Se mantienen las cuotas técnicas de invitaciones vigentes.
- Nunca eliminar ni desactivar automáticamente usuarios/cabañas por reducir plan.
  Si el uso supera el nuevo límite, informar exceso y bloquear únicamente las
  operaciones que aumenten ese recurso; conservar edición, consulta e historial.
- Si se aprueba baja de plan diferida, entra al siguiente periodo contratado. El
  exceso se resuelve desactivando recursos permitidos o cambiando plan; no se borran
  registros. Los límites actuales se revisan también en activaciones y altas por CLI.
- Bloqueo transaccional por empresa al contar y crear/reactivar: dos solicitudes
  simultáneas no pueden usar la última plaza. Definir orden de locks compartido con
  propiedades/membresías y probarlo antes de habilitar límites.

Las reglas técnicas de capacidad se implementaron en 11D.1; solo se aplican tras
habilitación expresa por empresa. No se asignan contratos por migración. La transición
confirmada exige inventario de uso y asignación manual antes de habilitar límites.

## 5. Estados de suscripción propuestos

Separar estado financiero, capacidades del plan y permisos del usuario.

| Estado | Significado | Efecto propuesto |
| --- | --- | --- |
| Sin asignación comercial | Estado transitorio previo a habilitación | Revisar uso y asignar plan manualmente antes de habilitar |
| Prueba | Trial activado, antes de trial_ends_at | Capacidad de trial aprobada |
| Activa | Periodo contratado vigente | Capacidad contratada |
| Vencida / pago pendiente | Trial terminado o periodo sin renovación válida | Aviso y revisión manual; sin bloqueo automático |
| Finalizada | Cancelación efectiva al final del periodo | Conservación de datos y acceso según política elegida |

`cancel_at_period_end` será una intención separada; pedir cancelación no termina
anticipadamente un periodo vigente. Solicitar un cambio no lo confirma ni autoriza
un cargo. Reintentar o actualizar el navegador tampoco renueva una suscripción.

La revisión manual confirmada permite continuar operando con aviso explícito de
vencimiento; no se mostrará «pagada» o «activa» sin confirmación. No se aplican siete
días de gracia ni modo de solo consulta. Una futura restricción requerirá otra
propuesta que cubra estadías en curso. Consulta y exportación respetarán siempre
permisos, aislamiento y privacidad existentes. Los límites de capacidad del plan
son una regla distinta: no se suprimen automáticamente por vencer el trial.
La prueba vencida conserva capacidad 1/1 y aviso hasta una asignación manual.

Toda cancelación conservará datos. Retención física y eventual eliminación siguen
necesitando política y autorización propias. Suspensión comercial no será un atajo
para desactivar Tenant.active ni invalidar sesiones globales de otras empresas.

## 6. Datos y arquitectura previstos

Módulo nuevo `backend/apps/billing/`, separado de payments:

- SubscriptionPlan: código, versión, nombre, límites y capacidades. Versiones
  contratadas inmutables; ocultar una versión a nuevas ventas no altera contratos.
- TenantSubscription: una referencia actual por empresa, plan/versionado,
  origen manual/simulado/proveedor, fechas de prueba/periodo, cancelación diferida
  y estado. No inferir «sin pago» de la ausencia de una fila histórica.
- SubscriptionEvent: historial de cambios, actor, motivo y referencias mínimas.
  Un administrador de plataforma podrá gestionar lo comercial con autorización
  y auditoría, sin acceso implícito a huéspedes/reservas ni editar sus membresías.
- En una etapa posterior, CheckoutAttempt, ProviderEvent y cargos/ajustes SaaS
  separados. Referencias externas únicas por proveedor, deduplicación e historial.

Precios futuros: Decimal/numeric, moneda explícita y representación decimal en API;
ningún float ni dato de tarjeta. Un catálogo sin precios no crea cargos ficticios.
Periodos de cobro definidos por el contrato/proveedor, no «mensual = 30 días».

Servicio central de capacidades en backend. Frontend solo presenta límites y uso;
no decide elegibilidad. Aplicar a todos los puntos de alta/reactivación existentes,
incluidos invitaciones, gestión de membresías, propiedades y comandos autorizados.
Un modelo de IA o webhook de WhatsApp nunca modifica planes ni cobros.

Transición aditiva: no cambiar empresas, cuotas técnicas ni flags existentes al
aplicar esquema. Migraciones de estructura sin contratar, suspender, expirar o
crear cobros para empresas actuales. Asignación comercial explícita y auditada.
Para habilitar límites: inventariar cabañas y membresías activas por empresa,
presentar el uso sin PII innecesaria y asignar un plan expresamente. No iniciarles
un trial retroactivo. La habilitación se detiene si quedan empresas sin revisar;
si ninguna capacidad cubre su uso, informar y resolver comercialmente sin borrar
ni desactivar recursos. Construir/aplicar el esquema no equivale a habilitarlo.

## 7. Entregas pequeñas para autorizar después

### 11D.1 — Catálogo, capacidad y suscripción manual local

Objetivo: probar reglas comerciales con datos ficticios sin proveedor ni dinero.
Subentrega autorizada con «sigue» e implementada localmente. Precios y pasarela
no bloquean esta entrega manual sin importes/cobros. La habilitación es por empresa
tras revisión y asignación, sin activar automáticamente otras empresas.

Incluye modelos/migraciones aditivas, servicio de capacidades, asignación manual
auditada mediante comando interno, consumo/límites y pantalla owner «Plan y uso».
Trial 14 días, capacidad 1/1 y aviso al vencer sin suspensión automática. Empresas
existentes se revisan y asignan manualmente antes de habilitar límites; migrar
esquema no cambia su operación. Sin permisos nuevos para frontend del superadmin.

Archivos previstos: billing/models, services, serializers, views, urls, migrations;
registro en config; integración en properties/services, tenants/member_services,
CLI de membresías y alta de empresa según política aprobada. Frontend features/billing
y navegación. Pruebas backend/frontend/E2E, README/API/MODELO_DATOS/PROGRESO.

No incluye checkout, cobros, pasarela, verificación de correo ni activación pública.
No requiere secretos reales ni una tarea recurrente adicional si las fechas pueden
evaluarse al consultar/operar. Notificaciones programadas se diseñan por separado.

Aceptación:

- Empresa A no lee ni cambia plan, uso o historial de B; staff no obtiene datos de
  facturación por acceder a reportes operativos.
- Propietario incluido en plazas; invitación vigente sin plaza rechazada al aceptar,
  con rollback completo y sin crear usuario/membresía parciales.
- Última plaza concurrente, reactivación, downgrade con exceso y caminos CLI probados
  con PostgreSQL; sin degradar locks ni reglas de reserva existentes.
- Fechas de trial y borde exacto verificados, sin renovación por sesión o reintento.
- Trial 1/1: propietario consume la única plaza; la segunda cabaña activa y una
  aceptación de invitación sin plaza se rechazan sin efectos parciales. Al vencer,
  continúan edición y operación existentes, con aviso y la misma capacidad.
- Empresas anteriores mantienen operación al aplicar migraciones; no cambian
  reservas, pagos de huéspedes, accesos o estados. Antes de habilitar límites,
  informe de uso y asignaciones manuales auditadas; no se asigna trial retroactivo.
- Dinero exacto si se agregan importes aprobados; UI española, CLP, responsive,
  errores claros, contrato OpenAPI y pruebas de permisos/concurrencia.

### 11D.2 — Contratación simulada y diseño de proveedor

Solo con nueva autorización y pasarela/contrato elegidos. Probar checkout simulado,
retornos y eventos duplicados/desordenados, rechazo, demora, idempotencia y
conciliación. Una URL de retorno o parámetro del navegador nunca acredita pago.
Autenticación del evento y confirmación del proveedor se definen con documentación
oficial al seleccionar la integración. No consumir ni almacenar payloads completos
innecesarios. Renovación, cambios de plan, prorrateo, reversos y cancelación requieren
reglas concretas, no supuestos del SDK.

### 11D.3 — Activación comercial real

Requiere puerta P, alta pública con correo verificado si se ofrece autoservicio,
dominio/TLS/SMTP, contrato y cuenta del proveedor, importes finales, tratamiento
tributario/comercial validado, soporte/recuperación, backups/retención y aprobación
expresa de despliegue/activación. No se implementa ni contrata en esta definición.

## 8. Preguntas pendientes antes de programar

Decisiones restantes; no volver a pedir las tres ya confirmadas:

- Precio por plan, presentación de impuestos, fecha/ciclo de contratación y moneda.
- Quién puede conceder excepciones de capacidad y cómo caducan; propuesta inicial:
  sin excepciones ocultas, cambio explícito auditado de contrato.
- Efecto de cancelación sobre operación en curso; restricción automática excluida
  de esta primera entrega por decisión del usuario.
- Política de upgrades/downgrades y ausencia/presencia de prorrateo antes de checkout.
- Proveedor/pasarela y medios de pago; hasta entonces todo será local/simulado.

Capacidad de trial y transición de empresas ya están resueltas en sección 3. Para
11D.1 se propone asignación y cambios exclusivamente manuales, efectivos al ejecutar
la acción auditada, sin importes, cargos, prorrateo ni cancelación de contratos
pagados. La cancelación diferida y los ciclos comerciales de sección 5 son diseño
futuro, no requisitos a implementar en esta primera subentrega local. Activación
del trial solo manual; cambiar de plan no permite obtener una segunda prueba.

Esta propuesta no modifica el alcance aprobado de pagos de huéspedes, no declara
precios de mercado, no realiza comparación de proveedores ni asesoría tributaria.
Las decisiones económicas finales se validarán con el responsable comercial.

Actualización de definición posterior a 11D.1: el usuario eligió Mercado Pago y
renovación mensual automática solo tras contratación/consentimiento explícitos.
El usuario aclaró que 4.500 CLP mensuales corresponden a Inicial y delegó completar
los otros precios: Crecimiento 9.900 y Operador 19.900 CLP, totales mensuales para
simulación. No se incorporan aún al catálogo implementado. Detalles y pendientes en
[PROPUESTA_CONTRATACION_SIMULADA.md](PROPUESTA_CONTRATACION_SIMULADA.md).
La elección no autoriza integración ni activación real.

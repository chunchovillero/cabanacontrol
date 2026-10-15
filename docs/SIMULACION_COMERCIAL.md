# Contratación simulada local — 11D.2

Autorizada con «SIGAMOS» después de presentar el alcance cerrado y confirmar
prorrateo. Implementación propia, sin SDK, credenciales, sandbox ni llamadas de
Mercado Pago. Mercado Pago sigue siendo el objetivo de una integración posterior.
Todos los contratos, eventos y cargos de este módulo son simulados.

## Revisar desde la web

Ruta: `/contratacion-simulada`, enlazada desde **Plan y uso**. En desarrollo
principal: http://localhost:15173/contratacion-simulada. Se requiere propietario,
empresa seleccionada y habilitación explícita; por defecto muestra deshabilitado.

Demostración aislada preparada en http://localhost:15174/ingresar:

- Cuenta ficticia: `e2e-simulation-chromium@example.invalid`.
- Contraseña de fixture, sin validez externa: `E2E-fictional-passphrase-2026!`.
- Seleccionar la última «Empresa simulación chromium …», entrar a Plan y uso y
  seguir «Revisar contratación simulada». La última prueba dejó un contrato de
  Crecimiento con bajada a Inicial programada y cancelación al fin del periodo.
- Puedes retirar la cancelación con consentimiento, retirar el cambio programado
  o revisar los intentos aprobados. Son pruebas, no dinero recibido.

Para reiniciar servicios aislados sin borrar historiales:

```powershell
docker compose -p cabanacontrol-e2e -f compose.yaml -f compose.e2e.yaml up -d --wait
```

Cada arranque del backend E2E agrega una empresa ficticia nueva para cada navegador,
sin borrar ni reiniciar contratos previos. La base y el flag E2E se comprueban antes
de sembrar datos. No se agregan estos fixtures en la base principal.

## Flujo

1. Seleccionar plan y obtener cotización. Backend determina precio y prorrateo.
2. Revisar importe, vigencia de 15 minutos, próxima renovación y condiciones.
3. Marcar consentimiento y confirmar. Se crea un intento pendiente, sin ampliar
   capacidad hasta que el resultado simulado sea aprobado.
4. Simular aprobado, rechazado, pendiente o incierto. Los dos últimos mantienen
   el contrato anterior y bloquean nuevos intentos hasta conciliar.
5. Gestionar subida, bajada o cancelación. Revisiones obsoletas responden 409.

Precios backend inmutables y versionados: Inicial 4.500, Crecimiento 9.900 y
Operador 19.900 CLP/mes, totales para simulación. Sin IVA supuesto ni emisión fiscal.

Primera compra desde trial o asignación sin periodo inicia mes completo desde la
aprobación. Subida inmediata: diferencia mensual × microsegundos restantes /
microsegundos totales del periodo; Decimal, ROUND_HALF_UP al peso, sin cambiar
anclaje. Con medio periodo Inicial→Crecimiento: 2.700. Si redondea a cero, conserva
cotización/consentimiento/evento de cambio y no crea un cargo positivo ficticio.

Mes calendario anclado a día/hora UTC originales. Día inexistente se ajusta al fin
de mes; luego recupera el día original: 31 enero → fin febrero → 31 marzo.
Intervalos [inicio, fin), fechas presentadas en zona de empresa. No son 30 días.

Bajada programada solo cambia capacidad al aprobar renovación del nuevo precio.
Con exceso de uso conserva recursos e historial y bloquea aumentos, según 11D.1.
Cancelar detiene la renovación al final del periodo, sin reembolso ni suspensión
automática. Reanudar antes del fin exige nuevo consentimiento del plan de renovación.
Una intención pendiente debe revisarse/retirarse antes de subir de plan; no se
reemplaza en silencio. No se puede reasignar manualmente un contrato simulado
vigente con manage_subscription: usar el flujo comercial.

## Habilitación explícita de una empresa ficticia

Requiere `DEBUG=true` y `BILLING_SIMULATION_ENABLED=true`. El ejemplo de entorno
mantiene false; `.env` principal no se modifica automáticamente. Al cambiar el
entorno, recrear backend para cargarlo. Producción fuerza false, incluso si se
define la variable. Además, una cuenta activa de plataforma debe marcar la empresa
ficticia, después de revisar/asignar plan y habilitar sus límites (11D.1).

```powershell
docker compose exec backend python manage.py migrate --noinput
docker compose exec backend python manage.py manage_subscription review --tenant-id UUID
# Solo después de asignación y habilitación manual de límites:
docker compose exec backend python manage.py billing_simulation prepare --tenant-id UUID --actor-email plataforma@example.invalid --reason "Empresa ficticia para prueba comercial"
```

Estos son ejemplos para sustituir expresamente, no comandos ejecutados en la
empresa principal. El comando crea precios de prueba desde catálogo fijo y marca
solo la empresa indicada. Migrar no inicia trials ni habilita simulaciones.

## Renovación y conciliación

La renovación automática consentida se ensaya con un comando, sin planificador ni
cargos externos. Usa hora actual del servidor; no admite fechas arbitrarias desde
el cliente. En un periodo vencido, prepara un único intento o finaliza la cancelación.

```powershell
docker compose exec backend python manage.py billing_simulation renew --tenant-id UUID --actor-email plataforma@example.invalid
# Solo tras rechazo terminal y revisión explícita:
docker compose exec backend python manage.py billing_simulation renew --tenant-id UUID --actor-email plataforma@example.invalid --retry-rejected
```

Repetir el comando devuelve el intento existente; inciertos/pendientes deben
conciliarse desde la pantalla. Un rechazo no se transforma por un evento tardío
en aprobación. Reintentar tras rechazo conserva el intento anterior y aumenta
contador; solo el nuevo resultado aprobado concede el periodo. Si el siguiente
periodo también terminó, el comando deriva a revisión manual sin cobrar meses
retroactivos. No es un sistema automático de recuperación de morosidad.

## Aislamiento, API y archivos

Todas las escrituras API usan sesión owner, CSRF y X-Tenant-Context. Guardas de
entorno, marca de empresa ficticia y límites revisados se revalidan en servicios.
Locks Tenant → intento/contrato; clave idempotente y un intento pendiente/incierto
por empresa. Resultados verifican revisión de contrato y asignación manual; los
obsoletos pasan a revisión sin conceder capacidad ni crear cargo.

Rutas `/api/v1/billing/simulation/`:

- GET raíz: habilitación, condiciones, catálogo backend, contrato y últimos 20 intentos.
- POST `quotes/`: code, expected_revision. Máximo 60 cotizaciones por usuario/hora.
- POST `attempts/{id}/accept/`: key UUID, terms y consent=true.
- POST `attempts/{id}/result/`: event_id UUID, result; simulador local protegido,
  no webhook ni endpoint de proveedor real. Reentrega idéntica es idempotente.
- POST `intents/`: operation cancel/resume/downgrade/clear_change, expected_revision;
  resume/downgrade exigen code, terms y consent=true.

Campos extra o consentimiento falso: 400; permisos/contexto: 403/409; IDs ajenos:
404; cotización vencida, contenido idempotente distinto o revisión obsoleta: 409.
Retorno `?approved=true` no modifica nada. Estado aprobado siempre rotulado simulado.
SaaSCharge nunca se suma a Payment, dashboards o reportes de huéspedes.

Nuevos archivos: billing/simulation.py, simulation_views.py, comando
billing_simulation.py, migraciones 0004–0007; SimulationPage.tsx y pruebas
test_billing_simulation.py, Simulation.test.tsx, e2e/simulation.spec.ts.
Modelos añadidos: SimulationCompany, PlanPrice, SimulatedContract, CheckoutAttempt,
SimulatedProviderEvent y SaaSCharge. Consentimiento con actor/fecha/versión, y
auditoría mínima sin contactos ni payloads completos. Precios protegidos por trigger.
Los intentos aprobados conservan fechas del periodo y las subidas referencian su
precio anterior inmutable; las renovaciones no sobrescriben ese historial.

Límites: sin contratación real, pasarela, reembolsos, anualidades, cupones, impuestos,
webhooks externos o compatibilidad Mercado Pago certificada. Puerta P y 11D.3 siguen
pendientes. Evidencias de pruebas y cambios posteriores en PROGRESO.md.

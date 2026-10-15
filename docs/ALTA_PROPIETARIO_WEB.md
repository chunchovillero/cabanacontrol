# Alta inicial desde la web — entrega local 11B

Autorización: el usuario eligió «Alta inicial desde la web: propietario y primera
empresa» después del cierre de colaboradores 11A. Alcance independiente de planes,
suscripciones, cobros y despliegue real. El plan maestro se conserva.

## Uso

Abrir `/ingresar` y elegir **Crear cuenta y empresa**, o entrar a `/registrarse`.
Ingresar nombre, apellido opcional, correo, empresa y contraseña con confirmación.
Tras el alta, iniciar sesión y seleccionar la empresa. Desde **Usuarios**, el
propietario puede invitar administradores y colaboradores con el flujo 11A.

En este equipo: http://localhost:15173/registrarse. Si hay una sesión abierta,
cerrarla primero: una cuenta existente no puede crear otras empresas con este flujo.

## Contrato y decisiones

- `GET /api/v1/auth/register/` devuelve `enabled` para presentar el enlace.
- `POST` recibe únicamente `email`, `first_name`, `last_name` opcional,
  `company_name` y `password`. No acepta rol, empresa existente ni privilegios.
- CSRF obligatorio incluso sin sesión. Cinco intentos por IP en diez minutos,
  independientes de los límites de login. Identificadores de cuotas con HMAC.
- Usuario, empresa, membresía owner y auditoría se crean en una transacción.
  La unicidad de correo en PostgreSQL resuelve también altas simultáneas.
- Cuenta normal: sin permisos de Django admin ni administrador de plataforma.
  CLP y America/Santiago fijos. Nombre comercial sin exigir RUT de empresa:
  no corresponde inventar validaciones tributarias para este alcance.
- Se aplican los validadores existentes de contraseña y límites de campos.
  Correo existente: no se cambia contraseña ni se agrega otra empresa; se orienta
  a iniciar sesión o recuperar acceso. El error local permite inferir existencia
  de una cuenta: deberá revisarse junto con la verificación antes del alta pública.
- No inicia sesión automáticamente. Password fuera de URL, almacenamiento local
  y auditoría; auditoría con IDs y acción `owner_registered_local`.
- No requiere migración: reutiliza los modelos actuales.

## Límite de esta entrega

El alta funciona solo con `DEBUG=true` y `LOCAL_ONBOARDING_ENABLED=true` (valor
predeterminado de desarrollo). `config.production` fuerza ambos a false.
Puede deshabilitarse localmente definiendo `LOCAL_ONBOARDING_ENABLED=false` y
recreando el backend. No se modificó el `.env` existente.

Este flujo local no verifica la titularidad del correo ni envía mensajes.
Antes del registro público quedan por implementar verificación de correo y
SMTP real, controles de abuso y decisiones comerciales/privacidad de la puerta P.
Los contenedores de producción ya construidos requieren reconstrucción para
incorporar código nuevo; esta entrega no despliega ni activa proveedores.

Las pruebas E2E crean únicamente cuentas y empresas ficticias en el proyecto
aislado `cabanacontrol-e2e`; se conservan sus datos y artefactos al detenerlo.

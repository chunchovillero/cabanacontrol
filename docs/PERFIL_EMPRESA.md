# Perfil y empresa — entrega 11C

Autorización: el usuario eligió «Perfil y empresa: editar nombre y datos de
contacto». Se implementa únicamente esta parte de gestión de cuenta; no habilita
registro público, cambios de correo de acceso, suscripciones ni despliegue real.

## Uso

Iniciar sesión y abrir **Perfil y empresa**, en `/configuracion`.
En este equipo: http://localhost:15173/configuracion.

Cualquier usuario activo puede editar su propio nombre y apellido. El nombre
pertenece a la cuenta global y se refleja en todas sus empresas; correo de acceso,
contraseña y privilegios conservan sus flujos actuales. No se necesita seleccionar
una empresa para editar el perfil.

El propietario de la empresa seleccionada puede editar nombre comercial, razón
social opcional, correo de contacto opcional y teléfono opcional. Administradores,
colaboradores y administradores de plataforma sin membresía owner no acceden a
esa configuración. El correo de contacto no cambia el correo de inicio de sesión.
Moneda, zona horaria, estado y propietarios no son editables en este formulario.
Se conserva la moneda/zona existentes; el alta local utiliza CLP/America/Santiago.

## API y decisiones

- `GET /api/v1/auth/profile/`: first_name, last_name, email.
- `PATCH /api/v1/auth/profile/`: first_name, last_name,
  expected_first_name y expected_last_name. Solo cuenta de la sesión; ningún ID
  de usuario suministrado por el cliente. Bloqueo de fila y comparación de valores
  previos: conflicto 409 si los nombres han cambiado.
- `GET /api/v1/company-settings/`: id, name, legal_name, contact_email,
  contact_phone, currency, timezone, updated_at. Solo owner/empresa activa.
- `PATCH /api/v1/company-settings/`: name, legal_name, contact_email,
  contact_phone y expected_updated_at. CSRF y X-Tenant-Context obligatorios.
  Bloqueo de empresa compartido con gestión de accesos, revalidación del propietario
  y comparación de updated_at. Conflicto 409 si hay una edición posterior.
- Campos desconocidos, texto vacío obligatorio, caracteres de control o correo
  inválido: 400. Teléfono permite dígitos, +, espacios, paréntesis, punto y guion,
  hasta 30 caracteres; admite contactos internacionales, no valida titularidad.
- Todos los campos editables del formulario se envían juntos; no se interpreta la
  omisión de un campo como borrado. Apellido y contactos sí admiten vacío explícito.
- Auditoría por IDs/acción, con nombres de campos cambiados en empresa; no replica
  nombres personales ni valores de contacto. Guardar sin cambios no crea evento.
- Frontend refresca sesión/lista de empresas al guardar. Ante 409 recarga valores,
  muestra aviso y exige revisión humana; no reintenta automáticamente la escritura.
  Formularios y caché separados por cuenta/empresa. No usa almacenamiento local.
- No requiere migraciones: reutiliza campos existentes de User y Tenant.

## Archivos principales

Backend: accounts/profile.py, tenants/configuration.py y sus rutas.
Frontend: features/auth/SettingsPage.tsx y navegación en IdentityApp.tsx.
Pruebas: tests/test_settings.py, Settings.test.tsx, e2e/settings.spec.ts y fixture
aislado en tests/e2e_seed.py. Los casos de navegador solo cambian datos ficticios
en `cabanacontrol-e2e`; no se modifican registros del entorno principal.

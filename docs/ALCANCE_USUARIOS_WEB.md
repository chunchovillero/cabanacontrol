# Entrega 11A local — Colaboradores desde la web

Autorizada al elegir «Usuarios web: propietario invita colaboradores y asigna permisos».
Excepción de orden limitada al desarrollo local de gestión de cuenta; la dependencia
de puerta P para uso comercial/desplegado sigue vigente. No se autoriza Fase 11 completa.

El propietario gestiona usuarios de su empresa: invita con rol manager o staff,
cambia entre esos roles y desactiva/reactiva membresías. No cambia propietarios,
su propia membresía, contraseñas globales ni accesos de otras empresas. Sin borrados.
El alta del primer propietario/empresa conserva su procedimiento administrativo.

Invitaciones manuales, 72 horas, token aleatorio de 256 bits guardado solo como hash,
un solo uso, revocable y mostrado únicamente al crearlo. Enlace en fragmento de URL,
sin tokens en logs, consultas, localStorage ni auditoría. El propietario copia el
enlace y lo comparte personalmente con su destinatario; no hay correo/WhatsApp externo.
No existe verificación de entregabilidad del correo mediante este mecanismo manual.

Quien no tiene cuenta establece su propia contraseña al aceptar. Quien ya tiene
cuenta inicia sesión con el correo invitado; el enlace no permite cambiar su contraseña
ni aceptar como otro usuario. Se conserva el aislamiento y la política de contraseñas.
La aceptación y los cambios se serializan por empresa; revisión de estado evita que
una pantalla antigua sobrescriba permisos nuevos. Revocar afecta solicitudes posteriores;
no revierte operaciones que ya habían sido admitidas antes de la revocación.

Límites iniciales: 10 creaciones por propietario/hora y 50 por empresa/día, máximo
25 invitaciones pendientes vigentes por empresa. Consulta/aceptación limitada por IP;
sin registro público, campañas, cobro, planes, trial, perfiles ni transferencia de dominio.

Pruebas: permisos/CSRF/contexto, IDs ajenos, token alterado/vencido/revocado/reutilizado,
cuenta existente, credenciales, carreras de aceptación/revocación, persistencia de
otros accesos, UI responsive y E2E con empresas/correos ficticios. Migración aditiva,
documentación y verificaciones integrales. No modificar registros de negocio existentes.

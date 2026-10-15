# Página pública de CabañaControl

Solicitud expresa: «Crear una página con todo el funcionamiento de la aplicación,
con precios, etc.». Se autoriza la página informativa dentro del proyecto local y
mostrar los precios definidos. No autoriza contratación, integración de Mercado
Pago, despliegue externo ni activación de 11D.2/11D.3.

## Acceso

- Siempre: http://localhost:15173/conocer.
- Inicio sin sesión: http://localhost:15173/.
- Con sesión, `/` conserva la pantalla de empresas. La navegación incluye
  **Conocer CabañaControl**; desde la presentación **Ir a mi cuenta** vuelve a las
  empresas sin cambiar su selección. Cerrar sesión desde el inicio muestra la
  presentación; el formulario de acceso sigue en `/ingresar`.

Servicios iniciados con el Compose existente; no hay comandos nuevos de instalación,
dependencias, migraciones ni variables de entorno para esta página.

## Contenido y comportamiento

Presentación responsive en español de Chile: portada, demostración interactiva de
reservas/abonos/limpieza con datos ficticios, seis grupos de funciones, recorrido
de uso, asistente/voz/WhatsApp, precios, trial, preguntas frecuentes y accesos.
Verde bosque, fondos crema y tipografía editorial; icono SVG propio sin archivos,
fuentes ni servicios externos. Estilos acotados a `.marketing`, sin alterar el
tema de pantallas de operación. Controles con foco visible, enlace de salto y
FAQ expandible nativa de teclado.

Precios por empresa y mes: Inicial $4.500 (3 cabañas/2 usuarios), Crecimiento $9.900
(8/5) y Operador $19.900 (20/10). Totales de referencia para simulación, con estado
de contratación pendiente visible. No son una suscripción contratada ni originan
cargos. El usuario autorizó ahora mostrarlos informativamente en esta página.

`src/lib/planPresentation.ts` comparte los precios visuales con Plan y uso, evitando
que una pantalla siga indicando precios sin definir. No agrega precios al API o
modelo comercial: un checkout futuro deberá obtener importes versionados del
servidor. Este catálogo visual nunca debe autorizar o calcular cargos.

Botones de planes llevan a **Cómo empezar**; no contratan ni modifican plan. Los
accesos de cuenta llevan a las rutas existentes. El registro de prueba conserva
su propia validación de disponibilidad del entorno; no inicia trial automáticamente.
Trial manual 14 días y capacidad 1/1; propietario ocupa la plaza. Vencimiento sin
suspensión automática, con revisión manual.

Se identifican límites reales: configuración/coste propios de IA y voz, activación
independiente de WhatsApp oficial, Mercado Pago futuro sin checkout, y ausencia
actual de sincronización Airbnb/Booking, emisión tributaria y cobros online a
huéspedes. No se inventan testimonios, clientes, disponibilidad real o cifras de
negocio. La demostración no consulta datos privados ni realiza escrituras.

## Archivos y verificaciones

Nuevos: features/marketing/LandingPage.tsx, landing.css, lib/planPresentation.ts y
e2e/landing.spec.ts. Ajustados IdentityApp, descripción en index.html, precios
visuales de PlanPage y sus pruebas; expectativas de login/logout en pruebas de
identidad reflejan el nuevo inicio público.

Las capturas de presentación se guardan en `docs/screenshots/landing-chromium.png`
y `landing-mobile.png`; solo contienen ejemplos ficticios. El recorrido público
se verifica en el desarrollo principal sin sesión y comprueba cero escrituras.
El recorrido de identidad/empresa y la pantalla Plan y uso se verifican con datos
ficticios en el proyecto Docker E2E separado. Resultados exactos en PROGRESO.md.

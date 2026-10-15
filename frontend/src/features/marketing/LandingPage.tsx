import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { publicPlans as plans } from '@/lib/planPresentation'
import './landing.css'

const features = [
  [
    '01',
    'Reservas y disponibilidad',
    'Calendario interactivo, reservas pendientes con vencimiento, confirmaciones y bloqueos de mantenimiento. El sistema comprueba los cruces de fechas antes de guardar.',
  ],
  [
    '02',
    'Huéspedes, bien registrados',
    'Fichas de huéspedes, validación de RUT chileno y documentos extranjeros. Datos organizados por empresa y acceso según el rol de cada persona.',
  ],
  [
    '03',
    'Abonos y saldos claros',
    'Registra pagos de huéspedes, adjunta comprobantes y revisa deuda o saldo a favor. Las anulaciones conservan su historial y requieren un motivo.',
  ],
  [
    '04',
    'Tu operación de cada día',
    'Entradas, salidas, tareas de limpieza con checklist y alertas internas. El check-out genera una tarea de limpieza para dar seguimiento a la preparación de la cabaña.',
  ],
  [
    '05',
    'Decisiones con información',
    'Panel con ocupación, importes pactados y cobros. Filtra reportes por periodo o cabaña y descarga CSV con los permisos de tu cuenta.',
  ],
  [
    '06',
    'Un equipo, cada cosa en su lugar',
    'Invita administradores o colaboradores, asigna roles y revoca accesos. Una cuenta puede trabajar en distintas empresas, conservando sus datos separados.',
  ],
]
const faqs = [
  [
    '¿Cómo funciona la prueba de 14 días?',
    'La prueba permite 1 cabaña activa y 1 usuario, incluido el propietario. Su activación es manual después de revisar la empresa; crear una cuenta no la inicia automáticamente. No pide tarjeta ni se transforma automáticamente en una contratación.',
  ],
  [
    '¿Qué pasa cuando termina la prueba?',
    'Aparece un aviso y se conserva la capacidad de 1 cabaña y 1 usuario hasta la revisión manual. No se borran los datos ni se suspende automáticamente la operación.',
  ],
  [
    '¿Los precios son por cabaña o por empresa?',
    'Son valores mensuales por empresa, para la capacidad indicada en cada plan. El propietario cuenta dentro del límite de usuarios. Los importes mostrados son totales de referencia para la simulación comercial; la contratación real todavía está en preparación.',
  ],
  [
    '¿Puedo pagar o contratar desde esta página?',
    'Todavía no. Mercado Pago es la pasarela elegida para una integración futura, pero no hay checkout ni cobros reales habilitados. Una futura renovación automática necesitará contratación y consentimiento explícitos.',
  ],
  [
    '¿Se conecta con Airbnb o Booking?',
    'La sincronización con Airbnb, Booking y otros canales no forma parte de la aplicación actual. Las reservas y bloqueos se gestionan dentro de CabañaControl.',
  ],
  [
    '¿Cómo funciona WhatsApp?',
    'Puedes preparar una respuesta editable y abrir WhatsApp manualmente desde una reserva. La conexión oficial de WhatsApp Business requiere configuración y activación independientes; no está habilitada para envíos reales en este entorno.',
  ],
  [
    '¿La inteligencia artificial crea o confirma reservas sola?',
    'No. El asistente permite consultar disponibilidad y preparar respuestas. Las notas dictadas se transcriben para revisión y pueden convertirse en borradores mediante una acción humana. La IA requiere configuración y presupuesto propios; no está incluida como consumo ilimitado en los planes.',
  ],
  [
    '¿Puedo emitir boletas o cobrar a mis huéspedes con tarjeta?',
    'Actualmente puedes registrar abonos y comprobantes. La emisión tributaria, los reembolsos y el cobro online a huéspedes requieren desarrollos posteriores. La mensualidad de CabañaControl se gestiona separada de los pagos de tus reservas.',
  ],
]

function CabinMark() {
  return (
    <svg viewBox="0 0 32 32" fill="none" aria-hidden="true" className="h-8 w-8">
      <path
        d="M3 17 16 5l13 12M8 14v13h16V14M13 27v-9h6v9"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M24 5v7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function ProductPreview() {
  const [tab, setTab] = useState<'reservas' | 'pagos' | 'limpieza'>('reservas')
  return (
    <section
      aria-label="Demostración de la aplicación con datos ficticios"
      className="marketing-preview"
    >
      <div className="flex items-center justify-between border-b border-[#e4e9df] px-5 py-4">
        <span className="text-sm font-bold">
          Tu alojamiento<span className="text-[#788675]"> / Panel</span>
        </span>
        <span className="rounded-full bg-[#edf2e8] px-2 py-1 text-[10px] font-semibold uppercase tracking-wider">
          Ejemplo ficticio
        </span>
      </div>
      <div className="p-5 sm:p-7">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-[#667361]">TODO A LA VISTA</p>
            <h2 className="mt-1 text-xl font-bold">Un día bien organizado.</h2>
          </div>
          <span aria-hidden="true" className="text-3xl text-[#bc814e]">
            ☀
          </span>
        </div>
        <div
          aria-label="Vistas de demostración"
          className="my-6 flex gap-1 rounded-xl bg-[#f0f3ed] p-1"
        >
          {(['reservas', 'pagos', 'limpieza'] as const).map((item) => (
            <button
              key={item}
              type="button"
              aria-pressed={tab === item}
              onClick={() => setTab(item)}
              className={`min-w-0 flex-1 rounded-lg px-2 py-2 text-xs font-semibold capitalize sm:text-sm ${tab === item ? 'bg-white text-[#193c30] shadow-sm' : 'text-[#596653]'}`}
            >
              {item}
            </button>
          ))}
        </div>
        <div className="min-h-52" aria-live="polite">
          {tab === 'reservas' && (
            <>
              <div className="mb-4 flex justify-between text-xs text-[#667361]">
                <span>Calendario de ejemplo</span>
                <span>5 noches · 3 cabañas</span>
              </div>
              <div className="grid grid-cols-[64px_repeat(5,minmax(0,1fr))] gap-y-4 text-center text-[10px] sm:grid-cols-[85px_repeat(5,minmax(0,1fr))] sm:text-xs">
                <span />
                {['Lun', 'Mar', 'Mié', 'Jue', 'Vie'].map((day) => (
                  <span className="text-[#667361]" key={day}>
                    {day}
                  </span>
                ))}
                {['Bosque', 'Río', 'Montaña'].map((name, index) => (
                  <div key={name} className="contents">
                    <span className="self-center text-left font-medium">{name}</span>
                    {index === 0 ? (
                      <>
                        <span className="col-span-3 rounded-lg bg-[#315d48] p-3 text-white">
                          Confirmada
                        </span>
                        <span className="col-span-2 rounded-lg border border-dashed border-[#c3cfbe] p-3 text-[#65745d]">
                          Libre
                        </span>
                      </>
                    ) : index === 1 ? (
                      <>
                        <span className="col-span-2 rounded-lg border border-dashed border-[#c3cfbe] p-3 text-[#65745d]">
                          Libre
                        </span>
                        <span className="col-span-3 rounded-lg bg-[#eee0c6] p-3 text-[#6e5125]">
                          Pendiente
                        </span>
                      </>
                    ) : (
                      <>
                        <span className="col-span-2 rounded-lg bg-[#e7eae3] p-3 text-[#55604f]">
                          Bloqueo
                        </span>
                        <span className="col-span-3 rounded-lg bg-[#315d48] p-3 text-white">
                          Confirmada
                        </span>
                      </>
                    )}
                  </div>
                ))}
              </div>
              <p className="mt-5 text-xs text-[#667361]">
                Cada reserva en su lugar. Cada fecha, clara.
              </p>
            </>
          )}
          {tab === 'pagos' && (
            <>
              <p className="mb-4 text-xs text-[#667361]">Reserva de ejemplo · Cabaña Bosque</p>
              {[
                ['Precio pactado', '$180.000'],
                ['Abonos registrados', '$60.000'],
                ['Saldo pendiente', '$120.000'],
              ].map(([label, value]) => (
                <div
                  key={label}
                  className="flex justify-between border-b border-[#e4e9df] py-4 text-sm"
                >
                  <span>{label}</span>
                  <strong>{value}</strong>
                </div>
              ))}
              <p className="mt-3 text-xs text-[#667361]">Importes ficticios en CLP.</p>
            </>
          )}
          {tab === 'limpieza' && (
            <>
              <p className="mb-4 text-xs text-[#667361]">Después del check-out · Cabaña Bosque</p>
              {['Baño', 'Cocina', 'Dormitorios', 'Inventario'].map((item, index) => (
                <div
                  key={item}
                  className="flex items-center gap-3 border-b border-[#e4e9df] py-3 text-sm"
                >
                  <span
                    aria-hidden="true"
                    className={`flex h-5 w-5 items-center justify-center rounded-md ${index < 2 ? 'bg-[#315d48] text-white' : 'border border-[#bcc8b5]'}`}
                  >
                    {index < 2 ? '✓' : ''}
                  </span>
                  {item}
                  <span className="ml-auto text-xs text-[#667361]">
                    {index < 2 ? 'Revisado' : 'Pendiente'}
                  </span>
                </div>
              ))}
            </>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2 border-t border-[#e4e9df] px-5 py-4 text-xs text-[#667361]">
        <span aria-hidden="true" className="h-2 w-2 rounded-full bg-[#68935b]" />
        Vista ilustrativa · no usa datos de huéspedes
      </div>
    </section>
  )
}

export function LandingPage({ signedIn = false }: { signedIn?: boolean }) {
  return (
    <div className="marketing min-h-screen bg-[#f7f7ef] text-[#20372b]">
      <a
        href="#contenido"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-white focus:p-3"
      >
        Saltar al contenido
      </a>
      <header className="border-b border-[#dfe4d7] bg-[#f7f7ef]">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-5 py-5 sm:px-8">
          <Link
            to="/conocer"
            aria-label="CabañaControl, presentación"
            className="flex items-center gap-2 text-lg font-bold tracking-tight"
          >
            <CabinMark />
            CabañaControl<span className="text-[#b57c4c]">.</span>
          </Link>
          <nav
            aria-label="Navegación de presentación"
            className="flex flex-wrap items-center gap-4 text-sm sm:gap-7"
          >
            <a className="hidden hover:underline sm:inline" href="#funciones">
              Funciones
            </a>
            <a href="#precios" className="hover:underline">
              Precios
            </a>
            <a href="#preguntas" className="hidden hover:underline sm:inline">
              Preguntas
            </a>
            <Button asChild className="bg-[#244d39] px-5">
              <Link to={signedIn ? '/' : '/ingresar'}>
                {signedIn ? 'Ir a mi cuenta' : 'Ingresar'}{' '}
                <span aria-hidden="true" className="ml-2">
                  ↗
                </span>
              </Link>
            </Button>
          </nav>
        </div>
      </header>
      <main id="contenido">
        <section className="marketing-hero mx-auto grid max-w-6xl items-center gap-12 px-5 py-16 sm:px-8 sm:py-24 lg:grid-cols-[1fr_1.04fr] lg:gap-14">
          <div>
            <p className="mb-6 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.17em]">
              <span aria-hidden="true" className="h-2 w-2 rounded-full bg-[#b57c4c]" />
              Tu alojamiento, bajo control
            </p>
            <h1 className="marketing-heading text-5xl leading-[1.06] tracking-tight sm:text-6xl">
              Menos planillas.
              <br />
              Más tiempo para
              <br />
              <span className="text-[#527347]">tus huéspedes.</span>
            </h1>
            <p className="mt-7 max-w-md text-base leading-7 text-[#5c6856]">
              Reservas, huéspedes, abonos y limpieza en un solo lugar. CabañaControl te ayuda a
              organizar tu operación y saber qué pasa en cada cabaña.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild className="bg-[#244d39] px-6 py-6 text-base">
                <a href="#funciones">
                  Conoce cómo funciona{' '}
                  <span aria-hidden="true" className="ml-2">
                    ↓
                  </span>
                </a>
              </Button>
              <Button
                asChild
                variant="outline"
                className="border-[#becab5] bg-transparent px-6 py-6 text-base"
              >
                <a href="#precios">Ver planes</a>
              </Button>
            </div>
            <p className="mt-5 text-xs leading-5 text-[#68745f]">
              Español de Chile · Pesos chilenos · Desde el computador o el celular
            </p>
          </div>
          <ProductPreview />
        </section>
        <div className="border-y border-[#dfe4d7] bg-[#eff1e7]">
          <div className="mx-auto grid max-w-6xl gap-4 px-5 py-6 text-sm sm:grid-cols-3 sm:px-8">
            <p>
              <span className="mr-2 text-[#6d875c]" aria-hidden="true">
                ✓
              </span>
              Disponibilidad validada al guardar
            </p>
            <p>
              <span className="mr-2 text-[#6d875c]" aria-hidden="true">
                ✓
              </span>
              Datos separados por empresa
            </p>
            <p>
              <span className="mr-2 text-[#6d875c]" aria-hidden="true">
                ✓
              </span>
              Permisos para cada integrante
            </p>
          </div>
        </div>
        <section
          id="funciones"
          className="mx-auto max-w-6xl scroll-mt-6 px-5 py-20 sm:px-8 sm:py-24"
        >
          <p className="marketing-eyebrow">DE LA RESERVA AL CHECK-OUT</p>
          <div className="mt-4 flex flex-wrap items-end justify-between gap-5">
            <h2 className="marketing-heading max-w-xl text-4xl leading-tight sm:text-5xl">
              Toda tu operación.
              <br />
              Una vista más clara.
            </h2>
            <p className="max-w-sm text-sm leading-6 text-[#65705c]">
              Herramientas conectadas para seguir el día a día de tus alojamientos, sin perder el
              historial.
            </p>
          </div>
          <div className="mt-12 grid gap-px overflow-hidden rounded-2xl border border-[#dfe4d7] bg-[#dfe4d7] md:grid-cols-2 lg:grid-cols-3">
            {features.map(([number, title, description]) => (
              <article key={number} className="bg-[#fafaf5] p-7 sm:p-8">
                <p className="text-sm font-medium text-[#927651]">{number} /</p>
                <h3 className="mt-6 text-xl font-semibold">{title}</h3>
                <p className="mt-3 text-sm leading-7 text-[#65705c]">{description}</p>
              </article>
            ))}
          </div>
        </section>
        <section id="como-funciona" className="bg-[#254333] px-5 py-20 text-[#f7f7ef] sm:px-8">
          <div className="mx-auto max-w-6xl">
            <p className="text-xs font-semibold tracking-[0.17em] text-[#c0d0b4]">
              ASÍ SE CONECTA TODO
            </p>
            <h2 className="marketing-heading mt-4 text-4xl sm:text-5xl">
              Un recorrido simple, de principio a fin.
            </h2>
            <ol className="mt-12 grid gap-9 sm:grid-cols-2 lg:grid-cols-4">
              {[
                [
                  'Prepara tu alojamiento',
                  'Registra las cabañas, su capacidad y los horarios. Invita al equipo y define sus permisos.',
                ],
                [
                  'Organiza las reservas',
                  'Consulta fechas, selecciona al huésped e ingresa el precio pactado. Revisa y confirma la reserva.',
                ],
                [
                  'Sigue los pagos',
                  'Registra cada abono y su comprobante. Consulta el saldo pendiente o a favor de la reserva.',
                ],
                [
                  'Cierra y vuelve a preparar',
                  'Registra entrada y salida, sigue la limpieza y revisa el calendario y los reportes.',
                ],
              ].map(([title, text], index) => (
                <li key={title}>
                  <span className="flex h-10 w-10 items-center justify-center rounded-full border border-[#77916b] text-sm text-[#d2ddc3]">
                    0{index + 1}
                  </span>
                  <h3 className="mt-5 font-semibold">{title}</h3>
                  <p className="mt-3 text-sm leading-7 text-[#c5d1bf]">{text}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>
        <section className="mx-auto grid max-w-6xl gap-10 px-5 py-20 sm:px-8 md:grid-cols-2">
          <div>
            <p className="marketing-eyebrow">AYUDA PARA RESPONDER MEJOR</p>
            <h2 className="marketing-heading mt-4 text-4xl">
              Un asistente.
              <br />
              Tú conservas el control.
            </h2>
            <p className="mt-5 text-sm leading-7 text-[#65705c]">
              Consulta disponibilidad, prepara respuestas de WhatsApp y revisa notas dictadas. El
              asistente apoya tu trabajo; la revisión y las decisiones siguen en tus manos.
            </p>
          </div>
          <div className="rounded-2xl border border-[#dfe4d7] bg-[#eff1e7] p-7">
            <h3 className="font-semibold">Qué puedes preparar</h3>
            <ul className="mt-4 space-y-4 text-sm leading-6">
              <li>✓ Consultas con datos de tu empresa y permisos de tu cuenta.</li>
              <li>✓ Respuestas editables para compartir manualmente por WhatsApp.</li>
              <li>✓ Notas dictadas, revisadas y convertidas en borradores por una persona.</li>
            </ul>
            <p className="mt-6 border-t border-[#ced8c6] pt-5 text-xs leading-6 text-[#59684f]">
              IA y voz requieren configuración y presupuesto propios. La integración oficial de
              WhatsApp Business tiene activación independiente. No se incluyen consumos ilimitados
              ni envíos reales en este entorno.
            </p>
          </div>
        </section>
        <section
          id="precios"
          className="scroll-mt-6 border-y border-[#dfe4d7] bg-[#eff1e7] px-5 py-20 sm:px-8"
        >
          <div className="mx-auto max-w-6xl">
            <p className="marketing-eyebrow">ESPACIO PARA CRECER</p>
            <h2 className="marketing-heading mt-4 text-4xl sm:text-5xl">
              Un plan para cada etapa.
            </h2>
            <p className="mt-5 max-w-2xl text-sm leading-7 text-[#65705c]">
              Precios mensuales por empresa, en CLP. Todos contemplan el núcleo operativo: reservas,
              huéspedes, abonos, calendario, reportes y limpieza.
            </p>
            <p className="mt-4 inline-block rounded-lg border border-[#d1d9c7] bg-[#fafaf5] px-4 py-3 text-xs leading-5">
              Valores totales de referencia para simulación. Contratación y cobros reales aún no
              habilitados.
            </p>
            <div className="mt-10 grid gap-5 md:grid-cols-3">
              {plans.map((plan, index) => (
                <article
                  key={plan.name}
                  aria-label={`Plan ${plan.name}`}
                  className={`flex flex-col rounded-2xl border p-7 ${index === 1 ? 'border-[#31533a] bg-[#254333] text-[#f7f7ef]' : 'border-[#d4dccb] bg-[#fafaf5]'}`}
                >
                  <p
                    className={`text-xs font-semibold uppercase tracking-widest ${index === 1 ? 'text-[#c0d0b4]' : 'text-[#6b795f]'}`}
                  >
                    {plan.name}
                  </p>
                  <p className="mt-6">
                    <strong className="text-4xl tracking-tight">
                      ${new Intl.NumberFormat('es-CL').format(plan.price)}
                    </strong>
                    <span
                      className={`ml-1 text-sm ${index === 1 ? 'text-[#c0d0b4]' : 'text-[#6b795f]'}`}
                    >
                      / mes
                    </span>
                  </p>
                  <p
                    className={`mt-3 min-h-12 text-sm leading-6 ${index === 1 ? 'text-[#c0d0b4]' : 'text-[#6b795f]'}`}
                  >
                    {plan.description}
                  </p>
                  <ul className="my-7 space-y-3 border-t border-current/20 pt-6 text-sm">
                    <li>
                      ✓ Hasta <strong>{plan.cabins} cabañas activas</strong>
                    </li>
                    <li>
                      ✓ Hasta <strong>{plan.users} usuarios activos</strong>
                    </li>
                    <li>✓ Propietario incluido en las plazas</li>
                    <li>✓ Funciones operativas del núcleo</li>
                  </ul>
                  <Button
                    asChild
                    variant="outline"
                    className={`mt-auto w-full border-current/30 ${index === 1 ? 'bg-[#f7f7ef] text-[#254333] hover:bg-[#e8eddc]' : 'bg-transparent'}`}
                  >
                    <a href="#comenzar">Cómo empezar con {plan.name}</a>
                  </Button>
                </article>
              ))}
            </div>
            <div className="mt-7 flex flex-wrap items-start justify-between gap-5 rounded-xl border border-[#d4dccb] p-5">
              <div>
                <h3 className="font-semibold">Prueba de 14 días · 1 cabaña · 1 usuario</h3>
                <p className="mt-2 text-sm leading-6 text-[#65705c]">
                  Sin tarjeta ni contratación automática. La activación es manual después de revisar
                  tu empresa.
                </p>
              </div>
              <a className="text-sm font-semibold underline underline-offset-4" href="#preguntas">
                Conoce las condiciones ↗
              </a>
            </div>
          </div>
        </section>
        <section id="preguntas" className="mx-auto max-w-3xl scroll-mt-6 px-5 py-20 sm:px-8">
          <p className="marketing-eyebrow">ANTES DE EMPEZAR</p>
          <h2 className="marketing-heading mt-4 text-4xl sm:text-5xl">Las cosas claras.</h2>
          <div className="mt-9 divide-y divide-[#dfe4d7]">
            {faqs.map(([question, answer]) => (
              <details key={question} className="group py-5">
                <summary className="cursor-pointer text-base font-semibold leading-7">
                  {question}
                </summary>
                <p className="mt-4 text-sm leading-7 text-[#65705c]">{answer}</p>
              </details>
            ))}
          </div>
        </section>
        <section
          id="comenzar"
          className="mx-5 mb-10 rounded-2xl bg-[#dfE6d5] px-6 py-14 text-center sm:mx-8"
        >
          <div className="mx-auto max-w-2xl">
            <p className="marketing-eyebrow">TU PRÓXIMO PASO</p>
            <h2 className="marketing-heading mt-4 text-4xl sm:text-5xl">
              Conoce tu nueva forma
              <br />
              de organizar las cabañas.
            </h2>
            <p className="mx-auto mt-5 max-w-lg text-sm leading-7 text-[#58694d]">
              Puedes ingresar a tu cuenta o revisar el alta de prueba disponible en este entorno.
              Crear una cuenta no contrata un plan ni activa automáticamente el trial.
            </p>
            <div className="mt-7 flex flex-wrap justify-center gap-3">
              <Button asChild className="bg-[#244d39] px-6 py-6">
                <Link to={signedIn ? '/' : '/ingresar'}>
                  {signedIn ? 'Ir a mis empresas' : 'Ingresar a mi cuenta'}
                </Link>
              </Button>
              {!signedIn && (
                <Button
                  asChild
                  variant="outline"
                  className="border-[#b9c9aa] bg-transparent px-6 py-6"
                >
                  <Link to="/registrarse">Revisar registro de prueba</Link>
                </Button>
              )}
            </div>
            <p className="mt-5 text-xs leading-5 text-[#58694d]">
              El alta web está disponible solo en desarrollo. Si el registro está deshabilitado, la
              pantalla te lo indicará.
            </p>
          </div>
        </section>
      </main>
      <footer className="border-t border-[#dfe4d7] px-5 py-8 sm:px-8">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-5 text-sm">
          <span className="flex items-center gap-2 font-bold">
            <CabinMark />
            CabañaControl.
          </span>
          <p className="text-xs text-[#65705c]">Gestión de cabañas y alojamientos turísticos.</p>
          <a href="#contenido" className="text-xs underline underline-offset-4">
            Volver arriba ↑
          </a>
        </div>
      </footer>
    </div>
  )
}

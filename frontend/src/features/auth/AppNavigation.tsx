import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import type { Session } from '@/lib/api'

const mainLinks = [
  { to: '/cabanas', label: 'Cabañas', icon: '⌂' },
  { to: '/reservas', label: 'Reservas', icon: '▤' },
  { to: '/calendario', label: 'Calendario', icon: '▦' },
  { to: '/operacion', label: 'Operación', icon: '✓' },
]

export function AppNavigation({
  session,
  loggingOut,
  logout,
}: {
  session: Session
  loggingOut: boolean
  logout: () => void
}) {
  const location = useLocation()
  const [openAt, setOpenAt] = useState<string | null>(null)
  const open = openAt === location.pathname
  const groups = [
    ...(session.active_tenant
      ? [
          {
            title: 'Alojamiento',
            links: [
              ['/panel', 'Panel general'],
              ['/huespedes', 'Huéspedes'],
              ['/reportes', 'Reportes'],
            ],
          },
          {
            title: 'Atención',
            links: [
              ['/consultas', 'Consultas'],
              ['/asistente', 'Asistente'],
              ['/whatsapp', 'WhatsApp'],
            ],
          },
        ]
      : []),
    {
      title: 'Cuenta',
      links: [
        ['/', 'Empresas'],
        ['/configuracion', 'Perfil y empresa'],
        ...(session.active_tenant?.role === 'owner'
          ? [
              ['/usuarios', 'Usuarios'],
              ['/plan', 'Plan y uso'],
            ]
          : []),
        ['/conocer', 'Conocer CabañaControl'],
      ],
    },
  ]
  const links = session.active_tenant ? mainLinks : [{ to: '/', label: 'Empresas', icon: '▦' }]
  return (
    <>
      <nav aria-label="Navegación principal" className="hidden items-center gap-1 lg:flex">
        {links.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `rounded-lg px-3 py-2 text-sm font-medium ${isActive ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted hover:text-foreground'}`
            }
          >
            {label}
          </NavLink>
        ))}
        <button
          type="button"
          aria-expanded={open}
          aria-controls="app-more-menu"
          onClick={() => setOpenAt(open ? null : location.pathname)}
          className="rounded-lg border border-border px-3 py-2 text-sm font-medium hover:bg-muted"
        >
          Más opciones
        </button>
      </nav>
      <nav
        aria-label="Navegación móvil"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
        className="fixed inset-x-0 bottom-0 z-40 flex justify-around border-t border-border bg-white shadow-[0_-4px_20px_rgba(0,0,0,0.05)] lg:hidden"
      >
        {links.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex min-h-16 min-w-0 flex-1 flex-col items-center justify-center gap-1 text-[11px] font-medium ${isActive ? 'bg-primary/10 text-primary' : 'text-muted-foreground'}`
            }
          >
            <span aria-hidden="true" className="text-xl leading-none">
              {icon}
            </span>
            {label}
          </NavLink>
        ))}
        <button
          type="button"
          aria-expanded={open}
          aria-controls="app-more-menu"
          onClick={() => setOpenAt(open ? null : location.pathname)}
          className={`flex min-h-16 flex-1 flex-col items-center justify-center gap-1 text-[11px] font-medium ${open ? 'bg-primary/10 text-primary' : 'text-muted-foreground'}`}
        >
          <span aria-hidden="true" className="text-xl leading-none">
            ☰
          </span>
          Más
        </button>
      </nav>
      {open && (
        <>
          <button
            type="button"
            aria-label="Cerrar menú"
            onClick={() => setOpenAt(null)}
            className="fixed inset-0 z-40 bg-black/30"
          />
          <section
            id="app-more-menu"
            aria-label="Más opciones"
            className="fixed inset-x-3 bottom-[calc(5rem+env(safe-area-inset-bottom))] z-50 max-h-[75dvh] overflow-y-auto rounded-2xl border border-border bg-white p-5 shadow-xl lg:inset-x-auto lg:bottom-auto lg:right-6 lg:top-20 lg:w-96"
          >
            <div className="mb-4 flex items-center justify-between gap-3">
              <h2 className="font-semibold">Menú</h2>
              <button
                type="button"
                onClick={() => setOpenAt(null)}
                className="rounded-lg px-3 py-2 text-sm hover:bg-muted"
              >
                Cerrar
              </button>
            </div>
            {groups.map(({ title, links: items }) => (
              <div key={title} className="mb-4">
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  {title}
                </h3>
                <div className="grid grid-cols-2 gap-1">
                  {items.map(([to, label]) => (
                    <NavLink
                      key={to}
                      to={to}
                      end={to === '/'}
                      onClick={() => setOpenAt(null)}
                      className={({ isActive }) =>
                        `rounded-lg px-3 py-3 text-sm ${isActive ? 'bg-primary/10 font-semibold text-primary' : 'hover:bg-muted'}`
                      }
                    >
                      {label}
                    </NavLink>
                  ))}
                </div>
              </div>
            ))}
            <button
              type="button"
              disabled={loggingOut}
              onClick={logout}
              className="w-full rounded-lg border border-border px-4 py-3 text-sm font-medium hover:bg-muted disabled:opacity-50"
            >
              {loggingOut ? 'Cerrando…' : 'Cerrar sesión'}
            </button>
          </section>
        </>
      )}
    </>
  )
}

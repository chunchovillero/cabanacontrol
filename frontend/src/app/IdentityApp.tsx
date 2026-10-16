import { lazy, Suspense, useState } from 'react'
import { Link, Route, Routes, useLocation } from 'react-router-dom'
import { LandingPage } from '@/features/marketing/LandingPage'
import { useQueryClient } from '@tanstack/react-query'
import { AuthProvider, useAuth } from '@/features/auth/AuthProvider'
import { RegisterPage } from '@/features/auth/RegisterPage'
import { SettingsPage } from '@/features/auth/SettingsPage'
const PlanPage = lazy(() =>
  import('@/features/billing/PlanPage').then((m) => ({ default: m.PlanPage })),
)
const SimulationPage = lazy(() =>
  import('@/features/billing/SimulationPage').then((m) => ({ default: m.SimulationPage })),
)
import { LoginPage, RecoverPage, ResetPage } from '@/features/auth/AuthPages'
import { CompanyPage } from '@/features/auth/CompanyPage'
import { AppNavigation } from '@/features/auth/AppNavigation'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import { HealthPage } from './HealthPage'
import { PropertyAccess } from '@/features/properties/PropertyAccess'
import { PropertyList } from '@/features/properties/PropertyList'
import { PropertyForm } from '@/features/properties/PropertyForm'
import { PropertyDetail } from '@/features/properties/PropertyDetail'
import { TenantAccess } from '@/features/auth/TenantAccess'
import { GuestList } from '@/features/guests/GuestList'
import { GuestForm } from '@/features/guests/GuestForm'
import { GuestDetail } from '@/features/guests/GuestDetail'
const UsersPage = lazy(() =>
  import('@/features/team/UsersPage').then((m) => ({ default: m.UsersPage })),
)
const AcceptInvitationPage = lazy(() =>
  import('@/features/team/AcceptInvitationPage').then((m) => ({ default: m.AcceptInvitationPage })),
)
const ReservationList = lazy(() =>
  import('@/features/reservations/ReservationList').then((m) => ({ default: m.ReservationList })),
)
const ReservationForm = lazy(() =>
  import('@/features/reservations/ReservationForm').then((m) => ({ default: m.ReservationForm })),
)
const ReservationDetail = lazy(() =>
  import('@/features/reservations/ReservationDetail').then((m) => ({
    default: m.ReservationDetail,
  })),
)
const AvailabilityPage = lazy(() =>
  import('@/features/reservations/AvailabilityPage').then((m) => ({ default: m.AvailabilityPage })),
)
const BlockList = lazy(() =>
  import('@/features/reservations/Blocks').then((m) => ({ default: m.BlockList })),
)
const BlockForm = lazy(() =>
  import('@/features/reservations/Blocks').then((m) => ({ default: m.BlockForm })),
)
const DashboardPage = lazy(() =>
  import('@/features/dashboard/DashboardPage').then((m) => ({ default: m.DashboardPage })),
)

const CalendarPage = lazy(() =>
  import('@/features/calendar/CalendarPage').then((m) => ({ default: m.CalendarPage })),
)

const ReportsPage = lazy(() =>
  import('@/features/reports/ReportsPage').then((m) => ({ default: m.ReportsPage })),
)

const OperationsPage = lazy(() =>
  import('@/features/operations/OperationsPage').then((m) => ({ default: m.OperationsPage })),
)

const HousekeepingList = lazy(() =>
  import('@/features/operations/Housekeeping').then((m) => ({ default: m.HousekeepingList })),
)
const HousekeepingCreate = lazy(() =>
  import('@/features/operations/Housekeeping').then((m) => ({ default: m.HousekeepingCreate })),
)
const HousekeepingDetail = lazy(() =>
  import('@/features/operations/Housekeeping').then((m) => ({ default: m.HousekeepingDetail })),
)
const AssistantPage = lazy(() =>
  import('@/features/assistant/AssistantPage').then((m) => ({ default: m.AssistantPage })),
)
const InquiryList = lazy(() =>
  import('@/features/inquiries/InquiryPages').then((m) => ({ default: m.InquiryList })),
)
const InquiryDetail = lazy(() =>
  import('@/features/inquiries/InquiryPages').then((m) => ({ default: m.InquiryDetail })),
)

const WhatsAppPage = lazy(() =>
  import('@/features/whatsapp/WhatsAppPage').then((m) => ({ default: m.WhatsAppPage })),
)
const WhatsAppConversation = lazy(() =>
  import('@/features/whatsapp/WhatsAppPage').then((m) => ({ default: m.WhatsAppConversation })),
)

function Shell() {
  const location = useLocation()
  const { session, loading, error, retry } = useAuth()
  const queryClient = useQueryClient()
  const [logoutError, setLogoutError] = useState('')
  const [loggingOut, setLoggingOut] = useState(false)
  const logout = async () => {
    setLoggingOut(true)
    setLogoutError('')
    try {
      await api.logout()
      await queryClient.cancelQueries()
      queryClient.removeQueries({
        predicate: (query) => query.queryKey[0] !== 'session',
      })
      queryClient.setQueryData(['session'], null)
    } catch (failure) {
      setLogoutError(failure instanceof Error ? failure.message : 'No se pudo cerrar sesión.')
      void queryClient.invalidateQueries({ queryKey: ['session'] })
    } finally {
      setLoggingOut(false)
    }
  }
  if (
    location.pathname === '/conocer' ||
    (location.pathname === '/' && !session && !loading && !error)
  ) {
    return <LandingPage signedIn={!!session} />
  }
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border bg-white px-5 py-4 sm:px-6">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3">
          <Link to="/" className="text-xl font-bold tracking-tight">
            CabañaControl<span className="text-primary">.</span>
          </Link>
          {session && (
            <AppNavigation
              session={session}
              loggingOut={loggingOut}
              logout={() => {
                void logout()
              }}
            />
          )}
        </div>
      </header>
      <main
        className={`mx-auto max-w-5xl px-5 py-8 sm:px-6 sm:py-12 ${session ? 'pb-[calc(6rem+env(safe-area-inset-bottom))] lg:pb-12' : ''}`}
      >
        {logoutError && (
          <p role="alert" className="mb-5 text-red-800">
            {logoutError}
          </p>
        )}
        {loading ? (
          <p role="status">Verificando sesión…</p>
        ) : error ? (
          <section role="alert">
            <p>{error.message}</p>
            <Button className="mt-4" onClick={retry}>
              Reintentar conexión
            </Button>
          </section>
        ) : (
          <Suspense fallback={<p role="status">Cargando pantalla…</p>}>
            <Routes>
              <Route path="/" element={<CompanyPage />} />
              <Route path="/ingresar" element={<LoginPage />} />
              <Route path="/registrarse" element={<RegisterPage />} />
              <Route path="/configuracion" element={<SettingsPage />} />
              <Route path="/plan" element={<TenantAccess />}>
                <Route index element={<PlanPage />} />
              </Route>
              <Route path="/contratacion-simulada" element={<TenantAccess />}>
                <Route index element={<SimulationPage />} />
              </Route>
              <Route path="/invitacion" element={<AcceptInvitationPage />} />
              <Route path="/usuarios" element={<TenantAccess />}>
                <Route index element={<UsersPage />} />
              </Route>
              <Route path="/recuperar" element={<RecoverPage />} />
              <Route path="/restablecer" element={<ResetPage />} />
              <Route path="/estado" element={<HealthPage />} />
              <Route path="/whatsapp" element={<TenantAccess />}>
                <Route index element={<WhatsAppPage />} />
                <Route path=":id" element={<WhatsAppConversation />} />
              </Route>
              <Route path="/asistente" element={<TenantAccess />}>
                <Route index element={<AssistantPage />} />
              </Route>
              <Route path="/consultas" element={<TenantAccess />}>
                <Route index element={<InquiryList />} />
                <Route path="nueva" element={<InquiryDetail />} />
                <Route path=":id" element={<InquiryDetail />} />
              </Route>
              <Route path="/cabanas" element={<PropertyAccess />}>
                <Route index element={<PropertyList />} />
                <Route path="nueva" element={<PropertyForm />} />
                <Route path=":id" element={<PropertyDetail />} />
                <Route path=":id/editar" element={<PropertyForm />} />
              </Route>
              <Route path="/huespedes" element={<TenantAccess />}>
                <Route index element={<GuestList />} />
                <Route path="nuevo" element={<GuestForm />} />
                <Route path=":id" element={<GuestDetail />} />
                <Route path=":id/editar" element={<GuestForm />} />
              </Route>
              <Route path="/limpieza" element={<TenantAccess />}>
                <Route index element={<HousekeepingList />} />
                <Route path="nueva" element={<HousekeepingCreate />} />
                <Route path=":id" element={<HousekeepingDetail />} />
              </Route>
              <Route path="/operacion" element={<TenantAccess />}>
                <Route index element={<OperationsPage />} />
              </Route>
              <Route path="/reportes" element={<TenantAccess />}>
                <Route index element={<ReportsPage />} />
              </Route>
              <Route path="/calendario" element={<TenantAccess />}>
                <Route index element={<CalendarPage />} />
              </Route>
              <Route path="/panel" element={<TenantAccess />}>
                <Route index element={<DashboardPage />} />
              </Route>
              <Route path="/reservas" element={<TenantAccess />}>
                <Route index element={<ReservationList />} />
                <Route path="nueva" element={<ReservationForm />} />
                <Route path="disponibilidad" element={<AvailabilityPage />} />
                <Route path="bloqueos" element={<BlockList />} />
                <Route path="bloqueos/nuevo" element={<BlockForm />} />
                <Route path="bloqueos/:id/editar" element={<BlockForm />} />
                <Route path=":id" element={<ReservationDetail />} />
                <Route path=":id/editar" element={<ReservationForm />} />
              </Route>
              <Route
                path="*"
                element={
                  <section>
                    <h1 className="text-2xl font-bold">Página no encontrada</h1>
                    <Link to="/" className="mt-4 inline-block text-primary underline">
                      Ir al inicio
                    </Link>
                  </section>
                }
              />
            </Routes>
          </Suspense>
        )}
      </main>
    </div>
  )
}

export function IdentityApp() {
  return (
    <AuthProvider>
      <Shell />
    </AuthProvider>
  )
}

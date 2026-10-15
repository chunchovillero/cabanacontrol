import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useTenantContext } from '@/features/auth/TenantAccess'
import { monthPeriod } from '@/features/dashboard/DashboardPage'
import { formatMoney } from '@/features/properties/api'
import { formatDate, todayInZone } from '@/features/reservations/dates'
import { reportApi, type ReportFilters, type ReportKind } from './api'
import { PropertyFilter } from './PropertyFilter'
import { ReportSummary } from './ReportSummary'

export function ReportsPage() {
  const { tenant } = useTenantContext()
  const initial = monthPeriod(todayInZone(tenant.timezone))
  const [start, setStart] = useState(initial.start)
  const [end, setEnd] = useState(initial.end)
  const [filters, setFilters] = useState<ReportFilters>({
    ...initial,
    property: '',
    kind: 'summary',
    status: '',
  })
  const [page, setPage] = useState(1)
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState('')
  const controller = useRef<AbortController | null>(null)
  useEffect(() => () => controller.current?.abort(), [])
  const result = useQuery({
    queryKey: ['reports', tenant.id, filters, page],
    queryFn: () => reportApi.get(tenant.id, filters, page),
  })
  const change = (values: Partial<ReportFilters>) => {
    setFilters({ ...filters, ...values })
    setPage(1)
    setDownloadError('')
    controller.current?.abort()
    setDownloading(false)
  }
  const download = async () => {
    const active = new AbortController()
    controller.current = active
    setDownloading(true)
    setDownloadError('')
    try {
      const blob = await reportApi.download(tenant.id, filters, active.signal)
      if (active.signal.aborted) return
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `cabanacontrol-${filters.kind}-${filters.start}-${filters.end}.csv`
      anchor.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (error) {
      if (!active.signal.aborted)
        setDownloadError(error instanceof Error ? error.message : 'No se pudo exportar.')
    } finally {
      if (!active.signal.aborted) setDownloading(false)
    }
  }
  return (
    <section>
      <p className="text-sm text-muted-foreground">{tenant.name}</p>
      <h1 className="mt-2 text-3xl font-bold">Reportes y exportaciones</h1>
      <p className="mt-3 text-sm text-muted-foreground">
        Periodo con fin exclusivo · {tenant.timezone}. CSV con los mismos filtros y todas las
        páginas, hasta 5.000 filas. Sin documentos, contactos ni notas de huéspedes.
      </p>
      <form
        className="mt-6 grid gap-4 rounded-xl border bg-white p-5 sm:grid-cols-2"
        onSubmit={(e) => {
          e.preventDefault()
          change({ start, end })
        }}
      >
        <label>
          Desde
          <input
            required
            type="date"
            className="mt-2 w-full rounded-lg border p-3"
            value={start}
            onChange={(e) => setStart(e.target.value)}
          />
        </label>
        <label>
          Hasta (exclusiva)
          <input
            required
            type="date"
            className="mt-2 w-full rounded-lg border p-3"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
          />
        </label>
        <Button type="submit">Aplicar periodo</Button>
        <p className="text-sm">
          Periodo aplicado: {formatDate(filters.start)} → {formatDate(filters.end)}
        </p>
      </form>
      <div className="mt-4 rounded-xl border bg-white p-5">
        <PropertyFilter
          tenant={tenant.id}
          value={filters.property}
          onChange={(property) => change({ property })}
        />
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="report-kind">Reporte</label>
            <select
              id="report-kind"
              className="mt-2 w-full rounded-lg border bg-white p-3"
              value={filters.kind}
              onChange={(e) => change({ kind: e.target.value as ReportKind, status: '' })}
            >
              <option value="summary">Resumen y ocupación</option>
              <option value="reservations">Reservas por fecha de entrada</option>
              <option value="payments">Cobros por fecha de pago</option>
            </select>
          </div>
          {filters.kind === 'reservations' && (
            <div>
              <label htmlFor="report-status">Estado de reserva</label>
              <select
                id="report-status"
                className="mt-2 w-full rounded-lg border bg-white p-3"
                value={filters.status}
                onChange={(e) => change({ status: e.target.value })}
              >
                <option value="">Todos los estados</option>
                <option value="draft">Borrador</option>
                <option value="pending">Pendiente</option>
                <option value="confirmed">Confirmada</option>
                <option value="checked_in">En estadía</option>
                <option value="checked_out">Finalizada</option>
                <option value="cancelled">Cancelada</option>
                <option value="no_show">Ausencia</option>
              </select>
            </div>
          )}
        </div>
      </div>
      <div className="mt-5 flex flex-wrap gap-3">
        <Button
          disabled={downloading || !result.data || Boolean(result.error) || result.isFetching}
          onClick={() => {
            void download()
          }}
        >
          {downloading ? 'Preparando CSV…' : 'Descargar CSV'}
        </Button>
        <Button
          variant="outline"
          onClick={() => {
            void result.refetch()
          }}
        >
          Actualizar reporte
        </Button>
      </div>
      {downloadError && (
        <p role="alert" className="mt-4 text-red-800">
          {downloadError}
        </p>
      )}
      {result.isPending && (
        <p role="status" className="mt-5">
          Cargando reporte…
        </p>
      )}
      {result.error && (
        <p role="alert" className="mt-5 text-red-800">
          {result.error.message}
        </p>
      )}
      {result.data?.kind === 'summary' && <ReportSummary data={result.data.data} />}
      {result.data && result.data.kind !== 'summary' && (
        <>
          <p className="mt-6">
            {result.data.data.count} registros · Página {page}
          </p>
          {!result.data.data.count && <p className="mt-4">No hay registros para estos filtros.</p>}
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            {result.data.kind === 'reservations'
              ? result.data.data.results.map((row) => (
                  <article key={row.id} className="min-w-0 rounded-xl border bg-white p-5">
                    <h2 className="break-words font-semibold">
                      <Link to={`/reservas/${row.id}`} className="text-primary underline">
                        {row.property_name} · {row.status_label}
                      </Link>
                    </h2>
                    <p className="mt-2">
                      {formatDate(row.check_in)} → {formatDate(row.check_out)} (salida)
                    </p>
                    <p>{row.property_active ? 'Cabaña activa' : 'Cabaña inactiva'}</p>
                    <p className="mt-3">Pactado: {formatMoney(row.total_amount, row.currency)}</p>
                    <p>Recibido válido actual: {formatMoney(row.received_amount, row.currency)}</p>
                    <p>Saldo actual: {formatMoney(row.balance, row.currency)}</p>
                    <p className="mt-2 break-all text-xs text-muted-foreground">
                      Reserva: {row.id}
                    </p>
                  </article>
                ))
              : result.data.data.results.map((row) => (
                  <article key={row.id} className="min-w-0 rounded-xl border bg-white p-5">
                    <h2 className="break-words font-semibold">
                      <Link
                        to={`/reservas/${row.reservation_id}`}
                        className="text-primary underline"
                      >
                        {row.property_name}
                      </Link>
                    </h2>
                    <p className="mt-3">
                      {formatMoney(row.amount, row.currency)} · {row.method_label}
                    </p>
                    <p>
                      {new Intl.DateTimeFormat('es-CL', {
                        dateStyle: 'short',
                        timeStyle: 'short',
                        timeZone: tenant.timezone,
                      }).format(new Date(row.paid_at))}
                    </p>
                    <p className="mt-2 break-all text-xs text-muted-foreground">Pago: {row.id}</p>
                  </article>
                ))}
          </div>
          <div className="mt-5 flex flex-wrap gap-3">
            <Button
              variant="outline"
              disabled={!result.data.data.previous}
              onClick={() => setPage(page - 1)}
            >
              Página anterior
            </Button>
            <Button
              variant="outline"
              disabled={!result.data.data.next}
              onClick={() => setPage(page + 1)}
            >
              Página siguiente
            </Button>
          </div>
        </>
      )}
    </section>
  )
}

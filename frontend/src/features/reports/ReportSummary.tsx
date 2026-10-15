import { formatMoney } from '@/features/properties/api'
import type { Summary } from './api'

export function ReportSummary({ data }: { data: Summary }) {
  return (
    <section className="mt-6">
      <h2 className="text-xl font-semibold">Resumen del periodo</h2>
      <p className="mt-3">
        Ocupación: {data.occupancy_percent.replace('.', ',')} % · {data.occupied_nights} noches
        reservadas / {data.capacity_nights} noches base.
      </p>
      <p className="mt-2">
        Noches bloqueadas: {data.blocked_nights} · Reservas canceladas con entrada en el periodo:{' '}
        {data.cancelled_count}
      </p>
      <p className="mt-3 text-sm text-muted-foreground">
        Ocupación sobre cabañas actualmente activas, sin sumar retenciones ni descontar bloqueos.
        Cobrado por fecha de pago válido; pactado y saldos por fecha de entrada. Deuda y saldo a
        favor se muestran separados. Importes y estados actuales, no un balance histórico al cierre.
      </p>
      {data.money.map((row) => (
        <dl key={row.currency} className="mt-5 grid gap-4 sm:grid-cols-2">
          {(
            [
              ['Cobrado', row.collected],
              ['Pactado', row.agreed],
              ['Deuda', row.outstanding],
              ['Saldo a favor', row.credit],
            ] as const
          ).map(([label, amount]) => (
            <div key={label} className="rounded-xl border bg-white p-5">
              <dt>
                {label} · {row.currency}
              </dt>
              <dd className="mt-2 break-words text-2xl font-semibold">
                {formatMoney(amount, row.currency)}
              </dd>
            </div>
          ))}
        </dl>
      ))}
    </section>
  )
}

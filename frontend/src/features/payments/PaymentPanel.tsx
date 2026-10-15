import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { useTenantContext } from '@/features/auth/TenantAccess'
import { formatMoney } from '@/features/properties/api'
import type { Reservation } from '@/features/reservations/api'
import { holdToIso, localHold, formatHold } from '@/features/reservations/dates'
import { paymentApi, methodLabels, paymentLabels, type Payment } from './api'
import { paymentFormSchema, validateReceipt } from './validation'

const inputClass =
  'mt-2 w-full rounded-lg border border-border bg-white px-3 py-3 focus-visible:outline-2 focus-visible:outline-primary'
function PaymentForm({
  reservation,
  onSaved,
  onClose,
}: {
  reservation: Reservation
  onSaved: (warning: string) => Promise<void>
  onClose: () => void
}) {
  const { tenant } = useTenantContext()
  const [requestId] = useState(() => crypto.randomUUID())
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState('')
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof paymentFormSchema>>({
    resolver: zodResolver(paymentFormSchema),
    defaultValues: {
      amount: '',
      paid_at: localHold(new Date().toISOString(), tenant.timezone),
      method: 'transfer',
      reference: '',
    },
  })
  const submit = handleSubmit(async (values) => {
    setError('')
    try {
      if (file) validateReceipt(file)
      const saved = await paymentApi.record(tenant.id, reservation.id, {
        ...values,
        amount: values.amount.replace(',', '.'),
        paid_at: holdToIso(values.paid_at, tenant.timezone),
        request_id: requestId,
      })
      let warning = ''
      if (file && !saved.receipt_url) {
        try {
          await paymentApi.receipt(tenant.id, saved.id, file)
        } catch {
          warning =
            'El abono está registrado. No se pudo adjuntar el comprobante; puedes hacerlo desde su historial.'
        }
      }
      await onSaved(warning)
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : 'No se pudo registrar el abono. Revisa el historial antes de iniciar otro registro.',
      )
    }
  })
  return (
    <form
      noValidate
      className="mt-5 space-y-5 rounded-xl border border-border bg-white p-5"
      onSubmit={(e) => {
        void submit(e)
      }}
    >
      <h3 className="text-lg font-semibold">Registrar abono</h3>
      <div className="grid gap-5 sm:grid-cols-2">
        <label className="text-sm font-medium">
          Monto del abono ({reservation.currency})
          <input inputMode="decimal" className={inputClass} {...register('amount')} />
        </label>
        <div>
          <label htmlFor="payment-date" className="text-sm font-medium">
            Fecha y hora del pago
          </label>
          <input
            id="payment-date"
            aria-describedby="payment-zone"
            type="datetime-local"
            className={inputClass}
            {...register('paid_at')}
          />
          <p id="payment-zone" className="mt-2 text-xs text-muted-foreground">
            Hora de {tenant.timezone}. Corresponde al momento en que recibiste el pago.
          </p>
        </div>
        <div>
          <label htmlFor="payment-method" className="text-sm font-medium">
            Método de pago
          </label>
          <select id="payment-method" className={inputClass} {...register('method')}>
            {Object.entries(methodLabels).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <label className="text-sm font-medium">
          Referencia de operación (opcional)
          <input
            maxLength={150}
            autoComplete="off"
            className={inputClass}
            {...register('reference')}
          />
        </label>
      </div>
      <div>
        <label htmlFor="payment-file" className="text-sm font-medium">
          Comprobante (opcional)
        </label>
        <input
          id="payment-file"
          aria-describedby="payment-file-help"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className={inputClass}
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <p id="payment-file-help" className="mt-2 text-xs text-muted-foreground">
          JPG, PNG o WebP; hasta 5 MB y 4096 píxeles por lado. No incluyas datos de tarjetas.
        </p>
      </div>
      {reservation.status === 'pending' && (
        <p className="text-sm text-muted-foreground">
          Registrar el abono no confirma la reserva ni renueva su retención.
        </p>
      )}
      {Object.entries(errors).map(([key, value]) => (
        <p key={key} role="alert" className="text-sm text-red-800">
          {value?.message}
        </p>
      ))}
      {error && (
        <p role="alert" className="text-red-800">
          {error}
        </p>
      )}
      <div className="flex flex-wrap gap-3">
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Registrando…' : 'Guardar abono'}
        </Button>
        <Button type="button" variant="outline" disabled={isSubmitting} onClick={onClose}>
          Volver sin registrar
        </Button>
      </div>
    </form>
  )
}

function ReceiptForm({ payment, onSaved }: { payment: Payment; onSaved: () => Promise<void> }) {
  const { tenant } = useTenantContext()
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  async function submit() {
    setError('')
    setSaving(true)
    try {
      validateReceipt(file!)
      await paymentApi.receipt(tenant.id, payment.id, file!)
      await onSaved()
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'No se pudo adjuntar el comprobante.')
    } finally {
      setSaving(false)
    }
  }
  return (
    <div className="mt-4">
      <label htmlFor={`receipt-${payment.id}`} className="text-sm">
        Adjuntar comprobante
      </label>
      <input
        id={`receipt-${payment.id}`}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className={inputClass}
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
      />
      {error && (
        <p role="alert" className="mt-2 text-red-800">
          {error}
        </p>
      )}
      <Button
        className="mt-3"
        variant="outline"
        disabled={!file || saving}
        onClick={() => {
          void submit()
        }}
      >
        {saving ? 'Adjuntando…' : 'Guardar comprobante'}
      </Button>
    </div>
  )
}

export function PaymentPanel({ reservation }: { reservation: Reservation }) {
  const { tenant } = useTenantContext()
  const client = useQueryClient()
  const [page, setPage] = useState(1)
  const [creating, setCreating] = useState(false)
  const [voiding, setVoiding] = useState<Payment | null>(null)
  const [reason, setReason] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [saving, setSaving] = useState(false)
  const result = useQuery({
    queryKey: ['payments', tenant.id, reservation.id, page],
    queryFn: () => paymentApi.list(tenant.id, reservation.id, page),
    refetchInterval: 30_000,
  })
  const chargeable = ['pending', 'confirmed', 'checked_in', 'checked_out'].includes(
    reservation.status,
  )
  async function refresh() {
    await Promise.all([
      client.invalidateQueries({ queryKey: ['payments', tenant.id, reservation.id] }),
      client.invalidateQueries({ queryKey: ['reservation', tenant.id, reservation.id] }),
      client.invalidateQueries({ queryKey: ['reservations', tenant.id] }),
    ])
  }
  async function saved(warning: string) {
    setCreating(false)
    setPage(1)
    setNotice(warning || 'Abono registrado.')
    await refresh()
  }
  async function annul() {
    setError('')
    setSaving(true)
    try {
      await paymentApi.void(tenant.id, voiding!.id, reason)
      setVoiding(null)
      setReason('')
      setNotice('Pago anulado; el historial se conserva.')
      await refresh()
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'No se pudo anular el pago.')
    } finally {
      setSaving(false)
    }
  }
  return (
    <section aria-labelledby="payments-title" className="mt-10 border-t border-border pt-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 id="payments-title" className="text-2xl font-bold">
          Pagos y abonos
        </h2>
        {chargeable && !creating && (
          <Button
            onClick={() => {
              setCreating(true)
              setNotice('')
            }}
          >
            Registrar abono
          </Button>
        )}
      </div>
      <dl className="mt-5 grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border bg-white p-5">
          <dt className="text-sm text-muted-foreground">Recibido válido</dt>
          <dd className="mt-2 text-xl font-semibold">
            {formatMoney(reservation.received_amount, reservation.currency)}
          </dd>
        </div>
        <div className="rounded-xl border bg-white p-5">
          <dt className="text-sm text-muted-foreground">
            {reservation.payment_state === 'credit' ? 'Saldo a favor' : 'Saldo de la reserva'}
          </dt>
          <dd className="mt-2 text-xl font-semibold">
            {formatMoney(reservation.balance.replace(/^-/, ''), reservation.currency)}
          </dd>
        </div>
        <div className="rounded-xl border bg-white p-5">
          <dt className="text-sm text-muted-foreground">Estado del pago</dt>
          <dd className="mt-2 font-semibold">{paymentLabels[reservation.payment_state]}</dd>
        </div>
      </dl>
      {!chargeable && (
        <p className="mt-4 text-sm text-muted-foreground">
          Esta reserva no admite abonos nuevos ni aparece en el listado de deuda. El importe y los
          pagos se conservan; no se generan devoluciones.
        </p>
      )}
      {notice && (
        <p role="status" className="mt-4 rounded-lg bg-muted p-4 text-sm">
          {notice}
        </p>
      )}
      {creating && chargeable && (
        <PaymentForm reservation={reservation} onSaved={saved} onClose={() => setCreating(false)} />
      )}
      {result.isPending && (
        <p role="status" className="mt-5">
          Cargando pagos…
        </p>
      )}
      {result.error && (
        <p role="alert" className="mt-5 text-red-800">
          {result.error.message}
        </p>
      )}
      {result.data?.count === 0 && (
        <p className="mt-6 text-muted-foreground">No hay abonos registrados.</p>
      )}
      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {result.data?.results.map((payment) => (
          <article key={payment.id} className="min-w-0 rounded-xl border bg-white p-5">
            <span className="rounded-full bg-muted px-3 py-1 text-xs">
              {payment.status === 'voided' ? 'Anulado' : 'Registrado'}
            </span>
            <h3 className="mt-4 text-xl font-semibold">
              {formatMoney(payment.amount, payment.currency)}
            </h3>
            <p className="mt-2 text-sm">
              {methodLabels[payment.method]} · {formatHold(payment.paid_at, tenant.timezone)}
            </p>
            {payment.reference && (
              <p className="mt-3 break-words text-sm text-muted-foreground">
                Referencia: {payment.reference}
              </p>
            )}
            {payment.void_reason && (
              <p className="mt-3 whitespace-pre-wrap break-words text-sm">
                Motivo: {payment.void_reason}
              </p>
            )}
            {payment.receipt_url && (
              <a
                href={payment.receipt_url}
                className="mt-4 inline-block text-sm text-primary underline"
              >
                Descargar comprobante
              </a>
            )}
            {payment.status === 'recorded' && (
              <>
                <div className="mt-4">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setVoiding(payment)
                      setReason('')
                      setError('')
                    }}
                  >
                    Anular pago
                  </Button>
                </div>
                {!payment.receipt_url && <ReceiptForm payment={payment} onSaved={refresh} />}
              </>
            )}
          </article>
        ))}
      </div>
      {result.data && result.data.count > 0 && (
        <div className="mt-6 flex flex-wrap items-center gap-4">
          <Button
            variant="outline"
            disabled={!result.data.previous}
            onClick={() => setPage(page - 1)}
          >
            Pagos anteriores
          </Button>
          <span className="text-sm">
            Página {page} · {result.data.count} pagos
          </span>
          <Button variant="outline" disabled={!result.data.next} onClick={() => setPage(page + 1)}>
            Más pagos
          </Button>
        </div>
      )}
      {voiding && (
        <div
          role="dialog"
          aria-label="Anular pago"
          className="mt-6 space-y-4 rounded-xl border bg-white p-6"
        >
          <h3 className="font-semibold">Anular {formatMoney(voiding.amount, voiding.currency)}</h3>
          <p className="text-sm">
            Se conservará el pago y su comprobante. Esta acción corrige el registro; no realiza una
            devolución.
          </p>
          <label className="block text-sm">
            Motivo de anulación
            <textarea
              maxLength={1000}
              rows={3}
              className={inputClass}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </label>
          {error && (
            <p role="alert" className="text-red-800">
              {error}
            </p>
          )}
          <div className="flex flex-wrap gap-3">
            <Button
              disabled={saving || !reason.trim()}
              onClick={() => {
                void annul()
              }}
            >
              {saving ? 'Anulando…' : 'Confirmar anulación'}
            </Button>
            <Button disabled={saving} variant="outline" onClick={() => setVoiding(null)}>
              Volver sin anular
            </Button>
          </div>
        </div>
      )}
    </section>
  )
}

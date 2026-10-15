import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { useTenantContext } from '@/features/auth/TenantAccess'
import { guestApi } from '@/features/guests/api'
import { propertyApi } from '@/features/properties/api'
import { reservationApi, sourceLabels, statusLabels, type Reservation } from './api'
import { holdToIso, localHold, todayInZone } from './dates'
import { reservationFormSchema } from './validation'
import { inquiryApi, type Inquiry } from '@/features/inquiries/api'

type Values = z.infer<typeof reservationFormSchema>
export const inputClass =
  'mt-2 w-full rounded-lg border border-border bg-white px-3 py-3 focus-visible:outline-2 focus-visible:outline-primary'

export function ReservationEditor({ item, inquiry }: { item?: Reservation; inquiry?: Inquiry }) {
  const { tenant } = useTenantContext()
  const navigate = useNavigate()
  const client = useQueryClient()
  const [error, setError] = useState('')
  const [reviewed, setReviewed] = useState(false)
  const [propertySearch, setPropertySearch] = useState('')
  const [propertyPage, setPropertyPage] = useState(1)
  const [guestSearch, setGuestSearch] = useState('')
  const [guestPage, setGuestPage] = useState(1)
  const props = useQuery({
    queryKey: ['properties', tenant.id, propertySearch, propertyPage],
    queryFn: () => propertyApi.list(tenant.id, propertySearch, 'true', propertyPage),
  })
  const guests = useQuery({
    queryKey: ['guests', tenant.id, guestSearch, guestPage],
    queryFn: () => guestApi.search(tenant.id, guestSearch, 'true', guestPage),
  })
  const {
    register,
    watch,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(reservationFormSchema),
    defaultValues: {
      property_id: item?.property_id ?? '',
      primary_guest_id: item?.primary_guest_id ?? '',
      check_in: item?.check_in ?? '',
      check_out: item?.check_out ?? '',
      adults: item?.adults ?? 1,
      children: item?.children ?? 0,
      total_amount: item?.total_amount ?? '',
      source:
        item?.source ??
        (inquiry?.channel === 'phone'
          ? 'phone'
          : inquiry?.channel === 'whatsapp_manual' || inquiry?.channel === 'whatsapp_api'
            ? 'whatsapp'
            : inquiry
              ? 'other'
              : 'direct'),
      notes: item?.notes ?? '',
      status:
        item?.status === 'pending'
          ? 'pending'
          : item?.status === 'confirmed'
            ? 'confirmed'
            : 'draft',
      hold_until: item?.hold_until ? localHold(item.hold_until, tenant.timezone) : '',
    },
  })
  const values = watch()
  const preview = useQuery({
    queryKey: [
      'availability',
      tenant.id,
      values.property_id,
      values.check_in,
      values.check_out,
      values.adults,
      values.children,
      item?.id,
    ],
    queryFn: () =>
      reservationApi.availability(
        tenant.id,
        values.check_in,
        values.check_out,
        values.adults + values.children,
        values.property_id,
      ),
    enabled: Boolean(
      values.property_id &&
      values.check_in >= todayInZone(tenant.timezone) &&
      values.check_out > values.check_in &&
      values.adults >= 1 &&
      values.children >= 0,
    ),
  })
  const submit = handleSubmit(async (data) => {
    setError('')
    try {
      const { status, hold_until, ...fields } = data
      const saved = inquiry
        ? await inquiryApi.convert(tenant.id, inquiry.id, inquiry.revision, {
            ...fields,
          })
        : await reservationApi.save(
            tenant.id,
            {
              ...fields,
              ...(item ? {} : { status }),
              hold_until: status === 'pending' ? holdToIso(hold_until, tenant.timezone) : null,
            },
            item?.id,
          )
      await client.invalidateQueries({ queryKey: ['reservations', tenant.id] })
      await client.invalidateQueries({ queryKey: ['availability', tenant.id] })
      client.setQueryData(['reservation', tenant.id, saved.id], saved)
      navigate(`/reservas/${saved.id}`)
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'No se pudo guardar la reserva.')
    }
  })
  return (
    <form
      noValidate
      onSubmit={(event) => {
        void submit(event)
      }}
      onChange={(event) => {
        if (
          inquiry &&
          !(event.target instanceof HTMLInputElement && event.target.type === 'checkbox')
        )
          setReviewed(false)
      }}
      className="mt-7 space-y-6 rounded-xl border border-border bg-white p-5 sm:p-7"
    >
      <div className="grid gap-6 sm:grid-cols-2">
        <div>
          <label className="text-sm font-medium" htmlFor="property-search">
            Buscar cabaña
          </label>
          <input
            id="property-search"
            className={inputClass}
            value={propertySearch}
            onChange={(e) => {
              setPropertySearch(e.target.value)
              setPropertyPage(1)
            }}
            maxLength={150}
          />
          <label className="mt-4 block text-sm font-medium" htmlFor="reservation-property">
            Cabaña
          </label>
          <select id="reservation-property" className={inputClass} {...register('property_id')}>
            <option value="">Seleccionar cabaña</option>
            {item && !props.data?.results.some((p) => p.id === item.property_id) && (
              <option value={item.property_id}>{item.property_name}</option>
            )}
            {props.data?.results.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} · {p.capacity} personas
              </option>
            ))}
          </select>
          {props.isPending && <p role="status">Cargando cabañas…</p>}
          {props.error && <p role="alert">{props.error.message}</p>}
          <div className="mt-3 flex flex-wrap gap-3">
            <Button
              type="button"
              variant="outline"
              disabled={!props.data?.previous}
              onClick={() => setPropertyPage(propertyPage - 1)}
            >
              Cabañas anteriores
            </Button>
            <Button
              type="button"
              variant="outline"
              disabled={!props.data?.next}
              onClick={() => setPropertyPage(propertyPage + 1)}
            >
              Más cabañas
            </Button>
          </div>
        </div>
        <div>
          <label className="text-sm font-medium" htmlFor="reservation-guest-search">
            Buscar huésped
          </label>
          <input
            id="reservation-guest-search"
            className={inputClass}
            value={guestSearch}
            onChange={(e) => {
              setGuestSearch(e.target.value)
              setGuestPage(1)
            }}
            maxLength={150}
            autoComplete="off"
          />
          <label className="mt-4 block text-sm font-medium" htmlFor="reservation-guest">
            Huésped principal
          </label>
          <select id="reservation-guest" className={inputClass} {...register('primary_guest_id')}>
            <option value="">Seleccionar huésped</option>
            {item && !guests.data?.results.some((g) => g.id === item.primary_guest_id) && (
              <option value={item.primary_guest_id}>
                {item.guest.first_name} {item.guest.last_name}
              </option>
            )}
            {guests.data?.results.map((g) => (
              <option key={g.id} value={g.id}>
                {g.first_name} {g.last_name} · {g.document_masked}
              </option>
            ))}
          </select>
          {guests.isPending && <p role="status">Cargando huéspedes…</p>}
          {guests.error && <p role="alert">{guests.error.message}</p>}
          <div className="mt-3 flex flex-wrap gap-3">
            <Button
              type="button"
              variant="outline"
              disabled={!guests.data?.has_previous}
              onClick={() => setGuestPage(guestPage - 1)}
            >
              Huéspedes anteriores
            </Button>
            <Button
              type="button"
              variant="outline"
              disabled={!guests.data?.has_next}
              onClick={() => setGuestPage(guestPage + 1)}
            >
              Más huéspedes
            </Button>
          </div>
          {tenant.role !== 'staff' && (
            <Link
              className="mt-3 inline-block text-sm text-primary underline"
              to="/huespedes/nuevo"
            >
              Registrar un huésped
            </Link>
          )}
        </div>
        <label className="text-sm font-medium">
          Entrada
          <input
            type="date"
            className={inputClass}
            min={item?.check_in ?? todayInZone(tenant.timezone)}
            {...register('check_in')}
          />
        </label>
        <label className="text-sm font-medium">
          Salida (exclusiva)
          <input type="date" className={inputClass} {...register('check_out')} />
        </label>
        <label className="text-sm font-medium">
          Adultos
          <input
            type="number"
            min="1"
            max="32767"
            className={inputClass}
            {...register('adults', { valueAsNumber: true })}
          />
        </label>
        <label className="text-sm font-medium">
          Niños
          <input
            type="number"
            min="0"
            max="32767"
            className={inputClass}
            {...register('children', { valueAsNumber: true })}
          />
        </label>
        <div>
          <label htmlFor="reservation-total" className="text-sm font-medium">
            Precio total pactado ({tenant.currency})
          </label>
          <input
            id="reservation-total"
            aria-describedby="reservation-price-help"
            inputMode="decimal"
            className={inputClass}
            {...register('total_amount')}
            placeholder="150000.00"
          />
          <span id="reservation-price-help" className="mt-2 block text-xs text-muted-foreground">
            Precio total ingresado manualmente. Usa punto para los decimales.
          </span>
        </div>
        <div>
          <label htmlFor="reservation-source" className="text-sm font-medium">
            Origen
          </label>
          <select id="reservation-source" className={inputClass} {...register('source')}>
            {Object.entries(sourceLabels).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </div>
        {!item && !inquiry && (
          <div>
            <label htmlFor="reservation-status" className="text-sm font-medium">
              Estado inicial
            </label>
            <select id="reservation-status" className={inputClass} {...register('status')}>
              {(['draft', 'pending', 'confirmed'] as const).map((key) => (
                <option key={key} value={key}>
                  {statusLabels[key]}
                </option>
              ))}
            </select>
          </div>
        )}
        {values.status === 'pending' && (
          <div>
            <label htmlFor="reservation-hold" className="text-sm font-medium">
              Retener hasta
            </label>
            <input
              id="reservation-hold"
              aria-describedby="reservation-hold-help"
              type="datetime-local"
              className={inputClass}
              {...register('hold_until')}
            />
            <span id="reservation-hold-help" className="mt-2 block text-xs text-muted-foreground">
              Hora local de la empresa: {tenant.timezone}. Al vencer, las fechas se liberan.
            </span>
          </div>
        )}
      </div>
      {preview.data && (
        <p role="status" className="rounded-lg bg-muted p-4 text-sm">
          {preview.data.results[0]?.available
            ? 'Disponible para las fechas y personas indicadas.'
            : item
              ? 'La consulta incluye esta reserva. Al guardar se comprobarán los demás conflictos.'
              : 'No disponible: revisa ocupación, reservas y bloqueos.'}{' '}
          La disponibilidad se vuelve a comprobar al guardar.
        </p>
      )}
      {preview.error && <p role="alert">{preview.error.message}</p>}
      <label className="block text-sm font-medium">
        Notas operativas (opcional)
        <textarea rows={3} maxLength={2000} className={inputClass} {...register('notes')} />
      </label>
      {Object.entries(errors).map(([key, value]) => (
        <p role="alert" className="text-sm text-red-800" key={key}>
          {value?.message}
        </p>
      ))}
      {error && (
        <p role="alert" className="text-red-800">
          {error}
        </p>
      )}
      {inquiry && (
        <label className="flex items-start gap-3">
          <input
            type="checkbox"
            checked={reviewed}
            onChange={(event) => setReviewed(event.target.checked)}
          />
          Revisé huésped, cabaña, fechas, ocupación y precio. Crear un borrador no retiene
          disponibilidad.
        </label>
      )}
      <div className="flex flex-wrap gap-4">
        <Button disabled={isSubmitting || (!!inquiry && !reviewed)} type="submit">
          {isSubmitting ? 'Guardando…' : inquiry ? 'Convertir a borrador' : 'Guardar reserva'}
        </Button>
        <Button variant="outline" asChild>
          <Link to={item ? `/reservas/${item.id}` : '/reservas'}>Volver</Link>
        </Button>
      </div>
    </form>
  )
}

export function ReservationForm() {
  const { id } = useParams()
  const { tenant } = useTenantContext()
  const result = useQuery({
    queryKey: ['reservation', tenant.id, id],
    queryFn: () => reservationApi.get(tenant.id, id!),
    enabled: Boolean(id),
  })
  if (id && result.isPending) return <p role="status">Cargando reserva…</p>
  if (id && result.error) return <p role="alert">{result.error.message}</p>
  if (result.data && ['cancelled', 'checked_out', 'no_show'].includes(result.data.status))
    return (
      <section>
        <p>Esta reserva está cerrada y conserva su historial.</p>
        <Link to={`/reservas/${id}`} className="text-primary underline">
          Volver a la reserva
        </Link>
      </section>
    )
  return (
    <section>
      <p className="text-sm text-muted-foreground">{tenant.name}</p>
      <h1 className="mt-2 text-3xl font-bold">{id ? 'Editar reserva' : 'Nueva reserva'}</h1>
      <p className="mt-3 text-muted-foreground">
        Estadía por noches. La fecha de salida no ocupa una noche adicional.
      </p>
      <ReservationEditor key={id ?? 'new'} item={result.data} />
    </section>
  )
}

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { useTenantContext } from '@/features/auth/TenantAccess'
import { documentLabels, duplicateGuestId, guestApi, type Guest } from './api'
import { guestFormSchema, normalizeRut } from './validation'

type Values = z.infer<typeof guestFormSchema>
const inputClass =
  'mt-2 w-full rounded-lg border border-border bg-white px-3 py-3 focus-visible:outline-2 focus-visible:outline-primary'
const labels = {
  first_name: 'Nombres',
  last_name: 'Apellidos',
  document_number: 'Número de documento',
  phone: 'Teléfono (opcional)',
  email: 'Correo electrónico (opcional)',
  notes: 'Notas restringidas (opcional)',
}

function Editor({ guest }: { guest?: Guest }) {
  const { tenant } = useTenantContext()
  const client = useQueryClient()
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const [duplicate, setDuplicate] = useState<string | null>(null)
  const {
    register,
    watch,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(guestFormSchema),
    defaultValues: {
      first_name: guest?.first_name ?? '',
      last_name: guest?.last_name ?? '',
      document_type: guest?.document_type ?? 'rut',
      document_number: guest?.document_number ?? '',
      phone: guest?.phone ?? '',
      email: guest?.email ?? '',
      notes: guest?.notes ?? '',
    },
  })
  const kind = watch('document_type')
  const submit = handleSubmit(async (values) => {
    setError('')
    setDuplicate(null)
    const data = {
      ...values,
      document_number:
        values.document_type === 'rut'
          ? normalizeRut(values.document_number)!
          : values.document_number.trim(),
      email: values.email.trim(),
    }
    try {
      const saved = guest
        ? await guestApi.update(tenant.id, guest.id, data)
        : await guestApi.create(tenant.id, data)
      client.setQueryData(['guest', tenant.id, saved.id], saved)
      await client.invalidateQueries({ queryKey: ['guests', tenant.id] })
      navigate(`/huespedes/${saved.id}`)
    } catch (failure) {
      const existing = duplicateGuestId(failure)
      setDuplicate(existing)
      setError(
        existing
          ? 'Este RUT ya está registrado. Abre la ficha existente para reutilizarla.'
          : failure instanceof Error
            ? failure.message
            : 'No se pudo guardar el huésped.',
      )
    }
  })
  return (
    <form
      className="mt-7 space-y-6 rounded-xl border border-border bg-white p-6"
      noValidate
      onSubmit={(event) => {
        void submit(event)
      }}
    >
      <div className="grid gap-5 sm:grid-cols-2">
        {(['first_name', 'last_name'] as const).map((field) => (
          <div key={field}>
            <label htmlFor={`guest-${field}`} className="text-sm font-medium">
              {labels[field]}
            </label>
            <input
              {...register(field)}
              id={`guest-${field}`}
              autoComplete={field === 'first_name' ? 'given-name' : 'family-name'}
              className={inputClass}
              aria-invalid={!!errors[field]}
              aria-describedby={`${field}-error`}
            />
            <p id={`${field}-error`} className="mt-2 text-sm text-red-800">
              {errors[field]?.message}
            </p>
          </div>
        ))}
        <div>
          <label htmlFor="guest-document_type" className="text-sm font-medium">
            Tipo de documento
          </label>
          <select {...register('document_type')} id="guest-document_type" className={inputClass}>
            {Object.entries(documentLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="guest-document_number" className="text-sm font-medium">
            {kind === 'rut' ? 'RUT' : 'Número de documento'}
          </label>
          <input
            {...register('document_number')}
            id="guest-document_number"
            autoComplete="off"
            maxLength={40}
            className={inputClass}
            aria-invalid={!!errors.document_number}
            aria-describedby="guest-document-help"
          />
          <div id="guest-document-help">
            {kind === 'rut' && (
              <p className="mt-2 text-xs text-muted-foreground">
                Incluye el dígito verificador; puedes usar puntos y guion.
              </p>
            )}
            {errors.document_number && (
              <p role="alert" className="mt-2 text-sm text-red-800">
                {errors.document_number.message}
              </p>
            )}
          </div>
        </div>
        {(['phone', 'email'] as const).map((field) => (
          <div key={field}>
            <label htmlFor={`guest-${field}`} className="text-sm font-medium">
              {labels[field]}
            </label>
            <input
              {...register(field)}
              id={`guest-${field}`}
              type={field === 'email' ? 'email' : 'tel'}
              autoComplete={field === 'email' ? 'email' : 'tel'}
              className={inputClass}
              aria-invalid={!!errors[field]}
              aria-describedby={`${field}-error`}
            />
            <p id={`${field}-error`} className="mt-2 text-sm text-red-800">
              {errors[field]?.message}
            </p>
          </div>
        ))}
        <div className="sm:col-span-2">
          <label htmlFor="guest-notes" className="text-sm font-medium">
            {labels.notes}
          </label>
          <textarea
            {...register('notes')}
            id="guest-notes"
            rows={4}
            maxLength={2000}
            className={inputClass}
            aria-describedby="notes-help"
          />
          <p id="notes-help" className="mt-2 text-xs text-muted-foreground">
            Solo propietarios y administradores pueden consultar estas notas. Registra únicamente
            información necesaria para la atención.
          </p>
          {errors.notes && (
            <p role="alert" className="mt-2 text-sm text-red-800">
              {errors.notes.message}
            </p>
          )}
        </div>
      </div>
      {error && (
        <div role="alert" className="text-sm text-red-800">
          <p>{error}</p>
          {duplicate && (
            <Link
              to={`/huespedes/${duplicate}`}
              className="mt-3 inline-block font-medium text-primary underline"
            >
              Abrir ficha existente
            </Link>
          )}
        </div>
      )}
      <div className="flex flex-wrap gap-3">
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Guardando…' : 'Guardar huésped'}
        </Button>
        <Button asChild variant="outline">
          <Link to={guest ? `/huespedes/${guest.id}` : '/huespedes'}>Cancelar</Link>
        </Button>
      </div>
    </form>
  )
}

export function GuestForm() {
  const { tenant, canEdit } = useTenantContext()
  const { id } = useParams()
  const query = useQuery({
    queryKey: ['guest', tenant.id, id],
    queryFn: () => guestApi.get(tenant.id, id!),
    enabled: !!id && canEdit,
    retry: false,
  })
  if (!canEdit) return <Navigate to="/huespedes" replace />
  return (
    <section className="mx-auto max-w-3xl">
      <Link to="/huespedes" className="text-sm text-primary underline">
        Volver a huéspedes
      </Link>
      <h1 className="mt-5 text-3xl font-bold">{id ? 'Editar huésped' : 'Nuevo huésped'}</h1>
      {id && query.isPending ? (
        <p role="status" className="mt-7">
          Cargando ficha…
        </p>
      ) : query.error ? (
        <p role="alert" className="mt-7">
          {query.error.message}
        </p>
      ) : (
        <Editor key={id ?? 'new'} guest={query.data} />
      )}
    </section>
  )
}

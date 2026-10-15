import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { propertyApi, type Property } from './api'
import { usePropertyContext } from './PropertyAccess'

const formSchema = z.object({
  name: z.string().trim().min(1, 'Ingresa el nombre.').max(150),
  code: z
    .string()
    .trim()
    .min(1, 'Ingresa el código.')
    .max(30)
    .regex(/^[a-zA-Z0-9_-]+$/, 'Usa letras, números, guion o guion bajo.'),
  description: z.string().max(5000),
  address: z.string().max(300),
  capacity: z
    .string()
    .regex(/^\d+$/, 'Ingresa una capacidad entera.')
    .refine(
      (value) => Number(value) >= 1 && Number(value) <= 32767,
      'La capacidad debe ser al menos una persona.',
    ),
  base_rate: z
    .string()
    .regex(
      /^\d{1,12}([.,]\d{1,2})?$/,
      'Ingresa un importe válido, sin puntos de miles y con hasta dos decimales.',
    ),
  check_in_time: z
    .string()
    .regex(/^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$/, 'Ingresa la hora de entrada.'),
  check_out_time: z
    .string()
    .regex(/^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$/, 'Ingresa la hora de salida.'),
})
type FormValues = z.infer<typeof formSchema>
const labels: Record<keyof FormValues, string> = {
  name: 'Nombre',
  code: 'Código',
  description: 'Descripción',
  address: 'Dirección',
  capacity: 'Capacidad máxima',
  base_rate: 'Tarifa base',
  check_in_time: 'Hora de entrada',
  check_out_time: 'Hora de salida',
}
const inputClass =
  'mt-2 w-full rounded-lg border border-border bg-white px-3 py-3 focus-visible:outline-2 focus-visible:outline-primary'

function Editor({ property }: { property?: Property }) {
  const { tenant } = usePropertyContext()
  const navigate = useNavigate()
  const client = useQueryClient()
  const [error, setError] = useState('')
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: property?.name ?? '',
      code: property?.code ?? '',
      description: property?.description ?? '',
      address: property?.address ?? '',
      capacity: property ? String(property.capacity) : '',
      base_rate: property?.base_rate ?? '',
      check_in_time: property?.check_in_time ?? '',
      check_out_time: property?.check_out_time ?? '',
    },
  })
  const submit = handleSubmit(async (values) => {
    setError('')
    const data = {
      ...values,
      capacity: Number(values.capacity),
      base_rate: values.base_rate.replace(',', '.'),
      code: values.code.toUpperCase(),
    }
    try {
      const saved = property
        ? await propertyApi.update(tenant.id, property.id, data)
        : await propertyApi.create(tenant.id, data)
      client.setQueryData(['property', tenant.id, saved.id], saved)
      await client.invalidateQueries({ queryKey: ['properties', tenant.id] })
      navigate(`/cabanas/${saved.id}`)
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'No se pudo guardar la cabaña.')
    }
  })
  return (
    <form
      onSubmit={(event) => {
        void submit(event)
      }}
      className="mt-7 space-y-6 rounded-xl border border-border bg-white p-6"
      noValidate
    >
      <div className="grid gap-5 sm:grid-cols-2">
        {(
          [
            'name',
            'code',
            'capacity',
            'base_rate',
            'check_in_time',
            'check_out_time',
            'address',
            'description',
          ] as const
        ).map((field) => (
          <div
            key={field}
            className={field === 'description' || field === 'address' ? 'sm:col-span-2' : ''}
          >
            <label htmlFor={`property-${field}`} className="text-sm font-medium">
              {labels[field]}
              {field === 'base_rate' ? ` (${tenant.currency})` : ''}
            </label>
            {field === 'description' ? (
              <textarea
                {...register(field)}
                id={`property-${field}`}
                rows={4}
                className={inputClass}
                aria-describedby={`${field}-help`}
                aria-invalid={!!errors[field]}
              />
            ) : (
              <input
                {...register(field)}
                id={`property-${field}`}
                type={field.includes('time') ? 'time' : 'text'}
                step={field.includes('time') ? 1 : undefined}
                inputMode={
                  field === 'capacity' ? 'numeric' : field === 'base_rate' ? 'decimal' : undefined
                }
                className={inputClass}
                aria-describedby={`${field}-help`}
                aria-invalid={!!errors[field]}
              />
            )}
            <div id={`${field}-help`}>
              {field === 'base_rate' && (
                <p className="mt-2 text-xs text-muted-foreground">
                  Ejemplo: 50000. No incluyas separadores de miles.
                </p>
              )}
              {errors[field] && (
                <p role="alert" className="mt-2 text-sm text-red-800">
                  {errors[field]?.message}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
      <p className="text-sm text-muted-foreground">
        Horarios locales de la empresa: {tenant.timezone}. La tarifa base no define todavía reglas
        de arriendo ni temporadas.
      </p>
      {error && (
        <p role="alert" className="text-sm text-red-800">
          {error}
        </p>
      )}
      <div className="flex flex-wrap gap-3">
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Guardando…' : 'Guardar cabaña'}
        </Button>
        <Button asChild variant="outline">
          <Link to={property ? `/cabanas/${property.id}` : '/cabanas'}>Cancelar</Link>
        </Button>
      </div>
    </form>
  )
}

export function PropertyForm() {
  const { tenant, canEdit } = usePropertyContext()
  const { id } = useParams()
  const query = useQuery({
    queryKey: ['property', tenant.id, id],
    queryFn: () => propertyApi.get(tenant.id, id!),
    enabled: !!id,
    retry: false,
  })
  if (!canEdit) return <Navigate to="/cabanas" replace />
  return (
    <section className="mx-auto max-w-3xl">
      <Link to="/cabanas" className="text-sm text-primary underline">
        Volver a cabañas
      </Link>
      <h1 className="mt-5 text-3xl font-bold">{id ? 'Editar cabaña' : 'Nueva cabaña'}</h1>
      {id && query.isPending ? (
        <p role="status" className="mt-7">
          Cargando cabaña…
        </p>
      ) : query.error ? (
        <p role="alert" className="mt-7">
          {query.error.message}
        </p>
      ) : (
        <Editor key={id ?? 'new'} property={query.data} />
      )}
    </section>
  )
}

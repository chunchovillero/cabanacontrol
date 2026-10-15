import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Navigate } from 'react-router-dom'
import { z } from 'zod'
import { ApiError, request, write } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { useAuth } from './AuthProvider'

const profileSchema = z.object({ first_name: z.string(), last_name: z.string(), email: z.string() })
const companySchema = z.object({
  id: z.string(),
  name: z.string(),
  legal_name: z.string(),
  contact_email: z.string(),
  contact_phone: z.string(),
  timezone: z.string(),
  currency: z.string(),
  updated_at: z.string(),
})

type Field = {
  name: string
  label: string
  value: string
  max: number
  type?: string
  optional?: boolean
}

function SettingsForm({
  title,
  fields,
  onSave,
  description,
}: {
  title: string
  fields: Field[]
  onSave: (data: Record<string, string>) => Promise<void>
  description: string
}) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  return (
    <section className="mt-6 rounded-2xl border border-border bg-white p-6">
      <h2 className="text-xl font-bold">{title}</h2>
      <p className="mt-3 break-words text-muted-foreground">{description}</p>
      <form
        className="mt-5 space-y-5"
        onSubmit={(event) => {
          event.preventDefault()
          setError('')
          setBusy(true)
          const data = Object.fromEntries(new FormData(event.currentTarget)) as Record<
            string,
            string
          >
          void onSave(data)
            .catch((failure: unknown) =>
              setError(failure instanceof Error ? failure.message : 'No se pudo guardar.'),
            )
            .finally(() => setBusy(false))
        }}
      >
        <fieldset disabled={busy} className="space-y-5">
          {fields.map((field) => (
            <div key={field.name}>
              <label htmlFor={`settings-${field.name}`} className="text-sm font-medium">
                {field.label}
              </label>
              <input
                id={`settings-${field.name}`}
                name={field.name}
                defaultValue={field.value}
                type={field.type || 'text'}
                maxLength={field.max}
                required={!field.optional}
                className="mt-2 w-full rounded-lg border border-border px-3 py-3 focus-visible:outline-primary"
              />
            </div>
          ))}
          <Button type="submit">{busy ? 'Guardando…' : `Guardar ${title.toLowerCase()}`}</Button>
        </fieldset>
        {error && (
          <p role="alert" className="text-red-800">
            {error}
          </p>
        )}
      </form>
    </section>
  )
}

export function SettingsPage() {
  const { session } = useAuth()
  if (!session) return <Navigate to="/ingresar" replace />
  return <SettingsContent key={`${session.id}:${session.active_tenant?.id || ''}`} />
}

function SettingsContent() {
  const { session } = useAuth()
  const client = useQueryClient()
  const [notice, setNotice] = useState<{ error: boolean; text: string } | null>(null)
  const tenant = session!.active_tenant
  const profileKey = ['profile', session!.id]
  const companyKey = ['company-settings', tenant?.id]
  const profile = useQuery({
    queryKey: profileKey,
    queryFn: async () => profileSchema.parse(await request('/api/v1/auth/profile/')),
    retry: false,
  })
  const company = useQuery({
    queryKey: companyKey,
    queryFn: async () =>
      companySchema.parse(
        await request('/api/v1/company-settings/', { headers: { 'X-Tenant-Context': tenant!.id } }),
      ),
    enabled: tenant?.role === 'owner',
    retry: false,
  })
  async function save(path: string, data: unknown, key: string[], headers = {}) {
    setNotice(null)
    try {
      await write(path, data, 'PATCH', headers)
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 409) {
        setNotice({
          error: true,
          text: 'Los datos cambiaron. Se recargaron los valores actuales; revísalos antes de guardar.',
        })
        await client.invalidateQueries({ queryKey: key })
        return
      }
      throw failure
    }
    await Promise.all([
      client.invalidateQueries({ queryKey: key }),
      client.invalidateQueries({ queryKey: ['session'] }),
      client.invalidateQueries({ queryKey: ['tenants'] }),
    ])
    setNotice({ error: false, text: 'Cambios guardados.' })
  }
  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-3xl font-bold">Perfil y empresa</h1>
      {notice && (
        <p className="mt-4" role={notice.error ? 'alert' : 'status'}>
          {notice.text}
        </p>
      )}
      {profile.isPending ? (
        <p role="status">Cargando perfil…</p>
      ) : profile.isError ? (
        <div role="alert">
          No se pudo cargar el perfil.{' '}
          <Button onClick={() => void profile.refetch()}>Reintentar perfil</Button>
        </div>
      ) : (
        <SettingsForm
          key={JSON.stringify([profile.data.first_name, profile.data.last_name])}
          title="Perfil"
          description={`Correo de acceso: ${profile.data.email}. Tu nombre se actualiza en todas tus empresas.`}
          fields={[
            { name: 'first_name', label: 'Nombre', value: profile.data.first_name, max: 150 },
            {
              name: 'last_name',
              label: 'Apellido (opcional)',
              value: profile.data.last_name,
              max: 150,
              optional: true,
            },
          ]}
          onSave={(data) =>
            save(
              '/api/v1/auth/profile/',
              {
                ...data,
                expected_first_name: profile.data.first_name,
                expected_last_name: profile.data.last_name,
              },
              profileKey,
            )
          }
        />
      )}
      {tenant?.role === 'owner' ? (
        company.isPending ? (
          <p role="status">Cargando empresa…</p>
        ) : company.isError ? (
          <div role="alert">
            No se pudo cargar la empresa.{' '}
            <Button onClick={() => void company.refetch()}>Reintentar empresa</Button>
          </div>
        ) : (
          <SettingsForm
            key={company.data.updated_at}
            title="Empresa"
            description={`${company.data.currency} · ${company.data.timezone}. Los datos de contacto son de la empresa y no cambian tu correo de acceso.`}
            fields={[
              { name: 'name', label: 'Nombre de la empresa', value: company.data.name, max: 150 },
              {
                name: 'legal_name',
                label: 'Razón social (opcional)',
                value: company.data.legal_name,
                max: 200,
                optional: true,
              },
              {
                name: 'contact_email',
                label: 'Correo de contacto (opcional)',
                value: company.data.contact_email,
                max: 254,
                type: 'email',
                optional: true,
              },
              {
                name: 'contact_phone',
                label: 'Teléfono de contacto (opcional)',
                value: company.data.contact_phone,
                max: 30,
                type: 'tel',
                optional: true,
              },
            ]}
            onSave={(data) =>
              save(
                '/api/v1/company-settings/',
                { ...data, expected_updated_at: company.data.updated_at },
                ['company-settings', tenant.id],
                { 'X-Tenant-Context': tenant.id },
              )
            }
          />
        )
      ) : (
        <p className="mt-6 text-muted-foreground">
          Selecciona una empresa como propietario para editar sus datos de contacto.
        </p>
      )}
    </div>
  )
}

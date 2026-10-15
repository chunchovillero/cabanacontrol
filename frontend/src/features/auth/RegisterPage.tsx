import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, Navigate } from 'react-router-dom'
import { write } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { AuthCard } from './AuthPages'
import { useAuth } from './AuthProvider'
import { GoogleSignIn, registrationOptions } from './GoogleSignIn'

export function RegistrationLink() {
  const options = useQuery({
    queryKey: ['registration-options'],
    queryFn: registrationOptions,
  })
  return options.data && (options.data.enabled || options.data.google_enabled) ? (
    <Link className="mt-5 block text-sm text-primary underline" to="/registrarse">
      Crear cuenta y empresa
    </Link>
  ) : null
}

export function RegisterPage() {
  const { session } = useAuth()
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')
  const options = useQuery({
    queryKey: ['registration-options'],
    queryFn: registrationOptions,
  })
  if (session) return <Navigate to="/" replace />
  return (
    <AuthCard title="Crea tu cuenta y empresa">
      {done ? (
        <p role="status" className="mt-5">
          Cuenta y empresa creadas. Ya puedes iniciar sesión y seleccionar tu empresa.
        </p>
      ) : options.isPending ? (
        <p role="status">Consultando disponibilidad…</p>
      ) : options.isError ? (
        <p role="alert">
          No pudimos consultar el registro.{' '}
          <Button onClick={() => void options.refetch()}>Reintentar</Button>
        </p>
      ) : !options.data.enabled && !options.data.google_enabled ? (
        <p role="status" className="mt-5">
          El alta web no está disponible en este entorno.
        </p>
      ) : options.data.enabled ? (
        <>
          <p className="mt-3 text-muted-foreground">
            Alta local de prueba. Serás propietario de la empresa, con moneda CLP y zona horaria de
            Chile. Este entorno no verifica el correo.
          </p>
          <form
            className="mt-6 space-y-5"
            onSubmit={(event) => {
              event.preventDefault()
              const form = event.currentTarget
              const data = new FormData(form)
              setError('')
              if (data.get('password') !== data.get('confirmation')) {
                setError('Las contraseñas no coinciden.')
                return
              }
              setBusy(true)
              void write('/api/v1/auth/register/', {
                email: data.get('email'),
                first_name: data.get('first_name'),
                last_name: data.get('last_name'),
                company_name: data.get('company_name'),
                password: data.get('password'),
              })
                .then(() => {
                  form.reset()
                  setDone(true)
                })
                .catch((failure: unknown) => {
                  setError(
                    failure instanceof Error ? failure.message : 'No se pudo crear la cuenta.',
                  )
                  form
                    .querySelectorAll<HTMLInputElement>('input[type="password"]')
                    .forEach((input) => {
                      input.value = ''
                    })
                })
                .finally(() => setBusy(false))
            }}
          >
            <fieldset disabled={busy} className="space-y-5">
              {(
                [
                  ['first_name', 'Nombre', 'text', 'given-name', 150],
                  ['last_name', 'Apellido (opcional)', 'text', 'family-name', 150],
                  ['email', 'Correo electrónico', 'email', 'email', 254],
                  ['company_name', 'Nombre de la empresa', 'text', 'organization', 150],
                  ['password', 'Contraseña', 'password', 'new-password', 256],
                  ['confirmation', 'Repite la contraseña', 'password', 'new-password', 256],
                ] as const
              ).map(([name, label, type, autoComplete, maxLength]) => (
                <div key={name}>
                  <label htmlFor={`register-${name}`} className="text-sm font-medium">
                    {label}
                  </label>
                  <input
                    id={`register-${name}`}
                    name={name}
                    type={type}
                    autoComplete={autoComplete}
                    required={name !== 'last_name'}
                    minLength={type === 'password' ? 12 : 1}
                    maxLength={maxLength}
                    className="mt-2 w-full rounded-lg border border-border px-3 py-3 focus-visible:outline-primary"
                  />
                </div>
              ))}
              <p className="text-sm text-muted-foreground">
                Usa al menos 12 caracteres y evita datos personales en tu contraseña.
              </p>
              {error && (
                <p role="alert" className="text-red-800">
                  {error}
                </p>
              )}
              <Button className="w-full" type="submit">
                {busy ? 'Creando…' : 'Crear cuenta y empresa'}
              </Button>
            </fieldset>
          </form>
        </>
      ) : (
        <>
          <p className="mt-3 text-muted-foreground">Usa tu cuenta de Google para registrarte.</p>
          <GoogleSignIn options={options.data} />
        </>
      )}
      <Link to="/ingresar" className="mt-5 inline-block text-sm text-primary underline">
        {done ? 'Iniciar sesión' : 'Volver al inicio de sesión'}
      </Link>
    </AuthCard>
  )
}

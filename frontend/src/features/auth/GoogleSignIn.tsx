import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { z } from 'zod'
import { api, type Session } from '@/lib/api'
import { Button } from '@/components/ui/button'

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize(config: {
            client_id: string
            callback: (value: { credential: string }) => void
          }): void
          renderButton(element: HTMLElement, config: Record<string, string>): void
        }
      }
    }
  }
}

const optionsSchema = z.object({
  enabled: z.boolean(),
  google_enabled: z.boolean(),
  google_client_id: z.string(),
})
export type RegistrationOptions = z.infer<typeof optionsSchema>

export async function registrationOptions() {
  return optionsSchema.parse(await api.registrationOptions())
}

export function GoogleSignIn({ options }: { options: RegistrationOptions }) {
  const button = useRef<HTMLDivElement>(null)
  const credential = useRef('')
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [profile, setProfile] = useState<{ email: string; name: string } | null>(null)
  const [companyName, setCompanyName] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const complete = useCallback(
    async (session: Session) => {
      await queryClient.cancelQueries()
      queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== 'session' })
      queryClient.setQueryData(['session'], session)
      navigate('/', { replace: true })
    },
    [navigate, queryClient],
  )

  useEffect(() => {
    if (!options.google_enabled || !button.current) return
    let active = true
    const render = () => {
      if (!active || !button.current || !window.google) return
      window.google.accounts.id.initialize({
        client_id: options.google_client_id,
        callback: ({ credential: value }) => {
          credential.current = value
          setBusy(true)
          setError('')
          void api
            .googleAuth(value)
            .then((result) => {
              if ('requires_company' in result) setProfile(result.profile)
              else void complete(result)
            })
            .catch((failure: unknown) =>
              setError(
                failure instanceof Error ? failure.message : 'No se pudo acceder con Google.',
              ),
            )
            .finally(() => setBusy(false))
        },
      })
      button.current.replaceChildren()
      window.google.accounts.id.renderButton(button.current, {
        type: 'standard',
        theme: 'outline',
        size: 'large',
        text: 'continue_with',
        shape: 'rectangular',
        width: '350',
        locale: 'es',
      })
    }
    if (window.google) render()
    else {
      const existing = document.querySelector<HTMLScriptElement>('script[data-google-identity]')
      const script = existing ?? document.createElement('script')
      script.addEventListener('load', render, { once: true })
      if (!existing) {
        script.src = 'https://accounts.google.com/gsi/client'
        script.async = true
        script.dataset.googleIdentity = 'true'
        document.head.appendChild(script)
      }
    }
    return () => {
      active = false
    }
  }, [complete, options.google_client_id, options.google_enabled])

  if (!options.google_enabled) return null
  return (
    <section className="mt-5" aria-label="Acceso con Google">
      {profile ? (
        <form
          className="space-y-4 rounded-lg border border-border p-4"
          onSubmit={(event) => {
            event.preventDefault()
            setBusy(true)
            setError('')
            void api
              .googleAuth(credential.current, companyName)
              .then((result) => {
                if ('requires_company' in result)
                  throw new Error('Ingresa el nombre de la empresa.')
                return complete(result)
              })
              .catch((failure: unknown) =>
                setError(
                  failure instanceof Error ? failure.message : 'No se pudo crear la cuenta.',
                ),
              )
              .finally(() => setBusy(false))
          }}
        >
          <p className="text-sm text-muted-foreground">
            Crearás la cuenta <strong>{profile.email}</strong> como propietaria de una empresa.
          </p>
          <label htmlFor="google-company" className="block text-sm font-medium">
            Nombre de la empresa
          </label>
          <input
            id="google-company"
            value={companyName}
            onChange={(event) => setCompanyName(event.target.value)}
            required
            maxLength={150}
            autoComplete="organization"
            className="w-full rounded-lg border border-border px-3 py-3 focus-visible:outline-primary"
          />
          <Button type="submit" className="w-full" disabled={busy}>
            {busy ? 'Creando…' : 'Crear cuenta y empresa'}
          </Button>
        </form>
      ) : (
        <>
          <div ref={button} className={busy ? 'pointer-events-none opacity-60' : ''} />
          <p className="mt-3 text-xs text-muted-foreground">
            Si aún no tienes cuenta, te pediremos el nombre de tu empresa.
          </p>
        </>
      )}
      {error && (
        <p role="alert" className="mt-3 text-sm text-red-800">
          {error}
        </p>
      )}
    </section>
  )
}

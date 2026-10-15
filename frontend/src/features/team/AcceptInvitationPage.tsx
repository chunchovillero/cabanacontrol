import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/features/auth/AuthProvider'
import { teamApi, type Preview } from './api'

export function AcceptInvitationPage() {
  const { session } = useAuth()
  const queries = useQueryClient()
  const [token] = useState(
    () => new URLSearchParams(window.location.hash.slice(1)).get('token') ?? '',
  )
  const [preview, setPreview] = useState<Preview | null>(null)
  const [name, setName] = useState('')
  const [surname, setSurname] = useState('')
  const [password, setPassword] = useState('')
  const [repeat, setRepeat] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [accepted, setAccepted] = useState(false)
  useEffect(() => {
    window.history.replaceState(window.history.state, '', window.location.pathname)
    let current = true
    if (!token) return
    void teamApi
      .preview(token)
      .then((data) => {
        if (current) setPreview(data)
      })
      .catch((failure: unknown) => {
        if (current)
          setError(failure instanceof Error ? failure.message : 'Invitación no disponible.')
      })
    return () => {
      current = false
    }
  }, [token])
  async function accept(event: React.FormEvent) {
    event.preventDefault()
    setError('')
    if (!session && password !== repeat) {
      setError('Las contraseñas no coinciden.')
      return
    }
    setBusy(true)
    try {
      await teamApi.accept(
        session
          ? { token, mode: 'existing' }
          : { token, mode: 'new', first_name: name, last_name: surname, password },
      )
      setAccepted(true)
      void queries.invalidateQueries({ queryKey: ['session'] })
      void queries.invalidateQueries({ queryKey: ['tenants'] })
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'No se pudo aceptar.')
    } finally {
      setBusy(false)
      setPassword('')
      setRepeat('')
    }
  }
  if (accepted)
    return (
      <section>
        <h1 className="text-3xl font-bold">Invitación aceptada</h1>
        <p className="mt-4">
          Ya tienes acceso a {preview?.company_name}. Selecciona la empresa para comenzar.
        </p>
        <Link className="mt-5 inline-block text-primary underline" to={session ? '/' : '/ingresar'}>
          {session ? 'Ir a Empresas' : 'Iniciar sesión'}
        </Link>
      </section>
    )
  return (
    <section className="mx-auto max-w-lg">
      <h1 className="text-3xl font-bold">Únete a tu equipo</h1>
      {!token && (
        <p role="alert" className="mt-4">
          Abre el enlace privado que te compartió el propietario.
        </p>
      )}
      {token && !preview && !error && (
        <p role="status" className="mt-4">
          Comprobando invitación…
        </p>
      )}
      {error && (
        <p role="alert" className="mt-4 text-red-800">
          {error}
        </p>
      )}
      {preview && (
        <form
          onSubmit={(event) => {
            void accept(event)
          }}
          className="mt-6 space-y-4 rounded-xl border border-border bg-white p-5"
        >
          <p className="font-semibold">{preview.company_name}</p>
          <p className="text-sm">
            Invitación para {preview.email_hint} ·{' '}
            {preview.role === 'manager' ? 'Administrador' : 'Colaborador'}
          </p>
          <p className="text-sm text-muted-foreground">
            Vence el {new Date(preview.expires_at).toLocaleString('es-CL')}.
          </p>
          <fieldset disabled={busy} className="space-y-4">
            {session ? (
              <p className="text-sm">
                Aceptarás con {session.email}. Si no es la cuenta invitada, cierra tu sesión antes
                de continuar.
              </p>
            ) : (
              <>
                <p className="text-sm">
                  Si ya tienes cuenta,{' '}
                  <Link className="text-primary underline" to="/ingresar">
                    inicia sesión
                  </Link>{' '}
                  y vuelve a abrir el enlace original. Si eres nuevo, crea tu cuenta aquí.
                </p>
                <label className="block text-sm">
                  Nombre
                  <input
                    className="mt-1 w-full rounded-lg border p-2"
                    required
                    autoComplete="given-name"
                    maxLength={150}
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                  />
                </label>
                <label className="block text-sm">
                  Apellido
                  <input
                    className="mt-1 w-full rounded-lg border p-2"
                    autoComplete="family-name"
                    maxLength={150}
                    value={surname}
                    onChange={(event) => setSurname(event.target.value)}
                  />
                </label>
                <label className="block text-sm">
                  Contraseña nueva
                  <input
                    className="mt-1 w-full rounded-lg border p-2"
                    type="password"
                    autoComplete="new-password"
                    minLength={12}
                    maxLength={256}
                    required
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                  />
                </label>
                <label className="block text-sm">
                  Repite tu contraseña
                  <input
                    className="mt-1 w-full rounded-lg border p-2"
                    type="password"
                    autoComplete="new-password"
                    minLength={12}
                    maxLength={256}
                    required
                    value={repeat}
                    onChange={(event) => setRepeat(event.target.value)}
                  />
                </label>
                <p className="text-sm text-muted-foreground">
                  Usa al menos 12 caracteres y evita datos personales o contraseñas comunes.
                </p>
              </>
            )}
            <Button type="submit">
              {busy ? 'Aceptando…' : session ? 'Aceptar invitación' : 'Crear cuenta y aceptar'}
            </Button>
          </fieldset>
        </form>
      )}
    </section>
  )
}

import { useEffect, useState, type ReactNode } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import { useAuth } from './AuthProvider'
import { RegistrationLink } from './RegisterPage'
import { GoogleSignIn, registrationOptions } from './GoogleSignIn'
import { finishSignIn } from './finishSignIn'

const loginSchema = z.object({
  email: z.email('Ingresa un correo válido.'),
  password: z.string().min(1, 'Ingresa tu contraseña.').max(256),
})
const emailSchema = loginSchema.pick({ email: true })
const passwordSchema = z
  .object({
    password: z.string().min(12, 'Usa al menos 12 caracteres.').max(256),
    confirmation: z.string(),
  })
  .refine((value) => value.password === value.confirmation, {
    message: 'Las contraseñas no coinciden.',
    path: ['confirmation'],
  })

const fieldClass =
  'mt-2 w-full rounded-lg border border-border bg-white px-3 py-3 text-foreground focus-visible:outline-2 focus-visible:outline-primary'

export function AuthCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mx-auto w-full max-w-md rounded-2xl border border-border bg-white p-6 shadow-sm sm:p-8">
      <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
      {children}
    </section>
  )
}

function FormError({ message }: { message?: string }) {
  return message ? (
    <p role="alert" className="mt-2 text-sm text-red-800">
      {message}
    </p>
  ) : null
}

export function LoginPage() {
  const { session } = useAuth()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const options = useQuery({ queryKey: ['registration-options'], queryFn: registrationOptions })
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof loginSchema>>({
    resolver: zodResolver(loginSchema),
  })
  if (session) return <Navigate to={session.active_tenant ? '/panel' : '/'} replace />
  const submit = handleSubmit(async (values) => {
    setError('')
    try {
      const result = await api.login(values)
      const completed = await finishSignIn(result)
      await queryClient.cancelQueries()
      queryClient.removeQueries({
        predicate: (query) => query.queryKey[0] !== 'session',
      })
      queryClient.setQueryData(['session'], completed.session)
      navigate(completed.destination, { replace: true })
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'No se pudo iniciar sesión.')
    }
  })
  return (
    <AuthCard title="Bienvenido a CabañaControl">
      <p className="mt-3 text-muted-foreground">Ingresa para acceder a tus empresas.</p>
      <RegistrationLink />
      {options.data?.google_enabled && <GoogleSignIn options={options.data} />}
      {options.data?.google_enabled && (
        <p className="my-5 text-center text-sm text-muted-foreground">o usa tu contraseña</p>
      )}
      <form
        onSubmit={(event) => {
          void submit(event)
        }}
        className="mt-6 space-y-5"
        noValidate
      >
        <div>
          <label htmlFor="login-email" className="text-sm font-medium">
            Correo electrónico
          </label>
          <input
            {...register('email')}
            id="login-email"
            type="email"
            autoComplete="username"
            className={fieldClass}
            aria-invalid={!!errors.email}
            aria-describedby={errors.email ? 'login-email-error' : undefined}
          />
          <div id="login-email-error">
            <FormError message={errors.email?.message} />
          </div>
        </div>
        <div>
          <label htmlFor="login-password" className="text-sm font-medium">
            Contraseña
          </label>
          <input
            {...register('password')}
            id="login-password"
            type="password"
            autoComplete="current-password"
            className={fieldClass}
            aria-invalid={!!errors.password}
            aria-describedby={errors.password ? 'login-password-error' : undefined}
          />
          <div id="login-password-error">
            <FormError message={errors.password?.message} />
          </div>
        </div>
        <FormError message={error} />
        <Button type="submit" className="w-full" disabled={isSubmitting}>
          {isSubmitting ? 'Ingresando…' : 'Iniciar sesión'}
        </Button>
      </form>
      <Link
        to="/recuperar"
        className="mt-5 inline-block text-sm font-medium text-primary underline underline-offset-4"
      >
        Olvidé mi contraseña
      </Link>
    </AuthCard>
  )
}

export function RecoverPage() {
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof emailSchema>>({
    resolver: zodResolver(emailSchema),
  })
  const submit = handleSubmit(async ({ email }) => {
    setError('')
    try {
      await api.resetPassword(email)
      setSent(true)
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'No se pudo completar la solicitud.')
    }
  })
  return (
    <AuthCard title="Recupera tu acceso">
      {sent ? (
        <p role="status" className="mt-5">
          Si el correo corresponde a una cuenta activa, recibirás instrucciones para recuperar el
          acceso.
        </p>
      ) : (
        <>
          <p className="mt-3 text-muted-foreground">
            Te enviaremos un enlace para definir una nueva contraseña.
          </p>
          <form
            onSubmit={(event) => {
              void submit(event)
            }}
            className="mt-6 space-y-5"
            noValidate
          >
            <div>
              <label htmlFor="recover-email" className="text-sm font-medium">
                Correo electrónico
              </label>
              <input
                {...register('email')}
                id="recover-email"
                type="email"
                autoComplete="email"
                className={fieldClass}
                aria-invalid={!!errors.email}
                aria-describedby="recover-email-error"
              />
              <div id="recover-email-error">
                <FormError message={errors.email?.message} />
              </div>
            </div>
            <FormError message={error} />
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? 'Enviando…' : 'Enviar instrucciones'}
            </Button>
          </form>
        </>
      )}
      <Link
        to="/ingresar"
        className="mt-5 inline-block text-sm text-primary underline underline-offset-4"
      >
        Volver al inicio de sesión
      </Link>
    </AuthCard>
  )
}

export function ResetPage() {
  const [credentials] = useState(() => {
    const fragment = new URLSearchParams(window.location.hash.slice(1))
    return {
      uid: fragment.get('uid') ?? '',
      token: fragment.get('token') ?? '',
    }
  })
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')
  const queryClient = useQueryClient()
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof passwordSchema>>({
    resolver: zodResolver(passwordSchema),
  })
  useEffect(() => {
    window.history.replaceState(null, '', window.location.pathname)
  }, [])
  const submit = handleSubmit(async ({ password }) => {
    setError('')
    try {
      await api.confirmPassword(credentials.uid, credentials.token, password)
      await queryClient.cancelQueries()
      queryClient.removeQueries({
        predicate: (query) => query.queryKey[0] !== 'session',
      })
      queryClient.setQueryData(['session'], null)
      setDone(true)
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'No se pudo restablecer la contraseña.')
    }
  })
  return (
    <AuthCard title="Define tu nueva contraseña">
      {!credentials.uid || !credentials.token ? (
        <p role="alert" className="mt-5">
          El enlace está incompleto. Solicita uno nuevo.
        </p>
      ) : done ? (
        <p role="status" className="mt-5">
          Contraseña actualizada. Ya puedes iniciar sesión.
        </p>
      ) : (
        <form
          onSubmit={(event) => {
            void submit(event)
          }}
          className="mt-6 space-y-5"
          noValidate
        >
          <div>
            <label htmlFor="reset-password" className="text-sm font-medium">
              Nueva contraseña
            </label>
            <input
              {...register('password')}
              id="reset-password"
              type="password"
              autoComplete="new-password"
              className={fieldClass}
              aria-invalid={!!errors.password}
              aria-describedby="reset-password-help"
            />
            <div id="reset-password-help">
              <p className="mt-2 text-sm text-muted-foreground">
                Usa al menos 12 caracteres y evita datos personales.
              </p>
              <FormError message={errors.password?.message} />
            </div>
          </div>
          <div>
            <label htmlFor="reset-confirmation" className="text-sm font-medium">
              Repite la contraseña
            </label>
            <input
              {...register('confirmation')}
              id="reset-confirmation"
              type="password"
              autoComplete="new-password"
              className={fieldClass}
              aria-invalid={!!errors.confirmation}
              aria-describedby="reset-confirmation-error"
            />
            <div id="reset-confirmation-error">
              <FormError message={errors.confirmation?.message} />
            </div>
          </div>
          <FormError message={error} />
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? 'Guardando…' : 'Guardar contraseña'}
          </Button>
        </form>
      )}
      <Link
        to={done ? '/ingresar' : '/recuperar'}
        className="mt-5 inline-block text-sm text-primary underline underline-offset-4"
      >
        {done ? 'Iniciar sesión' : 'Solicitar un nuevo enlace'}
      </Link>
    </AuthCard>
  )
}

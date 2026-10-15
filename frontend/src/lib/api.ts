import { z } from 'zod'

export const tenantSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  timezone: z.string(),
  currency: z.string(),
  role: z.enum(['owner', 'manager', 'staff']),
})
export const sessionSchema = z.object({
  id: z.string().uuid(),
  email: z.string(),
  name: z.string(),
  is_platform_admin: z.boolean(),
  active_tenant: tenantSchema.nullable(),
})
export type Tenant = z.infer<typeof tenantSchema>
export type Session = z.infer<typeof sessionSchema>

export function publicUrl(path: string): string {
  if (!path.startsWith('/') || import.meta.env.BASE_URL === '/') return path
  return `${import.meta.env.BASE_URL.replace(/\/$/, '')}${path}`
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public payload: unknown = null,
  ) {
    super(message)
  }
}

function errorMessage(body: unknown): string {
  const parsed = z.object({ error: z.object({ details: z.unknown() }) }).safeParse(body)
  if (!parsed.success) return 'No se pudo completar la solicitud. Intenta nuevamente.'
  const details = parsed.data.error.details
  if (typeof details === 'string') return details
  if (Array.isArray(details)) return details.filter((value) => typeof value === 'string').join(' ')
  if (typeof details === 'object' && details !== null) {
    return (
      Object.values(details)
        .flat()
        .filter((value) => typeof value === 'string')
        .join(' ') || 'Revisa los datos ingresados.'
    )
  }
  return 'No se pudo completar la solicitud.'
}

export async function request(
  path: string,
  options: RequestInit = {},
  timeout = 15000,
): Promise<unknown> {
  let response: Response
  try {
    response = await fetch(publicUrl(path), {
      ...options,
      credentials: 'same-origin',
      signal: options.signal
        ? AbortSignal.any([options.signal, AbortSignal.timeout(timeout)])
        : AbortSignal.timeout(timeout),
    })
  } catch {
    throw new ApiError(
      0,
      'No pudimos conectar con el servidor. Comprueba tu conexión e intenta nuevamente.',
    )
  }
  if (response.status === 204) return null
  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) throw new ApiError(response.status, errorMessage(body), body)
  return body
}

export async function write(
  path: string,
  data: unknown = {},
  method: 'POST' | 'PATCH' = 'POST',
  extraHeaders: Record<string, string> = {},
  timeout = 15000,
) {
  // Obtener un token fresco también después de que Django lo rote al iniciar sesión.
  const csrf = z.object({ csrf_token: z.string() }).parse(await request('/api/v1/auth/csrf/'))
  return request(
    path,
    {
      method,
      headers: {
        ...(data instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
        'X-CSRFToken': csrf.csrf_token,
        ...extraHeaders,
      },
      body: data instanceof FormData ? data : JSON.stringify(data),
    },
    timeout,
  )
}

const post = write

export const api = {
  async me(): Promise<Session | null> {
    try {
      return sessionSchema.parse(await request('/api/v1/auth/me/'))
    } catch (error) {
      if (error instanceof ApiError && error.status === 403) return null
      throw error
    }
  },
  async login(data: { email: string; password: string }) {
    return sessionSchema.parse(await post('/api/v1/auth/login/', data))
  },
  async logout() {
    await post('/api/v1/auth/logout/')
  },
  async tenants(): Promise<Tenant[]> {
    const tenants: Tenant[] = []
    let page = 1
    while (true) {
      const result = z
        .object({ results: z.array(tenantSchema), next: z.string().nullable() })
        .parse(await request(`/api/v1/tenants/?page=${page}`))
      tenants.push(...result.results)
      if (!result.next) return tenants
      // Paginar con rutas locales; no seguir URLs externas de una respuesta.
      page += 1
      if (page > 100)
        throw new ApiError(0, 'Hay demasiadas empresas para cargar. Contacta al administrador.')
    }
  },
  async selectTenant(id: string) {
    return tenantSchema.parse(await post(`/api/v1/tenants/${encodeURIComponent(id)}/select/`))
  },
  async resetPassword(email: string) {
    await post('/api/v1/auth/password-reset/', { email })
  },
  async confirmPassword(uid: string, token: string, password: string) {
    await post('/api/v1/auth/password-reset/confirm/', {
      uid,
      token,
      password,
    })
  },
}

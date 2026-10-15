import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'

export function HealthPage() {
  const [status, setStatus] = useState<'loading' | 'ok' | 'error'>('loading')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    let active = true
    const timeout = setTimeout(() => controller.abort(), 5000)
    fetch('/health/', { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error('No disponible')
        const data: unknown = await response.json()
        if (
          typeof data !== 'object' ||
          data === null ||
          !('status' in data) ||
          data.status !== 'ok' ||
          !('database' in data) ||
          data.database !== 'ok'
        )
          throw new Error('Respuesta inválida')
        if (active) setStatus('ok')
      })
      .catch(() => {
        if (active) setStatus('error')
      })
      .finally(() => clearTimeout(timeout))
    return () => {
      active = false
      controller.abort()
      clearTimeout(timeout)
    }
  }, [attempt])
  return (
    <section className="mx-auto max-w-xl rounded-2xl border border-border bg-white p-8">
      <h1 className="text-2xl font-bold">Conexión de servicios</h1>
      <p role="status" className="mt-4 text-muted-foreground">
        {status === 'loading' && 'Verificando conexión con la API…'}
        {status === 'ok' && 'Backend y PostgreSQL conectados correctamente.'}
        {status === 'error' &&
          'No se pudo verificar la conexión. Comprueba que los servicios estén iniciados.'}
      </p>
      <Button
        className="mt-5"
        variant="outline"
        disabled={status === 'loading'}
        onClick={() => {
          setStatus('loading')
          setAttempt((value) => value + 1)
        }}
      >
        Verificar nuevamente
      </Button>
    </section>
  )
}

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { whatsappApi } from './api'

export function TemplatesSetup({ tenant }: { tenant: string }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  async function save(form: HTMLFormElement) {
    const data = new FormData(form)
    setBusy(true)
    setError('')
    setSaved(false)
    try {
      await whatsappApi.saveTemplate(tenant, {
        name: String(data.get('name')),
        language: String(data.get('language')),
        body: String(data.get('body')),
        approved: data.get('approved') === 'on',
        enabled: data.get('enabled') === 'on',
        reviewed: data.get('reviewed') === 'on',
      })
      setSaved(true)
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'No se pudo guardar.')
    } finally {
      setBusy(false)
    }
  }
  return (
    <details className="rounded-xl border p-5">
      <summary>Catálogo de plantillas verificadas</summary>
      <p className="my-3 text-sm">
        Registra el nombre, idioma y texto exactos comprobados en Meta. Aquí se admiten plantillas
        estáticas para consultas de reservas. Esta pantalla no solicita aprobación a Meta.
      </p>
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault()
          void save(event.currentTarget)
        }}
      >
        <label className="block">
          Nombre de plantilla
          <input
            className="mt-2 w-full rounded border p-3"
            name="name"
            maxLength={100}
            pattern="[a-z0-9_]+"
            required
          />
        </label>
        <label className="block">
          Idioma de plantilla
          <input
            className="mt-2 w-full rounded border p-3"
            name="language"
            maxLength={12}
            defaultValue="es_CL"
            required
          />
        </label>
        <label className="block">
          Texto exacto de plantilla
          <textarea
            className="mt-2 w-full rounded border p-3"
            name="body"
            maxLength={4000}
            rows={4}
            required
          />
        </label>
        <label className="flex gap-3">
          <input name="approved" type="checkbox" />
          Aprobada en Meta
        </label>
        <label className="flex gap-3">
          <input name="enabled" type="checkbox" />
          Habilitada en este catálogo
        </label>
        <label className="flex gap-3">
          <input name="reviewed" type="checkbox" required />
          Verifiqué el texto y el estado para esta cuenta e idioma.
        </label>
        <Button disabled={busy}>{busy ? 'Guardando…' : 'Guardar plantilla verificada'}</Button>
      </form>
      {error && <p role="alert">{error}</p>}
      {saved && <p role="status">Plantilla registrada en el catálogo propio.</p>}
    </details>
  )
}

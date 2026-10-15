import { useState, type FormEvent } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { publicUrl } from '@/lib/api'
import { propertyApi, type Property, type Photo } from './api'
import { usePropertyContext } from './PropertyAccess'

export function PhotoManager({ property }: { property: Property }) {
  const { tenant, canEdit } = usePropertyContext()
  const client = useQueryClient()
  const [file, setFile] = useState<File | null>(null)
  const [alt, setAlt] = useState('')
  const [order, setOrder] = useState('0')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState<Photo | null>(null)
  const [hide, setHide] = useState<Photo | null>(null)
  const refresh = async () => {
    await client.invalidateQueries({ queryKey: ['property', tenant.id, property.id] })
    await client.invalidateQueries({ queryKey: ['properties', tenant.id] })
  }
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    const form = event.currentTarget
    event.preventDefault()
    setError('')
    if (!alt.trim()) {
      setError('Describe la fotografía para quienes usan lectores de pantalla.')
      return
    }
    if (!/^\d+$/.test(order) || Number(order) > 32767) {
      setError('Ingresa un orden entero entre 0 y 32767.')
      return
    }
    if (
      !editing &&
      (!file ||
        !['image/jpeg', 'image/png', 'image/webp'].includes(file.type) ||
        file.size > 5 * 1024 * 1024)
    ) {
      setError('Selecciona una imagen JPG, PNG o WebP de hasta 5 MB.')
      return
    }
    setPending(true)
    try {
      if (editing)
        await propertyApi.updatePhoto(tenant.id, property.id, editing.id, {
          alt: alt.trim(),
          order: Number(order),
        })
      else await propertyApi.upload(tenant.id, property.id, file!, alt.trim(), Number(order))
      await refresh()
      setEditing(null)
      setAlt('')
      setOrder('0')
      setFile(null)
      form.reset()
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'No se pudo guardar la fotografía.')
    } finally {
      setPending(false)
    }
  }
  const hidePhoto = async () => {
    if (!hide) return
    setPending(true)
    setError('')
    try {
      await propertyApi.updatePhoto(tenant.id, property.id, hide.id, { active: false })
      await refresh()
      setHide(null)
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'No se pudo ocultar la fotografía.')
    } finally {
      setPending(false)
    }
  }
  return (
    <section className="mt-8" aria-labelledby="photos-title">
      <h2 id="photos-title" className="text-xl font-semibold">
        Fotografías
      </h2>
      <p className="mt-2 text-sm text-muted-foreground">
        JPG, PNG o WebP · Máximo 5 MB y 4096 píxeles por lado · Hasta 10 fotos activas.
      </p>
      <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {property.photos.map((photo) => (
          <figure
            key={photo.id}
            className="overflow-hidden rounded-xl border border-border bg-white"
          >
            <img src={publicUrl(photo.url)} alt={photo.alt} className="h-48 w-full object-cover" />
            <figcaption className="p-4 text-sm">
              {photo.alt} · Orden {photo.order}
              {canEdit && (
                <div className="mt-3 flex gap-2">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setEditing(photo)
                      setAlt(photo.alt)
                      setOrder(String(photo.order))
                    }}
                  >
                    Editar foto
                  </Button>
                  <Button variant="outline" onClick={() => setHide(photo)}>
                    Ocultar foto
                  </Button>
                </div>
              )}
            </figcaption>
          </figure>
        ))}
      </div>
      {property.photos.length === 0 && (
        <p className="mt-5 text-muted-foreground">Esta cabaña todavía no tiene fotografías.</p>
      )}
      {hide && (
        <section
          role="alertdialog"
          aria-modal="false"
          aria-label="Confirmar ocultar fotografía"
          className="mt-5 rounded-xl border border-border bg-white p-5"
        >
          <p>¿Ocultar esta fotografía? El archivo se conservará.</p>
          <div className="mt-3 flex gap-2">
            <Button
              disabled={pending}
              onClick={() => {
                void hidePhoto()
              }}
            >
              Confirmar ocultar
            </Button>
            <Button variant="outline" disabled={pending} onClick={() => setHide(null)}>
              Cancelar
            </Button>
          </div>
        </section>
      )}
      {canEdit && (
        <form
          className="mt-6 space-y-4 rounded-xl border border-border bg-white p-6"
          onSubmit={(event) => {
            void submit(event)
          }}
        >
          <h3 className="font-semibold">{editing ? 'Editar fotografía' : 'Agregar fotografía'}</h3>
          {!editing && (
            <div>
              <label htmlFor="photo-file" className="text-sm font-medium">
                Archivo
              </label>
              <input
                id="photo-file"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="mt-2 block w-full text-sm"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
            </div>
          )}
          <div>
            <label htmlFor="photo-alt" className="text-sm font-medium">
              Descripción de la fotografía
            </label>
            <input
              id="photo-alt"
              value={alt}
              maxLength={200}
              onChange={(event) => setAlt(event.target.value)}
              className="mt-2 w-full rounded-lg border border-border px-3 py-2"
            />
          </div>
          <div>
            <label htmlFor="photo-order" className="text-sm font-medium">
              Orden
            </label>
            <input
              id="photo-order"
              value={order}
              inputMode="numeric"
              onChange={(event) => setOrder(event.target.value)}
              className="mt-2 block w-24 rounded-lg border border-border px-3 py-2"
            />
          </div>
          <div className="flex gap-3">
            <Button disabled={pending || (!editing && property.photos.length >= 10)}>
              {pending ? 'Guardando…' : editing ? 'Guardar foto' : 'Subir foto'}
            </Button>
            {editing && (
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setEditing(null)
                  setAlt('')
                  setOrder('0')
                }}
              >
                Cancelar edición
              </Button>
            )}
          </div>
        </form>
      )}
      {error && (
        <p role="alert" className="mt-4 text-red-800">
          {error}
        </p>
      )}
    </section>
  )
}

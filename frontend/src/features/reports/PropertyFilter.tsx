import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { propertyApi } from '@/features/properties/api'

export function PropertyFilter({
  tenant,
  value,
  onChange,
}: {
  tenant: string
  value: string
  onChange: (value: string) => void
}) {
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<{ id: string; name: string; active: boolean } | null>(
    null,
  )
  const result = useQuery({
    queryKey: ['report-properties', tenant, search, page],
    queryFn: () => propertyApi.list(tenant, search, 'all', page),
  })
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <label>
        Buscar cabaña
        <input
          className="mt-2 w-full rounded-lg border p-3"
          maxLength={150}
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setPage(1)
          }}
        />
      </label>
      <div>
        <label htmlFor="report-property">Cabaña</label>
        <select
          id="report-property"
          className="mt-2 w-full rounded-lg border bg-white p-3"
          value={value}
          onChange={(e) => {
            onChange(e.target.value)
            setSelected(result.data?.results.find((item) => item.id === e.target.value) ?? null)
          }}
        >
          <option value="">Todas las cabañas</option>
          {selected && !result.data?.results.some((item) => item.id === selected.id) && (
            <option value={selected.id}>
              {selected.name}
              {selected.active ? '' : ' · Inactiva'}
            </option>
          )}
          {result.data?.results.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
              {item.active ? '' : ' · Inactiva'}
            </option>
          ))}
        </select>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          disabled={!result.data?.previous}
          onClick={() => setPage(page - 1)}
        >
          Cabañas anteriores
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={!result.data?.next}
          onClick={() => setPage(page + 1)}
        >
          Más cabañas
        </Button>
      </div>
      {result.error && <p role="alert">{result.error.message}</p>}
    </div>
  )
}

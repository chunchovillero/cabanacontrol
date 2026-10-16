import { useId, useState } from 'react'

type Option = { value: string; label: string }

export function SearchSelect({
  label,
  value,
  selectedLabel,
  options,
  search,
  onSearch,
  onChange,
  loading,
  error,
  previous,
  next,
  onPrevious,
  onNext,
}: {
  label: string
  value: string
  selectedLabel?: string
  options: Option[]
  search: string
  onSearch: (text: string) => void
  onChange: (value: string) => void
  loading: boolean
  error?: string
  previous?: boolean
  next?: boolean
  onPrevious: () => void
  onNext: () => void
}) {
  const id = useId()
  const [open, setOpen] = useState(false)
  const [highlighted, setHighlighted] = useState(-1)
  const [chosen, setChosen] = useState<Option | null>(null)
  const current = options.find((option) => option.value === value)
  const display = selectedLabel ?? current?.label ?? (chosen?.value === value ? chosen.label : '')
  const choose = (option: Option) => {
    setChosen(option)
    onChange(option.value)
    setOpen(false)
    setHighlighted(-1)
  }
  return (
    <div
      className="relative min-w-0"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setOpen(false)
      }}
    >
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      <div className="relative mt-2">
        <input
          id={id}
          role="combobox"
          aria-expanded={open}
          aria-controls={`${id}-options`}
          aria-autocomplete="list"
          aria-activedescendant={
            open && highlighted >= 0 ? `${id}-option-${highlighted}` : undefined
          }
          autoComplete="off"
          maxLength={150}
          value={open ? search : display}
          placeholder={`Buscar y seleccionar ${label.toLowerCase()}…`}
          className="w-full rounded-lg border border-border bg-white px-3 py-3 pr-9 focus-visible:outline-2 focus-visible:outline-primary"
          onFocus={() => {
            setOpen(true)
            onSearch('')
            setHighlighted(-1)
          }}
          onChange={(event) => {
            onSearch(event.target.value)
            setOpen(true)
            setHighlighted(-1)
          }}
          onKeyDown={(event) => {
            if (event.key === 'Escape') {
              event.preventDefault()
              setOpen(false)
            }
            if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
              event.preventDefault()
              setOpen(true)
              setHighlighted((index) =>
                Math.max(
                  0,
                  Math.min(options.length - 1, index + (event.key === 'ArrowDown' ? 1 : -1)),
                ),
              )
            }
            if (event.key === 'Enter' && open) {
              event.preventDefault()
              if (options[highlighted]) choose(options[highlighted])
            }
          }}
        />
        <span
          aria-hidden="true"
          className="pointer-events-none absolute right-3 top-3 text-muted-foreground"
        >
          ⌄
        </span>
      </div>
      {open && (
        <div className="absolute inset-x-0 top-full z-30 mt-1 overflow-hidden rounded-xl border border-border bg-white shadow-lg">
          {value && (
            <button
              type="button"
              className="w-full border-b border-border px-3 py-2 text-left text-xs text-muted-foreground hover:bg-muted"
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => {
                onChange('')
                setChosen(null)
                onSearch('')
              }}
            >
              Quitar selección: {display}
            </button>
          )}
          <ul
            id={`${id}-options`}
            role="listbox"
            aria-label={label}
            className="max-h-60 overflow-y-auto p-1"
          >
            {options.map((option, index) => (
              <li
                key={option.value}
                id={`${id}-option-${index}`}
                role="option"
                aria-selected={value === option.value}
                onMouseDown={(event) => event.preventDefault()}
                onMouseEnter={() => setHighlighted(index)}
                onClick={() => choose(option)}
                className={`cursor-pointer rounded-lg px-3 py-3 text-sm ${highlighted === index || value === option.value ? 'bg-primary/10 text-primary' : 'hover:bg-muted'}`}
              >
                {option.label}
              </li>
            ))}
          </ul>
          {loading && (
            <p role="status" className="p-3 text-sm text-muted-foreground">
              Buscando…
            </p>
          )}
          {error && (
            <p role="alert" className="p-3 text-sm text-red-800">
              {error}
            </p>
          )}
          {!loading && !error && options.length === 0 && (
            <p className="p-3 text-sm text-muted-foreground">No hay resultados.</p>
          )}
          {(previous || next) && (
            <div className="flex justify-between border-t border-border p-2">
              <button
                type="button"
                disabled={!previous}
                onClick={() => {
                  onPrevious()
                  setHighlighted(-1)
                }}
                className="rounded-lg px-3 py-2 text-sm disabled:opacity-40"
              >
                Anterior
              </button>
              <button
                type="button"
                disabled={!next}
                onClick={() => {
                  onNext()
                  setHighlighted(-1)
                }}
                className="rounded-lg px-3 py-2 text-sm disabled:opacity-40"
              >
                Más resultados
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

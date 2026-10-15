function parts(date: Date, zone: string) {
  const fields = new Intl.DateTimeFormat('en-CA', {
    timeZone: zone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(date)
  const get = (key: string) => fields.find((part) => part.type === key)!.value
  return `${get('year')}-${get('month')}-${get('day')}T${get('hour')}:${get('minute')}`
}
export const todayInZone = (zone: string) => parts(new Date(), zone).slice(0, 10)
export const localHold = (iso: string, zone: string) => parts(new Date(iso), zone)
export function holdToIso(value: string, zone: string) {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value))
    throw new Error('Indica fecha y hora de retención.')
  const naive = new Date(`${value}:00Z`).getTime()
  if (!Number.isFinite(naive)) throw new Error('Fecha y hora no válidas.')
  const candidates: Date[] = []
  // Desplazamientos modernos IANA; no depender de la zona del navegador.
  for (let offset = -14 * 60; offset <= 14 * 60; offset += 15) {
    const candidate = new Date(naive + offset * 60000)
    if (parts(candidate, zone) === value) candidates.push(candidate)
  }
  if (candidates.length !== 1)
    throw new Error('Esa hora es inexistente o ambigua por el cambio de hora. Elige otra hora.')
  return candidates[0].toISOString()
}
export function formatDate(value: string) {
  const [year, month, day] = value.split('-')
  return `${day}/${month}/${year}`
}
export function formatHold(value: string, zone: string) {
  return new Intl.DateTimeFormat('es-CL', {
    dateStyle: 'short',
    timeStyle: 'short',
    timeZone: zone,
  }).format(new Date(value))
}

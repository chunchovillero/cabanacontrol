import { z } from 'zod'
import { request, write } from '@/lib/api'

export const photoSchema = z.object({
  id: z.string().uuid(),
  url: z.string().startsWith('/api/v1/properties/'),
  alt: z.string(),
  order: z.number().int(),
  active: z.boolean(),
})
export const propertySchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  code: z.string(),
  description: z.string(),
  capacity: z.number().int(),
  address: z.string(),
  base_rate: z.string(),
  currency: z.string(),
  check_in_time: z.string(),
  check_out_time: z.string(),
  active: z.boolean(),
  photos: z.array(photoSchema),
  created_at: z.string(),
  updated_at: z.string(),
})
export type Property = z.infer<typeof propertySchema>
export type Photo = z.infer<typeof photoSchema>
export type PropertyInput = Pick<
  Property,
  | 'name'
  | 'code'
  | 'description'
  | 'capacity'
  | 'address'
  | 'base_rate'
  | 'check_in_time'
  | 'check_out_time'
>
export const propertyListSchema = z.object({
  count: z.number(),
  next: z.string().nullable(),
  previous: z.string().nullable(),
  results: z.array(propertySchema),
})
const headers = (tenant: string) => ({ 'X-Tenant-Context': tenant })

export const propertyApi = {
  async list(tenant: string, search: string, active: string, page: number) {
    const params = new URLSearchParams({ search, page: String(page), ordering: 'name' })
    if (active !== 'all') params.set('active', active)
    return propertyListSchema.parse(
      await request(`/api/v1/properties/?${params}`, { headers: headers(tenant) }),
    )
  },
  async get(tenant: string, id: string) {
    return propertySchema.parse(
      await request(`/api/v1/properties/${encodeURIComponent(id)}/`, { headers: headers(tenant) }),
    )
  },
  async create(tenant: string, data: PropertyInput) {
    return propertySchema.parse(await write('/api/v1/properties/', data, 'POST', headers(tenant)))
  },
  async update(tenant: string, id: string, data: Partial<PropertyInput> & { active?: boolean }) {
    return propertySchema.parse(
      await write(`/api/v1/properties/${encodeURIComponent(id)}/`, data, 'PATCH', headers(tenant)),
    )
  },
  async upload(tenant: string, id: string, file: File, alt: string, order: number) {
    const form = new FormData()
    form.set('file', file)
    form.set('alt', alt)
    form.set('order', String(order))
    return photoSchema.parse(
      await write(
        `/api/v1/properties/${encodeURIComponent(id)}/photos/`,
        form,
        'POST',
        headers(tenant),
      ),
    )
  },
  async updatePhoto(
    tenant: string,
    id: string,
    photoId: string,
    data: { alt?: string; order?: number; active?: boolean },
  ) {
    return photoSchema.parse(
      await write(
        `/api/v1/properties/${encodeURIComponent(id)}/photos/${encodeURIComponent(photoId)}/`,
        data,
        'PATCH',
        headers(tenant),
      ),
    )
  },
}

export function formatMoney(value: string, currency: string) {
  const [whole, fraction = '00'] = value.split('.')
  const grouped = new Intl.NumberFormat('es-CL').format(BigInt(whole))
  return `${currency === 'CLP' ? '$' : currency} ${grouped}${fraction !== '00' ? `,${fraction}` : ''}`
}

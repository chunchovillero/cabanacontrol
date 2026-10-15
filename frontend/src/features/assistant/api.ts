import { z } from 'zod'
import { request, write } from '@/lib/api'

const settingsSchema = z.object({
  enabled: z.boolean(),
  voice_enabled: z.boolean(),
  daily_requests: z.number(),
  daily_tokens: z.number(),
  daily_audio_seconds: z.number(),
  daily_budget_usd: z.string(),
})
const capabilitiesSchema = z.object({
  simulated: z.boolean(),
  ready: z.boolean(),
  enabled: z.boolean(),
  voice_enabled: z.boolean(),
  settings: settingsSchema,
})
const itemSchema = z.object({
  id: z.string().uuid().optional(),
  name: z.string().optional(),
  capacity: z.number().optional(),
  property: z.string().optional(),
  guest: z.string().optional(),
  amount: z.string().optional(),
  currency: z.string().optional(),
  url: z
    .string()
    .regex(/^\/(reservas|cabanas)\/[0-9a-f-]{36}$/)
    .optional(),
})
export const answerSchema = z.object({
  context: z.string(),
  results: z.array(
    z.object({
      tool: z.enum([
        'clarify',
        'search_available_properties',
        'list_arrivals',
        'list_outstanding_balances',
        'summarize_collections',
        'prepare_whatsapp_message',
      ]),
      data: z.object({
        verified_at: z.string().optional(),
        messages: z.array(z.string()).optional(),
        message: z.string().optional(),
        price_notice: z.string().optional(),
        date: z.string().optional(),
        check_in: z.string().optional(),
        check_out: z.string().optional(),
        guests: z.number().int().optional(),
        start_date: z.string().optional(),
        end_date: z.string().optional(),
        total: z.number().optional(),
        page: z.number().optional(),
        has_more: z.boolean().optional(),
        items: z.array(itemSchema).optional(),
      }),
    }),
  ),
})
export type Answer = z.infer<typeof answerSchema>
export const assistantApi = {
  async prepare(
    tenant: string,
    data: { property_id: string; check_in: string; check_out: string; guests: number },
  ) {
    return answerSchema.parse(
      await write('/api/v1/assistant/whatsapp/', data, 'POST', { 'X-Tenant-Context': tenant }),
    )
  },
  async capabilities(tenant: string) {
    return capabilitiesSchema.parse(
      await request('/api/v1/assistant/capabilities/', { headers: { 'X-Tenant-Context': tenant } }),
    )
  },
  async configure(tenant: string, data: Partial<z.infer<typeof settingsSchema>>) {
    return settingsSchema.parse(
      await write('/api/v1/assistant/settings/', data, 'PATCH', { 'X-Tenant-Context': tenant }),
    )
  },
  async message(tenant: string, text: string, context: string) {
    return answerSchema.parse(
      await write(
        '/api/v1/assistant/messages/',
        { text, context, reviewed: true },
        'POST',
        { 'X-Tenant-Context': tenant },
        35000,
      ),
    )
  },
  async transcribe(tenant: string, file: Blob) {
    const data = new FormData()
    const extension = file.type.includes('mp4') ? 'mp4' : file.type.includes('wav') ? 'wav' : 'webm'
    data.append('audio', file, `dictado.${extension}`)
    data.append('reviewed', 'true')
    return z
      .object({ text: z.string().max(4000) })
      .parse(
        await write(
          '/api/v1/assistant/transcriptions/',
          data,
          'POST',
          { 'X-Tenant-Context': tenant },
          35000,
        ),
      )
  },
}

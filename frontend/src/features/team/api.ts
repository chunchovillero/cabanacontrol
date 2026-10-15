import { z } from 'zod'
import { request, write } from '@/lib/api'

const memberSchema = z.object({
  id: z.string().uuid(),
  user_id: z.string().uuid(),
  email: z.string(),
  name: z.string(),
  role: z.enum(['owner', 'manager', 'staff']),
  active: z.boolean(),
})
const invitationSchema = z.object({
  id: z.string().uuid(),
  email: z.string(),
  role: z.enum(['manager', 'staff']),
  state: z.enum(['pending', 'accepted', 'revoked', 'expired']),
  expires_at: z.string(),
})
const previewSchema = z.object({
  company_name: z.string(),
  role: z.string(),
  email_hint: z.string(),
  expires_at: z.string(),
})
export type Member = z.infer<typeof memberSchema>
export type Invitation = z.infer<typeof invitationSchema>
export type Preview = z.infer<typeof previewSchema>
export type MemberRole = 'manager' | 'staff'
const page = <T extends z.ZodType>(schema: T) =>
  z.object({
    results: z.array(schema),
    next: z.string().nullable(),
    previous: z.string().nullable(),
  })
const context = (tenant: string) => ({ 'X-Tenant-Context': tenant })
export const teamApi = {
  async members(tenant: string, number: number) {
    return page(memberSchema).parse(
      await request(`/api/v1/team/memberships/?page=${number}`, {
        headers: context(tenant),
      }),
    )
  },
  async invitations(tenant: string, number: number) {
    return page(invitationSchema).parse(
      await request(`/api/v1/team/invitations/?page=${number}`, { headers: context(tenant) }),
    )
  },
  async create(tenant: string, email: string, role: MemberRole) {
    return z
      .object({ invitation: invitationSchema, link: z.string() })
      .parse(await write('/api/v1/team/invitations/', { email, role }, 'POST', context(tenant)))
  },
  async change(tenant: string, member: Member, role: MemberRole, active: boolean) {
    return memberSchema.parse(
      await write(
        `/api/v1/team/memberships/${member.id}/`,
        {
          role,
          active,
          expected_role: member.role,
          expected_active: member.active,
        },
        'PATCH',
        context(tenant),
      ),
    )
  },
  async revoke(tenant: string, id: string) {
    return invitationSchema.parse(
      await write(`/api/v1/team/invitations/${id}/revoke/`, {}, 'POST', context(tenant)),
    )
  },
  async preview(token: string) {
    return previewSchema.parse(await write('/api/v1/invitations/preview/', { token }))
  },
  async accept(data: {
    token: string
    mode: 'existing' | 'new'
    first_name?: string
    last_name?: string
    password?: string
  }) {
    return z.object({ detail: z.string() }).parse(await write('/api/v1/invitations/accept/', data))
  },
}

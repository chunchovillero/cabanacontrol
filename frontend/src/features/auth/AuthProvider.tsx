import { createContext, useContext, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, type Session } from '@/lib/api'

const AuthContext = createContext<{
  session: Session | null
  loading: boolean
  error: Error | null
  retry: () => void
} | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const query = useQuery({
    queryKey: ['session'],
    queryFn: api.me,
    retry: false,
    staleTime: 0,
  })
  return (
    <AuthContext.Provider
      value={{
        session: query.data ?? null,
        loading: query.isPending,
        error: query.error,
        retry: () => {
          void query.refetch()
        },
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('AuthProvider requerido')
  return value
}

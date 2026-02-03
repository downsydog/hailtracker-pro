import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

export type UserRole = 'admin' | 'manager' | 'technician' | 'customer' | string

export interface User {
  id: string
  email: string
  name: string
  role: string
  first_name?: string
  last_name?: string
  phone?: string
  username?: string
  permissions?: string[]
}

export interface Tenant {
  id: string
  name: string
  settings?: Record<string, unknown>
  plan?: string
  api_limit?: number
  api_used?: number
}

export interface AuthContextType {
  user: User | null
  tenant: Tenant | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  register?: (data: { email: string; password: string; name?: string; company_name?: string; first_name?: string; last_name?: string; phone?: string }) => Promise<void>
  refreshUser?: () => Promise<void>
  canManageTeam: boolean
  canManageSettings: boolean
  canViewAllLeads: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [tenant, _setTenant] = useState<Tenant | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Permission helpers
  const canManageTeam = user?.role === 'admin' || user?.role === 'manager'
  const canManageSettings = user?.role === 'admin'
  const canViewAllLeads = user?.role === 'admin' || user?.role === 'manager'

  const refreshUser = async () => {
    // Placeholder for refreshing user data
  }

  const register = async (_data: { email: string; password: string; name?: string; company_name?: string; first_name?: string; last_name?: string; phone?: string }) => {
    // Placeholder for registration
    throw new Error('Registration not implemented')
  }

  useEffect(() => {
    // Check for existing session
    const token = localStorage.getItem('token')
    if (token) {
      // For now, create a mock user
      setUser({
        id: '1',
        email: 'admin@hailtracker.com',
        name: 'Admin User',
        role: 'admin'
      })
    }
    setIsLoading(false)
  }, [])

  const login = async (email: string, password: string) => {
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })

      if (!response.ok) {
        throw new Error('Login failed')
      }

      const data = await response.json()
      localStorage.setItem('token', data.token)
      setUser(data.user)
    } catch (error) {
      throw error
    }
  }

  const logout = () => {
    localStorage.removeItem('token')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{
      user,
      tenant,
      isLoading,
      isAuthenticated: !!user,
      login,
      logout,
      register,
      refreshUser,
      canManageTeam,
      canManageSettings,
      canViewAllLeads,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

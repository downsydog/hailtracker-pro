import { createContext, useContext, useState, useCallback, useEffect, useMemo, ReactNode } from "react"

// User roles for the multi-tenant system
export type UserRole = 'owner' | 'manager' | 'desk' | 'tech' | 'salesman'

export interface AuthUser {
  id: number
  username: string
  email: string
  name: string
  first_name?: string
  last_name?: string
  phone?: string
  role: UserRole
  permissions: string[]
  is_active: boolean
  created_at?: string
  // Tenant info
  tenant_id?: number
  tenant_name?: string
  tenant_slug?: string
}

interface Tenant {
  id: number
  name: string
  slug: string
  plan: string
  is_active: boolean
  api_limit: number
  api_used: number
}

interface AuthContextType {
  user: AuthUser | null
  tenant: Tenant | null
  token: string | null
  isLoading: boolean
  isAuthenticated: boolean
  // Role-based permissions
  isOwner: boolean
  isManager: boolean
  canManageTeam: boolean
  canViewAllLeads: boolean
  canExportData: boolean
  canManageSettings: boolean
  // Auth methods
  login: (email: string, password: string) => Promise<void>
  register: (data: RegisterData) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

interface RegisterData {
  company_name: string
  email: string
  password: string
  first_name: string
  last_name: string
  phone?: string
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

const API_BASE = '/api'

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [tenant, setTenant] = useState<Tenant | null>(null)
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('auth_token'))
  const [isLoading, setIsLoading] = useState(true)

  // Fetch current user from API
  const refreshUser = useCallback(async () => {
    const storedToken = localStorage.getItem('auth_token')
    if (!storedToken) {
      setUser(null)
      setTenant(null)
      setIsLoading(false)
      return
    }

    try {
      const response = await fetch(`${API_BASE}/auth/me`, {
        headers: {
          'Authorization': `Bearer ${storedToken}`,
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error('Not authenticated')
      }

      const data = await response.json()
      setUser(data.user)
      setTenant(data.tenant)
      setToken(storedToken)
    } catch {
      localStorage.removeItem('auth_token')
      setUser(null)
      setTenant(null)
      setToken(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Check auth on mount
  useEffect(() => {
    refreshUser()
  }, [refreshUser])

  // Login function
  const login = useCallback(async (email: string, password: string) => {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.error || 'Login failed')
    }

    const data = await response.json()

    localStorage.setItem('auth_token', data.token)
    setToken(data.token)
    setUser(data.user)
    setTenant(data.tenant)
  }, [])

  // Register function
  const register = useCallback(async (registerData: RegisterData) => {
    const response = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(registerData),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.error || 'Registration failed')
    }

    const data = await response.json()

    localStorage.setItem('auth_token', data.token)
    setToken(data.token)
    setUser(data.user)
    setTenant(data.tenant)
  }, [])

  // Logout function
  const logout = useCallback(() => {
    localStorage.removeItem('auth_token')
    setToken(null)
    setUser(null)
    setTenant(null)
  }, [])

  // Role-based permission helpers
  const isOwner = user?.role === 'owner'
  const isManager = user?.role === 'manager' || isOwner
  const canManageTeam = isOwner || isManager
  const canViewAllLeads = isOwner || isManager || user?.role === 'desk'
  const canExportData = isOwner || isManager
  const canManageSettings = isOwner

  const value = useMemo(
    () => ({
      user,
      tenant,
      token,
      isLoading,
      isAuthenticated: !!user && !!token,
      isOwner,
      isManager,
      canManageTeam,
      canViewAllLeads,
      canExportData,
      canManageSettings,
      login,
      register,
      logout,
      refreshUser,
    }),
    [user, tenant, token, isLoading, isOwner, isManager, canManageTeam, canViewAllLeads, canExportData, canManageSettings, login, register, logout, refreshUser]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}

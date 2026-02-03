import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react'

// DEV_MODE: When true, automatically logs in as dev admin
// Set VITE_DEV_MODE=false in .env to require real login
const DEV_MODE = import.meta.env.VITE_DEV_MODE !== 'false'

export type UserRole = 'admin' | 'owner' | 'manager' | 'technician' | 'viewer' | string

export interface User {
  id: number | string
  email: string
  name: string
  role: string
  first_name?: string
  last_name?: string
  phone?: string
  username?: string
  permissions?: string[]
  tenant_id?: number
  role_name?: string
}

export interface Tenant {
  id: string | number
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
  register: (data: RegisterData) => Promise<void>
  refreshUser: () => Promise<void>
  refreshToken: () => Promise<boolean>
  canManageTeam: boolean
  canManageSettings: boolean
  canViewAllLeads: boolean
  isDevMode: boolean
}

interface RegisterData {
  email: string
  password: string
  name?: string
  company_name?: string
  first_name?: string
  last_name?: string
  phone?: string
}

interface AuthResponse {
  success: boolean
  token: string
  refresh_token: string
  user: User
  dev_mode?: boolean
  error?: string
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [tenant, setTenant] = useState<Tenant | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Permission helpers
  const canManageTeam = user?.role === 'admin' || user?.role === 'owner' || user?.role === 'manager'
  const canManageSettings = user?.role === 'admin' || user?.role === 'owner'
  const canViewAllLeads = user?.role === 'admin' || user?.role === 'owner' || user?.role === 'manager'

  // Refresh user data from /api/auth/me
  const refreshUser = useCallback(async () => {
    const token = localStorage.getItem('token')
    if (!token) return

    try {
      const response = await fetch('/api/auth/me', {
        headers: { Authorization: `Bearer ${token}` }
      })

      if (response.ok) {
        const userData = await response.json()
        setUser(userData)
        if (userData.tenant_id) {
          setTenant({
            id: userData.tenant_id,
            name: userData.tenant_name || 'My Company',
            plan: userData.plan || 'free'
          })
        }
      } else if (response.status === 401) {
        // Token expired, try to refresh
        const refreshed = await refreshTokenFn()
        if (refreshed) {
          // Retry getting user info
          await refreshUser()
        } else {
          // Refresh failed, logout
          logout()
        }
      }
    } catch (error) {
      console.error('Failed to refresh user:', error)
    }
  }, [])

  // Refresh the access token using refresh token
  const refreshTokenFn = async (): Promise<boolean> => {
    const refreshToken = localStorage.getItem('refresh_token')
    if (!refreshToken) return false

    try {
      const response = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken })
      })

      if (response.ok) {
        const data = await response.json()
        localStorage.setItem('token', data.token)
        localStorage.setItem('refresh_token', data.refresh_token)
        return true
      }
    } catch (error) {
      console.error('Token refresh failed:', error)
    }

    return false
  }

  // Auto-login in DEV_MODE
  const devModeLogin = useCallback(async () => {
    try {
      // Call login with any credentials - backend will return dev user
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'dev@dev.com', password: 'dev' })
      })

      if (response.ok) {
        const data: AuthResponse = await response.json()
        localStorage.setItem('token', data.token)
        localStorage.setItem('refresh_token', data.refresh_token)
        setUser(data.user)
        if (data.user.tenant_id) {
          setTenant({
            id: data.user.tenant_id,
            name: 'Dev Tenant',
            plan: 'enterprise'
          })
        }
        console.log('DEV_MODE: Auto-logged in as', data.user.email)
      }
    } catch (error) {
      console.error('DEV_MODE login failed:', error)
    }
  }, [])

  // Initialize auth state
  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('token')

      if (token) {
        // Have a token, verify it's still valid
        await refreshUser()
      } else if (DEV_MODE) {
        // No token but DEV_MODE is on, auto-login
        await devModeLogin()
      }

      setIsLoading(false)
    }

    initAuth()
  }, [devModeLogin, refreshUser])

  const login = async (email: string, password: string) => {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    })

    const data: AuthResponse = await response.json()

    if (!response.ok || !data.success) {
      throw new Error(data.error || 'Login failed')
    }

    localStorage.setItem('token', data.token)
    localStorage.setItem('refresh_token', data.refresh_token)
    setUser(data.user)

    if (data.user.tenant_id) {
      setTenant({
        id: data.user.tenant_id,
        name: data.user.name + "'s Company",
        plan: 'free'
      })
    }
  }

  const register = async (formData: RegisterData) => {
    // Build name from first_name and last_name if provided
    const name = formData.name ||
      (formData.first_name && formData.last_name
        ? `${formData.first_name} ${formData.last_name}`
        : formData.email.split('@')[0])

    const response = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: formData.email,
        password: formData.password,
        name: name,
        phone: formData.phone
      })
    })

    const data: AuthResponse = await response.json()

    if (!response.ok || !data.success) {
      throw new Error(data.error || 'Registration failed')
    }

    localStorage.setItem('token', data.token)
    localStorage.setItem('refresh_token', data.refresh_token)
    setUser(data.user)

    if (data.user.tenant_id) {
      setTenant({
        id: data.user.tenant_id,
        name: formData.company_name || name + "'s Company",
        plan: 'free'
      })
    }
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('refresh_token')
    setUser(null)
    setTenant(null)

    // Call logout endpoint (fire and forget)
    fetch('/api/auth/logout', { method: 'POST' }).catch(() => {})

    // In DEV_MODE, re-login after logout
    if (DEV_MODE) {
      setTimeout(() => {
        devModeLogin()
      }, 100)
    }
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
      refreshToken: refreshTokenFn,
      canManageTeam,
      canManageSettings,
      canViewAllLeads,
      isDevMode: DEV_MODE,
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

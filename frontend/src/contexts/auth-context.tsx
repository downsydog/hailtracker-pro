import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react'

// DEV_MODE: When true, automatically logs in as dev admin
// Set VITE_DEV_MODE=false in .env to require real login
const DEV_MODE = import.meta.env.VITE_DEV_MODE !== 'false'

export type UserRole = 'admin' | 'owner' | 'manager' | 'technician' | 'viewer' | string

/**
 * Permission summary returned by /api/auth/me endpoint.
 * These match the backend's get_role_permissions_summary() output.
 */
export interface UserPermissions {
  canSendEmail: boolean
  canCreateShareLink: boolean
  canDownloadDisputePack: boolean
  canCreateSupplement: boolean
  canSendSupplement: boolean
  canEditPricing: boolean
  canEditDamage: boolean
  canManageUsers: boolean
  canManageSettings: boolean
  // Customer authorization workflow
  canRequestSignature: boolean
  // Legacy (for backward compatibility)
  canApproveEstimate: boolean
  canDeclineEstimate: boolean
  // Insurer workflow
  canSubmitToInsurer: boolean
  canInsurerApprove: boolean
  canInsurerDecline: boolean
}

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
  role_display?: string
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
  // Legacy permission checks
  canManageTeam: boolean
  canManageSettings: boolean
  canViewAllLeads: boolean
  isDevMode: boolean
  // Estimating-specific permissions (from backend)
  permissions: UserPermissions
  roleDisplay: string
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

// Default permissions for unauthenticated or when backend doesn't provide them
const DEFAULT_PERMISSIONS: UserPermissions = {
  canSendEmail: false,
  canCreateShareLink: false,
  canDownloadDisputePack: false,
  canCreateSupplement: false,
  canSendSupplement: false,
  canEditPricing: false,
  canEditDamage: false,
  canManageUsers: false,
  canManageSettings: false,
  canRequestSignature: false,
  canApproveEstimate: false,
  canDeclineEstimate: false,
  canSubmitToInsurer: false,
  canInsurerApprove: false,
  canInsurerDecline: false,
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [tenant, setTenant] = useState<Tenant | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [permissions, setPermissions] = useState<UserPermissions>(DEFAULT_PERMISSIONS)
  const [roleDisplay, setRoleDisplay] = useState<string>('')

  // Legacy permission helpers (based on role)
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
        const data = await response.json()
        // Backend returns { user, tenant, permissions, can, role_display }
        const userData = data.user || data
        setUser(userData)

        // Update tenant from response
        const tenantData = data.tenant
        if (tenantData) {
          setTenant({
            id: tenantData.id,
            name: tenantData.company_name || tenantData.name || 'My Company',
            plan: tenantData.plan || 'free'
          })
        } else if (userData.tenant_id) {
          setTenant({
            id: userData.tenant_id,
            name: userData.tenant_name || 'My Company',
            plan: userData.plan || 'free'
          })
        }

        // Update permissions from backend's "can" summary
        if (data.can) {
          setPermissions({
            canSendEmail: data.can.canSendEmail ?? false,
            canCreateShareLink: data.can.canCreateShareLink ?? false,
            canDownloadDisputePack: data.can.canDownloadDisputePack ?? false,
            canCreateSupplement: data.can.canCreateSupplement ?? false,
            canSendSupplement: data.can.canSendSupplement ?? false,
            canEditPricing: data.can.canEditPricing ?? false,
            canEditDamage: data.can.canEditDamage ?? false,
            canManageUsers: data.can.canManageUsers ?? false,
            canManageSettings: data.can.canManageSettings ?? false,
            canRequestSignature: data.can.canRequestSignature ?? false,
            canApproveEstimate: data.can.canApproveEstimate ?? false,
            canDeclineEstimate: data.can.canDeclineEstimate ?? false,
            canSubmitToInsurer: data.can.canSubmitToInsurer ?? false,
            canInsurerApprove: data.can.canInsurerApprove ?? false,
            canInsurerDecline: data.can.canInsurerDecline ?? false,
          })
        }

        // Update role display name
        if (data.role_display) {
          setRoleDisplay(data.role_display)
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
    setPermissions(DEFAULT_PERMISSIONS)
    setRoleDisplay('')

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
      permissions,
      roleDisplay,
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

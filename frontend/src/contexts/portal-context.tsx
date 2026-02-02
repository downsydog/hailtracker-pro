import * as React from "react"
import { portalApi, PortalCustomer } from "@/api/portal"

interface PortalContextType {
  customer: PortalCustomer | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (accessCode: string, identifier?: string) => Promise<boolean>
  logout: () => Promise<void>
  refreshCustomer: () => Promise<void>
}

const PortalContext = React.createContext<PortalContextType | undefined>(undefined)

export function PortalProvider({ children }: { children: React.ReactNode }) {
  const [customer, setCustomer] = React.useState<PortalCustomer | null>(null)
  const [isLoading, setIsLoading] = React.useState(true)

  // Check for existing session on mount
  React.useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem("portal_token")
      if (token) {
        try {
          const response = await portalApi.verifyToken()
          if (response.success && response.customer) {
            setCustomer(response.customer)
          } else {
            localStorage.removeItem("portal_token")
          }
        } catch {
          localStorage.removeItem("portal_token")
        }
      }
      setIsLoading(false)
    }
    checkAuth()
  }, [])

  const login = async (accessCode: string, identifier?: string): Promise<boolean> => {
    try {
      const response = await portalApi.login({
        access_code: accessCode,
        email: identifier?.includes("@") ? identifier : undefined,
        phone: identifier && !identifier.includes("@") ? identifier : undefined,
      })

      if (response.success && response.token && response.customer) {
        localStorage.setItem("portal_token", response.token)
        setCustomer(response.customer)
        return true
      }
      return false
    } catch {
      return false
    }
  }

  const logout = async () => {
    try {
      await portalApi.logout()
    } catch {
      // Ignore errors
    }
    localStorage.removeItem("portal_token")
    setCustomer(null)
  }

  const refreshCustomer = async () => {
    try {
      const profile = await portalApi.getProfile()
      setCustomer(profile)
    } catch {
      // Ignore errors
    }
  }

  return (
    <PortalContext.Provider
      value={{
        customer,
        isAuthenticated: !!customer,
        isLoading,
        login,
        logout,
        refreshCustomer,
      }}
    >
      {children}
    </PortalContext.Provider>
  )
}

export function usePortal() {
  const context = React.useContext(PortalContext)
  if (context === undefined) {
    throw new Error("usePortal must be used within a PortalProvider")
  }
  return context
}

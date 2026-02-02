import * as React from "react"

interface PortalCustomer {
  id?: number
  first_name?: string
  last_name?: string
  email?: string
  phone?: string
  [key: string]: unknown  // Allow additional properties
}

interface PortalContextValue {
  isPortalView: boolean
  setIsPortalView: (value: boolean) => void
  portalToken: string | null
  setPortalToken: (token: string | null) => void
  portalJobId: number | null
  setPortalJobId: (id: number | null) => void
  customer: PortalCustomer | null
  setCustomer: (customer: PortalCustomer | null) => void
  isLoading: boolean
  isAuthenticated: boolean
  login: (token: string, identifier?: string) => Promise<boolean>
  logout: () => void
  refreshCustomer: () => Promise<void>
}

const PortalContext = React.createContext<PortalContextValue | undefined>(undefined)

export function PortalProvider({ children }: { children: React.ReactNode }) {
  const [isPortalView, setIsPortalView] = React.useState(false)
  const [portalToken, setPortalToken] = React.useState<string | null>(null)
  const [portalJobId, setPortalJobId] = React.useState<number | null>(null)
  const [customer, setCustomer] = React.useState<PortalCustomer | null>(null)
  const [isLoading, setIsLoading] = React.useState(false)

  const isAuthenticated = !!portalToken

  const login = React.useCallback(async (token: string, _identifier?: string): Promise<boolean> => {
    setPortalToken(token)
    return true
  }, [])

  const logout = React.useCallback(() => {
    setPortalToken(null)
    setCustomer(null)
  }, [])

  const refreshCustomer = React.useCallback(async () => {
    // Placeholder for refreshing customer data
    setIsLoading(true)
    try {
      // Could fetch customer data here
    } finally {
      setIsLoading(false)
    }
  }, [])

  React.useEffect(() => {
    // Check if we're in portal mode based on URL
    const path = window.location.pathname
    if (path.startsWith("/portal")) {
      setIsPortalView(true)
      // Extract token from URL if present
      const params = new URLSearchParams(window.location.search)
      const token = params.get("token")
      if (token) {
        setPortalToken(token)
      }
    }
  }, [])

  const value = React.useMemo(
    () => ({
      isPortalView,
      setIsPortalView,
      portalToken,
      setPortalToken,
      portalJobId,
      setPortalJobId,
      customer,
      setCustomer,
      isLoading,
      isAuthenticated,
      login,
      logout,
      refreshCustomer,
    }),
    [isPortalView, portalToken, portalJobId, customer, isLoading, isAuthenticated, login, logout, refreshCustomer]
  )

  return <PortalContext.Provider value={value}>{children}</PortalContext.Provider>
}

export function usePortal() {
  const context = React.useContext(PortalContext)
  if (!context) {
    throw new Error("usePortal must be used within a PortalProvider")
  }
  return context
}

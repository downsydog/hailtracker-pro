import * as React from "react"

interface PortalContextValue {
  isPortalView: boolean
  setIsPortalView: (value: boolean) => void
  portalToken: string | null
  setPortalToken: (token: string | null) => void
  portalJobId: number | null
  setPortalJobId: (id: number | null) => void
}

const PortalContext = React.createContext<PortalContextValue | undefined>(undefined)

export function PortalProvider({ children }: { children: React.ReactNode }) {
  const [isPortalView, setIsPortalView] = React.useState(false)
  const [portalToken, setPortalToken] = React.useState<string | null>(null)
  const [portalJobId, setPortalJobId] = React.useState<number | null>(null)

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
    }),
    [isPortalView, portalToken, portalJobId]
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

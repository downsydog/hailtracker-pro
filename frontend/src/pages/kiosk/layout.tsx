import { Outlet } from "react-router-dom"
import { Car } from "lucide-react"

export function KioskLayout() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 to-blue-800 flex flex-col">
      {/* Header */}
      <header className="bg-white/10 backdrop-blur-sm border-b border-white/20">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-12 w-12 rounded-full bg-white flex items-center justify-center">
              <Car className="h-7 w-7 text-blue-600" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">Self Check-In</h1>
              <p className="text-blue-200 text-sm">HailTracker Pro</p>
            </div>
          </div>
          <div className="text-right text-white">
            <p className="text-sm text-blue-200">Need help?</p>
            <p className="font-medium">Ask our staff</p>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-2xl">
          <Outlet />
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white/5 border-t border-white/20 py-4">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <p className="text-blue-200 text-sm">
            Touch anywhere to begin • Tap buttons to select
          </p>
        </div>
      </footer>
    </div>
  )
}

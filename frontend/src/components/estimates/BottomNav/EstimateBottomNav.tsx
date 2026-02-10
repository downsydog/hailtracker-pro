/**
 * Estimate Bottom Navigation
 * PDR / HAIL / R&I / PARTS tabs with running total
 * Always visible at screen bottom
 */

import { cn } from '@/lib/utils'
import { Wrench, CloudRain, RefreshCw, Package } from 'lucide-react'

export type ServiceTab = 'pdr' | 'hail' | 'ri' | 'parts'

interface EstimateBottomNavProps {
  activeTab: ServiceTab
  onTabChange: (tab: ServiceTab) => void
  totals: {
    pdr: number
    hail: number
    ri: number
    parts: number
    grand: number
  }
  className?: string
}

export function EstimateBottomNav({
  activeTab,
  onTabChange,
  totals,
  className
}: EstimateBottomNavProps) {
  const tabs: { id: ServiceTab; label: string; icon: React.ReactNode; amount: number }[] = [
    { id: 'pdr', label: 'PDR', icon: <Wrench className="h-4 w-4" />, amount: totals.pdr },
    { id: 'hail', label: 'HAIL', icon: <CloudRain className="h-4 w-4" />, amount: totals.hail },
    { id: 'ri', label: 'R&I', icon: <RefreshCw className="h-4 w-4" />, amount: totals.ri },
    { id: 'parts', label: 'PARTS', icon: <Package className="h-4 w-4" />, amount: totals.parts },
  ]

  return (
    <div className={cn(
      'fixed bottom-0 left-0 right-0 bg-white border-t shadow-lg z-50',
      className
    )}>
      <div className="flex items-stretch h-16">
        {/* Service Tabs */}
        <div className="flex flex-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={cn(
                'flex-1 flex flex-col items-center justify-center gap-0.5 transition-colors',
                'border-r last:border-r-0',
                activeTab === tab.id
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
              )}
            >
              {tab.icon}
              <span className="text-xs font-semibold">{tab.label}</span>
              {tab.amount > 0 && (
                <span className={cn(
                  'text-xs',
                  activeTab === tab.id ? 'text-blue-100' : 'text-gray-400'
                )}>
                  ${tab.amount.toFixed(0)}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Grand Total */}
        <div className="w-32 flex flex-col items-center justify-center bg-green-600 text-white px-4">
          <span className="text-xs font-medium opacity-80">TOTAL</span>
          <span className="text-xl font-bold">
            ${totals.grand.toFixed(2)}
          </span>
        </div>
      </div>
    </div>
  )
}

export default EstimateBottomNav

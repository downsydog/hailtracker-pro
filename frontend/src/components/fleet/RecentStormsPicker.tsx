import { useState, useEffect } from 'react'
import { recentStormsApi, SignificantStorm } from '../../api/fleet'

interface RecentStormsPickerProps {
  onSelectDate: (date: string) => void
  selectedDate?: string
}

export function RecentStormsPicker({ onSelectDate, selectedDate }: RecentStormsPickerProps) {
  const [storms, setStorms] = useState<SignificantStorm[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    loadStorms()
  }, [])

  const loadStorms = async () => {
    try {
      const data = await recentStormsApi.getRecentStorms({ days: 90, min_size: 1.0 })
      setStorms(data.storms || [])
    } catch (error) {
      console.error('Failed to load storms:', error)
    } finally {
      setLoading(false)
    }
  }

  const getSeverityStyle = (maxSize: number) => {
    if (maxSize >= 2.0) {
      return {
        bg: 'bg-red-100',
        text: 'text-red-700',
        badge: 'bg-red-500 text-white',
        border: 'border-red-300',
        severity: 'SEVERE',
      }
    } else if (maxSize >= 1.5) {
      return {
        bg: 'bg-orange-100',
        text: 'text-orange-700',
        badge: 'bg-orange-500 text-white',
        border: 'border-orange-300',
        severity: 'SIGNIFICANT',
      }
    } else {
      return {
        bg: 'bg-yellow-100',
        text: 'text-yellow-700',
        badge: 'bg-yellow-500 text-white',
        border: 'border-yellow-300',
        severity: 'MODERATE',
      }
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
    })
  }

  const displayedStorms = expanded ? storms : storms.slice(0, 5)

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-4">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-1/2 mb-3"></div>
          {[1, 2, 3].map(i => (
            <div key={i} className="h-16 bg-gray-100 rounded mb-2"></div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="font-bold text-lg mb-2 flex items-center gap-2">
        ⚡ Recent Significant Storms
        <span className="text-xs font-normal text-gray-500">(1&quot;+ hail, last 90 days)</span>
      </h3>

      <p className="text-sm text-gray-600 mb-3">
        Click a storm to see affected fleet businesses
      </p>

      {storms.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <div className="text-4xl mb-2">☀️</div>
          <div>No significant hail events in the last 90 days</div>
        </div>
      ) : (
        <>
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {displayedStorms.map(storm => {
              const style = getSeverityStyle(storm.max_hail_size)
              const isSelected = selectedDate === storm.date

              return (
                <button
                  key={storm.date}
                  onClick={() => onSelectDate(storm.date)}
                  className={`
                    w-full p-3 border rounded-lg text-left transition-all
                    ${style.bg} ${style.border}
                    ${isSelected ? 'ring-2 ring-blue-500 shadow-md' : 'hover:shadow'}
                  `}
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="font-medium flex items-center gap-2">
                        🌨️ {formatDate(storm.date)}
                        <span className={`text-xs px-2 py-0.5 rounded-full ${style.badge}`}>
                          {style.severity}
                        </span>
                      </div>
                      <div className="text-xs text-gray-600 mt-1">
                        {storm.major_cities?.slice(0, 3).join(', ')}
                        {storm.major_cities && storm.major_cities.length > 3 && ` +${storm.major_cities.length - 3} more`}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        {storm.states_affected?.join(', ')} • {storm.total_events} events
                        {storm.total_area_sq_miles > 0 && ` • ${storm.total_area_sq_miles.toFixed(0)} sq mi`}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className={`text-2xl font-bold ${style.text}`}>
                        {storm.max_hail_size}&quot;
                      </div>
                      <div className="text-xs text-gray-500">max hail</div>
                    </div>
                  </div>
                </button>
              )
            })}
          </div>

          {storms.length > 5 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="w-full mt-3 text-sm text-blue-600 hover:text-blue-800"
            >
              {expanded ? '← Show less' : `Show all ${storms.length} storms →`}
            </button>
          )}
        </>
      )}

      {/* Refresh Button */}
      <button
        onClick={loadStorms}
        className="w-full mt-3 text-xs text-gray-500 hover:text-gray-700"
      >
        🔄 Refresh storm data
      </button>
    </div>
  )
}

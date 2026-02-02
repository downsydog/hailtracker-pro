import { useState, useEffect } from 'react'
import { batchScrapeApi, ScrapePreset, BatchScrapeResult } from '../../api/fleet'

interface PresetWithKey extends ScrapePreset {
  key: string
  city_count: number
}

interface BatchScrapePanelProps {
  onComplete?: () => void
}

export function BatchScrapePanel({ onComplete }: BatchScrapePanelProps) {
  const [presets, setPresets] = useState<PresetWithKey[]>([])
  const [loading, setLoading] = useState(true)
  const [scraping, setScraping] = useState(false)
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null)
  const [result, setResult] = useState<BatchScrapeResult | null>(null)
  const [progress, setProgress] = useState<string>('')

  // Preset icons and colors
  const presetStyles: Record<string, { icon: string; color: string; bgColor: string }> = {
    hail_alley: { icon: '🌪️', color: 'text-red-700', bgColor: 'bg-red-50 border-red-200 hover:bg-red-100' },
    texas: { icon: '⭐', color: 'text-orange-700', bgColor: 'bg-orange-50 border-orange-200 hover:bg-orange-100' },
    midwest: { icon: '🌾', color: 'text-yellow-700', bgColor: 'bg-yellow-50 border-yellow-200 hover:bg-yellow-100' },
    southeast: { icon: '🍑', color: 'text-green-700', bgColor: 'bg-green-50 border-green-200 hover:bg-green-100' },
  }

  useEffect(() => {
    loadPresets()
  }, [])

  const loadPresets = async () => {
    try {
      const data = await batchScrapeApi.getPresets()
      // Convert object to array
      const presetsObj = data.presets || data
      const presetsArray = Object.entries(presetsObj).map(([key, value]: [string, any]) => ({
        key,
        name: value.name,
        description: value.description,
        cities: value.cities || [],
        city_count: value.cities?.length || value.city_count || 0,
      }))
      setPresets(presetsArray)
    } catch (error) {
      console.error('Failed to load presets:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleScrape = async (presetKey: string) => {
    setScraping(true)
    setSelectedPreset(presetKey)
    setResult(null)
    setProgress('Starting batch scrape...')

    try {
      // Simulate progress updates
      const progressMessages = [
        'Connecting to BBB...',
        'Scraping businesses...',
        'Processing results...',
        'Geocoding addresses...',
        'Almost done...',
      ]
      let msgIndex = 0

      const progressInterval = setInterval(() => {
        setProgress(progressMessages[msgIndex % progressMessages.length])
        msgIndex++
      }, 3000)

      const data = await batchScrapeApi.scrapePreset(presetKey)
      clearInterval(progressInterval)

      setResult(data)
      setProgress('')
      onComplete?.()
    } catch (error) {
      console.error('Batch scrape failed:', error)
      setProgress('')
      alert('Batch scrape failed. Check console for details.')
    } finally {
      setScraping(false)
      setSelectedPreset(null)
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-4">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="grid grid-cols-2 gap-3">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-20 bg-gray-100 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="font-bold text-lg mb-2 flex items-center gap-2">
        🔄 Batch Scrape Cities
      </h3>
      <p className="text-sm text-gray-600 mb-4">
        Scrape fleet businesses from multiple cities at once. This may take 5-15 minutes.
      </p>

      {/* Preset Buttons */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        {presets.map(preset => {
          const style = presetStyles[preset.key] || { icon: '📍', color: 'text-gray-700', bgColor: 'bg-gray-50 border-gray-200' }
          const isSelected = selectedPreset === preset.key

          return (
            <button
              key={preset.key}
              onClick={() => handleScrape(preset.key)}
              disabled={scraping}
              className={`
                p-4 border rounded-lg text-left transition-all
                ${style.bgColor}
                ${isSelected ? 'ring-2 ring-blue-500' : ''}
                ${scraping ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              `}
            >
              <div className={`font-bold flex items-center gap-2 ${style.color}`}>
                <span className="text-xl">{style.icon}</span>
                {preset.name}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {preset.description}
              </div>
              <div className="text-xs text-gray-400 mt-1">
                {preset.city_count} cities
              </div>
            </button>
          )
        })}
      </div>

      {/* Progress Indicator */}
      {scraping && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
          <div className="flex items-center gap-3">
            <div className="animate-spin text-2xl">🔄</div>
            <div>
              <div className="font-medium text-blue-700">Scraping in progress...</div>
              <div className="text-sm text-blue-600">{progress}</div>
            </div>
          </div>
          <div className="mt-3 text-xs text-blue-500">
            ⏱️ This typically takes 5-15 minutes. You can leave this page and come back.
          </div>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-2xl">✅</span>
            <span className="font-bold text-green-700">Scrape Complete!</span>
          </div>

          {/* Summary Stats */}
          <div className="grid grid-cols-3 gap-3 mb-4">
            <div className="bg-white rounded p-2 text-center">
              <div className="text-2xl font-bold text-blue-600">
                {result.total_new_businesses?.toLocaleString() || 0}
              </div>
              <div className="text-xs text-gray-500">Businesses</div>
            </div>
            <div className="bg-white rounded p-2 text-center">
              <div className="text-2xl font-bold text-purple-600">
                {result.total_new_vehicles?.toLocaleString() || 0}
              </div>
              <div className="text-xs text-gray-500">Est. Vehicles</div>
            </div>
            <div className="bg-white rounded p-2 text-center">
              <div className="text-2xl font-bold text-green-600">
                {result.results?.length || 0}
              </div>
              <div className="text-xs text-gray-500">Cities</div>
            </div>
          </div>

          {/* By City Breakdown */}
          {result.results && result.results.length > 0 && (
            <details className="mb-3">
              <summary className="cursor-pointer text-sm font-medium text-green-700 hover:text-green-800">
                View breakdown by city →
              </summary>
              <div className="mt-2 max-h-48 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="text-left text-gray-500">
                    <tr>
                      <th className="py-1">City</th>
                      <th className="text-right">Businesses</th>
                      <th className="text-right">Vehicles</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.results.map((city, i) => (
                      <tr key={i} className="border-t border-green-100">
                        <td className="py-1">{city.city}, {city.state}</td>
                        <td className="text-right">{city.new_businesses}</td>
                        <td className="text-right">{city.new_vehicles?.toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          )}

          {/* Errors */}
          {result.errors && result.errors.length > 0 && (
            <div className="text-xs text-red-600 mb-2">
              ⚠️ {result.errors.length} errors occurred
            </div>
          )}
        </div>
      )}

      {/* Tips */}
      <div className="mt-4 pt-4 border-t">
        <div className="text-xs text-gray-500">
          💡 Tip: Scrape before hail season to have businesses ready when storms hit.
        </div>
      </div>
    </div>
  )
}

import { useState, useEffect } from 'react'
import { fleetReportsApi, FleetLeadReports as ReportsData } from '../../api/fleet'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts'

const COLORS = ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

const STATUS_COLORS: Record<string, string> = {
  NEW: '#94a3b8',
  CONTACTED: '#3b82f6',
  QUALIFIED: '#f59e0b',
  NEGOTIATING: '#8b5cf6',
  CONVERTED: '#22c55e',
  LOST: '#ef4444',
}

export default function FleetLeadReportsPage() {
  const [data, setData] = useState<ReportsData | null>(null)
  const [startDate, setStartDate] = useState<string>('')
  const [endDate, setEndDate] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadReports()
  }, [startDate, endDate])

  const loadReports = async () => {
    setLoading(true)
    setError(null)

    try {
      const result = await fleetReportsApi.getReports({
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      })
      setData(result.reports)
    } catch (err) {
      console.error('Failed to load reports:', err)
      setError('Failed to load reports. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value: number) => {
    if (value >= 1000000) {
      return `$${(value / 1000000).toFixed(1)}M`
    } else if (value >= 1000) {
      return `$${(value / 1000).toFixed(0)}K`
    }
    return `$${value.toLocaleString()}`
  }

  const formatPercent = (value: number | null | undefined) => {
    if (value === null || value === undefined) return '0%'
    return `${value.toFixed(1)}%`
  }

  // Date range presets
  const setDateRange = (days: number) => {
    const end = new Date()
    const start = new Date()
    start.setDate(start.getDate() - days)
    setEndDate(end.toISOString().split('T')[0])
    setStartDate(start.toISOString().split('T')[0])
  }

  if (loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-200 rounded w-1/3"></div>
          <div className="grid grid-cols-4 gap-4">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-24 bg-gray-100 rounded-lg"></div>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-6">
            <div className="h-64 bg-gray-100 rounded-lg"></div>
            <div className="h-64 bg-gray-100 rounded-lg"></div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-8 text-center">
        <div className="text-red-500 text-xl mb-4">⚠️ {error}</div>
        <button
          onClick={loadReports}
          className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600"
        >
          Try Again
        </button>
      </div>
    )
  }

  if (!data) return null

  const conversionStats = data.conversion_stats || { total_leads: 0, converted: 0, lost: 0, active: 0, conversion_rate: 0, loss_rate: 0 }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">📊 Fleet Lead Reports</h1>
          <p className="text-gray-500">Track your fleet prospecting performance</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setDateRange(7)}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded hover:bg-gray-50"
          >
            7 days
          </button>
          <button
            onClick={() => setDateRange(30)}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded hover:bg-gray-50"
          >
            30 days
          </button>
          <button
            onClick={() => setDateRange(90)}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded hover:bg-gray-50"
          >
            90 days
          </button>
          <button
            onClick={() => { setStartDate(''); setEndDate('') }}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded hover:bg-gray-50"
          >
            All time
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
          <div className="text-gray-500 text-sm mb-1">Total Leads</div>
          <div className="text-3xl font-bold text-gray-800">
            {conversionStats.total_leads.toLocaleString()}
          </div>
          <div className="text-xs text-gray-400 mt-1">
            from fleet discovery
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
          <div className="text-gray-500 text-sm mb-1">Converted</div>
          <div className="text-3xl font-bold text-green-600">
            {conversionStats.converted}
          </div>
          <div className="text-xs text-gray-400 mt-1">
            successful deals
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
          <div className="text-gray-500 text-sm mb-1">Active</div>
          <div className="text-3xl font-bold text-blue-600">
            {conversionStats.active}
          </div>
          <div className="text-xs text-gray-400 mt-1">
            in progress
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
          <div className="text-gray-500 text-sm mb-1">Conversion Rate</div>
          <div className="text-3xl font-bold text-purple-600">
            {formatPercent(conversionStats.conversion_rate)}
          </div>
          <div className="text-xs text-gray-400 mt-1">
            lead → converted
          </div>
        </div>
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-2 gap-6 mb-6">
        {/* Sales Funnel */}
        <div className="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
          <h2 className="font-bold text-lg mb-4">Sales Funnel</h2>
          {data.funnel && data.funnel.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={data.funnel} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" />
                <YAxis type="category" dataKey="status" width={100} />
                <Tooltip
                  formatter={(value: number) => [value.toLocaleString(), 'Leads']}
                />
                <Bar
                  dataKey="count"
                  fill="#3b82f6"
                  radius={[0, 4, 4, 0]}
                >
                  {data.funnel.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={STATUS_COLORS[entry.status] || COLORS[index % COLORS.length]}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="text-center text-gray-400 py-8">No funnel data available</div>
          )}
        </div>

        {/* By Temperature */}
        <div className="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
          <h2 className="font-bold text-lg mb-4">By Temperature</h2>
          {data.by_temperature && data.by_temperature.length > 0 ? (
            <div className="space-y-6">
              {data.by_temperature.map((item, i) => {
                const colors: Record<string, { bg: string; text: string }> = {
                  HOT: { bg: 'bg-red-500', text: 'text-red-600' },
                  WARM: { bg: 'bg-orange-500', text: 'text-orange-600' },
                  COLD: { bg: 'bg-blue-500', text: 'text-blue-600' },
                }
                const color = colors[item.temperature] || { bg: 'bg-gray-500', text: 'text-gray-600' }
                return (
                  <div key={i}>
                    <div className="flex justify-between text-sm mb-2">
                      <span className={`font-medium ${color.text}`}>
                        {item.temperature === 'HOT' ? '🔥' : item.temperature === 'WARM' ? '☀️' : '❄️'} {item.temperature}
                      </span>
                      <span>
                        {item.total} leads • {item.converted} converted ({formatPercent(item.conversion_rate)})
                      </span>
                    </div>
                    <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${color.bg} rounded-full transition-all duration-500`}
                        style={{ width: `${Math.min((item.converted / Math.max(item.total, 1)) * 100, 100)}%` }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="text-center text-gray-400 py-8">No temperature data available</div>
          )}
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-2 gap-6 mb-6">
        {/* Hail vs Non-Hail */}
        <div className="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
          <h2 className="font-bold text-lg mb-4">🌨️ Hail vs Non-Hail Performance</h2>
          {data.hail_comparison && data.hail_comparison.length > 0 ? (
            <div className="flex items-center">
              <ResponsiveContainer width="50%" height={200}>
                <PieChart>
                  <Pie
                    data={data.hail_comparison}
                    dataKey="total"
                    nameKey="category"
                    cx="50%"
                    cy="50%"
                    outerRadius={70}
                    label={({ name, percent }) => `${(percent * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {data.hail_comparison.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={entry.category === 'Hail Affected' ? '#ef4444' : '#3b82f6'}
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex-1 space-y-3">
                {data.hail_comparison.map((item, i) => (
                  <div key={i} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                    <div className="flex items-center gap-2">
                      <div className={`w-3 h-3 rounded-full ${item.category === 'Hail Affected' ? 'bg-red-500' : 'bg-blue-500'}`}></div>
                      <span className="text-sm">{item.category}</span>
                    </div>
                    <div className="text-right">
                      <div className="font-bold">{item.total} leads</div>
                      <div className="text-xs text-gray-500">
                        {item.converted} converted • {formatPercent(item.conversion_rate)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-center text-gray-400 py-8">No data available</div>
          )}
        </div>

        {/* Weekly Trend */}
        <div className="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
          <h2 className="font-bold text-lg mb-4">📈 Weekly Trend</h2>
          {data.weekly_trends && data.weekly_trends.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={data.weekly_trends}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="week"
                  tick={{ fontSize: 10 }}
                  tickFormatter={(val) => val.split('-')[1] ? `W${val.split('-')[1]}` : val}
                />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="new_leads"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  name="New Leads"
                />
                <Line
                  type="monotone"
                  dataKey="converted"
                  stroke="#22c55e"
                  strokeWidth={2}
                  name="Converted"
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="text-center text-gray-400 py-8">No trend data available</div>
          )}
        </div>
      </div>

      {/* Tables Row */}
      <div className="grid grid-cols-2 gap-6 mb-6">
        {/* By City */}
        <div className="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
          <h2 className="font-bold text-lg mb-4">📍 By City</h2>
          {data.by_city && data.by_city.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b">
                    <th className="pb-2">City</th>
                    <th className="pb-2 text-right">Leads</th>
                    <th className="pb-2 text-right">Converted</th>
                    <th className="pb-2 text-right">Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {data.by_city.slice(0, 8).map((city, i) => (
                    <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                      <td className="py-2">{city.city}, {city.state}</td>
                      <td className="py-2 text-right">{city.total_leads}</td>
                      <td className="py-2 text-right text-green-600">{city.converted}</td>
                      <td className="py-2 text-right font-medium">
                        {formatPercent(city.conversion_rate)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center text-gray-400 py-8">No city data available</div>
          )}
        </div>

        {/* Lost Reasons */}
        <div className="bg-white rounded-xl shadow-sm p-5 border border-gray-100">
          <h2 className="font-bold text-lg mb-4">❌ Lost Reasons</h2>
          {data.lost_reasons && data.lost_reasons.length > 0 ? (
            <div className="space-y-3">
              {data.lost_reasons.map((item, i) => (
                <div key={i} className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">{item.reason}</span>
                  <span className="font-bold text-red-600">{item.count}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center text-gray-400 py-8">No lost leads yet! 🎉</div>
          )}
        </div>
      </div>

      {/* Top Deals */}
      <div className="bg-white rounded-xl shadow-sm p-5 border border-gray-100 mb-6">
        <h2 className="font-bold text-lg mb-4">🏆 Recent Conversions</h2>
        {data.top_deals && data.top_deals.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b">
                  <th className="pb-2">Company</th>
                  <th className="pb-2">Location</th>
                  <th className="pb-2">Temperature</th>
                  <th className="pb-2 text-right">Created</th>
                  <th className="pb-2 text-right">Converted</th>
                </tr>
              </thead>
              <tbody>
                {data.top_deals.map((deal, i) => (
                  <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-3 font-medium">{deal.company_name}</td>
                    <td className="py-3 text-gray-600">{deal.city}, {deal.state}</td>
                    <td className="py-3">
                      <span className={`px-2 py-1 rounded text-xs ${
                        deal.temperature === 'HOT' ? 'bg-red-100 text-red-700' :
                        deal.temperature === 'WARM' ? 'bg-orange-100 text-orange-700' :
                        'bg-blue-100 text-blue-700'
                      }`}>
                        {deal.temperature}
                      </span>
                    </td>
                    <td className="py-3 text-right text-gray-500">
                      {new Date(deal.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 text-right text-green-600 font-medium">
                      {new Date(deal.converted_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center text-gray-400 py-8">
            No converted deals yet. Keep prospecting! 💪
          </div>
        )}
      </div>

      {/* Response Time Stats */}
      {data.response_time && (
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl p-5 border border-blue-100">
          <h2 className="font-bold text-lg mb-4">⏱️ Response Time Metrics</h2>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {data.response_time.avg_days} days
              </div>
              <div className="text-sm text-gray-600">Avg Time to Contact</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {data.response_time.min_days} days
              </div>
              <div className="text-sm text-gray-600">Fastest Response</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">
                {data.response_time.max_days} days
              </div>
              <div className="text-sm text-gray-600">Slowest Response</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

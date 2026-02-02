import { useEffect, useState } from 'react';
import adminApi from '../api/adminApi';

interface UsageData {
  month: Record<string, { used: number; limit: number | null; percent: number }>;
  today: Record<string, number>;
  history: Record<string, Record<string, number>>;
}

const apiColors: Record<string, string> = {
  osm: '#4ade80',
  yelp: '#f87171',
  here: '#60a5fa',
  tomtom: '#c084fc',
  google: '#fbbf24',
  foursquare: '#34d399'
};

export default function ApiUsage() {
  const [data, setData] = useState<UsageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadUsage();
  }, []);

  const loadUsage = async () => {
    try {
      const result = await adminApi.getApiUsage();
      setData(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load usage');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-gray-400">Loading...</div>;
  }

  if (error || !data) {
    return <div className="text-red-400 p-4 bg-red-500/10 rounded">{error || 'Failed to load usage data'}</div>;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">API Usage</h1>

      {/* Monthly Usage Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {Object.entries(data.month).map(([api, usage]) => (
          <div key={api} className="bg-gray-800 rounded-lg p-4">
            <div className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: apiColors[api] || '#888' }}
              />
              <span className="text-gray-300 font-medium capitalize">{api}</span>
            </div>

            <div className="text-3xl font-bold text-white mt-2">
              {usage.used.toLocaleString()}
            </div>

            {usage.limit ? (
              <>
                <div className="text-sm text-gray-400">
                  of {usage.limit.toLocaleString()} ({usage.percent.toFixed(1)}%)
                </div>
                <div className="mt-2 h-2 bg-gray-700 rounded overflow-hidden">
                  <div
                    className="h-full rounded"
                    style={{
                      width: `${Math.min(usage.percent, 100)}%`,
                      backgroundColor: usage.percent > 80 ? '#ef4444' : usage.percent > 50 ? '#eab308' : '#22c55e'
                    }}
                  />
                </div>
              </>
            ) : (
              <div className="text-sm text-gray-400">Unlimited</div>
            )}
          </div>
        ))}
      </div>

      {/* Today's Usage */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Today's Usage</h2>
        {Object.keys(data.today).length === 0 ? (
          <p className="text-gray-400">No API calls today</p>
        ) : (
          <div className="flex flex-wrap gap-6">
            {Object.entries(data.today).map(([api, count]) => (
              <div key={api} className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: apiColors[api] || '#888' }}
                />
                <span className="text-gray-300 capitalize">{api}:</span>
                <span className="text-white font-semibold">{count.toLocaleString()}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Usage History */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-white mb-4">30-Day History</h2>
        {Object.keys(data.history).length === 0 ? (
          <p className="text-gray-400">No usage history available</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400">
                  <th className="text-left py-2 px-2">Date</th>
                  {Object.keys(apiColors).map(api => (
                    <th key={api} className="text-right py-2 px-2 capitalize">{api}</th>
                  ))}
                  <th className="text-right py-2 px-2">Total</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(data.history)
                  .sort(([a], [b]) => b.localeCompare(a))
                  .slice(0, 30)
                  .map(([date, apis]) => {
                    const total = Object.values(apis).reduce((sum, n) => sum + n, 0);
                    return (
                      <tr key={date} className="border-t border-gray-700">
                        <td className="py-2 px-2 text-gray-300">{date}</td>
                        {Object.keys(apiColors).map(api => (
                          <td key={api} className="text-right py-2 px-2 text-gray-400">
                            {apis[api] || 0}
                          </td>
                        ))}
                        <td className="text-right py-2 px-2 text-white font-semibold">{total}</td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* API Limits Info */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-white mb-4">API Limits</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">Yelp</span>
            <span className="text-white">150,000/month (5,000/day)</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">HERE</span>
            <span className="text-white">250,000/month</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">TomTom</span>
            <span className="text-white">75,000/month (2,500/day)</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Google</span>
            <span className="text-white">10,000/month ($200 credit)</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Foursquare</span>
            <span className="text-white">100,000/month</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">OSM/Overpass</span>
            <span className="text-green-400">Unlimited</span>
          </div>
        </div>
      </div>
    </div>
  );
}

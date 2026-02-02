import { useState, useEffect } from 'react';
import { useApi, Storm, PaginatedResponse } from '../../../hooks/useApi';

export default function Storms() {
  const api = useApi();
  const [storms, setStorms] = useState<Storm[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [stateFilter, setStateFilter] = useState('');

  useEffect(() => {
    loadStorms();
  }, [page, stateFilter]);

  const loadStorms = async () => {
    setLoading(true);
    try {
      const data = await api.get<PaginatedResponse<Storm>>('/storms', {
        page,
        per_page: 20,
        state: stateFilter || undefined,
      });
      setStorms(data.items);
      setTotalPages(data.pages);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load storms');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const statusColors: Record<string, string> = {
    processed: 'bg-green-500/20 text-green-400',
    processing: 'bg-yellow-500/20 text-yellow-400',
    pending: 'bg-gray-500/20 text-gray-400',
    failed: 'bg-red-500/20 text-red-400',
  };

  const usStates = [
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
  ];

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Storms</h1>
          <p className="text-gray-400">Browse recent hail storms and find leads</p>
        </div>

        <select
          value={stateFilter}
          onChange={(e) => {
            setStateFilter(e.target.value);
            setPage(1);
          }}
          className="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
        >
          <option value="">All States</option>
          {usStates.map((state) => (
            <option key={state} value={state}>{state}</option>
          ))}
        </select>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/50 text-red-400 px-4 py-3 rounded mb-6">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <>
          <div className="bg-gray-800 rounded-lg overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-700">
                  <th className="text-left px-6 py-3 text-sm font-medium text-gray-300">Storm</th>
                  <th className="text-left px-6 py-3 text-sm font-medium text-gray-300">Location</th>
                  <th className="text-left px-6 py-3 text-sm font-medium text-gray-300">Date</th>
                  <th className="text-left px-6 py-3 text-sm font-medium text-gray-300">Hail Size</th>
                  <th className="text-left px-6 py-3 text-sm font-medium text-gray-300">Businesses</th>
                  <th className="text-left px-6 py-3 text-sm font-medium text-gray-300">Status</th>
                  <th className="text-right px-6 py-3 text-sm font-medium text-gray-300">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {storms.map((storm) => (
                  <tr key={storm.id} className="hover:bg-gray-750">
                    <td className="px-6 py-4">
                      <span className="text-white font-medium">{storm.name}</span>
                    </td>
                    <td className="px-6 py-4 text-gray-300">
                      {storm.city}, {storm.state}
                    </td>
                    <td className="px-6 py-4 text-gray-300">{formatDate(storm.event_date)}</td>
                    <td className="px-6 py-4 text-gray-300">{storm.hail_size}"</td>
                    <td className="px-6 py-4 text-gray-300">{storm.business_count}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded text-xs font-medium capitalize ${statusColors[storm.status] || 'bg-gray-500/20 text-gray-400'}`}>
                        {storm.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      {storm.status === 'processed' && storm.business_count > 0 ? (
                        <a
                          href={`/app/storms/${storm.id}/businesses`}
                          className="text-purple-400 hover:text-purple-300 text-sm"
                        >
                          View Businesses
                        </a>
                      ) : (
                        <span className="text-gray-500 text-sm">
                          {storm.status === 'processing' ? 'Processing...' : 'No data'}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
                {storms.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-6 py-8 text-center text-gray-400">
                      No storms found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-center gap-2 mt-6">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 text-white rounded transition"
              >
                Previous
              </button>
              <span className="px-4 py-2 text-gray-400">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page === totalPages}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-600 text-white rounded transition"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

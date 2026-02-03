import { useState, useEffect } from 'react';
import { useAuth } from '../../../contexts/auth-context';
import { useApi, Lead, PaginatedResponse } from '../../../hooks/useApi';

export default function Leads() {
  const { canViewAllLeads } = useAuth();
  const api = useApi();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');
  const [showMyLeads, setShowMyLeads] = useState(!canViewAllLeads);

  useEffect(() => {
    loadLeads();
  }, [page, statusFilter, showMyLeads]);

  const loadLeads = async () => {
    setLoading(true);
    try {
      const data = await api.get<PaginatedResponse<Lead>>('/leads', {
        page,
        per_page: 20,
        status: statusFilter || undefined,
        my_leads: showMyLeads,
      });
      setLeads(data.items);
      setTotalPages(data.pages);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load leads');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateStatus = async (id: number, status: string) => {
    try {
      await api.patch(`/leads/${id}`, { status });
      loadLeads();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update lead');
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
    new: 'bg-blue-500/20 text-blue-400',
    contacted: 'bg-yellow-500/20 text-yellow-400',
    qualified: 'bg-purple-500/20 text-purple-400',
    proposal: 'bg-orange-500/20 text-orange-400',
    won: 'bg-green-500/20 text-green-400',
    lost: 'bg-red-500/20 text-red-400',
  };

  const statuses = ['new', 'contacted', 'qualified', 'proposal', 'won', 'lost'];

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Leads</h1>
          <p className="text-gray-400">Manage your saved leads</p>
        </div>

        <div className="flex gap-3">
          {canViewAllLeads && (
            <label className="flex items-center gap-2 text-gray-300">
              <input
                type="checkbox"
                checked={showMyLeads}
                onChange={(e) => {
                  setShowMyLeads(e.target.checked);
                  setPage(1);
                }}
                className="rounded bg-gray-700 border-gray-600 text-purple-500 focus:ring-purple-500"
              />
              My Leads Only
            </label>
          )}

          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            <option value="">All Statuses</option>
            {statuses.map((status) => (
              <option key={status} value={status} className="capitalize">{status}</option>
            ))}
          </select>
        </div>
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
                  <th className="text-left px-6 py-3 text-sm font-medium text-gray-300">Business</th>
                  <th className="text-left px-6 py-3 text-sm font-medium text-gray-300">Location</th>
                  <th className="text-left px-6 py-3 text-sm font-medium text-gray-300">Category</th>
                  <th className="text-left px-6 py-3 text-sm font-medium text-gray-300">Phone</th>
                  <th className="text-left px-6 py-3 text-sm font-medium text-gray-300">Status</th>
                  <th className="text-left px-6 py-3 text-sm font-medium text-gray-300">Added</th>
                  <th className="text-right px-6 py-3 text-sm font-medium text-gray-300">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {leads.map((lead) => (
                  <tr key={lead.id} className="hover:bg-gray-750">
                    <td className="px-6 py-4">
                      <span className="text-white font-medium">{lead.business.name}</span>
                    </td>
                    <td className="px-6 py-4 text-gray-300">
                      {lead.business.city}, {lead.business.state}
                    </td>
                    <td className="px-6 py-4 text-gray-300">{lead.business.category}</td>
                    <td className="px-6 py-4">
                      <a
                        href={`tel:${lead.business.phone}`}
                        className="text-purple-400 hover:text-purple-300"
                      >
                        {lead.business.phone}
                      </a>
                    </td>
                    <td className="px-6 py-4">
                      <select
                        value={lead.status}
                        onChange={(e) => handleUpdateStatus(lead.id, e.target.value)}
                        className={`px-2 py-1 rounded text-xs font-medium capitalize bg-transparent border-0 cursor-pointer ${statusColors[lead.status] || 'text-gray-400'}`}
                      >
                        {statuses.map((status) => (
                          <option key={status} value={status} className="bg-gray-800 text-white">
                            {status}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-6 py-4 text-gray-300">{formatDate(lead.created_at)}</td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => {
                          const note = prompt('Add a note:');
                          if (note) {
                            api.patch(`/leads/${lead.id}`, { notes: note }).then(loadLeads);
                          }
                        }}
                        className="text-gray-400 hover:text-white text-sm"
                      >
                        Add Note
                      </button>
                    </td>
                  </tr>
                ))}
                {leads.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-6 py-8 text-center text-gray-400">
                      No leads found. Browse storms to add businesses as leads.
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

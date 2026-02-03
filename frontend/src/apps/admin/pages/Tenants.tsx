import { useEffect, useState } from 'react';
import adminApi from '../api/adminApi';

interface Tenant {
  id: number;
  company_name: string;
  slug: string;
  owner_email: string;
  plan: string;
  status: string;
  max_users: number;
  user_count: number;
  created_at: string;
}

interface CreateTenantForm {
  company_name: string;
  owner_email: string;
  plan: string;
  max_users: number;
}

export default function Tenants() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<CreateTenantForm>({
    company_name: '',
    owner_email: '',
    plan: 'free',
    max_users: 2,
  });

  useEffect(() => {
    loadTenants();
  }, []);

  const loadTenants = async () => {
    try {
      const result = await adminApi.getTenants();
      setTenants(result.tenants || []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load tenants');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      await adminApi.createTenant(form);
      setShowCreate(false);
      setForm({ company_name: '', owner_email: '', plan: 'free', max_users: 2 });
      loadTenants();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create tenant');
    } finally {
      setCreating(false);
    }
  };

  const handleUpdateStatus = async (id: number, status: string) => {
    try {
      await adminApi.updateTenant(id, { status });
      loadTenants();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to update tenant');
    }
  };

  const handleUpdatePlan = async (id: number, plan: string) => {
    try {
      await adminApi.updateTenant(id, { plan });
      loadTenants();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to update tenant');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Tenant Management</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded transition"
        >
          + New Tenant
        </button>
      </div>

      {error && (
        <div className="text-red-400 p-4 bg-red-500/10 rounded">{error}</div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 w-full max-w-md">
            <h2 className="text-lg font-semibold text-white mb-4">Create New Tenant</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-gray-400 text-sm mb-1">Company Name</label>
                <input
                  type="text"
                  value={form.company_name}
                  onChange={(e) => setForm({ ...form, company_name: e.target.value })}
                  className="w-full bg-gray-700 text-white rounded px-3 py-2"
                  required
                />
              </div>
              <div>
                <label className="block text-gray-400 text-sm mb-1">Owner Email</label>
                <input
                  type="email"
                  value={form.owner_email}
                  onChange={(e) => setForm({ ...form, owner_email: e.target.value })}
                  className="w-full bg-gray-700 text-white rounded px-3 py-2"
                  required
                />
              </div>
              <div>
                <label className="block text-gray-400 text-sm mb-1">Plan</label>
                <select
                  value={form.plan}
                  onChange={(e) => setForm({ ...form, plan: e.target.value })}
                  className="w-full bg-gray-700 text-white rounded px-3 py-2"
                >
                  <option value="free">Free (2 users, 3 storms/mo)</option>
                  <option value="pro">Pro (8 users, 50 storms/mo) - $99/mo</option>
                  <option value="enterprise">Enterprise (100 users, unlimited) - $299/mo</option>
                </select>
              </div>
              <div>
                <label className="block text-gray-400 text-sm mb-1">Max Users</label>
                <input
                  type="number"
                  value={form.max_users}
                  onChange={(e) => setForm({ ...form, max_users: parseInt(e.target.value) })}
                  className="w-full bg-gray-700 text-white rounded px-3 py-2"
                  min={1}
                />
              </div>
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreate(false)}
                  className="flex-1 bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="flex-1 bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded transition disabled:opacity-50"
                >
                  {creating ? 'Creating...' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Tenants Table */}
      <div className="bg-gray-800 rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-700">
            <tr>
              <th className="px-4 py-3 text-left text-gray-300 font-medium">Company</th>
              <th className="px-4 py-3 text-left text-gray-300 font-medium">Owner</th>
              <th className="px-4 py-3 text-left text-gray-300 font-medium">Plan</th>
              <th className="px-4 py-3 text-left text-gray-300 font-medium">Users</th>
              <th className="px-4 py-3 text-left text-gray-300 font-medium">Status</th>
              <th className="px-4 py-3 text-left text-gray-300 font-medium">Created</th>
              <th className="px-4 py-3 text-left text-gray-300 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {tenants.map((tenant) => (
              <tr key={tenant.id} className="hover:bg-gray-700/50">
                <td className="px-4 py-3">
                  <div className="text-white font-medium">{tenant.company_name}</div>
                  <div className="text-gray-500 text-sm">{tenant.slug}</div>
                </td>
                <td className="px-4 py-3 text-gray-300">{tenant.owner_email}</td>
                <td className="px-4 py-3">
                  <select
                    value={tenant.plan}
                    onChange={(e) => handleUpdatePlan(tenant.id, e.target.value)}
                    className="bg-gray-700 text-white rounded px-2 py-1 text-sm"
                  >
                    <option value="free">Free</option>
                    <option value="pro">Pro</option>
                    <option value="enterprise">Enterprise</option>
                  </select>
                </td>
                <td className="px-4 py-3 text-gray-300">
                  {tenant.user_count} / {tenant.max_users}
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded text-xs ${
                    tenant.status === 'active' ? 'bg-green-500/20 text-green-400' :
                    tenant.status === 'suspended' ? 'bg-red-500/20 text-red-400' :
                    'bg-gray-500/20 text-gray-400'
                  }`}>
                    {tenant.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-400 text-sm">
                  {tenant.created_at ? new Date(tenant.created_at).toLocaleDateString() : '-'}
                </td>
                <td className="px-4 py-3">
                  {tenant.status === 'active' ? (
                    <button
                      onClick={() => handleUpdateStatus(tenant.id, 'suspended')}
                      className="text-red-400 hover:text-red-300 text-sm"
                    >
                      Suspend
                    </button>
                  ) : (
                    <button
                      onClick={() => handleUpdateStatus(tenant.id, 'active')}
                      className="text-green-400 hover:text-green-300 text-sm"
                    >
                      Activate
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {tenants.length === 0 && (
          <div className="p-8 text-center text-gray-400">
            No tenants found. Create your first tenant.
          </div>
        )}
      </div>
    </div>
  );
}

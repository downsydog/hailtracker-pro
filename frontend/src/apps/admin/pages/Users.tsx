import { useEffect, useState } from 'react';
import adminApi from '../api/adminApi';

interface User {
  id: number;
  tenant_id: number;
  tenant_name: string;
  email: string;
  name: string;
  phone: string;
  role: string;
  is_active: boolean;
  last_login: string | null;
  created_at: string;
}

interface Tenant {
  id: number;
  company_name: string;
}

interface CreateUserForm {
  email: string;
  password: string;
  name: string;
  tenant_id: number;
  role: string;
  phone: string;
}

export default function Users() {
  const [users, setUsers] = useState<User[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [filterTenant, setFilterTenant] = useState<number | null>(null);
  const [form, setForm] = useState<CreateUserForm>({
    email: '',
    password: '',
    name: '',
    tenant_id: 0,
    role: 'viewer',
    phone: '',
  });

  useEffect(() => {
    loadData();
  }, [filterTenant]);

  const loadData = async () => {
    try {
      const [usersResult, tenantsResult] = await Promise.all([
        adminApi.getUsers(filterTenant || undefined),
        adminApi.getTenants(),
      ]);
      setUsers(usersResult.users || []);
      setTenants(tenantsResult.tenants || []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.tenant_id) {
      setError('Please select a tenant');
      return;
    }
    setCreating(true);
    try {
      await adminApi.createUser(form);
      setShowCreate(false);
      setForm({ email: '', password: '', name: '', tenant_id: 0, role: 'viewer', phone: '' });
      loadData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create user');
    } finally {
      setCreating(false);
    }
  };

  const handleUpdateRole = async (id: number, role: string) => {
    try {
      await adminApi.updateUser(id, { role });
      loadData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to update user');
    }
  };

  const handleToggleActive = async (id: number, is_active: boolean) => {
    try {
      await adminApi.updateUser(id, { is_active: !is_active });
      loadData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to update user');
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
        <h1 className="text-2xl font-bold text-white">User Management</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded transition"
        >
          + New User
        </button>
      </div>

      {error && (
        <div className="text-red-400 p-4 bg-red-500/10 rounded flex items-center justify-between">
          {error}
          <button onClick={() => setError('')} className="text-red-300 hover:text-red-200">×</button>
        </div>
      )}

      {/* Filter */}
      <div className="flex items-center gap-4">
        <label className="text-gray-400">Filter by Tenant:</label>
        <select
          value={filterTenant || ''}
          onChange={(e) => setFilterTenant(e.target.value ? parseInt(e.target.value) : null)}
          className="bg-gray-700 text-white rounded px-3 py-2"
        >
          <option value="">All Tenants</option>
          {tenants.map((t) => (
            <option key={t.id} value={t.id}>{t.company_name}</option>
          ))}
        </select>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 w-full max-w-md">
            <h2 className="text-lg font-semibold text-white mb-4">Create New User</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-gray-400 text-sm mb-1">Name</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full bg-gray-700 text-white rounded px-3 py-2"
                  required
                />
              </div>
              <div>
                <label className="block text-gray-400 text-sm mb-1">Email</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  className="w-full bg-gray-700 text-white rounded px-3 py-2"
                  required
                />
              </div>
              <div>
                <label className="block text-gray-400 text-sm mb-1">Password</label>
                <input
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  className="w-full bg-gray-700 text-white rounded px-3 py-2"
                  required
                  minLength={6}
                />
              </div>
              <div>
                <label className="block text-gray-400 text-sm mb-1">Tenant</label>
                <select
                  value={form.tenant_id || ''}
                  onChange={(e) => setForm({ ...form, tenant_id: parseInt(e.target.value) })}
                  className="w-full bg-gray-700 text-white rounded px-3 py-2"
                  required
                >
                  <option value="">Select Tenant</option>
                  {tenants.map((t) => (
                    <option key={t.id} value={t.id}>{t.company_name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-gray-400 text-sm mb-1">Role</label>
                <select
                  value={form.role}
                  onChange={(e) => setForm({ ...form, role: e.target.value })}
                  className="w-full bg-gray-700 text-white rounded px-3 py-2"
                >
                  <option value="viewer">Viewer (read-only)</option>
                  <option value="technician">Technician (assigned jobs)</option>
                  <option value="manager">Manager (leads, jobs, estimates)</option>
                  <option value="owner">Owner (full tenant access)</option>
                  <option value="admin">Admin (system admin)</option>
                </select>
              </div>
              <div>
                <label className="block text-gray-400 text-sm mb-1">Phone (optional)</label>
                <input
                  type="tel"
                  value={form.phone}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })}
                  className="w-full bg-gray-700 text-white rounded px-3 py-2"
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

      {/* Users Table */}
      <div className="bg-gray-800 rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-700">
            <tr>
              <th className="px-4 py-3 text-left text-gray-300 font-medium">User</th>
              <th className="px-4 py-3 text-left text-gray-300 font-medium">Tenant</th>
              <th className="px-4 py-3 text-left text-gray-300 font-medium">Role</th>
              <th className="px-4 py-3 text-left text-gray-300 font-medium">Status</th>
              <th className="px-4 py-3 text-left text-gray-300 font-medium">Last Login</th>
              <th className="px-4 py-3 text-left text-gray-300 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {users.map((user) => (
              <tr key={user.id} className="hover:bg-gray-700/50">
                <td className="px-4 py-3">
                  <div className="text-white font-medium">{user.name}</div>
                  <div className="text-gray-500 text-sm">{user.email}</div>
                </td>
                <td className="px-4 py-3 text-gray-300">{user.tenant_name}</td>
                <td className="px-4 py-3">
                  <select
                    value={user.role}
                    onChange={(e) => handleUpdateRole(user.id, e.target.value)}
                    className="bg-gray-700 text-white rounded px-2 py-1 text-sm"
                  >
                    <option value="viewer">Viewer</option>
                    <option value="technician">Technician</option>
                    <option value="manager">Manager</option>
                    <option value="owner">Owner</option>
                    <option value="admin">Admin</option>
                  </select>
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded text-xs ${
                    user.is_active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                  }`}>
                    {user.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-400 text-sm">
                  {user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => handleToggleActive(user.id, user.is_active)}
                    className={`text-sm ${
                      user.is_active ? 'text-red-400 hover:text-red-300' : 'text-green-400 hover:text-green-300'
                    }`}
                  >
                    {user.is_active ? 'Deactivate' : 'Activate'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {users.length === 0 && (
          <div className="p-8 text-center text-gray-400">
            No users found.
          </div>
        )}
      </div>
    </div>
  );
}

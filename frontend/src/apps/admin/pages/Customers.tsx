import React, { useEffect, useState } from 'react';
import adminApi from '../api/adminApi';

interface Customer {
  id: number;
  company_name: string;
  slug: string;
  owner_email: string;
  plan: string;
  status: string;
  user_count: number;
  max_users: number;
  created_at: string;
}

export default function Customers() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newCustomer, setNewCustomer] = useState({
    company_name: '',
    owner_name: '',
    owner_email: '',
    password: '',
    plan: 'free'
  });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadCustomers();
  }, []);

  const loadCustomers = async () => {
    try {
      const result = await adminApi.getCustomers();
      setCustomers(result.customers);
    } catch (err) {
      console.error('Failed to load customers:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddCustomer = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);

    try {
      await adminApi.createCustomer(newCustomer);
      setShowAddModal(false);
      setNewCustomer({
        company_name: '',
        owner_name: '',
        owner_email: '',
        password: '',
        plan: 'free'
      });
      loadCustomers();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to create customer');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSuspend = async (id: number) => {
    if (!confirm('Suspend this customer? They will lose access.')) return;

    try {
      await adminApi.suspendCustomer(id);
      loadCustomers();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to suspend customer');
    }
  };

  const handleActivate = async (id: number) => {
    try {
      await adminApi.activateCustomer(id);
      loadCustomers();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to activate customer');
    }
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      active: 'bg-green-500/20 text-green-400',
      suspended: 'bg-red-500/20 text-red-400',
      cancelled: 'bg-gray-500/20 text-gray-400'
    };
    return colors[status] || 'bg-gray-500/20 text-gray-400';
  };

  const getPlanBadge = (plan: string) => {
    const colors: Record<string, string> = {
      free: 'bg-gray-500/20 text-gray-400',
      starter: 'bg-blue-500/20 text-blue-400',
      pro: 'bg-purple-500/20 text-purple-400',
      enterprise: 'bg-yellow-500/20 text-yellow-400'
    };
    return colors[plan] || 'bg-gray-500/20 text-gray-400';
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-white">Customer Management</h1>

        <button
          onClick={() => setShowAddModal(true)}
          className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded transition"
        >
          Add Customer
        </button>
      </div>

      {loading ? (
        <div className="text-gray-400">Loading customers...</div>
      ) : customers.length === 0 ? (
        <div className="text-gray-400 p-8 text-center bg-gray-800 rounded-lg">
          No customers found. Click "Add Customer" to create one.
        </div>
      ) : (
        <div className="bg-gray-800 rounded-lg overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-700">
              <tr>
                <th className="px-4 py-3 text-left text-gray-300">Company</th>
                <th className="px-4 py-3 text-left text-gray-300">Owner</th>
                <th className="px-4 py-3 text-left text-gray-300">Plan</th>
                <th className="px-4 py-3 text-left text-gray-300">Status</th>
                <th className="px-4 py-3 text-left text-gray-300">Users</th>
                <th className="px-4 py-3 text-left text-gray-300">Created</th>
                <th className="px-4 py-3 text-left text-gray-300">Actions</th>
              </tr>
            </thead>
            <tbody>
              {customers.map((customer) => (
                <tr key={customer.id} className="border-t border-gray-700 hover:bg-gray-750">
                  <td className="px-4 py-3">
                    <div className="text-white font-medium">{customer.company_name}</div>
                    <div className="text-gray-400 text-sm">{customer.slug}</div>
                  </td>
                  <td className="px-4 py-3 text-gray-300">{customer.owner_email}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-sm capitalize ${getPlanBadge(customer.plan)}`}>
                      {customer.plan}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-sm ${getStatusBadge(customer.status)}`}>
                      {customer.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-300">
                    {customer.user_count}/{customer.max_users}
                  </td>
                  <td className="px-4 py-3 text-gray-300">
                    {new Date(customer.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    {customer.status === 'active' ? (
                      <button
                        onClick={() => handleSuspend(customer.id)}
                        className="text-red-400 hover:text-red-300"
                      >
                        Suspend
                      </button>
                    ) : (
                      <button
                        onClick={() => handleActivate(customer.id)}
                        className="text-green-400 hover:text-green-300"
                      >
                        Activate
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Add Customer Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold text-white mb-4">Add Customer</h2>

            <form onSubmit={handleAddCustomer}>
              <div className="space-y-4">
                <div>
                  <label className="block text-gray-300 mb-1">Company Name</label>
                  <input
                    type="text"
                    value={newCustomer.company_name}
                    onChange={(e) => setNewCustomer(prev => ({ ...prev, company_name: e.target.value }))}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                    required
                  />
                </div>

                <div>
                  <label className="block text-gray-300 mb-1">Owner Name</label>
                  <input
                    type="text"
                    value={newCustomer.owner_name}
                    onChange={(e) => setNewCustomer(prev => ({ ...prev, owner_name: e.target.value }))}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                    required
                  />
                </div>

                <div>
                  <label className="block text-gray-300 mb-1">Owner Email</label>
                  <input
                    type="email"
                    value={newCustomer.owner_email}
                    onChange={(e) => setNewCustomer(prev => ({ ...prev, owner_email: e.target.value }))}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                    required
                  />
                </div>

                <div>
                  <label className="block text-gray-300 mb-1">Temporary Password</label>
                  <input
                    type="text"
                    value={newCustomer.password}
                    onChange={(e) => setNewCustomer(prev => ({ ...prev, password: e.target.value }))}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                    required
                    minLength={8}
                  />
                  <p className="text-gray-500 text-sm mt-1">Min 8 characters</p>
                </div>

                <div>
                  <label className="block text-gray-300 mb-1">Plan</label>
                  <select
                    value={newCustomer.plan}
                    onChange={(e) => setNewCustomer(prev => ({ ...prev, plan: e.target.value }))}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                  >
                    <option value="free">Free</option>
                    <option value="starter">Starter</option>
                    <option value="pro">Pro</option>
                    <option value="enterprise">Enterprise</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-4 mt-6">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded transition"
                  disabled={submitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded transition disabled:opacity-50"
                  disabled={submitting}
                >
                  {submitting ? 'Creating...' : 'Create Customer'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

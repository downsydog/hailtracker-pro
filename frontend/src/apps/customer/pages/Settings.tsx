import React, { useState } from 'react';
import { useAuth } from '../../../contexts/auth-context';
import { useApi } from '../../../hooks/useApi';

export default function Settings() {
  const { tenant, canManageSettings, refreshUser } = useAuth();
  const api = useApi();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [companyName, setCompanyName] = useState(tenant?.name || '');

  const handleSaveCompany = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      await api.patch('/settings/company', { name: companyName });
      await refreshUser?.();
      setSuccess('Company settings updated');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update settings');
    } finally {
      setLoading(false);
    }
  };

  if (!canManageSettings) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold text-white mb-2">Access Denied</h2>
        <p className="text-gray-400">Only account owners can manage settings.</p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-white mb-6">Settings</h1>

      {error && (
        <div className="bg-red-500/10 border border-red-500/50 text-red-400 px-4 py-3 rounded mb-6">
          {error}
        </div>
      )}

      {success && (
        <div className="bg-green-500/10 border border-green-500/50 text-green-400 px-4 py-3 rounded mb-6">
          {success}
        </div>
      )}

      {/* Company Settings */}
      <div className="bg-gray-800 rounded-lg p-6 mb-6">
        <h2 className="text-lg font-semibold text-white mb-4">Company Information</h2>

        <form onSubmit={handleSaveCompany} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Company Name</label>
            <input
              type="text"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              required
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-800 text-white rounded transition"
          >
            {loading ? 'Saving...' : 'Save Changes'}
          </button>
        </form>
      </div>

      {/* Plan Info */}
      <div className="bg-gray-800 rounded-lg p-6 mb-6">
        <h2 className="text-lg font-semibold text-white mb-4">Your Plan</h2>

        <div className="space-y-3">
          <div className="flex justify-between">
            <span className="text-gray-400">Current Plan</span>
            <span className="text-white capitalize font-medium">{tenant?.plan || 'Free'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Monthly API Limit</span>
            <span className="text-white">{tenant?.api_limit?.toLocaleString() || '1,000'} calls</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">API Calls Used</span>
            <span className="text-white">{tenant?.api_used?.toLocaleString() || '0'} calls</span>
          </div>
        </div>

        <div className="mt-6 pt-4 border-t border-gray-700">
          <p className="text-gray-400 text-sm mb-3">
            Need more API calls or features? Contact us to upgrade your plan.
          </p>
          <a
            href="mailto:support@hailtrackerpro.com?subject=Plan Upgrade"
            className="inline-block px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded transition"
          >
            Contact Sales
          </a>
        </div>
      </div>

      {/* API Key */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-white mb-4">API Access</h2>

        <p className="text-gray-400 mb-4">
          Use your API key to access the HailTracker Pro API programmatically.
        </p>

        <div className="bg-gray-900 p-3 rounded font-mono text-sm text-gray-300 mb-4">
          Bearer Token: Use the JWT token from login
        </div>

        <div className="text-sm text-gray-400">
          <p className="mb-2">API Base URL: <code className="text-purple-400">/api</code></p>
          <p>See our API documentation for available endpoints.</p>
        </div>
      </div>
    </div>
  );
}

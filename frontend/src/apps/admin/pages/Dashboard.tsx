import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import adminApi from '../api/adminApi';

interface DashboardData {
  tenant: {
    company_name: string;
    plan: string;
    status: string;
  };
  users: {
    active: number;
    max_allowed: number;
  };
  storms: {
    pending: number;
    processing: number;
    ready: number;
  };
  api_usage: Record<string, {
    used: number;
    limit: number | null;
    percent: number;
  }>;
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const result = await adminApi.getDashboard();
      setData(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading...</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="text-red-400 p-4 bg-red-500/10 rounded">{error || 'Failed to load dashboard'}</div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Dashboard</h1>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Pending Storms */}
        <div className="bg-gray-800 rounded-lg p-6">
          <div className="text-gray-400 text-sm">Pending Storms</div>
          <div className="text-3xl font-bold text-yellow-400 mt-2">
            {data.storms.pending}
          </div>
          <Link to="/admin/storms?status=pending" className="text-sm text-purple-400 hover:underline">
            View pending →
          </Link>
        </div>

        {/* Processing Storms */}
        <div className="bg-gray-800 rounded-lg p-6">
          <div className="text-gray-400 text-sm">Processing</div>
          <div className="text-3xl font-bold text-blue-400 mt-2">
            {data.storms.processing}
          </div>
          <span className="text-sm text-gray-500">Currently running</span>
        </div>

        {/* Ready Storms */}
        <div className="bg-gray-800 rounded-lg p-6">
          <div className="text-gray-400 text-sm">Ready Storms</div>
          <div className="text-3xl font-bold text-green-400 mt-2">
            {data.storms.ready}
          </div>
          <Link to="/admin/storms?status=ready" className="text-sm text-purple-400 hover:underline">
            View ready →
          </Link>
        </div>

        {/* Active Users */}
        <div className="bg-gray-800 rounded-lg p-6">
          <div className="text-gray-400 text-sm">Team Members</div>
          <div className="text-3xl font-bold text-white mt-2">
            {data.users.active}/{data.users.max_allowed}
          </div>
          <span className="text-sm text-gray-500">Active users</span>
        </div>
      </div>

      {/* API Usage */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-white mb-4">API Usage This Month</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {Object.entries(data.api_usage).map(([api, usage]) => (
            <div key={api} className="bg-gray-700 rounded p-4">
              <div className="text-gray-300 font-medium capitalize">{api}</div>
              <div className="text-2xl font-bold text-white mt-1">
                {usage.used.toLocaleString()}
              </div>
              {usage.limit ? (
                <>
                  <div className="text-sm text-gray-400">
                    of {usage.limit.toLocaleString()}
                  </div>
                  <div className="mt-2 h-2 bg-gray-600 rounded">
                    <div
                      className={`h-full rounded ${
                        usage.percent > 80 ? 'bg-red-500' :
                        usage.percent > 50 ? 'bg-yellow-500' : 'bg-green-500'
                      }`}
                      style={{ width: `${Math.min(usage.percent, 100)}%` }}
                    />
                  </div>
                  <div className="text-xs text-gray-400 mt-1">
                    {usage.percent.toFixed(1)}% used
                  </div>
                </>
              ) : (
                <div className="text-sm text-gray-400">Unlimited</div>
              )}
            </div>
          ))}
        </div>
        <Link to="/admin/usage" className="text-sm text-purple-400 hover:underline mt-4 inline-block">
          View detailed usage →
        </Link>
      </div>

      {/* Quick Actions */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Quick Actions</h2>
        <div className="flex flex-wrap gap-4">
          <Link
            to="/admin/storms?status=pending"
            className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded transition"
          >
            Process Pending Storms
          </Link>
          <Link
            to="/admin/customers"
            className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded transition"
          >
            Manage Customers
          </Link>
          <Link
            to="/admin/usage"
            className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded transition"
          >
            View API Usage
          </Link>
        </div>
      </div>
    </div>
  );
}

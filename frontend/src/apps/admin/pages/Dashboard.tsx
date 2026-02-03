import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import adminApi from '../api/adminApi';

interface StatsData {
  tenants: {
    total: number;
    recent_signups: number;
    plan_distribution: Record<string, number>;
  };
  users: {
    total: number;
    active_last_7_days: number;
  };
  storms: number;
  leads: number;
  jobs: number;
  system_health: string;
}

export default function Dashboard() {
  const [data, setData] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const result = await adminApi.getStats();
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
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">System Dashboard</h1>
        <div className={`px-3 py-1 rounded-full text-sm ${
          data.system_health === 'ok' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
        }`}>
          {data.system_health === 'ok' ? '● System Healthy' : '● System Issues'}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Tenants */}
        <div className="bg-gray-800 rounded-lg p-6">
          <div className="text-gray-400 text-sm">Total Tenants</div>
          <div className="text-3xl font-bold text-purple-400 mt-2">
            {data.tenants.total}
          </div>
          <div className="text-sm text-gray-500 mt-1">
            {data.tenants.recent_signups} new this month
          </div>
          <Link to="/admin/tenants" className="text-sm text-purple-400 hover:underline">
            Manage tenants →
          </Link>
        </div>

        {/* Total Users */}
        <div className="bg-gray-800 rounded-lg p-6">
          <div className="text-gray-400 text-sm">Total Users</div>
          <div className="text-3xl font-bold text-blue-400 mt-2">
            {data.users.total}
          </div>
          <div className="text-sm text-gray-500 mt-1">
            {data.users.active_last_7_days} active last 7 days
          </div>
          <Link to="/admin/users" className="text-sm text-purple-400 hover:underline">
            Manage users →
          </Link>
        </div>

        {/* Total Storms */}
        <div className="bg-gray-800 rounded-lg p-6">
          <div className="text-gray-400 text-sm">Storms in Database</div>
          <div className="text-3xl font-bold text-yellow-400 mt-2">
            {data.storms.toLocaleString()}
          </div>
          <span className="text-sm text-gray-500">Shared storm data</span>
        </div>

        {/* Leads & Jobs */}
        <div className="bg-gray-800 rounded-lg p-6">
          <div className="text-gray-400 text-sm">Leads / Jobs</div>
          <div className="text-3xl font-bold text-green-400 mt-2">
            {data.leads} / {data.jobs}
          </div>
          <span className="text-sm text-gray-500">Total across tenants</span>
        </div>
      </div>

      {/* Plan Distribution */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Tenant Plans</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(data.tenants.plan_distribution).map(([plan, count]) => (
            <div key={plan} className="bg-gray-700 rounded p-4">
              <div className="text-gray-300 font-medium capitalize">{plan}</div>
              <div className="text-2xl font-bold text-white mt-1">{count}</div>
              <div className="text-sm text-gray-400">tenants</div>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Quick Actions</h2>
        <div className="flex flex-wrap gap-4">
          <Link
            to="/admin/tenants"
            className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded transition"
          >
            Manage Tenants
          </Link>
          <Link
            to="/admin/users"
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded transition"
          >
            Manage Users
          </Link>
          <Link
            to="/admin/usage"
            className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded transition"
          >
            View API Usage
          </Link>
          <Link
            to="/admin/storms"
            className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded transition"
          >
            Browse Storms
          </Link>
        </div>
      </div>
    </div>
  );
}

import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import adminApi from '../api/adminApi';

interface Storm {
  id: number;
  noaa_id: string;
  event_date: string;
  state: string;
  status: string;
  business_count: number;
  swath_count: number;
  processed_at: string | null;
  expires_at: string | null;
}

interface Task {
  storm_id: number;
  task_id: string;
  status: string;
  progress?: { status: string };
}

export default function Storms() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [storms, setStorms] = useState<Storm[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedStorms, setSelectedStorms] = useState<Set<number>>(new Set());
  const [activeTasks, setActiveTasks] = useState<Map<number, Task>>(new Map());
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || '');

  useEffect(() => {
    loadStorms();
  }, [statusFilter]);

  useEffect(() => {
    const interval = setInterval(() => {
      activeTasks.forEach((task, stormId) => {
        if (task.status !== 'SUCCESS' && task.status !== 'FAILURE') {
          checkTaskStatus(stormId, task.task_id);
        }
      });
    }, 3000);

    return () => clearInterval(interval);
  }, [activeTasks]);

  const loadStorms = async () => {
    setLoading(true);
    try {
      const result = await adminApi.getStorms(statusFilter || undefined);
      setStorms(result.storms);
    } catch (err) {
      console.error('Failed to load storms:', err);
    } finally {
      setLoading(false);
    }
  };

  const checkTaskStatus = async (stormId: number, taskId: string) => {
    try {
      const result = await adminApi.getTaskStatus(taskId);

      setActiveTasks(prev => {
        const updated = new Map(prev);
        updated.set(stormId, { ...result, storm_id: stormId });
        return updated;
      });

      if (result.ready) {
        loadStorms();
      }
    } catch (err) {
      console.error('Failed to check task status:', err);
    }
  };

  const handleProcess = async (stormId: number) => {
    try {
      const result = await adminApi.processStorm(stormId);

      setActiveTasks(prev => {
        const updated = new Map(prev);
        updated.set(stormId, {
          storm_id: stormId,
          task_id: result.task_id,
          status: 'PENDING'
        });
        return updated;
      });

      setStorms(prev => prev.map(s =>
        s.id === stormId ? { ...s, status: 'processing' } : s
      ));
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to process storm');
    }
  };

  const handleReprocess = async (stormId: number) => {
    if (!confirm('This will clear existing data and reprocess. Continue?')) return;

    try {
      const result = await adminApi.reprocessStorm(stormId);

      setActiveTasks(prev => {
        const updated = new Map(prev);
        updated.set(stormId, {
          storm_id: stormId,
          task_id: result.task_id,
          status: 'PENDING'
        });
        return updated;
      });

      loadStorms();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to reprocess storm');
    }
  };

  const handleBatchProcess = async () => {
    if (selectedStorms.size === 0) {
      alert('Select storms to process');
      return;
    }

    try {
      const result = await adminApi.processBatch(Array.from(selectedStorms));

      result.tasks.forEach((task: { storm_id: number; task_id: string }) => {
        setActiveTasks(prev => {
          const updated = new Map(prev);
          updated.set(task.storm_id, {
            storm_id: task.storm_id,
            task_id: task.task_id,
            status: 'PENDING'
          });
          return updated;
        });
      });

      setSelectedStorms(new Set());
      loadStorms();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to process batch');
    }
  };

  const toggleSelect = (stormId: number) => {
    setSelectedStorms(prev => {
      const updated = new Set(prev);
      if (updated.has(stormId)) {
        updated.delete(stormId);
      } else {
        updated.add(stormId);
      }
      return updated;
    });
  };

  const selectAllPending = () => {
    const pendingIds = storms
      .filter(s => s.status === 'pending')
      .map(s => s.id);
    setSelectedStorms(new Set(pendingIds));
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'bg-yellow-500/20 text-yellow-400',
      processing: 'bg-blue-500/20 text-blue-400',
      ready: 'bg-green-500/20 text-green-400',
      failed: 'bg-red-500/20 text-red-400',
      expired: 'bg-gray-500/20 text-gray-400'
    };
    return colors[status] || 'bg-gray-500/20 text-gray-400';
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center flex-wrap gap-4">
        <h1 className="text-2xl font-bold text-white">Storm Management</h1>

        <div className="flex gap-4 flex-wrap">
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setSearchParams(e.target.value ? { status: e.target.value } : {});
            }}
            className="bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
          >
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="processing">Processing</option>
            <option value="ready">Ready</option>
            <option value="failed">Failed</option>
            <option value="expired">Expired</option>
          </select>

          {selectedStorms.size > 0 && (
            <button
              onClick={handleBatchProcess}
              className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded transition"
            >
              Process Selected ({selectedStorms.size})
            </button>
          )}

          <button
            onClick={selectAllPending}
            className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded transition"
          >
            Select All Pending
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-gray-400">Loading storms...</div>
      ) : storms.length === 0 ? (
        <div className="text-gray-400 p-8 text-center bg-gray-800 rounded-lg">
          No storms found
        </div>
      ) : (
        <div className="bg-gray-800 rounded-lg overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-700">
              <tr>
                <th className="px-4 py-3 text-left text-gray-300 w-12">
                  <input
                    type="checkbox"
                    onChange={(e) => {
                      if (e.target.checked) {
                        selectAllPending();
                      } else {
                        setSelectedStorms(new Set());
                      }
                    }}
                    checked={selectedStorms.size > 0}
                    className="rounded"
                  />
                </th>
                <th className="px-4 py-3 text-left text-gray-300">Date</th>
                <th className="px-4 py-3 text-left text-gray-300">State</th>
                <th className="px-4 py-3 text-left text-gray-300">Status</th>
                <th className="px-4 py-3 text-left text-gray-300">Swaths</th>
                <th className="px-4 py-3 text-left text-gray-300">Businesses</th>
                <th className="px-4 py-3 text-left text-gray-300">Expires</th>
                <th className="px-4 py-3 text-left text-gray-300">Actions</th>
              </tr>
            </thead>
            <tbody>
              {storms.map((storm) => {
                const task = activeTasks.get(storm.id);

                return (
                  <tr key={storm.id} className="border-t border-gray-700 hover:bg-gray-750">
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedStorms.has(storm.id)}
                        onChange={() => toggleSelect(storm.id)}
                        disabled={storm.status === 'processing'}
                        className="rounded"
                      />
                    </td>
                    <td className="px-4 py-3 text-white">
                      {new Date(storm.event_date).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-white">{storm.state}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-sm ${getStatusBadge(storm.status)}`}>
                        {storm.status}
                      </span>
                      {task && task.status === 'PROGRESS' && task.progress && (
                        <span className="ml-2 text-sm text-blue-400">
                          {task.progress.status}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-300">{storm.swath_count}</td>
                    <td className="px-4 py-3 text-gray-300">
                      {storm.business_count.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-gray-300">
                      {storm.expires_at
                        ? new Date(storm.expires_at).toLocaleDateString()
                        : '-'}
                    </td>
                    <td className="px-4 py-3">
                      {storm.status === 'pending' && (
                        <button
                          onClick={() => handleProcess(storm.id)}
                          className="text-purple-400 hover:text-purple-300"
                        >
                          Process
                        </button>
                      )}
                      {storm.status === 'failed' && (
                        <button
                          onClick={() => handleProcess(storm.id)}
                          className="text-yellow-400 hover:text-yellow-300"
                        >
                          Retry
                        </button>
                      )}
                      {storm.status === 'ready' && (
                        <button
                          onClick={() => handleReprocess(storm.id)}
                          className="text-gray-400 hover:text-gray-300"
                        >
                          Reprocess
                        </button>
                      )}
                      {storm.status === 'expired' && (
                        <button
                          onClick={() => handleReprocess(storm.id)}
                          className="text-blue-400 hover:text-blue-300"
                        >
                          Rescan
                        </button>
                      )}
                      {storm.status === 'processing' && (
                        <span className="text-blue-400 animate-pulse">
                          Processing...
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

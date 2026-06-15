import { useState, useEffect } from 'react';
import { statsApi, pipelineApi } from '../services/api';
import { formatDistanceToNow } from 'date-fns';
import { vi } from 'date-fns/locale';

const STATE_COLORS: Record<string, { bg: string; text: string }> = {
  blue: { bg: 'bg-blue-100', text: 'text-blue-800' },
  indigo: { bg: 'bg-indigo-100', text: 'text-indigo-800' },
  purple: { bg: 'bg-purple-100', text: 'text-purple-800' },
  cyan: { bg: 'bg-cyan-100', text: 'text-cyan-800' },
  yellow: { bg: 'bg-yellow-100', text: 'text-yellow-800' },
  orange: { bg: 'bg-orange-100', text: 'text-orange-800' },
  green: { bg: 'bg-green-100', text: 'text-green-800' },
  emerald: { bg: 'bg-emerald-100', text: 'text-emerald-800' },
  red: { bg: 'bg-red-100', text: 'text-red-800' },
};

const STATES = [
  { key: 'SIGNAL_COLLECTED', label: 'Signal', color: 'blue' },
  { key: 'CATEGORIZED', label: 'Categorized', color: 'indigo' },
  { key: 'TRENDING', label: 'Trending', color: 'purple' },
  { key: 'RESEARCHED', label: 'Researched', color: 'cyan' },
  { key: 'WRITTEN', label: 'Written', color: 'yellow' },
  { key: 'GOVERNED', label: 'Governed', color: 'orange' },
  { key: 'APPROVED', label: 'Approved', color: 'green' },
  { key: 'PUBLISHED', label: 'Published', color: 'emerald' },
  { key: 'FAILED', label: 'Failed', color: 'red' },
];

export default function Overview() {
  const [stats, setStats] = useState<{
    today: { collected: number; written: number; published: number; failed: number };
    by_state: Record<string, number>;
    total: number;
  } | null>(null);
  const [queueStatus, setQueueStatus] = useState<{
    pending: number;
    oldest_queued_at?: string;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      setError(null);
      // Load stats first, then pipeline (not blocking)
      const statsData = await statsApi.get().catch(() => null);
      if (statsData) {
        setStats(statsData);
      }
      const queueData = await pipelineApi.status().catch(() => null);
      if (queueData) {
        setQueueStatus({
          pending: queueData.queue_size,
          oldest_queued_at: queueData.last_run_at,
        });
      }
      // If both failed, show error
      if (!statsData && !queueData) {
        throw new Error('Không thể tải dữ liệu từ server');
      }
    } catch (err) {
      console.error('Failed to load stats:', err);
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(`Không thể kết nối server: ${message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = () => {
    setLoading(true);
    loadData();
  };

  if (loading && !stats) {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin mb-4" />
        <div className="text-gray-500">Đang tải...</div>
      </div>
    );
  }

  if (error && !stats) {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <div className="text-red-600 mb-4">
            <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <p className="text-red-800 font-medium mb-2">Không thể kết nối</p>
          <p className="text-red-600 text-sm mb-4">{error}</p>
          <button
            onClick={handleRetry}
            className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 transition"
          >
            Thử lại
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Tổng quan</h1>

      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="Tín hiệu hôm nay"
          value={stats?.today.collected || 0}
          icon="📡"
        />
        <StatCard
          title="Đã viết hôm nay"
          value={stats?.today.written || 0}
          icon="✍️"
        />
        <StatCard
          title="Đã đăng hôm nay"
          value={stats?.today.published || 0}
          icon="🚀"
        />
        <StatCard
          title="Thất bại hôm nay"
          value={stats?.today.failed || 0}
          icon="❌"
        />
      </div>

      {/* Pipeline State Flow */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Luồng Pipeline</h2>
        <div className="flex items-center justify-between overflow-x-auto">
          {STATES.map((state, index) => (
            <div key={state.key} className="flex items-center">
              <div className="text-center">
                <div
                  className={`w-16 h-16 rounded-full flex items-center justify-center text-2xl font-bold ${STATE_COLORS[state.color].bg} ${STATE_COLORS[state.color].text}`}
                >
                  {stats?.by_state[state.key] || 0}
                </div>
                <div className="mt-2 text-xs text-gray-600">{state.label}</div>
              </div>
              {index < STATES.length - 1 && (
                <div className="w-8 h-0.5 bg-gray-300 mx-2" />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Queue Status */}
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Trạng thái Queue</h2>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Đang chờ xử lý</span>
              <span className="text-2xl font-bold text-primary-600">
                {queueStatus?.pending || 0}
              </span>
            </div>
            {queueStatus?.oldest_queued_at && (
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Cũ nhất trong queue</span>
                <span className="text-sm">
                  {formatDistanceToNow(new Date(queueStatus.oldest_queued_at), {
                    addSuffix: true,
                    locale: vi,
                  })}
                </span>
              </div>
            )}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Tổng số bài viết</h2>
          <div className="text-4xl font-bold text-gray-900">
            {stats?.total || 0}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon,
}: {
  title: string;
  value: number;
  icon: string;
}) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-600">{title}</p>
          <p className="text-3xl font-bold text-gray-900">{value}</p>
        </div>
        <span className="text-3xl">{icon}</span>
      </div>
    </div>
  );
}

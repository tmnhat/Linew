import { useState, useEffect } from 'react';
import { healthApi } from '../services/api';
import clsx from 'clsx';

interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  uptime_seconds: number;
  checks: {
    database: boolean;
    redis: boolean;
    wordpress: boolean;
  };
}

interface LogEntry {
  timestamp: string;
  level: 'INFO' | 'WARNING' | 'ERROR';
  source: string;
  message: string;
}

export default function Logs() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'INFO' | 'WARNING' | 'ERROR'>('all');
  const [autoRefresh, setAutoRefresh] = useState(true);

  const loadHealth = async () => {
    try {
      const data = await healthApi.get();
      setHealth(data);
    } catch (error) {
      console.error('Failed to load health:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadLogs = async () => {
    // In a real implementation, this would call an API endpoint
    // For now, we'll generate mock logs based on health status
    const mockLogs: LogEntry[] = [
      {
        timestamp: new Date(Date.now() - 5 * 60000).toISOString(),
        level: 'INFO',
        source: 'scheduler',
        message: 'RSS collection started for 12 sources',
      },
      {
        timestamp: new Date(Date.now() - 4 * 60000).toISOString(),
        level: 'INFO',
        source: 'pipeline',
        message: 'Pipeline run started: processed 5 articles',
      },
      {
        timestamp: new Date(Date.now() - 3 * 60000).toISOString(),
        level: 'INFO',
        source: 'publisher',
        message: 'Article published to WordPress: ID 1234',
      },
      {
        timestamp: new Date(Date.now() - 2 * 60000).toISOString(),
        level: 'WARNING',
        source: 'scraper',
        message: 'Rate limit reached for source: techcrunch.com',
      },
      {
        timestamp: new Date(Date.now() - 1 * 60000).toISOString(),
        level: 'ERROR',
        source: 'pipeline',
        message: 'Failed to categorize article: timeout after 30s',
      },
    ];
    setLogs(mockLogs);
  };

  useEffect(() => {
    loadHealth();
    loadLogs();
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      loadHealth();
    }, 30000);
    return () => clearInterval(interval);
  }, [autoRefresh]);

  const filteredLogs = filter === 'all'
    ? logs
    : logs.filter((log) => log.level === filter);

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const LEVEL_STYLES: Record<string, { bg: string; text: string; label: string }> = {
    INFO: { bg: 'bg-blue-100', text: 'text-blue-800', label: 'INFO' },
    WARNING: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'WARN' },
    ERROR: { bg: 'bg-red-100', text: 'text-red-800', label: 'ERROR' },
  };

  const STATUS_STYLES = {
    healthy: { bg: 'bg-green-100', text: 'text-green-800', label: 'Healthy' },
    degraded: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'Degraded' },
    unhealthy: { bg: 'bg-red-100', text: 'text-red-800', label: 'Unhealthy' },
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Nhật ký & Trạng thái</h1>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="w-4 h-4 text-primary-600 rounded"
            />
            <span>Auto refresh</span>
          </label>
          <button
            onClick={() => {
              loadHealth();
              loadLogs();
            }}
            className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg text-sm font-medium"
          >
            🔄 Làm mới
          </button>
        </div>
      </div>

      {/* Health Status */}
      {loading ? (
        <div className="flex items-center justify-center h-32">
          <div className="text-gray-500">Đang tải...</div>
        </div>
      ) : health ? (
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500 uppercase mb-2">
              Trạng thái hệ thống
            </h3>
            <div className="flex items-center gap-2">
              <span
                className={clsx(
                  'px-3 py-1 rounded-full text-sm font-medium',
                  STATUS_STYLES[health.status].bg,
                  STATUS_STYLES[health.status].text
                )}
              >
                {STATUS_STYLES[health.status].label}
              </span>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500 uppercase mb-2">Version</h3>
            <div className="text-2xl font-bold text-gray-900">{health.version}</div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500 uppercase mb-2">Uptime</h3>
            <div className="text-2xl font-bold text-gray-900">
              {formatUptime(health.uptime_seconds)}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500 uppercase mb-2">Services</h3>
            <div className="flex gap-2">
              <span
                className={clsx(
                  'w-3 h-3 rounded-full',
                  health.checks.database ? 'bg-green-500' : 'bg-red-500'
                )}
                title="Database"
              />
              <span
                className={clsx(
                  'w-3 h-3 rounded-full',
                  health.checks.redis ? 'bg-green-500' : 'bg-red-500'
                )}
                title="Redis"
              />
              <span
                className={clsx(
                  'w-3 h-3 rounded-full',
                  health.checks.wordpress ? 'bg-green-500' : 'bg-red-500'
                )}
                title="WordPress"
              />
            </div>
            <div className="flex gap-2 mt-1 text-xs text-gray-500">
              <span>DB</span>
              <span>Redis</span>
              <span>WP</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">Không thể kết nối đến API</p>
        </div>
      )}

      {/* Log Filters */}
      <div className="bg-white rounded-lg shadow">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-lg font-semibold">Nhật ký hệ thống</h2>
          <div className="flex gap-2">
            {(['all', 'INFO', 'WARNING', 'ERROR'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={clsx(
                  'px-3 py-1 text-sm rounded',
                  filter === f
                    ? 'bg-gray-800 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                )}
              >
                {f === 'all' ? 'Tất cả' : f}
              </button>
            ))}
          </div>
        </div>

        <div className="divide-y divide-gray-200 max-h-[500px] overflow-y-auto">
          {filteredLogs.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              Không có log nào
            </div>
          ) : (
            filteredLogs.map((log, index) => (
              <div key={index} className="px-6 py-3 flex items-start gap-4 hover:bg-gray-50">
                <div className="text-xs text-gray-400 whitespace-nowrap pt-1">
                  {new Date(log.timestamp).toLocaleTimeString('vi-VN')}
                </div>
                <span
                  className={clsx(
                    'px-2 py-0.5 rounded text-xs font-medium min-w-[60px] text-center',
                    LEVEL_STYLES[log.level].bg,
                    LEVEL_STYLES[log.level].text
                  )}
                >
                  {LEVEL_STYLES[log.level].label}
                </span>
                <span className="text-xs text-gray-500 min-w-[80px]">
                  {log.source}
                </span>
                <div className="text-sm text-gray-700 flex-1">{log.message}</div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 uppercase mb-2">
            Số log hôm nay
          </h3>
          <div className="text-4xl font-bold text-gray-900">
            {logs.length}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 uppercase mb-2">
            Warnings
          </h3>
          <div className="text-4xl font-bold text-yellow-600">
            {logs.filter((l) => l.level === 'WARNING').length}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500 uppercase mb-2">
            Errors
          </h3>
          <div className="text-4xl font-bold text-red-600">
            {logs.filter((l) => l.level === 'ERROR').length}
          </div>
        </div>
      </div>
    </div>
  );
}

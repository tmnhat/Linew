import { useState, useEffect } from 'react';
import { distributionApi, DistributionStats, DistributionLog } from '../services/api';
import { useToastStore } from '../store/toast';

const channelIcons: Record<string, string> = {
  telegram: '📱',
  facebook: '📘',
  twitter: '🐦',
  newsletter: '📧',
  medium: '📝',
};

const statusColors: Record<string, { bg: string; text: string }> = {
  success: { bg: 'bg-green-100', text: 'text-green-700' },
  failed: { bg: 'bg-red-100', text: 'text-red-700' },
  pending: { bg: 'bg-yellow-100', text: 'text-yellow-700' },
  skipped: { bg: 'bg-gray-100', text: 'text-gray-700' },
};

export default function DistributionPage() {
  const { addToast } = useToastStore();
  const [stats, setStats] = useState<DistributionStats | null>(null);
  const [logs, setLogs] = useState<DistributionLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string }>>({});

  const loadData = async () => {
    try {
      const [statsData, logsData] = await Promise.all([
        distributionApi.getStats(7),
        distributionApi.getLogs({ limit: 50 }),
      ]);
      setStats(statsData);
      setLogs(logsData.logs || []);
    } catch (error) {
      console.error('Failed to load distribution data:', error);
      addToast({
        type: 'error',
        title: 'Lỗi tải dữ liệu',
        message: String(error),
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleTestChannel = async (channel: string) => {
    setTesting(channel);
    setTestResults((prev) => ({ ...prev, [channel]: { success: false, message: 'Testing...' } }));

    try {
      let result;
      switch (channel) {
        case 'telegram':
          result = await distributionApi.testTelegram();
          break;
        case 'facebook':
          result = await distributionApi.testFacebook();
          break;
        case 'twitter':
          result = await distributionApi.testTwitter();
          break;
        case 'newsletter':
          result = await distributionApi.testNewsletter();
          break;
        default:
          throw new Error('Unknown channel');
      }

      setTestResults((prev) => ({
        ...prev,
        [channel]: {
          success: result.success,
          message: result.success
            ? result.bot_username || result.page_name || result.username || 'Connected!'
            : result.error || 'Connection failed',
        },
      }));

      addToast({
        type: result.success ? 'success' : 'error',
        title: `${channel.charAt(0).toUpperCase() + channel.slice(1)} Test`,
        message: result.success
          ? 'Kết nối thành công!'
          : result.error || 'Kết nối thất bại',
      });
    } catch (error) {
      setTestResults((prev) => ({
        ...prev,
        [channel]: {
          success: false,
          message: String(error),
        },
      }));
      addToast({
        type: 'error',
        title: 'Test Error',
        message: String(error),
      });
    } finally {
      setTesting(null);
    }
  };

  const getChannelStats = (channel: string) => {
    if (!stats?.stats?.[channel]) {
      return { total: 0, success: 0, failed: 0, pending: 0 };
    }
    return stats.stats[channel];
  };

  const calculateSuccessRate = (channel: string) => {
    const s = getChannelStats(channel);
    if (s.total === 0) return 0;
    return Math.round((s.success / s.total) * 100);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Đang tải...</div>
      </div>
    );
  }

  const channels = ['telegram', 'facebook', 'twitter', 'newsletter'];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Distribution</h1>
        <button
          onClick={loadData}
          className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg font-medium"
        >
          🔄 Refresh
        </button>
      </div>

      {/* Channel Cards */}
      <div className="grid grid-cols-4 gap-6">
        {channels.map((channel) => {
          const channelStats = getChannelStats(channel);
          const successRate = calculateSuccessRate(channel);
          const result = testResults[channel];

          return (
            <div key={channel} className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <span className="text-3xl">{channelIcons[channel]}</span>
                  <div>
                    <h3 className="font-semibold text-gray-900 capitalize">{channel}</h3>
                    <p className="text-sm text-gray-500">
                      {successRate}% success rate
                    </p>
                  </div>
                </div>
              </div>

              <div className="space-y-2 mb-4">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Total</span>
                  <span className="font-medium">{channelStats.total}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-green-500">Success</span>
                  <span className="font-medium text-green-600">{channelStats.success}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-red-500">Failed</span>
                  <span className="font-medium text-red-600">{channelStats.failed}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-yellow-500">Pending</span>
                  <span className="font-medium text-yellow-600">{channelStats.pending}</span>
                </div>
              </div>

              {/* Success Rate Bar */}
              <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
                <div
                  className="bg-green-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${successRate}%` }}
                />
              </div>

              {/* Test Button */}
              <button
                onClick={() => handleTestChannel(channel)}
                disabled={testing === channel}
                className="w-full py-2 px-4 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-300 text-white rounded-lg font-medium transition-colors"
              >
                {testing === channel ? '⏳ Testing...' : '🔗 Test Connection'}
              </button>

              {/* Test Result */}
              {result && (
                <div
                  className={`mt-3 p-3 rounded-lg text-sm ${
                    result.success
                      ? 'bg-green-50 text-green-700 border border-green-200'
                      : 'bg-red-50 text-red-700 border border-red-200'
                  }`}
                >
                  {result.success ? '✓' : '✗'} {result.message}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Summary Stats */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Tổng quan 7 ngày</h2>
        <div className="grid grid-cols-4 gap-6">
          <div className="text-center">
            <div className="text-3xl font-bold text-primary-600">
              {stats?.today_distributed || 0}
            </div>
            <div className="text-sm text-gray-500">Hôm nay</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-blue-600">
              {Object.values(stats?.stats || {}).reduce((sum, s) => sum + (s.total || 0), 0)}
            </div>
            <div className="text-sm text-gray-500">Tổng 7 ngày</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-green-600">
              {Object.values(stats?.stats || {}).reduce((sum, s) => sum + (s.success || 0), 0)}
            </div>
            <div className="text-sm text-gray-500">Thành công</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-red-600">
              {Object.values(stats?.stats || {}).reduce((sum, s) => sum + (s.failed || 0), 0)}
            </div>
            <div className="text-sm text-gray-500">Thất bại</div>
          </div>
        </div>
      </div>

      {/* Recent Logs */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b">
          <h2 className="text-lg font-semibold">Nhật ký Distribution gần đây</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Channel</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Article ID</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">URL</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Error</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                    Chưa có nhật ký distribution
                  </td>
                </tr>
              ) : (
                logs.map((log) => {
                  const statusStyle = statusColors[log.status] || statusColors.pending;
                  return (
                    <tr key={log.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(log.created_at).toLocaleString('vi-VN')}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="flex items-center gap-2">
                          <span>{channelIcons[log.channel] || '📤'}</span>
                          <span className="font-medium capitalize">{log.channel}</span>
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`px-2 py-1 rounded-full text-xs font-medium ${statusStyle.bg} ${statusStyle.text}`}
                        >
                          {log.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {log.article_id.substring(0, 8)}...
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {log.external_url ? (
                          <a
                            href={log.external_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary-600 hover:text-primary-700 hover:underline"
                          >
                            Link
                          </a>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-sm text-red-600 max-w-xs truncate">
                        {log.error || '-'}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

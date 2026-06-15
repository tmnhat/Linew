import { useState, useEffect } from 'react';
import { seoApi, SEOLinkStats } from '../services/api';
import { useToastStore } from '../store/toast';

export default function SEOPage() {
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState<any>(null);
  const [linkStats, setLinkStats] = useState<SEOLinkStats | null>(null);
  const [pingUrl, setPingUrl] = useState('');
  const [pingLoading, setPingLoading] = useState(false);
  const [refreshingLinks, setRefreshingLinks] = useState(false);
  const { addToast } = useToastStore();

  const loadData = async () => {
    setLoading(true);
    try {
      const [healthData, statsData] = await Promise.all([
        seoApi.health(),
        seoApi.getLinkStats(),
      ]);
      setHealth(healthData);
      setLinkStats(statsData);
    } catch (error) {
      console.error('Failed to load SEO data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handlePing = async () => {
    if (!pingUrl.trim()) {
      addToast({
        type: 'warning',
        title: 'Chưa nhập URL',
        message: 'Vui lòng nhập URL cần ping',
      });
      return;
    }

    setPingLoading(true);
    try {
      const result = await seoApi.pingUrl(pingUrl, 'publish');
      if (result.google_success || result.bing_success) {
        addToast({
          type: 'success',
          title: 'Ping thành công',
          message: `Google: ${result.google_success ? 'OK' : 'Fail'}, Bing: ${result.bing_success ? 'OK' : 'Fail'}`,
        });
      } else {
        addToast({
          type: 'error',
          title: 'Ping thất bại',
          message: result.error || 'Không thể ping URL',
        });
      }
    } catch (error) {
      addToast({
        type: 'error',
        title: 'Lỗi',
        message: String(error),
      });
    } finally {
      setPingLoading(false);
    }
  };

  const handleRefreshLinks = async () => {
    setRefreshingLinks(true);
    try {
      const result = await seoApi.refreshLinks();
      addToast({
        type: 'success',
        title: 'Đã cập nhật',
        message: `Đã cập nhật ${result.stats?.updated || 0} bài viết`,
      });
      await loadData();
    } catch (error) {
      addToast({
        type: 'error',
        title: 'Lỗi',
        message: String(error),
      });
    } finally {
      setRefreshingLinks(false);
    }
  };

  const handleTestConnections = async () => {
    setPingLoading(true);
    try {
      const result = await seoApi.testConnections();
      if (result.overall === 'ok') {
        addToast({
          type: 'success',
          title: 'Kết nối thành công',
          message: 'Google & Bing đã được kết nối',
        });
      } else if (result.overall === 'partial') {
        addToast({
          type: 'warning',
          title: 'Kết nối một phần',
          message: 'Một số dịch vụ chưa được cấu hình',
        });
      } else {
        addToast({
          type: 'error',
          title: 'Chưa cấu hình',
          message: 'Vui lòng cấu hình Google Indexing API và Bing API Key',
        });
      }
      setHealth(result);
    } catch (error) {
      addToast({
        type: 'error',
        title: 'Lỗi',
        message: String(error),
      });
    } finally {
      setPingLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Đang tải...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">SEO Crawler Bot</h1>
        <button
          onClick={handleTestConnections}
          disabled={pingLoading}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium disabled:opacity-50"
        >
          {pingLoading ? 'Đang kiểm tra...' : '🔗 Kiểm tra kết nối'}
        </button>
      </div>

      {/* Connection Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Google Status */}
        <div className={`p-6 rounded-lg shadow border ${
          health?.ping_service?.google?.status === 'connected'
            ? 'bg-green-50 border-green-200'
            : health?.ping_service?.google?.status === 'not_configured'
            ? 'bg-yellow-50 border-yellow-200'
            : 'bg-red-50 border-red-200'
        }`}>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center shadow-sm">
              <span className="text-2xl">🔍</span>
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Google Indexing API</h3>
              <p className={`text-sm ${
                health?.ping_service?.google?.status === 'connected'
                  ? 'text-green-600'
                  : 'text-yellow-600'
              }`}>
                {health?.ping_service?.google?.status === 'connected' ? 'Đã kết nối' : 'Chưa cấu hình'}
              </p>
            </div>
          </div>
          {health?.ping_service?.google?.status !== 'connected' && (
            <div className="text-sm text-gray-600 space-y-2">
              <p>Cần cấu hình:</p>
              <ol className="list-decimal list-inside space-y-1 text-xs">
                <li>Tạo Service Account trong Google Cloud Console</li>
                <li>Cấp quyền Indexing API</li>
                <li>Thêm email vào Google Search Console</li>
                <li>Set GOOGLE_SERVICE_ACCOUNT_JSON env</li>
              </ol>
            </div>
          )}
          {health?.ping_service?.google?.site_url && (
            <div className="mt-3 text-xs text-gray-500">
              Site: {health.ping_service.google.site_url}
            </div>
          )}
        </div>

        {/* Bing Status */}
        <div className={`p-6 rounded-lg shadow border ${
          health?.ping_service?.bing?.status === 'connected'
            ? 'bg-green-50 border-green-200'
            : health?.ping_service?.bing?.status === 'not_configured'
            ? 'bg-yellow-50 border-yellow-200'
            : 'bg-red-50 border-red-200'
        }`}>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center shadow-sm">
              <span className="text-2xl">🌐</span>
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Bing Webmaster API</h3>
              <p className={`text-sm ${
                health?.ping_service?.bing?.status === 'connected'
                  ? 'text-green-600'
                  : 'text-yellow-600'
              }`}>
                {health?.ping_service?.bing?.status === 'connected' ? 'Đã kết nối' : 'Chưa cấu hình'}
              </p>
            </div>
          </div>
          {health?.ping_service?.bing?.status !== 'connected' && (
            <div className="text-sm text-gray-600 space-y-2">
              <p>Cần cấu hình:</p>
              <ol className="list-decimal list-inside space-y-1 text-xs">
                <li>Đăng ký site trong Bing Webmaster Tools</li>
                <li>Lấy API Key</li>
                <li>Set BING_API_KEY env</li>
              </ol>
            </div>
          )}
          {health?.ping_service?.bing?.api_key_prefix && (
            <div className="mt-3 text-xs text-gray-500">
              Key: {health.ping_service.bing.api_key_prefix}
            </div>
          )}
        </div>

        {/* Internal Linking Status */}
        <div className="p-6 rounded-lg shadow border bg-white border-gray-200">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center shadow-sm">
              <span className="text-2xl">🔗</span>
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Internal Linking</h3>
              <p className="text-sm text-green-600">Hoạt động</p>
            </div>
          </div>
          {linkStats && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Tổng bài viết:</span>
                <span className="font-medium">{linkStats.total_articles}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Có internal links:</span>
                <span className="font-medium">{linkStats.articles_with_internal_links}</span>
              </div>
              <div className="mt-3">
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-gray-500">Coverage</span>
                  <span className="font-medium">{linkStats.coverage_percent}%</span>
                </div>
                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary-500 rounded-full"
                    style={{ width: `${linkStats.coverage_percent}%` }}
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Manual Ping Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          📡 Ping URL to Search Engines
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          Ping thủ công một URL để thông báo Google và Bing về bài viết mới hoặc thay đổi.
        </p>
        <div className="flex gap-3">
          <input
            type="url"
            value={pingUrl}
            onChange={(e) => setPingUrl(e.target.value)}
            placeholder="https://example.com/article-slug"
            className="flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
          />
          <button
            onClick={handlePing}
            disabled={pingLoading || !pingUrl.trim()}
            className="px-6 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium disabled:opacity-50"
          >
            {pingLoading ? 'Đang ping...' : '🚀 Ping'}
          </button>
        </div>
      </div>

      {/* Internal Linking Management */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold flex items-center gap-2">
              🔗 Internal Linking Engine
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              Tự động thêm links giữa các bài viết liên quan
            </p>
          </div>
          <button
            onClick={handleRefreshLinks}
            disabled={refreshingLinks}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium disabled:opacity-50"
          >
            {refreshingLinks ? 'Đang cập nhật...' : '🔄 Refresh All Links'}
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="text-2xl font-bold text-gray-900">{linkStats?.total_articles || 0}</div>
            <div className="text-sm text-gray-500">Tổng bài viết</div>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="text-2xl font-bold text-gray-900">{linkStats?.articles_with_internal_links || 0}</div>
            <div className="text-sm text-gray-500">Có internal links</div>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="text-2xl font-bold text-primary-600">{linkStats?.coverage_percent || 0}%</div>
            <div className="text-sm text-gray-500">Tỷ lệ coverage</div>
          </div>
        </div>

        <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-100">
          <h3 className="font-medium text-blue-900 mb-2">📋 Cách hoạt động</h3>
          <ul className="text-sm text-blue-700 space-y-1">
            <li><strong>New → Old:</strong> Bài viết mới tự động link đến các bài cũ trong cùng category</li>
            <li><strong>Old → New:</strong> Các bài viết gần đây được cập nhật để link đến bài mới</li>
            <li><strong>Related Posts:</strong> Mỗi bài viết có section "See Also" với các bài liên quan</li>
          </ul>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">⚡ Quick Actions</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <button
            onClick={() => {
              navigator.clipboard.writeText('https://example.com/sitemap.xml');
              addToast({ type: 'success', title: 'Đã copy', message: 'Sitemap URL copied!' });
            }}
            className="p-4 bg-gray-50 hover:bg-gray-100 rounded-lg text-center transition-colors"
          >
            <div className="text-2xl mb-2">🗺️</div>
            <div className="text-sm font-medium">Sitemap</div>
            <div className="text-xs text-gray-500">/sitemap.xml</div>
          </button>
          <button
            onClick={() => {
              navigator.clipboard.writeText('https://example.com/sitemap-news.xml');
              addToast({ type: 'success', title: 'Đã copy', message: 'News Sitemap URL copied!' });
            }}
            className="p-4 bg-gray-50 hover:bg-gray-100 rounded-lg text-center transition-colors"
          >
            <div className="text-2xl mb-2">📰</div>
            <div className="text-sm font-medium">News Sitemap</div>
            <div className="text-xs text-gray-500">/sitemap-news.xml</div>
          </button>
          <button
            onClick={() => {
              navigator.clipboard.writeText('https://example.com/robots.txt');
              addToast({ type: 'success', title: 'Đã copy', message: 'Robots.txt URL copied!' });
            }}
            className="p-4 bg-gray-50 hover:bg-gray-100 rounded-lg text-center transition-colors"
          >
            <div className="text-2xl mb-2">🤖</div>
            <div className="text-sm font-medium">Robots.txt</div>
            <div className="text-xs text-gray-500">/robots.txt</div>
          </button>
          <button
            onClick={() => window.open('https://search.google.com/search-console', '_blank')}
            className="p-4 bg-gray-50 hover:bg-gray-100 rounded-lg text-center transition-colors"
          >
            <div className="text-2xl mb-2">🔧</div>
            <div className="text-sm font-medium">GSC</div>
            <div className="text-xs text-gray-500">Search Console</div>
          </button>
        </div>
      </div>
    </div>
  );
}

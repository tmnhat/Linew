import { useState, useEffect } from 'react';
import { sourcesApi, Source } from '../services/api';
import { formatDistanceToNow } from 'date-fns';
import { vi } from 'date-fns/locale';
import clsx from 'clsx';

export default function Sources() {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingSource, setEditingSource] = useState<Source | null>(null);
  const [testingResult, setTestingResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [fetchingSourceId, setFetchingSourceId] = useState<string | null>(null);

  const loadSources = async () => {
    try {
      const data = await sourcesApi.list();
      setSources(data.sources || data || []);
    } catch (error) {
      console.error('Failed to load sources:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSources();
  }, []);

  const handleDelete = async (id: string) => {
    if (!confirm('Bạn có chắc muốn xóa nguồn tin này?')) return;
    try {
      await sourcesApi.delete(id);
      setSources((prev) => prev.filter((s) => s.id !== id));
    } catch (error) {
      console.error('Delete failed:', error);
    }
  };

  const handleTest = async (feedUrl: string) => {
    setTestingResult(null);
    try {
      const result = await sourcesApi.test(feedUrl);
      setTestingResult({ ok: true, message: JSON.stringify(result, null, 2) });
    } catch (error) {
      setTestingResult({ ok: false, message: String(error) });
    }
  };

  const handleFetch = async (sourceId?: string) => {
    setFetchingSourceId(sourceId || 'all');
    try {
      const result = await sourcesApi.fetch(sourceId);
      alert(result.message || 'Đã bắt đầu thu thập tín hiệu');
    } catch (error) {
      console.error('Fetch failed:', error);
    } finally {
      setFetchingSourceId(null);
    }
  };

  const handleDiscover = async () => {
    const siteUrl = prompt('Nhập URL trang web để khám phá nguồn RSS:');
    if (!siteUrl) return;
    try {
      const feeds = await sourcesApi.discover(siteUrl);
      const feedList = Array.isArray(feeds) ? feeds : feeds.feeds || [];
      if (feedList.length === 0) {
        alert('Không tìm thấy nguồn RSS nào');
        return;
      }
      const confirmImport = confirm(`Tìm thấy ${feedList.length} nguồn RSS. Thêm vào danh sách?`);
      if (confirmImport) {
        for (const feed of feedList) {
          await sourcesApi.create({
            name: feed.title || siteUrl,
            feed_url: feed.url,
            site_url: siteUrl,
            language: 'vi',
            is_active: true,
            crawl_difficulty: 'easy',
            requires_flaresolverr: false,
          });
        }
        loadSources();
      }
    } catch (error) {
      console.error('Discover failed:', error);
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
        <h1 className="text-2xl font-bold text-gray-900">Nguồn tin</h1>
        <div className="flex gap-2">
          <button
            onClick={handleDiscover}
            className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg text-sm font-medium"
          >
            🔍 Khám phá RSS
          </button>
          <button
            onClick={() => handleFetch()}
            disabled={!!fetchingSourceId}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium disabled:opacity-50"
          >
            {fetchingSourceId === 'all' ? '⏳ Đang thu thập...' : '📡 Thu thập tất cả'}
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-medium"
          >
            + Thêm nguồn
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tên</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Feed URL</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ngôn ngữ</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Trạng thái</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Thu thập lần cuối</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Hành động</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sources.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                  Chưa có nguồn tin nào. Thêm nguồn để bắt đầu.
                </td>
              </tr>
            ) : (
              sources.map((source) => (
                <tr key={source.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{source.name}</div>
                    {source.category_hint && (
                      <div className="text-xs text-gray-500">{source.category_hint}</div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <a
                      href={source.feed_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-600 hover:underline font-mono"
                    >
                      {source.feed_url.length > 50
                        ? source.feed_url.substring(0, 50) + '...'
                        : source.feed_url}
                    </a>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs px-2 py-1 bg-gray-100 rounded">
                      {source.language}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={clsx(
                        'text-xs px-2 py-1 rounded',
                        source.is_active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-600'
                      )}
                    >
                      {source.is_active ? 'Hoạt động' : 'Tắt'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {source.last_fetched_at
                      ? formatDistanceToNow(new Date(source.last_fetched_at), {
                          addSuffix: true,
                          locale: vi,
                        })
                      : 'Chưa bao giờ'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-1">
                      <button
                        onClick={() => handleFetch(source.id)}
                        disabled={!!fetchingSourceId}
                        className="px-2 py-1 text-xs text-blue-600 hover:bg-blue-50 rounded"
                        title="Thu thập ngay"
                      >
                        📡
                      </button>
                      <button
                        onClick={() => handleTest(source.feed_url)}
                        className="px-2 py-1 text-xs text-green-600 hover:bg-green-50 rounded"
                        title="Kiểm tra feed"
                      >
                        🧪
                      </button>
                      <button
                        onClick={() => setEditingSource(source)}
                        className="px-2 py-1 text-xs text-gray-600 hover:bg-gray-100 rounded"
                        title="Sửa"
                      >
                        ✏️
                      </button>
                      <button
                        onClick={() => handleDelete(source.id)}
                        className="px-2 py-1 text-xs text-red-600 hover:bg-red-50 rounded"
                        title="Xóa"
                      >
                        🗑️
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {(showAddModal || editingSource) && (
        <SourceModal
          source={editingSource}
          onClose={() => {
            setShowAddModal(false);
            setEditingSource(null);
          }}
          onSave={() => {
            setShowAddModal(false);
            setEditingSource(null);
            loadSources();
          }}
        />
      )}

      {testingResult && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-lg w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">
              Kết quả kiểm tra {testingResult.ok ? '✅' : '❌'}
            </h3>
            <pre className="text-xs bg-gray-100 p-4 rounded overflow-auto max-h-64 whitespace-pre-wrap">
              {testingResult.message}
            </pre>
            <button
              onClick={() => setTestingResult(null)}
              className="mt-4 px-4 py-2 bg-gray-600 text-white rounded-lg"
            >
              Đóng
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function SourceModal({
  source,
  onClose,
  onSave,
}: {
  source: Source | null;
  onClose: () => void;
  onSave: () => void;
}) {
  const [form, setForm] = useState({
    name: source?.name || '',
    feed_url: source?.feed_url || '',
    site_url: source?.site_url || '',
    category_hint: source?.category_hint || '',
    language: source?.language || 'vi',
    is_active: source?.is_active ?? true,
    crawl_difficulty: source?.crawl_difficulty || 'easy',
    requires_flaresolverr: source?.requires_flaresolverr ?? false,
  });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (source) {
        await sourcesApi.update(source.id, form);
      } else {
        await sourcesApi.create(form);
      }
      onSave();
    } catch (error) {
      console.error('Save failed:', error);
      alert('Lưu thất bại: ' + error);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-lg w-full mx-4">
        <h3 className="text-lg font-semibold mb-4">
          {source ? 'Sửa nguồn tin' : 'Thêm nguồn tin'}
        </h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tên</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              required
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Feed URL</label>
            <input
              type="url"
              value={form.feed_url}
              onChange={(e) => setForm((f) => ({ ...f, feed_url: e.target.value }))}
              required
              placeholder="https://example.com/feed"
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Site URL</label>
            <input
              type="url"
              value={form.site_url}
              onChange={(e) => setForm((f) => ({ ...f, site_url: e.target.value }))}
              placeholder="https://example.com"
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Ngôn ngữ</label>
              <select
                value={form.language}
                onChange={(e) => setForm((f) => ({ ...f, language: e.target.value }))}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="vi">Tiếng Việt</option>
                <option value="en">English</option>
                <option value="auto">Tự động</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Độ khó</label>
              <select
                value={form.crawl_difficulty}
                onChange={(e) => setForm((f) => ({ ...f, crawl_difficulty: e.target.value }))}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="easy">Dễ</option>
                <option value="medium">Trung bình</option>
                <option value="hard">Khó</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Gợi ý danh mục</label>
            <input
              type="text"
              value={form.category_hint}
              onChange={(e) => setForm((f) => ({ ...f, category_hint: e.target.value }))}
              placeholder="công nghệ, kinh tế, thể thao..."
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <div className="flex items-center gap-6">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
                className="w-4 h-4 text-primary-600 rounded"
              />
              <span className="text-sm">Hoạt động</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.requires_flaresolverr}
                onChange={(e) => setForm((f) => ({ ...f, requires_flaresolverr: e.target.checked }))}
                className="w-4 h-4 text-primary-600 rounded"
              />
              <span className="text-sm">Cần FlareSolverr</span>
            </label>
          </div>
          <div className="flex justify-end gap-2 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              Hủy
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg disabled:opacity-50"
            >
              {saving ? 'Đang lưu...' : 'Lưu'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

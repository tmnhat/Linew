import { useState, useEffect } from 'react';
import { newsletterApi, NewsletterStats, NewsletterSubscriber } from '../services/api';
import { useToastStore } from '../store/toast';

export default function NewsletterPage() {
  const { addToast } = useToastStore();
  const [stats, setStats] = useState<NewsletterStats | null>(null);
  const [subscribers, setSubscribers] = useState<NewsletterSubscriber[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newEmail, setNewEmail] = useState('');
  const [newName, setNewName] = useState('');
  const [testEmail, setTestEmail] = useState(false);

  const loadData = async () => {
    try {
      const [statsData, subscribersData] = await Promise.all([
        newsletterApi.getStats(),
        newsletterApi.getSubscribers({ limit: 100 }),
      ]);
      setStats(statsData);
      setSubscribers(subscribersData.subscribers || []);
    } catch (error) {
      console.error('Failed to load newsletter data:', error);
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

  const handleSubscribe = async () => {
    if (!newEmail) {
      addToast({
        type: 'error',
        title: 'Lỗi',
        message: 'Vui lòng nhập email',
      });
      return;
    }

    try {
      const result = await newsletterApi.subscribe(newEmail, newName);
      if (result.success) {
        addToast({
          type: 'success',
          title: 'Thành công',
          message: result.message || 'Đăng ký thành công!',
        });
        setNewEmail('');
        setNewName('');
        setShowAddModal(false);
        loadData();
      } else {
        addToast({
          type: 'error',
          title: 'Thất bại',
          message: result.message || 'Email đã được đăng ký',
        });
      }
    } catch (error) {
      addToast({
        type: 'error',
        title: 'Lỗi',
        message: String(error),
      });
    }
  };

  const handleUnsubscribe = async (email: string) => {
    if (!confirm(`Hủy đăng ký ${email}?`)) return;

    try {
      const result = await newsletterApi.unsubscribe(email);
      if (result.success) {
        addToast({
          type: 'success',
          title: 'Thành công',
          message: 'Đã hủy đăng ký',
        });
        loadData();
      } else {
        addToast({
          type: 'error',
          title: 'Thất bại',
          message: result.message,
        });
      }
    } catch (error) {
      addToast({
        type: 'error',
        title: 'Lỗi',
        message: String(error),
      });
    }
  };

  const handleTestEmail = async () => {
    if (!newEmail) {
      addToast({
        type: 'error',
        title: 'Lỗi',
        message: 'Vui lòng nhập email để test',
      });
      return;
    }

    setTestEmail(true);
    try {
      const result = await newsletterApi.subscribe(newEmail, 'Test User');
      if (result.success || result.message?.includes('kích hoạt')) {
        addToast({
          type: 'success',
          title: 'Thành công',
          message: 'Email hợp lệ, có thể nhận email',
        });
      } else {
        addToast({
          type: 'warning',
          title: 'Cảnh báo',
          message: result.message,
        });
      }
    } catch (error) {
      addToast({
        type: 'error',
        title: 'Lỗi',
        message: String(error),
      });
    } finally {
      setTestEmail(false);
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
        <h1 className="text-2xl font-bold text-gray-900">Newsletter</h1>
        <div className="flex gap-3">
          <button
            onClick={loadData}
            className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg font-medium"
          >
            🔄 Refresh
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium"
          >
            ➕ Thêm Subscriber
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
              <span className="text-2xl">👥</span>
            </div>
            <div>
              <div className="text-3xl font-bold text-gray-900">{stats?.total || 0}</div>
              <div className="text-sm text-gray-500">Tổng subscribers</div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
              <span className="text-2xl">✅</span>
            </div>
            <div>
              <div className="text-3xl font-bold text-green-600">{stats?.active || 0}</div>
              <div className="text-sm text-gray-500">Active</div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
              <span className="text-2xl">❌</span>
            </div>
            <div>
              <div className="text-3xl font-bold text-red-600">{stats?.inactive || 0}</div>
              <div className="text-sm text-gray-500">Inactive</div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center">
              <span className="text-2xl">📊</span>
            </div>
            <div>
              <div className="text-3xl font-bold text-purple-600">
                {stats?.total ? Math.round((stats.active / stats.total) * 100) : 0}%
              </div>
              <div className="text-sm text-gray-500">Active Rate</div>
            </div>
          </div>
        </div>
      </div>

      {/* Category Breakdown */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Phân bố theo danh mục</h2>
        <div className="flex gap-8">
          {Object.entries(stats?.by_category || {}).map(([category, count]) => (
            <div key={category} className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
                <span className="text-lg">
                  {category === 'tech' ? '💻' : category === 'finance' ? '💰' : '📰'}
                </span>
              </div>
              <div>
                <div className="font-semibold text-gray-900 capitalize">{category}</div>
                <div className="text-sm text-gray-500">{count} subscribers</div>
              </div>
            </div>
          ))}
          {Object.keys(stats?.by_category || {}).length === 0 && (
            <div className="text-gray-500">Chưa có dữ liệu</div>
          )}
        </div>
      </div>

      {/* Subscribers Table */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b">
          <h2 className="text-lg font-semibold">Danh sách Subscribers</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Categories</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Frequency</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Subscribed</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Sent</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {subscribers.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-6 py-8 text-center text-gray-500">
                    Chưa có subscribers nào
                  </td>
                </tr>
              ) : (
                subscribers.map((sub) => (
                  <tr key={sub.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="font-medium text-gray-900">{sub.email}</div>
                    </td>
                    <td className="px-6 py-4 text-gray-500">{sub.name || '-'}</td>
                    <td className="px-6 py-4">
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-medium ${
                          sub.is_active
                            ? 'bg-green-100 text-green-700'
                            : 'bg-red-100 text-red-700'
                        }`}
                      >
                        {sub.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex gap-1">
                        {(sub.categories || []).map((cat) => (
                          <span
                            key={cat}
                            className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs"
                          >
                            {cat}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-gray-500 capitalize">{sub.frequency}</td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {new Date(sub.subscribed_at).toLocaleDateString('vi-VN')}
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm">
                        <span className="font-medium">{sub.total_sent}</span>
                        <span className="text-gray-400"> sent</span>
                        <span className="mx-1">/</span>
                        <span className="font-medium">{sub.total_opened}</span>
                        <span className="text-gray-400"> opened</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {sub.is_active && (
                        <button
                          onClick={() => handleUnsubscribe(sub.email)}
                          className="text-red-600 hover:text-red-700 text-sm font-medium"
                        >
                          Hủy
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Subscriber Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
            <h3 className="text-lg font-semibold mb-4">Thêm Subscriber</h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email *
                </label>
                <input
                  type="email"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  placeholder="email@example.com"
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Name
                </label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="Optional"
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
                />
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={handleTestEmail}
                disabled={testEmail || !newEmail}
                className="flex-1 py-2 px-4 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg font-medium disabled:opacity-50"
              >
                {testEmail ? '⏳ Testing...' : '🔗 Test Email'}
              </button>
              <button
                onClick={handleSubscribe}
                className="flex-1 py-2 px-4 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium"
              >
                Đăng ký
              </button>
              <button
                onClick={() => {
                  setShowAddModal(false);
                  setNewEmail('');
                  setNewName('');
                }}
                className="py-2 px-4 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg font-medium"
              >
                Hủy
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
